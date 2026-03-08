"""Tests for core domain models."""

from pathlib import Path

from devwayfinder.core.graph import DependencyGraph
from devwayfinder.core.guide import OnboardingGuide, Section, SectionType
from devwayfinder.core.models import Module, ModuleType, Project


class TestModule:
    """Tests for Module model."""

    def test_create_module(self) -> None:
        """Test basic module creation."""
        module = Module(
            name="test.py",
            path=Path("/project/test.py"),
            module_type=ModuleType.FILE,
        )

        assert module.name == "test.py"
        assert module.path == Path("/project/test.py")
        assert module.module_type == ModuleType.FILE
        assert module.language is None
        assert module.imports == []
        assert module.exports == []
        assert module.entry_point is False

    def test_module_with_analysis_results(self) -> None:
        """Test module with full analysis data."""
        module = Module(
            name="main.py",
            path=Path("/project/main.py"),
            module_type=ModuleType.FILE,
            language="python",
            imports=["os", "sys", "utils"],
            exports=["main", "run"],
            entry_point=True,
        )

        assert module.language == "python"
        assert len(module.imports) == 3
        assert len(module.exports) == 2
        assert module.entry_point is True

    def test_module_equality(self) -> None:
        """Test modules are equal by path."""
        m1 = Module(name="test.py", path=Path("/a/test.py"), module_type=ModuleType.FILE)
        m2 = Module(name="test.py", path=Path("/a/test.py"), module_type=ModuleType.FILE)
        m3 = Module(name="test.py", path=Path("/b/test.py"), module_type=ModuleType.FILE)

        assert m1 == m2
        assert m1 != m3

    def test_module_hashable(self) -> None:
        """Test modules can be used in sets."""
        m1 = Module(name="a.py", path=Path("/a.py"), module_type=ModuleType.FILE)
        m2 = Module(name="a.py", path=Path("/a.py"), module_type=ModuleType.FILE)

        module_set = {m1, m2}
        assert len(module_set) == 1


class TestProject:
    """Tests for Project model."""

    def test_create_project(self) -> None:
        """Test basic project creation."""
        project = Project(
            name="test-project",
            root_path=Path("/project"),
        )

        assert project.name == "test-project"
        assert project.root_path == Path("/project")
        assert project.modules == {}
        assert project.entry_points == []

    def test_project_with_modules(self) -> None:
        """Test project with modules."""
        project = Project(
            name="test-project",
            root_path=Path("/project"),
            primary_language="python",
        )

        # Add modules
        m1 = Module(
            name="main.py",
            path=Path("/project/main.py"),
            module_type=ModuleType.FILE,
            entry_point=True,
        )
        m2 = Module(name="utils.py", path=Path("/project/utils.py"), module_type=ModuleType.FILE)

        project.modules[str(m1.path)] = m1
        project.modules[str(m2.path)] = m2

        assert project.module_count == 2
        assert len(project.entry_points) == 1
        assert project.entry_points[0].name == "main.py"


class TestDependencyGraph:
    """Tests for DependencyGraph."""

    def test_empty_graph(self) -> None:
        """Test empty graph creation."""
        graph = DependencyGraph()

        assert graph.node_count == 0
        assert graph.edge_count == 0

    def test_add_modules_and_dependencies(self) -> None:
        """Test adding modules and dependencies."""
        graph = DependencyGraph()

        m1 = Module(name="main.py", path=Path("/main.py"), module_type=ModuleType.FILE)
        m2 = Module(name="utils.py", path=Path("/utils.py"), module_type=ModuleType.FILE)

        graph.add_module(m1)
        graph.add_module(m2)
        graph.add_dependency(m1.path, m2.path, "import")

        assert graph.node_count == 2
        assert graph.edge_count == 1

        deps = graph.get_dependencies(m1.path)
        assert len(deps) == 1
        assert deps[0].name == "utils.py"

    def test_entry_points(self) -> None:
        """Test finding entry points."""
        graph = DependencyGraph()

        m1 = Module(name="main.py", path=Path("/main.py"), module_type=ModuleType.FILE)
        m2 = Module(name="utils.py", path=Path("/utils.py"), module_type=ModuleType.FILE)

        graph.add_module(m1)
        graph.add_module(m2)
        graph.add_dependency(m1.path, m2.path, "import")

        entry_points = graph.get_entry_points()
        assert len(entry_points) == 1
        assert entry_points[0].name == "main.py"

    def test_to_mermaid(self) -> None:
        """Test Mermaid diagram generation."""
        graph = DependencyGraph()

        m1 = Module(name="main.py", path=Path("/main.py"), module_type=ModuleType.FILE)
        m2 = Module(name="utils.py", path=Path("/utils.py"), module_type=ModuleType.FILE)

        graph.add_module(m1)
        graph.add_module(m2)
        graph.add_dependency(m1.path, m2.path, "import")

        mermaid = graph.to_mermaid()
        assert "graph TD" in mermaid
        assert "-->" in mermaid


class TestOnboardingGuide:
    """Tests for OnboardingGuide."""

    def test_create_guide(self) -> None:
        """Test guide creation."""
        guide = OnboardingGuide(
            project_name="Test Project",
            project_path="/project",
        )

        assert guide.project_name == "Test Project"
        assert guide.sections == []

    def test_add_section(self) -> None:
        """Test adding sections."""
        guide = OnboardingGuide(
            project_name="Test Project",
            project_path="/project",
        )

        section = Section(
            section_type=SectionType.OVERVIEW,
            title="Overview",
            content="This is the overview.",
        )

        guide.add_section(section)

        assert len(guide.sections) == 1
        assert guide.get_section(SectionType.OVERVIEW) is not None

    def test_to_markdown(self) -> None:
        """Test Markdown rendering."""
        guide = OnboardingGuide(
            project_name="Test Project",
            project_path="/project",
        )

        guide.add_section(
            Section(
                section_type=SectionType.OVERVIEW,
                title="Overview",
                content="This is the project overview.",
            )
        )

        md = guide.to_markdown()

        assert "# Test Project — Onboarding Guide" in md
        assert "## Overview" in md
        assert "This is the project overview." in md
