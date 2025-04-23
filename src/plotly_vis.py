# pragma: no cover
# type: ignore
# WARNING: This file is deprecated and should be excluded from coverage reports.


import os
import re
import networkx as nx
from typing import List, Tuple, Dict, Optional  # Added Optional
from pyvis.network import Network
import json
import textwrap
from pathlib import Path
import plotly.graph_objects as go  # Import Plotly
import math  # For ceiling function

SCALING_CONSTANT: float = 2


def calculate_dag_layout(
    graph: nx.DiGraph,
    node_types: Dict[str, Dict[str, str]],
    horizontal_spacing=20.0,  # Increased from 2.0 to create wider layout
    vertical_spacing=4,    # Decreased from 1.0 to compact vertical layout
) -> Dict[str, Tuple[float, float]]:
    """
    Calculates node positions for a DAG layout going left-to-right.

    Args:
        graph: The NetworkX DiGraph.
        node_types: Dictionary mapping node names to their types ('table', 'view', etc.)
        horizontal_spacing: Base distance between layers.
        vertical_spacing: Base distance between nodes within a layer.

    Returns:
        A dictionary mapping node names to (x, y) positions.
    """
    pos = {}
    layers = {}
    source_nodes = [n for n, d in graph.in_degree() if d == 0]

    # Handle graphs with cycles or no clear sources
    if not source_nodes:
        print(
            "Warning: No source nodes found or graph might have cycles. Attempting topological sort for layering."
        )
        try:
            # Topological sort works on DAGs. If it fails, the graph has a cycle.
            for i, layer_nodes in enumerate(nx.topological_sort(graph)):
                # Can't directly use layers from topological sort as it's one node at a time.
                # We need a fallback layout in case of cycles.
                print(
                    "Falling back to spring layout due to cycles or complex structure."
                )
                # Adjust k parameter for wider layout in spring layout
                return nx.spring_layout(
                    graph,
                    k=1.8 / math.sqrt(len(graph.nodes()))
                    if len(graph.nodes()) > 0
                    else 1,
                    iterations=75,
                    seed=42,
                )
        except nx.NetworkXUnfeasible:
            print(
                "Error: Graph contains cycles, cannot use topological sort or simple layering. Falling back to spring layout."
            )
            # Adjust k parameter for wider layout in spring layout
            return nx.spring_layout(
                graph,
                k=1.8 / math.sqrt(len(graph.nodes())) if len(graph.nodes()) > 0 else 1,
                iterations=75,
                seed=42,
            )

    # Calculate layers based on longest path from any source node
    max_layer = 0
    node_to_layer = {}
    for node in nx.topological_sort(graph):  # Process in topological order
        current_max_layer = -1
        if node in source_nodes:
            current_max_layer = 0
        else:
            for pred in graph.predecessors(node):
                if pred in node_to_layer:
                    current_max_layer = max(current_max_layer, node_to_layer[pred])
            current_max_layer += 1  # Layer is one more than max predecessor layer

        node_to_layer[node] = current_max_layer
        layers.setdefault(current_max_layer, []).append(node)
        max_layer = max(max_layer, current_max_layer)

    print(f"Calculated {max_layer + 1} layers.")

    # Assign positions
    # Sort nodes within each layer alphabetically for consistent initial placement
    for layer in layers:
        layers[layer].sort()

    max_nodes_in_layer = max(len(nodes) for nodes in layers.values()) if layers else 1

    for layer, nodes in layers.items():
        num_nodes_in_layer = len(nodes)
        # Calculate vertical extent needed for this layer
        layer_height = (num_nodes_in_layer - 1) * vertical_spacing
        y_start = -layer_height / 2.0  # Center the layer vertically

        for i, node in enumerate(nodes):
            x = layer * horizontal_spacing
            y = y_start + i * vertical_spacing
            pos[node] = (x, y)

    # Optional: Add post-processing step here to adjust Y positions
    # based on predecessors (barycenter) for potentially fewer crossings,
    # but this adds complexity. Sticking to simple vertical distribution for now.

    print("DAG layout calculated.")
    return pos


def create_plotly_figure(
    graph: nx.DiGraph,
    pos: Dict[str, Tuple[float, float]],
    node_types: Dict[str, Dict[str, str]],
    fig_width: int = 4500,
    fig_height: int = 1600,
    default_node_size: int = 15,  # Smaller default size for Plotly
    scaling_factor_node: int = 25,  # Reduced scaling factor
    focus_nodes: List[str] = [],
    alternate_text: bool = True,
) -> go.Figure:
    """
    Creates Plotly figure for the given graph. Adjusted for DAG layout.
    """
    if not pos:
        print("Warning: Empty position dictionary provided to create_plotly_figure.")
        return go.Figure()

    # No Y-axis flipping needed for this layout
    transformed_pos = pos

    missing_pos = [n for n in graph.nodes() if n not in transformed_pos]
    if missing_pos:
        print(
            f"Warning: Nodes missing positions: {missing_pos}."
        )  # Should not happen with DAG layout

    if not transformed_pos:
        print("Warning: No node positions available for Plotly figure.")
        return go.Figure()

    x_values, y_values = zip(*transformed_pos.values())
    x_min, x_max = min(x_values), max(x_values)
    y_min, y_max = min(y_values), max(y_values)

    # Adjust padding based on spread
    x_range_val = x_max - x_min if x_max > x_min else 1
    y_range_val = y_max - y_min if y_max > y_min else 1
    x_padding = x_range_val * 0.15  # Reduced horizontal padding for wider look
    y_padding = y_range_val * 0.1   # Increased vertical padding slightly
    x_range_plot = [
        x_min - x_padding - 0.5,
        x_max + x_padding + 0.5,
    ]  # Add some fixed padding too
    y_range_plot = [y_min - y_padding - 0.5, y_max + y_padding + 0.5]

    edge_trace = []
    for edge in graph.edges():
        if edge[0] in transformed_pos and edge[1] in transformed_pos:
            x0, y0 = transformed_pos[edge[0]]
            x1, y1 = transformed_pos[edge[1]]
            edge_trace.append(
                go.Scatter(
                    x=[x0, x1, None],
                    y=[y0, y1, None],
                    line=dict(
                        width=0.5, color="rgba(100,100,100,0.5)"
                    ),  # Thinner, lighter edges
                    hoverinfo="none",
                    mode="lines",
                    showlegend=False,
                )
            )

    node_x, node_y, node_text, node_color, node_size_list = [], [], [], [], []
    node_border_color, node_border_width = [], []
    label_x, label_y, label_text, label_position = [], [], [], []
    label_font_color, label_font_size = [], []

    max_out_degree = 1
    if graph.nodes():
        out_degrees = {node: graph.out_degree(node) for node in graph.nodes()}
        if out_degrees:
            max_out_degree = max(out_degrees.values())

    # Group nodes by X coordinate (layer) for text alternation
    x_levels = {}
    for node, (x, y) in transformed_pos.items():
        rounded_x = round(x, 3)
        x_levels.setdefault(rounded_x, []).append((node, y))

    for x_approx, nodes_at_level in x_levels.items():
        nodes_at_level.sort(key=lambda item: item[1])  # Sort by Y within layer
        for i, (node, y_pos) in enumerate(nodes_at_level):
            if node not in transformed_pos:
                continue

            x, y = transformed_pos[node]
            node_info = node_types.get(node, {"type": "unknown", "database": "", "full_name": node})
            node_type = node_info["type"]
            node_out_degree = graph.out_degree(node)
            # More subtle size scaling
            node_size = default_node_size + (
                scaling_factor_node * node_out_degree / max(1, max_out_degree)
            )

            node_x.append(x)
            node_y.append(y)
            node_text.append(f"Name: {node_info['full_name']}<br>Type: {node_type}<br>Database: {node_info['database']}")
            node_color.append(
                "#59a14f"  # Green for table
                if node_type == "table"
                else "#4e79a7"  # Blue for view
                if node_type == "view"
                else "#ed7be7"  # Purple for datamarket
                if node_type == "datamarket"
                else "#f28e2c"  # Orange for other
                if node_type == "other"
                else "#e15759"  # Red for unknown
            )
            node_size_list.append(node_size)
            node_border_color.append("red" if node in focus_nodes else "rgba(0,0,0,0)")
            node_border_width.append(
                2 if node in focus_nodes else 0
            )  # Thinner highlight border

            label_x.append(x)
            label_y.append(y)
            label_text.append(node)
            # Text position logic - modified to favor horizontal positioning for wide ratio
            # For leftmost layer, always position text on right side
            if x_approx == min(x_levels.keys()):
                text_pos = "middle right" 
            # For rightmost layer, always position text on left side
            elif x_approx == max(x_levels.keys()):
                text_pos = "middle left"
            # For middle layers, alternate based on node index
            else:
                text_pos = "middle right" if i % 2 == 0 else "middle left"
                
            label_position.append(text_pos)
            label_font_color.append("red" if node in focus_nodes else "black")
            # Further reduce font size based on total nodes
            label_font_size.append(max(8, 16 - 0.03 * len(list(graph.nodes()))))

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers",
        hoverinfo="text",
        text=node_text,
        marker=dict(
            size=node_size_list,
            color=node_color,
            line=dict(width=node_border_width, color=node_border_color),
        ),
        showlegend=False,
    )

    label_trace = go.Scatter(
        x=label_x,
        y=label_y,
        mode="text",
        text=label_text,
        textposition=label_position,
        textfont=dict(color=label_font_color, size=label_font_size),
        hoverinfo="none",
        showlegend=False,
    )

    legend_trace = [
        go.Scatter(
            x=[None],
            y=[None],
            mode="markers",
            marker=dict(size=10, color="green"),
                name="Table",
                legendgroup="1",
            ),
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=10, color="#4e79a7"),
                name="View",
                legendgroup="2",
            ),
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=10, color="#ed7be7"),
                name="Data Market",
                legendgroup="3",
            ),
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=10, color="#f28e2c"),
                name="Other DB",
                legendgroup="4",
            ),
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=10, color="#e15759"),
                name="Unknown",
                legendgroup="5",
            ),
    ]

    # Arrows - place near the target node
    annotations = []
    for edge in graph.edges():
        if edge[0] in transformed_pos and edge[1] in transformed_pos:
            x0, y0 = transformed_pos[edge[0]]
            x1, y1 = transformed_pos[edge[1]]
            # Vector from source to target
            vec_x, vec_y = x1 - x0, y1 - y0
            vec_len = math.sqrt(vec_x**2 + vec_y**2)
            if vec_len == 0:
                continue  # Avoid division by zero for self-loops

            # Normalized vector
            norm_x, norm_y = vec_x / vec_len, vec_y / vec_len
            # Offset back from target node (adjust offset as needed)
            offset = 0.15  # Small offset based on plot scale
            arrow_tip_x = x1 - norm_x * offset
            arrow_tip_y = y1 - norm_y * offset

            annotations.append(
                dict(
                    ax=x0,
                    ay=y0,
                    axref="x",
                    ayref="y",
                    x=arrow_tip_x,
                    y=arrow_tip_y,
                    xref="x",
                    yref="y",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1.2,
                    arrowwidth=0.5,  # Smaller arrows
                    arrowcolor="rgba(100,100,100,0.6)",
                )
            )

    fig = go.Figure(
        data=[node_trace, label_trace] + edge_trace + legend_trace,
        layout=go.Layout(
            showlegend=True,
            hovermode="closest",
            margin=dict(b=10, l=10, r=10, t=10),  # Minimal margin
            xaxis=dict(
                showgrid=False,
                zeroline=False,
                showticklabels=False,
                range=x_range_plot,
                fixedrange=False,
            ),
            yaxis=dict(
                showgrid=False,
                zeroline=False,
                showticklabels=False,
                range=y_range_plot,
                fixedrange=False,
                scaleanchor="x",
                scaleratio=1,
            ),  # Try to keep aspect ratio
            annotations=annotations,
            width=fig_width,
            height=fig_height,
            legend=dict(
                x=0.01,
                y=0.99,
                traceorder="normal",
                font=dict(size=10),
                bgcolor="rgba(255,255,255,0.7)",
                borderwidth=1,
            ),
            plot_bgcolor="white",
        ),
    )

    return fig


# --- generate_plotly_png function (Modified) ---
def generate_plotly_png(
    edges: List[Tuple[str, str]],
    node_types: Dict[str, Dict[str, str]],
    save_path: str = "",
    file_name: str = "",
    draw_edgeless: bool = False,
    fig_width: int = 6000,  # Increased default width
    fig_height: int = 3000,  # Increased default height
    focus_nodes: List[str] = [],
    png_scale: int = 2,  # Scale factor for write_image
) -> None:
    """
    Generates a static PNG using Plotly and a custom DAG layout.
    """
    print(f"Generating Plotly PNG using custom DAG layout...")
    G = nx.DiGraph()
    G.add_edges_from(edges)
    valid_nodes = list(node_types.keys())
    if draw_edgeless:
        G.add_nodes_from(valid_nodes)
    else:
        nodes_in_edges = set(u for u, v in edges) | set(v for u, v in edges)
        nodes_to_draw = nodes_in_edges.union(set(valid_nodes))
        if not nodes_to_draw:
            print("Warning: No nodes to draw for Plotly PNG.")
            return
        G = G.subgraph(nodes_to_draw).copy()

    # Ensure all nodes in the final graph have a type
    final_node_types = {
        node: node_types.get(node, {
            "type": "unknown",
            "database": "",
            "full_name": node
        }) 
        for node in G.nodes()
    }
    if not G.nodes():
        print("Warning: Graph is empty for Plotly PNG.")
        return

    # Calculate positions using the custom DAG layout
    pos = calculate_dag_layout(G, final_node_types)
    if not pos:  # Check if layout failed (e.g., cycle fallback failed)
        print("Error: Failed to calculate node positions. Skipping Plotly PNG.")
        return

    # Estimate appropriate figure size based on layout spread
    if len(pos) > 1:
        x_coords, y_coords = zip(*pos.values())
        x_span = max(x_coords) - min(x_coords)
        y_span = max(y_coords) - min(y_coords)
        
        # Define minimum aspect ratio (16:9)
        min_aspect_ratio = 16/9
        
        # Calculate base dimensions
        base_width = int(min(max(4500, x_span * 600 + 1000), 7680))
        base_height = int(min(max(1920, y_span * 300 + 800), 4320))
        
        # Ensure aspect ratio is at least 16:9 or wider
        current_ratio = base_width / base_height
        if current_ratio < min_aspect_ratio:
            # If too narrow, increase width to match 16:9 ratio
            base_width = int(base_height * min_aspect_ratio)
        
        fig_width = base_width
        fig_height = base_height
        print(f"Estimated Plotly figure size: {fig_width}x{fig_height} (ratio: {fig_width/fig_height:.2f})")
    else:  # Use default if only one node or calculation failed
        # Ensure default sizes maintain wide ratio
        min_aspect_ratio = 16/9
        if fig_width / fig_height < min_aspect_ratio:
            fig_width = int(fig_height * min_aspect_ratio)
        print(f"Using default Plotly figure size: {fig_width}x{fig_height} (ratio: {fig_width/fig_height:.2f})")

    fig = create_plotly_figure(
        graph=G,
        pos=pos,
        node_types=final_node_types,
        fig_width=fig_width,
        fig_height=fig_height,
        focus_nodes=focus_nodes,
        # Use smaller node sizes for Plotly static image
        default_node_size=10,
        scaling_factor_node=30,
    )

    png_file_name = f"data_flow_plotly{('_' + file_name) if file_name else ''}.png"
    png_file_path = os.path.join(save_path, png_file_name)
    

    try:
        print(f"Writing Plotly PNG (scale={png_scale}) to: {png_file_path}")
        fig.write_image(png_file_path, scale=png_scale)  # Use scale factor

        resolved_png_file_path = Path(png_file_path).resolve()
        print(f"Successfully generated Plotly PNG: \033]8;;file://{resolved_png_file_path}\033\\{resolved_png_file_path}\033]8;;\033\\")
    except Exception as e:
        print(f"\n--- Error generating Plotly PNG ---")
        print(f"Failed to write image: {e}")
        print(
            "Ensure 'plotly' and 'kaleido' are installed ('pip install plotly kaleido'). Check Kaleido dependencies.\n"
        )


    svg_file_name = f"data_flow_plotly{('_' + file_name) if file_name else ''}.svg"
    svg_file_path = os.path.join(save_path, svg_file_name)

    try:
        print(f"Writing Plotly SVG  to: {svg_file_path}")
        fig.write_image(svg_file_path, scale=png_scale)  # Use scale factor
        resolved_svg_file_path = Path(svg_file_path).resolve()
        print(f"Successfully generated Plotly SVG: \033]8;;file://{resolved_svg_file_path}\033\\{resolved_svg_file_path}\033]8;;\033\\")
    except Exception as e:
        print(f"\n--- Error generating Plotly PNG ---")
        print(f"Failed to write image: {e}")
        print(
            "Ensure 'plotly' and 'kaleido' are installed ('pip install plotly kaleido'). Check Kaleido dependencies.\n"
        )
