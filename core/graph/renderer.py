"""
core/graph/renderer.py — Converts the NetworkX graph to interactive HTML.

What this produces:
  A self-contained HTML string that renders an interactive dependency graph.
  Users can:
    - Click and drag nodes
    - Zoom in/out with scroll wheel
    - Hover nodes to see file details
    - See edges (arrows) showing import direction

How it works:
  NetworkX builds the graph structure (nodes + edges).
  Pyvis converts that structure into a vis.js-powered HTML page.
  vis.js is a JavaScript library for interactive network visualisation.
  Pyvis bundles vis.js into the output HTML — no external CDN needed.

  The frontend receives this HTML string and renders it in an <iframe>.
  The entire interactive graph is self-contained in that one HTML string.

Visual design decisions:
  Node colour by language:
    Python     → blue  (#4B8BBE — Python's brand colour)
    JavaScript → yellow (#F7DF1E — JS's brand colour)
    TypeScript → blue-ish (#3178C6 — TS's brand colour)
    Default    → grey

  Node size by in-degree:
    Files imported by many others are larger.
    This makes "core" files visually prominent at a glance.
    Minimum size 15, scales up by 5 per incoming edge, capped at 50.

  Edge direction:
    Arrow points FROM importer TO imported file.
    "A → B" means "A imports B".
"""

import os
import networkx as nx
from pyvis.network import Network


# Colour scheme by language
LANGUAGE_COLOURS = {
    "python":     "#4B8BBE",
    "javascript": "#F7DF1E",
    "typescript": "#3178C6",
    "default":    "#888780",
}

# Colour for nodes with circular dependencies (highlights problem files)
CYCLE_COLOUR = "#E24B4A"


def _get_node_size(in_degree: int) -> int:
    """
    Scale node size based on how many files import it.
    More depended-on = bigger node = visually prominent.
    """
    base = 15
    per_edge = 5
    cap = 50
    return min(base + (in_degree * per_edge), cap)


def render_graph_html(G: nx.DiGraph) -> str:
    """
    Convert a NetworkX DiGraph to a self-contained interactive HTML string.

    Args:
        G: The dependency graph from builder.py

    Returns:
        HTML string. The frontend puts this in an <iframe srcdoc="...">.

    If the graph is empty (no files found), returns a simple
    "no data" HTML page rather than an empty graph.
    """

    if G.number_of_nodes() == 0:
        return """
        <html><body style="font-family:sans-serif;color:#888;
        display:flex;align-items:center;justify-content:center;height:100vh;">
        <p>No dependency graph available. Index a repo first.</p>
        </body></html>
        """

    # -----------------------------------------------------------------------
    # Detect which nodes are part of circular dependencies.
    # We'll colour these red to make them immediately visible.
    # -----------------------------------------------------------------------
    cycle_nodes = set()
    for cycle in nx.simple_cycles(G):
        cycle_nodes.update(cycle)

    # -----------------------------------------------------------------------
    # Create Pyvis Network object.
    #
    # height/width: fills the iframe container
    # directed=True: shows arrows on edges (import direction)
    # notebook=False: generates standalone HTML (not Jupyter output)
    # bgcolor: dark background — looks professional
    # font_color: light text for dark background
    # -----------------------------------------------------------------------
    net = Network(
        height="100%",
        width="100%",
        directed=True,
        notebook=False,
        bgcolor="#1a1a2e",
        font_color="#e0e0e0",
    )

    # -----------------------------------------------------------------------
    # Add nodes to the Pyvis network.
    # For each node in the NetworkX graph, create a Pyvis node with:
    #   - label: shortened filename (not full path — too long)
    #   - title: full path shown on hover
    #   - color: by language or red if in a cycle
    #   - size:  scaled by in-degree
    #   - shape: dot (default circle)
    # -----------------------------------------------------------------------
    in_degrees = dict(G.in_degree())

    for node, attrs in G.nodes(data=True):
        language = attrs.get("language", "default")
        in_deg   = in_degrees.get(node, 0)

        # Use just the filename as the label (keeps graph readable)
        # Full path in the hover tooltip
        label = os.path.basename(node)

        # Red if circular dependency, otherwise language colour
        colour = CYCLE_COLOUR if node in cycle_nodes else LANGUAGE_COLOURS.get(
            language, LANGUAGE_COLOURS["default"]
        )

        size = _get_node_size(in_deg)

        # Hover tooltip — shown when user mouses over a node
        title = (
            f"<b>{node}</b><br>"
            f"Language: {language}<br>"
            f"Imported by: {in_deg} file(s)<br>"
            f"{'⚠️ Part of circular dependency' if node in cycle_nodes else ''}"
        )

        net.add_node(
            node,          # node ID (unique)
            label=label,   # displayed text
            title=title,   # hover tooltip (HTML supported)
            color=colour,
            size=size,
            shape="dot",
        )

    # -----------------------------------------------------------------------
    # Add edges to the Pyvis network.
    # Each edge is a directed arrow: importer → imported
    # -----------------------------------------------------------------------
    for source, target in G.edges():
        # Highlight edges that are part of cycles
        is_cycle_edge = source in cycle_nodes and target in cycle_nodes
        edge_colour = CYCLE_COLOUR if is_cycle_edge else "#555577"

        net.add_edge(
            source,
            target,
            color=edge_colour,
            arrows="to",         # arrowhead at the target end
            width=1.5,
        )

    # -----------------------------------------------------------------------
    # Physics configuration — controls how the graph lays itself out.
    #
    # We use the "forceAtlas2Based" solver:
    #   - Pulls connected nodes together
    #   - Pushes unconnected nodes apart
    #   - Produces a natural clustering layout
    #
    # stabilization: run physics simulation until stable, then freeze.
    # This prevents the graph from jiggling after load.
    # -----------------------------------------------------------------------
    net.set_options("""
    {
      "physics": {
        "enabled": true,
        "forceAtlas2Based": {
          "gravitationalConstant": -50,
          "centralGravity": 0.01,
          "springLength": 120,
          "springConstant": 0.08
        },
        "solver": "forceAtlas2Based",
        "stabilization": {
          "enabled": true,
          "iterations": 200,
          "fit": true
        }
      },
      "edges": {
        "smooth": {
          "type": "curvedCW",
          "roundness": 0.2
        }
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 100,
        "zoomView": true,
        "dragView": true
      }
    }
    """)

    # -----------------------------------------------------------------------
    # Generate the HTML.
    #
    # net.generate_html() returns a complete HTML document string.
    # We use this instead of net.write_html() (which writes to a file)
    # because we want to return the HTML as a string from our API.
    #
    # The frontend will put this in an <iframe srcdoc="..."> tag.
    # -----------------------------------------------------------------------
    html_content = net.generate_html()

    return html_content