"""Behavior tests for dependency graph operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from devwayfinder.core.graph import DependencyGraph
from devwayfinder.core.models import Module, ModuleType

if TYPE_CHECKING:
    from pathlib import Path


class TestDependencyGraphBehaviors:
    """Test cycle handling, ordering, and export behavior."""

    def test_graph_detects_cycles(self, tmp_path: Path) -> None:
        """Test cycle detection in dependency graph."""
        graph = DependencyGraph()

        # Create circular dependency: A -> B -> C -> A
        modA = Module(
            name="modA",
            path=tmp_path / "a.py",
            module_type=ModuleType.FILE,
            language="python",
        )
        modB = Module(
            name="modB",
            path=tmp_path / "b.py",
            module_type=ModuleType.FILE,
            language="python",
        )
        modC = Module(
            name="modC",
            path=tmp_path / "c.py",
            module_type=ModuleType.FILE,
            language="python",
        )

        graph.add_module(modA)
        graph.add_module(modB)
        graph.add_module(modC)

        # Create cycle
        graph.add_dependency(modA.path, modB.path)
        graph.add_dependency(modB.path, modC.path)
        graph.add_dependency(modC.path, modA.path)

        # Should detect cycle
        assert graph.has_cycles()

    def test_graph_topological_sort_no_cycles(self, tmp_path: Path) -> None:
        """Test topological sort on acyclic graph."""
        graph = DependencyGraph()

        # Create DAG: A -> B -> C
        modA = Module(
            name="modA",
            path=tmp_path / "a.py",
            module_type=ModuleType.FILE,
            language="python",
        )
        modB = Module(
            name="modB",
            path=tmp_path / "b.py",
            module_type=ModuleType.FILE,
            language="python",
        )
        modC = Module(
            name="modC",
            path=tmp_path / "c.py",
            module_type=ModuleType.FILE,
            language="python",
        )

        graph.add_module(modA)
        graph.add_module(modB)
        graph.add_module(modC)

        graph.add_dependency(modA.path, modB.path)
        graph.add_dependency(modB.path, modC.path)

        # Should not detect cycle
        assert not graph.has_cycles()

        # Topological sort should succeed
        topo = graph.topological_order()
        assert len(topo) == 3

    def test_graph_find_cycles(self, tmp_path: Path) -> None:
        """Test cycle finding functionality."""
        graph = DependencyGraph()

        # Component 1: A -> B
        modA = Module(
            name="modA",
            path=tmp_path / "a.py",
            module_type=ModuleType.FILE,
            language="python",
        )
        modB = Module(
            name="modB",
            path=tmp_path / "b.py",
            module_type=ModuleType.FILE,
            language="python",
        )

        # Component 2: C (isolated)
        modC = Module(
            name="modC",
            path=tmp_path / "c.py",
            module_type=ModuleType.FILE,
            language="python",
        )

        graph.add_module(modA)
        graph.add_module(modB)
        graph.add_module(modC)

        graph.add_dependency(modA.path, modB.path)

        # Find cycles (should be none in DAG)
        cycles = graph.find_cycles()
        assert isinstance(cycles, list)

    def test_graph_entry_points_detection(self, tmp_path: Path) -> None:
        """Test entry points detection."""
        graph = DependencyGraph()

        # Create: main -> util, cli -> util (util is not entry point)
        main = Module(
            name="main",
            path=tmp_path / "main.py",
            module_type=ModuleType.FILE,
            language="python",
            entry_point=True,
        )
        cli = Module(
            name="cli",
            path=tmp_path / "cli.py",
            module_type=ModuleType.FILE,
            language="python",
            entry_point=True,
        )
        util = Module(
            name="util",
            path=tmp_path / "util.py",
            module_type=ModuleType.FILE,
            language="python",
            entry_point=False,
        )

        graph.add_module(main)
        graph.add_module(cli)
        graph.add_module(util)

        graph.add_dependency(main.path, util.path)
        graph.add_dependency(cli.path, util.path)

        # Get entry points
        entry_points = graph.get_entry_points()
        assert len(entry_points) == 2
        assert main in entry_points
        assert cli in entry_points

    def test_graph_core_modules_threshold(self, tmp_path: Path) -> None:
        """Test core module detection with threshold."""
        graph = DependencyGraph()

        # Create hub structure: core -> a, core -> b, a -> util
        core = Module(
            name="core",
            path=tmp_path / "core.py",
            module_type=ModuleType.FILE,
            language="python",
        )
        a = Module(
            name="a",
            path=tmp_path / "a.py",
            module_type=ModuleType.FILE,
            language="python",
        )
        b = Module(
            name="b",
            path=tmp_path / "b.py",
            module_type=ModuleType.FILE,
            language="python",
        )
        util = Module(
            name="util",
            path=tmp_path / "util.py",
            module_type=ModuleType.FILE,
            language="python",
        )

        graph.add_module(core)
        graph.add_module(a)
        graph.add_module(b)
        graph.add_module(util)

        graph.add_dependency(core.path, a.path)
        graph.add_dependency(core.path, b.path)
        graph.add_dependency(a.path, util.path)

        # Get core modules (in_degree + out_degree >= threshold)
        core_mods = graph.get_core_modules(threshold=2)
        # core has in=0, out=2 (total=2, meets threshold)
        # a has in=1, out=1 (total=2, meets threshold if we count)
        assert len(core_mods) >= 1

    def test_graph_edge_count(self, tmp_path: Path) -> None:
        """Test edge counting."""
        graph = DependencyGraph()

        mod1 = Module(
            name="mod1",
            path=tmp_path / "mod1.py",
            module_type=ModuleType.FILE,
            language="python",
        )
        mod2 = Module(
            name="mod2",
            path=tmp_path / "mod2.py",
            module_type=ModuleType.FILE,
            language="python",
        )

        graph.add_module(mod1)
        graph.add_module(mod2)

        assert graph.edge_count == 0

        graph.add_dependency(mod1.path, mod2.path)
        assert graph.edge_count == 1

    def test_graph_node_count(self, tmp_path: Path) -> None:
        """Test node counting."""
        graph = DependencyGraph()

        assert graph.node_count == 0

        mod1 = Module(
            name="mod1",
            path=tmp_path / "mod1.py",
            module_type=ModuleType.FILE,
            language="python",
        )

        graph.add_module(mod1)
        assert graph.node_count == 1

    def test_graph_mermaid_export(self, tmp_path: Path) -> None:
        """Test Mermaid diagram export."""
        graph = DependencyGraph()

        mod1 = Module(
            name="mod1",
            path=tmp_path / "mod1.py",
            module_type=ModuleType.FILE,
            language="python",
            entry_point=True,
        )
        mod2 = Module(
            name="mod2",
            path=tmp_path / "mod2.py",
            module_type=ModuleType.FILE,
            language="python",
        )

        graph.add_module(mod1)
        graph.add_module(mod2)
        graph.add_dependency(mod1.path, mod2.path)

        # Export to Mermaid
        mermaid = graph.to_mermaid()
        assert "graph" in mermaid.lower() or "td" in mermaid.lower()
        assert "mod1" in mermaid
        assert "mod2" in mermaid
