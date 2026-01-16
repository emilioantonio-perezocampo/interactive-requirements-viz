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
        select_menu=True,
        filter_menu=True,
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
        
        # Create simple text tooltip (HTML will be rendered via custom tooltip div)
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
            level=G.in_degree(node_id),  # For hierarchical hints
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
        item = f'<div class="legend-item" onclick="filterByArea(\'{a}\')">'
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
    
    # Build node data for JavaScript (include all fields for custom tooltip)
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
        body {
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Arial, sans-serif;
            background: #1a1a2e;
            overflow: hidden;
        }
        
        #controls {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: linear-gradient(180deg, #16213e 0%, #1a1a2e 100%);
            padding: 15px 20px;
            z-index: 1000;
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            align-items: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
            border-bottom: 1px solid #4a4a6a;
        }
        
        #controls h1 {
            color: #00ff88;
            margin: 0;
            font-size: 1.3em;
            font-weight: 600;
            margin-right: 20px;
        }
        
        .control-group {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .control-group label {
            color: #8888aa;
            font-size: 0.85em;
            font-weight: 500;
        }
        
        .control-group select, .control-group input {
            background: #0f0f23;
            border: 1px solid #4a4a6a;
            color: #ffffff;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.9em;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .control-group select:hover, .control-group input:hover {
            border-color: #00ff88;
        }
        
        .control-group select:focus, .control-group input:focus {
            outline: none;
            border-color: #00ff88;
            box-shadow: 0 0 10px rgba(0,255,136,0.3);
        }
        
        button {
            background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);
            border: none;
            color: #1a1a2e;
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 0.9em;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0,255,136,0.4);
        }
        
        button.secondary {
            background: #4a4a6a;
            color: #ffffff;
        }
        
        button.secondary:hover {
            background: #5a5a7a;
        }
        
        #stats {
            position: fixed;
            bottom: 20px;
            left: 20px;
            background: rgba(22, 33, 62, 0.95);
            padding: 15px 20px;
            border-radius: 10px;
            color: #ffffff;
            font-size: 0.85em;
            z-index: 1000;
            border: 1px solid #4a4a6a;
            max-width: 280px;
        }
        
        #stats h3 {
            margin: 0 0 10px 0;
            color: #00ff88;
            font-size: 1em;
        }
        
        #stats p {
            margin: 5px 0;
            color: #aaaacc;
        }
        
        #stats span {
            color: #ffffff;
            font-weight: 600;
        }
        
        #legend {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: rgba(22, 33, 62, 0.95);
            padding: 15px 20px;
            border-radius: 10px;
            color: #ffffff;
            font-size: 0.8em;
            z-index: 1000;
            border: 1px solid #4a4a6a;
            max-height: 400px;
            overflow-y: auto;
        }
        
        #legend h3 {
            margin: 0 0 10px 0;
            color: #00ff88;
            font-size: 1em;
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 5px 0;
            cursor: pointer;
            padding: 3px 5px;
            border-radius: 4px;
            transition: background 0.2s;
        }
        
        .legend-item:hover {
            background: rgba(255,255,255,0.1);
        }
        
        .legend-color {
            width: 16px;
            height: 16px;
            border-radius: 4px;
            border: 1px solid rgba(255,255,255,0.3);
        }
        
        #mynetwork {
            margin-top: 70px;
            height: calc(100vh - 70px) !important;
        }
        
        #node-info {
            position: fixed;
            top: 80px;
            right: 20px;
            background: rgba(22, 33, 62, 0.95);
            padding: 15px 20px;
            border-radius: 10px;
            color: #ffffff;
            font-size: 0.85em;
            z-index: 1000;
            border: 1px solid #4a4a6a;
            max-width: 350px;
            display: none;
        }
        
        #node-info h3 {
            margin: 0 0 10px 0;
            color: #00ff88;
        }
        
        #node-info .close-btn {
            position: absolute;
            top: 10px;
            right: 15px;
            cursor: pointer;
            color: #888;
            font-size: 1.2em;
        }
        
        #node-info .close-btn:hover {
            color: #fff;
        }
        
        .help-text {
            color: #6a6a8a;
            font-size: 0.8em;
            margin-left: auto;
        }

        /* Custom hover tooltip */
        #hover-tooltip {
            position: fixed;
            background: rgba(22, 33, 62, 0.98);
            padding: 15px 20px;
            border-radius: 10px;
            color: #ffffff;
            font-size: 0.85em;
            z-index: 2000;
            border: 1px solid #4a4a6a;
            max-width: 420px;
            pointer-events: none;
            display: none;
            box-shadow: 0 8px 32px rgba(0,0,0,0.5);
        }

        #hover-tooltip h4 {
            margin: 0 0 12px 0;
            color: #00ff88;
            font-size: 1.1em;
            border-bottom: 1px solid #4a4a6a;
            padding-bottom: 8px;
        }

        #hover-tooltip .tooltip-row {
            display: flex;
            margin: 6px 0;
            line-height: 1.4;
        }

        #hover-tooltip .tooltip-label {
            color: #8888aa;
            min-width: 100px;
            font-weight: 500;
        }

        #hover-tooltip .tooltip-value {
            color: #ffffff;
            flex: 1;
        }

        #hover-tooltip .tooltip-requisito {
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid #4a4a6a;
            line-height: 1.5;
            color: #ccccdd;
            font-size: 0.95em;
        }

        #hover-tooltip .tooltip-requisito-label {
            color: #8888aa;
            font-weight: 500;
            display: block;
            margin-bottom: 6px;
        }

        /* Layout toggle button styles */
        .layout-toggle {
            display: flex;
            gap: 0;
            border-radius: 6px;
            overflow: hidden;
            border: 1px solid #4a4a6a;
        }

        .layout-btn {
            background: #0f0f23;
            border: none;
            color: #8888aa;
            padding: 8px 14px;
            font-size: 0.85em;
            cursor: pointer;
            transition: all 0.2s;
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

        .layout-btn:first-child {
            border-right: 1px solid #4a4a6a;
        }
    </style>
    """
    
    custom_controls = f"""
    <div id="controls">
        <h1>📊 {title}</h1>
        
        <div class="control-group">
            <label>Área:</label>
            <select id="area-filter">
                <option value="">Todas</option>
                {"".join(f'<option value="{a}">{a}</option>' for a in areas)}
            </select>
        </div>
        
        <div class="control-group">
            <label>Prioridad:</label>
            <select id="priority-filter">
                <option value="">Todas</option>
                {"".join(f'<option value="{p}">{p}</option>' for p in priorities)}
            </select>
        </div>
        
        <div class="control-group">
            <label>Versión:</label>
            <select id="version-filter">
                <option value="">Todas</option>
                {"".join(f'<option value="{v}">{v}</option>' for v in versions)}
            </select>
        </div>
        
        <div class="control-group">
            <label>Nodo:</label>
            <input type="text" id="node-search" placeholder="RM-001" style="width: 80px;">
            <button onclick="focusNode()">Buscar</button>
        </div>
        
        <div class="control-group">
            <button onclick="showAncestors()">← Dependencias</button>
            <button onclick="showDescendants()">Dependientes →</button>
            <button onclick="showNeighborhood()">Vecindario</button>
        </div>

        <div class="control-group">
            <label>Layout:</label>
            <div class="layout-toggle">
                <button class="layout-btn active" id="layout-force" onclick="setLayout('force')">Fuerza</button>
                <button class="layout-btn" id="layout-tree" onclick="setLayout('tree')">Árbol</button>
            </div>
        </div>

        <button class="secondary" onclick="resetView()">Reset</button>
        
        <span class="help-text">Click en nodo para seleccionar • Doble click para fijar • Scroll para zoom</span>
    </div>
    
    <div id="stats">
        <h3>📈 Estadísticas</h3>
        <p>Nodos visibles: <span id="visible-nodes">{len(G.nodes())}</span></p>
        <p>Aristas visibles: <span id="visible-edges">{len(G.edges())}</span></p>
        <p>Nodo seleccionado: <span id="selected-node">—</span></p>
        <p>In-degree: <span id="in-degree">—</span></p>
        <p>Out-degree: <span id="out-degree">—</span></p>
    </div>
    
    <div id="legend">
        <h3>🎨 Áreas</h3>
        {generate_legend_items(areas)}
    </div>
    
    <div id="node-info">
        <span class="close-btn" onclick="closeNodeInfo()">×</span>
        <h3 id="info-title">—</h3>
        <div id="info-content"></div>
        <div style="margin-top: 15px; display: flex; gap: 10px;">
            <button onclick="showAncestorsOf(selectedNodeId)">Ver dependencias</button>
            <button onclick="showDescendantsOf(selectedNodeId)">Ver dependientes</button>
        </div>
    </div>

    <div id="hover-tooltip"></div>
    """
    
    custom_js = f"""
    <script>
        const nodeData = {json.dumps(node_data_js)};
        const subgraphData = {json.dumps(subgraph_data)};
        const areaColors = {json.dumps(AREA_COLORS)};

        let selectedNodeId = null;
        let allNodes = null;
        let allEdges = null;
        let currentLayout = 'force';
        const hoverTooltip = document.getElementById('hover-tooltip');

        // Store original data after network is ready
        network.once('stabilizationIterationsDone', function() {{
            allNodes = nodes.get();
            allEdges = edges.get();
        }});

        // Node click handler
        network.on('click', function(params) {{
            if (params.nodes.length > 0) {{
                selectedNodeId = params.nodes[0];
                updateStats(selectedNodeId);
                showNodeInfo(selectedNodeId);
            }} else {{
                selectedNodeId = null;
                updateStats(null);
                closeNodeInfo();
            }}
        }});

        // Hover tooltip handlers
        network.on('hoverNode', function(params) {{
            const nodeId = params.node;
            const data = nodeData[nodeId];
            if (!data) return;

            const color = areaColors[data.area] || '#888888';
            hoverTooltip.innerHTML = `
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
                    <span class="tooltip-label">Estatus:</span>
                    <span class="tooltip-value">${{data.estatus}}</span>
                </div>
                <div class="tooltip-row">
                    <span class="tooltip-label">Owner:</span>
                    <span class="tooltip-value">${{data.owner}}</span>
                </div>
                <div class="tooltip-row">
                    <span class="tooltip-label">Roles:</span>
                    <span class="tooltip-value">${{data.roles}}</span>
                </div>
                <div class="tooltip-row">
                    <span class="tooltip-label">Dependencias:</span>
                    <span class="tooltip-value">${{data.dependencias}}</span>
                </div>
                <div class="tooltip-requisito">
                    <span class="tooltip-requisito-label">Requisito:</span>
                    ${{data.requisito}}
                </div>
            `;
            hoverTooltip.style.display = 'block';
        }});

        network.on('blurNode', function() {{
            hoverTooltip.style.display = 'none';
        }});

        // Update tooltip position on mouse move
        document.getElementById('mynetwork').addEventListener('mousemove', function(e) {{
            if (hoverTooltip.style.display === 'block') {{
                const x = e.clientX + 15;
                const y = e.clientY + 15;
                const tooltipRect = hoverTooltip.getBoundingClientRect();

                // Keep tooltip within viewport
                const maxX = window.innerWidth - tooltipRect.width - 20;
                const maxY = window.innerHeight - tooltipRect.height - 20;

                hoverTooltip.style.left = Math.min(x, maxX) + 'px';
                hoverTooltip.style.top = Math.min(y, maxY) + 'px';
            }}
        }});

        function updateStats(nodeId) {{
            document.getElementById('selected-node').textContent = nodeId || '—';
            if (nodeId && nodeData[nodeId]) {{
                document.getElementById('in-degree').textContent = nodeData[nodeId].in_degree;
                document.getElementById('out-degree').textContent = nodeData[nodeId].out_degree;
            }} else {{
                document.getElementById('in-degree').textContent = '—';
                document.getElementById('out-degree').textContent = '—';
            }}
        }}

        function showNodeInfo(nodeId) {{
            const data = nodeData[nodeId];
            const subgraph = subgraphData[nodeId];
            if (!data) return;

            document.getElementById('info-title').textContent = nodeId + ': ' + data.funcionalidad;
            document.getElementById('info-content').innerHTML = `
                <p><strong>Área:</strong> ${{data.area}}</p>
                <p><strong>Prioridad:</strong> ${{data.prioridad}}</p>
                <p><strong>Versión:</strong> ${{data.version}}</p>
                <p><strong>Estatus:</strong> ${{data.estatus}}</p>
                <p><strong>Owner:</strong> ${{data.owner}}</p>
                <hr style="border-color: #4a4a6a; margin: 10px 0;">
                <p><strong>Dependencias directas:</strong> ${{data.in_degree}}</p>
                <p><strong>Dependientes directos:</strong> ${{data.out_degree}}</p>
                <p><strong>Total ancestros:</strong> ${{subgraph.ancestors.length}}</p>
                <p><strong>Total descendientes:</strong> ${{subgraph.descendants.length}}</p>
            `;
            document.getElementById('node-info').style.display = 'block';
        }}

        function closeNodeInfo() {{
            document.getElementById('node-info').style.display = 'none';
        }}

        // Layout switching
        function setLayout(layout) {{
            currentLayout = layout;

            // Update button states
            document.getElementById('layout-force').classList.toggle('active', layout === 'force');
            document.getElementById('layout-tree').classList.toggle('active', layout === 'tree');

            if (layout === 'tree') {{
                // Hierarchical layout
                network.setOptions({{
                    layout: {{
                        hierarchical: {{
                            enabled: true,
                            direction: 'UD',
                            sortMethod: 'directed',
                            levelSeparation: 120,
                            nodeSpacing: 150,
                            treeSpacing: 200,
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
                // Force-directed layout
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
                        }},
                        stabilization: {{
                            enabled: true,
                            iterations: 200,
                            updateInterval: 25
                        }}
                    }}
                }});
            }}

            // Fit view after layout change
            setTimeout(() => {{
                network.fit({{ animation: {{ duration: 500 }} }});
            }}, 300);
        }}

        function focusNode() {{
            const nodeId = document.getElementById('node-search').value.toUpperCase();
            if (nodes.get(nodeId)) {{
                network.focus(nodeId, {{
                    scale: 1.5,
                    animation: {{ duration: 500, easingFunction: 'easeInOutQuad' }}
                }});
                network.selectNodes([nodeId]);
                selectedNodeId = nodeId;
                updateStats(nodeId);
                showNodeInfo(nodeId);
            }} else {{
                alert('Nodo no encontrado: ' + nodeId);
            }}
        }}

        function filterByArea(area) {{
            document.getElementById('area-filter').value = area;
            applyFilters();
        }}

        function applyFilters() {{
            const areaFilter = document.getElementById('area-filter').value;
            const priorityFilter = document.getElementById('priority-filter').value;
            const versionFilter = document.getElementById('version-filter').value;

            if (!allNodes) allNodes = nodes.get();
            if (!allEdges) allEdges = edges.get();

            // Filter nodes
            const visibleNodeIds = new Set();
            allNodes.forEach(node => {{
                const data = nodeData[node.id];
                if (!data) return;

                const matchArea = !areaFilter || data.area === areaFilter;
                const matchPriority = !priorityFilter || data.prioridad === priorityFilter;
                const matchVersion = !versionFilter || data.version === versionFilter;

                if (matchArea && matchPriority && matchVersion) {{
                    visibleNodeIds.add(node.id);
                }}
            }});

            // Update node visibility
            const updates = allNodes.map(node => ({{
                id: node.id,
                hidden: !visibleNodeIds.has(node.id)
            }}));
            nodes.update(updates);

            // Update edge visibility
            const edgeUpdates = allEdges.map(edge => ({{
                id: edge.id,
                hidden: !visibleNodeIds.has(edge.from) || !visibleNodeIds.has(edge.to)
            }}));
            edges.update(edgeUpdates);

            // Update stats
            const visibleEdges = allEdges.filter(e =>
                visibleNodeIds.has(e.from) && visibleNodeIds.has(e.to)
            ).length;

            document.getElementById('visible-nodes').textContent = visibleNodeIds.size;
            document.getElementById('visible-edges').textContent = visibleEdges;
        }}

        function showAncestors() {{
            if (!selectedNodeId) {{
                alert('Selecciona un nodo primero');
                return;
            }}
            showAncestorsOf(selectedNodeId);
        }}

        function showAncestorsOf(nodeId) {{
            const ancestors = subgraphData[nodeId]?.ancestors || [];
            const visibleIds = new Set([nodeId, ...ancestors]);
            showSubgraph(visibleIds, 'Dependencias de ' + nodeId);
        }}

        function showDescendants() {{
            if (!selectedNodeId) {{
                alert('Selecciona un nodo primero');
                return;
            }}
            showDescendantsOf(selectedNodeId);
        }}

        function showDescendantsOf(nodeId) {{
            const descendants = subgraphData[nodeId]?.descendants || [];
            const visibleIds = new Set([nodeId, ...descendants]);
            showSubgraph(visibleIds, 'Dependientes de ' + nodeId);
        }}

        function showNeighborhood() {{
            if (!selectedNodeId) {{
                alert('Selecciona un nodo primero');
                return;
            }}

            // Get immediate neighbors only (depth 1)
            const neighbors = new Set([selectedNodeId]);
            allEdges.forEach(edge => {{
                if (edge.from === selectedNodeId) neighbors.add(edge.to);
                if (edge.to === selectedNodeId) neighbors.add(edge.from);
            }});

            showSubgraph(neighbors, 'Vecindario de ' + selectedNodeId);
        }}

        function showSubgraph(visibleIds, title) {{
            if (!allNodes) allNodes = nodes.get();
            if (!allEdges) allEdges = edges.get();

            // Update nodes
            const updates = allNodes.map(node => ({{
                id: node.id,
                hidden: !visibleIds.has(node.id)
            }}));
            nodes.update(updates);

            // Update edges
            const edgeUpdates = allEdges.map(edge => ({{
                id: edge.id,
                hidden: !visibleIds.has(edge.from) || !visibleIds.has(edge.to)
            }}));
            edges.update(edgeUpdates);

            // Update stats
            const visibleEdges = allEdges.filter(e =>
                visibleIds.has(e.from) && visibleIds.has(e.to)
            ).length;

            document.getElementById('visible-nodes').textContent = visibleIds.size;
            document.getElementById('visible-edges').textContent = visibleEdges;

            // Fit view
            network.fit({{ animation: {{ duration: 500 }} }});
        }}

        function resetView() {{
            // Clear filters
            document.getElementById('area-filter').value = '';
            document.getElementById('priority-filter').value = '';
            document.getElementById('version-filter').value = '';
            document.getElementById('node-search').value = '';

            if (!allNodes) allNodes = nodes.get();
            if (!allEdges) allEdges = edges.get();

            // Show all nodes
            const updates = allNodes.map(node => ({{ id: node.id, hidden: false }}));
            nodes.update(updates);

            // Show all edges
            const edgeUpdates = allEdges.map(edge => ({{ id: edge.id, hidden: false }}));
            edges.update(edgeUpdates);

            // Update stats
            document.getElementById('visible-nodes').textContent = allNodes.length;
            document.getElementById('visible-edges').textContent = allEdges.length;

            // Deselect
            network.unselectAll();
            selectedNodeId = null;
            updateStats(null);
            closeNodeInfo();

            // Reset layout to force if needed and fit view
            if (currentLayout === 'force') {{
                network.stabilize();
            }}
            network.fit({{ animation: {{ duration: 500 }} }});
        }}

        // Add event listeners to filters
        document.getElementById('area-filter').addEventListener('change', applyFilters);
        document.getElementById('priority-filter').addEventListener('change', applyFilters);
        document.getElementById('version-filter').addEventListener('change', applyFilters);

        // Enter key for search
        document.getElementById('node-search').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') focusNode();
        }});
    </script>
    """
    
    # Inject into HTML
    html_content = html_content.replace('</head>', custom_css + '</head>')
    html_content = html_content.replace('<body>', '<body>' + custom_controls)
    html_content = html_content.replace('</body>', custom_js + '</body>')
    
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
