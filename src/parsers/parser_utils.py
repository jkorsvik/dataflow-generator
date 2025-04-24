import os
import logging
from typing import List, Tuple, Dict, Set, Optional, Union, Callable

from sqlfluff.core import Linter, SQLLintError
from sqlfluff.core.parser.segments.base import BaseSegment

from src.dataflow_structs import NodeInfo
from src.exceptions import InvalidSQLError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# --- Node Management ---

def add_node(
    nodes: Dict[str, NodeInfo],
    full_name: str,
    node_type: str,
    db_objects: Dict[str, Set[str]], # Simplified: Just track objects per DB
    is_dependency: bool = False
) -> Optional[str]:
    \"\"\"Adds or updates node information, prioritizing CTEs. Returns base_name or None.

    Handles quoted identifiers and basic database/schema extraction.
    Updates node type based on a simple priority if the node already exists.
    \"\"\"
    if not full_name:
        return None

    # Handle potentially quoted identifiers and split
    # Regex to handle quotes correctly, even if mismatched (e.g., "schema".table or schema."table")
    parts = re.split(r'\\\.(?=(?:[^"]*"[^"]*")*[^"]*$)(?=(?:[^\\\']*\\\'[^\\\']*\')*[^\\\']*$)', full_name)
    cleaned_parts = [p.strip().strip('"`\'') for p in parts] # Strip quotes and spaces
    base_name = cleaned_parts[-1]

    if not base_name: # Skip if base name is empty after stripping
        return None

    is_new_type_cte = node_type == "cte_view"
    database_or_schema = None
    if len(cleaned_parts) > 1 and not is_new_type_cte:
        # Use the first part as potential DB/Schema name
        database_or_schema = cleaned_parts[0]
    # Note: No 'else', single-part names have database = None

    effective_full_name = base_name if is_new_type_cte else full_name # Use original full_name for non-CTEs

    # Track defined objects per database/schema (optional, for stats)
    if database_or_schema and not is_new_type_cte:
        db_objects.setdefault(database_or_schema, set())
        db_objects[database_or_schema].add(base_name)

    # Add/Update the node in the main dictionary
    if base_name not in nodes:
        nodes[base_name] = {
            "type": node_type,
            "database": database_or_schema or "", # Store empty string if None
            "full_name": effective_full_name,
        }
    else:
        # Existing node logic (prioritize CTE, then view > mview > table)
        existing_info = nodes[base_name]
        current_type = existing_info["type"]
        if current_type == "cte_view":
            pass # CTE type is final
        elif is_new_type_cte:
            existing_info["type"] = "cte_view"
            existing_info["database"] = "" # CTEs don't have a DB/Schema in this context
            existing_info["full_name"] = base_name # Full name is just the base name
        else:
            # Simple priority: view > materialized_view > table > unknown
            type_priority = {"unknown": 0, "table": 1, "materialized_view": 2, "view": 3}
            new_prio = type_priority.get(node_type, 0)
            curr_prio = type_priority.get(current_type, 0)
            if new_prio >= curr_prio:
                existing_info["type"] = node_type
                # Update database/schema only if new one is found and current is empty
                if not existing_info["database"] and database_or_schema:
                    existing_info["database"] = database_or_schema
                    # Update full_name only if it was just the base name before
                    if existing_info["full_name"] == base_name:
                        existing_info["full_name"] = effective_full_name

    return base_name

# --- Dependency Finding ---

def find_dependencies(segment: BaseSegment, defined_ctes: Set[str]) -> Set[str]:
    \"\"\"Recursively finds table/view/CTE references within a segment using common sqlfluff structures.\"\"\"
    dependencies = set()

    # 1. Look for explicit table/view references
    # `table_reference` is common, but might contain nested `object_reference`
    for table_ref_seg in segment.recursive_crawl("table_reference"):
        # Prioritize finding an object_reference within the table_reference
        obj_ref_seg = next(table_ref_seg.recursive_crawl("object_reference"), None)
        if obj_ref_seg:
            # Use the raw content of the object reference
            raw_name = obj_ref_seg.raw.strip().strip('"`\'')
            base_name = raw_name.split('.')[-1].strip('"`\'')
            if base_name not in defined_ctes:
                 # Check if it's not just an alias defined nearby
                 parent_from = table_ref_seg.get_parent_of_type("from_expression_element")
                 alias_name = None
                 if parent_from:
                     alias_seg = next(parent_from.recursive_crawl("alias_expression"), None)
                     if alias_seg:
                          alias_name = alias_seg.raw_segments[-1].raw.strip('"`\'') # Get last part as alias
                 
                 # Add if it's not the alias itself being referenced weirdly
                 if raw_name != alias_name:
                    dependencies.add(raw_name)
        else:
             # Fallback: if no object_reference, use the raw content of table_reference itself?
             # This might be too broad, handle with care. Let's skip for now.
             # raw_name = table_ref_seg.raw.strip().strip('"`\'')
             # base_name = raw_name.split('.')[-1].strip('"`\'')
             # if base_name not in defined_ctes:
             #     dependencies.add(raw_name)
             pass


    # 2. Look for identifiers that might be CTE references
    # Be careful not to pick up column names or aliases. Check context.
    for identifier_seg in segment.recursive_crawl("identifier", "naked_identifier"):
        parent = identifier_seg.get_parent()
        # Check if the parent indicates it's likely a table/cte reference
        # (e.g., part of object_reference, table_reference, or directly after FROM/JOIN)
        is_likely_ref = False
        if parent:
            if parent.is_type("object_reference", "table_reference"):
                is_likely_ref = True
            else:
                # Check preceding segments for FROM/JOIN keywords if parent isn't specific enough
                idx = parent.segments.index(identifier_seg) if identifier_seg in parent.segments else -1
                if idx > 0:
                    prev_seg = parent.segments[idx-1]
                    if prev_seg.is_type("keyword") and prev_seg.raw_upper in ("FROM", "JOIN"):
                        is_likely_ref = True

        if is_likely_ref:
            raw_name = identifier_seg.raw.strip('"`\'')
            # Check if it IS one of the CTEs defined in the current scope
            # (We link *to* CTEs, dependencies *within* CTEs are handled separately)
            if raw_name in defined_ctes:
                dependencies.add(raw_name) # Add the CTE name itself as a dependency

    # Clean up potential empty strings
    dependencies.discard("")

    return dependencies


# --- Main Parsing Orchestrator ---

# Define type hints for the handlers
ProcessSegmentHandler = Callable[[BaseSegment, Dict[str, NodeInfo], Dict[str, Set[str]], Set[str]], Optional[Tuple[str, str]]]
FindDependenciesHandler = Callable[[BaseSegment, Set[str]], Set[str]]

def parse_using_sqlfluff(
    file_path: Union[str, os.PathLike],
    dialect: str,
    created_object_handler: ProcessSegmentHandler,
    dependency_finder: FindDependenciesHandler = find_dependencies # Use default finder
) -> Tuple[List[Tuple[str, str]], Dict[str, NodeInfo], Dict[str, int]]:
    \"\"\"
    Core parsing function using sqlfluff.

    Args:
        file_path: Path to the SQL file or SQL content as string.
        dialect: The sqlfluff dialect name (e.g., 'postgres', 'mysql').
        created_object_handler: A function that takes a statement segment and other state
                                 and returns a tuple of (target_full_name, target_type)
                                 if the statement defines an object, otherwise None.
        dependency_finder: A function to find dependencies within a segment.

    Returns:
        Tuple containing edges, node_types, and database_stats.
    \"\"\"
    logger.info(f"Starting {dialect} parsing for: {file_path}")
    try:
        # Check if file_path is actually content
        if isinstance(file_path, str) and ("\\n" in file_path or ";" in file_path) and not os.path.exists(file_path):
             content = file_path
             logger.info("Input treated as raw SQL content.")
        else:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
            logger.info(f"Read content from file: {file_path}")
    except (FileNotFoundError, OSError, TypeError) as e:
         raise ValueError(f"Invalid input: Could not read file '{file_path}'. Error: {e}")

    if not content.strip():
        raise InvalidSQLError("SQL content is empty.")

    # Initialize results
    edges: List[Tuple[str, str]] = []
    node_types: Dict[str, NodeInfo] = {}
    db_objects: Dict[str, Set[str]] = {} # Tracks objects per DB/Schema for stats
    edge_set: Set[Tuple[str, str]] = set() # Avoid duplicate edges

    # Lint and parse
    linter = Linter(dialect=dialect)
    try:
        linted_path = linter.lint_string(content)
        # Check for unparsable segments
        if any(s.is_type('unparsable') for s in linted_path.tree.recursive_crawl('unparsable')):
             logger.warning(f"File contains unparsable segments according to sqlfluff dialect '{dialect}'. Results may be incomplete.")
             # Optionally raise an error here if strict parsing is required:
             # raise InvalidSQLError(f"SQLFluff found unparsable segments in the file using dialect '{dialect}'.")
        parsed_tree = linted_path.tree
        if not parsed_tree:
             raise InvalidSQLError(f"SQLFluff could not parse the file using dialect '{dialect}'.")
    except SQLLintError as e:
        logger.error(f"SQLFluff parsing error ({dialect}): {e}")
        raise InvalidSQLError(f"SQLFluff parsing failed ({dialect}): {e}") from e
    except Exception as e: # Catch broader exceptions
        logger.error(f"Unexpected error during SQLFluff linting ({dialect}): {e}", exc_info=True)
        raise InvalidSQLError(f"Unexpected SQLFluff error ({dialect}): {e}") from e

    # --- Process statements ---
    statements = parsed_tree.recursive_crawl("statement")
    for stmt in statements:
        defined_ctes: Set[str] = set()
        current_target_base_name: Optional[str] = None

        # 1. Handle WITH clauses (CTEs) - process them first within the statement
        with_clause = next(stmt.recursive_crawl("with_compound_statement"), None)
        cte_segments = {} # Store segment for dependency lookup
        if with_clause:
            for cte_segment in with_clause.recursive_crawl("common_table_expression"):
                # Prefer CommonTableExpressionSegment if available for name
                cte_name_seg = next(cte_segment.recursive_crawl("common_table_expression_identifier","identifier"), None)

                if cte_name_seg:
                    cte_name = cte_name_seg.raw.strip('"`\'')
                    if not cte_name: continue

                    defined_ctes.add(cte_name)
                    cte_segments[cte_name] = cte_segment
                    # Add CTE node
                    add_node(node_types, cte_name, "cte_view", db_objects)


        # Link dependencies *within* CTEs after identifying all CTEs in the clause
        for cte_name, cte_body_segment in cte_segments.items():
             # Find dependencies within this specific CTE body
             # Pass only CTEs defined *before* or *at the same level* if dialect supports it (tricky)
             # For simplicity, pass all CTEs defined in this WITH clause.
             # The finder checks `if base_name not in defined_ctes` for external deps.
             cte_internal_deps = dependency_finder(cte_body_segment, defined_ctes)
             for dep_full_name in cte_internal_deps:
                 dep_base_name = dep_full_name.split('.')[-1].strip('"`\'')
                 if not dep_base_name: continue

                 # Determine dependency type (could be another CTE, table, view)
                 is_cte_dep = dep_base_name in defined_ctes
                 dep_type = "cte_view" if is_cte_dep else node_types.get(dep_base_name, {}).get("type", "unknown")
                 if dep_type == "unknown" and not is_cte_dep:
                     # Basic guess if it's an external dependency we haven't seen defined
                     # Prioritize view slightly if name suggests it
                     dep_type = "view" if any(v in dep_base_name.lower() for v in ['_v_', '_view']) else "table"

                 # Add dependency node (ensure it exists, might update type)
                 dep_node_base = add_node(node_types, dep_full_name, dep_type, db_objects, is_dependency=True)
                 if dep_node_base:
                     edge = (dep_node_base, cte_name) # Dependency -> CTE
                     if edge not in edge_set and dep_node_base != cte_name:
                         edges.append(edge)
                         edge_set.add(edge)

        # 2. Identify the main object being created by the statement (using the handler)
        create_result = created_object_handler(stmt, node_types, db_objects, defined_ctes)

        if create_result:
            target_full_name, target_type = create_result
            current_target_base_name = add_node(node_types, target_full_name, target_type, db_objects)

            # 3. Find dependencies for the main created object (if any)
            if current_target_base_name:
                # Search the whole statement segment for dependencies
                # Pass the CTEs defined in *this* statement's WITH clause
                main_deps = dependency_finder(stmt, defined_ctes)
                for dep_full_name in main_deps:
                    dep_base_name = dep_full_name.split('.')[-1].strip('"`\'')
                    if not dep_base_name: continue

                    # Determine dependency type
                    is_cte_dep = dep_base_name in defined_ctes
                    dep_type = "cte_view" if is_cte_dep else node_types.get(dep_base_name, {}).get("type", "unknown")
                    if dep_type == "unknown" and not is_cte_dep:
                         dep_type = "view" if any(v in dep_base_name.lower() for v in ['_v_', '_view']) else "table"


                    # Add dependency node
                    dep_node_base = add_node(node_types, dep_full_name, dep_type, db_objects, is_dependency=True)

                    if dep_node_base:
                        edge = (dep_node_base, current_target_base_name) # Dependency -> Target
                        if edge not in edge_set and dep_node_base != current_target_base_name:
                            edges.append(edge)
                            edge_set.add(edge)

    # Calculate final database stats
    database_stats: Dict[str, int] = {}
    for node_info in node_types.values():
        # Count objects with a database/schema assigned, excluding CTEs
        if node_info["type"] != "cte_view" and node_info["database"]:
            db_name = node_info["database"]
            database_stats[db_name] = database_stats.get(db_name, 0) + 1

    logger.info(f"{dialect} parsing complete. Found {len(node_types)} nodes and {len(edges)} edges.")
    # Sort nodes by name for consistent output
    sorted_node_types = dict(sorted(node_types.items()))
    return edges, sorted_node_types, database_stats


# --- Dialect Specific Handlers (Examples) ---

def default_created_object_handler(
    stmt: BaseSegment,
    nodes: Dict[str, NodeInfo], # Allow modification if needed for complex cases
    db_objects: Dict[str, Set[str]],
    defined_ctes: Set[str] # Context of CTEs in this statement
) -> Optional[Tuple[str, str]]:
    \"\"\"
    Default handler to find created table/view/mview names.
    Searches for common CREATE statement types and extracts the object reference.
    \"\"\"
    create_types = {
        "create_table_statement": "table",
        "create_view_statement": "view",
        "create_materialized_view_statement": "materialized_view",
        # Add other CREATE types common across dialects if needed
        "create_table_as_select_statement": "table", # Common variation
         "create_schema_statement": "schema", # Could be useful? Ignore for now.
    }

    for seg_type, node_type in create_types.items():
        create_segment = next(stmt.recursive_crawl(seg_type), None)
        if create_segment:
            # Find the primary object reference (table, view name)
            # The reference is often nested, e.g., inside table_reference/view_reference
            ref_container_types = ("table_reference", "view_reference", "object_reference")
            obj_ref = None
            # Search directly first
            obj_ref = next(create_segment.recursive_crawl("object_reference", no_recursive=True), None)
             # If not found directly, search common containers
            if not obj_ref:
                for container_type in ref_container_types:
                    container = next(create_segment.recursive_crawl(container_type, no_recursive=True), None)
                    if container:
                        obj_ref = next(container.recursive_crawl("object_reference"), None)
                        if obj_ref: break # Found it

            if obj_ref:
                target_full_name = obj_ref.raw.strip().strip('"`\'')
                if target_full_name:
                    # logger.debug(f"Found created object: {target_full_name} (Type: {node_type}) in segment type {seg_type}")
                    return target_full_name, node_type
            else:
                 logger.warning(f"Could not extract object reference from {seg_type} segment: {create_segment.raw[:100]}...")


    return None # No known CREATE statement found

# --- Helper to add missing imports ---
# Need to import re for the add_node function
import re
