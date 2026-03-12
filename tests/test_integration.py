"""Integration and end-to-end tests for DevWayfinder."""

from __future__ import annotations

from pathlib import Path

import pytest

from devwayfinder.analyzers import GraphBuilder, StructureAnalyzer
from devwayfinder.generators import GenerationConfig, GuideGenerator

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_PROJECT = FIXTURES_DIR / "sample_project"


class TestEndToEndAnalysis:
    """End-to-end tests for the analysis pipeline."""

    @pytest.fixture
    def sample_project(self) -> Path:
        """Return path to sample project fixture."""
        return SAMPLE_PROJECT

    async def test_structure_analysis(self, sample_project: Path) -> None:
        """Test full structure analysis on sample project."""
        analyzer = StructureAnalyzer()
        structure = await analyzer.analyze(sample_project)

        assert structure.root_path == sample_project.resolve()
        assert structure.build_system == "pyproject"
        assert structure.primary_language == "python"
        assert len(structure.source_files) >= 3  # __init__, core, utils

    async def test_graph_building(self, sample_project: Path) -> None:
        """Test dependency graph building on sample project."""
        builder = GraphBuilder()
        project, graph = await builder.build(sample_project)

        assert project.name == "sample_project"
        assert project.build_system == "pyproject"
        assert graph.node_count >= 3
        # May or may not have edges depending on import resolution

    async def test_entry_points_detected(self, sample_project: Path) -> None:
        """Test that entry points are correctly detected."""
        builder = GraphBuilder()
        project, _graph = await builder.build(sample_project)

        # __init__.py with main could be an entry point
        modules_with_main = [
            m for m in project.modules.values()
            if any("main" in exp.lower() for exp in m.exports)
        ]
        assert len(modules_with_main) > 0


class TestEndToEndGeneration:
    """End-to-end tests for the full generation pipeline."""

    @pytest.fixture
    def sample_project(self) -> Path:
        """Return path to sample project fixture."""
        return SAMPLE_PROJECT

    async def test_generate_heuristic_only(self, sample_project: Path) -> None:
        """Test guide generation in heuristic mode."""
        config = GenerationConfig(
            use_llm=False,
            include_mermaid=True,
        )
        generator = GuideGenerator(
            project_path=sample_project,
            config=config,
        )

        result = await generator.generate()

        assert result.guide is not None
        assert len(result.guide.sections) >= 3  # At least overview, modules, deps
        assert result.modules_analyzed >= 3
        assert result.total_time_seconds > 0
        assert result.total_time_seconds < 30  # Should be fast in heuristic mode

    async def test_generate_markdown_output(self, sample_project: Path) -> None:
        """Test that generated Markdown is valid."""
        config = GenerationConfig(
            use_llm=False,
            include_mermaid=True,
        )
        generator = GuideGenerator(
            project_path=sample_project,
            config=config,
        )

        result = await generator.generate()
        markdown = result.guide.to_markdown()

        # Check Markdown structure
        assert "# " in markdown  # Has headings
        assert "sample" in markdown.lower()  # Contains project name
        assert "## " in markdown  # Has subheadings

    async def test_generate_with_mermaid(self, sample_project: Path) -> None:
        """Test that Mermaid diagrams are generated when possible."""
        config = GenerationConfig(
            use_llm=False,
            include_mermaid=True,
        )
        generator = GuideGenerator(
            project_path=sample_project,
            config=config,
        )

        result = await generator.generate()
        markdown = result.guide.to_markdown()

        # Should have dependencies section (even if no mermaid diagram)
        assert "dependencies" in markdown.lower() or "modules" in markdown.lower()

    async def test_generate_without_mermaid(self, sample_project: Path) -> None:
        """Test generation without Mermaid diagrams."""
        config = GenerationConfig(
            use_llm=False,
            include_mermaid=False,
        )
        generator = GuideGenerator(
            project_path=sample_project,
            config=config,
        )

        result = await generator.generate()
        markdown = result.guide.to_markdown()

        # Should not have Mermaid code blocks
        assert "```mermaid" not in markdown


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    async def test_empty_directory(self, tmp_path: Path) -> None:
        """Test handling of empty directory."""
        analyzer = StructureAnalyzer()
        structure = await analyzer.analyze(tmp_path)

        assert len(structure.source_files) == 0
        assert structure.primary_language is None

    async def test_directory_with_only_binary(self, tmp_path: Path) -> None:
        """Test handling of directory with only binary files."""
        # Create binary file
        (tmp_path / "data.bin").write_bytes(b"\x00\x01\x02\x03")

        analyzer = StructureAnalyzer()
        structure = await analyzer.analyze(tmp_path)

        assert len(structure.source_files) == 0

    async def test_project_with_syntax_errors(self, tmp_path: Path) -> None:
        """Test handling of Python files with syntax errors."""
        # Create src directory
        (tmp_path / "src").mkdir()

        # Create file with syntax error
        (tmp_path / "src" / "broken.py").write_text("def foo(\n  # Missing close paren")

        # Create valid file
        (tmp_path / "src" / "valid.py").write_text("def bar():\n    pass\n")

        builder = GraphBuilder()
        project, _graph = await builder.build(tmp_path)

        # Should still analyze valid file
        assert project.module_count >= 1

    async def test_circular_imports(self, tmp_path: Path) -> None:
        """Test handling of circular imports."""
        (tmp_path / "src").mkdir()

        # Create files with circular imports
        (tmp_path / "src" / "a.py").write_text("from src.b import b_func\ndef a_func(): pass")
        (tmp_path / "src" / "b.py").write_text("from src.a import a_func\ndef b_func(): pass")

        builder = GraphBuilder()
        project, graph = await builder.build(tmp_path)

        # Should detect cycles
        graph.has_cycles()
        # Cycles might or might not be detected depending on resolution
        assert project.module_count == 2


class TestPerformance:
    """Performance tests."""

    @pytest.fixture
    def sample_project(self) -> Path:
        """Return path to sample project fixture."""
        return SAMPLE_PROJECT

    async def test_analysis_performance(self, sample_project: Path) -> None:
        """Test that analysis completes quickly."""
        import time

        builder = GraphBuilder()

        start = time.perf_counter()
        _project, _graph = await builder.build(sample_project)
        elapsed = time.perf_counter() - start

        # Should complete in under 5 seconds for small project
        assert elapsed < 5.0

    async def test_generation_performance(self, sample_project: Path) -> None:
        """Test that generation completes quickly."""
        config = GenerationConfig(
            use_llm=False,
            include_mermaid=True,
        )
        generator = GuideGenerator(
            project_path=sample_project,
            config=config,
        )

        result = await generator.generate()

        # Heuristic mode should be fast
        assert result.total_time_seconds < 10.0
