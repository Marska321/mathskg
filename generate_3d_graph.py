import json

# 1. Load the Grade 4 Knowledge Graph
try:
    with open('caps_graph.json', 'r') as f:
        skills = json.load(f)
except FileNotFoundError:
    print("Error: 'caps_graph.json' not found. Please ensure it is in the same directory.")
    exit()

# 2. Format the data for the 3D Force Graph library
nodes = []
links = []

# Domain color mapping to easily identify the different CAPS trunks
domain_colors = {
    'N': '#4CAF50', # Whole Numbers (Green)
    'F': '#2196F3', # Fractions (Blue)
    'M': '#FF9800', # Measurement (Orange)
    'G': '#9C27B0', # Geometry (Purple)
    'P': '#E91E63', # Patterns/Algebra (Pink)
    'D': '#00BCD4'  # Data Handling (Cyan)
}

for skill in skills:
    # Extract domain code (e.g., 'N' from 'M4-N-001')
    domain_code = skill['skill_id'].split('-')[1]
    color = domain_colors.get(domain_code, '#ffffff')
    
    # Scale node size slightly by difficulty
    difficulty = skill.get('difficulty', 2.0)
    
    nodes.append({
        "id": skill['skill_id'],
        "name": f"{skill['skill_id']}: {skill['skill_name']} (Difficulty: {difficulty})",
        "color": color,
        "val": difficulty 
    })
    
    # Add directional edges for prerequisites
    for prereq in skill.get('prerequisites', []):
        links.append({
            "source": prereq,
            "target": skill['skill_id']
        })

graph_data = {
    "nodes": nodes,
    "links": links
}

# 3. Create the HTML template injecting the WebGL library and our JSON data
html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Lumen Grade 4 Knowledge Graph</title>
  <style> 
    body {{ margin: 0; overflow: hidden; background-color: #000011; font-family: sans-serif; }} 
    #info {{ position: absolute; top: 15px; left: 15px; color: rgba(255,255,255,0.8); z-index: 10; pointer-events: none; }}
  </style>
  <script src="https://cdn.jsdelivr.net/npm/3d-force-graph"></script>
</head>
<body>
  <div id="info">
    <h2>Lumen Knowledge Graph</h2>
    <p>Scroll to zoom, drag to rotate space, hover over nodes for details.</p>
  </div>
  <div id="3d-graph"></div>

  <script>
    const gData = {json.dumps(graph_data)};

    const Graph = ForceGraph3D()
      (document.getElementById('3d-graph'))
        .graphData(gData)
        .nodeLabel('name')
        .nodeColor('color')
        .nodeRelSize(4)
        .linkDirectionalArrowLength(3.5)
        .linkDirectionalArrowRelPos(1)
        .linkColor(() => 'rgba(255, 255, 255, 0.2)');

    // Slowly rotate the camera to visualize the trunks naturally
    let angle = 0;
    setInterval(() => {{
      Graph.cameraPosition({{
        x: 400 * Math.sin(angle),
        z: 400 * Math.cos(angle)
      }});
      angle += Math.PI / 1500;
    }}, 10);
  </script>
</body>
</html>
"""

# 4. Save the HTML file
output_filename = 'lumen_3d_graph.html'
with open(output_filename, 'w') as f:
    f.write(html_content)

print(f"3D Graph successfully generated! Open '{output_filename}' in your web browser.")