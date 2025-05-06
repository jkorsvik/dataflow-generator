import json
import os
import re
from typing import Dict, List, Tuple, Optional, Union

import sqlglot
from sqlglot import parse, exp

from ..dataflow_structs import NodeInfo, SQL_PATTERNS, InvalidSQLError


def _extract_schema(schema_expr) -> Optional[str]:
    if isinstance(schema_expr, exp.Identifier):
        return schema_expr.name
    if isinstance(schema_expr, str):
        return schema_expr
    return None


def add_node(
    base: str,
    node_type: str,
    schema: Optional[str],
    definition: Optional[str],
    node_types: Dict[str, NodeInfo],
) -> None:
    info: NodeInfo = {
        "type": node_type,
        "database": schema or "",
        "full_name": f"{schema + '.' if schema else ''}{base}",
        "definition": definition,
    }
    existing = node_types.get(base)
    # CTE highest
    if existing and existing["type"] == "cte_view":
        return
    if existing and node_type == "cte_view":
        node_types[base] = info
        return
    # view over table
    prio = {"table":1, "view":2, "cte_view":3}
    if not existing or prio[node_type] >= prio.get(existing["type"],0):
        node_types[base] = info


def find_dependencies(expr: exp.Expression) -> List[Tuple[str, Optional[str]]]:
    deps: List[Tuple[str, Optional[str]]] = []
    for tbl in expr.find_all(exp.Table):
        name = tbl.name
        schema = _extract_schema(tbl.args.get("db") or tbl.args.get("catalog"))
        if name:
            deps.append((name, schema))
    return deps


def parse_dump(
    file_path: Union[str, os.PathLike],
) -> Tuple[List[Tuple[str, str]], Dict[str, NodeInfo], Dict[str, int]]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        if isinstance(file_path, str):
            content = file_path
        else:
            raise ValueError("Invalid input: path or SQL string required.")

    # Comment out meta-commands and COPY FROM STDIN blocks
    lines = content.splitlines()
    cleaned_lines: List[str] = []
    in_copy_block: bool = False

    for line in lines:
        stripped_line = line.strip()

        if in_copy_block:
            cleaned_lines.append(f"--{line}")
            if stripped_line == '\\.' or re.match(r'^\\\.', stripped_line):
                in_copy_block = False
            continue

        if re.match(r'^COPY .* FROM ST(?:DIN)?', stripped_line, re.I):
            cleaned_lines.append(f"--{line}")
            if not stripped_line.endswith('\\.'):
                in_copy_block = True
            continue

        if re.match(r'^CREATE\s+SCHEMA', stripped_line, re.I) or \
           re.match(r'^ALTER\s+SCHEMA', stripped_line, re.I) or \
           stripped_line.startswith('\\connect') or \
           stripped_line.startswith('\\set'):
            cleaned_lines.append(f"--{line}")
            continue

        cleaned_lines.append(line)

    content = "\n".join(cleaned_lines)

    # Validate
    if not content or not any(re.search(p, content, re.I) for p in SQL_PATTERNS):
        raise InvalidSQLError("Invalid SQL.")

    # SQLFluff cleanup
    try:
        import sqlfluff
        content = sqlfluff.fix(content, dialect='postgres', fix_even_unparsable=True)
    except ImportError:
        pass

    stmts = parse(content, read='postgres')
    node_types: Dict[str, NodeInfo] = {}
    edges: List[Tuple[str,str]] = []

    for stmt in stmts:
        if not isinstance(stmt, exp.Create): continue
        # target must be a Table
        target = stmt.this
        if not isinstance(target, exp.Table): continue
        base = target.name
        schema = _extract_schema(target.args.get('db') or target.args.get('catalog'))
        kind = (stmt.args.get('kind') or 'TABLE').upper()
        node_type = 'view' if kind=='VIEW' else 'table'
        definition = stmt.sql(dialect='postgres')
        add_node(base, node_type, schema, definition, node_types)

        expr = stmt.args.get('expression')
        # CTEs
        if isinstance(expr, exp.With):
            for cte in expr.expressions:
                cname=cte.alias
                cdef=cte.sql(dialect='postgres')
                add_node(cname,'cte_view',None,cdef,node_types)
                for dn, ds in find_dependencies(cte.this):
                    add_node(dn,'table',ds,None,node_types)
                    edges.append((dn,cname))
            expr = expr.this
        # main deps
        if expr:
            for dn, ds in find_dependencies(expr):
                add_node(dn,'table',ds,None,node_types)
                edges.append((dn, base))

    # stats
    stats: Dict[str,int] = {}
    for b,info in node_types.items():
        if info['type']=='cte_view': continue
        sch=info['database'] or 'public'
        stats[sch]=stats.get(sch,0)+1

    os.makedirs('json_structure',exist_ok=True)
    json.dump(edges, open('json_structure/edges.json','w'),indent=2)
    json.dump(node_types, open('json_structure/node_types.json','w'),indent=2)

    return edges,node_types,stats
