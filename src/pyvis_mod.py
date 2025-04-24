import os
from pathlib import Path
import re
import networkx as nx
from typing import List, Tuple, Dict, Optional, Union
from pyvis.network import Network
import json
import textwrap
import plotly.graph_objects as go  # Added import for Plotly graph objects
import math  # For ceiling function


def create_pyvis_figure(
    graph: Union[nx.DiGraph, nx.Graph], # DO NOT EDIT THIS LINE
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
        cdn_resources="in_line", # Use 'local' if you want offline files
    )

    # Calculate degrees for sizing
    in_degrees = dict(graph.in_degree()) # type: ignore
    out_degrees = dict(graph.out_degree()) # type: ignore
    degrees = {
        node: in_degrees.get(node, 0) + out_degrees.get(node, 0)
        for node in graph.nodes()
    }
    max_degree = max(degrees.values()) if degrees else 1
    min_size, max_size = 15, 45 # Node size range
    epsilon = 1e-6 # Small value to avoid division by zero
    for node in graph.nodes():
        node_degree = degrees.get(node, 0)
        # Scale size logarithmically or linearly - linear used here
        size = min_size + (node_degree / (max_degree + epsilon)) * (max_size - min_size)
        # Ensure size doesn't exceed max_size (can happen if max_degree is 0)
        size = min(size, max_size)

        #print(node, node_degree, size)  # Debugging output
        # Get node info - use fallback if somehow missing (shouldn't happen)
        node_info = node_types.get(node, {"type": "unknown", "database": "", "full_name": node})
        node_type = node_info.get("type", "unknown") # Use .get for safety
        #print(node_info)  # Debugging output
        # Color mapping
        color_map = {
            "view": "#4e79a7",     # Blue
            "table": "#59a14f",     # Green
            "cte_view": "#f9c846",  # Yellow for CTE views
            "unknown": "#e15759",   # Red (Should be less common now)
            "datamarket": "#ed7be7", # Purple (Example)
            "other": "#f28e2c"      # Orange (Example)
        }
        color = color_map.get(node_type, "#bab0ab") # Default grey for unmapped types

        border_color = "#2b2b2b" # Darker border
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

        # Create hover text (tooltip)
        hover_text = (
            f"{node_info['full_name']}\n"
            f"--------------------\n"
            f"Type: {node_type}\n"
            f"Database: {node_info['database'] or '(default)'}\n"
            f"Connections: {node_degree}\n"
            f"--------------------\n"
            f"Parents ({len(parents)}):\n" +
            ("\n".join(f"  • {p}" for p in parents) if parents else "  (None)") +
            "\n\n" +
            f"Children ({len(children)}):\n" +
            ("\n".join(f"  • {c}" for c in children) if children else "  (None)")
        )

        # Add node to pyvis network
        nt.add_node(
            node, # Node ID (base name)
            label=node, # Label displayed on the node
            color=color,
            shape="dot", # Circle shape
            size=size,
            borderWidth=border_width,
            borderColor=border_color,
            font={
                "color": font_color,
                "size": 12,
                "strokeWidth": 0, # No text stroke
                # "strokeColor": "#ffffff", # Not needed if strokeWidth is 0
                "align": "center",
            },
            title=hover_text, # HTML tooltip content
            mass=1 + node_degree / (max_degree + epsilon) * 2, # Influence physics
            fixed=False, # Allow physics engine to move node
        )

    # Add edges to pyvis network
    for u, v in graph.edges():
        if u in graph.nodes() and v in graph.nodes(): # Ensure both nodes exist in the graph
            nt.add_edge(
                u,
                v,
                color={
                    "color": "#cccccc",       # Light grey edge
                    "opacity": 0.7,
                    "highlight": "#e60049",   # Red highlight color
                    "hover": "#e60049",       # Red hover color
                },
                width=1.5,                # Default edge width
                hoverWidth=2.5,           # Width on hover
                selectionWidth=2.5,       # Width when selected
                # Smooth edges look better for hierarchical usually
                smooth={
                    "enabled": True,
                    "type": "cubicBezier",
                    "forceDirection": "vertical", # Changed for better hierarchical flow sometimes
                    "roundness": 0.4
                },
                arrows={"to": {"enabled": True, "scaleFactor": 0.6}}, # Arrow pointing to target
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
    min_height = 2000
    # --- 1. Custom CSS (Same as before, includes loading overlay) ---
    custom_css = textwrap.dedent("""
    <style type="text/css">
        @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css');
        html, body {
            height: 100vh; /* Ensure parents can provide percentage height */
            min-height: 1150px; /* << SET YOUR DESIRED MINIMUM HEIGHT HERE >> */
            /*min-width: 1000px; << SET YOUR DESIRED MINIMUM HEIGHT HERE >> */
            margin: 0;
            padding: 0;
            overflow: hidden; /* Consider 'auto' if internal scrollbars are sometimes okay */
            font-family: sans-serif;
        }
        #mynetwork {
            position: absolute;
            top: 0;
            left: 0;
            right: 0; /* Controlled by JS panel */
            bottom: 0;
            transition: right 0.3s ease;
            border: 1px solid lightgray; /* Optional border */

            /* --- Key Height/Width Settings --- */
            min-height: 1140px;  /*<< SET YOUR DESIRED MINIMUM HEIGHT FOR THE GRAPH HERE >> */
            /*min-width: 1000px;  << SET YOUR DESIRED MINIMUM HEIGHT HERE >> */
            height: 99vh; /* Ensure parents can provide percentage height */
            width: 100%;       /* Take available width (panel JS might adjust 'right') */
            background-color: #ffffff; /* Ensure background covers area */
        }
        .vis-network {
            outline: none;
            /* Ensure vis-network itself doesn't constrain height unnecessarily */
            height: 100% !important;
            width: 100% !important;
        }
        /* Hide the loading bar with CSS but keep it in the DOM */
        #loadingBar { opacity: 0.35; }
        .control-panel { position: fixed; top: 0; right: 0; height: 100vh; width: 300px; background: rgba(248, 248, 248, 0.98); box-shadow: -3px 0 8px rgba(0,0,0,0.15); transform: translateX(100%); transition: transform 0.3s ease; z-index: 1001; font-size: 13px; color: #333; display: flex; flex-direction: column; }
        .control-panel.expanded { transform: translateX(0); }
        .panel-tab { 
            position: absolute; 
            left: -40px; 
            top: 40px; 
            width: 40px; 
            height: 40px; 
            background: rgba(248, 248, 248, 0.9); 
            border-radius: 8px 0 0 8px; 
            box-shadow: -2px 2px 6px rgba(0,0,0,0.1); 
            cursor: pointer; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            color: #555; 
            border: 1px solid #ddd; 
            border-right: none; 
        }
        .panel-tab:hover { background-color: #eee; }
        .panel-tab i { transition: transform 0.3s ease; }
        .panel-tab .hamburger-icon {
            width: 20px;
            height: 16px;
            position: relative;
            margin: 0 auto;
        }
        .panel-tab .hamburger-icon span {
            display: block;
            position: absolute;
            height: 2px;
            width: 100%;
            background: #555;
            border-radius: 2px;
            opacity: 1;
            left: 0;
            transform: rotate(0deg);
            transition: .25s ease-in-out;
        }
        .panel-tab .hamburger-icon span:nth-child(1) { top: 0px; }
        .panel-tab .hamburger-icon span:nth-child(2) { top: 7px; }
        .panel-tab .hamburger-icon span:nth-child(3) { top: 14px; }
        .control-panel.expanded .panel-tab .hamburger-icon span:nth-child(1) {
            top: 7px;
            transform: rotate(135deg);
        }
        .control-panel.expanded .panel-tab .hamburger-icon span:nth-child(2) {
            opacity: 0;
            left: -60px;
        }
        .control-panel.expanded .panel-tab .hamburger-icon span:nth-child(3) {
            top: 7px;
            transform: rotate(-135deg);
        }
        .panel-header { padding: 10px 15px; border-bottom: 1px solid #ddd; font-weight: bold; font-size: 15px; color: #444; text-align: center; flex-shrink: 0; }
        .panel-content { padding: 10px 15px; flex-grow: 1; overflow-y: auto; }
        .control-group { margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px dotted #ccc; }
        .control-group:last-child { border-bottom: none; }
        .control-group h3 { margin: 0 0 10px; font-size: 12px; color: #666; text-transform: uppercase; border-bottom: 1px solid #eee; padding-bottom: 4px; }
        .control-item { margin-bottom: 6px; display: flex; align-items: center; justify-content: space-between; }
        .control-item label, .control-item span { font-size: 12px; color: #444; margin-right: 6px; flex-shrink: 0; max-width: 100px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .control-item select, .control-item input[type="number"], .control-item input[type="range"] { flex-grow: 1; padding: 4px 6px; font-size: 12px; border: 1px solid #ccc; border-radius: 3px; max-width: 150px; box-sizing: border-box; }
        .control-item input[type="range"] { padding: 0; height: 18px; }
        .control-item .value-display { font-size: 11px; color: #777; min-width: 30px; text-align: right; }
        .control-button { display: block; width: 100%; padding: 8px 10px; margin: 8px 0; background-color: #007bff; color: white; border: none; border-radius: 4px; text-align: center; cursor: pointer; font-size: 14px; transition: background-color 0.2s ease; }
        .control-button:hover { background-color: #0056b3; }
        .control-button.secondary { background-color: #6c757d; }
        .control-button.secondary:hover { background-color: #5a6268; }
        .control-button i { margin-right: 8px; }
        .switch-container { display: flex; align-items: center; justify-content: space-between; margin: 5px 0; }
        .switch-container label.text-label { font-size: 12px; color: #444; margin-right: 10px; }
        .switch { position: relative; display: inline-block; width: 38px; height: 20px; flex-shrink: 0; }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #ccc; transition: .3s; border-radius: 20px; }
        .slider:before { position: absolute; content: ""; height: 14px; width: 14px; left: 3px; bottom: 3px; background-color: white; transition: .3s; border-radius: 50%; }
        input:checked + .slider { background-color: #66bb6a; }
        input:checked + .slider:before { transform: translateX(18px); }
        .legend { position: absolute; bottom: 15px; left: 15px; background: rgba(255, 255, 255, 0.9); padding: 10px 15px; border-radius: 6px; box-shadow: 0 2px 5px rgba(0,0,0,0.15); z-index: 1000; }
        .legend-item { display: flex; align-items: center; margin-bottom: 6px; } .legend-item:last-child { margin-bottom: 0; }
        .legend-color { width: 15px; height: 15px; margin-right: 8px; border-radius: 3px; border: 1px solid #ccc; }
        .legend-label { font-size: 13px; color: #555; }
        div.vis-tooltip { font-family: monospace; white-space: pre-wrap; padding: 8px; background-color: #fff; border: 1px solid #ccc; box-shadow: 2px 2px 6px rgba(0,0,0,0.1); border-radius: 4px; max-width: 350px; color: #333; }
        #loadingOverlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(200, 200, 200, 0.6); z-index: 1002; display: none; justify-content: center; align-items: center; font-size: 1.5em; color: #333; text-align: center; }
        #loadingOverlay .spinner { border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin-bottom: 15px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
                                 
        /* --- NEW: Selection Overlay and Rectangle Styles --- */
        #selectionOverlay {
            position: absolute;
            top: 0; left: 0; width: 100%; height: 100%;
            background-color: rgba(0, 100, 255, 0.1); /* Light blue semi-transparent */
            z-index: 1005; /* Above network, below controls maybe */
            cursor: crosshair;
            display: none; /* Hidden by default */
        }
        #selectionRectangle {
            position: absolute;
            border: 1px dashed #007bff; /* Blue dashed border */
            background-color: rgba(0, 100, 255, 0.05); /* Very light blue fill */
            pointer-events: none; /* Allow clicks to pass through */
            display: none; /* Hidden initially */
        }

        /* Export Choice Modal Styles (Updated button styles) */
        #exportChoiceModal {
            position: fixed; left: 50%; top: 50%; transform: translate(-50%, -50%);
            background-color: white; padding: 25px; border: 1px solid #ccc;
            border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            z-index: 1010; display: none; text-align: center; font-size: 14px;
        }
        #exportChoiceModal h4 { margin-top: 0; margin-bottom: 15px; font-size: 16px; color: #333; }
        #exportChoiceModal button { padding: 8px 15px; margin: 5px; cursor: pointer; border: 1px solid #ccc; border-radius: 4px; min-width: 120px; /* Slightly wider */ }
        /* SVG is now the primary (green) button */
        #exportChoiceModal button.export-svg { background-color: #28a745; color: white; border-color: #28a745; }
        #exportChoiceModal button.export-svg:hover { background-color: #218838; }
        /* PNG is now secondary (blue, matching general button) */
        #exportChoiceModal button.export-png { background-color: #007bff; color: white; border-color: #007bff; }
        #exportChoiceModal button.export-png:hover { background-color: #0056b3; }
        #exportChoiceModal button.export-cancel { background-color: #f8f9fa; color: #333; } /* Consistent cancel style */
        #exportChoiceModal button.export-cancel:hover { background-color: #e2e6ea; }
        
        /* --- NEW: Search Panel Styles --- */
        #searchIcon {
            position: fixed;
            top: 15px;
            right: 15px;
            width: 40px;
            height: 40px;
            background: rgba(255, 255, 255, 0.85);
            border-radius: 50%;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 1001;
            transition: background-color 0.2s;
        }
        
        #searchIcon:hover {
            background-color: #f0f0f0;
        }
        
        #searchIcon i {
            color: #555;
            font-size: 18px;
        }
        
        #searchPanel {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            background: rgba(250, 250, 250, 0.92);
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            padding: 15px;
            z-index: 1002;
            transform: translateY(-100%);
            transition: transform 0.3s ease;
            display: flex;
            flex-direction: column;
        }
        
        #searchPanel.expanded {
            transform: translateY(0);
        }
        
        .search-header {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .search-header h3 {
            margin: 0;
            flex-grow: 1;
            font-size: 16px;
            color: #333;
        }
        
        .search-header .close-search {
            background: none;
            border: none;
            color: #777;
            cursor: pointer;
            font-size: 20px;
            padding: 5px;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background-color 0.2s;
        }
        
        .search-header .close-search:hover {
            color: #333;
            background-color: rgba(0, 0, 0, 0.05);
        }
        
        .search-container {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .search-input-container {
            position: relative;
            flex-grow: 1;
            margin-right: 10px;
        }
        
        #searchInput {
            width: 100%;
            padding: 8px 10px 8px 35px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 14px;
            spellcheck: false;
        }
        
        .search-input-icon {
            position: absolute;
            left: 10px;
            top: 50%;
            transform: translateY(-50%);
            color: #777;
        }
        
        .search-options {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 10px;
        }
        
        .search-option {
            display: flex;
            align-items: center;
        }
        
        .search-option label {
            margin-left: 5px;
            font-size: 13px;
            color: #555;
        }
        
        .search-navigation {
            display: flex;
            align-items: center;
            margin-top: 5px;
        }
        
        .search-count {
            flex-grow: 1;
            font-size: 13px;
            color: #555;
        }
        
        .search-nav-buttons {
            display: flex;
            gap: 5px;
        }
        
        .search-nav-button {
            background: #f5f5f5;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 5px 10px;
            cursor: pointer;
            font-size: 12px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }
        
        .search-nav-button:hover {
            background: #e9e9e9;
        }
        
        .search-nav-button i {
            margin-right: 4px;
        }
        
        .search-nav-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .search-results-info {
            font-size: 13px;
            color: #666;
            margin: 5px 0;
        }
        
        /* Node highlighting styles */
        .search-highlight {
            border: 2px solid #ff5722 !important;
            box-shadow: 0 0 10px rgba(255, 87, 34, 0.5);
        }
        
        .search-highlight-current {
            border: 3px solid #e91e63 !important;
            box-shadow: 0 0 15px rgba(233, 30, 99, 0.7);
        }
        
        .search-dimmed {
            opacity: 0.25;
        }
        
        #searchStatus {
            font-size: 13px;
            color: #666;
            margin-top: 5px;
            min-height: 20px;
        }
        
        /* Keyboard shortcut hint */
        .shortcut-hint {
            color: #888;
            font-size: 11px;
            margin-left: 10px;
        }
        
        .search-keyboard-shortcuts {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
            border-top: 1px solid #eee;
            padding-top: 5px;
        }
        
        .keyboard-shortcut {
            display: inline-block;
            background: #f5f5f5;
            border: 1px solid #ddd;
            border-radius: 3px;
            padding: 2px 5px;
            margin: 0 2px;
            font-family: monospace;
        }
    </style>
    """)

    # --- 2. Custom HTML ---
    # (Use the same dynamic generation logic as before)
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
            html += f'<input type="range" id="{key_path}" min="0" max="1" step="0.01" value="{value}">' \
                    f'<span class="value-display" id="{key_path}_value">{value:.2f}</span>'
        elif key_path == "nodes.size":
            # Add a slider for node size with a reasonable range
            html += f'<input type="range" id="{key_path}" min="5" max="100" step="1" value="{value}">' \
                    f'<span class="value-display" id="{key_path}_value">{value}</span>'
        elif key_path == "nodes.scaling.min":
            html += f'<input type="range" id="{key_path}" min="1" max="100" step="1" value="{value}">' \
                    f'<span class="value-display" id="{key_path}_value">{value}</span>'
        elif key_path == "nodes.scaling.max":
            html += f'<input type="range" id="{key_path}" min="1" max="1000" step="1" value="{value}">' \
                    f'<span class="value-display" id="{key_path}_value">{value}</span>'
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

    # --- 3. Custom JavaScript ---
    initial_options_json = json.dumps(initial_options)
    export_file_name_base = f"{file_name if file_name else 'network_export'}"

    custom_js = textwrap.dedent(f"""
    <script type="text/javascript">
        const initialNetworkOptions = {initial_options_json};
        let isPanelExpanded = false;
        const panelWidth = 300; // Match CSS
        let loadingTimeout = null; // For fallback hide timer
        const baseFileName = "{export_file_name_base}"; // Use the python-generated base name

        // --- Selection State Variables ---
        let isSelecting = false;
        let selectionStartX = 0;
        let selectionStartY = 0;
        let selectionRect = {{ x: 0, y: 0, width: 0, height: 0 }}; // Store selection rect relative to overlay
        let selectionCanvasCoords = null; // To store converted canvas coordinates

        // --- DOM Elements ---
        let selectionOverlay = null;
        let selectionRectangle = null;
        let exportChoiceModal = null;
        
        // --- Search Variables ---
        let searchPanel = null;
        let searchInput = null;
        let searchResultCount = null;
        let searchStatus = null;
        let prevSearchResultBtn = null;
        let nextSearchResultBtn = null;
        let currentSearchQuery = "";
        let currentSearchResults = [];
        let currentSearchResultIndex = -1;
        let searchFuseInstance = null;
        let isSearchPanelOpen = false;

        // --- Function to hide loading bar ---
        function hideLoadingBar() {{
            const loadingBar = document.getElementById('loadingBar');
            if (loadingBar) {{
                loadingBar.style.display = 'none';
                console.log("Loading bar hidden by timer");
            }}
        }}
        
        // Set up a recurring timer to hide the loading bar every 10 seconds
        setInterval(hideLoadingBar, 10000);
        
        // Also hide it when it reaches 100%
        function setupLoadingBarObserver() {{
            // Find the loading bar element
            const loadingBar = document.getElementById('loadingBar');
            if (!loadingBar) {{
                console.warn("Loading bar element not found");
                return;
            }}
            
            // Setup mutation observer to watch for text content or style changes
            const observer = new MutationObserver((mutations) => {{
                mutations.forEach((mutation) => {{
                    // Check if the loading bar text is 100%
                    const textElement = loadingBar.querySelector('#text');
                    const bar = loadingBar.querySelector('#bar');
                    
                    if ((textElement && textElement.textContent === '100%') || 
                        (bar && bar.style.width === '100%')) {{
                        hideLoadingBar();
                    }}
                }});
            }});
            
            // Observe both attribute changes and child content
            observer.observe(loadingBar, {{ 
                attributes: true, 
                childList: true, 
                subtree: true, 
                attributeFilter: ['style'] 
            }});
            
            console.log("Loading bar observer set up");
            
            // Hide loading bar immediately to start
            hideLoadingBar();
        }}

        // --- Loading Overlay Functions ---
        function showLoadingOverlay() {{
            const overlay = document.getElementById('loadingOverlay');
            if (overlay) {{ overlay.style.display = 'flex'; }}
            clearTimeout(loadingTimeout);
            loadingTimeout = setTimeout(hideLoadingOverlay, 15000); // Increase safety timeout to 15s
             console.log("Loading overlay shown.");
        }}
        function hideLoadingOverlay() {{
            clearTimeout(loadingTimeout);
            const overlay = document.getElementById('loadingOverlay');
            if (overlay) {{ overlay.style.display = 'none'; }}
            console.log("Loading overlay hidden.");
        }}

// --- Panel Toggle ---
        function togglePanel() {{
             const panel = document.getElementById('controlPanel'); 
             const networkContainer = document.getElementById('mynetwork');
             
             if (!panel) {{
                 console.error("Control panel element not found");
                 return;
             }}
             
             isPanelExpanded = !isPanelExpanded;
             panel.classList.toggle('expanded');
             
             if (networkContainer) {{
                 networkContainer.style.right = isPanelExpanded ? panelWidth + 'px' : '0px';
             }}
             
             // No need to update icon classes as we're now using the hamburger-icon spans
             // that are styled with CSS based on the panel's expanded state
         }}

        // --- Search Panel Toggle ---
        function toggleSearchPanel() {{
            searchPanel = document.getElementById('searchPanel');
            if (!searchPanel) return;
            
            isSearchPanelOpen = !isSearchPanelOpen;
            searchPanel.classList.toggle('expanded', isSearchPanelOpen);
            
            if (isSearchPanelOpen) {{
                // Focus the search input
                searchInput = document.getElementById('searchInput');
                if (searchInput) {{
                    searchInput.focus();
                    initializeSearch();
                }}
            }} else {{
                // Clear search when closing
                clearSearch();
            }}
        }}
        
        function closeSearchPanel() {{
            searchPanel = document.getElementById('searchPanel');
            if (!searchPanel) return;
            
            searchPanel.classList.remove('expanded');
            isSearchPanelOpen = false;
            
            // Clear highlights when closing
            clearSearch();
        }}
        
        function initializeSearch() {{
            if (!searchInput) {{
                searchInput = document.getElementById('searchInput');
            }}
            
            if (!searchResultCount) {{
                searchResultCount = document.getElementById('searchResultCount');
            }}
            
            if (!searchStatus) {{
                searchStatus = document.getElementById('searchStatus');
            }}
            
            if (!prevSearchResultBtn) {{
                prevSearchResultBtn = document.getElementById('prevSearchResult');
            }}
            
            if (!nextSearchResultBtn) {{
                nextSearchResultBtn = document.getElementById('nextSearchResult');
            }}
            
            // Set up event listeners for search input
            if (searchInput && !searchInput.onkeyup) {{
                searchInput.addEventListener('keyup', function(e) {{
                    // Check for special key events (Enter, Escape)
                    if (e.key === 'Enter') {{
                        if (e.shiftKey) {{
                            navigateSearchResult(-1); // Shift+Enter = Previous
                        }} else {{
                            navigateSearchResult(1); // Enter = Next
                        }}
                        return;
                    }}
                    
                    if (e.key === 'Escape') {{
                        closeSearchPanel();
                        return;
                    }}
                    
                    // For other keys, update search
                    const query = searchInput.value.trim();
                    if (query !== currentSearchQuery) {{
                        performSearch(query);
                    }}
                }});
            }}
            
            // Initialize Fuse.js if not already done
            initializeSearchEngine();
        }}
        
        function initializeSearchEngine() {{
            // Only initialize if network is ready and we don't already have an instance
            if (network && network.body && !searchFuseInstance) {{
                const nodes = network.body.data.nodes.get() || [];
                if (!nodes.length) {{
                    if (searchStatus) searchStatus.textContent = "No nodes available for search.";
                    return;
                }}
                
                // Load Fuse.js if not already loaded
                if (typeof Fuse === 'undefined') {{
                    const fusejsScript = document.createElement('script');
                    fusejsScript.src = 'https://cdn.jsdelivr.net/npm/fuse.js@7.1.0';
                    fusejsScript.onload = () => {{
                        console.log("Fuse.js library loaded");
                        createFuseInstance(nodes);
                    }};
                    fusejsScript.onerror = (err) => {{
                        console.error("Failed to load Fuse.js:", err);
                        if (searchStatus) searchStatus.textContent = "Search engine failed to load.";
                    }};
                    document.head.appendChild(fusejsScript);
                }} else {{
                    createFuseInstance(nodes);
                }}
            }}
        }}
        
        function createFuseInstance(nodes) {{
            // Transform nodes for better searching
            const searchableNodes = nodes.map(node => {{
                // Get tooltip data (to extract database, type info)
                const fullDetails = extractInfoFromTooltip(node.title || "");
                return {{
                    id: node.id,
                    label: node.label || node.id,
                    ...fullDetails
                }};
            }});
            
            // Create Fuse instance with appropriate options
            searchFuseInstance = new Fuse(searchableNodes, {{
                keys: [
                    'label',
                    'fullName',
                    'type',
                    'database'
                ],
                includeScore: true,
                threshold: 0.4,
                ignoreLocation: true,
                useExtendedSearch: true
            }});
            
            if (searchStatus) searchStatus.textContent = "Search engine ready.";
        }}
        
        function extractInfoFromTooltip(tooltipHtml) {{
            // Parse tooltip content to extract useful info
            // This handles tooltip format from our node generation
            const info = {{
                fullName: "",
                type: "unknown",
                database: "",
                connections: 0
            }};
            
            if (!tooltipHtml) return info;
            
            try {{
                // Split by newlines to extract the different sections
                const lines = tooltipHtml.split('\\n');
                
                // First line should be full name
                if (lines.length > 0) {{
                    info.fullName = lines[0].trim();
                }}
                
                // Try to match Type
                const typeMatch = tooltipHtml.match(/Type: ([^\\n]+)/i);
                if (typeMatch && typeMatch[1]) {{
                    info.type = typeMatch[1].trim();
                }}
                
                // Try to match Database
                const dbMatch = tooltipHtml.match(/Database: ([^\\n]+)/i);
                if (dbMatch && dbMatch[1]) {{
                    info.database = dbMatch[1].trim();
                    // Handle "(default)" placeholder
                    if (info.database === "(default)") {{
                        info.database = "default";
                    }}
                }}
                
                // Try to match Connections count
                const conMatch = tooltipHtml.match(/Connections: (\\d+)/i);
                if (conMatch && conMatch[1]) {{
                    info.connections = parseInt(conMatch[1].trim(), 10);
                }}
            }} catch (e) {{
                console.warn("Error parsing tooltip data:", e);
            }}
            
            return info;
        }}
        
        function performSearch(query) {{
            currentSearchQuery = query;
            
            // Clear previous results
            currentSearchResults = [];
            currentSearchResultIndex = -1;
            
            // Reset UI initially
            resetSearchHighlights();
            updateSearchResultUI();
            
            // If query is empty, just clear everything
            if (!query) {{
                return;
            }}
            
            if (!network || !network.body) {{
                if (searchStatus) searchStatus.textContent = "Network not ready for search.";
                return;
            }}
            
            // Initialize search engine if needed
            if (!searchFuseInstance) {{
                initializeSearchEngine();
                // If it's still not available, show error message
                if (!searchFuseInstance) {{
                    if (searchStatus) searchStatus.textContent = "Search engine initializing...";
                    return;
                }}
            }}
            
            // Get search options from UI
            const isCaseSensitive = document.getElementById('searchCaseSensitive')?.checked || false;
            const isFuzzy = document.getElementById('searchFuzzy')?.checked || false;
            
            // Adjust Fuse.js search options based on UI settings
            const searchOptions = {{}};
            if (!isFuzzy) {{
                // For exact matching
                searchOptions.threshold = 0.0;
            }} else {{
                // For fuzzy matching
                searchOptions.threshold = 0.4;
            }}
            
            if (isCaseSensitive) {{
                searchOptions.ignoreCase = false;
            }} else {{
                searchOptions.ignoreCase = true;
            }}
            
            // Perform search with Fuse
            const searchResults = searchFuseInstance.search(query, searchOptions);
            currentSearchResults = searchResults.map(result => result.item.id);
            
            // Update UI with results
            if (currentSearchResults.length > 0) {{
                currentSearchResultIndex = 0; // Start with first result
                highlightSearchResults();
                updateSearchResultUI();
                focusOnCurrentResult();
            }} else {{
                if (searchStatus) searchStatus.textContent = "No matches found for {{query}}";
            }}
        }}
        
        function updateSearchResultUI() {{
            if (searchResultCount) {{
                if (currentSearchResults.length === 0) {{
                    searchResultCount.textContent = "0 results";
                }} else {{
                    searchResultCount.textContent = `${{currentSearchResultIndex + 1}} of ${{currentSearchResults.length}} results`;
                }}
            }}
            
            // Update navigation buttons
            if (prevSearchResultBtn) {{
                prevSearchResultBtn.disabled = currentSearchResults.length === 0 || currentSearchResultIndex <= 0;
            }}
            
            if (nextSearchResultBtn) {{
                nextSearchResultBtn.disabled = currentSearchResults.length === 0 || currentSearchResultIndex >= currentSearchResults.length - 1;
            }}
        }}
        
        function navigateSearchResult(direction) {{
            if (currentSearchResults.length === 0) return;
            
            // Calculate new index, wrap around if needed
            let newIndex = currentSearchResultIndex + direction;
            
            if (newIndex < 0) {{
                newIndex = currentSearchResults.length - 1;
            }} else if (newIndex >= currentSearchResults.length) {{
                newIndex = 0;
            }}
            
            currentSearchResultIndex = newIndex;
            
            // Highlight current result in a different color
            highlightSearchResults();
            updateSearchResultUI();
            focusOnCurrentResult();
        }}
        
        function focusOnCurrentResult() {{
            if (currentSearchResults.length === 0 || currentSearchResultIndex < 0) return;
            
            const nodeId = currentSearchResults[currentSearchResultIndex];
            
            // Get network options
            const options = {{
                scale: 1.2,
                offset: {{ x: 0, y: 0 }},
                animation: {{
                    duration: 500,
                    easingFunction: 'easeInOutQuad'
                }}
            }};
            
            // Focus/zoom on the node
            network.focus(nodeId, options);
            
            // Select the node
            network.selectNodes([nodeId]);
        }}
        
        function highlightSearchResults() {{
            if (!network || !network.body) return;
            
            // Reset all node appearances
            resetSearchHighlights();
            
            // Get search options
            const shouldHighlightAll = document.getElementById('searchHighlightAll')?.checked || false;
            const shouldDimOthers = document.getElementById('searchDimOthers')?.checked || false;
            
            if (currentSearchResults.length === 0) {{
                return; // Nothing to highlight
            }}
            
            // Get all nodes for dimming (if needed)
            const nodeIds = network.body.nodeIndices;
            
            // First handle dimming all non-matching nodes
            if (shouldDimOthers) {{
                for (const nodeId of nodeIds) {{
                    if (!currentSearchResults.includes(nodeId)) {{
                        const node = network.body.nodes[nodeId];
                        node.setOptions({{ opacity: 0.25 }}); // Make non-matching nodes transparent
                    }}
                }}
            }}
            
            // Highlight matching nodes
            if (shouldHighlightAll) {{
                // Highlight all matching results
                for (const nodeId of currentSearchResults) {{
                    const node = network.body.nodes[nodeId];
                    if (node) {{
                        const isCurrentResult = nodeId === currentSearchResults[currentSearchResultIndex];
                        const borderWidth = isCurrentResult ? 3 : 2;
                        const borderColor = isCurrentResult ? "#e91e63" : "#ff5722"; // Current = pink, others = orange
                        node.setOptions({{
                            borderWidth: borderWidth,
                            borderColor: borderColor,
                            opacity: 1.0 // Ensure visible even if dimming is on
                        }});
                    }}
                }}
            }} else {{
                // Only highlight current result
                const nodeId = currentSearchResults[currentSearchResultIndex];
                const node = network.body.nodes[nodeId];
                if (node) {{
                    node.setOptions({{
                        borderWidth: 3,
                        borderColor: "#e91e63", // Pink
                        opacity: 1.0
                    }});
                }}
            }}
            
            // Redraw network to show highlights
            network.redraw();
        }}
        
        function resetSearchHighlights() {{
            if (!network || !network.body) return;
            
            // Reset node appearances to original
            const nodeIds = network.body.nodeIndices;
            for (const nodeId of nodeIds) {{
                const node = network.body.nodes[nodeId];
                if (node) {{
                    node.setOptions({{
                        borderWidth: undefined, // Reset to default from options
                        borderColor: undefined, // Reset to default from options
                        opacity: 1.0 // Reset opacity
                    }});
                }}
            }}
            
            // Clear search status
            if (searchStatus) searchStatus.textContent = "";
            
            // Redraw network
            network.redraw();
        }}
        
        function clearSearch() {{
            // Clear search input
            if (searchInput) {{
                searchInput.value = "";
            }}
            
            // Reset search variables
            currentSearchQuery = "";
            currentSearchResults = [];
            currentSearchResultIndex = -1;
            
            // Reset node appearances
            resetSearchHighlights();
            
            // Update UI
            updateSearchResultUI();
            
            // Clear any node selection
            if (network) {{
                network.unselectAll();
            }}
        }}
        
        // --- Setup global keyboard shortcuts ---
        function setupKeyboardShortcuts() {{
            document.addEventListener('keydown', function(e) {{
                // Check if we should ignore the event (input fields, etc.)
                if (shouldIgnoreKeyboardEvent(e)) return;
                
                // Ctrl+F for search
                if ((e.ctrlKey || e.metaKey) && e.key === 'f') {{
                    e.preventDefault(); // Prevent browser's find
                    toggleSearchPanel();
                }}
                
                // Escape to close search panel
                if (e.key === 'Escape' && isSearchPanelOpen) {{
                    closeSearchPanel();
                }}
                
                // Navigation in search results
                if (isSearchPanelOpen && currentSearchResults.length > 0) {{
                    if (e.key === 'Enter') {{
                        e.preventDefault();
                        
                        if (e.shiftKey) {{
                            navigateSearchResult(-1); // Previous
                        }} else {{
                            navigateSearchResult(1); // Next
                        }}
                    }}
                }}
            }});
        }}
        
        function shouldIgnoreKeyboardEvent(e) {{
            // Ignore keyboard events when typing in input elements
            const target = e.target;
            const tagName = target.tagName.toLowerCase();
            
            if (tagName === 'input' || tagName === 'textarea' || tagName === 'select') {{
                return true;
            }}
            
            // Ignore events with contentEditable elements
            if (target.isContentEditable) {{
                return true;
            }}
            
            return false;
        }}

        // --- Helper to get value from UI element ---
        function getElementValue(elementId) {{
             const el = document.getElementById(elementId); if (!el) return undefined;
             if (el.type === 'checkbox') return el.checked;
             if (el.type === 'range' || el.type === 'number') {{
                 // Special handling for avoidOverlap: always parse as float
                 if (elementId === 'physics.hierarchicalRepulsion.avoidOverlap') {{
                     return parseFloat(el.value);
                 }}
                 return el.valueAsNumber;
             }}
             return el.value;
        }}

        // --- Nested Property Helper ---
         function setNestedProperty(obj, path, value) {{
             const keys = path.split('.'); let current = obj;
             for (let i = 0; i < keys.length - 1; i++) {{ current = current[keys[i]] = current[keys[i]] || {{}}; }}
             current[keys[keys.length - 1]] = value;
         }}
         
         // --- Helper to update value display for sliders ---
        function updateValueDisplay(rangeInputId, value) {{
            const displayElement = document.getElementById(rangeInputId + '_value'); if (displayElement) {{ displayElement.textContent = Number.isFinite(parseFloat(value)) ? parseFloat(value).toFixed(2) : value; }}
        }}

        // --- Apply Settings Button Logic ---
        function applyUISettings() {{
            if (!network || !network.setOptions) {{ console.error("Network not ready."); return; }}
            console.log("Applying UI settings...");
            showLoadingOverlay();

            const currentOptions = {{}};
            const controlElements = document.querySelectorAll('.control-panel [id]');
            controlElements.forEach(el => {{
                if (el.id && el.id !== 'loadingOverlay' && el.id !== 'controlPanel' && (el.tagName === 'INPUT' || el.tagName === 'SELECT')) {{
                    const optionPath = el.id; const value = getElementValue(el.id);
                    if (value !== undefined) {{ setNestedProperty(currentOptions, optionPath, value); }}
                }}
            }});

            console.log("Applying options:", JSON.stringify(currentOptions, null, 2));
            try {{
                setTimeout(() => {{ // Short delay for overlay
                    network.setOptions(currentOptions);
                    if (currentOptions.physics?.enabled || currentOptions.layout?.hierarchical?.enabled) {{
                        console.log("Stabilizing network after applying changes...");
                        network.stabilize(); // Stabilization event will hide overlay
                    }} else {{
                        console.log("Redrawing network (no stabilization needed)...");
                        network.redraw();
                        hideLoadingOverlay(); // Hide manually if not stabilizing
                    }}
                }}, 50);
            }} catch (error) {{
                console.error("Error applying settings:", error, "Attempted options:", currentOptions);
                hideLoadingOverlay();
            }}
        }}

        // --- Reset Function ---
        function resetToInitialOptions() {{
             if (!network || !network.setOptions) {{ console.error("Network not ready."); return; }}
             console.log("Resetting to initial options...");
             showLoadingOverlay();

            // Reset UI elements FIRST
             const controlElements = document.querySelectorAll('.control-panel [id]');
             controlElements.forEach(el => {{
                  if (el.id && (el.tagName === 'INPUT' || el.tagName === 'SELECT')) {{
                     const optionPath = el.id; let initialValue = initialNetworkOptions;
                     try {{ optionPath.split('.').forEach(k => {{ initialValue = initialValue[k]; }}); }} catch (e) {{ initialValue = undefined; }}
                     if (initialValue !== undefined) {{
                         if (el.type === 'checkbox') {{ el.checked = initialValue; }}
                         else if (el.type === 'range') {{ el.value = initialValue; updateValueDisplay(el.id, initialValue); }}
                         else {{ el.value = initialValue; }}
                     }} }}
             }});

             // Apply initial options to the network
             setTimeout(() => {{
                 try {{
                    network.setOptions(initialNetworkOptions);
                    console.log("Stabilizing network after reset...");
                    network.stabilize(); // Stabilization event will hide overlay
                 }} catch (error) {{
                     console.error("Error resetting options:", error);
                     hideLoadingOverlay();
                 }}
             }}, 50);
        }}


        // --- SVG Generation (Mostly unchanged, added basic error checking) ---
        async function generateNetworkSVG(cropArea = null) {{
            console.log("Generating SVG representation...", cropArea ? "for selection" : "for full network");
            if (!network || !network.body || !network.getPositions) {{
                console.error("Network object or required components not available.");
                throw new Error("Network not ready for SVG export.");
            }}

            const nodeIds = network.body.nodeIndices;
            const edgeIds = network.body.edgeIndices;
            const positions = network.getPositions();

            // Determine bounding box
            let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
            let hasContent = false; // Flag to check if there's anything to draw

            nodeIds.forEach(nodeId => {{
                 const node = network.body.nodes[nodeId];
                 if (!node || node.options.hidden || !positions[nodeId]) return;
                 const pos = positions[nodeId];
                 const size = (node.options.size || 10) * 2; // diameter
                 const borderWidth = (node.options.borderWidth || 1) * 2; // consider border width on both sides
                 const extent = size / 2 + borderWidth / 2;

                 // If cropping, only consider nodes within the crop area
                 if (cropArea && (pos.x < cropArea.x || pos.x > cropArea.x + cropArea.width || pos.y < cropArea.y || pos.y > cropArea.y + cropArea.height)) {{
                     // Basic check, could be refined to check intersection instead of center point only
                     return;
                 }}

                 minX = Math.min(minX, pos.x - extent);
                 maxX = Math.max(maxX, pos.x + extent);
                 minY = Math.min(minY, pos.y - extent);
                 maxY = Math.max(maxY, pos.y + extent);
                 hasContent = true;
             }});

             // If cropping, adjust bounds to the selection area
             if (cropArea) {{
                 minX = cropArea.x;
                 minY = cropArea.y;
                 maxX = cropArea.x + cropArea.width;
                 maxY = cropArea.y + cropArea.height;
             }} else if (!hasContent) {{ // Handle empty network case for full export
                minX = -100; minY = -100; maxX = 100; maxY = 100; // Default non-zero size
             }} else {{
                 // Add padding for full export only if there's content
                 const padding = 50;
                 minX -= padding;
                 minY -= padding;
                 maxX += padding;
                 maxY += padding;
             }}

             const width = maxX - minX;
             const height = maxY - minY;

             if (width <= 0 || height <= 0) {{
                 console.warn("Calculated network bounds are zero or negative. Using default size.");
                 minX = -200; minY = -200; maxX = 200; maxY = 200;
                 width = 400; height = 400;
             }}

             const svgNS = "http://www.w3.org/2000/svg";
             const svg = document.createElementNS(svgNS, "svg");
             svg.setAttribute("xmlns", svgNS);
             svg.setAttribute("viewBox", `${{minX}} ${{minY}} ${{width}} ${{height}}`);
             svg.setAttribute("width", width); // Set physical size for better rendering
             svg.setAttribute("height", height);
             svg.style.backgroundColor = "#ffffff";
             svg.setAttribute("shape-rendering", "geometricPrecision");

            // Define marker for arrowheads (unchanged)
             const defs = document.createElementNS(svgNS, "defs");
             const marker = document.createElementNS(svgNS, "marker");
             marker.setAttribute("id", "arrowhead");
             marker.setAttribute("viewBox", "-5 -5 10 10");
             marker.setAttribute("refX", "6"); // Adjusted slightly
             marker.setAttribute("refY", "0");
             marker.setAttribute("markerWidth", "6");
             marker.setAttribute("markerHeight", "6");
             marker.setAttribute("orient", "auto-start-reverse");
             const arrowPath = document.createElementNS(svgNS, "path");
             arrowPath.setAttribute("d", "M -5 -5 L 5 0 L -5 5 z");
             marker.appendChild(arrowPath);
             defs.appendChild(marker);
             svg.appendChild(defs);


             // Draw Edges
             const edgesGroup = document.createElementNS(svgNS, "g");
             edgesGroup.setAttribute("id", "edges");
             edgeIds.forEach(edgeId => {{
                 const edge = network.body.edges[edgeId];
                 if (!edge || edge.options.hidden || !edge.fromId || !edge.toId) return; // Skip invalid edges
                 const fromNode = network.body.nodes[edge.fromId];
                 const toNode = network.body.nodes[edge.toId];
                 if (!fromNode || !toNode || !positions[edge.fromId] || !positions[edge.toId]) return;

                 const fromPos = positions[edge.fromId];
                 const toPos = positions[edge.toId];

                 // Basic check if edge is within cropArea (can be improved for curve intersections)
                 if (cropArea) {{
                    const roughlyInside = (p) => p.x >= cropArea.x && p.x <= cropArea.x + cropArea.width && p.y >= cropArea.y && p.y <= cropArea.y + cropArea.height;
                    if (!roughlyInside(fromPos) && !roughlyInside(toPos)) {{
                        // More sophisticated check needed for edges crossing the boundary
                        // For simplicity, only drawing edges whose endpoints are roughly inside
                        // A better approach involves clipping paths, which is complex.
                       // return; // Skipped for simplicity, draw all for now and let viewBox clip
                    }}
                 }}


                 const edgeOptions = edge.options;
                 const path = document.createElementNS(svgNS, "path");
                 let pathD = `M ${{fromPos.x}} ${{fromPos.y}}`;

                 if (edgeOptions.smooth && edgeOptions.smooth.enabled && edgeOptions.smooth.type === 'cubicBezier') {{
                    const dx = toPos.x - fromPos.x;
                    const roundnessFactor = edgeOptions.smooth.roundness != null ? edgeOptions.smooth.roundness : 0.5;
                    const controlPointOffset = dx * roundnessFactor * 0.5;
                    const cp1x = fromPos.x + controlPointOffset;
                    const cp1y = fromPos.y;
                    const cp2x = toPos.x - controlPointOffset;
                    const cp2y = toPos.y;
                    pathD += ` C ${{cp1x}} ${{cp1y}}, ${{cp2x}} ${{cp2y}}, ${{toPos.x}} ${{toPos.y}}`;
                 }} else {{
                    pathD += ` L ${{toPos.x}} ${{toPos.y}}`;
                 }}

                 path.setAttribute("d", pathD);
                 const color = (edgeOptions.color && edgeOptions.color.color) || "#cccccc";
                 const opacity = (edgeOptions.color && edgeOptions.color.opacity != null) ? edgeOptions.color.opacity : 0.6;
                 const width = edgeOptions.width || 1.5;

                 path.setAttribute("stroke", color);
                 path.setAttribute("stroke-width", width);
                 path.setAttribute("stroke-opacity", opacity);
                 path.setAttribute("fill", "none");

                 if (edgeOptions.arrows && edgeOptions.arrows.to && edgeOptions.arrows.to.enabled) {{
                     path.setAttribute("marker-end", "url(#arrowhead)");
                     const markerPath = marker.querySelector('path');
                     if (markerPath) {{
                         markerPath.setAttribute("fill", color);
                     }}
                 }}

                 edgesGroup.appendChild(path);
             }});
             svg.appendChild(edgesGroup);

             // Draw Nodes
            const nodesGroup = document.createElementNS(svgNS, "g");
            nodesGroup.setAttribute("id", "nodes");
            nodeIds.forEach(nodeId => {{
                const node = network.body.nodes[nodeId];
                if (!node || node.options.hidden || !positions[nodeId]) return;

                const pos = positions[nodeId];

                // Skip node if outside crop area
                if (cropArea && (pos.x < cropArea.x || pos.x > cropArea.x + cropArea.width || pos.y < cropArea.y || pos.y > cropArea.y + cropArea.height)) {{
                    // Again, simple check. Could improve by checking if any part of the node overlaps.
                   // return; // Skipped for simplicity, draw all for now and let viewBox clip
                }}


                const nodeOptions = node.options;
                const size = nodeOptions.size || 10;
                const radius = size; // Assuming 'dot' shape
                const borderWidth = nodeOptions.borderWidth || 1;
                const color = (nodeOptions.color && nodeOptions.color.background) || "#97C2FC";
                const borderColor = nodeOptions.borderColor || (nodeOptions.color && nodeOptions.color.border) || color;

                const shape = document.createElementNS(svgNS, "circle");
                shape.setAttribute("cx", pos.x);
                shape.setAttribute("cy", pos.y);
                shape.setAttribute("r", radius);
                shape.setAttribute("fill", color);
                shape.setAttribute("stroke", borderColor);
                shape.setAttribute("stroke-width", borderWidth);
                nodesGroup.appendChild(shape);

                if (nodeOptions.label && nodeOptions.font) {{
                    const text = document.createElementNS(svgNS, "text");
                    text.setAttribute("x", pos.x);
                    text.setAttribute("y", pos.y);
                    text.setAttribute("text-anchor", "middle");
                    text.setAttribute("dominant-baseline", "central");
                    text.setAttribute("font-family", nodeOptions.font.face || "arial");
                    text.setAttribute("font-size", nodeOptions.font.size || 12);
                    text.setAttribute("fill", nodeOptions.font.color || "#343434");
                    text.setAttribute("text-rendering", "geometricPrecision");


                    const labelLines = String(nodeOptions.label).split('\\n');
                     if (labelLines.length > 1) {{
                         const fontSize = nodeOptions.font.size || 12;
                         const approxLineHeightFactor = 1.2; // Adjust as needed
                         const totalLabelHeight = fontSize * labelLines.length * approxLineHeightFactor;
                         const startY = pos.y - totalLabelHeight / 2 + fontSize * 0.6; // Rough vertical centering

                         labelLines.forEach((line, index) => {{
                             const tspan = document.createElementNS(svgNS, "tspan");
                             tspan.setAttribute("x", pos.x);
                             tspan.setAttribute("dy", index === 0 ? startY - pos.y : fontSize * approxLineHeightFactor);
                             tspan.textContent = line;
                             text.appendChild(tspan);
                         }});
                     }} else {{
                         text.textContent = nodeOptions.label;
                     }}

                    nodesGroup.appendChild(text);
                }}
            }});
            svg.appendChild(nodesGroup);

            console.log("SVG generation complete.");
            return new XMLSerializer().serializeToString(svg);
        }}

        // --- PNG Export Function (handles selection or full) ---
        async function exportToPNG(selection = null, qualityScaleFactor = 1.5) {{
             const exportType = selection ? `selection (Scale: ${{qualityScaleFactor}})` : `full network (Scale: ${{qualityScaleFactor}})`;
             console.log(`High-quality PNG export started for ${{exportType}}...`);
             if (!network || !network.body) {{
                 console.error("Network not ready for PNG export.");
                 alert("Error: Network not ready");
                 return;
             }}

             showLoadingOverlay(`Generating PNG for ${{selection ? 'selection' : 'full network'}}...`);

             try {{
                 // 1. Generate SVG (pass null for cropArea if it's a full export)
                 const svgCropArea = selection ? {{
                     x: selection.x,
                     y: selection.y,
                     width: selection.width,
                     height: selection.height
                 }} : null;
                 const svgString = await generateNetworkSVG(svgCropArea);

                 // 2. Get dimensions from SVG viewBox
                 const svgMatch = svgString.match(/viewBox="([^"]+)"/);
                 const viewBox = svgMatch ? svgMatch[1].split(' ').map(Number) : [0, 0, 600, 600];
                 const svgWidth = viewBox[2];
                 const svgHeight = viewBox[3];

                 if (svgWidth <= 0 || svgHeight <= 0) {{
                     throw new Error("Invalid SVG dimensions calculated for PNG export.");
                 }}

                 // 3. Create high-resolution canvas
                 const dpr = window.devicePixelRatio || 1;
                 const scale = dpr * qualityScaleFactor;
                 const canvas = document.createElement('canvas');
                 canvas.width = Math.round(svgWidth * scale);
                 canvas.height = Math.round(svgHeight * scale);
                 const ctx = canvas.getContext('2d');

                 ctx.imageSmoothingEnabled = true;
                 ctx.imageSmoothingQuality = 'high';

                 ctx.fillStyle = '#FFFFFF';
                 ctx.fillRect(0, 0, canvas.width, canvas.height);

                 // 4. Render SVG onto the canvas
                 const img = new Image();
                 const blob = new Blob([svgString], {{ type: 'image/svg+xml;charset=utf-8' }});
                 const url = URL.createObjectURL(blob);

                 await new Promise((resolve, reject) => {{
                     img.onload = () => {{
                         console.log("SVG loaded, drawing to PNG canvas...");
                         try {{
                            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                            URL.revokeObjectURL(url);
                            console.log("PNG Canvas drawing complete.");
                            resolve();
                         }} catch (drawError) {{
                            URL.revokeObjectURL(url);
                             console.error("Error drawing SVG to canvas:", drawError);
                             reject(new Error("Failed to draw SVG onto canvas."));
                         }}
                     }};
                     img.onerror = (err) => {{
                         URL.revokeObjectURL(url);
                         console.error("Error loading SVG into image for PNG export:", err);
                         reject(new Error("Failed to load SVG for PNG rendering."));
                     }};
                     img.src = url;
                 }});

                 // 5. Save the canvas as PNG
                 const link = document.createElement('a');
                 const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
                 const fileNameSuffix = selection ? '_selection_' + timestamp : '_full_' + timestamp;
                 link.download = `${{baseFileName}}${{fileNameSuffix}}.png`;
                 link.href = canvas.toDataURL('image/png'); // Ensure this step happens after drawImage completes
                 link.click();

                 console.log(`PNG export successful for ${{exportType}}.`);
                 hideLoadingOverlay();

             }} catch (error) {{
                 console.error(`PNG export failed for ${{exportType}}:`, error);
                 alert(`Error saving PNG (${{exportType}}): ` + error.message);
                 hideLoadingOverlay();
             }}
        }}

        // --- SVG Export Function (handles selection or full) ---
        async function exportToSVG(selection = null) {{
            const exportType = selection ? "selection" : "full network";
            console.log(`SVG export started for ${{exportType}}...`);
            if (!network || !network.body) {{
                console.error("Network not ready for SVG export.");
                alert("Error: Network not ready");
                return;
            }}
            showLoadingOverlay(`Generating SVG for ${{selection ? 'selection' : 'full network'}}...`);

            try {{
                const svgCropArea = selection ? {{
                     x: selection.x,
                     y: selection.y,
                     width: selection.width,
                     height: selection.height
                 }} : null;
                const svgString = await generateNetworkSVG(svgCropArea);

                const blob = new Blob([svgString], {{ type: 'image/svg+xml;charset=utf-8' }});
                const link = document.createElement('a');
                link.href = URL.createObjectURL(blob);
                 const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
                 const fileNameSuffix = selection ? '_selection_' + timestamp : '_full_' + timestamp;
                 link.download = `${{baseFileName}}${{fileNameSuffix}}.svg`;
                link.click();

                setTimeout(() => URL.revokeObjectURL(link.href), 100); // Cleanup

                console.log(`SVG export successful for ${{exportType}}.`);
                hideLoadingOverlay();

            }} catch (error) {{
                console.error(`SVG export failed for ${{exportType}}:`, error);
                alert(`Error saving SVG (${{exportType}}): ` + error.message);
                hideLoadingOverlay();
            }}
        }}

        // --- Functions to trigger FULL network exports ---
        function saveFullNetworkPNG(qualityScaleFactor = 1.5) {{
            exportToPNG(null, qualityScaleFactor);
        }}
        function saveFullNetworkSVG() {{
            exportToSVG(null);
        }}


        // --- Selection Mode Functions ---
        function startSelectionMode() {{
            if (!network) {{ alert("Network not ready."); return; }}
            console.log("Starting selection mode...");
            selectionOverlay = document.getElementById('selectionOverlay');
            selectionRectangle = document.getElementById('selectionRectangle');
            exportChoiceModal = document.getElementById('exportChoiceModal');

            if (!selectionOverlay || !selectionRectangle || !exportChoiceModal) {{
                console.error("Selection UI elements not found.");
                return;
            }}

            selectionOverlay.style.display = 'block';
            exportChoiceModal.style.display = 'none'; // Hide export choice initially
            selectionRectangle.style.display = 'none';
            isSelecting = false;
            selectionCanvasCoords = null; // Reset previous selection

             // Add event listeners for selection
             selectionOverlay.addEventListener('mousedown', handleMouseDown);
             selectionOverlay.addEventListener('mousemove', handleMouseMove);
             selectionOverlay.addEventListener('mouseup', handleMouseUp);
             selectionOverlay.addEventListener('mouseleave', handleMouseLeave); // Cancel if mouse leaves
        }}

        function cancelSelectionMode() {{
            console.log("Cancelling selection mode...");
            if (selectionOverlay) {{
                selectionOverlay.style.display = 'none';
                selectionOverlay.removeEventListener('mousedown', handleMouseDown);
                selectionOverlay.removeEventListener('mousemove', handleMouseMove);
                selectionOverlay.removeEventListener('mouseup', handleMouseUp);
                selectionOverlay.removeEventListener('mouseleave', handleMouseLeave);
            }}
            if (selectionRectangle) {{
                selectionRectangle.style.display = 'none';
            }}
             if (exportChoiceModal) {{
                exportChoiceModal.style.display = 'none';
            }}
            isSelecting = false;
            selectionCanvasCoords = null;
        }}

        function handleMouseDown(event) {{
            if (event.button !== 0) return; // Only left click
            isSelecting = true;
            selectionStartX = event.clientX;
            selectionStartY = event.clientY;
            const rect = selectionOverlay.getBoundingClientRect(); // Get overlay position
            selectionRect.x = event.clientX - rect.left;
            selectionRect.y = event.clientY - rect.top;
            selectionRect.width = 0;
            selectionRect.height = 0;
            selectionRectangle.style.left = selectionRect.x + 'px';
            selectionRectangle.style.top = selectionRect.y + 'px';
            selectionRectangle.style.width = '0px';
            selectionRectangle.style.height = '0px';
            selectionRectangle.style.display = 'block';
            event.preventDefault(); // Prevent text selection, etc.
        }}

        function handleMouseMove(event) {{
            if (!isSelecting) return;
            const rect = selectionOverlay.getBoundingClientRect();
            const currentX = event.clientX - rect.left;
            const currentY = event.clientY - rect.top;

            selectionRect.width = currentX - selectionRect.x;
            selectionRect.height = currentY - selectionRect.y;

            // Adjust for dragging in different directions
            let displayX = selectionRect.x;
            let displayY = selectionRect.y;
            let displayWidth = selectionRect.width;
            let displayHeight = selectionRect.height;

            if (selectionRect.width < 0) {{
                displayX = currentX;
                displayWidth = -selectionRect.width;
            }}
            if (selectionRect.height < 0) {{
                displayY = currentY;
                displayHeight = -selectionRect.height;
            }}

            selectionRectangle.style.left = displayX + 'px';
            selectionRectangle.style.top = displayY + 'px';
            selectionRectangle.style.width = displayWidth + 'px';
            selectionRectangle.style.height = displayHeight + 'px';
        }}

         function handleMouseUp(event) {{
             if (!isSelecting) return;
             isSelecting = false;
             selectionRectangle.style.display = 'none'; // Hide rectangle after selection
             selectionOverlay.style.display = 'none'; // Hide overlay

             // Remove overlay listeners immediately
            selectionOverlay.removeEventListener('mousedown', handleMouseDown);
            selectionOverlay.removeEventListener('mousemove', handleMouseMove);
            selectionOverlay.removeEventListener('mouseup', handleMouseUp);
            selectionOverlay.removeEventListener('mouseleave', handleMouseLeave);


             // Final coordinates relative to the overlay
             const rect = selectionOverlay.getBoundingClientRect();
             const finalX = selectionRect.x + rect.left; // Use original start, not event.clientX
             const finalY = selectionRect.y + rect.top;  // Use original start, not event.clientY
             const finalWidth = selectionRect.width;
             const finalHeight = selectionRect.height;

             // Ensure positive width/height
             let startDOMX = finalX;
             let startDOMY = finalY;
             let endDOMX = finalX + finalWidth;
             let endDOMY = finalY + finalHeight;

             if (finalWidth < 0) {{ [startDOMX, endDOMX] = [endDOMX, startDOMX]; }}
             if (finalHeight < 0) {{ [startDOMY, endDOMY] = [endDOMY, startDOMY]; }}

             const absWidth = Math.abs(finalWidth);
             const absHeight = Math.abs(finalHeight);

             // Ignore tiny selections
             if (absWidth < 5 || absHeight < 5) {{
                 console.log("Selection too small, cancelled.");
                 cancelSelectionMode();
                 return;
             }}

             // Convert DOM coordinates to Canvas coordinates
             const startCanvas = network.DOMtoCanvas({{ x: startDOMX, y: startDOMY }});
             const endCanvas = network.DOMtoCanvas({{ x: endDOMX, y: endDOMY }});

             selectionCanvasCoords = {{
                 x: Math.min(startCanvas.x, endCanvas.x),
                 y: Math.min(startCanvas.y, endCanvas.y),
                 width: Math.abs(endCanvas.x - startCanvas.x),
                 height: Math.abs(endCanvas.y - startCanvas.y)
             }};

              console.log("Selection finished. Canvas Coords:", selectionCanvasCoords);

             // Show export choice modal
             if (exportChoiceModal) {{
                 exportChoiceModal.style.display = 'block';
             }} else {{
                 console.error("Export choice modal not found!");
                 cancelSelectionMode(); // Fallback: just cancel if modal is missing
             }}
        }}

        function handleMouseLeave(event) {{
             // If selecting and mouse leaves the area, cancel the selection
             if (isSelecting) {{
                 console.log("Mouse left overlay during selection, cancelling.");
                 cancelSelectionMode();
             }}
         }}

         // --- Trigger Export based on Choice ---
         function exportSelection(format) {{
             exportChoiceModal.style.display = 'none'; // Hide modal

             if (!selectionCanvasCoords) {{
                 console.error("No selection coordinates available for export.");
                 alert("Error: No selection was made.");
                 cancelSelectionMode();
                 return;
             }}

             if (format === 'png') {{
                 exportToPNG(selectionCanvasCoords, 1.5); // Export selection as PNG with 1.5x upscale
             }} else if (format === 'svg') {{
                 exportToSVG(selectionCanvasCoords); // Export selection as SVG
             }} else {{
                 console.error("Unknown export format:", format);
             }}

             // Reset selection state after export attempt
             selectionCanvasCoords = null;
         }}


        // --- Event Listener Setup (Mostly unchanged) ---
         function setupEventListeners() {{
             console.log("Setting up event listeners for controls...");
             document.querySelectorAll('.control-panel input[type="range"]').forEach(input => {{
                 input.oninput = () => updateValueDisplay(input.id, input.value);
             }});
             
             // Setup search-related event listeners
             setupKeyboardShortcuts();
             
             // Setup event listeners for search options
             document.querySelectorAll('.search-option input[type="checkbox"]').forEach(checkbox => {{
                checkbox.addEventListener('change', function() {{
                    // Re-highlight with new settings if we have search results
                    if (currentSearchResults.length > 0) {{
                        highlightSearchResults();
                    }}
                }});
             }});
         }}

        // --- Network Ready & Initialization (Check overlay setup) ---
        let networkReady = false;
        let listenersAttached = false;

        function onNetworkReady() {{
            if (networkReady && !listenersAttached) {{
                setupEventListeners();
                 hideLoadingBar(); // Ensure loading bar is hidden
                listenersAttached = true;
                console.log("Network ready, listeners attached.");

                network.on("stabilizationIterationsDone", () => {{
                    console.log("Stabilization finished.");
                    setTimeout(hideLoadingOverlay, 250);
                    hideLoadingBar();
                }});
                 network.on("stabilizationProgress", (params) => {{ /* Optional logging */ }});
                 // Hide overlay initially, stabilization might be fast or off
                 setTimeout(hideLoadingOverlay, 100); // Hide a bit faster after ready
                 
                 // Initialize search functionality
                 initializeSearchEngine();
            }}
        }}

        document.addEventListener('DOMContentLoaded', () => {{
            console.log("DOM Content Loaded.");
            // Get references to new UI elements
             selectionOverlay = document.getElementById('selectionOverlay');
             selectionRectangle = document.getElementById('selectionRectangle');
             exportChoiceModal = document.getElementById('exportChoiceModal');
             searchPanel = document.getElementById('searchPanel');
             searchInput = document.getElementById('searchInput');
             searchResultCount = document.getElementById('searchResultCount');
             searchStatus = document.getElementById('searchStatus');

            const networkContainer = document.getElementById('mynetwork');
            if(networkContainer) networkContainer.style.right = '0px';

            if (!document.getElementById('loadingOverlay')) {{
                const overlay = document.createElement('div');
                overlay.id = 'loadingOverlay';
                overlay.innerHTML = '<div class="spinner"></div><div>Loading Network...</div>'; // Use spinner class
                overlay.style.cssText = '/* ... loading overlay CSS from style block ... */ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(200, 200, 200, 0.6); z-index: 1002; display: flex; flex-direction: column; justify-content: center; align-items: center; font-size: 1.5em; color: #333; text-align: center;';
                document.body.appendChild(overlay);
            }}
            document.getElementById('loadingOverlay').style.display = 'flex'; // Show initially

            hideLoadingBar(); // Attempt early hide
            setupLoadingBarObserver(); // Set up observer early

            const checkNetworkInterval = setInterval(() => {{
                if (window.network && typeof window.network.on === 'function') {{
                    clearInterval(checkNetworkInterval);
                    networkReady = true;
                    console.log("Network object found.");
                    onNetworkReady();
                }}
            }}, 100);

            setTimeout(() => {{
                clearInterval(checkNetworkInterval);
                if (!networkReady) {{
                    console.warn("Network object failed to initialize within timeout.");
                    hideLoadingOverlay();
                }}
            }}, 15000);
        }});

        window.addEventListener('load', () => {{
            console.log("Window Load event fired.");
            hideLoadingBar();
            if (!networkReady && window.network && typeof window.network.on === 'function') {{
                networkReady = true;
                console.log("Network object found on window.load.");
                onNetworkReady();
            }}
             setTimeout(hideLoadingOverlay, 500); // Ensure overlay is hidden after load
             
             // Add Fuse.js library
             if (typeof Fuse === 'undefined') {{
                try {{
                    const fusejsScript = document.createElement('script');
                    fusejsScript.src = 'https://cdn.jsdelivr.net/npm/fuse.js@7.1.0';
                    fusejsScript.onload = () => console.log("Fuse.js library loaded successfully");
                    fusejsScript.onerror = (err) => console.error("Failed to load Fuse.js:", err);
                    document.head.appendChild(fusejsScript);
                }} catch (e) {{
                    console.error("Error attempting to add Fuse.js:", e);
                }}
             }}
        }});

        // --- Window Resize Handler (Unchanged) ---
        window.addEventListener('resize', () => {{
            clearTimeout(window.resizeTimeout);
            window.resizeTimeout = setTimeout(() => {{
                console.log("Window resized.");
                const networkContainer = document.getElementById('mynetwork');
                if (networkContainer) {{
                    networkContainer.style.right = isPanelExpanded ? panelWidth + 'px' : '0px';
                }}
                if (network?.redraw) {{ network.redraw(); }}
                 if (network?.fit) {{ network.fit({{ animation: false }}); }}
            }}, 250);
        }});
    </script>
    """)
    
    # --- 4. Injection ---
    html_content = html_content.replace("</head>", custom_css + "\n</head>", 1)
    html_content = html_content.replace(
        "</body>", custom_html + "\n" + custom_js + "\n</body>", 1
    )

    return html_content

def inject_html_doctype(html_content: str) -> str:
    """Injects the HTML doctype into the HTML content."""
    doctype = "<!DOCTYPE html>"
    return doctype + "\n" + html_content

def draw_pyvis_html(
    edges: List[Tuple[str, str]],
    node_types: Dict[str, Dict[str, str]],
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

    final_node_types = {node: node_types.get(node, {"type": "unknown", "database": "", "full_name": node}) for node in G.nodes()}
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
    try:
        with open(html_file_path, "w", encoding="utf-8") as file:
            file.write(modified_html_content)
        resolved_html_file_path = Path(html_file_path).resolve()
        print(f"Successfully generated Pyvis HTML: \033]8;;file://{resolved_html_file_path}\033\\{resolved_html_file_path}\033]8;;\033\\")
    except Exception as e:
        print(f"Error writing Pyvis HTML file {html_file_path}: {e}")
