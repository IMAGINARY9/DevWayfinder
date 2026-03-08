"""Dependency graph implementation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

import networkx as nx

if TYPE_CHECKING:
    from devwayfinder.core.models import Module


class DependencyGraph:
    """
    Directed graph representing module dependencies.

    Wraps networkx DiGraph with domain-specific methods.
    """

    def __init__(self) -> None:
        """Initialize empty dependency graph."""
        self._graph: nx.DiGraph = nx.DiGraph()

    def add_module(self, module: Module) -> None:
        """
        Add a module as a node in the graph.

        Args:
            module: Module to add
        """
        self._graph.add_node(str(module.path), module=module)

    def add_dependency(self, from_path: Path, to_path: Path, kind: str = "import") -> None:
        """
        Add a dependency edge between two modules.

        Args:
            from_path: Path of the importing module
            to_path: Path of the imported module
            kind: Type of dependency (import, require, dynamic)
        """
        self._graph.add_edge(str(from_path), str(to_path), kind=kind)

    def get_module(self, path: Path) -> Module | None:
        """
        Get a module by path.

        Args:
            path: Path to look up

        Returns:
            Module if found, None otherwise
        """
        node_data = self._graph.nodes.get(str(path))
        if node_data:
            return cast("Module | None", node_data.get("module"))
        return None

    def get_dependencies(self, path: Path) -> list[Module]:
        """
        Get modules that the given module depends on.

        Args:
            path: Path of the module

        Returns:
            List of dependency modules
        """
        result = []
        for successor in self._graph.successors(str(path)):
            module = self.get_module(Path(successor))
            if module:
                result.append(module)
        return result

    def get_dependents(self, path: Path) -> list[Module]:
        """
        Get modules that depend on the given module.

        Args:
            path: Path of the module

        Returns:
            List of dependent modules
        """
        result = []
        for predecessor in self._graph.predecessors(str(path)):
            module = self.get_module(Path(predecessor))
            if module:
                result.append(module)
        return result

    def get_entry_points(self) -> list[Module]:
        """
        Find modules with no incoming dependencies.

        These are potential entry points to the codebase.

        Returns:
            List of entry point modules
        """
        result = []
        for node in self._graph.nodes:
            if self._graph.in_degree(node) == 0:
                module = self.get_module(Path(node))
                if module:
                    result.append(module)
        return result

    def get_core_modules(self, threshold: int = 5) -> list[Module]:
        """
        Find highly-connected modules (likely important).

        Args:
            threshold: Minimum number of connections

        Returns:
            List of core modules sorted by connectivity
        """
        result = []
        for node in self._graph.nodes:
            connections = self._graph.in_degree(node) + self._graph.out_degree(node)
            if connections >= threshold:
                module = self.get_module(Path(node))
                if module:
                    result.append((module, connections))

        result.sort(key=lambda x: x[1], reverse=True)
        return [m for m, _ in result]

    def topological_order(self) -> list[Module]:
        """
        Return modules in dependency order (dependencies first).

        Returns:
            List of modules in topological order

        Raises:
            ValueError: If graph has cycles
        """
        try:
            ordered = list(nx.topological_sort(self._graph))
            result = []
            for node in ordered:
                module = self.get_module(Path(node))
                if module:
                    result.append(module)
            return result
        except nx.NetworkXUnfeasible as e:
            raise ValueError("Dependency graph contains cycles") from e

    def has_cycles(self) -> bool:
        """Check if the graph contains cycles."""
        return not nx.is_directed_acyclic_graph(self._graph)

    def find_cycles(self) -> list[list[str]]:
        """Find all cycles in the graph."""
        return list(nx.simple_cycles(self._graph))

    @property
    def node_count(self) -> int:
        """Number of nodes in the graph."""
        return int(self._graph.number_of_nodes())

    @property
    def edge_count(self) -> int:
        """Number of edges in the graph."""
        return int(self._graph.number_of_edges())

    def to_mermaid(self, max_nodes: int = 50) -> str:
        """
        Export graph as Mermaid diagram.

        Args:
            max_nodes: Maximum nodes to include (for readability)

        Returns:
            Mermaid diagram string
        """
        lines = ["graph TD"]

        # Limit nodes for readability
        nodes = list(self._graph.nodes)[:max_nodes]
        node_set = set(nodes)

        # Add edges between included nodes
        for u, v, data in self._graph.edges(data=True):
            if u in node_set and v in node_set:
                # Sanitize names for Mermaid
                u_name = Path(u).stem.replace("-", "_").replace(".", "_")
                v_name = Path(v).stem.replace("-", "_").replace(".", "_")
                kind = data.get("kind", "import")

                if kind == "import":
                    lines.append(f"    {u_name} --> {v_name}")
                else:
                    lines.append(f"    {u_name} -.-> {v_name}")

        if len(self._graph.nodes) > max_nodes:
            lines.append(f"    %% Note: {len(self._graph.nodes) - max_nodes} nodes omitted")

        return "\n".join(lines)

    def to_ascii(self, max_depth: int = 3) -> str:
        """
        Export graph as ASCII tree.

        Args:
            max_depth: Maximum depth to display

        Returns:
            ASCII tree string
        """
        entry_points = self.get_entry_points()
        if not entry_points:
            return "(no entry points found)"

        lines = []
        visited: set[str] = set()

        def _render(module: Module, depth: int, prefix: str) -> None:
            if depth > max_depth or str(module.path) in visited:
                return

            visited.add(str(module.path))
            lines.append(f"{prefix}{module.name}")

            deps = self.get_dependencies(module.path)
            for i, dep in enumerate(deps):
                is_last = i == len(deps) - 1
                new_prefix = prefix.replace("├── ", "│   ").replace("└── ", "    ")
                child_prefix = new_prefix + ("└── " if is_last else "├── ")
                _render(dep, depth + 1, child_prefix)

        for ep in entry_points[:5]:  # Limit entry points
            _render(ep, 0, "")
            lines.append("")

        return "\n".join(lines)
