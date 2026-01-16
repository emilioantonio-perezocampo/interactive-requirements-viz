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
            level=G.in_degree(node_id),
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

        /* Selected node info */
        .selected-info {
            padding: 15px;
            background: rgba(0,255,136,0.05);
            border-bottom: 1px solid #4a4a6a;
            display: none;
        }

        .selected-info.visible {
            display: block;
        }

        .selected-info h3 {
            color: #00ff88;
            margin: 0 0 8px 0;
            font-size: 0.95em;
        }

        .selected-info p {
            color: #cccccc;
            margin: 4px 0;
            font-size: 0.85em;
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
    <div class="app-container">
        <!-- Left Panel: Controls -->
        <div class="left-panel">
            <div class="panel-header">
                <h1 class="app-title">📊 {title}</h1>
                <p class="app-subtitle">Grafo interactivo de dependencias</p>
            </div>

            <div class="controls-section">
                <h3>🔍 Buscar Nodo</h3>
                <div class="control-row">
                    <label>ID del Requisito:</label>
                    <input type="text" id="node-search" placeholder="Ej: RM-001, RM-015">
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
            <div id="mynetwork"></div>
        </div>

        <!-- Right Panel: Data Table -->
        <div class="right-panel">
            <div class="selected-info" id="selected-info">
                <h3 id="selected-title">Nodo Seleccionado</h3>
                <p><strong>ID:</strong> <span id="sel-id">—</span></p>
                <p><strong>Área:</strong> <span id="sel-area">—</span></p>
                <p><strong>Prioridad:</strong> <span id="sel-priority">—</span></p>
                <p><strong>Dependencias:</strong> <span id="sel-deps">—</span></p>
            </div>
            <div class="table-header">
                <h2>📋 Requisitos Visibles</h2>
                <span class="table-count" id="table-count">{len(G.nodes())} requisitos</span>
            </div>
            <div class="table-container">
                <table class="data-table" id="data-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Área</th>
                            <th>Funcionalidad</th>
                            <th>Prioridad</th>
                            <th>Versión</th>
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

    custom_js = f"""
    <script>
    (function() {{
        // Data
        const nodeData = {json.dumps(node_data_js, ensure_ascii=False)};
        const subgraphData = {json.dumps(subgraph_data)};
        const areaColors = {json.dumps(AREA_COLORS)};
        const totalNodes = {len(G.nodes())};
        const totalEdges = {len(G.edges())};

        // State
        let selectedNodeId = null;
        let currentLayout = 'force';
        let visibleNodeIds = new Set(Object.keys(nodeData));

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
            // Initial table render
            updateTable();

            // Bind event handlers
            bindEventHandlers();

            // Setup network event handlers
            setupNetworkHandlers();
        }}

        function bindEventHandlers() {{
            // Search button
            document.getElementById('btn-search').addEventListener('click', focusNode);

            // Search input enter key
            document.getElementById('node-search').addEventListener('keypress', function(e) {{
                if (e.key === 'Enter') focusNode();
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

            // Legend clicks
            document.querySelectorAll('.legend-item').forEach(item => {{
                item.addEventListener('click', function() {{
                    const area = this.getAttribute('data-area');
                    document.getElementById('area-filter').value = area;
                    applyFilters();
                }});
            }});
        }}

        function setupNetworkHandlers() {{
            // Click handler
            network.on('click', function(params) {{
                if (params.nodes.length > 0) {{
                    selectedNodeId = params.nodes[0];
                    showSelectedInfo(selectedNodeId);
                }} else {{
                    selectedNodeId = null;
                    hideSelectedInfo();
                }}
            }});

            // Hover tooltip
            const tooltip = document.getElementById('hover-tooltip');

            network.on('hoverNode', function(params) {{
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
                tooltip.style.display = 'none';
            }});

            // Tooltip follows mouse
            document.querySelector('.graph-panel').addEventListener('mousemove', function(e) {{
                if (tooltip.style.display === 'block') {{
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

        function focusNode() {{
            const input = document.getElementById('node-search').value.trim().toUpperCase();
            if (!input) {{
                alert('Por favor ingresa un ID de requisito (ej: RM-001)');
                return;
            }}

            if (nodeData[input]) {{
                network.focus(input, {{
                    scale: 1.5,
                    animation: {{ duration: 500, easingFunction: 'easeInOutQuad' }}
                }});
                network.selectNodes([input]);
                selectedNodeId = input;
                showSelectedInfo(input);
            }} else {{
                alert('Nodo no encontrado: ' + input + '\\n\\nAsegúrate de usar el formato correcto (ej: RM-001)');
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

            updateVisibility();
            updateTable();
            updateStats();
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
            const sortedIds = Array.from(visibleNodeIds).sort();

            let html = '';
            sortedIds.forEach(id => {{
                const data = nodeData[id];
                const priorityClass = data.prioridad.includes('P0') ? 'priority-p0' :
                                      data.prioridad.includes('P1') ? 'priority-p1' : 'priority-p2';

                html += `
                    <tr data-id="${{id}}" style="cursor: pointer;">
                        <td class="id-cell">${{id}}</td>
                        <td class="area-cell">${{data.area}}</td>
                        <td class="func-cell">${{data.funcionalidad}}</td>
                        <td><span class="priority-badge ${{priorityClass}}">${{data.prioridad}}</span></td>
                        <td>${{data.version}}</td>
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

        function updateStats() {{
            document.getElementById('visible-nodes').textContent = visibleNodeIds.size;
            const visibleEdgeCount = edges.get().filter(e =>
                visibleNodeIds.has(e.from) && visibleNodeIds.has(e.to)
            ).length;
            document.getElementById('visible-edges').textContent = visibleEdgeCount;
        }}

        function showSelectedInfo(nodeId) {{
            const data = nodeData[nodeId];
            if (!data) return;

            document.getElementById('sel-id').textContent = nodeId;
            document.getElementById('sel-area').textContent = data.area;
            document.getElementById('sel-priority').textContent = data.prioridad;
            document.getElementById('sel-deps').textContent = data.dependencias;
            document.getElementById('selected-title').textContent = data.funcionalidad;
            document.getElementById('selected-info').classList.add('visible');
        }}

        function hideSelectedInfo() {{
            document.getElementById('selected-info').classList.remove('visible');
        }}

        function showAncestors() {{
            if (!selectedNodeId) {{
                alert('Primero selecciona un nodo haciendo clic en el grafo');
                return;
            }}
            const ancestors = subgraphData[selectedNodeId]?.ancestors || [];
            visibleNodeIds = new Set([selectedNodeId, ...ancestors]);
            updateVisibility();
            updateTable();
            updateStats();
        }}

        function showDescendants() {{
            if (!selectedNodeId) {{
                alert('Primero selecciona un nodo haciendo clic en el grafo');
                return;
            }}
            const descendants = subgraphData[selectedNodeId]?.descendants || [];
            visibleNodeIds = new Set([selectedNodeId, ...descendants]);
            updateVisibility();
            updateTable();
            updateStats();
        }}

        function showNeighborhood() {{
            if (!selectedNodeId) {{
                alert('Primero selecciona un nodo haciendo clic en el grafo');
                return;
            }}
            const neighbors = new Set([selectedNodeId]);
            edges.get().forEach(edge => {{
                if (edge.from === selectedNodeId) neighbors.add(edge.to);
                if (edge.to === selectedNodeId) neighbors.add(edge.from);
            }});
            visibleNodeIds = neighbors;
            updateVisibility();
            updateTable();
            updateStats();
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
                            levelSeparation: 100,
                            nodeSpacing: 120,
                            treeSpacing: 150,
                            blockShifting: true,
                            edgeMinimization: true,
                            parentCentralization: true
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
            updateVisibility();
            updateTable();

            // Reset stats
            document.getElementById('visible-nodes').textContent = totalNodes;
            document.getElementById('visible-edges').textContent = totalEdges;

            // Deselect
            network.unselectAll();
            selectedNodeId = null;
            hideSelectedInfo();

            // Reset layout to force
            if (currentLayout === 'tree') {{
                setLayout('force');
            }}

            network.fit({{ animation: {{ duration: 500 }} }});
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
