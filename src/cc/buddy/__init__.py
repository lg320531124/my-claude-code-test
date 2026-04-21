"""Buddy Module - AI visual companion for codebase visualization.

Provides visual representation of:
- Code structure
- Dependencies
- Architecture
- Execution flow
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum


class VisualizationType(Enum):
    """Visualization types."""
    ARCHITECTURE = "architecture"
    DEPENDENCIES = "dependencies"
    FLOW = "flow"
    STRUCTURE = "structure"
    METRICS = "metrics"
    DIFF = "diff"


@dataclass
class Node:
    """Graph node."""
    id: str
    name: str
    type: str  # file, module, class, function
    path: str
    dependencies: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    color: str = "#4A90D9"
    size: int = 50


@dataclass
class Edge:
    """Graph edge."""
    source: str
    target: str
    type: str  # import, call, inheritance
    weight: int = 1
    color: str = "#999"


@dataclass
class VisualizationGraph:
    """Graph for visualization."""
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    layout: str = "force-directed"  # force-directed, hierarchical, circular


class BuddyVisualizer:
    """AI visual companion."""

    def __init__(self):
        self._graphs: Dict[str, VisualizationGraph] = {}

    async def analyze_architecture(self, root_path: Path) -> VisualizationGraph:
        """Analyze code architecture."""
        graph = VisualizationGraph(layout="hierarchical")
        nodes = {}
        edges = []

        # Scan files
        for filepath in root_path.rglob("*.py"):
            module_name = str(filepath.relative_to(root_path)).replace("/", ".").replace(".py", "")

            node = Node(
                id=module_name,
                name=filepath.stem,
                type="module",
                path=str(filepath),
            )
            nodes[module_name] = node
            graph.nodes.append(node)

        # Analyze imports
        for filepath in root_path.rglob("*.py"):
            content = await self._read_file(filepath)
            imports = self._extract_imports(content)

            source_module = str(filepath.relative_to(root_path)).replace("/", ".").replace(".py", "")
            for imp in imports:
                if imp in nodes:
                    edge = Edge(source=source_module, target=imp, type="import")
                    edges.append(edge)
                    nodes[source_module].dependencies.append(imp)

        graph.edges = edges
        self._graphs["architecture"] = graph
        return graph

    async def analyze_dependencies(self, root_path: Path) -> VisualizationGraph:
        """Analyze dependencies."""
        graph = VisualizationGraph(layout="force-directed")
        nodes = {}
        edges = []

        # Parse imports
        for filepath in root_path.rglob("*.py"):
            content = await self._read_file(filepath)
            imports = self._extract_imports(content)

            module_name = filepath.stem
            node = Node(
                id=module_name,
                name=module_name,
                type="file",
                path=str(filepath),
            )
            nodes[module_name] = node
            graph.nodes.append(node)

            for imp in imports:
                if imp.startswith("src.cc") or imp.startswith("cc"):
                    target = imp.split(".")[-1]
                    if target not in nodes:
                        target_node = Node(
                            id=target,
                            name=target,
                            type="module",
                            path=imp,
                        )
                        nodes[target] = target_node
                        graph.nodes.append(target_node)

                    edge = Edge(source=module_name, target=target, type="import")
                    edges.append(edge)

        graph.edges = edges
        self._graphs["dependencies"] = graph
        return graph

    async def analyze_flow(self, entry_point: Path) -> VisualizationGraph:
        """Analyze execution flow."""
        graph = VisualizationGraph(layout="flow")
        nodes = []
        edges = []

        # Trace execution
        content = await self._read_file(entry_point)
        functions = self._extract_functions(content)

        for func in functions:
            node = Node(
                id=func,
                name=func,
                type="function",
                path=str(entry_point),
            )
            nodes.append(node)

        # Add edges based on call order (simplified)
        for i in range(len(nodes) - 1):
            edge = Edge(source=nodes[i].id, target=nodes[i + 1].id, type="call")
            edges.append(edge)

        graph.nodes = nodes
        graph.edges = edges
        self._graphs["flow"] = graph
        return graph

    async def visualize_diff(self, before: str, after: str) -> VisualizationGraph:
        """Visualize diff."""
        graph = VisualizationGraph()

        # Parse changes
        before_lines = before.splitlines()
        after_lines = after.splitlines()

        for i, (b, a) in enumerate(zip(before_lines, after_lines)):
            if b != a:
                node = Node(
                    id=f"diff_{i}",
                    name=f"Line {i+1}",
                    type="diff",
                    path="",
                    color="#FF6B6B" if b else "#4CAF50",
                )
                graph.nodes.append(node)

        return graph

    def get_graph(self, viz_type: VisualizationType) -> Optional[VisualizationGraph]:
        """Get cached graph."""
        return self._graphs.get(viz_type.value)

    async def _read_file(self, path: Path) -> str:
        """Read file content."""
        import aiofiles
        async with aiofiles.open(path, "r") as f:
            return await f.read()

    def _extract_imports(self, content: str) -> List[str]:
        """Extract import statements."""
        imports = []
        for line in content.splitlines():
            if line.startswith("import ") or line.startswith("from "):
                # Parse import
                if "from " in line:
                    parts = line.split("from ")[1].split(" import")[0]
                    imports.append(parts.strip())
                elif "import " in line:
                    parts = line.split("import ")[1].split(",")
                    for p in parts:
                        imports.append(p.strip().split(" as ")[0])
        return imports

    def _extract_functions(self, content: str) -> List[str]:
        """Extract function names."""
        functions = []
        for line in content.splitlines():
            if line.startswith("def ") or line.startswith("async def "):
                func_name = line.split("def ")[1].split("(")[0]
                functions.append(func_name.strip())
        return functions

    def to_json(self, graph: VisualizationGraph) -> Dict[str, Any]:
        """Convert graph to JSON."""
        return {
            "nodes": [
                {
                    "id": n.id,
                    "name": n.name,
                    "type": n.type,
                    "path": n.path,
                    "color": n.color,
                    "size": n.size,
                    "metrics": n.metrics,
                }
                for n in graph.nodes
            ],
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "type": e.type,
                    "weight": e.weight,
                    "color": e.color,
                }
                for e in graph.edges
            ],
            "layout": graph.layout,
        }


# Global visualizer
_visualizer: Optional[BuddyVisualizer] = None


def get_visualizer() -> BuddyVisualizer:
    """Get global visualizer."""
    if _visualizer is None:
        _visualizer = BuddyVisualizer()
    return _visualizer


async def visualize_architecture(path: Path = None) -> Dict[str, Any]:
    """Visualize architecture."""
    viz = get_visualizer()
    path = path or Path.cwd()
    graph = await viz.analyze_architecture(path)
    return viz.to_json(graph)


__all__ = [
    "VisualizationType",
    "Node",
    "Edge",
    "VisualizationGraph",
    "BuddyVisualizer",
    "get_visualizer",
    "visualize_architecture",
]