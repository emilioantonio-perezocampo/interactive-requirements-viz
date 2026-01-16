#!/usr/bin/env python3
"""
Interactive Requirements Graph Visualizer
==========================================
Creates an interactive HTML visualization with:
- Zoom/pan/drag
- Hover tooltips with full details
- Click to highlight connections
- Filter by area, priority, version
- Subgraph exploration
- Data table showing visible requirements
"""

import pandas as pd
import networkx as nx
from pyvis.network import Network
import re
import json
from pathlib import Path
from typing import List, Optional
import argparse


# Color palette for areas
AREA_COLORS = {
    'Ingesta': '#4ECDC4',
    'Extracción': '#FF6B6B',
    'Modelo de datos': '#45B7D1',
    'Normalización': '#96CEB4',
    'Transformación': '#96CEB4',
    'Métricas': '#FFD93D',
    'Dataset': '#DDA0DD',
    'Algoritmo': '#98D8C8',
    'Backtest': '#F7DC6F',
    'Reportes': '#BB8FCE',
    'UI/UX': '#85C1E9',
    'Dashboard': '#85C1E9',
    'Seguridad': '#F1948A',
    'Observabilidad': '#ABEBC6',
    'Testing': '#F5B041',
    'DevOps': '#AED6F1',
    'Gobernanza de datos': '#D7BDE2',
    'Gobernanza': '#D7BDE2',
    'Privacidad': '#FADBD8',
    'Documentación': '#D5DBDB',
    'Extensibilidad': '#A9DFBF',
    'Entregables': '#FAD7A0',
    'UX': '#85C1E9',
    'Calidad de datos': '#82E0AA',
    'Auditabilidad': '#F9E79F',
    'Exportación': '#D2B4DE',
    'Reproducibilidad': '#AEB6BF',
    'Performance': '#F5CBA7',
    'Validación de algoritmo': '#76D7C4',
}

PRIORITY_SIZES = {
    'Alta (P0)': 35,
    'Media (P1)': 25,
    'Baja (P2)': 18,
}


def parse_dependencies(dep_str: str) -> List[str]:
    """Parse dependency string into list of requirement IDs."""
    if pd.isna(dep_str) or dep_str == '—' or dep_str.strip() == '':
        return []

    # Handle ranges like RM-001..RM-049
    range_match = re.match(r'RM-(\d+)\.\.RM-(\d+)', dep_str)
    if range_match:
        start, end = int(range_match.group(1)), int(range_match.group(2))
        return [f'RM-{i:03d}' for i in range(start, end + 1)]

    deps = re.findall(r'RM-\d+', dep_str)
    return deps


def load_requirements(csv_path: str) -> pd.DataFrame:
    """Load requirements from CSV file."""
    df = pd.read_csv(csv_path)
    df['parsed_deps'] = df['Dependencias'].apply(parse_dependencies)
    return df


def build_graph(df: pd.DataFrame) -> nx.DiGraph:
    """Build directed graph from requirements dataframe."""
    G = nx.DiGraph()

    for _, row in df.iterrows():
        # Truncate long text for display
        requisito = str(row['Requisito_detallado']) if pd.notna(row['Requisito_detallado']) else 'N/A'
        if len(requisito) > 300:
            requisito = requisito[:300] + '...'

        G.add_node(
            row['ID'],
            area=row['Área'] if pd.notna(row['Área']) else 'Unknown',
            funcionalidad=row['Funcionalidad'] if pd.notna(row['Funcionalidad']) else 'N/A',
            requisito=requisito,
            prioridad=row['Prioridad'] if pd.notna(row['Prioridad']) else 'Media (P1)',
            estatus=row['Estatus'] if pd.notna(row['Estatus']) else 'N/A',
            version=row['Versión_objetivo'] if pd.notna(row['Versión_objetivo']) else 'N/A',
            owner=row['Owner'] if pd.notna(row['Owner']) else 'N/A',
            roles=row['Roles'] if pd.notna(row['Roles']) else 'N/A',
            dependencias=row['Dependencias'] if pd.notna(row['Dependencias']) else '—',
        )

    for _, row in df.iterrows():
        for dep in row['parsed_deps']:
            if dep in G.nodes:
                G.add_edge(dep, row['ID'])

    return G


def calculate_hierarchical_levels(G: nx.DiGraph) -> dict:
    """Calculate proper hierarchical levels for tree layout.

    Root nodes (no incoming edges) get level=0.
    Each child gets level = max(parent_levels) + 1.
    This ensures proper top-down hierarchy in tree visualization.
    """
    levels = {}

    # Handle cycles gracefully - use try/except for topological sort
    try:
        for node in nx.topological_sort(G):
            predecessors = list(G.predecessors(node))
            if not predecessors:
                levels[node] = 0  # Root nodes at level 0 (top)
            else:
                levels[node] = max(levels.get(pred, 0) for pred in predecessors) + 1
    except nx.NetworkXUnfeasible:
        # Graph has cycles - fall back to BFS from roots
        roots = [n for n in G.nodes() if G.in_degree(n) == 0]
        if not roots:
            # No roots found, pick node with lowest in_degree
            roots = [min(G.nodes(), key=lambda n: G.in_degree(n))]

        visited = set()
        queue = [(r, 0) for r in roots]
        while queue:
            node, level = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            levels[node] = max(levels.get(node, 0), level)
            for successor in G.successors(node):
                if successor not in visited:
                    queue.append((successor, level + 1))

        # Assign level 0 to any unvisited nodes
        for node in G.nodes():
            if node not in levels:
                levels[node] = 0

    return levels


def create_interactive_graph(
    G: nx.DiGraph,
    title: str = "Requirements Dependency Graph",
    height: str = "900px",
    width: str = "100%",
    output_path: str = "requirements_graph.html",
    highlight_node: Optional[str] = None,
):
    """Create interactive Pyvis network visualization."""

    # Create Pyvis network
    net = Network(
        height=height,
        width=width,
        directed=True,
        notebook=False,
        bgcolor="#1a1a2e",
        font_color="#ffffff",
        select_menu=False,
        filter_menu=False,
    )

    # Configure physics
    net.set_options("""
    {
        "nodes": {
            "font": {
                "size": 14,
                "face": "arial",
                "strokeWidth": 3,
                "strokeColor": "#1a1a2e"
            },
            "borderWidth": 2,
            "borderWidthSelected": 4,
            "shadow": {
                "enabled": true,
                "color": "rgba(0,0,0,0.5)",
                "size": 10,
                "x": 3,
                "y": 3
            }
        },
        "edges": {
            "color": {
                "color": "#4a4a6a",
                "highlight": "#00ff88",
                "hover": "#00ff88"
            },
            "arrows": {
                "to": {
                    "enabled": true,
                    "scaleFactor": 0.8
                }
            },
            "smooth": {
                "enabled": true,
                "type": "curvedCW",
                "roundness": 0.2
            },
            "width": 1.5,
            "selectionWidth": 3
        },
        "physics": {
            "enabled": true,
            "solver": "forceAtlas2Based",
            "forceAtlas2Based": {
                "gravitationalConstant": -80,
                "centralGravity": 0.01,
                "springLength": 150,
                "springConstant": 0.08,
                "damping": 0.4,
                "avoidOverlap": 0.8
            },
            "stabilization": {
                "enabled": true,
                "iterations": 200,
                "updateInterval": 25
            }
        },
        "interaction": {
            "hover": true,
            "hoverConnectedEdges": true,
            "selectConnectedEdges": true,
            "multiselect": true,
            "dragNodes": true,
            "dragView": true,
            "zoomView": true,
            "navigationButtons": true,
            "keyboard": {
                "enabled": true,
                "speed": {"x": 10, "y": 10, "zoom": 0.1}
            },
            "tooltipDelay": 100
        },
        "configure": {
            "enabled": false
        }
    }
    """)

    # Calculate proper hierarchical levels for tree layout
    node_levels = calculate_hierarchical_levels(G)

    # Add nodes
    for node_id in G.nodes():
        node_data = G.nodes[node_id]
        area = node_data.get('area', 'Unknown')
        priority = node_data.get('prioridad', 'Media (P1)')

        color = AREA_COLORS.get(area, '#888888')
        size = PRIORITY_SIZES.get(priority, 25)

        # Highlight specific node if requested
        if highlight_node and node_id == highlight_node:
            border_color = "#ff0000"
            border_width = 5
        else:
            border_color = "#ffffff"
            border_width = 2

        # Create simple text tooltip
        tooltip = f"{node_id}: {node_data.get('funcionalidad', 'N/A')}"

        net.add_node(
            node_id,
            label=node_id,
            title=tooltip,
            color={
                'background': color,
                'border': border_color,
                'highlight': {'background': color, 'border': '#00ff88'},
                'hover': {'background': color, 'border': '#00ff88'},
            },
            size=size,
            borderWidth=border_width,
            group=area,
            level=node_levels.get(node_id, 0),
        )

    # Add edges
    for source, target in G.edges():
        net.add_edge(source, target)

    # Generate HTML
    net.save_graph(output_path)

    # Inject custom CSS and controls
    inject_custom_controls(output_path, G, title)

    print(f"Interactive graph saved to: {output_path}")
    return output_path


def generate_legend_items(areas):
    """Generate legend HTML items."""
    items = []
    for a in areas:
        color = AREA_COLORS.get(a, "#888")
        item = f'<div class="legend-item" data-area="{a}">'
        item += f'<div class="legend-color" style="background: {color}"></div>'
        item += f'<span>{a}</span></div>'
        items.append(item)
    return ''.join(items)


def inject_custom_controls(html_path: str, G: nx.DiGraph, title: str):
    """Inject custom filtering controls and styles into the HTML."""

    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Get unique values for filters
    areas = sorted(set(G.nodes[n].get('area', 'Unknown') for n in G.nodes()))
    priorities = ['Alta (P0)', 'Media (P1)', 'Baja (P2)']
    versions = sorted(set(G.nodes[n].get('version', 'N/A') for n in G.nodes()))

    # Detect cycles
    try:
        cycles = list(nx.simple_cycles(G))
        has_cycles = len(cycles) > 0
        cycle_nodes = set()
        for cycle in cycles:
            cycle_nodes.update(cycle)
    except:
        has_cycles = False
        cycles = []
        cycle_nodes = set()

    # Build node data for JavaScript (include all fields)
    node_data_js = {}
    for n in G.nodes():
        node_data_js[n] = {
            'area': G.nodes[n].get('area', 'Unknown'),
            'prioridad': G.nodes[n].get('prioridad', 'Media (P1)'),
            'version': G.nodes[n].get('version', 'N/A'),
            'funcionalidad': G.nodes[n].get('funcionalidad', ''),
            'requisito': G.nodes[n].get('requisito', 'N/A'),
            'owner': G.nodes[n].get('owner', 'N/A'),
            'roles': G.nodes[n].get('roles', 'N/A'),
            'estatus': G.nodes[n].get('estatus', 'N/A'),
            'dependencias': G.nodes[n].get('dependencias', '—'),
            'in_degree': G.in_degree(n),
            'out_degree': G.out_degree(n),
            'in_cycle': n in cycle_nodes,
        }

    # Get ancestors and descendants for each node
    subgraph_data = {}
    for n in G.nodes():
        ancestors = list(nx.ancestors(G, n))
        descendants = list(nx.descendants(G, n))
        subgraph_data[n] = {
            'ancestors': ancestors,
            'descendants': descendants,
        }

    custom_css = """
    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Arial, sans-serif;
            background: #1a1a2e;
            overflow: hidden;
        }

        /* Toast notifications */
        .toast-container {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .toast {
            padding: 12px 20px;
            border-radius: 8px;
            color: #fff;
            font-size: 0.9em;
            box-shadow: 0 4px 20px rgba(0,0,0,0.4);
            animation: toastSlideIn 0.3s ease-out;
            display: flex;
            align-items: center;
            gap: 10px;
            max-width: 400px;
        }

        .toast.hiding {
            animation: toastSlideOut 0.3s ease-in forwards;
        }

        @keyframes toastSlideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }

        @keyframes toastSlideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }

        .toast-success { background: linear-gradient(135deg, #00c853 0%, #00a844 100%); }
        .toast-error { background: linear-gradient(135deg, #ff5252 0%, #d32f2f 100%); }
        .toast-warning { background: linear-gradient(135deg, #ffc107 0%, #ff9800 100%); color: #1a1a2e; }
        .toast-info { background: linear-gradient(135deg, #2196f3 0%, #1976d2 100%); }

        .toast-icon { font-size: 1.2em; }

        /* Keyboard shortcuts modal */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.7);
            z-index: 8000;
            display: none;
            justify-content: center;
            align-items: center;
        }

        .modal-overlay.visible {
            display: flex;
        }

        .modal-content {
            background: #16213e;
            border-radius: 12px;
            border: 1px solid #4a4a6a;
            padding: 25px;
            max-width: 500px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 10px 40px rgba(0,0,0,0.5);
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid #4a4a6a;
        }

        .modal-header h2 {
            color: #00ff88;
            margin: 0;
            font-size: 1.2em;
        }

        .modal-close {
            background: none;
            border: none;
            color: #8888aa;
            font-size: 1.5em;
            cursor: pointer;
            padding: 5px;
        }

        .modal-close:hover {
            color: #ffffff;
        }

        .shortcut-row {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #2a2a4a;
        }

        .shortcut-key {
            background: #0f0f23;
            padding: 4px 10px;
            border-radius: 4px;
            font-family: monospace;
            color: #00ff88;
            border: 1px solid #4a4a6a;
        }

        .shortcut-desc {
            color: #cccccc;
        }

        /* Filter chips */
        .filter-chips-container {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            padding: 0 15px 10px 15px;
            min-height: 10px;
        }

        .filter-chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(0,255,136,0.15);
            border: 1px solid rgba(0,255,136,0.3);
            color: #00ff88;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75em;
            animation: chipFadeIn 0.2s ease-out;
        }

        @keyframes chipFadeIn {
            from { transform: scale(0.8); opacity: 0; }
            to { transform: scale(1); opacity: 1; }
        }

        .filter-chip-label {
            color: #8888aa;
        }

        .filter-chip-remove {
            background: none;
            border: none;
            color: #00ff88;
            cursor: pointer;
            padding: 0;
            font-size: 1.1em;
            line-height: 1;
            opacity: 0.7;
        }

        .filter-chip-remove:hover {
            opacity: 1;
        }

        /* Breadcrumb */
        .breadcrumb-bar {
            background: rgba(0,0,0,0.3);
            padding: 10px 15px;
            display: flex;
            align-items: center;
            gap: 10px;
            border-bottom: 1px solid #3a3a5a;
        }

        .breadcrumb-icon {
            color: #8888aa;
        }

        .breadcrumb-text {
            color: #cccccc;
            font-size: 0.85em;
        }

        .breadcrumb-text strong {
            color: #00ff88;
        }

        .breadcrumb-reset {
            background: none;
            border: 1px solid #4a4a6a;
            color: #8888aa;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.75em;
            cursor: pointer;
            margin-left: auto;
        }

        .breadcrumb-reset:hover {
            border-color: #00ff88;
            color: #00ff88;
        }

        /* Search autocomplete */
        .search-container {
            position: relative;
        }

        .autocomplete-dropdown {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: #0f0f23;
            border: 1px solid #4a4a6a;
            border-top: none;
            border-radius: 0 0 6px 6px;
            max-height: 200px;
            overflow-y: auto;
            z-index: 100;
            display: none;
        }

        .autocomplete-dropdown.visible {
            display: block;
        }

        .autocomplete-item {
            padding: 8px 12px;
            cursor: pointer;
            border-bottom: 1px solid #2a2a4a;
        }

        .autocomplete-item:last-child {
            border-bottom: none;
        }

        .autocomplete-item:hover,
        .autocomplete-item.selected {
            background: rgba(0,255,136,0.1);
        }

        .autocomplete-id {
            color: #00ff88;
            font-weight: 600;
        }

        .autocomplete-func {
            color: #8888aa;
            font-size: 0.85em;
            margin-left: 8px;
        }

        /* Main layout */
        .app-container {
            display: flex;
            height: 100vh;
            width: 100vw;
        }

        .left-panel {
            width: 320px;
            min-width: 320px;
            background: linear-gradient(180deg, #16213e 0%, #1a1a2e 100%);
            border-right: 1px solid #4a4a6a;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .graph-panel {
            flex: 1;
            display: flex;
            flex-direction: column;
            position: relative;
        }

        .right-panel {
            width: 400px;
            min-width: 400px;
            background: linear-gradient(180deg, #16213e 0%, #1a1a2e 100%);
            border-left: 1px solid #4a4a6a;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        /* Header */
        .panel-header {
            padding: 15px;
            border-bottom: 1px solid #4a4a6a;
            background: rgba(0,0,0,0.2);
        }

        .panel-header h2 {
            color: #00ff88;
            margin: 0;
            font-size: 1.1em;
            font-weight: 600;
        }

        .app-title {
            color: #00ff88;
            margin: 0 0 5px 0;
            font-size: 1.2em;
            font-weight: 600;
        }

        .app-subtitle {
            color: #8888aa;
            margin: 0;
            font-size: 0.8em;
        }

        /* Controls section */
        .controls-section {
            padding: 15px;
            border-bottom: 1px solid #3a3a5a;
        }

        .controls-section h3 {
            color: #00ff88;
            margin: 0 0 12px 0;
            font-size: 0.95em;
            font-weight: 600;
        }

        .control-row {
            margin-bottom: 12px;
        }

        .control-row:last-child {
            margin-bottom: 0;
        }

        .control-row label {
            display: block;
            color: #8888aa;
            font-size: 0.8em;
            margin-bottom: 5px;
            font-weight: 500;
        }

        .control-row select,
        .control-row input[type="text"] {
            width: 100%;
            background: #0f0f23;
            border: 1px solid #4a4a6a;
            color: #ffffff;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.9em;
        }

        .control-row select:hover,
        .control-row input:hover {
            border-color: #00ff88;
        }

        .control-row select:focus,
        .control-row input:focus {
            outline: none;
            border-color: #00ff88;
            box-shadow: 0 0 10px rgba(0,255,136,0.3);
        }

        /* Buttons */
        .btn {
            background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);
            border: none;
            color: #1a1a2e;
            padding: 10px 16px;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 0.85em;
            width: 100%;
        }

        .btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 15px rgba(0,255,136,0.4);
        }

        .btn-secondary {
            background: #4a4a6a;
            color: #ffffff;
        }

        .btn-secondary:hover {
            background: #5a5a7a;
            box-shadow: none;
        }

        .btn-group {
            display: flex;
            gap: 8px;
            margin-top: 10px;
        }

        .btn-group .btn {
            flex: 1;
        }

        /* Layout toggle */
        .layout-toggle {
            display: flex;
            gap: 0;
            border-radius: 6px;
            overflow: hidden;
            border: 1px solid #4a4a6a;
        }

        .layout-btn {
            flex: 1;
            background: #0f0f23;
            border: none;
            color: #8888aa;
            padding: 10px 14px;
            font-size: 0.85em;
            cursor: pointer;
            transition: all 0.2s;
        }

        .layout-btn:first-child {
            border-right: 1px solid #4a4a6a;
        }

        .layout-btn:hover {
            background: #1a1a3e;
            color: #ffffff;
        }

        .layout-btn.active {
            background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);
            color: #1a1a2e;
            font-weight: 600;
        }

        /* Stats panel */
        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            padding: 15px;
        }

        .stat-box {
            background: rgba(0,0,0,0.2);
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #3a3a5a;
        }

        .stat-label {
            color: #8888aa;
            font-size: 0.75em;
            margin-bottom: 4px;
        }

        .stat-value {
            color: #ffffff;
            font-size: 1.3em;
            font-weight: 600;
        }

        /* Legend */
        .legend-container {
            flex: 1;
            overflow-y: auto;
            padding: 15px;
        }

        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 4px 0;
            cursor: pointer;
            padding: 6px 8px;
            border-radius: 4px;
            transition: background 0.2s;
        }

        .legend-item:hover {
            background: rgba(255,255,255,0.1);
        }

        .legend-color {
            width: 14px;
            height: 14px;
            border-radius: 3px;
            border: 1px solid rgba(255,255,255,0.3);
            flex-shrink: 0;
        }

        .legend-item span {
            color: #cccccc;
            font-size: 0.8em;
        }

        /* Graph container */
        #mynetwork {
            flex: 1;
            background-color: #1a1a2e;
            border: none !important;
        }

        /* Hover tooltip */
        #hover-tooltip {
            position: fixed;
            background: rgba(22, 33, 62, 0.98);
            padding: 15px 18px;
            border-radius: 10px;
            color: #ffffff;
            font-size: 0.85em;
            z-index: 2000;
            border: 1px solid #4a4a6a;
            max-width: 380px;
            pointer-events: none;
            display: none;
            box-shadow: 0 8px 32px rgba(0,0,0,0.5);
        }

        #hover-tooltip h4 {
            margin: 0 0 10px 0;
            color: #00ff88;
            font-size: 1em;
            border-bottom: 1px solid #4a4a6a;
            padding-bottom: 8px;
        }

        .tooltip-row {
            display: flex;
            margin: 5px 0;
            line-height: 1.4;
        }

        .tooltip-label {
            color: #8888aa;
            min-width: 90px;
            font-weight: 500;
            font-size: 0.9em;
        }

        .tooltip-value {
            color: #ffffff;
            flex: 1;
        }

        .tooltip-requisito {
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #4a4a6a;
            line-height: 1.5;
            color: #ccccdd;
            font-size: 0.9em;
        }

        .tooltip-pinned-badge {
            margin-top: 10px;
            padding-top: 8px;
            border-top: 1px solid #4a4a6a;
            color: #00ff88;
            font-size: 0.75em;
            text-align: center;
        }

        #hover-tooltip.pinned {
            border: 2px solid #00ff88;
            box-shadow: 0 8px 32px rgba(0,255,136,0.3);
        }

        /* Data table */
        .table-header {
            padding: 15px;
            border-bottom: 1px solid #4a4a6a;
            background: rgba(0,0,0,0.2);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .table-header h2 {
            color: #00ff88;
            margin: 0;
            font-size: 1em;
        }

        .table-count {
            color: #8888aa;
            font-size: 0.85em;
        }

        .table-container {
            flex: 1;
            overflow: auto;
        }

        .data-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.8em;
        }

        .data-table th {
            background: rgba(0,0,0,0.3);
            color: #8888aa;
            padding: 10px 8px;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
            border-bottom: 1px solid #4a4a6a;
        }

        .data-table td {
            padding: 8px;
            border-bottom: 1px solid #2a2a4a;
            color: #cccccc;
            vertical-align: top;
        }

        .data-table tr:hover td {
            background: rgba(0,255,136,0.05);
        }

        .data-table .id-cell {
            color: #00ff88;
            font-weight: 600;
            white-space: nowrap;
        }

        .data-table .area-cell {
            white-space: nowrap;
        }

        .data-table .func-cell {
            max-width: 200px;
        }

        /* Sortable table headers */
        .data-table th.sortable {
            cursor: pointer;
            user-select: none;
            position: relative;
            padding-right: 20px;
        }

        .data-table th.sortable:hover {
            background: rgba(0,255,136,0.1);
        }

        .data-table th .sort-indicator {
            position: absolute;
            right: 8px;
            opacity: 0.5;
        }

        .data-table th.sort-asc .sort-indicator,
        .data-table th.sort-desc .sort-indicator {
            opacity: 1;
            color: #00ff88;
        }

        .priority-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.85em;
            font-weight: 500;
        }

        .priority-p0 {
            background: rgba(255,107,107,0.2);
            color: #ff6b6b;
        }

        .priority-p1 {
            background: rgba(255,217,61,0.2);
            color: #ffd93d;
        }

        .priority-p2 {
            background: rgba(78,205,196,0.2);
            color: #4ecdc4;
        }

        /* Statistics panel */
        .stats-panel {
            padding: 15px;
            border-bottom: 1px solid #4a4a6a;
            background: rgba(0,0,0,0.2);
        }

        .stats-panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }

        .stats-panel-header h3 {
            color: #00ff88;
            margin: 0;
            font-size: 0.95em;
        }

        .stats-toggle {
            background: none;
            border: none;
            color: #8888aa;
            cursor: pointer;
            font-size: 0.85em;
        }

        .stats-toggle:hover {
            color: #00ff88;
        }

        .stats-content {
            display: grid;
            gap: 15px;
        }

        .stats-content.collapsed {
            display: none;
        }

        .stats-section h4 {
            color: #8888aa;
            font-size: 0.8em;
            margin: 0 0 8px 0;
            font-weight: 500;
        }

        .stats-bar-container {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .stats-bar-row {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.75em;
        }

        .stats-bar-label {
            width: 80px;
            color: #cccccc;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .stats-bar-wrapper {
            flex: 1;
            background: #0f0f23;
            height: 16px;
            border-radius: 3px;
            overflow: hidden;
        }

        .stats-bar {
            height: 100%;
            border-radius: 3px;
            transition: width 0.3s ease;
        }

        .stats-bar-value {
            width: 30px;
            text-align: right;
            color: #8888aa;
        }

        .top-connected-list {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .top-connected-item {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.75em;
            padding: 4px 8px;
            background: rgba(0,0,0,0.2);
            border-radius: 4px;
            cursor: pointer;
        }

        .top-connected-item:hover {
            background: rgba(0,255,136,0.1);
        }

        .top-connected-id {
            color: #00ff88;
            font-weight: 600;
        }

        .top-connected-count {
            color: #8888aa;
            margin-left: auto;
        }

        /* Export buttons */
        .export-section {
            padding: 10px 15px;
            border-bottom: 1px solid #3a3a5a;
            display: flex;
            gap: 8px;
        }

        .btn-export {
            flex: 1;
            background: #2a2a4a;
            border: 1px solid #4a4a6a;
            color: #cccccc;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.8em;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            transition: all 0.2s;
        }

        .btn-export:hover {
            background: #3a3a5a;
            border-color: #00ff88;
            color: #00ff88;
        }

        /* Cycle warning */
        .cycle-warning {
            background: rgba(255,107,107,0.1);
            border: 1px solid rgba(255,107,107,0.3);
            color: #ff6b6b;
            padding: 10px 15px;
            margin: 10px 15px;
            border-radius: 6px;
            font-size: 0.8em;
            display: none;
        }

        .cycle-warning.visible {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .cycle-warning-icon {
            font-size: 1.2em;
        }

        .cycle-warning-text {
            flex: 1;
        }

        .cycle-warning-btn {
            background: none;
            border: 1px solid #ff6b6b;
            color: #ff6b6b;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.85em;
            cursor: pointer;
        }

        .cycle-warning-btn:hover {
            background: rgba(255,107,107,0.2);
        }

        /* Hide pyvis default elements */
        center, h1:empty {
            display: none !important;
        }

        .card {
            border: none !important;
            background: transparent !important;
        }

        /* Scrollbar styling */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }

        ::-webkit-scrollbar-track {
            background: #1a1a2e;
        }

        ::-webkit-scrollbar-thumb {
            background: #4a4a6a;
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #5a5a7a;
        }
    </style>
    """

    # Generate area options
    area_options = ''.join(f'<option value="{a}">{a}</option>' for a in areas)
    priority_options = ''.join(f'<option value="{p}">{p}</option>' for p in priorities)
    version_options = ''.join(f'<option value="{v}">{v}</option>' for v in versions)

    custom_html = f"""
    <div class="toast-container" id="toast-container"></div>

    <!-- Keyboard shortcuts modal -->
    <div class="modal-overlay" id="shortcuts-modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>⌨️ Atajos de Teclado</h2>
                <button class="modal-close" id="modal-close">&times;</button>
            </div>
            <div class="shortcut-row">
                <span class="shortcut-key">?</span>
                <span class="shortcut-desc">Mostrar/ocultar esta ayuda</span>
            </div>
            <div class="shortcut-row">
                <span class="shortcut-key">Esc</span>
                <span class="shortcut-desc">Restablecer vista / cerrar modal</span>
            </div>
            <div class="shortcut-row">
                <span class="shortcut-key">/</span>
                <span class="shortcut-desc">Enfocar campo de búsqueda</span>
            </div>
            <div class="shortcut-row">
                <span class="shortcut-key">R</span>
                <span class="shortcut-desc">Restablecer vista</span>
            </div>
            <div class="shortcut-row">
                <span class="shortcut-key">1</span>
                <span class="shortcut-desc">Disposición de fuerza</span>
            </div>
            <div class="shortcut-row">
                <span class="shortcut-key">2</span>
                <span class="shortcut-desc">Disposición de árbol</span>
            </div>
            <div class="shortcut-row">
                <span class="shortcut-key">A</span>
                <span class="shortcut-desc">Mostrar ancestros (nodo seleccionado)</span>
            </div>
            <div class="shortcut-row">
                <span class="shortcut-key">D</span>
                <span class="shortcut-desc">Mostrar descendientes (nodo seleccionado)</span>
            </div>
            <div class="shortcut-row">
                <span class="shortcut-key">N</span>
                <span class="shortcut-desc">Mostrar vecindario (nodo seleccionado)</span>
            </div>
        </div>
    </div>

    <div class="app-container">
        <!-- Left Panel: Controls -->
        <div class="left-panel">
            <div class="panel-header">
                <h1 class="app-title">📊 {title}</h1>
                <p class="app-subtitle">Grafo interactivo de dependencias <button id="btn-shortcuts" style="background:none;border:none;color:#8888aa;cursor:pointer;font-size:0.9em;padding:2px 6px;" title="Atajos de teclado">⌨️ ?</button></p>
            </div>

            <div class="controls-section">
                <h3>🔍 Buscar Nodo</h3>
                <div class="control-row search-container">
                    <label>ID o texto del Requisito:</label>
                    <input type="text" id="node-search" placeholder="Ej: RM-001, autenticación..." autocomplete="off">
                    <div class="autocomplete-dropdown" id="autocomplete-dropdown"></div>
                </div>
                <button class="btn" id="btn-search">Buscar y Enfocar</button>
            </div>

            <div class="controls-section">
                <h3>🎛️ Filtros</h3>
                <div class="control-row">
                    <label>Área:</label>
                    <select id="area-filter">
                        <option value="">— Todas las áreas —</option>
                        {area_options}
                    </select>
                </div>
                <div class="control-row">
                    <label>Prioridad:</label>
                    <select id="priority-filter">
                        <option value="">— Todas las prioridades —</option>
                        {priority_options}
                    </select>
                </div>
                <div class="control-row">
                    <label>Versión:</label>
                    <select id="version-filter">
                        <option value="">— Todas las versiones —</option>
                        {version_options}
                    </select>
                </div>
            </div>
            <div class="filter-chips-container" id="filter-chips"></div>

            <div class="controls-section">
                <h3>🔗 Explorar Conexiones</h3>
                <p style="color: #8888aa; font-size: 0.8em; margin: 0 0 10px 0;">Primero selecciona un nodo en el grafo</p>
                <div class="btn-group">
                    <button class="btn btn-secondary" id="btn-ancestors">← Dependencias</button>
                    <button class="btn btn-secondary" id="btn-descendants">Dependientes →</button>
                </div>
                <button class="btn btn-secondary" id="btn-neighborhood" style="margin-top: 8px;">Vecindario Completo</button>
            </div>

            <div class="controls-section">
                <h3>📐 Disposición</h3>
                <div class="layout-toggle">
                    <button class="layout-btn active" id="layout-force">Fuerza</button>
                    <button class="layout-btn" id="layout-tree">Árbol</button>
                </div>
            </div>

            <div class="controls-section">
                <button class="btn btn-secondary" id="btn-reset">🔄 Restablecer Vista</button>
            </div>

            <div class="cycle-warning" id="cycle-warning">
                <span class="cycle-warning-icon">⚠️</span>
                <span class="cycle-warning-text">Se detectaron dependencias circulares</span>
                <button class="cycle-warning-btn" id="btn-show-cycles">Ver ciclos</button>
            </div>

            <div class="stats-grid">
                <div class="stat-box">
                    <div class="stat-label">Nodos Visibles</div>
                    <div class="stat-value" id="visible-nodes">{len(G.nodes())}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Conexiones</div>
                    <div class="stat-value" id="visible-edges">{len(G.edges())}</div>
                </div>
            </div>

            <div class="panel-header">
                <h2>🎨 Leyenda de Áreas</h2>
            </div>
            <div class="legend-container">
                {generate_legend_items(areas)}
            </div>
        </div>

        <!-- Center: Graph -->
        <div class="graph-panel">
            <div class="breadcrumb-bar" id="breadcrumb-bar">
                <span class="breadcrumb-icon">📍</span>
                <span class="breadcrumb-text" id="breadcrumb-text">Todos los requisitos (<strong>{len(G.nodes())}</strong>)</span>
                <button class="breadcrumb-reset" id="breadcrumb-reset" style="display:none;">Mostrar todos</button>
            </div>
            <div id="mynetwork"></div>
        </div>

        <!-- Right Panel: Data Table -->
        <div class="right-panel">
            <div class="export-section">
                <button class="btn-export" id="btn-export-png">
                    <span>📷</span> Exportar PNG
                </button>
                <button class="btn-export" id="btn-export-csv">
                    <span>📄</span> Exportar CSV
                </button>
            </div>

            <div class="stats-panel" id="stats-panel">
                <div class="stats-panel-header">
                    <h3>📊 Estadísticas</h3>
                    <button class="stats-toggle" id="stats-toggle">▼</button>
                </div>
                <div class="stats-content" id="stats-content">
                    <div class="stats-section">
                        <h4>Por Prioridad</h4>
                        <div class="stats-bar-container" id="priority-stats"></div>
                    </div>
                    <div class="stats-section">
                        <h4>Top Áreas</h4>
                        <div class="stats-bar-container" id="area-stats"></div>
                    </div>
                    <div class="stats-section">
                        <h4>Más Conectados</h4>
                        <div class="top-connected-list" id="top-connected"></div>
                    </div>
                </div>
            </div>

            <div class="table-header">
                <h2>📋 Requisitos Visibles</h2>
                <span class="table-count" id="table-count">{len(G.nodes())} requisitos</span>
            </div>
            <div class="table-container">
                <table class="data-table" id="data-table">
                    <thead>
                        <tr>
                            <th class="sortable" data-sort="id">ID <span class="sort-indicator">⇅</span></th>
                            <th class="sortable" data-sort="area">Área <span class="sort-indicator">⇅</span></th>
                            <th class="sortable" data-sort="funcionalidad">Funcionalidad <span class="sort-indicator">⇅</span></th>
                            <th class="sortable" data-sort="prioridad">Prioridad <span class="sort-indicator">⇅</span></th>
                            <th class="sortable" data-sort="version">Versión <span class="sort-indicator">⇅</span></th>
                            <th class="sortable" data-sort="connections">Conex. <span class="sort-indicator">⇅</span></th>
                        </tr>
                    </thead>
                    <tbody id="table-body">
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <div id="hover-tooltip"></div>
    """

    # Prepare cycle data for JS
    cycles_js = [list(c) for c in cycles[:10]]  # Limit to first 10 cycles

    custom_js = f"""
    <script>
    (function() {{
        // Data
        const nodeData = {json.dumps(node_data_js, ensure_ascii=False)};
        const subgraphData = {json.dumps(subgraph_data)};
        const areaColors = {json.dumps(AREA_COLORS)};
        const totalNodes = {len(G.nodes())};
        const totalEdges = {len(G.edges())};
        const hasCycles = {str(has_cycles).lower()};
        const cycles = {json.dumps(cycles_js)};
        const cycleNodeCount = {len(cycle_nodes)};

        // State
        let selectedNodeId = null;
        let currentLayout = 'force';
        let visibleNodeIds = new Set(Object.keys(nodeData));
        let currentViewContext = {{ type: 'all', node: null }};
        let sortState = {{ column: 'id', direction: 'asc' }};
        let autocompleteIndex = -1;

        // Toast notification system
        function showToast(message, type = 'info', duration = 3000) {{
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast toast-${{type}}`;
            const icons = {{ success: '✓', error: '✗', warning: '⚠', info: 'ℹ' }};
            toast.innerHTML = `<span class="toast-icon">${{icons[type] || icons.info}}</span><span>${{message}}</span>`;
            container.appendChild(toast);
            setTimeout(() => {{
                toast.classList.add('hiding');
                setTimeout(() => toast.remove(), 300);
            }}, duration);
        }}

        // Wait for network to be ready
        function waitForNetwork(callback) {{
            if (typeof network !== 'undefined' && network) {{
                callback();
            }} else {{
                setTimeout(() => waitForNetwork(callback), 100);
            }}
        }}

        // Initialize when ready
        waitForNetwork(function() {{
            console.log('Network ready, initializing custom controls...');
            initializeApp();
        }});

        function initializeApp() {{
            // Initial renders
            updateTable();
            updateStatsPanel();

            // Bind event handlers
            bindEventHandlers();

            // Setup network event handlers
            setupNetworkHandlers();

            // Setup keyboard shortcuts
            setupKeyboardShortcuts();

            // Setup autocomplete
            setupAutocomplete();

            // Show cycle warning if cycles detected
            if (hasCycles) {{
                document.getElementById('cycle-warning').classList.add('visible');
                showToast(`⚠️ Se detectaron ${{cycles.length}} ciclos de dependencias`, 'warning', 5000);
            }}

            showToast('Visualización cargada correctamente', 'success');
        }}

        function bindEventHandlers() {{
            // Search button
            document.getElementById('btn-search').addEventListener('click', focusNode);

            // Search input enter key
            document.getElementById('node-search').addEventListener('keypress', function(e) {{
                if (e.key === 'Enter') {{
                    const dropdown = document.getElementById('autocomplete-dropdown');
                    if (dropdown.classList.contains('visible') && autocompleteIndex >= 0) {{
                        const items = dropdown.querySelectorAll('.autocomplete-item');
                        if (items[autocompleteIndex]) {{
                            items[autocompleteIndex].click();
                            return;
                        }}
                    }}
                    focusNode();
                }}
            }});

            // Filter dropdowns
            document.getElementById('area-filter').addEventListener('change', applyFilters);
            document.getElementById('priority-filter').addEventListener('change', applyFilters);
            document.getElementById('version-filter').addEventListener('change', applyFilters);

            // Exploration buttons
            document.getElementById('btn-ancestors').addEventListener('click', showAncestors);
            document.getElementById('btn-descendants').addEventListener('click', showDescendants);
            document.getElementById('btn-neighborhood').addEventListener('click', showNeighborhood);

            // Layout buttons
            document.getElementById('layout-force').addEventListener('click', () => setLayout('force'));
            document.getElementById('layout-tree').addEventListener('click', () => setLayout('tree'));

            // Reset button
            document.getElementById('btn-reset').addEventListener('click', resetView);

            // Breadcrumb reset
            document.getElementById('breadcrumb-reset').addEventListener('click', resetView);

            // Legend clicks
            document.querySelectorAll('.legend-item').forEach(item => {{
                item.addEventListener('click', function() {{
                    const area = this.getAttribute('data-area');
                    document.getElementById('area-filter').value = area;
                    applyFilters();
                }});
            }});

            // Export buttons
            document.getElementById('btn-export-png').addEventListener('click', exportPNG);
            document.getElementById('btn-export-csv').addEventListener('click', exportCSV);

            // Stats panel toggle
            document.getElementById('stats-toggle').addEventListener('click', function() {{
                const content = document.getElementById('stats-content');
                const isCollapsed = content.classList.toggle('collapsed');
                this.textContent = isCollapsed ? '▶' : '▼';
            }});

            // Sortable table headers
            document.querySelectorAll('.data-table th.sortable').forEach(th => {{
                th.addEventListener('click', function() {{
                    const column = this.dataset.sort;
                    if (sortState.column === column) {{
                        sortState.direction = sortState.direction === 'asc' ? 'desc' : 'asc';
                    }} else {{
                        sortState.column = column;
                        sortState.direction = 'asc';
                    }}
                    updateSortIndicators();
                    updateTable();
                }});
            }});

            // Keyboard shortcuts modal
            document.getElementById('btn-shortcuts').addEventListener('click', () => {{
                document.getElementById('shortcuts-modal').classList.add('visible');
            }});
            document.getElementById('modal-close').addEventListener('click', () => {{
                document.getElementById('shortcuts-modal').classList.remove('visible');
            }});
            document.getElementById('shortcuts-modal').addEventListener('click', function(e) {{
                if (e.target === this) this.classList.remove('visible');
            }});

            // Cycle warning button
            document.getElementById('btn-show-cycles').addEventListener('click', showCycleNodes);
        }}

        function showCycleNodes() {{
            if (!hasCycles || cycles.length === 0) {{
                showToast('No se encontraron ciclos de dependencias', 'info');
                return;
            }}

            // Get all nodes involved in cycles
            const cycleNodeIds = new Set();
            cycles.forEach(cycle => cycle.forEach(nodeId => cycleNodeIds.add(nodeId)));

            visibleNodeIds = cycleNodeIds;
            currentViewContext = {{ type: 'cycles', count: cycles.length }};
            updateVisibility();
            updateTable();
            updateStats();
            updateBreadcrumb();
            updateStatsPanel();

            // Update breadcrumb manually for cycles
            document.getElementById('breadcrumb-text').innerHTML = `Nodos en ciclos (<strong>${{cycleNodeIds.size}}</strong> nodos, ${{cycles.length}} ciclos)`;
            document.getElementById('breadcrumb-reset').style.display = 'block';

            showToast(`Mostrando ${{cycleNodeIds.size}} nodos involucrados en ${{cycles.length}} ciclos`, 'warning');
        }}

        function setupNetworkHandlers() {{
            // Tooltip element
            const tooltip = document.getElementById('hover-tooltip');
            let tooltipPinned = false;

            // Click handler - pins the tooltip
            network.on('click', function(params) {{
                if (params.nodes.length > 0) {{
                    selectedNodeId = params.nodes[0];
                    showSelectedInfo(selectedNodeId);

                    // Pin the tooltip for clicked node
                    const data = nodeData[selectedNodeId];
                    if (data) {{
                        const color = areaColors[data.area] || '#888888';
                        tooltip.innerHTML = `
                            <h4 style="color: ${{color}}">${{selectedNodeId}}: ${{data.funcionalidad}}</h4>
                            <div class="tooltip-row">
                                <span class="tooltip-label">Área:</span>
                                <span class="tooltip-value">${{data.area}}</span>
                            </div>
                            <div class="tooltip-row">
                                <span class="tooltip-label">Prioridad:</span>
                                <span class="tooltip-value">${{data.prioridad}}</span>
                            </div>
                            <div class="tooltip-row">
                                <span class="tooltip-label">Versión:</span>
                                <span class="tooltip-value">${{data.version}}</span>
                            </div>
                            <div class="tooltip-row">
                                <span class="tooltip-label">Owner:</span>
                                <span class="tooltip-value">${{data.owner}}</span>
                            </div>
                            <div class="tooltip-row">
                                <span class="tooltip-label">Dependencias:</span>
                                <span class="tooltip-value">${{data.dependencias}}</span>
                            </div>
                            <div class="tooltip-requisito">${{data.requisito}}</div>
                            <div class="tooltip-pinned-badge">📌 Fijado (clic en vacío para cerrar)</div>
                        `;
                        tooltip.style.display = 'block';
                        tooltip.classList.add('pinned');
                        tooltipPinned = true;
                    }}
                }} else {{
                    // Clicked on empty space - unpin and hide
                    selectedNodeId = null;
                    hideSelectedInfo();
                    tooltipPinned = false;
                    tooltip.classList.remove('pinned');
                    tooltip.style.display = 'none';
                }}
            }});

            // Hover tooltip
            network.on('hoverNode', function(params) {{
                if (tooltipPinned) return; // Don't update if pinned

                const nodeId = params.node;
                const data = nodeData[nodeId];
                if (!data) return;

                const color = areaColors[data.area] || '#888888';
                tooltip.innerHTML = `
                    <h4 style="color: ${{color}}">${{nodeId}}: ${{data.funcionalidad}}</h4>
                    <div class="tooltip-row">
                        <span class="tooltip-label">Área:</span>
                        <span class="tooltip-value">${{data.area}}</span>
                    </div>
                    <div class="tooltip-row">
                        <span class="tooltip-label">Prioridad:</span>
                        <span class="tooltip-value">${{data.prioridad}}</span>
                    </div>
                    <div class="tooltip-row">
                        <span class="tooltip-label">Versión:</span>
                        <span class="tooltip-value">${{data.version}}</span>
                    </div>
                    <div class="tooltip-row">
                        <span class="tooltip-label">Owner:</span>
                        <span class="tooltip-value">${{data.owner}}</span>
                    </div>
                    <div class="tooltip-row">
                        <span class="tooltip-label">Dependencias:</span>
                        <span class="tooltip-value">${{data.dependencias}}</span>
                    </div>
                    <div class="tooltip-requisito">${{data.requisito}}</div>
                `;
                tooltip.style.display = 'block';
            }});

            network.on('blurNode', function() {{
                if (!tooltipPinned) {{
                    tooltip.style.display = 'none';
                }}
            }});

            // Tooltip follows mouse only when not pinned
            document.querySelector('.graph-panel').addEventListener('mousemove', function(e) {{
                if (tooltip.style.display === 'block' && !tooltipPinned) {{
                    const x = e.clientX + 15;
                    const y = e.clientY + 15;
                    const rect = tooltip.getBoundingClientRect();
                    const maxX = window.innerWidth - rect.width - 20;
                    const maxY = window.innerHeight - rect.height - 20;
                    tooltip.style.left = Math.min(x, maxX) + 'px';
                    tooltip.style.top = Math.min(y, maxY) + 'px';
                }}
            }});
        }}

        // Keyboard shortcuts
        function setupKeyboardShortcuts() {{
            document.addEventListener('keydown', function(e) {{
                // Don't trigger when typing in input fields
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') {{
                    if (e.key === 'Escape') {{
                        e.target.blur();
                        document.getElementById('autocomplete-dropdown').classList.remove('visible');
                    }}
                    return;
                }}

                const modal = document.getElementById('shortcuts-modal');

                switch(e.key) {{
                    case '?':
                        modal.classList.toggle('visible');
                        break;
                    case 'Escape':
                        if (modal.classList.contains('visible')) {{
                            modal.classList.remove('visible');
                        }} else {{
                            resetView();
                        }}
                        break;
                    case '/':
                        e.preventDefault();
                        document.getElementById('node-search').focus();
                        break;
                    case 'r':
                    case 'R':
                        resetView();
                        break;
                    case '1':
                        setLayout('force');
                        showToast('Disposición: Fuerza', 'info', 1500);
                        break;
                    case '2':
                        setLayout('tree');
                        showToast('Disposición: Árbol', 'info', 1500);
                        break;
                    case 'a':
                    case 'A':
                        if (selectedNodeId) showAncestors();
                        break;
                    case 'd':
                    case 'D':
                        if (selectedNodeId) showDescendants();
                        break;
                    case 'n':
                    case 'N':
                        if (selectedNodeId) showNeighborhood();
                        break;
                }}
            }});
        }}

        // Autocomplete
        function setupAutocomplete() {{
            const input = document.getElementById('node-search');
            const dropdown = document.getElementById('autocomplete-dropdown');

            input.addEventListener('input', function() {{
                const query = this.value.trim().toLowerCase();
                if (query.length < 2) {{
                    dropdown.classList.remove('visible');
                    return;
                }}

                const matches = [];
                Object.keys(nodeData).forEach(id => {{
                    const data = nodeData[id];
                    const idMatch = id.toLowerCase().includes(query);
                    const funcMatch = data.funcionalidad.toLowerCase().includes(query);
                    const reqMatch = data.requisito.toLowerCase().includes(query);
                    if (idMatch || funcMatch || reqMatch) {{
                        matches.push({{ id, data, idMatch, funcMatch, reqMatch }});
                    }}
                }});

                if (matches.length === 0) {{
                    dropdown.classList.remove('visible');
                    return;
                }}

                // Sort: ID matches first, then func matches, then req matches
                matches.sort((a, b) => {{
                    if (a.idMatch && !b.idMatch) return -1;
                    if (!a.idMatch && b.idMatch) return 1;
                    if (a.funcMatch && !b.funcMatch) return -1;
                    if (!a.funcMatch && b.funcMatch) return 1;
                    return a.id.localeCompare(b.id);
                }});

                dropdown.innerHTML = matches.slice(0, 10).map((m, i) => `
                    <div class="autocomplete-item" data-id="${{m.id}}">
                        <span class="autocomplete-id">${{m.id}}</span>
                        <span class="autocomplete-func">${{m.data.funcionalidad.substring(0, 40)}}${{m.data.funcionalidad.length > 40 ? '...' : ''}}</span>
                    </div>
                `).join('');

                dropdown.classList.add('visible');
                autocompleteIndex = -1;

                dropdown.querySelectorAll('.autocomplete-item').forEach(item => {{
                    item.addEventListener('click', function() {{
                        const id = this.dataset.id;
                        input.value = id;
                        dropdown.classList.remove('visible');
                        focusOnNode(id);
                    }});
                }});
            }});

            input.addEventListener('keydown', function(e) {{
                const items = dropdown.querySelectorAll('.autocomplete-item');
                if (!dropdown.classList.contains('visible') || items.length === 0) return;

                if (e.key === 'ArrowDown') {{
                    e.preventDefault();
                    autocompleteIndex = Math.min(autocompleteIndex + 1, items.length - 1);
                    updateAutocompleteSelection(items);
                }} else if (e.key === 'ArrowUp') {{
                    e.preventDefault();
                    autocompleteIndex = Math.max(autocompleteIndex - 1, 0);
                    updateAutocompleteSelection(items);
                }}
            }});

            // Close dropdown when clicking outside
            document.addEventListener('click', function(e) {{
                if (!input.contains(e.target) && !dropdown.contains(e.target)) {{
                    dropdown.classList.remove('visible');
                }}
            }});
        }}

        function updateAutocompleteSelection(items) {{
            items.forEach((item, i) => {{
                item.classList.toggle('selected', i === autocompleteIndex);
            }});
        }}

        function focusOnNode(nodeId) {{
            if (nodeData[nodeId]) {{
                network.focus(nodeId, {{
                    scale: 1.5,
                    animation: {{ duration: 500, easingFunction: 'easeInOutQuad' }}
                }});
                network.selectNodes([nodeId]);
                selectedNodeId = nodeId;
                showSelectedInfo(nodeId);
                showToast(`Enfocando en ${{nodeId}}`, 'success', 1500);
            }}
        }}

        function focusNode() {{
            const input = document.getElementById('node-search').value.trim();
            if (!input) {{
                showToast('Por favor ingresa un ID o texto de búsqueda', 'warning');
                return;
            }}

            const upperInput = input.toUpperCase();

            // First try exact ID match
            if (nodeData[upperInput]) {{
                focusOnNode(upperInput);
                return;
            }}

            // Try full-text search
            const query = input.toLowerCase();
            const matches = [];
            Object.keys(nodeData).forEach(id => {{
                const data = nodeData[id];
                if (id.toLowerCase().includes(query) ||
                    data.funcionalidad.toLowerCase().includes(query) ||
                    data.requisito.toLowerCase().includes(query)) {{
                    matches.push(id);
                }}
            }});

            if (matches.length === 1) {{
                focusOnNode(matches[0]);
            }} else if (matches.length > 1) {{
                // Filter to show only matches
                visibleNodeIds = new Set(matches);
                currentViewContext = {{ type: 'search', query: input, count: matches.length }};
                updateVisibility();
                updateTable();
                updateStats();
                updateBreadcrumb();
                updateStatsPanel();
                showToast(`Encontrados ${{matches.length}} resultados para "${{input}}"`, 'info');
            }} else {{
                showToast(`No se encontró: "${{input}}"`, 'error');
            }}
        }}

        function applyFilters() {{
            const areaFilter = document.getElementById('area-filter').value;
            const priorityFilter = document.getElementById('priority-filter').value;
            const versionFilter = document.getElementById('version-filter').value;

            visibleNodeIds = new Set();

            Object.keys(nodeData).forEach(nodeId => {{
                const data = nodeData[nodeId];
                const matchArea = !areaFilter || data.area === areaFilter;
                const matchPriority = !priorityFilter || data.prioridad === priorityFilter;
                const matchVersion = !versionFilter || data.version === versionFilter;

                if (matchArea && matchPriority && matchVersion) {{
                    visibleNodeIds.add(nodeId);
                }}
            }});

            currentViewContext = {{ type: 'filter', area: areaFilter, priority: priorityFilter, version: versionFilter }};
            updateVisibility();
            updateTable();
            updateStats();
            updateFilterChips();
            updateBreadcrumb();
            updateStatsPanel();
        }}

        function updateVisibility() {{
            const nodeUpdates = Object.keys(nodeData).map(id => ({{
                id: id,
                hidden: !visibleNodeIds.has(id)
            }}));
            nodes.update(nodeUpdates);

            const edgeUpdates = edges.get().map(edge => ({{
                id: edge.id,
                hidden: !visibleNodeIds.has(edge.from) || !visibleNodeIds.has(edge.to)
            }}));
            edges.update(edgeUpdates);

            setTimeout(() => {{
                network.fit({{ animation: {{ duration: 300 }} }});
            }}, 100);
        }}

        function updateTable() {{
            const tbody = document.getElementById('table-body');

            // Get sorted IDs based on sortState
            let sortedData = Array.from(visibleNodeIds).map(id => ({{
                id,
                ...nodeData[id],
                connections: nodeData[id].in_degree + nodeData[id].out_degree
            }}));

            sortedData.sort((a, b) => {{
                let aVal, bVal;
                switch (sortState.column) {{
                    case 'id':
                        aVal = a.id;
                        bVal = b.id;
                        break;
                    case 'area':
                        aVal = a.area;
                        bVal = b.area;
                        break;
                    case 'funcionalidad':
                        aVal = a.funcionalidad;
                        bVal = b.funcionalidad;
                        break;
                    case 'prioridad':
                        const priorityOrder = {{ 'Alta (P0)': 0, 'Media (P1)': 1, 'Baja (P2)': 2 }};
                        aVal = priorityOrder[a.prioridad] ?? 1;
                        bVal = priorityOrder[b.prioridad] ?? 1;
                        break;
                    case 'version':
                        aVal = a.version;
                        bVal = b.version;
                        break;
                    case 'connections':
                        aVal = a.connections;
                        bVal = b.connections;
                        break;
                    default:
                        aVal = a.id;
                        bVal = b.id;
                }}

                if (typeof aVal === 'number') {{
                    return sortState.direction === 'asc' ? aVal - bVal : bVal - aVal;
                }}
                return sortState.direction === 'asc' ?
                    String(aVal).localeCompare(String(bVal)) :
                    String(bVal).localeCompare(String(aVal));
            }});

            let html = '';
            sortedData.forEach(item => {{
                const priorityClass = item.prioridad.includes('P0') ? 'priority-p0' :
                                      item.prioridad.includes('P1') ? 'priority-p1' : 'priority-p2';

                html += `
                    <tr data-id="${{item.id}}" style="cursor: pointer;">
                        <td class="id-cell">${{item.id}}</td>
                        <td class="area-cell">${{item.area}}</td>
                        <td class="func-cell">${{item.funcionalidad}}</td>
                        <td><span class="priority-badge ${{priorityClass}}">${{item.prioridad}}</span></td>
                        <td>${{item.version}}</td>
                        <td style="text-align:center">${{item.connections}}</td>
                    </tr>
                `;
            }});

            tbody.innerHTML = html;
            document.getElementById('table-count').textContent = visibleNodeIds.size + ' requisitos';

            // Add click handlers to table rows
            tbody.querySelectorAll('tr').forEach(row => {{
                row.addEventListener('click', function() {{
                    const id = this.getAttribute('data-id');
                    network.focus(id, {{
                        scale: 1.5,
                        animation: {{ duration: 500 }}
                    }});
                    network.selectNodes([id]);
                    selectedNodeId = id;
                    showSelectedInfo(id);
                }});
            }});
        }}

        function updateSortIndicators() {{
            document.querySelectorAll('.data-table th.sortable').forEach(th => {{
                th.classList.remove('sort-asc', 'sort-desc');
                if (th.dataset.sort === sortState.column) {{
                    th.classList.add(sortState.direction === 'asc' ? 'sort-asc' : 'sort-desc');
                    th.querySelector('.sort-indicator').textContent = sortState.direction === 'asc' ? '▲' : '▼';
                }} else {{
                    th.querySelector('.sort-indicator').textContent = '⇅';
                }}
            }});
        }}

        function updateStats() {{
            document.getElementById('visible-nodes').textContent = visibleNodeIds.size;
            const visibleEdgeCount = edges.get().filter(e =>
                visibleNodeIds.has(e.from) && visibleNodeIds.has(e.to)
            ).length;
            document.getElementById('visible-edges').textContent = visibleEdgeCount;
        }}

        function updateFilterChips() {{
            const container = document.getElementById('filter-chips');
            const chips = [];
            const areaFilter = document.getElementById('area-filter').value;
            const priorityFilter = document.getElementById('priority-filter').value;
            const versionFilter = document.getElementById('version-filter').value;

            if (areaFilter) {{
                chips.push({{ type: 'area', label: 'Área', value: areaFilter }});
            }}
            if (priorityFilter) {{
                chips.push({{ type: 'priority', label: 'Prioridad', value: priorityFilter }});
            }}
            if (versionFilter) {{
                chips.push({{ type: 'version', label: 'Versión', value: versionFilter }});
            }}

            container.innerHTML = chips.map(chip => `
                <div class="filter-chip" data-type="${{chip.type}}">
                    <span class="filter-chip-label">${{chip.label}}:</span>
                    <span>${{chip.value}}</span>
                    <button class="filter-chip-remove" data-type="${{chip.type}}">&times;</button>
                </div>
            `).join('');

            container.querySelectorAll('.filter-chip-remove').forEach(btn => {{
                btn.addEventListener('click', function() {{
                    const type = this.dataset.type;
                    if (type === 'area') document.getElementById('area-filter').value = '';
                    if (type === 'priority') document.getElementById('priority-filter').value = '';
                    if (type === 'version') document.getElementById('version-filter').value = '';
                    applyFilters();
                }});
            }});
        }}

        function updateBreadcrumb() {{
            const textEl = document.getElementById('breadcrumb-text');
            const resetBtn = document.getElementById('breadcrumb-reset');
            const ctx = currentViewContext;

            if (ctx.type === 'all') {{
                textEl.innerHTML = `Todos los requisitos (<strong>${{totalNodes}}</strong>)`;
                resetBtn.style.display = 'none';
            }} else if (ctx.type === 'filter') {{
                const parts = [];
                if (ctx.area) parts.push(ctx.area);
                if (ctx.priority) parts.push(ctx.priority);
                if (ctx.version) parts.push(ctx.version);
                textEl.innerHTML = `Filtrado: ${{parts.join(', ')}} (<strong>${{visibleNodeIds.size}}</strong>)`;
                resetBtn.style.display = 'block';
            }} else if (ctx.type === 'ancestors') {{
                textEl.innerHTML = `Ancestros de <strong>${{ctx.node}}</strong> (${{visibleNodeIds.size}})`;
                resetBtn.style.display = 'block';
            }} else if (ctx.type === 'descendants') {{
                textEl.innerHTML = `Descendientes de <strong>${{ctx.node}}</strong> (${{visibleNodeIds.size}})`;
                resetBtn.style.display = 'block';
            }} else if (ctx.type === 'neighborhood') {{
                textEl.innerHTML = `Vecindario de <strong>${{ctx.node}}</strong> (${{visibleNodeIds.size}})`;
                resetBtn.style.display = 'block';
            }} else if (ctx.type === 'search') {{
                textEl.innerHTML = `Búsqueda: "${{ctx.query}}" (<strong>${{ctx.count}}</strong> resultados)`;
                resetBtn.style.display = 'block';
            }}
        }}

        function updateStatsPanel() {{
            // Priority distribution
            const priorityCounts = {{ 'Alta (P0)': 0, 'Media (P1)': 0, 'Baja (P2)': 0 }};
            visibleNodeIds.forEach(id => {{
                const p = nodeData[id].prioridad;
                if (priorityCounts[p] !== undefined) priorityCounts[p]++;
            }});

            const priorityColors = {{ 'Alta (P0)': '#ff6b6b', 'Media (P1)': '#ffd93d', 'Baja (P2)': '#4ecdc4' }};
            const maxPriority = Math.max(...Object.values(priorityCounts), 1);

            document.getElementById('priority-stats').innerHTML = Object.entries(priorityCounts).map(([label, count]) => `
                <div class="stats-bar-row">
                    <span class="stats-bar-label">${{label.replace(' (P0)', '').replace(' (P1)', '').replace(' (P2)', '')}}</span>
                    <div class="stats-bar-wrapper">
                        <div class="stats-bar" style="width: ${{(count / maxPriority) * 100}}%; background: ${{priorityColors[label]}}"></div>
                    </div>
                    <span class="stats-bar-value">${{count}}</span>
                </div>
            `).join('');

            // Area distribution (top 5)
            const areaCounts = {{}};
            visibleNodeIds.forEach(id => {{
                const area = nodeData[id].area;
                areaCounts[area] = (areaCounts[area] || 0) + 1;
            }});

            const topAreas = Object.entries(areaCounts)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5);
            const maxArea = topAreas.length > 0 ? topAreas[0][1] : 1;

            document.getElementById('area-stats').innerHTML = topAreas.map(([area, count]) => `
                <div class="stats-bar-row">
                    <span class="stats-bar-label" title="${{area}}">${{area.substring(0, 12)}}</span>
                    <div class="stats-bar-wrapper">
                        <div class="stats-bar" style="width: ${{(count / maxArea) * 100}}%; background: ${{areaColors[area] || '#888'}}"></div>
                    </div>
                    <span class="stats-bar-value">${{count}}</span>
                </div>
            `).join('');

            // Top connected nodes
            const connections = Array.from(visibleNodeIds).map(id => ({{
                id,
                total: nodeData[id].in_degree + nodeData[id].out_degree
            }})).sort((a, b) => b.total - a.total).slice(0, 5);

            document.getElementById('top-connected').innerHTML = connections.map(c => `
                <div class="top-connected-item" data-id="${{c.id}}">
                    <span class="top-connected-id">${{c.id}}</span>
                    <span>${{nodeData[c.id].funcionalidad.substring(0, 20)}}...</span>
                    <span class="top-connected-count">${{c.total}} conex.</span>
                </div>
            `).join('');

            // Click handlers for top connected items
            document.querySelectorAll('.top-connected-item').forEach(item => {{
                item.addEventListener('click', function() {{
                    focusOnNode(this.dataset.id);
                }});
            }});
        }}

        // Export functions
        function exportPNG() {{
            showToast('Generando imagen PNG...', 'info', 2000);
            try {{
                const canvas = document.querySelector('#mynetwork canvas');
                if (!canvas) {{
                    showToast('No se pudo encontrar el canvas del grafo', 'error');
                    return;
                }}

                // Create a new canvas with white background and title
                const exportCanvas = document.createElement('canvas');
                const ctx = exportCanvas.getContext('2d');
                const padding = 40;

                exportCanvas.width = canvas.width + padding * 2;
                exportCanvas.height = canvas.height + padding * 2 + 50;

                // Dark background
                ctx.fillStyle = '#1a1a2e';
                ctx.fillRect(0, 0, exportCanvas.width, exportCanvas.height);

                // Title
                ctx.fillStyle = '#00ff88';
                ctx.font = 'bold 24px Segoe UI, Arial, sans-serif';
                ctx.fillText('Requirements Dependency Graph', padding, 35);

                // Timestamp
                ctx.fillStyle = '#8888aa';
                ctx.font = '12px Segoe UI, Arial, sans-serif';
                ctx.fillText(new Date().toLocaleString(), padding, 55);

                // Draw the original canvas
                ctx.drawImage(canvas, padding, padding + 50);

                // Create download link
                const link = document.createElement('a');
                link.download = `requirements-graph-${{Date.now()}}.png`;
                link.href = exportCanvas.toDataURL('image/png');
                link.click();

                showToast('PNG exportado correctamente', 'success');
            }} catch (err) {{
                showToast('Error al exportar PNG: ' + err.message, 'error');
            }}
        }}

        function exportCSV() {{
            showToast('Generando archivo CSV...', 'info', 1500);
            try {{
                const headers = ['ID', 'Área', 'Funcionalidad', 'Prioridad', 'Versión', 'Owner', 'Estatus', 'Dependencias', 'In-Degree', 'Out-Degree'];
                const rows = [headers.join(',')];

                Array.from(visibleNodeIds).sort().forEach(id => {{
                    const d = nodeData[id];
                    const row = [
                        id,
                        `"${{d.area}}"`,
                        `"${{d.funcionalidad.replace(/"/g, '""')}}"`,
                        `"${{d.prioridad}}"`,
                        `"${{d.version}}"`,
                        `"${{d.owner}}"`,
                        `"${{d.estatus}}"`,
                        `"${{d.dependencias}}"`,
                        d.in_degree,
                        d.out_degree
                    ];
                    rows.push(row.join(','));
                }});

                // UTF-8 BOM for Excel compatibility
                const BOM = '\\uFEFF';
                const csvContent = BOM + rows.join('\\n');
                const blob = new Blob([csvContent], {{ type: 'text/csv;charset=utf-8;' }});

                const link = document.createElement('a');
                link.href = URL.createObjectURL(blob);
                link.download = `requirements-${{visibleNodeIds.size}}-${{Date.now()}}.csv`;
                link.click();

                showToast(`CSV exportado (${{visibleNodeIds.size}} requisitos)`, 'success');
            }} catch (err) {{
                showToast('Error al exportar CSV: ' + err.message, 'error');
            }}
        }}

        function showSelectedInfo(nodeId) {{
            // Info is now shown in the pinned tooltip
        }}

        function hideSelectedInfo() {{
            // Info is now hidden via the pinned tooltip
        }}

        function showAncestors() {{
            if (!selectedNodeId) {{
                showToast('Primero selecciona un nodo haciendo clic en el grafo', 'warning');
                return;
            }}
            const ancestors = subgraphData[selectedNodeId]?.ancestors || [];
            visibleNodeIds = new Set([selectedNodeId, ...ancestors]);
            currentViewContext = {{ type: 'ancestors', node: selectedNodeId }};
            updateVisibility();
            updateTable();
            updateStats();
            updateBreadcrumb();
            updateStatsPanel();
            showToast(`Mostrando ${{visibleNodeIds.size}} ancestros de ${{selectedNodeId}}`, 'info');
        }}

        function showDescendants() {{
            if (!selectedNodeId) {{
                showToast('Primero selecciona un nodo haciendo clic en el grafo', 'warning');
                return;
            }}
            const descendants = subgraphData[selectedNodeId]?.descendants || [];
            visibleNodeIds = new Set([selectedNodeId, ...descendants]);
            currentViewContext = {{ type: 'descendants', node: selectedNodeId }};
            updateVisibility();
            updateTable();
            updateStats();
            updateBreadcrumb();
            updateStatsPanel();
            showToast(`Mostrando ${{visibleNodeIds.size}} descendientes de ${{selectedNodeId}}`, 'info');
        }}

        function showNeighborhood() {{
            if (!selectedNodeId) {{
                showToast('Primero selecciona un nodo haciendo clic en el grafo', 'warning');
                return;
            }}
            const neighbors = new Set([selectedNodeId]);
            edges.get().forEach(edge => {{
                if (edge.from === selectedNodeId) neighbors.add(edge.to);
                if (edge.to === selectedNodeId) neighbors.add(edge.from);
            }});
            visibleNodeIds = neighbors;
            currentViewContext = {{ type: 'neighborhood', node: selectedNodeId }};
            updateVisibility();
            updateTable();
            updateStats();
            updateBreadcrumb();
            updateStatsPanel();
            showToast(`Mostrando vecindario de ${{selectedNodeId}} (${{visibleNodeIds.size}} nodos)`, 'info');
        }}

        function setLayout(layout) {{
            currentLayout = layout;

            // Update button states
            document.getElementById('layout-force').classList.toggle('active', layout === 'force');
            document.getElementById('layout-tree').classList.toggle('active', layout === 'tree');

            if (layout === 'tree') {{
                network.setOptions({{
                    layout: {{
                        hierarchical: {{
                            enabled: true,
                            direction: 'UD',
                            sortMethod: 'directed',
                            levelSeparation: 150,
                            nodeSpacing: 180,
                            treeSpacing: 220,
                            blockShifting: true,
                            edgeMinimization: true,
                            parentCentralization: true,
                            shakeTowards: 'roots'
                        }}
                    }},
                    physics: {{
                        enabled: false
                    }}
                }});
            }} else {{
                network.setOptions({{
                    layout: {{
                        hierarchical: {{
                            enabled: false
                        }}
                    }},
                    physics: {{
                        enabled: true,
                        solver: 'forceAtlas2Based',
                        forceAtlas2Based: {{
                            gravitationalConstant: -80,
                            centralGravity: 0.01,
                            springLength: 150,
                            springConstant: 0.08,
                            damping: 0.4,
                            avoidOverlap: 0.8
                        }}
                    }}
                }});
            }}

            setTimeout(() => {{
                network.fit({{ animation: {{ duration: 500 }} }});
            }}, 300);
        }}

        function resetView() {{
            // Clear filters
            document.getElementById('area-filter').value = '';
            document.getElementById('priority-filter').value = '';
            document.getElementById('version-filter').value = '';
            document.getElementById('node-search').value = '';

            // Show all nodes
            visibleNodeIds = new Set(Object.keys(nodeData));
            currentViewContext = {{ type: 'all', node: null }};
            updateVisibility();
            updateTable();

            // Reset stats
            document.getElementById('visible-nodes').textContent = totalNodes;
            document.getElementById('visible-edges').textContent = totalEdges;

            // Clear filter chips
            document.getElementById('filter-chips').innerHTML = '';

            // Update breadcrumb
            updateBreadcrumb();

            // Update stats panel
            updateStatsPanel();

            // Deselect
            network.unselectAll();
            selectedNodeId = null;
            hideSelectedInfo();

            // Hide pinned tooltip
            const tooltip = document.getElementById('hover-tooltip');
            tooltip.style.display = 'none';
            tooltip.classList.remove('pinned');

            // Reset layout to force
            if (currentLayout === 'tree') {{
                setLayout('force');
            }}

            network.fit({{ animation: {{ duration: 500 }} }});
            showToast('Vista restablecida', 'info', 1500);
        }}
    }})();
    </script>
    """

    # Remove pyvis default card structure and replace body content
    html_content = html_content.replace('</head>', custom_css + '</head>')

    # Find the body tag and insert our HTML
    body_start = html_content.find('<body>')
    if body_start != -1:
        # Find where the card div ends to extract just the script content
        card_div_start = html_content.find('<div class="card"', body_start)
        if card_div_start != -1:
            # We need to keep the scripts but replace the HTML structure
            script_start = html_content.find('<script type="text/javascript">', body_start)
            body_end = html_content.find('</body>')

            if script_start != -1 and body_end != -1:
                scripts = html_content[script_start:body_end]
                html_content = html_content[:body_start + 6] + custom_html + scripts + custom_js + '</body></html>'

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)


def main():
    parser = argparse.ArgumentParser(description='Create interactive requirements graph visualization')
    parser.add_argument('csv_file', help='Path to requirements CSV file')
    parser.add_argument('--output', '-o', default='requirements_interactive.html', help='Output HTML file')
    parser.add_argument('--title', '-t', default='Requirements Dependency Graph', help='Graph title')
    parser.add_argument('--highlight', help='Node ID to highlight')

    args = parser.parse_args()

    print(f"Loading requirements from: {args.csv_file}")
    df = load_requirements(args.csv_file)
    print(f"Loaded {len(df)} requirements")

    G = build_graph(df)
    print(f"Built graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")

    create_interactive_graph(
        G,
        title=args.title,
        output_path=args.output,
        highlight_node=args.highlight,
    )


if __name__ == '__main__':
    main()
