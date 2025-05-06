import os
from pathlib import Path
import re
import networkx as nx
from typing import List, Tuple, Dict, Optional, Union
from pyvis.network import Network
import json
import textwrap
import math  # For ceiling function
import webbrowser
import html # Added for HTML escaping


def create_pyvis_figure(
    graph: Union[nx.DiGraph, nx.Graph],  # DO NOT EDIT THIS LINE
    node_types: Dict[str, Dict[str, str]],
    focus_nodes: List[str] = [],
    shake_towards_roots: bool = False,
) -> Tuple[Network, Dict]:
    """
    Creates the PyVis Network object and the initial options dictionary.
    Uses the exact initial_options provided by the user.
    """
    nt = Network(
        height="100vh",
        width="100vw",
        directed=True,
        bgcolor="#ffffff",
        font_color="#343434",
        heading="",
        cdn_resources="in_line",  # Use 'local' if you want offline files
    )

    # Calculate degrees for sizing
    in_degrees = dict(graph.in_degree())  # type: ignore
    out_degrees = dict(graph.out_degree())  # type: ignore
    degrees = {
        node: in_degrees.get(node, 0) + out_degrees.get(node, 0)
        for node in graph.nodes()
    }
    max_degree = max(degrees.values()) if degrees else 1
    min_size, max_size = 15, 45  # Node size range
    epsilon = 1e-6  # Small value to avoid division by zero
    for node in graph.nodes():
        node_degree = degrees.get(node, 0)
        # Scale size logarithmically or linearly - linear used here
        size = min_size + (node_degree / (max_degree + epsilon)) * (max_size - min_size)
        # Ensure size doesn't exceed max_size (can happen if max_degree is 0)
        size = min(size, max_size)

        # print(node, node_degree, size)  # Debugging output
        # Get node info - use fallback if somehow missing (shouldn't happen)
        node_info = node_types.get(
            node, {"type": "unknown", "database": "", "full_name": node}
        )
        node_type = node_info.get("type", "unknown")  # Use .get for safety
        # print(node_info)  # Debugging output
        # Color mapping
        color_map = {
            "view": "#4e79a7",  # Blue
            "table": "#59a14f",  # Green
            "cte_view": "#f9c846",  # Yellow for CTE views
            "unknown": "#e15759",  # Red (Should be less common now)
            "datamarket": "#ed7be7",  # Purple (Example)
            "other": "#f28e2c",  # Orange (Example)
        }
        color = color_map.get(node_type, "#bab0ab")  # Default grey for unmapped types

        border_color = "#2b2b2b"  # Darker border
        border_width = 1
        font_color = "#343434"

        # Get parents and children from the graph
        if not isinstance(graph, nx.DiGraph):
            # If the graph is undirected, use neighbors as both parents and children
            parents = sorted(list(graph.neighbors(node)))
            children = sorted(list(graph.neighbors(node)))
        elif isinstance(graph, nx.DiGraph):
            # If the graph is directed, use predecessors and successors
            parents = sorted(list(graph.predecessors(node)))
            children = sorted(list(graph.successors(node)))

        # Create hover text (tooltip) with definition as a styled card
        node_definition = node_info.get("definition")
        definition_html = ""
        if node_definition:
            escaped_node_definition = html.escape(node_definition)
            definition_html = (
                f"<div style='margin-top:10px;'><b>Definition:</b>"
                # The <pre> tag will now be styled by pyvis_styles.css to handle scrolling, padding, background (from Prism theme) etc.
                f'<pre class="language-sql"><code class="language-sql">{escaped_node_definition}</code></pre>'
                f"</div>"
            )

        hover_text = (
            f"<b>{node_info['full_name']}</b><br>"
            f"--------------------<br>"
            f"Type: {node_type}<br>"
            f"Database: {node_info['database'] or '(default)'}<br>"
            f"Connections: {node_degree}<br>"
            f"--------------------<br>"
            f"<b>Parents ({len(parents)}):</b><br>"
            + ("<br>".join(f"  • {p}" for p in parents) if parents else "  (None)")
            + "<br><br>"
            + f"<b>Children ({len(children)}):</b><br>"
            + ("<br>".join(f"  • {c}" for c in children) if children else "  (None)")
            + (definition_html if node_definition else "")
        )

        # Add node to pyvis network
        nt.add_node(
            node,  # Node ID (base name)
            label=node,  # Label displayed on the node
            color=color,
            shape="dot",  # Circle shape
            size=size,
            borderWidth=border_width,
            borderColor=border_color,
            font={
                "color": font_color,
                "size": 12,
                "strokeWidth": 0,  # No text stroke
                # "strokeColor": "#ffffff", # Not needed if strokeWidth is 0
                "align": "center",
            },
            title=hover_text,  # HTML tooltip content
            mass=1 + node_degree / (max_degree + epsilon) * 2,  # Influence physics
            fixed=False,  # Allow physics engine to move node
        )

    # Add edges to pyvis network
    for u, v in graph.edges():
        if (
            u in graph.nodes() and v in graph.nodes()
        ):  # Ensure both nodes exist in the graph
            nt.add_edge(
                u,
                v,
                color={
                    "color": "#cccccc",  # Light grey edge
                    "opacity": 0.7,
                    "highlight": "#e60049",  # Red highlight color
                    "hover": "#e60049",  # Red hover color
                },
                width=1.5,  # Default edge width
                hoverWidth=2.5,  # Width on hover
                selectionWidth=2.5,  # Width when selected
                # Smooth edges look better for hierarchical usually
                smooth={
                    "enabled": True,
                    "type": "cubicBezier",
                    "forceDirection": "vertical",  # Changed for better hierarchical flow sometimes
                    "roundness": 0.4,
                },
                arrows={
                    "to": {"enabled": True, "scaleFactor": 0.6}
                },  # Arrow pointing to target
            )
    # --- Use the EXACT Initial Pyvis options provided by the user ---
    # <<< PASTE THE USER'S PROVIDED initial_options DICTIONARY HERE >>>
    initial_options = {
        "layout": {
            "hierarchical": {
                "enabled": True,
                "direction": "LR",
                "sortMethod": "directed",
                "shakeTowards": "roots" if shake_towards_roots else "leaves",
                "nodeSpacing": 1,
                "treeSpacing": 200,
                "levelSeparation": 300,
                "blockShifting": True,
                "edgeMinimization": True,
                "parentCentralization": True,
            }
        },
        "interaction": {
            "dragNodes": True,
            "dragView": True,
            "hover": True,
            "hoverConnectedEdges": True,
            "keyboard": {
                "enabled": True,
                "speed": {"x": 10, "y": 10, "zoom": 0.02},
                "bindToWindow": True,
            },
            "multiselect": True,
            "navigationButtons": False,
            "selectable": True,
            "selectConnectedEdges": True,
            "tooltipDelay": 150,
            "zoomView": True,
        },
        "physics": {
            "enabled": True,
            "solver": "hierarchicalRepulsion",
            "barnesHut": {
                "gravitationalConstant": -2000,
                "centralGravity": 0.3,
                "springLength": 95,
                "springConstant": 0.04,
                "damping": 0.09,
                "avoidOverlap": 0,
            },
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "centralGravity": 0.01,
                "springLength": 100,
                "springConstant": 0.08,
                "damping": 0.4,
                "avoidOverlap": 0,
            },
            "hierarchicalRepulsion": {
                "centralGravity": 0.3,
                "springLength": 150,
                "springConstant": 0.015,
                "nodeDistance": 140,
                "damping": 0.15,
                "avoidOverlap": 1,
            },
            "repulsion": {
                "centralGravity": 0.2,
                "springLength": 200,
                "springConstant": 0.05,
                "nodeDistance": 100,
                "damping": 0.09,
            },
            "stabilization": {
                "enabled": True,
                "iterations": 1000,
                "updateInterval": 25,
                "fit": True,
            },
            "adaptiveTimestep": True,
            "minVelocity": 0.75,
            "timestep": 0.5,
        },
        "edges": {
            "arrows": {"to": {"enabled": True, "scaleFactor": 0.5}},
            "color": {"inherit": False},
            "smooth": {
                "enabled": True,
                "type": "cubicBezier",
                "forceDirection": "horizontal",
                "roundness": 0.2,
            },
            "width": 1.5,
            "selectionWidth": 2.5,
            "hoverWidth": 2.5,
            "widthConstraint": False,
        },
        "nodes": {
            "borderWidth": 1,
            "borderWidthSelected": 3,
            "font": {"size": 12, "face": "arial", "color": "#343434"},
            "scaling": {
                "min": 10,
                "max": 45,
                "label": {"enabled": True, "min": 10, "max": 20},
            },
            "shape": "dot",
            "shapeProperties": {"interpolation": False},
            "shadow": {"enabled": False, "size": 10, "x": 5, "y": 5},
        },
    }
    # <<< END OF PASTED DICTIONARY >>>

    nt.set_options(json.dumps(initial_options))
    return nt, initial_options


def inject_controls_and_styles(
    html_content: str, initial_options: Dict, file_name: str = ""
) -> str:
    """Injects custom CSS, HTML for controls/legend, and JavaScript into Pyvis HTML."""
    # --- 1. Custom CSS Injection ---
    css_path = os.path.join(os.path.dirname(__file__), "pyvis_styles.css")
    with open(css_path, "r", encoding="utf-8") as f:
        css_content = f.read()
    custom_css = f'<style type="text/css">\n{css_content}\n</style>'

    # --- 2. Custom HTML (controls/legend/search panel) ---
    def create_control(key_path, config):
        label_text = key_path.split(".")[-1].replace("_", " ").title()
        html = f'<div class="control-item" id="ctrl_{key_path.replace(".", "_")}">'
        html += f'<label for="{key_path}" title="{key_path}">{label_text}</label>'
        value = initial_options
        try:
            for k in key_path.split("."):
                value = value[k]
        except KeyError:
            print(f"Warning: Initial option key not found: {key_path}")
            value = None
        if isinstance(value, bool):
            html = (
                f'<div class="switch-container" id="ctrl_{key_path.replace(".", "_")}">'
                f'<label for="{key_path}" class="text-label" title="{key_path}">{label_text}</label>'
                f'<label class="switch"><input type="checkbox" id="{key_path}" {"checked" if value else ""}> <span class="slider"></span></label>'
            )
        elif key_path == "physics.solver":
            options = [
                "barnesHut",
                "forceAtlas2Based",
                "hierarchicalRepulsion",
                "repulsion",
            ]
            opts_html = "".join(
                [
                    f'<option value="{o}" {"selected" if value == o else ""}>{o}</option>'
                    for o in options
                ]
            )
            html += f'<select id="{key_path}">{opts_html}</select>'
        elif key_path == "layout.hierarchical.direction":
            options = ["LR", "RL", "UD", "DU"]
            opts_html = "".join(
                [
                    f'<option value="{o}" {"selected" if value == o else ""}>{o}</option>'
                    for o in options
                ]
            )
            html += f'<select id="{key_path}">{opts_html}</select>'
        elif key_path == "layout.hierarchical.sortMethod":
            options = ["hubsize", "directed"]
            opts_html = "".join(
                [
                    f'<option value="{o}" {"selected" if value == o else ""}>{o}</option>'
                    for o in options
                ]
            )
            html += f'<select id="{key_path}">{opts_html}</select>'
        elif key_path == "edges.smooth.type":
            options = [
                "dynamic",
                "continuous",
                "discrete",
                "diagonalCross",
                "horizontal",
                "vertical",
                "curvedCW",
                "curvedCCW",
                "cubicBezier",
            ]
            opts_html = "".join(
                [
                    f'<option value="{o}" {"selected" if value == o else ""}>{o}</option>'
                    for o in options
                ]
            )
            html += f'<select id="{key_path}">{opts_html}</select>'
        elif key_path == "nodes.shape":
            options = [
                "ellipse",
                "circle",
                "database",
                "box",
                "text",
                "diamond",
                "dot",
                "star",
                "triangle",
                "triangleDown",
                "square",
            ]
            opts_html = "".join(
                [
                    f'<option value="{o}" {"selected" if value == o else ""}>{o}</option>'
                    for o in options
                ]
            )
            html += f'<select id="{key_path}">{opts_html}</select>'
        elif key_path == "physics.hierarchicalRepulsion.avoidOverlap":
            # Always render avoidOverlap as a slider with min=0, max=1, step=0.01
            html += (
                f'<input type="range" id="{key_path}" min="0" max="1" step="0.01" value="{value}">'
                f'<span class="value-display" id="{key_path}_value">{value:.2f}</span>'
            )
        elif key_path == "nodes.size":
            # Add a slider for node size with a reasonable range
            html += (
                f'<input type="range" id="{key_path}" min="5" max="100" step="1" value="{value}">'
                f'<span class="value-display" id="{key_path}_value">{value}</span>'
            )
        elif key_path == "nodes.scaling.min":
            html += (
                f'<input type="range" id="{key_path}" min="1" max="100" step="1" value="{value}">'
                f'<span class="value-display" id="{key_path}_value">{value}</span>'
            )
        elif key_path == "nodes.scaling.max":
            html += (
                f'<input type="range" id="{key_path}" min="1" max="1000" step="1" value="{value}">'
                f'<span class="value-display" id="{key_path}_value">{value}</span>'
            )
        elif isinstance(value, (int, float)):
            if (
                "delay" in key_path.lower()
                or "iteration" in key_path.lower()
                or "velocity" in key_path.lower()
                or "timestep" in key_path.lower()
                or "constant" in key_path.lower()
                or "factor" in key_path.lower()
                or "size" in key_path.lower()
                or "width" in key_path.lower()
            ):
                step = (
                    0.01
                    if isinstance(value, float) and value < 5
                    else (0.1 if isinstance(value, float) else 1)
                )
                min_val, max_val = 0, 1000  # Simplified range detection
                if "delay" in key_path.lower():
                    max_val = 2000
                elif "iteration" in key_path.lower():
                    max_val = 5000
                elif "factor" in key_path.lower():
                    max_val = 2
                elif "size" in key_path.lower() or "width" in key_path.lower():
                    max_val = 50
                elif value <= 1:
                    max_val = 1
                elif value > 0:
                    max_val = value * 3
                html += f'<input type="number" id="{key_path}" value="{value}" step="{step}" min="{min_val}">'
            else:
                step = (
                    0.01
                    if isinstance(value, float) and value < 1
                    else (0.1 if isinstance(value, float) else 10)
                )
                min_val = 0 if "damping" not in key_path.lower() else 0.05
                max_val = (
                    1
                    if "damping" in key_path.lower()
                    or "overlap" in key_path.lower()
                    or "gravity" in key_path.lower()
                    else 1000
                )
                html += f'<input type="range" id="{key_path}" min="{min_val}" max="{max_val}" step="{step}" value="{value}">'
                html += (
                    f'<span class="value-display" id="{key_path}_value">{value:.2f}</span>'
                    if isinstance(value, float)
                    else f'<span class="value-display" id="{key_path}_value">{value}</span>'
                )
        else:
            html += f'<input type="text" id="{key_path}" value="{value if value is not None else ""}">'
        html += "</div>"
        return html

    physics_controls = [
        create_control(k, initial_options)
        for k in [
            "physics.enabled",
            "physics.solver",
            "physics.hierarchicalRepulsion.nodeDistance",
            "physics.hierarchicalRepulsion.centralGravity",
            "physics.hierarchicalRepulsion.springLength",
            "physics.hierarchicalRepulsion.springConstant",
            "physics.hierarchicalRepulsion.damping",
            "physics.hierarchicalRepulsion.avoidOverlap",
            "physics.minVelocity",
            "physics.timestep",
        ]
    ]
    layout_controls = [
        create_control(k, initial_options)
        for k in [
            "layout.hierarchical.enabled",
            "layout.hierarchical.direction",
            "layout.hierarchical.sortMethod",
            "layout.hierarchical.levelSeparation",
            "layout.hierarchical.nodeSpacing",
            "layout.hierarchical.treeSpacing",
        ]
    ]
    interaction_controls = [
        create_control(k, initial_options)
        for k in [
            "interaction.dragNodes",
            "interaction.dragView",
            "interaction.hover",
            "interaction.hoverConnectedEdges",
            "interaction.keyboard.enabled",
            "interaction.multiselect",
            "interaction.selectable",
            "interaction.selectConnectedEdges",
            "interaction.tooltipDelay",
            "interaction.zoomView",
        ]
    ]
    edge_controls = [
        create_control(k, initial_options)
        for k in [
            "edges.smooth.enabled",
            "edges.smooth.type",
            "edges.smooth.roundness",
            "edges.arrows.to.enabled",
            "edges.arrows.to.scaleFactor",
        ]
    ]
    node_controls = [
        create_control(k, initial_options)
        for k in [
            "nodes.scaling.min",
            "nodes.scaling.max",
            "nodes.scaling.label.enabled",
            "nodes.font.size",
            "nodes.shape",
            "nodes.shadow.enabled",
        ]
    ]

    custom_html = textwrap.dedent(f"""
    <div id="loadingOverlay"><div class="spinner"></div><div>Processing...</div></div>
    <div class="control-panel" id="controlPanel">
        <div class="panel-tab" onclick="togglePanel()" title="Toggle Controls">
            <div class="hamburger-icon">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
        <div class="panel-header">Network Controls</div>
        <div class="panel-content">
            <div class="control-group"><h3>General</h3>
                 <button class="control-button secondary" onclick="network.fit()"><i class="fas fa-expand-arrows-alt"></i> Fit View</button>
                 <button class="control-button secondary" onclick="resetToInitialOptions()"><i class="fas fa-undo-alt"></i> Reset Options</button>
                 <button class="control-button" onclick="applyUISettings()"><i class="fas fa-check"></i> Apply Changes</button>
            </div>
            <div class="control-group"><h3>Physics</h3>{"".join(physics_controls)}</div>
            <div class="control-group"><h3>Layout</h3>{"".join(layout_controls)}</div>
            <div class="control-group"><h3>Interaction</h3>{"".join(interaction_controls)}</div>
            <div class="control-group"><h3>Edges</h3>{"".join(edge_controls)}</div>
            <div class="control-group"><h3>Nodes</h3>{"".join(node_controls)}</div>
            <div class="control-group"><h3>Export</h3>
                 <!-- NEW Export Buttons with tooltip -->
                 <button class="control-button secondary" onclick="startSelectionMode()"><i class="fas fa-crop-alt"></i> Export Selection</button>
                 <button class="control-button secondary" onclick="saveFullNetworkSVG()"><i class="fas fa-file-svg"></i> Save Full SVG</button>
                 <button class="control-button secondary" title="Warning: PNG rendering may fail if the image is too large!" onclick="saveFullNetworkPNG(3)"><i class="fas fa-image"></i> Save Full PNG (1.5x)</button>
            </div>
        </div>
    </div>
    <div class="legend">
        <div class="legend-item"><div class="legend-color" style="background-color: #4e79a7;"></div><div class="legend-label">View</div></div>
        <div class="legend-item"><div class="legend-color" style="background-color: #59a14f;"></div><div class="legend-label">Table</div></div>
        <div class="legend-item"><div class="legend-color" style="background-color: #f9c846;"></div><div class="legend-label">CTE View</div></div>
        <div class="legend-item"><div class="legend-color" style="background-color: #ed7be7;"></div><div class="legend-label">Data Market</div></div>
        <div class="legend-item"><div class="legend-color" style="background-color: #f28e2c;"></div><div class="legend-label">Other DB</div></div>
        <div class="legend-item"><div class="legend-color" style="background-color: #e15759;"></div><div class="legend-label">Unknown</div></div>
    </div>

    <!-- Node Creation FAB and Modal -->
    <button id="addNodeFab" title="Add Node">+</button>
    <div id="addNodeModal">
        <h4>Add New Node</h4>
        <div class="error" id="addNodeError"></div>
        <label for="addNodeId">Node ID</label>
        <input type="text" id="addNodeId" placeholder="Enter node ID..." autocomplete="off">
        <label for="addNodeType">Type</label>
        <select id="addNodeType">
            <option value="table">Table</option>
            <option value="view">View</option>
            <option value="cte_view">CTE View</option>
            <option value="datamarket">Data Market</option>
            <option value="other">Other</option>
            <option value="unknown">Unknown</option>
        </select>
        <label for="addNodeDatabase">Database</label>
        <input type="text" id="addNodeDatabase" placeholder="(Optional)">
        <div class="modal-actions">
            <button class="add-btn" id="addNodeModalAddBtn">Add</button>
            <button class="cancel-btn" id="addNodeModalCancelBtn">Cancel</button>
        </div>
    </div>

    <!-- NEW: Search Icon & Panel -->
    <div id="searchIcon" onclick="toggleSearchPanel()" title="Search (Ctrl+F)">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="#555" xmlns="http://www.w3.org/2000/svg">
            <path d="M15.5 14h-.79l-.28-.27a6.471 6.471 0 001.48-5.34C15.46 5.59 13.13 3.26 10 3.26S4.54 5.59 4.54 8.39s2.33 5.13 5.46 5.13a6.5 6.5 0 005.34-1.48l.27.28v.79l4.25 4.25 1.27-1.27L15.5 14zM10 12.26a3.87 3.87 0 110-7.74 3.87 3.87 0 010 7.74z"/>
        </svg>
    </div>
    
    <div id="searchPanel">
        <div class="search-header">
            <h3>Search Nodes</h3>
            <button class="close-search" onclick="closeSearchPanel()"><i class="fas fa-times"></i></button>
        </div>
        <div class="search-container">
            <div class="search-input-container">
                <i class="fas fa-search search-input-icon"></i>
                <input type="text" id="searchInput" placeholder="Search by label, type, database, etc." autocomplete="off">
            </div>
        </div>
        <div class="search-options">
            <div class="search-option">
                <input type="checkbox" id="searchCaseSensitive">
                <label for="searchCaseSensitive">Case sensitive</label>
            </div>
            <div class="search-option">
                <input type="checkbox" id="searchFuzzy" checked>
                <label for="searchFuzzy">Fuzzy search</label>
            </div>
            <div class="search-option">
                <input type="checkbox" id="searchHighlightAll" checked>
                <label for="searchHighlightAll">Highlight all matches</label>
            </div>
            <div class="search-option">
                <input type="checkbox" id="searchDimOthers">
                <label for="searchDimOthers">Dim non-matches</label>
            </div>
        </div>
        <div class="search-navigation">
            <div class="search-count" id="searchResultCount">0 results</div>
            <div class="search-nav-buttons">
                <button class="search-nav-button" id="prevSearchResult" disabled onclick="navigateSearchResult(-1)">
                    <i class="fas fa-chevron-up"></i> Prev
                </button>
                <button class="search-nav-button" id="nextSearchResult" disabled onclick="navigateSearchResult(1)">
                    <i class="fas fa-chevron-down"></i> Next
                </button>
                <button class="search-nav-button" onclick="clearSearch()">
                    <i class="fas fa-times"></i> Clear
                </button>
            </div>
        </div>
        <div id="searchStatus"></div>
        <div class="search-keyboard-shortcuts">
            <span class="keyboard-shortcut">Ctrl+F</span> Open/close search | 
            <span class="keyboard-shortcut">Enter</span> Next result | 
            <span class="keyboard-shortcut">Shift+Enter</span> Previous result | 
            <span class="keyboard-shortcut">Esc</span> Close
        </div>
    </div>

    <!-- NEW: Selection Overlay -->
    <div id="selectionOverlay">
        <div id="selectionRectangle"></div>
    </div>

    <!-- Export Choice Modal (Updated button order and text with tooltip) -->
    <div id="exportChoiceModal">
        <h4>Export Selection</h4>
        <button class="export-svg" onclick="exportSelection('svg')">Save as SVG (Recommended)</button>
        <button class="export-png" title="Warning: PNG rendering may fail if the selection is too large!" onclick="exportSelection('png')">Save as PNG (1.5x) !NB will not work if image is too large</button>
        <button class="export-cancel" onclick="cancelSelectionMode()">Cancel</button>
    </div>
    """)

    # --- 3. Custom JavaScript Injection ---
    js_path = os.path.join(os.path.dirname(__file__), "pyvis_scripts.js")
    with open(js_path, "r", encoding="utf-8") as f:
        js_template = f.read()
    initial_options_json = json.dumps(initial_options)
    export_file_name_base = f"{file_name if file_name else 'network_export'}"
    js_content = js_template.replace(
        '"%%INITIAL_NETWORK_OPTIONS%%"', initial_options_json
    ).replace(
        '"%%BASE_FILE_NAME%%"', json.dumps(export_file_name_base)
    )
    custom_js = f'<script type="text/javascript">\n{js_content}\n</script>'

    # --- 4. Injection ---
    html_content = html_content.replace("</head>", custom_css + "\n</head>", 1)
    html_content = html_content.replace(
        "</body>",
        custom_html
        + "\n"
        + custom_js
        + "\n</body>",
        1,
    )
    # Additional fix: highlight SQL in Vis tooltip container
    tooltip_hook = '<script>if(window.network&&window.Prism){network.on("showPopup",function(){var t=document.querySelector(".vis-tooltip"); if(t){Prism.highlightAllUnder(t);}});}</script>'
    if '</body>' in html_content:
        html_content = html_content.replace('</body>', tooltip_hook + '</body>', 1)
    else:
        html_content = html_content + tooltip_hook
    return html_content


def inject_html_doctype(html_content: str) -> str:
    """Injects the HTML doctype into the HTML content."""
    doctype = "<!DOCTYPE html>"
    return doctype + "\n" + html_content


def inject_sql_code_highlighting(html_content: str) -> str:
    """Injects Prism.js CSS in <head> and JS before </body> for SQL code highlighting,
    and adds a trigger to highlight code in dynamic tooltips."""
    prism_css = (
        '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism.min.css">\n'
    )
    prism_js_core = '<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>\n'
    prism_js_sql = '<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-sql.min.js"></script>\n'
    
    prism_js_trigger = '''<script> document.addEventListener("DOMContentLoaded", function() { if (window.Prism && typeof network.on === "function") { network.on("showPopup", function() { Prism.highlightAll(); }); } }); \</script> '''


    # Inject CSS in <head>
    if '</head>' in html_content:
        html_content = html_content.replace('</head>', prism_css + '</head>', 1)
    elif '<meta charset="utf-8">' in html_content: # Fallback if </head> is not present but meta charset is
        html_content = html_content.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n' + prism_css, 1)
    else: # Fallback: prepend to content
        html_content = prism_css + html_content

    # Inject JS (core, sql component, and trigger script) before </body>
    all_prism_js = prism_js_core + prism_js_sql + prism_js_trigger
    if '</body>' in html_content:
        html_content = html_content.replace('</body>', all_prism_js + '</body>', 1)
    else: # Fallback: append to content
        html_content = html_content + all_prism_js
        
    # Add fallback Prism highlight hook for dynamic popups
    fallback_script = '<script>document.addEventListener("click", function(){ Prism.highlightAll(); });</script>'
    if '</body>' in html_content:
        html_content = html_content.replace('</body>', fallback_script + '</body>', 1)
    else:
        html_content = html_content + fallback_script
        
    return html_content


def draw_pyvis_html(
    edges: List[Tuple[str, str]],
    node_types: Dict[str, Dict[str, str]],
    auto_open: bool = False,  # Add option to auto-open in browser
    save_path: str = "",
    file_name: str = "",
    draw_edgeless: bool = False,
    focus_nodes: List[str] = [],  # Add focus nodes for potential highlighting
    is_focused_view: bool = False,  # Flag for layout direction
) -> None:
    """Generates the interactive Pyvis HTML file."""
    print(
        f"Generating Pyvis HTML{' (focused view)' if is_focused_view else ' (complete view)'}..."
    )
    G: Union[nx.DiGraph, nx.Graph] = nx.DiGraph()
    G.add_edges_from(edges)
    valid_nodes = list(node_types.keys())
    if draw_edgeless:
        G.add_nodes_from(valid_nodes)
    else:
        nodes_in_edges = set(u for u, v in edges) | set(v for u, v in edges)
        nodes_to_draw = nodes_in_edges.union(set(valid_nodes))
        if not nodes_to_draw:
            print("Warning: No nodes to draw for Pyvis HTML.")
            return
        G = G.subgraph(nodes_to_draw).copy()

    final_node_types = {
        node: node_types.get(
            node, {"type": "unknown", "database": "", "full_name": node}
        )
        for node in G.nodes()
    }
    if not G.nodes():
        print("Warning: Graph is empty for Pyvis HTML.")
        return

    # Use shake_towards_roots for focused views
    shake_dir = is_focused_view

    html_file_name_part = (
        "focused_data_flow_pyvis" if is_focused_view else "data_flow_pyvis"
    )
    html_file_name = (
        f"{html_file_name_part}{('_' + file_name) if file_name else ''}.html"
    )
    html_file_path = os.path.join(save_path, html_file_name)

    fig, initial_options = create_pyvis_figure(
        G, final_node_types, focus_nodes, shake_towards_roots=shake_dir
    )
    html_content = fig.generate_html()
    # Use a distinct file name identifier for the PNG downloaded from this specific HTML
    png_export_name = f"{html_file_name_part}{('_' + file_name) if file_name else ''}"
    modified_html_content = inject_controls_and_styles(
        html_content, initial_options, png_export_name
    )
    modified_html_content = inject_html_doctype(modified_html_content)
    modified_html_content = inject_sql_code_highlighting(modified_html_content)
    try:
        with open(html_file_path, "w", encoding="utf-8") as file:
            file.write(modified_html_content)
        resolved_html_file_path = Path(html_file_path).resolve()
        print(f"Successfully generated Pyvis HTML: {resolved_html_file_path}")

        # If auto_open is enabled, open the file in the default browser
        if auto_open:
            try:
                print("Opening in default browser...")
                webbrowser.open(f"file://{resolved_html_file_path}")
            except Exception as e:
                print(f"Could not open browser automatically: {e}")
                print(
                    f"Please open this URL manually: file://{resolved_html_file_path}"
                )
    except Exception as e:
        print(f"Error writing Pyvis HTML file {html_file_path}: {e}")
