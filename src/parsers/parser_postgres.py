import json
import os
import re
from typing import Dict, List, Tuple, Optional, Union

# import sqlglot  (unused)
import sqlfluff
from sqlglot import parse, exp


from ..dataflow_structs import NodeInfo as NodeInfo, InvalidSQLError


class NodeInfoPG(NodeInfo, total=False):
    constraints: List[str]  # For potential future use, not heavily used in current code
    definition_parts: List[str]  # Internal list to accumulate DDL segments

SQL_PATTERNS = [
    r"CREATE\s+TABLE", r"ALTER\s+TABLE", r"CREATE\s+VIEW",
    r"CREATE\s+MATERIALIZED\s+VIEW", r"CREATE\s+FUNCTION",
    r"CREATE\s+PROCEDURE", r"CREATE\s+TYPE", r"CREATE\s+DOMAIN",
    r"CREATE\s+SEQUENCE",
] # Basic patterns to check if content is SQL DDL


def _extract_schema(schema_expr: Optional[exp.Expression]) -> Optional[str]:
    """Extracts schema name from a schema expression node (Identifier)."""
    if isinstance(schema_expr, exp.Identifier):
        return schema_expr.name
    return None


def format_sql(definition: str) -> str:
    """Pretty-format SQL definition using sqlfluff if available, else sqlglot."""
    try:
        # Use sqlfluff to lint and fix the SQL for formatting
        formatted = sqlfluff.fix(definition, dialect='postgres')
        if formatted and formatted.strip():
            return formatted.strip()
    except Exception:
        pass  # Fallback to sqlglot if sqlfluff is not available or fails

   
    # Fallback to simple strip if formatting fails for any reason
    return definition.strip()


def add_node(
    name: str,
    node_type: str,
    schema: Optional[str],
    definition: Optional[str], # SQL text of the statement being processed
    node_types: Dict[str, NodeInfoPG],
) -> str:
    """
    Adds or updates a node in the node_types dictionary.
    Nodes are keyed by their full name (e.g., "schema.name").
    This function accumulates definitions (e.g., from CREATE and subsequent ALTER statements).
    Definitions are pretty-formatted.
    Returns the full_name key of the node.
    """
    if not name: # Skip if name is somehow empty
        # This case should ideally be prevented by callers or parser.
        # Consider logging a warning if this happens.
        return "" 
        
    full_name = f"{schema + '.' if schema else ''}{name}"
    
    # Retrieve existing node info or initialize a new one if it's the first time seeing this node.
    # Type casting to NodeInfoPG for type checker, assuming dict matches NodeInfoPG structure.
    existing_info = node_types.get(full_name)
    # Initialize or reuse a single info dict, including DDL parts and initial definition
    info: NodeInfoPG = existing_info if existing_info else {
        "constraints": [],
        "definition_parts": [],
        "type": node_type,
        "database": schema or "",
        "full_name": full_name,
        "definition": None
    }  # type: ignore

    # Append the new DDL segment
    if definition:
        formatted_part = format_sql(definition)
        info["definition_parts"].append(formatted_part)
        info["definition"] = "\n\n-- Additional DDL --\n".join(info["definition_parts"])

    node_types[full_name] = info
    return full_name


def find_dependencies(query_expr: exp.Expression) -> List[Tuple[str, Optional[str]]]:
    """
    Finds all table/view dependencies within a given SQL query expression.
    Useful for identifying source tables for views, CTAS, or CTEs.
    Returns a list of (table_name, schema_name) tuples.
    """
    deps: List[Tuple[str, Optional[str]]] = []
    # find_all(exp.Table) gets all table objects mentioned in the expression.
    for tbl_expr in query_expr.find_all(exp.Table):
        table_name = tbl_expr.name
        # Schema can be in 'db' (most common) or 'catalog' part of the table expression.
        schema_name = _extract_schema(tbl_expr.args.get("db") or tbl_expr.args.get("catalog"))
        if table_name: # Ensure a table name was actually found.
            deps.append((table_name, schema_name))
    return deps


def find_foreign_keys(statement_expr: Union[exp.Create, exp.Alter]) -> List[Tuple[str, str]]:
    """
    Extracts foreign key references from a CREATE or ALTER statement.
    Returns a list of (local_table_full_name, referenced_table_full_name) tuples.
    This represents an edge: local_table_full_name -> referenced_table_full_name.
    """
    fks: List[Tuple[str, str]] = []
    # Iterate over all ForeignKey expressions within the given statement.
    for fk_constraint_expr in statement_expr.find_all(exp.ForeignKey):
        # The ForeignKey constraint is part of a larger statement (CREATE/ALTER).
        # We need to identify the table this statement applies to (the local table).
        
        # `statement_expr.this` should point to the table being created or altered.
        if not isinstance(statement_expr.this, exp.Table):
            continue # Should be a table for FKs.

        local_table_obj = statement_expr.this
        local_table_name = local_table_obj.name
        local_schema_name = _extract_schema(local_table_obj.args.get("db") or local_table_obj.args.get("catalog"))
        local_full_name = f"{local_schema_name + '.' if local_schema_name else ''}{local_table_name}"

        # The 'reference' (or 'references') arg in ForeignKey points to the referenced table.
        referenced_table_expr = fk_constraint_expr.args.get('reference') or fk_constraint_expr.args.get('references')
        if isinstance(referenced_table_expr, exp.Table):
            ref_table_name = referenced_table_expr.name
            ref_schema_name = _extract_schema(referenced_table_expr.args.get("db") or referenced_table_expr.args.get("catalog"))
            ref_full_name = f"{ref_schema_name + '.' if ref_schema_name else ''}{ref_table_name}"
            
            if local_full_name and ref_full_name: # Ensure both names are valid
                 fks.append((local_full_name, ref_full_name))
            
    return fks


def parse_dump(
    file_path_or_sql_string: Union[str, os.PathLike],
) -> Tuple[List[Tuple[str, str]], Dict[str, NodeInfoPG], Dict[str, int]]:
    """
    Parses a SQL dump file (or a string containing SQL) to extract schema information,
    dependencies (e.g., for views), and foreign keys.
    """
    try:
        # Check if input is a file path and read it.
        if isinstance(file_path_or_sql_string, (str, os.PathLike)) and os.path.exists(file_path_or_sql_string):
             with open(file_path_or_sql_string, "r", encoding="utf-8") as f:
                content = f.read()
        # If not an existing path, assume it's an SQL string.
        elif isinstance(file_path_or_sql_string, str):
            content = file_path_or_sql_string
        else:
            raise ValueError("Invalid input: an existing file path or an SQL string is required.")
    except Exception as e:
        # Catch-all for file reading errors or other initial issues.
        raise ValueError(f"Error reading input: {e}")


    # Pre-processing: Comment out lines that are not DDL for tables/views or are problematic for parsing.
    # Remove all comments (single-line and block)
    def _remove_sql_comments(sql: str) -> str:
        # Remove block comments
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        # Remove single-line comments
        sql = re.sub(r'--.*?$', '', sql, flags=re.MULTILINE)
        return sql

    content = _remove_sql_comments(content)
    
    lines = content.splitlines()
    cleaned_lines: List[str] = []
    in_copy_data_block: bool = False # Flag for being inside a COPY ... FROM STDIN data block.
    in_ignored_multiline_statement: bool = False # True if inside a multi-line statement to be ignored
    ignored_statement_type: Optional[str] = None # Stores type like "FUNCTION", "TRIGGER"

    # Regex to detect start of ignored DDL statements that might be multi-line
    ignored_ddl_start_regex = re.compile(
        r'^\s*(CREATE|ALTER)\s+(?:OR\s+REPLACE\s+)?(SCHEMA|INDEX|FUNCTION|TRIGGER|PROCEDURE|SEQUENCE)\b',
        re.IGNORECASE
    )
    # Regex for other single-line ignored commands (e.g., \connect, SET var =, SELECT pg_catalog.setval)
    # pg_dump uses "SET name = value;"
    other_ignored_line_regex = re.compile(
        r'^\s*(?:\\connect|\\set|SET\s+[a-zA-Z_][a-zA-Z0-9_]*\s*=|SELECT\s+pg_catalog\.setval)\b',
        re.IGNORECASE
    )
    
    
    for line in lines:
        stripped_line = line.strip()
        
        # Handle COPY ... FROM STDIN data blocks
        if in_copy_data_block:
            cleaned_lines.append(f"--{line}") # Comment out lines within COPY data
            if stripped_line == '\\.' or re.match(r'^\\\.', stripped_line): # End of COPY data
                in_copy_data_block = False
            continue
        
        # Detect start of COPY ... FROM STDIN statement
        if re.match(r'^\s*COPY\s+.*\s+FROM\s+ST(?:DIN)?', stripped_line, re.IGNORECASE):
            cleaned_lines.append(f"--{line}") # Comment out the COPY statement itself
            if not stripped_line.endswith('\\.'): # If data is on subsequent lines
                in_copy_data_block = True
            continue

        # Handle lines within an ignored multi-line DDL statement
        if in_ignored_multiline_statement:
            cleaned_lines.append(f"--{line}") # Comment out the line
            
            terminated = False
            # Check for termination based on statement type
            if ignored_statement_type in ("FUNCTION", "PROCEDURE"):
                # For functions/procedures, termination is typically '$$;'
                if re.search(r'\$\$\s*;$', stripped_line): # Ends with '$$;' possibly with space
                    terminated = True
            elif stripped_line.endswith(';'): # For other types (TRIGGER, SEQUENCE, etc.)
                terminated = True
            
            if terminated:
                in_ignored_multiline_statement = False
                ignored_statement_type = None
            continue

        # Detect start of an ignored DDL statement (CREATE/ALTER FUNCTION, TRIGGER, etc.)
        match_ignored_ddl = ignored_ddl_start_regex.match(stripped_line)
        if match_ignored_ddl:
            cleaned_lines.append(f"--{line}") # Comment out the starting line
            
            current_statement_main_type = match_ignored_ddl.group(2).upper() # FUNCTION, TRIGGER, etc.

            # Determine if it's single-line or multi-line
            is_single_line_terminated = False
            if current_statement_main_type in ("FUNCTION", "PROCEDURE"):
                if re.search(r'\$\$\s*;$', stripped_line):
                    is_single_line_terminated = True
            elif stripped_line.endswith(';'):
                is_single_line_terminated = True
            
            if not is_single_line_terminated:
                in_ignored_multiline_statement = True
                ignored_statement_type = current_statement_main_type
            # If single-line, it's handled, and in_ignored_multiline_statement remains False.
            continue

        # Detect other ignored single-line commands (like \set, SET var =, etc.)
        if other_ignored_line_regex.match(stripped_line):
            cleaned_lines.append(f"--{line}")
            continue
        
        # If none of the above, keep the line as is
        cleaned_lines.append(line)
        
    content = "\n".join(cleaned_lines)
    with open("cleaned_sql.sql", "w", encoding="utf-8") as f:
        f.write(content)
    # Basic validation: Check if any relevant DDL patterns are present after cleaning.
    if not content or not any(re.search(pattern, content, re.IGNORECASE) for pattern in SQL_PATTERNS):
        raise InvalidSQLError("Invalid SQL or no relevant DDL statements found after cleaning.")

    # Optional: Use SQLFluff to lint/fix SQL for better parsability if it's installed.
    try:
        import sqlfluff
        content = sqlfluff.fix(content, dialect='postgres', fix_even_unparsable=True)
    except ImportError:
        pass # SQLFluff is optional.

    # Parse the preprocessed SQL content using sqlglot.
    try:
        # `read='postgres'` tells sqlglot to use PostgreSQL dialect.
        parsed_statements = parse(content, read='postgres') 
        if not parsed_statements:  # parse can return None or empty list if content is effectively empty.
            return [], {}, {}
    except Exception as e:
        # Catch parsing errors from sqlglot.
        raise InvalidSQLError(f"SQL parsing failed with sqlglot: {e}")

    node_types: Dict[str, NodeInfoPG] = {} # Stores info about each node (table, view, CTE).
    edges: List[Tuple[str, str]] = []    # Stores relationships (dependencies, FKs) as (source, target) tuples.

    # Process each parsed SQL statement from the dump.
    for stmt_expr in parsed_statements:
        # Handle CREATE TABLE and CREATE VIEW statements.
        if isinstance(stmt_expr, exp.Create) and isinstance(stmt_expr.this, exp.Table):
            table_obj = stmt_expr.this
            name = table_obj.name
            schema = _extract_schema(table_obj.args.get('db') or table_obj.args.get('catalog'))
            
            # Determine if it's a TABLE, VIEW, MATERIALIZED VIEW, etc.
            kind = (stmt_expr.args.get('kind') or 'TABLE').upper()
            # Simplify node type to 'view' if it contains "VIEW", otherwise 'table'.
            node_type = 'view' if 'VIEW' in kind else 'table'
            
            definition_sql = stmt_expr.sql(dialect='postgres') # Get SQL for the CREATE statement.
            node_key = add_node(name, node_type, schema, definition_sql, node_types)

            # Extract foreign keys defined directly within this CREATE TABLE statement.
            edges.extend(find_foreign_keys(stmt_expr))
            
            # For views or CTAS (CREATE TABLE AS SELECT), find dependencies from the SELECT query.
            query_expression = stmt_expr.args.get('expression') # This holds the SELECT part.
            
            if isinstance(query_expression, exp.With): # Handles CTEs (WITH ... AS ...).
                # Process Common Table Expressions first.
                for cte_sub_expr in query_expression.expressions or []: # exp.With.expressions lists exp.CTE.
                    if isinstance(cte_sub_expr, exp.CTE):
                        cte_name = cte_sub_expr.alias_or_name
                        cte_definition_sql = cte_sub_expr.sql(dialect='postgres')
                        # CTEs are like temporary, schemaless views for the query's scope.
                        # Schema is None for CTEs.
                        cte_key = add_node(cte_name, 'cte_view', None, cte_definition_sql, node_types)
                        
                        # Find dependencies for this CTE from its own query part (cte_sub_expr.this).
                        for dep_name, dep_schema in find_dependencies(cte_sub_expr.this):
                            # Add dependency node (usually a table or another view).
                            # Definition is None as we only know its name/schema here.
                            dep_key = add_node(dep_name, 'table', dep_schema, None, node_types)
                            edges.append((dep_key, cte_key)) # Edge: source_object -> cte_view
                # The main query part after the WITH clause.
                query_expression = query_expression.this 
            
            if query_expression: # If there's a main query (view's SELECT, CTAS's SELECT).
                for dep_name, dep_schema in find_dependencies(query_expression):
                    # These are tables/views the main query selects from.
                    # Default type to 'table'; actual DDL will confirm/correct type later if needed.
                    dep_key = add_node(dep_name, 'table', dep_schema, None, node_types)
                    if node_key: # Ensure the main node was successfully added
                        edges.append((dep_key, node_key)) # Edge: source_object -> created_table/view

        # Handle ALTER TABLE statements.
        elif isinstance(stmt_expr, exp.Alter) and isinstance(stmt_expr.this, exp.Table):
            table_obj = stmt_expr.this
            name = table_obj.name
            schema = _extract_schema(table_obj.args.get('db') or table_obj.args.get('catalog'))
            
            definition_sql = stmt_expr.sql(dialect='postgres') # Get SQL for the ALTER statement.
            # Add this ALTER statement's definition to the existing table's node.
            # Node type is 'table' for ALTER TABLE.
            _ = add_node(name, 'table', schema, definition_sql, node_types)
            
            # Extract foreign keys defined or modified by this ALTER TABLE statement.
            edges.extend(find_foreign_keys(stmt_expr))

    # Calculate statistics: count of nodes per schema (excluding CTEs from this stat).
    stats: Dict[str, int] = {}
    for info_dict in node_types.values():
        # info_dict is an instance of NodeInfoPG (a TypedDict), which is a dict at runtime.
        if info_dict.get('type') == 'cte_view': # Check type directly
            continue # Exclude CTEs from schema object counts.
        
        # No need for isinstance(info_dict, dict) here as it's guaranteed by type hints
        schema_name = info_dict.get('database') or 'public' # Default to 'public' if schema is empty/None.
        stats[schema_name] = stats.get(schema_name, 0) + 1

    # Create directory for JSON output if it doesn't exist.
    output_dir = 'json_structure'
    os.makedirs(output_dir, exist_ok=True)
    
    # Save edges and node_types to JSON files.
    try:
        with open(os.path.join(output_dir, 'edges.json'), 'w', encoding='utf-8') as f_edges:
            json.dump(edges, f_edges, indent=2)
        with open(os.path.join(output_dir, 'node_types.json'), 'w', encoding='utf-8') as f_nodes:
            json.dump(node_types, f_nodes, indent=2)
    except IOError as e:
        # Handle potential errors during file writing.
        print(f"Warning: Could not write JSON output files: {e}")


    return edges, node_types, stats
