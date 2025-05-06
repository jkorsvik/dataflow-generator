import json
import os
import re
from typing import List, Tuple, Dict, TypedDict, Union, Set, Any, Optional  # noqa: F401

from ..dataflow_structs import NodeInfo
from ..dataflow_structs import SQL_PATTERNS
from ..exceptions import InvalidSQLError
import sqlparse  # type: ignore[import]



# Global variable declarations with updated type annotations
database_stats: Dict[str, int] = {}
node_types: Dict[str, "NodeInfo"] = {}
edges: List[Tuple[str, str]] = []
# Updated type annotation to support boolean values
db_objects: Dict[str, Dict[str, Dict[str, Union[str, bool]]]] = {}


# Restore find_script_dependencies closer to original, ensure context passing works
def find_script_dependencies(
    vql_script: str,
    node_types: Dict[str, NodeInfo],  # Pass for context
    db_objects: Dict[
        str, Dict[str, Dict[str, Union[str, bool]]]
    ],  # Updated type annotation
) -> List[str]:
    """Finds potential dependencies (tables/views) in FROM/JOIN clauses."""
    dependencies: Set[str] = set()  # noqa: F841
    statement = vql_script  # Process as single block

    comment_pattern = r"(--.*?$|/\*.*?\*/)"
    statement_no_comments = re.sub(
        comment_pattern, "", statement, flags=re.DOTALL | re.MULTILINE | re.IGNORECASE
    )

    # --- Description source extraction (Keep existing logic) ---
    description_pattern = re.compile(
        r"DESCRIPTION\s?=\s?'((?:[^']|'')*)'",
        re.DOTALL | re.MULTILINE | re.IGNORECASE,
    )
    vql_descriptions = re.findall(description_pattern, statement_no_comments)
    desc_sources_found: Set[str] = set()
    for desc in vql_descriptions:
        description_sources_pattern = re.compile(
            r"source>>(.*?)<<source", re.DOTALL | re.MULTILINE | re.IGNORECASE
        )
        desc_sources = [
            source.strip().replace("'", "")
            for source in re.findall(description_sources_pattern, desc)
        ]
        desc_sources_found.update(ds for ds in desc_sources if ds)

    statement_no_descriptions = re.sub(description_pattern, "", statement_no_comments)
    # --- End Description source extraction ---

    normalized_stmt = re.sub(r"\s+", " ", statement_no_descriptions).strip()

    # Use the tried-and-tested comprehensive pattern for table references
    table_pattern = re.compile(
        r"""
        \b(?:FROM(?:\s+FLATTEN)?|JOIN|INTO|IMPLEMENTATION)\s+ # Support FROM FLATTEN
        (?:')?                    # Optional opening quote
        (?!\s*SELECT\b|\s*WITH\b|\s*VALUES\b|\s*LATERAL\b|\s*UNNEST\b|\s*TABLE\b|\() # Negative lookahead
        \s*
        ((?:[a-zA-Z0-9_]+\.)?     # Optional database prefix
         [a-zA-Z0-9_]+            # Table/view name
        )
        (?:')?                    # Optional closing quote
        # Removed alias capture as it might interfere, rely on context post-match
        # (?:\s+(?:AS\s+)? [a-zA-Z0-9_]+)?
        \b # Use word boundary
        """,
        re.VERBOSE | re.IGNORECASE,
    )

    found_tables = set()
    for match in table_pattern.finditer(normalized_stmt):
        table_ref = match.group(1).strip()
        # Original Skip SQL keywords check - reinstate if needed, be careful
        # if table_ref.upper() not in ('SELECT', 'WITH', 'VALUES', 'LATERAL', 'UNNEST'):
        if table_ref:  # Basic check for non-empty match
            found_tables.add(table_ref)

    # --- Resolve Dependencies ---
    final_dependencies = set()

    def resolve_database(base_name: str) -> str:
        """Find the correct database for an object."""
        # Prioritize node_types if available and not a CTE
        if node_types and base_name in node_types:
            if node_types[base_name].get("type") != "cte_view":  # Check type if exists
                return node_types[base_name].get("database", "")
            else:
                return ""  # CTEs have no DB

        # Fallback to db_objects context
        if db_objects:
            matching_dbs = [
                db
                for db, objs in db_objects.items()
                if base_name in objs and not objs[base_name].get("is_dependency", False)
            ]
            if matching_dbs:
                return matching_dbs[0]
            matching_deps = [db for db, objs in db_objects.items() if base_name in objs]
            if matching_deps:
                return matching_deps[0]
        return ""

    for table_ref in found_tables:
        parts = table_ref.split(".")
        base_name = parts[-1]
        if len(parts) > 1:
            final_dependencies.add(table_ref)
        else:
            db = resolve_database(base_name)
            full_name = f"{db}.{base_name}" if db else base_name
            final_dependencies.add(full_name)

    # SET IMPLEMENTATION dependencies
    imp_pattern = re.compile(
        r"SET\s+IMPLEMENTATION\s+([a-zA-Z0-9_\.]+)", re.IGNORECASE | re.MULTILINE
    )
    final_dependencies.update(
        m.strip() for m in imp_pattern.findall(statement_no_descriptions) if m.strip()
    )

    final_dependencies.update(desc_sources_found)  # Add description sources

    return list(dep for dep in final_dependencies if dep)


def add_node(full_name: str, node_type: str, is_dependency: bool = False, definition: Optional[str] = None) -> str:
    """Adds or updates node information, ensuring CTE type priority."""
    if not full_name:
        return ""
    parts = full_name.split(".")
    base_name = parts[-1]

    # Determine database and effective name based on type
    is_new_type_cte = node_type == "cte_view"
    database = "" if is_new_type_cte else (parts[0] if len(parts) > 1 else "")
    effective_full_name = base_name if is_new_type_cte else full_name

    # Update db_objects (Only track non-CTE objects with a database)
    if database and not is_new_type_cte:
        db_objects.setdefault(database, {})
        db_objects[database].setdefault(base_name, {})
        if (
            not db_objects[database][base_name].get("is_dependency", True)
            or not is_dependency
        ):
            db_objects[database][base_name].update(
                {
                    "full_name": effective_full_name,
                    "type": node_type,
                    "is_dependency": is_dependency,
                }
            )

    # Add/update node_types
    if base_name not in node_types:
        # New node - Add it directly
        # Initialize with all required keys for NodeInfo, definition can be None
        node_info_dict: NodeInfo = {
            "type": node_type,
            "database": database,
            "full_name": effective_full_name,
            "definition": None,
        }
        if definition and not is_dependency:
            node_info_dict["definition"] = definition
        node_types[base_name] = node_info_dict
    else:
        # Existing node - Check before updating
        existing_info = node_types[base_name]
        current_type = existing_info["type"]

        # *** RULE 1: If the existing type is already 'cte_view', NEVER change it. ***
        if current_type == "cte_view":
            pass  # Do nothing, CTE type is final
        # *** RULE 2: If the new type is 'cte_view', ALWAYS update to it. ***
        elif is_new_type_cte:
            existing_info["type"] = "cte_view"
            existing_info["database"] = ""  # Reset database
            existing_info["full_name"] = base_name  # Reset full name
        # *** RULE 3: Neither current nor new is CTE, apply view/table priority. ***
        else:
            type_priority = {"unknown": 0, "table": 1, "view": 2}
            new_prio = type_priority.get(node_type, 0)
            curr_prio = type_priority.get(current_type, 0)

            # Update only if new type is same or better priority
            if new_prio >= curr_prio:
                existing_info["type"] = node_type
                # Update database only if we found one and didn't have one before
                if not existing_info["database"] and database:
                    existing_info["database"] = database
                    if (
                        existing_info["full_name"] == base_name
                    ):  # Update full_name if it was just base
                        existing_info["full_name"] = effective_full_name
        # Only set definition if not a dependency and not already set
        if definition and not is_dependency and not existing_info.get("definition"):
            existing_info["definition"] = definition

    return base_name


def guess_type(name: str) -> str:
    """Guesses node type based on name conventions or content."""
    # Check known types FIRST
    if name in node_types:
        return node_types[name]["type"]
    # Conventions
    if name.startswith(("v_", "iv_", "rv_", "bv_", "wv_", "u_")):
        return "view"
    if name.startswith(("t_", "it_", "ft_", "i_")):
        return "table"
    # Fallback
    return "view" if "view" in name.lower() else "table"


# Fix for lines near 294 - Adding proper None check before accessing .group()
def parse_dump(
    file_path: Union[str, os.PathLike],
) -> Tuple[List[Tuple[str, str]], Dict[str, NodeInfo], Dict[str, int]]:
    """
    Parses a SQL/VQL input to extract object definitions, dependencies,
    and associated database statistics from the provided content.

    This function processes SQL/VQL content from either a file (specified by a file path)
    or directly from a string input. It identifies object definitions such as tables, views,
    and Common Table Expressions (CTEs), and then extracts dependency relationships between these objects.
    The function also builds statistics for objects associated with various databases.

    Parameters:
        file_path (Union[str, os.PathLike]):
            Either a file path pointing to a SQL/VQL file, or a string containing SQL/VQL content.
            The function attempts to open and read the file. In case of file I/O errors,
            it treats the provided file_path as direct SQL/VQL content, unless it is an invalid type,
            in which case a ValueError is raised.

    Returns:
        Tuple[List[Tuple[str, str]], Dict[str, NodeInfo], Dict[str, int]]:
            - edges (List[Tuple[str, str]]): A list of tuples representing dependencies between objects.
              Each tuple is in the form (source_node, target_node) indicating that the source_node is used
              by the target_node.
            - node_types (Dict[str, NodeInfo]): A dictionary mapping a node’s base name to its information.
              The NodeInfo dictionary contains:
                  • "type": The type of object (e.g., "table", "view", "cte_view"),
                  • "database": The associated database name (if applicable),
                  • "full_name": The fully qualified name, adjusted based on type and context.
            - database_stats (Dict[str, int]): A dictionary counting the number of non-CTE nodes per database.
              Only nodes associated with a specific database (and not marked as CTE) are included.

    Raises:
        InvalidSQLError:
            If the SQL/VQL content is empty or does not contain expected SQL keywords as defined by the SQL_PATTERNS.
        ValueError:
            If the provided file_path is neither a valid file path nor a string containing SQL/VQL content.

    Detailed Description:
        1. The function attempts to read the input content from a file. On failure, it checks if the input is a string.
        2. It validates the content by ensuring that it is non-empty and contains common SQL keywords; if not, an error is raised.
        3. The content is split into individual SQL statements which are then cleaned of comments.
        4. For each statement, the function searches for CREATE statements related to views or tables.
           It extracts the target object's full name and determines its type.
        5. The function processes the definition part following the "AS" keyword or within a DATA_LOAD_QUERY,
           extracting any embedded Common Table Expressions (CTEs) by balancing parentheses.
        6. CTEs are given priority; their nodes are registered before processing the main query such that dependencies
           inside CTE bodies are linked appropriately.
        7. Dependencies within both CTE bodies and the main query are identified via helper routines (e.g., find_script_dependencies).
           Edges representing dependency relationships are created and stored.
        8. Additional dependencies may be extracted from object descriptions if provided via a DESCRIPTION field.
        9. Finally, the function computes database-specific statistics by counting non-CTE nodes per database,
           sorts the node information, and returns the dependency edges, node definitions, and statistics.

    Note:
        This function uses helper functions such as add_node and guess_type to manage node registration and determine
        object types based on naming conventions or context. It also leverages regular expressions extensively for parsing.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
    except (FileNotFoundError, OSError, TypeError):
        if isinstance(file_path, str):
            content = file_path
        else:
            raise ValueError("Invalid input: must be a file path or a string.")

    if not content or not any(
        re.search(pattern, content, re.I) for pattern in SQL_PATTERNS
    ):
        raise InvalidSQLError(
            "Invalid SQL/VQL: No common SQL keywords found or content empty."
        )

    # Reset globals for each parse call if necessary (or manage scope differently)
    # These might be better as instance variables if part of a class, or passed around more explicitly
    global database_stats, node_types, edges, db_objects
    database_stats = {}
    node_types = {}
    edges = []
    db_objects = {}

    raw_statements = [
        s.strip()
        for s in re.split(r";(?=(?:[^']*'[^']*')*[^']*$)", content)
        if s.strip()
    ]

    for raw_stmt in raw_statements:
        if not re.match(r"^\s*CREATE", raw_stmt, re.IGNORECASE):
            continue

        comment_pattern = r"(--.*?$|/\*.*?\*/|#.*?$)"
        clean_stmt = re.sub(
            comment_pattern,
            "",
            raw_stmt,
            flags=re.DOTALL | re.MULTILINE | re.IGNORECASE,
        ).strip()
        if not clean_stmt:
            continue

        view_pattern = re.compile(
            r"CREATE(?: OR REPLACE)?(?:\s+INTERFACE)?\s+VIEW\s+([a-zA-Z0-9_\.]+)",
            re.IGNORECASE | re.DOTALL,
        )
        table_pattern = re.compile(
            r"CREATE(?: OR REPLACE)?(?:\s+\w+)?\s+TABLE\s+([a-zA-Z0-9_\.]+)",
            re.IGNORECASE | re.DOTALL,
        )
        view_match = view_pattern.search(clean_stmt)
        table_match = table_pattern.search(clean_stmt)

        if not (view_match or table_match):
            continue

        # Fix for line 294 - Add proper null check
        target_full_name = ""
        if view_match:
            target_full_name = view_match.group(1)
            target_type = "view"
        elif table_match:
            target_full_name = table_match.group(1)
            target_type = "table"
        else:
            continue

        target_base_name = add_node(target_full_name, target_type, is_dependency=False, definition=clean_stmt)
        if not target_base_name:
            continue

        # Always check for SET IMPLEMENTATION for any view
        if target_type == "view":
            imp_pattern = re.compile(
                r"SET\s+IMPLEMENTATION\s+([a-zA-Z0-9_\.]+)", re.IGNORECASE | re.MULTILINE
            )
            imp_match = imp_pattern.search(clean_stmt)
            if imp_match:
                implementation_name = imp_match.group(1).strip()
                if implementation_name:
                    actual_dep_base = add_node(
                        implementation_name, guess_type(implementation_name), is_dependency=True
                    )
                    if actual_dep_base:
                        edge = (actual_dep_base, target_base_name)
                        if edge not in edges and actual_dep_base != target_base_name:
                            edges.append(edge)

        # --- Extract Definition Part ---
        definition_part = None
        as_match = re.search(r"\bAS\b", clean_stmt, re.IGNORECASE)
        if as_match:
            definition_part = clean_stmt[as_match.end() :].strip()

            # Pre-process Denodo-specific prefixes like "SQL UNION ALL"
            definition_part = re.sub(
                r'\bSQL\s+(SELECT|FROM|WHERE|JOIN|UNION|ALL|GROUP|ORDER|BY|HAVING|AS)\b',
                r'\1',
                definition_part,
                flags=re.IGNORECASE,
            )
        elif target_type == "table":
            query_pattern = re.compile(
                r"DATA_LOAD_QUERY\s?=\s?'((?:[^']|'')*)'",
                re.IGNORECASE | re.MULTILINE | re.DOTALL,
            )
            load_query_match = query_pattern.search(clean_stmt)
            if load_query_match:
                definition_part = load_query_match.group(1).replace("''", "'")
        if not definition_part:
            continue
        # --- End Extract Definition Part ---

        # === START: Focused CTE Handling ===
        ctes_info = {}  # Dict {cte_name: cte_body}
        main_query_part = definition_part  # Default: assume no CTEs
        defined_cte_names = set()
        last_cte_end = 0  # Track end of CTE block

        # Robust CTE parsing using parenthesis balancing
        with_match = re.match(r"\s*WITH\b", definition_part, re.IGNORECASE)
        if with_match:
            current_pos = with_match.end()
            while current_pos < len(definition_part):
                # Find the next 'cte_name AS (' - start search from current_pos
                cte_header_match = re.search(
                    r"([a-zA-Z0-9_]+)\s+AS\s*\(",
                    definition_part[current_pos:],
                    re.IGNORECASE,
                )
                if not cte_header_match:
                    break  # No more CTEs

                cte_name = cte_header_match.group(1)
                # Calculate absolute index for parenthesis start
                paren_start_index = current_pos + cte_header_match.end()
                open_paren_count = 1
                cte_body_end = -1

                # Find matching closing parenthesis for this CTE body
                for i in range(paren_start_index, len(definition_part)):
                    char = definition_part[i]
                    if char == "(":
                        open_paren_count += 1
                    elif char == ")":
                        open_paren_count -= 1
                        if open_paren_count == 0:
                            cte_body_end = i
                            break
                else:
                    print(
                        f"Warning: Could not find matching ')' for CTE '{cte_name}' in statement for '{target_base_name}'."
                    )
                    break  # Stop processing CTEs

                cte_body = definition_part[paren_start_index:cte_body_end].strip()
                ctes_info[cte_name] = cte_body
                defined_cte_names.add(cte_name)

                # Find next relevant position (comma or main query start)
                search_after_cte_body_pos = cte_body_end + 1
                next_marker_match = re.search(
                    r"\s*,|\s*\bSELECT\b|\s*\bINSERT\b|\s*\bUPDATE\b|\s*\bDELETE\b",
                    definition_part[search_after_cte_body_pos:],
                    re.IGNORECASE | re.DOTALL,
                )

                if next_marker_match and next_marker_match.group().strip() == ",":
                    # Move current_pos past the comma
                    current_pos = search_after_cte_body_pos + next_marker_match.end()
                else:
                    # Assume end of CTE block, main query starts after this CTE's body
                    last_cte_end = search_after_cte_body_pos
                    break  # Exit CTE finding loop

            # Determine main_query_part based on parsing results
            if last_cte_end > 0:
                main_query_part = definition_part[last_cte_end:].strip()
            # Handle cases where WITH exists but parsing didn't find CTEs or end properly
            elif with_match and not defined_cte_names:
                main_query_part = definition_part[with_match.end() :].strip()
            elif (
                with_match and last_cte_end == 0
            ):  # Parsing finished but didn't hit SELECT etc.
                # This might mean the query ONLY contained CTEs? Unlikely but possible.
                # Or the logic to find the end of the last CTE needs refinement.
                # For now, assume main query starts after where we stopped searching.
                main_query_part = definition_part[current_pos:].strip()

        # 1. Add CTE nodes first with the correct type
        for cte_name in defined_cte_names:
            # Call add_node with 'cte_view'. The new logic ensures this type is prioritized.
            add_node(cte_name, "cte_view")

        # 2. Process dependencies *inside* each CTE body
        for cte_name, cte_body in ctes_info.items():
            # Pass the GLOBAL node_types and db_objects for context
            cte_deps_full = find_script_dependencies(cte_body, node_types, db_objects)
            for dep_full_name in cte_deps_full:
                dep_base_name = dep_full_name.split(".")[-1]
                is_dep_a_cte = dep_base_name in defined_cte_names
                # Get type using guess_type AFTER potentially adding the node
                # Call add_node first to ensure the dependency node exists
                actual_dep_base = add_node(
                    dep_full_name,
                    guess_type(dep_base_name) if not is_dep_a_cte else "cte_view",
                    is_dependency=True,
                )
                if not actual_dep_base:
                    continue

                # Create edge: dependency -> current CTE
                edge = (actual_dep_base, cte_name)
                if edge not in edges and actual_dep_base != cte_name:
                    edges.append(edge)

        # 3. Process dependencies in the main query part
        if main_query_part:
            # Pass the GLOBAL node_types and db_objects for context
            main_deps_full = find_script_dependencies(
                main_query_part, node_types, db_objects
            )
            for dep_full_name in main_deps_full:
                dep_base_name = dep_full_name.split(".")[-1]
                is_dep_a_cte = dep_base_name in defined_cte_names

                # If dependency is a CTE, source is just the name.
                # If not, ensure the node exists and get its base name.
                if is_dep_a_cte:
                    edge_source_base_name = dep_base_name  # Already added as cte_view
                else:
                    # Ensure the base table/view dependency node exists
                    edge_source_base_name = add_node(
                        dep_full_name, guess_type(dep_base_name), is_dependency=True
                    )

                if not edge_source_base_name:
                    continue

                # Create edge: dependency (or CTE) -> main target
                edge = (edge_source_base_name, target_base_name)
                if edge not in edges and edge_source_base_name != target_base_name:
                    edges.append(edge)

        # === END: Focused CTE Handling ===

        # --- Process Description Sources (Remains the same) ---
        description_pattern = re.compile(
            r"DESCRIPTION\s?=\s?'((?:[^']|'')*)'",
            re.DOTALL | re.MULTILINE | re.IGNORECASE,
        )
        # ... (rest of description source logic remains unchanged) ...
        descriptions = re.findall(description_pattern, clean_stmt)
        for desc in descriptions:
            description_sources_pattern = re.compile(
                r"source>>(.*?)<<source", re.DOTALL | re.MULTILINE | re.IGNORECASE
            )
            desc_sources = [
                s.strip().replace("'", "")
                for s in re.findall(description_sources_pattern, desc)
            ]
            for source_full in desc_sources:
                if source_full:
                    dep_base = source_full.split(".")[-1]
                    if dep_base not in defined_cte_names:  # Check against CTEs
                        actual_dep_base = add_node(
                            source_full, guess_type(dep_base), is_dependency=True
                        )
                        if actual_dep_base:
                            edge = (actual_dep_base, target_base_name)
                            if (
                                edge not in edges
                                and actual_dep_base != target_base_name
                            ):
                                edges.append(edge)

    # --- Finalize and Calculate Stats ---
    # Use the final GLOBAL node_types to calculate stats
    final_database_stats: Dict[str, int] = {}
    for node_name, node_info in node_types.items():
        db = node_info.get("database")
        if db and node_info.get("type") != "cte_view":
            final_database_stats[db] = final_database_stats.get(db, 0) + 1

    # Ensure json_structure directory exists before writing files
    json_dir = "json_structure"
    if not os.path.exists(json_dir):
        os.makedirs(json_dir)
    # Write edges and nodes to json dump
    with open("json_structure/edges.json", "w", encoding="utf-8") as f:
        json.dump(edges, f, indent=4)
    with open("json_structure/node_types.json", "w", encoding="utf-8") as f:
        json.dump(dict(sorted(node_types.items())), f, indent=4)

    # Return the final GLOBAL edges and sorted node_types
    return edges, dict(sorted(node_types.items())), final_database_stats
