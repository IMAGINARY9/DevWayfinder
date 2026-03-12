"""
Mermaid diagram generator for dependency graphs.

Generates Mermaid.js compatible diagrams for visualizing
module dependencies and project structure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from devwayfinder.core.graph import DependencyGraph
    from devwayfinder.core.models import Module


class DiagramDirection(StrEnum):
    """Direction for Mermaid flowcharts."""

    TOP_DOWN = "TD"
    BOTTOM_UP = "BU"
    LEFT_RIGHT = "LR"
    RIGHT_LEFT = "RL"


class NodeShape(StrEnum):
    """Node shapes for Mermaid diagrams."""

    RECTANGLE = "rect"
    ROUNDED = "rounded"
    STADIUM = "stadium"
    CIRCLE = "circle"
    DIAMOND = "diamond"
    HEXAGON = "hexagon"


@dataclass
class MermaidConfig:
    """Configuration for Mermaid diagram generation."""

    direction: DiagramDirection = DiagramDirection.TOP_DOWN
    max_nodes: int = 50
    max_label_length: int = 30
    show_entry_points: bool = True
    show_orphans: bool = False
    cluster_by_directory: bool = True
    node_shape: NodeShape = NodeShape.ROUNDED
    entry_point_color: str = "#2ecc71"
    core_module_color: str = "#3498db"
    default_color: str = "#95a5a6"


@dataclass
class DiagramNode:
    """A node in the Mermaid diagram."""

    id: str
    label: str
    module_path: Path
    is_entry_point: bool = False
    is_core: bool = False  # High connectivity
    subgraph: str | None = None


@dataclass
class DiagramEdge:
    """An edge in the Mermaid diagram."""

    source_id: str
    target_id: str
    edge_type: str = "import"


@dataclass
class MermaidDiagram:
    """A complete Mermaid diagram."""

    nodes: list[DiagramNode] = field(default_factory=list)
    edges: list[DiagramEdge] = field(default_factory=list)
    subgraphs: dict[str, list[str]] = field(default_factory=dict)
    config: MermaidConfig = field(default_factory=MermaidConfig)

    def render(self) -> str:
        """
        Render the diagram as Mermaid syntax.

        Returns:
            Mermaid diagram string
        """
        lines = [f"flowchart {self.config.direction}"]

        # Add style classes
        lines.extend(self._render_styles())

        # Render subgraphs if clustering enabled
        if self.config.cluster_by_directory and self.subgraphs:
            for subgraph_name, node_ids in self.subgraphs.items():
                lines.append(f"    subgraph {self._sanitize_id(subgraph_name)}[{subgraph_name}]")
                for node_id in node_ids:
                    node = self._find_node(node_id)
                    if node:
                        lines.append(f"        {self._render_node(node)}")
                lines.append("    end")

            # Render nodes not in subgraphs
            orphan_nodes = [n for n in self.nodes if n.subgraph is None]
            for node in orphan_nodes:
                lines.append(f"    {self._render_node(node)}")
        else:
            # Render all nodes without subgraphs
            for node in self.nodes:
                lines.append(f"    {self._render_node(node)}")

        # Render edges
        for edge in self.edges:
            lines.append(f"    {self._render_edge(edge)}")

        # Apply classes to nodes
        for node in self.nodes:
            if node.is_entry_point:
                lines.append(f"    class {node.id} entryPoint")
            elif node.is_core:
                lines.append(f"    class {node.id} coreModule")

        return "\n".join(lines)

    def _render_node(self, node: DiagramNode) -> str:
        """Render a single node."""
        label = self._truncate_label(node.label)
        shape = self.config.node_shape

        if shape == NodeShape.ROUNDED or shape == NodeShape.STADIUM:
            return f"{node.id}([{label}])"
        elif shape == NodeShape.CIRCLE:
            return f"{node.id}(({label}))"
        elif shape == NodeShape.DIAMOND:
            return f"{node.id}{{{label}}}"
        elif shape == NodeShape.HEXAGON:
            return f"{node.id}{{{{{label}}}}}"
        else:  # RECTANGLE
            return f"{node.id}[{label}]"

    def _render_edge(self, edge: DiagramEdge) -> str:
        """Render a single edge."""
        return f"{edge.source_id} --> {edge.target_id}"

    def _render_styles(self) -> list[str]:
        """Render CSS class definitions."""
        return [
            f"    classDef entryPoint fill:{self.config.entry_point_color},stroke:#27ae60",
            f"    classDef coreModule fill:{self.config.core_module_color},stroke:#2980b9",
        ]

    def _truncate_label(self, label: str) -> str:
        """Truncate label to max length."""
        if len(label) <= self.config.max_label_length:
            return label
        return label[: self.config.max_label_length - 3] + "..."

    def _sanitize_id(self, text: str) -> str:
        """Sanitize text for use as Mermaid ID."""
        # Replace non-alphanumeric with underscore
        import re

        return re.sub(r"[^a-zA-Z0-9]", "_", text)

    def _find_node(self, node_id: str) -> DiagramNode | None:
        """Find node by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None


class MermaidGenerator:
    """
    Generates Mermaid diagrams from dependency graphs.

    Handles large graphs through filtering and clustering.
    """

    def __init__(self, config: MermaidConfig | None = None) -> None:
        """
        Initialize the generator.

        Args:
            config: Optional configuration
        """
        self.config = config or MermaidConfig()

    def generate(
        self,
        graph: DependencyGraph,
        root_path: Path | None = None,
    ) -> MermaidDiagram:
        """
        Generate a Mermaid diagram from a dependency graph.

        Args:
            graph: The dependency graph to visualize
            root_path: Project root path for relative paths

        Returns:
            MermaidDiagram ready to render
        """
        diagram = MermaidDiagram(config=self.config)

        # Get all modules from graph
        modules = self._get_modules(graph)

        # Filter if needed
        if len(modules) > self.config.max_nodes:
            modules = self._filter_modules(modules, graph)

        # Identify core modules (high connectivity)
        core_module_paths = self._identify_core_modules(modules, graph)

        # Build nodes
        for module in modules:
            node = self._create_node(module, root_path, core_module_paths)
            diagram.nodes.append(node)

            # Track subgraphs
            if node.subgraph:
                if node.subgraph not in diagram.subgraphs:
                    diagram.subgraphs[node.subgraph] = []
                diagram.subgraphs[node.subgraph].append(node.id)

        # Build edges (only between included modules)
        module_paths = {m.path for m in modules}
        for module in modules:
            deps = graph.get_dependencies(module.path)
            for dep in deps:
                if dep.path in module_paths:
                    edge = DiagramEdge(
                        source_id=self._path_to_id(module.path),
                        target_id=self._path_to_id(dep.path),
                    )
                    diagram.edges.append(edge)

        return diagram

    def generate_markdown(
        self,
        graph: DependencyGraph,
        root_path: Path | None = None,
        title: str = "Dependency Graph",
    ) -> str:
        """
        Generate a Markdown code block with Mermaid diagram.

        Args:
            graph: The dependency graph
            root_path: Project root path
            title: Optional title for the diagram

        Returns:
            Markdown string with Mermaid code block
        """
        diagram = self.generate(graph, root_path)
        mermaid_code = diagram.render()

        lines = [
            f"### {title}",
            "",
            "```mermaid",
            mermaid_code,
            "```",
        ]

        return "\n".join(lines)

    def _get_modules(self, graph: DependencyGraph) -> list[Module]:
        """Get all modules from the graph."""
        return graph.get_all_modules()

    def _filter_modules(
        self,
        modules: list[Module],
        graph: DependencyGraph,
    ) -> list[Module]:
        """
        Filter modules to fit within max_nodes limit.

        Prioritizes:
        1. Entry points
        2. Core modules (high connectivity)
        3. Recent changes (if git info available)
        """
        # Score modules
        scored: list[tuple[float, Module]] = []

        for module in modules:
            score = 0.0

            # Entry points get highest priority
            if module.entry_point:
                score += 10.0

            # Connectivity score
            deps = graph.get_dependencies(module.path)
            dependents = graph.get_dependents(module.path)
            score += len(dependents) * 0.5  # More valuable if depended on
            score += len(deps) * 0.2

            scored.append((score, module))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        return [m for _, m in scored[: self.config.max_nodes]]

    def _identify_core_modules(
        self,
        modules: list[Module],
        graph: DependencyGraph,
    ) -> set[Path]:
        """Identify core modules based on connectivity."""
        core_paths: set[Path] = set()

        for module in modules:
            dependents = graph.get_dependents(module.path)
            if len(dependents) >= 3:  # If 3+ modules depend on it
                core_paths.add(module.path)

        return core_paths

    def _create_node(
        self,
        module: Module,
        root_path: Path | None,
        core_module_paths: set[Path],
    ) -> DiagramNode:
        """Create a diagram node from a module."""
        # Create relative path for label
        if root_path and module.path.is_relative_to(root_path):
            rel_path = module.path.relative_to(root_path)
            label = str(rel_path)
        else:
            label = module.name

        # Determine subgraph (parent directory)
        if self.config.cluster_by_directory:
            parent = module.path.parent.name
            subgraph = parent if parent and parent != "." else None
        else:
            subgraph = None

        return DiagramNode(
            id=self._path_to_id(module.path),
            label=label,
            module_path=module.path,
            is_entry_point=module.entry_point,
            is_core=module.path in core_module_paths,
            subgraph=subgraph,
        )

    def _path_to_id(self, path: Path) -> str:
        """Convert a path to a valid Mermaid node ID."""
        # Use just the filename stem for short IDs
        stem = path.stem
        # Replace special characters
        import re

        clean = re.sub(r"[^a-zA-Z0-9]", "_", stem)
        # Add hash for uniqueness if needed
        path_hash = abs(hash(str(path))) % 10000
        return f"{clean}_{path_hash}"


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def generate_mermaid_diagram(
    graph: DependencyGraph,
    root_path: Path | None = None,
    max_nodes: int = 50,
    direction: DiagramDirection = DiagramDirection.TOP_DOWN,
) -> str:
    """
    Generate a Mermaid diagram from a dependency graph.

    Args:
        graph: Dependency graph to visualize
        root_path: Project root for relative paths
        max_nodes: Maximum nodes to include
        direction: Diagram direction

    Returns:
        Mermaid diagram string
    """
    config = MermaidConfig(max_nodes=max_nodes, direction=direction)
    generator = MermaidGenerator(config)
    diagram = generator.generate(graph, root_path)
    return diagram.render()


def generate_mermaid_markdown(
    graph: DependencyGraph,
    root_path: Path | None = None,
    title: str = "Dependency Graph",
) -> str:
    """
    Generate Markdown with embedded Mermaid diagram.

    Args:
        graph: Dependency graph
        root_path: Project root
        title: Section title

    Returns:
        Markdown string
    """
    generator = MermaidGenerator()
    return generator.generate_markdown(graph, root_path, title)
