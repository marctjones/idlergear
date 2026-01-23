"""Knowledge graph visualization and export capabilities."""

from pathlib import Path
from typing import Optional, Dict, Any, List, Literal
import json
from datetime import datetime

from .database import GraphDatabase


class GraphVisualizer:
    """Generate visual representations of knowledge graph structure.

    Supports multiple export formats:
    - GraphML: For Gephi, Cytoscape, yEd
    - DOT: For Graphviz (PNG, SVG, PDF)
    - JSON: For custom visualization
    - D3.js data format: For web visualizations

    Example:
        >>> from idlergear.graph import get_database
        >>> from idlergear.graph.visualize import GraphVisualizer
        >>> db = get_database()
        >>> viz = GraphVisualizer(db)
        >>> viz.export_graphml("output.graphml", node_types=["Task", "File"])
    """

    def __init__(self, db: GraphDatabase):
        """Initialize visualizer.

        Args:
            db: Graph database instance
        """
        self.db = db

    def export_graphml(
        self,
        output_path: Path | str,
        node_types: Optional[List[str]] = None,
        relationship_types: Optional[List[str]] = None,
        max_nodes: int = 1000,
    ) -> Dict[str, int]:
        """Export graph to GraphML format for external tools.

        GraphML is supported by Gephi, Cytoscape, yEd, and other tools.

        Args:
            output_path: Path to output file
            node_types: Filter by node types (None = all types)
            relationship_types: Filter by relationship types (None = all types)
            max_nodes: Maximum nodes to export (prevents huge files)

        Returns:
            Dictionary with counts: nodes, edges
        """
        output_path = Path(output_path)
        conn = self.db.get_connection()

        # Collect nodes
        nodes = self._collect_nodes(conn, node_types, max_nodes)

        # Collect edges
        edges = self._collect_edges(conn, relationship_types, [n["id"] for n in nodes])

        # Generate GraphML
        graphml = self._generate_graphml(nodes, edges)

        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(graphml)

        return {
            "nodes": len(nodes),
            "edges": len(edges),
            "output": str(output_path),
        }

    def export_dot(
        self,
        output_path: Path | str,
        node_types: Optional[List[str]] = None,
        relationship_types: Optional[List[str]] = None,
        max_nodes: int = 100,
        layout: Literal["dot", "neato", "fdp", "circo", "twopi"] = "dot",
    ) -> Dict[str, int]:
        """Export graph to DOT format for Graphviz.

        Can be rendered to PNG, SVG, PDF with graphviz tools.

        Args:
            output_path: Path to output .dot file
            node_types: Filter by node types
            relationship_types: Filter by relationship types
            max_nodes: Maximum nodes (DOT renders poorly with >100 nodes)
            layout: Graphviz layout engine

        Returns:
            Dictionary with counts and render command
        """
        output_path = Path(output_path)
        conn = self.db.get_connection()

        # Collect nodes
        nodes = self._collect_nodes(conn, node_types, max_nodes)

        # Collect edges
        edges = self._collect_edges(conn, relationship_types, [n["id"] for n in nodes])

        # Generate DOT
        dot = self._generate_dot(nodes, edges, layout)

        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(dot)

        return {
            "nodes": len(nodes),
            "edges": len(edges),
            "output": str(output_path),
            "render_command": f"{layout} -Tpng {output_path} -o {output_path.with_suffix('.png')}",
        }

    def export_json(
        self,
        output_path: Path | str,
        node_types: Optional[List[str]] = None,
        relationship_types: Optional[List[str]] = None,
        max_nodes: int = 1000,
        format: Literal["raw", "d3"] = "raw",
    ) -> Dict[str, int]:
        """Export graph to JSON format.

        Args:
            output_path: Path to output .json file
            node_types: Filter by node types
            relationship_types: Filter by relationship types
            max_nodes: Maximum nodes to export
            format: 'raw' for direct export, 'd3' for D3.js force layout

        Returns:
            Dictionary with counts
        """
        output_path = Path(output_path)
        conn = self.db.get_connection()

        # Collect nodes
        nodes = self._collect_nodes(conn, node_types, max_nodes)

        # Collect edges
        edges = self._collect_edges(conn, relationship_types, [n["id"] for n in nodes])

        # Format data
        if format == "d3":
            data = self._format_d3(nodes, edges)
        else:
            data = {
                "nodes": nodes,
                "edges": edges,
                "metadata": {
                    "exported_at": datetime.now().isoformat(),
                    "node_types": node_types,
                    "relationship_types": relationship_types,
                },
            }

        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(data, indent=2))

        return {
            "nodes": len(nodes),
            "edges": len(edges),
            "output": str(output_path),
        }

    def visualize_task_network(
        self,
        task_id: int,
        output_path: Path | str,
        depth: int = 2,
        format: Literal["graphml", "dot", "json"] = "dot",
    ) -> Dict[str, int]:
        """Visualize task and its connected nodes (commits, files, symbols).

        Args:
            task_id: Task ID to visualize
            output_path: Output file path
            depth: How many hops from task (1=direct, 2=2nd degree)
            format: Output format

        Returns:
            Dictionary with counts
        """
        conn = self.db.get_connection()

        # Get task and connected nodes
        nodes, edges = self._get_task_neighborhood(conn, task_id, depth)

        # Export based on format
        if format == "graphml":
            graphml = self._generate_graphml(nodes, edges)
            Path(output_path).write_text(graphml)
        elif format == "dot":
            dot = self._generate_dot(nodes, edges, "dot")
            Path(output_path).write_text(dot)
        else:  # json
            data = {"nodes": nodes, "edges": edges}
            Path(output_path).write_text(json.dumps(data, indent=2))

        return {
            "nodes": len(nodes),
            "edges": len(edges),
            "output": str(output_path),
        }

    def visualize_dependency_graph(
        self,
        file_path: str,
        output_path: Path | str,
        depth: int = 2,
        format: Literal["graphml", "dot", "json"] = "dot",
    ) -> Dict[str, int]:
        """Visualize file dependencies (imports, calls).

        Args:
            file_path: Starting file path
            output_path: Output file path
            depth: How many import/call hops to follow
            format: Output format

        Returns:
            Dictionary with counts
        """
        conn = self.db.get_connection()

        # Get file and dependencies
        nodes, edges = self._get_dependency_neighborhood(conn, file_path, depth)

        # Export based on format
        if format == "graphml":
            graphml = self._generate_graphml(nodes, edges)
            Path(output_path).write_text(graphml)
        elif format == "dot":
            dot = self._generate_dot(nodes, edges, "dot")
            Path(output_path).write_text(dot)
        else:  # json
            data = {"nodes": nodes, "edges": edges}
            Path(output_path).write_text(json.dumps(data, indent=2))

        return {
            "nodes": len(nodes),
            "edges": len(edges),
            "output": str(output_path),
        }

    def _collect_nodes(
        self,
        conn,
        node_types: Optional[List[str]],
        max_nodes: int,
    ) -> List[Dict[str, Any]]:
        """Collect nodes from database."""
        nodes = []

        # Default to common types if none specified
        if node_types is None:
            node_types = ["Task", "File", "Symbol", "Commit"]

        for node_type in node_types:
            try:
                # Query nodes with LIMIT
                query = f"MATCH (n:{node_type}) RETURN n LIMIT {max_nodes - len(nodes)}"
                result = conn.execute(query)

                while result.has_next():
                    row = result.get_next()
                    node_data = row[0]

                    # Convert to dict
                    node = {
                        "id": self._get_node_id(node_data, node_type),
                        "type": node_type,
                        "label": self._get_node_label(node_data, node_type),
                        "properties": self._extract_properties(node_data),
                    }
                    nodes.append(node)

                    if len(nodes) >= max_nodes:
                        break

            except Exception as e:
                print(f"Error collecting {node_type} nodes: {e}")

            if len(nodes) >= max_nodes:
                break

        return nodes

    def _collect_edges(
        self,
        conn,
        relationship_types: Optional[List[str]],
        node_ids: List[str],
    ) -> List[Dict[str, Any]]:
        """Collect edges between collected nodes."""
        edges = []

        # Convert node_ids to set for faster lookup
        node_id_set = set(node_ids)

        # Default relationship types
        if relationship_types is None:
            relationship_types = ["MODIFIES", "CONTAINS", "IMPORTS", "CALLS", "IMPLEMENTED_IN"]

        for rel_type in relationship_types:
            try:
                # Query relationships
                query = f"MATCH (a)-[r:{rel_type}]->(b) RETURN a, r, b LIMIT 5000"
                result = conn.execute(query)

                while result.has_next():
                    row = result.get_next()
                    source_node = row[0]
                    rel = row[1]
                    target_node = row[2]

                    # Get source/target IDs (need to infer type)
                    source_id = self._infer_node_id(source_node)
                    target_id = self._infer_node_id(target_node)

                    # Only include edges between collected nodes
                    if source_id in node_id_set and target_id in node_id_set:
                        edge = {
                            "source": source_id,
                            "target": target_id,
                            "type": rel_type,
                            "properties": self._extract_properties(rel),
                        }
                        edges.append(edge)

            except Exception as e:
                print(f"Error collecting {rel_type} relationships: {e}")

        return edges

    def _get_node_id(self, node_data: Any, node_type: str) -> str:
        """Get unique ID for a node."""
        # Extract primary key based on node type
        if node_type == "Task":
            return f"task_{node_data['id']}"
        elif node_type == "File":
            return f"file_{node_data['path']}"
        elif node_type == "Symbol":
            return f"symbol_{node_data['id']}"
        elif node_type == "Commit":
            return f"commit_{node_data['hash']}"
        elif node_type == "Person":
            return f"person_{node_data['email']}"
        elif node_type == "Dependency":
            return f"dep_{node_data['name']}"
        elif node_type == "Test":
            return f"test_{node_data['id']}"
        else:
            # Fallback: try common ID fields
            for field in ['id', 'path', 'name', 'hash', 'email']:
                if field in node_data:
                    return f"{node_type.lower()}_{node_data[field]}"
            return f"{node_type.lower()}_unknown"

    def _infer_node_id(self, node_data: Any) -> str:
        """Infer node ID without knowing type."""
        # Try to infer from available fields
        if 'hash' in node_data:
            return f"commit_{node_data['hash']}"
        elif 'path' in node_data:
            return f"file_{node_data['path']}"
        elif 'email' in node_data:
            return f"person_{node_data['email']}"
        elif 'id' in node_data:
            # Could be task, symbol, test, etc.
            # Check other fields to disambiguate
            if 'title' in node_data:
                return f"task_{node_data['id']}"
            elif 'name' in node_data and 'file_path' in node_data:
                return f"symbol_{node_data['id']}"
            else:
                return f"node_{node_data['id']}"
        elif 'name' in node_data:
            return f"dep_{node_data['name']}"
        return "unknown"

    def _get_node_label(self, node_data: Any, node_type: str) -> str:
        """Get display label for node."""
        if node_type == "Task":
            return node_data.get('title', 'Untitled Task')
        elif node_type == "File":
            path = node_data.get('path', '')
            return Path(path).name if path else 'Unknown File'
        elif node_type == "Symbol":
            return node_data.get('name', 'Unknown Symbol')
        elif node_type == "Commit":
            return node_data.get('short_hash', node_data.get('hash', '')[:7])
        elif node_type == "Person":
            return node_data.get('name', node_data.get('email', 'Unknown'))
        elif node_type == "Dependency":
            return node_data.get('name', 'Unknown Dependency')
        elif node_type == "Test":
            return node_data.get('name', 'Unknown Test')
        else:
            return node_data.get('name', node_data.get('title', str(node_data)))

    def _extract_properties(self, data: Any) -> Dict[str, Any]:
        """Extract properties from node/edge data."""
        props = {}
        if isinstance(data, dict):
            for key, value in data.items():
                # Skip null values and internal fields
                if value is not None and not key.startswith('_'):
                    # Convert complex types to strings
                    if isinstance(value, (datetime, list)):
                        props[key] = str(value)
                    else:
                        props[key] = value
        return props

    def _generate_graphml(self, nodes: List[Dict], edges: List[Dict]) -> str:
        """Generate GraphML XML format."""
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
            '  <key id="type" for="node" attr.name="type" attr.type="string"/>',
            '  <key id="label" for="node" attr.name="label" attr.type="string"/>',
            '  <key id="rel_type" for="edge" attr.name="type" attr.type="string"/>',
            '  <graph id="G" edgedefault="directed">',
        ]

        # Add nodes
        for node in nodes:
            lines.append(f'    <node id="{node["id"]}">')
            lines.append(f'      <data key="type">{node["type"]}</data>')
            lines.append(f'      <data key="label">{self._escape_xml(node["label"])}</data>')
            lines.append('    </node>')

        # Add edges
        for i, edge in enumerate(edges):
            lines.append(f'    <edge id="e{i}" source="{edge["source"]}" target="{edge["target"]}">')
            lines.append(f'      <data key="rel_type">{edge["type"]}</data>')
            lines.append('    </edge>')

        lines.append('  </graph>')
        lines.append('</graphml>')

        return '\n'.join(lines)

    def _generate_dot(self, nodes: List[Dict], edges: List[Dict], layout: str) -> str:
        """Generate DOT format for Graphviz."""
        lines = [
            f'digraph G {{',
            f'  layout={layout};',
            '  node [shape=box, style=filled];',
            '',
        ]

        # Add nodes with colors by type
        colors = {
            "Task": "lightblue",
            "File": "lightgreen",
            "Symbol": "lightyellow",
            "Commit": "lightpink",
            "Person": "lightcoral",
            "Dependency": "lightgray",
            "Test": "lavender",
        }

        for node in nodes:
            color = colors.get(node["type"], "white")
            label = self._escape_dot(node["label"])
            lines.append(f'  "{node["id"]}" [label="{label}", fillcolor={color}];')

        lines.append('')

        # Add edges
        for edge in edges:
            label = edge["type"]
            lines.append(f'  "{edge["source"]}" -> "{edge["target"]}" [label="{label}"];')

        lines.append('}')

        return '\n'.join(lines)

    def _format_d3(self, nodes: List[Dict], edges: List[Dict]) -> Dict[str, Any]:
        """Format data for D3.js force-directed layout."""
        # Map node IDs to indices
        node_index = {node["id"]: i for i, node in enumerate(nodes)}

        # Format nodes
        d3_nodes = [
            {
                "id": node["id"],
                "name": node["label"],
                "type": node["type"],
                "properties": node["properties"],
            }
            for node in nodes
        ]

        # Format links (D3 uses source/target indices)
        d3_links = []
        for edge in edges:
            if edge["source"] in node_index and edge["target"] in node_index:
                d3_links.append({
                    "source": node_index[edge["source"]],
                    "target": node_index[edge["target"]],
                    "type": edge["type"],
                })

        return {
            "nodes": d3_nodes,
            "links": d3_links,
        }

    def _get_task_neighborhood(self, conn, task_id: int, depth: int) -> tuple:
        """Get nodes and edges around a task."""
        nodes = []
        edges = []

        # Get task node
        try:
            result = conn.execute(
                "MATCH (t:Task {id: $id}) RETURN t",
                {"id": task_id}
            )
            if result.has_next():
                task_data = result.get_next()[0]
                nodes.append({
                    "id": f"task_{task_id}",
                    "type": "Task",
                    "label": task_data.get('title', 'Task'),
                    "properties": self._extract_properties(task_data),
                })
        except Exception as e:
            print(f"Error getting task: {e}")
            return nodes, edges

        # Get connected nodes (files, commits, etc.)
        if depth >= 1:
            # Get files modified by task
            try:
                result = conn.execute("""
                    MATCH (t:Task {id: $id})-[r:MODIFIES]->(f:File)
                    RETURN f, r
                """, {"id": task_id})

                while result.has_next():
                    row = result.get_next()
                    file_data = row[0]
                    file_id = f"file_{file_data['path']}"

                    nodes.append({
                        "id": file_id,
                        "type": "File",
                        "label": Path(file_data['path']).name,
                        "properties": self._extract_properties(file_data),
                    })

                    edges.append({
                        "source": f"task_{task_id}",
                        "target": file_id,
                        "type": "MODIFIES",
                        "properties": {},
                    })
            except Exception as e:
                print(f"Error getting files: {e}")

        return nodes, edges

    def _get_dependency_neighborhood(self, conn, file_path: str, depth: int) -> tuple:
        """Get nodes and edges around a file (dependencies)."""
        nodes = []
        edges = []

        # Get file node
        try:
            result = conn.execute(
                "MATCH (f:File {path: $path}) RETURN f",
                {"path": file_path}
            )
            if result.has_next():
                file_data = result.get_next()[0]
                nodes.append({
                    "id": f"file_{file_path}",
                    "type": "File",
                    "label": Path(file_path).name,
                    "properties": self._extract_properties(file_data),
                })
        except Exception as e:
            print(f"Error getting file: {e}")
            return nodes, edges

        # Get imports
        if depth >= 1:
            try:
                result = conn.execute("""
                    MATCH (f:File {path: $path})-[r:IMPORTS]->(imported:File)
                    RETURN imported, r
                """, {"path": file_path})

                while result.has_next():
                    row = result.get_next()
                    imported_data = row[0]
                    imported_id = f"file_{imported_data['path']}"

                    nodes.append({
                        "id": imported_id,
                        "type": "File",
                        "label": Path(imported_data['path']).name,
                        "properties": self._extract_properties(imported_data),
                    })

                    edges.append({
                        "source": f"file_{file_path}",
                        "target": imported_id,
                        "type": "IMPORTS",
                        "properties": {},
                    })
            except Exception as e:
                print(f"Error getting imports: {e}")

        return nodes, edges

    def _escape_xml(self, text: str) -> str:
        """Escape special characters for XML."""
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    def _escape_dot(self, text: str) -> str:
        """Escape special characters for DOT format."""
        return str(text).replace('"', '\\"').replace('\n', '\\n')
