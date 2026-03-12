"""Tests for Mermaid diagram generator."""

from pathlib import Path

import pytest

from devwayfinder.core.graph import DependencyGraph
from devwayfinder.core.models import Module, ModuleType
from devwayfinder.generators.mermaid import (
    DiagramDirection,
    DiagramEdge,
    DiagramNode,
    MermaidConfig,
    MermaidDiagram,
    MermaidGenerator,
    NodeShape,
    generate_mermaid_diagram,
    generate_mermaid_markdown,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_graph() -> DependencyGraph:
    """Create a sample dependency graph."""
    graph = DependencyGraph()

    # Create modules
    main = Module(
        name="main.py",
        path=Path("/project/src/main.py"),
        module_type=ModuleType.FILE,
        entry_point=True,
    )
    core = Module(
        name="core.py",
        path=Path("/project/src/core.py"),
        module_type=ModuleType.FILE,
    )
    utils = Module(
        name="utils.py",
        path=Path("/project/src/utils.py"),
        module_type=ModuleType.FILE,
    )

    graph.add_module(main)
    graph.add_module(core)
    graph.add_module(utils)

    graph.add_dependency(main.path, core.path)
    graph.add_dependency(core.path, utils.path)

    return graph


# =============================================================================
# DIAGRAM NODE TESTS
# =============================================================================


class TestDiagramNode:
    """Tests for DiagramNode."""

    def test_creation(self) -> None:
        """Test node creation."""
        node = DiagramNode(
            id="main_1234",
            label="main.py",
            module_path=Path("/project/main.py"),
            is_entry_point=True,
        )
        assert node.id == "main_1234"
        assert node.is_entry_point

    def test_core_node(self) -> None:
        """Test core module node."""
        node = DiagramNode(
            id="core_5678",
            label="core.py",
            module_path=Path("/project/core.py"),
            is_core=True,
        )
        assert node.is_core


# =============================================================================
# DIAGRAM EDGE TESTS
# =============================================================================


class TestDiagramEdge:
    """Tests for DiagramEdge."""

    def test_creation(self) -> None:
        """Test edge creation."""
        edge = DiagramEdge(
            source_id="main_1234",
            target_id="core_5678",
            edge_type="import",
        )
        assert edge.source_id == "main_1234"
        assert edge.target_id == "core_5678"


# =============================================================================
# MERMAID CONFIG TESTS
# =============================================================================


class TestMermaidConfig:
    """Tests for MermaidConfig."""

    def test_default_config(self) -> None:
        """Test default configuration."""
        config = MermaidConfig()
        assert config.direction == DiagramDirection.TOP_DOWN
        assert config.max_nodes == 50
        assert config.show_entry_points is True

    def test_custom_config(self) -> None:
        """Test custom configuration."""
        config = MermaidConfig(
            direction=DiagramDirection.LEFT_RIGHT,
            max_nodes=100,
            node_shape=NodeShape.CIRCLE,
        )
        assert config.direction == DiagramDirection.LEFT_RIGHT
        assert config.max_nodes == 100


# =============================================================================
# MERMAID DIAGRAM TESTS
# =============================================================================


class TestMermaidDiagram:
    """Tests for MermaidDiagram."""

    def test_render_empty(self) -> None:
        """Test rendering empty diagram."""
        diagram = MermaidDiagram()
        result = diagram.render()
        assert "flowchart TD" in result

    def test_render_with_nodes(self) -> None:
        """Test rendering with nodes."""
        diagram = MermaidDiagram()
        diagram.nodes = [
            DiagramNode(
                id="main",
                label="main.py",
                module_path=Path("/project/main.py"),
            )
        ]
        result = diagram.render()
        assert "main" in result
        assert "main.py" in result

    def test_render_with_edges(self) -> None:
        """Test rendering with edges."""
        diagram = MermaidDiagram()
        diagram.nodes = [
            DiagramNode(id="a", label="a.py", module_path=Path("/a.py")),
            DiagramNode(id="b", label="b.py", module_path=Path("/b.py")),
        ]
        diagram.edges = [DiagramEdge(source_id="a", target_id="b")]
        result = diagram.render()
        assert "a --> b" in result

    def test_entry_point_styling(self) -> None:
        """Test that entry points get styled."""
        diagram = MermaidDiagram()
        diagram.nodes = [
            DiagramNode(
                id="main",
                label="main.py",
                module_path=Path("/main.py"),
                is_entry_point=True,
            )
        ]
        result = diagram.render()
        assert "class main entryPoint" in result

    def test_label_truncation(self) -> None:
        """Test long label truncation."""
        config = MermaidConfig(max_label_length=10)
        diagram = MermaidDiagram(config=config)
        truncated = diagram._truncate_label("this_is_a_very_long_label")
        assert len(truncated) <= 10
        assert truncated.endswith("...")


# =============================================================================
# MERMAID GENERATOR TESTS
# =============================================================================


class TestMermaidGenerator:
    """Tests for MermaidGenerator."""

    def test_generate_basic(self, sample_graph: DependencyGraph) -> None:
        """Test basic diagram generation."""
        generator = MermaidGenerator()
        diagram = generator.generate(sample_graph)

        assert len(diagram.nodes) == 3
        assert len(diagram.edges) == 2

    def test_generate_with_root_path(self, sample_graph: DependencyGraph) -> None:
        """Test generation with root path for relative labels."""
        generator = MermaidGenerator()
        diagram = generator.generate(sample_graph, root_path=Path("/project"))

        # Labels should be relative
        for node in diagram.nodes:
            assert not node.label.startswith("/project")

    def test_generate_markdown(self, sample_graph: DependencyGraph) -> None:
        """Test Markdown generation."""
        generator = MermaidGenerator()
        md = generator.generate_markdown(sample_graph, title="Test Graph")

        assert "### Test Graph" in md
        assert "```mermaid" in md
        assert "flowchart" in md
        assert "```" in md

    def test_max_nodes_filtering(self) -> None:
        """Test that large graphs are filtered."""
        graph = DependencyGraph()

        # Create many modules
        for i in range(100):
            m = Module(
                name=f"mod{i}.py",
                path=Path(f"/project/mod{i}.py"),
                module_type=ModuleType.FILE,
                entry_point=(i == 0),  # One entry point
            )
            graph.add_module(m)

        config = MermaidConfig(max_nodes=10)
        generator = MermaidGenerator(config)
        diagram = generator.generate(graph)

        assert len(diagram.nodes) <= 10

    def test_core_module_detection(self) -> None:
        """Test detection of core modules."""
        graph = DependencyGraph()

        core = Module(
            name="core.py",
            path=Path("/project/core.py"),
            module_type=ModuleType.FILE,
        )
        graph.add_module(core)

        # Create modules that depend on core
        for i in range(5):
            m = Module(
                name=f"mod{i}.py",
                path=Path(f"/project/mod{i}.py"),
                module_type=ModuleType.FILE,
            )
            graph.add_module(m)
            graph.add_dependency(m.path, core.path)

        generator = MermaidGenerator()
        diagram = generator.generate(graph)

        # Find core node
        core_nodes = [n for n in diagram.nodes if n.label.startswith("core")]
        assert len(core_nodes) == 1
        assert core_nodes[0].is_core

    def test_direction_config(self, sample_graph: DependencyGraph) -> None:
        """Test different diagram directions."""
        config = MermaidConfig(direction=DiagramDirection.LEFT_RIGHT)
        generator = MermaidGenerator(config)
        diagram = generator.generate(sample_graph)

        result = diagram.render()
        assert "flowchart LR" in result

    def test_subgraph_clustering(self) -> None:
        """Test subgraph clustering by directory."""
        graph = DependencyGraph()

        # Create modules in different directories
        src_main = Module(
            name="main.py",
            path=Path("/project/src/main.py"),
            module_type=ModuleType.FILE,
        )
        src_core = Module(
            name="core.py",
            path=Path("/project/src/core.py"),
            module_type=ModuleType.FILE,
        )
        tests_test = Module(
            name="test_main.py",
            path=Path("/project/tests/test_main.py"),
            module_type=ModuleType.FILE,
        )

        graph.add_module(src_main)
        graph.add_module(src_core)
        graph.add_module(tests_test)

        config = MermaidConfig(cluster_by_directory=True)
        generator = MermaidGenerator(config)
        diagram = generator.generate(graph)

        # Should have subgraphs for src and tests
        assert "src" in diagram.subgraphs or any(
            n.subgraph == "src" for n in diagram.nodes
        )


# =============================================================================
# CONVENIENCE FUNCTION TESTS
# =============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_generate_mermaid_diagram(self, sample_graph: DependencyGraph) -> None:
        """Test generate_mermaid_diagram function."""
        result = generate_mermaid_diagram(sample_graph)

        assert "flowchart" in result
        assert "-->" in result

    def test_generate_mermaid_markdown(self, sample_graph: DependencyGraph) -> None:
        """Test generate_mermaid_markdown function."""
        result = generate_mermaid_markdown(sample_graph, title="My Graph")

        assert "### My Graph" in result
        assert "```mermaid" in result


# =============================================================================
# NODE SHAPE TESTS
# =============================================================================


class TestNodeShapes:
    """Tests for different node shapes."""

    @pytest.mark.parametrize(
        "shape,expected_char",
        [
            (NodeShape.ROUNDED, "("),
            (NodeShape.RECTANGLE, "["),
            (NodeShape.CIRCLE, "("),
            (NodeShape.DIAMOND, "{"),
        ],
    )
    def test_node_shape_rendering(
        self, shape: NodeShape, expected_char: str
    ) -> None:
        """Test that node shapes render correctly."""
        config = MermaidConfig(node_shape=shape)
        diagram = MermaidDiagram(config=config)
        diagram.nodes = [
            DiagramNode(id="test", label="test.py", module_path=Path("/test.py"))
        ]
        result = diagram.render()
        assert expected_char in result


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestMermaidIntegration:
    """Integration tests for Mermaid generation."""

    def test_realistic_project(self) -> None:
        """Test with realistic project structure."""
        graph = DependencyGraph()

        # Create realistic modules
        modules = [
            ("__main__.py", "/project/src/__main__.py", True),
            ("cli.py", "/project/src/cli/app.py", False),
            ("core.py", "/project/src/core/core.py", False),
            ("models.py", "/project/src/core/models.py", False),
            ("utils.py", "/project/src/utils/helpers.py", False),
            ("config.py", "/project/src/config/settings.py", False),
        ]

        for name, path, is_entry in modules:
            m = Module(
                name=name,
                path=Path(path),
                module_type=ModuleType.FILE,
                entry_point=is_entry,
            )
            graph.add_module(m)

        # Add dependencies
        graph.add_dependency(Path(modules[0][1]), Path(modules[1][1]))  # main -> cli
        graph.add_dependency(Path(modules[1][1]), Path(modules[2][1]))  # cli -> core
        graph.add_dependency(Path(modules[2][1]), Path(modules[3][1]))  # core -> models
        graph.add_dependency(Path(modules[2][1]), Path(modules[4][1]))  # core -> utils
        graph.add_dependency(Path(modules[1][1]), Path(modules[5][1]))  # cli -> config

        generator = MermaidGenerator()
        diagram = generator.generate(graph, root_path=Path("/project"))
        result = diagram.render()

        # Should have all nodes
        assert len(diagram.nodes) == 6
        # Should have all edges
        assert len(diagram.edges) == 5
        # Should render successfully
        assert "flowchart" in result
        assert "-->" in result

    def test_empty_graph(self) -> None:
        """Test with empty graph."""
        graph = DependencyGraph()
        generator = MermaidGenerator()
        diagram = generator.generate(graph)

        assert len(diagram.nodes) == 0
        assert len(diagram.edges) == 0
