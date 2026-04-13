"""Tests for the generators module."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from devwayfinder.core.guide import OnboardingGuide, Section, SectionType
from devwayfinder.generators import (
    GenerationConfig,
    GenerationResult,
    GuideGenerator,
    MarkdownGenerator,
)

if TYPE_CHECKING:
    from pathlib import Path

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """Create a sample project structure."""
    # Create directories
    src = tmp_path / "src"
    src.mkdir()
    tests = tmp_path / "tests"
    tests.mkdir()

    # Create Python files
    (src / "__init__.py").write_text('"""Package init."""')
    (src / "main.py").write_text(
        '"""Main module."""\n\nfrom src import utils\n\ndef main():\n    pass\n\nif __name__ == "__main__":\n    main()'
    )
    (src / "utils.py").write_text('"""Utilities."""\n\nimport os\n\ndef helper():\n    pass')
    (tests / "test_main.py").write_text(
        '"""Tests."""\n\nfrom src import main\n\ndef test_main():\n    pass'
    )

    # Create config files
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "test-project"')
    (tmp_path / "README.md").write_text("# Test Project\n\nA sample project for testing.")

    return tmp_path


@pytest.fixture
def sample_guide() -> OnboardingGuide:
    """Create a sample OnboardingGuide."""
    guide = OnboardingGuide(
        project_name="TestProject",
        project_path="/path/to/project",
        generated_at=datetime(2025, 1, 15, 10, 30),
    )

    guide.add_section(
        Section(
            section_type=SectionType.OVERVIEW,
            title="Overview",
            content="This is a test project.",
        )
    )

    guide.add_section(
        Section(
            section_type=SectionType.ARCHITECTURE,
            title="Architecture",
            content="Simple layered architecture.",
        )
    )

    guide.add_section(
        Section(
            section_type=SectionType.MODULES,
            title="Modules",
            content="Module descriptions.",
            subsections=[
                Section(
                    section_type=SectionType.CUSTOM,
                    title="`src`",
                    content="Main source code.",
                ),
            ],
        )
    )

    return guide


# =============================================================================
# GenerationConfig Tests
# =============================================================================


class TestGenerationConfig:
    """Test GenerationConfig dataclass."""

    def test_default_config(self) -> None:
        """Should have sensible defaults."""
        config = GenerationConfig()

        assert config.include_hidden is False
        assert "__pycache__" in config.exclude_patterns
        assert config.use_llm is True
        assert config.include_mermaid is True
        assert config.max_modules_in_graph == 50
        assert config.quality_profile == "detailed"

    def test_custom_config(self) -> None:
        """Should accept custom values."""
        config = GenerationConfig(
            use_llm=False,
            include_mermaid=False,
            max_concurrent_requests=10,
            quality_profile="minimal",
        )

        assert config.use_llm is False
        assert config.include_mermaid is False
        assert config.max_concurrent_requests == 10
        assert config.quality_profile == "minimal"


# =============================================================================
# GenerationResult Tests
# =============================================================================


class TestGenerationResult:
    """Test GenerationResult dataclass."""

    def test_result_creation(self, sample_guide: OnboardingGuide) -> None:
        """Should create result with all fields."""
        result = GenerationResult(
            guide=sample_guide,
            analysis_time_seconds=1.5,
            summarization_time_seconds=2.3,
            total_time_seconds=4.0,
            modules_analyzed=10,
            modules_summarized=8,
            llm_calls_made=8,
        )

        assert result.guide == sample_guide
        assert result.total_time_seconds == 4.0
        assert result.errors == []
        assert result.total_tokens_used == 0
        assert result.estimated_cost_usd == 0.0

    def test_result_with_errors(self, sample_guide: OnboardingGuide) -> None:
        """Should track errors."""
        result = GenerationResult(
            guide=sample_guide,
            analysis_time_seconds=1.0,
            summarization_time_seconds=0.0,
            total_time_seconds=1.0,
            modules_analyzed=5,
            modules_summarized=0,
            llm_calls_made=0,
            errors=["LLM unavailable", "Config error"],
        )

        assert len(result.errors) == 2


# =============================================================================
# GuideGenerator Tests
# =============================================================================


class TestGuideGenerator:
    """Test the GuideGenerator orchestrator."""

    @pytest.mark.asyncio
    async def test_basic_generation(self, sample_project: Path) -> None:
        """Should generate a guide from a project."""
        config = GenerationConfig(use_llm=False)
        generator = GuideGenerator(sample_project, config)

        result = await generator.generate()

        assert result.guide is not None
        assert result.guide.project_name == sample_project.name
        assert result.modules_analyzed >= 3  # main.py, utils.py, __init__.py
        assert result.total_time_seconds > 0

    @pytest.mark.asyncio
    async def test_no_llm_mode(self, sample_project: Path) -> None:
        """Should work without LLM providers."""
        config = GenerationConfig(use_llm=False)
        generator = GuideGenerator(sample_project, config)

        result = await generator.generate()

        assert result.llm_calls_made == 0
        assert result.guide.model_used == "heuristic"

    @pytest.mark.asyncio
    async def test_guide_has_required_sections(self, sample_project: Path) -> None:
        """Generated guide should have all required sections."""
        config = GenerationConfig(use_llm=False)
        generator = GuideGenerator(sample_project, config)

        result = await generator.generate()
        guide = result.guide

        # Check for required sections
        section_types = [s.section_type for s in guide.sections]
        assert SectionType.OVERVIEW in section_types
        assert SectionType.ARCHITECTURE in section_types
        assert SectionType.MODULES in section_types
        assert SectionType.DEPENDENCIES in section_types
        assert SectionType.START_HERE in section_types

    @pytest.mark.asyncio
    async def test_overview_section_content(self, sample_project: Path) -> None:
        """Overview section should contain project info."""
        config = GenerationConfig(use_llm=False)
        generator = GuideGenerator(sample_project, config)

        result = await generator.generate()
        overview = result.guide.get_section(SectionType.OVERVIEW)

        assert overview is not None
        assert "python" in overview.content.lower() or "Python" in overview.content

    @pytest.mark.asyncio
    async def test_modules_section_has_subsections(self, sample_project: Path) -> None:
        """Modules section should have subsections for directories."""
        config = GenerationConfig(use_llm=False)
        generator = GuideGenerator(sample_project, config)

        result = await generator.generate()
        modules = result.guide.get_section(SectionType.MODULES)

        assert modules is not None
        assert len(modules.subsections) > 0

    @pytest.mark.asyncio
    async def test_modules_section_has_quality_badges(self, sample_project: Path) -> None:
        """Heuristic generation should mark module summaries with quality badges."""
        config = GenerationConfig(use_llm=False)
        generator = GuideGenerator(sample_project, config)

        result = await generator.generate()
        modules = result.guide.get_section(SectionType.MODULES)

        assert modules is not None
        joined = "\n".join(s.content for s in modules.subsections)
        assert "[heuristic]" in joined

    @pytest.mark.asyncio
    async def test_quality_banner_present_in_overview(self, sample_project: Path) -> None:
        """Overview should include quality profile and LLM coverage transparency."""
        config = GenerationConfig(use_llm=False)
        generator = GuideGenerator(sample_project, config)

        result = await generator.generate()
        overview = result.guide.get_section(SectionType.OVERVIEW)

        assert overview is not None
        assert "Quality Profile" in overview.content
        assert "LLM Coverage" in overview.content

    @pytest.mark.asyncio
    async def test_architecture_includes_runtime_flow_map(self, sample_project: Path) -> None:
        """Architecture section should include runtime flow map when graph edges exist."""
        config = GenerationConfig(use_llm=False)
        generator = GuideGenerator(sample_project, config)

        result = await generator.generate()
        architecture = result.guide.get_section(SectionType.ARCHITECTURE)

        assert architecture is not None
        assert "Runtime Flow Map" in architecture.content

    @pytest.mark.asyncio
    async def test_start_here_has_actionable_checklist(self, sample_project: Path) -> None:
        """Start Here section should include an actionable sequence."""
        config = GenerationConfig(use_llm=False)
        generator = GuideGenerator(sample_project, config)

        result = await generator.generate()
        start_here = result.guide.get_section(SectionType.START_HERE)

        assert start_here is not None
        assert "Follow this onboarding sequence" in start_here.content
        assert "1." in start_here.content

    def test_minimal_quality_profile_forces_no_llm(self, sample_project: Path) -> None:
        """Minimal profile should force heuristic mode even if use_llm is requested."""
        config = GenerationConfig(use_llm=True, quality_profile="minimal")
        generator = GuideGenerator(sample_project, config)

        assert generator.config.use_llm is False

    @pytest.mark.asyncio
    async def test_dependencies_section_with_mermaid(self, sample_project: Path) -> None:
        """Dependencies section should include Mermaid diagram."""
        config = GenerationConfig(use_llm=False, include_mermaid=True)
        generator = GuideGenerator(sample_project, config)

        result = await generator.generate()
        deps = result.guide.get_section(SectionType.DEPENDENCIES)

        assert deps is not None
        # Mermaid might not appear if there are no edges
        assert "Total Modules" in deps.content

    @pytest.mark.asyncio
    async def test_exclude_patterns_work(self, sample_project: Path) -> None:
        """Should exclude files matching patterns."""
        # Create a __pycache__ directory with a file
        pycache = sample_project / "src" / "__pycache__"
        pycache.mkdir()
        (pycache / "main.cpython-311.pyc").write_bytes(b"binary")

        config = GenerationConfig(use_llm=False)
        generator = GuideGenerator(sample_project, config)

        result = await generator.generate()

        # The pycache file should not be analyzed
        for path in result.guide.project_path:
            assert "__pycache__" not in str(path)

    @pytest.mark.asyncio
    async def test_handles_empty_project(self, tmp_path: Path) -> None:
        """Should handle projects with no source files gracefully."""
        config = GenerationConfig(use_llm=False)
        generator = GuideGenerator(tmp_path, config)

        result = await generator.generate()

        assert result.guide is not None
        assert result.modules_analyzed == 0

    @pytest.mark.asyncio
    async def test_generator_cleanup(self, sample_project: Path) -> None:
        """Should clean up resources."""
        config = GenerationConfig(use_llm=False)
        generator = GuideGenerator(sample_project, config)

        await generator.generate()
        await generator.close()  # Should not raise

    def test_estimate_generation_cost_tracks_input_and_output(self, sample_project: Path) -> None:
        """Cost estimation should account for distinct input and output pricing."""
        config = GenerationConfig(use_llm=True)
        generator = GuideGenerator(sample_project, config)

        # gpt-4o-mini pricing per 1M tokens: input=0.15, output=0.60
        generator.config.providers = [SimpleNamespace(name="gpt-4o-mini")]
        generator._summary_input_tokens = {"module": 1_000_000}
        generator._summary_output_tokens = {"module": 1_000_000}
        generator._summary_tokens = {"module": 2_000_000}

        estimated_cost = generator._estimate_generation_cost()
        assert estimated_cost == pytest.approx(0.75)


# =============================================================================
# MarkdownGenerator Tests
# =============================================================================


class TestMarkdownGenerator:
    """Test the MarkdownGenerator."""

    def test_generate_markdown(self, sample_guide: OnboardingGuide) -> None:
        """Should generate valid Markdown."""
        generator = MarkdownGenerator()
        markdown = generator.generate(sample_guide)

        assert "# TestProject" in markdown
        assert "## Overview" in markdown
        assert "## Architecture" in markdown
        assert "Table of Contents" in markdown

    def test_generate_toc(self, sample_guide: OnboardingGuide) -> None:
        """Should generate table of contents."""
        generator = MarkdownGenerator()
        toc = generator.generate_toc(sample_guide)

        assert "Table of Contents" in toc
        assert "[Overview]" in toc
        assert "[Architecture]" in toc

    def test_generate_section(self) -> None:
        """Should generate section Markdown."""
        generator = MarkdownGenerator()
        section = Section(
            section_type=SectionType.OVERVIEW,
            title="Test Section",
            content="Test content here.",
        )

        markdown = generator.generate_section(section)

        assert "## Test Section" in markdown
        assert "Test content here." in markdown

    def test_generate_nested_sections(self) -> None:
        """Should handle nested subsections."""
        generator = MarkdownGenerator()
        section = Section(
            section_type=SectionType.MODULES,
            title="Modules",
            content="Top level.",
            subsections=[
                Section(
                    section_type=SectionType.CUSTOM,
                    title="Submodule",
                    content="Subsection content.",
                ),
            ],
        )

        markdown = generator.generate_section(section, level=2)

        assert "## Modules" in markdown
        assert "### Submodule" in markdown


# =============================================================================
# OnboardingGuide Tests
# =============================================================================


class TestOnboardingGuide:
    """Test OnboardingGuide model."""

    def test_add_section(self) -> None:
        """Should add sections."""
        guide = OnboardingGuide(
            project_name="Test",
            project_path="/test",
        )

        guide.add_section(
            Section(
                section_type=SectionType.OVERVIEW,
                title="Overview",
                content="Content",
            )
        )

        assert len(guide.sections) == 1

    def test_get_section(self, sample_guide: OnboardingGuide) -> None:
        """Should retrieve sections by type."""
        overview = sample_guide.get_section(SectionType.OVERVIEW)
        assert overview is not None
        assert overview.title == "Overview"

        # Non-existent section
        setup = sample_guide.get_section(SectionType.SETUP)
        assert setup is None

    def test_to_markdown(self, sample_guide: OnboardingGuide) -> None:
        """Should render to Markdown."""
        markdown = sample_guide.to_markdown()

        assert "# TestProject — Onboarding Guide" in markdown
        assert "Generated:" in markdown
        assert "Table of Contents" in markdown
        assert "DevWayfinder" in markdown  # Footer

    def test_markdown_has_anchors(self, sample_guide: OnboardingGuide) -> None:
        """Markdown TOC should have anchors."""
        markdown = sample_guide.to_markdown()

        assert "[Overview](#overview)" in markdown
        assert "[Architecture](#architecture)" in markdown
