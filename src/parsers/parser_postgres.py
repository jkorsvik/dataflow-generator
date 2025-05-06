import json
import os
import re
from typing import Dict, List, Tuple, Optional, Union

import sqlglot
from sqlglot import parse, exp

from ..dataflow_structs import NodeInfo, SQL_PATTERNS, InvalidSQLError


def _extract_schema(schema_expr) -> Optional[str]:
    """Convert sqlglot schema expression to string."""
    if isinstance(schema_expr, exp.Identifier):
        return schema_expr.name
    if isinstance(schema_expr, str):
        return schema_expr
    return None


def add_node(
    name: str,
    node_type: str,
    schema: Optional[str],
    definition: Optional[str],
    node_types: Dict[str, NodeInfo],
) -> str:
    """
    Register or update a node in node_types with priority:
      - cte_view highest (never overwritten)
      - view above table
    Returns the base name of the node.
    """
    base = name.split('.')[-1]
    info: NodeInfo = {
        "type": node_type,
        "database": schema or "",
        "full_name": name,
        "definition": definition,
    }
    existing = node_types.get(base)

    # Never overwrite an existing CTE
    if existing and existing["type"] == "cte_view":
        return base

    # Promote to CTE if new node is a CTE
    if existing and node_type == "cte_view":
        node_types[base] = info
        return base

    # Determine priority for view/table
    priority = {"table": 1, "view": 2, "cte_view": 3}
    new_prio = priority.get(node_type, 0)
    curr_prio = priority.get(existing["type"], 0) if existing else 0

    # Overwrite if new node has equal or higher priority
    if not existing or new_prio >= curr_prio:
        node_types[base] = info

    return base


def find_dependencies(
    expression: exp.Expression,
) -> List[Tuple[str, Optional[str]]]:
    """
    Traverse an AST expression to collect referenced tables:
    Returns list of (name, schema).
    """
    deps: List[Tuple[str, Optional[str]]] = []
    for tbl in expression.find_all(exp.Table):
        name = tbl.name
        schema_expr = tbl.args.get("db") or tbl.args.get("catalog")
        schema = _extract_schema(schema_expr)
        if name:
            deps.append((name, schema))
    return deps


def parse_dump(
    file_path: Union[str, os.PathLike],
) -> Tuple[List[Tuple[str, str]], Dict[str, NodeInfo], Dict[str, int]]:
    """
    Parse Postgres SQL script to extract tables, views, CTEs, and dependencies.
    Returns edges, node_types, and schema statistics.
    """
    # Read content
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (FileNotFoundError, OSError, TypeError):
        if isinstance(file_path, str):
            content = file_path
        else:
            raise ValueError("Invalid input: must be a file path or SQL string.")

    # Preprocess: comment out psql meta-commands
    lines = content.splitlines()
    cleaned = []
    skip_copy = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("\\"):
            cleaned.append(f"-- {stripped}")
            continue
        if re.match(r"^\s*ALTER\s+SCHEMA", stripped, re.I):
            cleaned.append(f"-- {stripped}")
            continue
        if re.match(r"^\s*COPY\s+.*\s+FROM\s+STDIN", stripped, re.I):
            skip_copy = True
            cleaned.append(f"-- {stripped}")
            continue
        if skip_copy:
            cleaned.append(f"-- {line}")
            if stripped == "\\." or re.match(r"^\\\.\s*$", stripped):
                skip_copy = False
            continue
        cleaned.append(line)
    content = "\n".join(cleaned)

    # Basic SQL validation
    if not content or not any(re.search(pat, content, re.I) for pat in SQL_PATTERNS):
        raise InvalidSQLError("Invalid SQL: no common keywords found or content empty.")

    node_types: Dict[str, NodeInfo] = {}
    edges: List[Tuple[str, str]] = []

    # Clean unsupported syntax using SQLFluff (auto-comments unparsable)
    try:
        import sqlfluff
        content = sqlfluff.fix(
            content,
            dialect='postgres',
            fix_even_unparsable=True,
        )
    except ImportError:
        pass

    # Parse with Postgres dialect
    statements = parse(content, read="postgres")

    for stmt in statements:
        if not isinstance(stmt, exp.Create):
            continue
        kind = (stmt.args.get("kind") or "TABLE").upper()
        target = stmt.this
        # Extract full name and schema safely
        if isinstance(target, exp.Table):
            full_name = target.sql(dialect="postgres")
            schema = _extract_schema(target.args.get("db") or target.args.get("catalog"))
        else:
            full_name = str(target)
            schema = None
        node_type = "view" if kind == "VIEW" else "table"
        definition_sql = stmt.sql(dialect="postgres")
        target_base = add_node(full_name, node_type, schema, definition_sql, node_types)

        expr = stmt.args.get("expression")
        # Handle CTEs
        if node_type == "view" and isinstance(expr, exp.With):
            with_clause: exp.With = expr  # type: ignore
            for cte in with_clause.expressions:
                cte_name = cte.alias
                cte_def = cte.sql(dialect="postgres")
                add_node(cte_name, "cte_view", None, cte_def, node_types)
                for dep_name, dep_schema in find_dependencies(cte.this):
                    dep_full = f"{dep_schema + '.' if dep_schema else ''}{dep_name}"
                    dep_base = add_node(dep_full, "table", dep_schema, None, node_types)
                    if dep_base != cte_name:
                        edges.append((dep_base, cte_name))
            main_expr = with_clause.this
        else:
            main_expr = expr

        if main_expr:
            for dep_name, dep_schema in find_dependencies(main_expr):
                dep_full = f"{dep_schema + '.' if dep_schema else ''}{dep_name}"
                dep_base = add_node(dep_full, "table", dep_schema, None, node_types)
                if dep_base != target_base:
                    edges.append((dep_base, target_base))

    # Compute schema-level stats
    stats: Dict[str, int] = {}
    for info in node_types.values():
        if info["type"] != "cte_view":
            sch = info["database"] or "public"
            stats[sch] = stats.get(sch, 0) + 1

    # Write JSON outputs
    out_dir = "json_structure"
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "edges.json"), "w", encoding="utf-8") as f:
        json.dump(edges, f, indent=2)
    with open(os.path.join(out_dir, "node_types.json"), "w", encoding="utf-8") as f:
        json.dump(node_types, f, indent=2)

    return edges, node_types, stats