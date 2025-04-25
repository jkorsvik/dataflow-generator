# mypy: ignore-errors

import os
import logging
from typing import List, Tuple, Dict, Set, Optional, Union
from sqlfluff.core import Linter, SQLLintError
from sqlfluff.core.parser.segments.base import BaseSegment

from src.dataflow_structs import NodeInfo
from src.exceptions import InvalidSQLError

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# --- Helper Function to manage nodes (similar to denodo parser's add_node) ---
def _add_node(
    nodes: Dict[str, NodeInfo],
    full_name: str,
    node_type: str,
    db_objects: Dict[str, Set[str]],  # Simplified: Just track objects per DB
    is_dependency: bool = False,
) -> Optional[str]:
    """Adds or updates node information, prioritizing CTEs. Returns base_name or None."""
    if not full_name:
        return None

    parts = full_name.split(".")
    base_name = parts[-1].strip('"')  # Handle quoted identifiers

    is_new_type_cte = node_type == "cte_view"
    database = None
    if len(parts) > 1 and not is_new_type_cte:
        # Potentially schema.table or db.schema.table - take first part as potential DB/Schema
        database = parts[0].strip('"')
    elif len(parts) == 1 and not is_new_type_cte:
        # Could be a table in the default search path, no explicit DB/Schema
        database = None  # Represent default/unknown schema

    effective_full_name = base_name if is_new_type_cte else full_name

    # Track objects per database/schema (optional, for stats)
    if database and not is_new_type_cte:
        db_objects.setdefault(database, set())
        db_objects[database].add(base_name)

    if base_name not in nodes:
        nodes[base_name] = {
            "type": node_type,
            "database": database or "",  # Store empty string if no DB/Schema found
            "full_name": effective_full_name,
        }
    else:
        existing_info = nodes[base_name]
        current_type = existing_info["type"]
        if current_type == "cte_view":
            pass  # CTE type is final
        elif is_new_type_cte:
            existing_info["type"] = "cte_view"
            existing_info["database"] = ""
            existing_info["full_name"] = base_name
        else:
            # Simple priority: view > table > unknown
            type_priority = {
                "unknown": 0,
                "table": 1,
                "materialized_view": 2,
                "view": 3,
            }
            new_prio = type_priority.get(node_type, 0)
            curr_prio = type_priority.get(current_type, 0)
            if new_prio >= curr_prio:
                existing_info["type"] = node_type
                # Update database only if new one is found and current is empty
                if not existing_info["database"] and database:
                    existing_info["database"] = database
                    if existing_info["full_name"] == base_name:
                        existing_info["full_name"] = effective_full_name

    return base_name


# --- Core Parsing Logic ---


def _find_dependencies(segment: BaseSegment, defined_ctes: Set[str]) -> Set[str]:
    """Recursively finds table/view/CTE references within a segment."""
    dependencies = set()
    # Look for table references specifically
    for sub_segment in segment.recursive_crawl("table_reference"):
        # Sometimes the reference is nested, crawl deeper if needed
        ref_name_segment = next(sub_segment.recursive_crawl("object_reference"), None)
        if ref_name_segment:
            raw_name = ref_name_segment.raw.strip('"')
            # Check if it's one of the CTEs defined in the current scope
            base_name = raw_name.split(".")[-1]
            if base_name not in defined_ctes:
                dependencies.add(
                    raw_name
                )  # Add the full reference (e.g., schema.table)

    # Also consider CTE references directly (might not be inside table_reference)
    for cte_ref_segment in segment.recursive_crawl(
        "common_table_expression_identifier"
    ):
        raw_name = cte_ref_segment.raw.strip('"')
        # We only care about references *to* CTEs defined *elsewhere* or in this scope
        # The logic processing the statement needs to handle linking *within* the scope
        # This function mainly finds external table/view deps or cross-CTE deps if structure allows
        # Let's assume for now this finds references to CTEs defined in the *current* WITH clause
        # This might need refinement based on how sqlfluff structures nested WITHs.
        dependencies.add(raw_name)  # Add CTE name

    return dependencies


def parse_dump(
    file_path: Union[str, os.PathLike],
) -> Tuple[List[Tuple[str, str]], Dict[str, NodeInfo], Dict[str, int]]:
    """Parses a PostgreSQL SQL dump file using sqlfluff to extract structure."""
    logger.info(f"Starting PostgreSQL parsing for: {file_path}")
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
    except (FileNotFoundError, OSError, TypeError):
        if isinstance(file_path, str):
            content = file_path  # Treat as content if not a valid path
        else:
            raise ValueError("Invalid input: must be a file path or a string.")

    if not content:
        raise InvalidSQLError("SQL content is empty.")

    # Initialize results
    edges: List[Tuple[str, str]] = []
    node_types: Dict[str, NodeInfo] = {}
    db_objects: Dict[str, Set[str]] = {}  # Simplified tracking for stats
    edge_set: Set[Tuple[str, str]] = set()  # To avoid duplicate edges

    # Use sqlfluff linter to get the parsed tree
    linter = Linter(dialect="postgres")
    try:
        linted_path = linter.lint_string(content)
        parsed_tree = linted_path.tree
        if not parsed_tree:
            raise InvalidSQLError("SQLFluff could not parse the file.")
    except SQLLintError as e:
        logger.error(f"SQLFluff parsing error: {e}")
        # Depending on severity, you might want to raise or just log
        raise InvalidSQLError(f"SQLFluff parsing failed: {e}") from e
    except Exception as e:  # Catch broader exceptions during linting
        logger.error(f"Unexpected error during SQLFluff linting: {e}")
        raise InvalidSQLError(f"Unexpected SQLFluff error: {e}") from e

    # --- Process statements ---
    statements = parsed_tree.recursive_crawl("statement")
    for stmt in statements:
        defined_ctes: Set[str] = set()
        current_target_name: Optional[str] = None
        current_target_type: Optional[str] = None

        # 1. Handle WITH clauses (CTEs) first
        with_clause = next(stmt.recursive_crawl("with_compound_statement"), None)
        if with_clause:
            for cte_segment in with_clause.recursive_crawl("common_table_expression"):
                cte_name_segment = next(cte_segment.recursive_crawl("identifier"), None)
                if cte_name_segment:
                    cte_name = cte_name_segment.raw.strip('"')
                    defined_ctes.add(cte_name)
                    # Add CTE node immediately
                    _add_node(node_types, cte_name, "cte_view", db_objects)
                    # Find dependencies *within* this CTE body
                    cte_body = cte_segment  # Assuming the body is within the CTE segment itself
                    cte_internal_deps = _find_dependencies(cte_body, defined_ctes)
                    for dep_full_name in cte_internal_deps:
                        # Ensure dependency node exists (could be another CTE or table/view)
                        # Guess type if not already known (might be table/view)
                        dep_base_name = dep_full_name.split(".")[-1].strip('"')
                        dep_type = node_types.get(dep_base_name, {}).get(
                            "type", "unknown"
                        )
                        if dep_type == "unknown":
                            # Basic guess if unknown - could be improved
                            dep_type = (
                                "view" if "view" in dep_base_name.lower() else "table"
                            )

                        # Add the dependency node (might update type if guess is better)
                        dep_node_base = _add_node(
                            node_types,
                            dep_full_name,
                            dep_type,
                            db_objects,
                            is_dependency=True,
                        )
                        if dep_node_base:
                            edge = (dep_node_base, cte_name)
                            if edge not in edge_set and dep_node_base != cte_name:
                                edges.append(edge)
                                edge_set.add(edge)

        # 2. Identify the main object being created (Table, View, MView)
        create_table_segment = next(
            stmt.recursive_crawl("create_table_statement"), None
        )
        create_view_segment = next(stmt.recursive_crawl("create_view_statement"), None)
        create_mview_segment = next(
            stmt.recursive_crawl("create_materialized_view_statement"), None
        )

        target_segment = None
        if create_table_segment:
            current_target_type = "table"
            target_segment = create_table_segment
        elif create_view_segment:
            current_target_type = "view"
            target_segment = create_view_segment
        elif create_mview_segment:
            current_target_type = "materialized_view"
            target_segment = create_mview_segment

        if target_segment and current_target_type:
            # Find the object reference for the created object
            obj_ref = next(
                target_segment.recursive_crawl("object_reference", no_recursive=True),
                None,
            )
            # Sometimes it's nested directly under table_reference or view_reference
            if not obj_ref:
                table_ref = next(
                    target_segment.recursive_crawl(
                        "table_reference", no_recursive=True
                    ),
                    None,
                )
                if table_ref:
                    obj_ref = next(table_ref.recursive_crawl("object_reference"), None)
            if not obj_ref:
                view_ref = next(
                    target_segment.recursive_crawl("view_reference", no_recursive=True),
                    None,
                )
                if view_ref:
                    obj_ref = next(view_ref.recursive_crawl("object_reference"), None)

            if obj_ref:
                target_full_name = obj_ref.raw.strip('"')
                current_target_name = _add_node(
                    node_types, target_full_name, current_target_type, db_objects
                )

                # 3. Find dependencies for the main created object
                if current_target_name:
                    # Search within the definition part (usually after 'AS')
                    definition_segment = (
                        target_segment  # Start search from the create statement itself
                    )
                    main_deps = _find_dependencies(definition_segment, defined_ctes)
                    for dep_full_name in main_deps:
                        dep_base_name = dep_full_name.split(".")[-1].strip('"')
                        dep_type = node_types.get(dep_base_name, {}).get(
                            "type", "unknown"
                        )
                        # If the dependency is a CTE defined above, its type is known
                        if dep_base_name in defined_ctes:
                            dep_type = "cte_view"
                        elif dep_type == "unknown":
                            # Basic guess if unknown
                            dep_type = (
                                "view" if "view" in dep_base_name.lower() else "table"
                            )

                        dep_node_base = _add_node(
                            node_types,
                            dep_full_name,
                            dep_type,
                            db_objects,
                            is_dependency=True,
                        )
                        if dep_node_base:
                            edge = (dep_node_base, current_target_name)
                            if (
                                edge not in edge_set
                                and dep_node_base != current_target_name
                            ):
                                edges.append(edge)
                                edge_set.add(edge)
        # TODO: Handle other statement types like INSERT, UPDATE, DELETE if needed for lineage

    # Calculate database stats (count non-CTE nodes per db/schema)
    database_stats: Dict[str, int] = {}
    for node_info in node_types.values():
        if node_info["type"] != "cte_view" and node_info["database"]:
            db_name = node_info["database"]
            database_stats[db_name] = database_stats.get(db_name, 0) + 1

    logger.info(
        f"PostgreSQL parsing complete. Found {len(node_types)} nodes and {len(edges)} edges."
    )
    return edges, node_types, database_stats


# Example usage (optional, for testing)
if __name__ == "__main__":
    # Create a dummy SQL file for testing
    dummy_sql = """
    -- PostgreSQL database dump example
    CREATE SCHEMA IF NOT EXISTS production;

    CREATE TABLE production.users (
        user_id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE production.orders (
        order_id SERIAL PRIMARY KEY,
        user_id INT REFERENCES production.users(user_id),
        order_date DATE,
        total_amount DECIMAL(10, 2)
    );

    CREATE VIEW production.recent_orders_v AS
    SELECT
        o.order_id,
        u.username,
        o.order_date
    FROM production.orders o
    JOIN production.users u ON o.user_id = u.user_id
    WHERE o.order_date > CURRENT_DATE - INTERVAL '30 days';

    WITH monthly_sales AS (
        SELECT
            date_trunc('month', order_date) AS sale_month,
            sum(total_amount) as monthly_total
        FROM production.orders
        GROUP BY 1
    ),
    -- Another CTE depending on the first
    avg_sales AS (
        SELECT avg(monthly_total) as average_sale FROM monthly_sales
    )
    CREATE MATERIALIZED VIEW production.high_value_users_mv AS
    SELECT u.user_id, u.username
    FROM production.users u
    JOIN production.recent_orders_v rov ON u.user_id = (SELECT user_id FROM production.orders WHERE order_id = rov.order_id) -- Example subquery reference
    JOIN monthly_sales ms ON date_trunc('month', rov.order_date) = ms.sale_month -- Join with CTE
    WHERE rov.order_id IN (SELECT order_id FROM production.orders WHERE total_amount > (SELECT average_sale FROM avg_sales)) -- Reference another CTE
    GROUP BY 1, 2
    HAVING count(rov.order_id) > 5;

    INSERT INTO production.users (username) VALUES ('testuser');
    """
    test_file = "./dummy_postgres_dump.sql"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(dummy_sql)

    try:
        res_edges, res_nodes, res_stats = parse_dump(test_file)
        print("\n--- Edges ---")
        for edge in res_edges:
            print(edge)
        print("\n--- Nodes ---")
        import json

        print(json.dumps(res_nodes, indent=2))
        print("\n--- Stats ---")
        print(res_stats)
    except Exception as e:
        print(f"Error during test run: {e}")
    finally:
        # Clean up the dummy file
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"\nCleaned up {test_file}")
