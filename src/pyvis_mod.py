import os
from pathlib import Path
import re
import networkx as nx
from typing import List, Tuple, Dict, Optional, Union
from pyvis.network import Network
import json
import textwrap
import math
import webbrowser
import html # Ensure this is imported

def create_pyvis_figure(
    graph: Union[nx.DiGraph, nx.Graph],
    node_types: Dict[str, Dict[str, str]],
    focus_nodes: List[str] = [],
    shake_towards_roots: bool = False,
) -> Tuple[Network, Dict]:
    nt = Network(
        height="100vh",
        width="100vw",
        directed=True,
        bgcolor="#ffffff",
        font_color="#343434",
        heading="",
        cdn_resources="in_line",
    )

    in_degrees = dict(graph.in_degree()) # type: ignore
    out_degrees = dict(graph.out_degree()) # type: ignore
    degrees = {
        node: in_degrees.get(node, 0) + out_degrees.get(node, 0)
        for node in graph.nodes()
    }
    max_degree = max(degrees.values()) if degrees else 1
    min_size, max_size = 15, 45
    epsilon = 1e-6

    for node_id_str in graph.nodes():
        node_degree = degrees.get(node_id_str, 0)
        size = min_size + (node_degree / (max_degree + epsilon)) * (max_size - min_size)
        size = min(size, max_size)

        node_info = node_types.get(
            node_id_str, {"type": "unknown", "database": "", "full_name": node_id_str}
        )
        node_type = node_info.get("type", "unknown")
        
        color_map = {
            "view": "#4e79a7", "table": "#59a14f", "cte_view": "#f9c846",
            "unknown": "#e15759", "datamarket": "#ed7be7", "other": "#f28e2c",
        }
        color = color_map.get(node_type, "#bab0ab")
        border_color = "#2b2b2b"
        border_width = 1
        font_color = "#343434"
        
        # Part 1: Simple info for hover tooltip
        simple_hover_info = (
            f"<b>{html.escape(node_info['full_name'])}</b><br>"
            f"Type: {html.escape(node_type)}<br>"
            f"Database: {html.escape(node_info['database'] or '(default)')}"
        )

        # Part 2: Definition (for persistent tooltip)
        node_definition = node_info.get("definition")
        definition_html_part = ""
        if node_definition:
            escaped_node_definition = html.escape(node_definition)
            definition_html_part = (
                f"<div class='pyvis-definition-block' style='margin-top:10px; padding-top: 5px; border-top: 1px solid #eee;'><b>Definition:</b>"
                f"<pre class='language-sql' style='max-height: 250px; overflow: auto;'><code class='language-sql'>{escaped_node_definition}</code></pre>"
                f"</div>"
            )
        
        hover_content_separator = "<div class='pyvis-hover-separator' style='display:none !important;'>---HOVER_END---</div>"
        full_node_title = simple_hover_info + hover_content_separator + definition_html_part
        
        nt.add_node(
            node_id_str,
            label=node_id_str,
            color=color,
            shape="dot",
            size=size,
            borderWidth=border_width,
            borderColor=border_color,
            font={"color": font_color, "size": 12, "strokeWidth": 0, "align": "center"},
            title=full_node_title,
            mass=1 + node_degree / (max_degree + epsilon) * 2,
            fixed=False,
        )

    for u, v in graph.edges():
        if u in graph.nodes() and v in graph.nodes():
            nt.add_edge(
                u, v,
                color={"color": "#cccccc", "opacity": 0.7, "highlight": "#e60049", "hover": "#e60049"},
                width=1.5, hoverWidth=2.5, selectionWidth=2.5,
                smooth={"enabled": True, "type": "cubicBezier", "forceDirection": "vertical", "roundness": 0.4},
                arrows={"to": {"enabled": True, "scaleFactor": 0.6}},
            )

    initial_options = {
        "layout": {
            "hierarchical": {
                "enabled": True,
                "direction": "LR",
                "sortMethod": "directed",
                "shakeTowards": "roots" if shake_towards_roots else "leaves",
                "nodeSpacing": 1, # Adjust as needed
                "treeSpacing": 200, # Adjust as needed
                "levelSeparation": 300, # Adjust as needed
                "blockShifting": True,
                "edgeMinimization": True,
                "parentCentralization": True,
            }
        },
        "interaction": {
            "dragNodes": True,
            "dragView": True,
            "hover": True,  # CRITICAL: Ensure this is true for hover tooltips to work
            "hoverConnectedEdges": False, # Usually false if using custom hover tooltips
            "keyboard": {
                "enabled": True,
                "speed": {"x": 10, "y": 10, "zoom": 0.02},
                "bindToWindow": True,
            },
            "multiselect": True,
            "navigationButtons": False, # Set to true if you want vis.js navigation buttons
            "selectable": True,
            "selectConnectedEdges": True,
            "tooltipDelay": 100, # Native vis.js tooltip delay (Tippy has its own)
            "zoomView": True,
        },
        "physics": {
            "enabled": True, # False if using hierarchical and want static layout after initial
            "solver": "hierarchicalRepulsion", # Good for hierarchical
            "barnesHut": {
                "gravitationalConstant": -2000, "centralGravity": 0.3,
                "springLength": 95, "springConstant": 0.04, "damping": 0.09, "avoidOverlap": 0
            },
            "forceAtlas2Based": {
                "gravitationalConstant": -50, "centralGravity": 0.01, "springLength": 100,
                "springConstant": 0.08, "damping": 0.4, "avoidOverlap": 0
            },
            "hierarchicalRepulsion": {
                "centralGravity": 0.0, # Often 0 for hierarchical
                "springLength": 120,
                "springConstant": 0.01,
                "nodeDistance": 120, # Min distance between nodes on same level
                "damping": 0.09,
                "avoidOverlap": 0 # Set to 1 if overlap is an issue, might slow down
            },
            "repulsion": {
                "centralGravity": 0.2, "springLength": 200, "springConstant": 0.05,
                "nodeDistance": 100, "damping": 0.09
            },
            "stabilization": { # Should run if physics or hierarchical is enabled
                "enabled": True, "iterations": 1000, "updateInterval": 25, "fit": True
            },
            "adaptiveTimestep": True,
            "minVelocity": 0.75,
            "timestep": 0.5,
        },
        "edges": {
            "arrows": {"to": {"enabled": True, "scaleFactor": 0.5}},
            "color": {"inherit": False}, # Explicit color setting for edges
            "smooth": {
                "enabled": True, "type": "cubicBezier",
                "forceDirection": "horizontal", # or "vertical" or "none"
                "roundness": 0.4 # 0 for straight, 0.5 for very curvy
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
                "min": 10, "max": 45,
                "label": {"enabled": True, "min": 10, "max": 20}
            },
            "shape": "dot",
            "shapeProperties": {"interpolation": False}, # For images
            "shadow": {"enabled": False, "size": 10, "x": 5, "y": 5},
        },
    }
    nt.set_options(json.dumps(initial_options))
    return nt, initial_options

def inject_controls_and_styles(
    html_content: str, initial_options: Dict, file_name: str = ""
) -> str:
    # --- 1. Custom CSS Injection ---
    css_path = os.path.join(os.path.dirname(__file__), "pyvis_styles.css")
    css_content = ""
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()
    except FileNotFoundError:
        print(f"Warning: pyvis_styles.css not found at {css_path}")
    custom_css = f'<style type="text/css">\n{css_content}\n</style>'

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

    custom_html_elements = textwrap.dedent(f"""
    <div id="loadingOverlay"><div class="spinner"></div><div>Processing...</div></div>
    <div class="control-panel" id="controlPanel">
        <div class="panel-tab" onclick="togglePanel()" title="Toggle Controls"><div class="hamburger-icon"><span></span><span></span><span></span></div></div>
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
                 <button class="control-button secondary" onclick="startSelectionMode()"><i class="fas fa-crop-alt"></i> Export Selection</button>
                 <button class="control-button secondary" onclick="saveFullNetworkSVG()"><i class="fas fa-file-svg"></i> Save Full SVG</button>
                 <button class="control-button secondary" title="Warning: PNG rendering may fail if the image is too large!" onclick="saveFullNetworkPNG(1.5)"><i class="fas fa-image"></i> Save Full PNG (1.5x)</button>
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
    <button id="addNodeFab" title="Add Node">+</button>
    <div id="addNodeModal">
        <h4>Add New Node</h4><div class="error" id="addNodeError"></div>
        <label for="addNodeId">Node ID</label><input type="text" id="addNodeId" placeholder="Enter node ID..." autocomplete="off">
        <label for="addNodeType">Type</label><select id="addNodeType"><option value="table">Table</option><option value="view">View</option></select>
        <label for="addNodeDatabase">Database</label><input type="text" id="addNodeDatabase" placeholder="(Optional)">
        <div class="modal-actions"><button class="add-btn" id="addNodeModalAddBtn">Add</button><button class="cancel-btn" id="addNodeModalCancelBtn">Cancel</button></div>
    </div>
    <div id="searchIcon" onclick="toggleSearchPanel()" title="Search (Ctrl+F)"><i class="fas fa-search"></i></div>
    <div id="searchPanel">
        <div class="search-header"><h3>Search Nodes</h3><button class="close-search" onclick="closeSearchPanel()"><i class="fas fa-times"></i></button></div>
        <div class="search-container"><div class="search-input-container"><i class="fas fa-search search-input-icon"></i><input type="text" id="searchInput" placeholder="Search..." autocomplete="off"></div></div>
        <div class="search-options">
            <div class="search-option"><input type="checkbox" id="searchCaseSensitive"><label for="searchCaseSensitive">Case sensitive</label></div>
            <div class="search-option"><input type="checkbox" id="searchFuzzy" checked><label for="searchFuzzy">Fuzzy</label></div>
            <div class="search-option"><input type="checkbox" id="searchHighlightAll" checked><label for="searchHighlightAll">Highlight all</label></div>
            <div class="search-option"><input type="checkbox" id="searchDimOthers"><label for="searchDimOthers">Dim others</label></div>
        </div>
        <div class="search-navigation"><div class="search-count" id="searchResultCount"></div><div class="search-nav-buttons"><button id="prevSearchResult" disabled><i class="fas fa-chevron-up"></i></button><button id="nextSearchResult" disabled><i class="fas fa-chevron-down"></i></button><button onclick="clearSearch()"><i class="fas fa-times"></i></button></div></div>
        <div id="searchStatus"></div><div class="search-keyboard-shortcuts"><span class="keyboard-shortcut">Ctrl+F</span> Open | <span class="keyboard-shortcut">Enter</span> Next | <span class="keyboard-shortcut">Shift+Enter</span> Prev | <span class="keyboard-shortcut">Esc</span> Close</div>
    </div>
    <div id="selectionOverlay"><div id="selectionRectangle"></div></div>
    <div id="exportChoiceModal"><h4>Export Selection</h4><button class="export-svg" onclick="exportSelection('svg')">SVG</button><button class="export-png" onclick="exportSelection('png')">PNG</button><button class="export-cancel" onclick="cancelSelectionMode()">Cancel</button></div>
    """)


    # --- 3. Custom JavaScript Injection ---
    js_components_dir = os.path.join(os.path.dirname(__file__), "js", "pyvis_components")
    js_files_order = [
        "core.js", "loading.js", "panels.js", "search.js", "keyboard.js",
        "settings.js", "export.js", "selection.js", "tooltips.js",
        "hover_tooltips.js", # This is our modified one
        "node_actions.js", "init.js"
    ]

    concatenated_js_content = []
    for js_file_name in js_files_order:
        js_file_path = os.path.join(js_components_dir, js_file_name)
        try:
            with open(js_file_path, "r", encoding="utf-8") as f:
                concatenated_js_content.append(f.read())
        except FileNotFoundError:
            print(f"Warning: JavaScript component file not found: {js_file_path}")

    js_template_concatenated = "\n\n// --- Next Component: {js_file_name} --- \n\n".join(concatenated_js_content)
    
    initial_options_json = json.dumps(initial_options) # Ensure initial_options is the complete dict
    export_file_name_base = f"{file_name if file_name else 'network_export'}"

    js_content_final = js_template_concatenated.replace(
        'const initialNetworkOptions = "%%INITIAL_NETWORK_OPTIONS%%";',
        f'const initialNetworkOptions = {initial_options_json};'
    ).replace(
        'const baseFileName = "%%BASE_FILE_NAME%%";',
        f'const baseFileName = {json.dumps(export_file_name_base)};'
    )
    custom_js = f'<script type="text/javascript">\n{js_content_final}\n</script>'

    # --- 4. Injection ---
    # Inject FontAwesome (if used by icons), Tippy.css before custom CSS
    head_injections = (
        '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">\n'
        '<link rel="stylesheet" href="https://unpkg.com/tippy.js@6/dist/tippy.css"/>\n'
        '<link rel="stylesheet" href="https://unpkg.com/tippy.js@6/themes/light-border.css"/>\n' # For the default theme used by hover_tooltips.js if you keep it
        '<link rel="stylesheet" href="https://unpkg.com/tippy.js@6/animations/shift-away.css"/>\n'
         # Prism CSS (ensure this path is correct or use CDN)
        '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-okaidia.min.css">\n' # Using okaidia theme as an example
        f"{custom_css}\n"
    )
    html_content = html_content.replace("</head>", head_injections + "</head>", 1)

    # Inject Tippy.js, Popper.js, Prism.js and custom HTML/JS before closing body
    body_prepend_scripts = (
        '<script src="https://unpkg.com/@popperjs/core@2"></script>\n'
        '<script src="https://unpkg.com/tippy.js@6"></script>\n'
        '<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>\n'
        '<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-sql.min.js"></script>\n'
         # Autoloader is good if you might use more languages with Prism
        '<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins/autoloader/prism-autoloader.min.js"></script>\n'

    )
    body_injection = body_prepend_scripts + custom_html_elements + "\n" + custom_js + "\n</body>"
    html_content = html_content.replace("</body>", body_injection, 1)
    
    return html_content


def inject_html_doctype(html_content: str) -> str:
    doctype = "<!DOCTYPE html>"
    if not html_content.strip().startswith(doctype):
        return doctype + "\n" + html_content
    return html_content

# Removed inject_sql_code_highlighting as its parts are now integrated into inject_controls_and_styles

def draw_pyvis_html(
    edges: List[Tuple[str, str]],
    node_types: Dict[str, Dict[str, str]],
    auto_open: bool = False,
    save_path: str = "",
    file_name: str = "",
    draw_edgeless: bool = False,
    focus_nodes: List[str] = [],
    is_focused_view: bool = False,
) -> Union[str, None]:
    print(f"Generating Pyvis HTML{' (focused view)' if is_focused_view else ' (complete view)'}...")
    G: Union[nx.DiGraph, nx.Graph] = nx.DiGraph()
    G.add_edges_from(edges)
    valid_nodes = list(node_types.keys())
    if draw_edgeless:
        G.add_nodes_from(valid_nodes)
    else:
        nodes_in_edges = set(u for u, v in edges) | set(v for u, v in edges)
        # nodes_to_draw = nodes_in_edges.union(set(valid_nodes)) # This might be too broad if valid_nodes includes nodes not in edges

        if nodes_in_edges:
            nodes_to_draw = nodes_in_edges if not draw_edgeless else nodes_in_edges.union(set(valid_nodes))
        else:
            nodes_to_draw = set(valid_nodes) if draw_edgeless else set()

        if not nodes_to_draw:
            print("Warning: No nodes to draw for Pyvis HTML.")
            # Create an empty graph but still generate HTML for UI consistency
            G = nx.DiGraph()
            # return None
        else:
            G = G.subgraph(list(nodes_to_draw)).copy() # Ensure it's a list for subgraph

    final_node_types = {
        node: node_types.get(
            node, {"type": "unknown", "database": "", "full_name": node}
        )
        for node in G.nodes()
    }
    # Allow empty graph generation for UI consistency
    # if not G.nodes():
    #     print("Warning: Graph is empty for Pyvis HTML.")
    #     return None

    shake_dir = is_focused_view
    html_file_name_part = "focused_data_flow_pyvis" if is_focused_view else "data_flow_pyvis"
    html_file_name = f"{html_file_name_part}{('_' + file_name) if file_name else ''}.html"
    html_file_path = os.path.join(save_path, html_file_name)

    fig, initial_options_dict = create_pyvis_figure(
        G, final_node_types, focus_nodes, shake_towards_roots=shake_dir
    )
    
    # Generate base HTML from Pyvis
    # fig.show(html_file_path) # This writes the file directly, we want to modify content first
    # html_content_from_pyvis = ""
    # with open(html_file_path, "r", encoding="utf-8") as f:
    #     html_content_from_pyvis = f.read()
    # For more direct control, use generate_html() if available and suitable
    html_content_from_pyvis = fig.generate_html()


    export_file_name_identifier = f"{html_file_name_part}{('_' + file_name) if file_name else ''}"
    
    modified_html_content = inject_controls_and_styles(
        html_content_from_pyvis, initial_options_dict, export_file_name_identifier
    )
    modified_html_content = inject_html_doctype(modified_html_content)
    # SQL highlighting injection is now part of inject_controls_and_styles

    try:
        with open(html_file_path, "w", encoding="utf-8") as file:
            file.write(modified_html_content)
        resolved_html_file_path = Path(html_file_path).resolve()
        print(f"Successfully generated Pyvis HTML: {resolved_html_file_path}")
        if auto_open:
            try:
                print("Opening in default browser...")
                webbrowser.open(f"file://{resolved_html_file_path}")
            except Exception as e:
                print(f"Could not open browser automatically: {e}")
                print(f"Please open this URL manually: file://{resolved_html_file_path}")
    except Exception as e:
        print(f"Error writing Pyvis HTML file {html_file_path}: {e}")
        return None # Return None on failure
    
    return modified_html_content # Return content for testing or further processing