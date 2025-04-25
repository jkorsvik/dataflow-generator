import json
import os

import networkx as nx
from typing import List, Tuple, Dict, TypedDict, Union, Set, Any, Optional, cast  # noqa: F401

from . import pyvis_mod
from .dataflow_structs import NodeInfo
from .parser_register import guess_database_type, _PARSER_REGISTRY, DatabaseType


def parse_dump(
    file_path: Union[str, os.PathLike],
    database_type: Optional[DatabaseType] = None,
) -> Tuple[List[Tuple[str, str]], Dict[str, NodeInfo], Dict[str, int]]:
    """
    Detect the dump type if not provided, then dispatch to the correct parser.
    """
    if database_type is None:
        database_type = guess_database_type(file_path)
    if database_type not in _PARSER_REGISTRY:
        raise ValueError(f"Unsupported or unrecognized database type: {database_type}")
    parser = _PARSER_REGISTRY[database_type]
    result = parser.parse_dump(file_path)
    if not (isinstance(result, tuple) and len(result) == 3):
        raise TypeError("Parser returned an invalid result. Expected a tuple of (edges, node_types, node_counts).")
    return cast(Tuple[List[Tuple[str, str]], Dict[str, NodeInfo], Dict[str, int]], result)


def draw_complete_data_flow(
    edges, node_types, save_path="", file_name="", draw_edgeless=False, auto_open=False
) -> None:
    print(f"Generating complete data flow{' for ' + file_name if file_name else ''}...")
    pyvis_mod.draw_pyvis_html(
        edges,
        node_types,
        save_path=save_path,
        auto_open=auto_open,
        file_name=file_name,
        draw_edgeless=draw_edgeless,
    )


def draw_focused_data_flow(
    edges,
    node_types,
    focus_nodes,
    save_path="",
    file_name="",
    auto_open=False,
    see_ancestors=True,
    see_descendants=True,
):
    print(f"Generating focused data flow{' for ' + file_name if file_name else ''}...")
    print(f"Focus nodes: {focus_nodes}")
    G = nx.DiGraph()
    G.add_edges_from(edges)
    valid_nodes_set = set(node_types.keys())
    nodes_in_edges = set(u for u, v in edges) | set(v for u, v in edges)
    G.add_nodes_from(nodes_in_edges)
    G.add_nodes_from(valid_nodes_set)
    existing_focus_nodes = [node for node in focus_nodes if node in G]

    if not existing_focus_nodes:
        print(f"Warning: Focus nodes {focus_nodes} not found.")
        return
    if len(existing_focus_nodes) < len(focus_nodes):
        print(
            f"Warning: Missing focus nodes: {set(focus_nodes) - set(existing_focus_nodes)}"
        )

    subgraph_nodes = set(existing_focus_nodes)
    for node in existing_focus_nodes:
        if see_ancestors:
            try:
                subgraph_nodes.update(nx.ancestors(G, node))
            except nx.NetworkXError:
                print(f"Error finding ancestors for '{node}'.")
        if see_descendants:
            try:
                subgraph_nodes.update(nx.descendants(G, node))
            except nx.NetworkXError:
                print(f"Error finding descendants for '{node}'.")

    # Create focused subgraph
    focused_subgraph = G.subgraph(subgraph_nodes).copy()
    if not focused_subgraph.nodes():
        print("Warning: Focused subgraph empty.")
        return

    # Prepare node types for focused view
    subgraph_node_types = {
        node: {
            "type": node_types.get(node, {"type": "unknown"})["type"],
            "database": node_types.get(node, {"database": ""})["database"],
            "full_name": node_types.get(node, {"full_name": node})["full_name"],
        }
        for node in focused_subgraph.nodes()
    }

    # Use the draw_pyvis_html function
    pyvis_mod.draw_pyvis_html(
        list(focused_subgraph.edges()),
        subgraph_node_types,
        save_path=save_path,
        file_name=file_name,
        auto_open=auto_open,
        focus_nodes=existing_focus_nodes,
        is_focused_view=True,
    )
