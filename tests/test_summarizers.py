"""Tests for the summarization module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from devwayfinder.core.models import Module, ModuleType, Project
from devwayfinder.core.protocols import HealthStatus, SummarizationContext
from devwayfinder.summarizers import (
    ARCHITECTURE_SUMMARY_TEMPLATE,
    ENTRY_POINT_SUMMARY_TEMPLATE,
    MODULE_SUMMARY_TEMPLATE,
    ContextBuilder,
    PromptTemplate,
    SummarizationConfig,
    SummarizationController,
    SummarizationResult,
    SummarizationType,
    get_template,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Create a temporary project root."""
    return tmp_path


@pytest.fixture
def sample_module(tmp_path: Path) -> Module:
    """Create a sample module for testing."""
    return Module(
        name="sample.py",
        path=tmp_path / "src" / "sample.py",
        module_type=ModuleType.FILE,
        language="python",
        imports=["os", "sys", "pathlib"],
        exports=["SampleClass", "sample_function"],
        entry_point=False,
    )


@pytest.fixture
def entry_point_module(tmp_path: Path) -> Module:
    """Create a sample entry point module."""
    return Module(
        name="main.py",
        path=tmp_path / "main.py",
        module_type=ModuleType.FILE,
        language="python",
        imports=["app", "config"],
        exports=["main"],
        entry_point=True,
    )


@pytest.fixture
def sample_project(tmp_path: Path, sample_module: Module) -> Project:
    """Create a sample project with modules."""
    return Project(
        name="TestProject",
        root_path=tmp_path,
        primary_language="python",
        build_system="poetry",
        readme_content="# Test Project\n\nA sample project for testing.",
        modules={str(sample_module.path): sample_module},
    )


@pytest.fixture
def mock_provider() -> MagicMock:
    """Create a mock LLM provider."""
    provider = MagicMock()
    provider.name = "mock_provider"
    provider.summarize = AsyncMock(return_value="This is a mock summary.")
    provider.health_check = AsyncMock(return_value=HealthStatus(healthy=True, message="OK"))
    return provider


@pytest.fixture
def failing_provider() -> MagicMock:
    """Create a mock provider that always fails."""
    provider = MagicMock()
    provider.name = "failing_provider"
    provider.summarize = AsyncMock(side_effect=RuntimeError("Provider failed"))
    return provider


@pytest.fixture
def mock_structure_info() -> MagicMock:
    """Create a mock StructureInfo."""
    info = MagicMock()
    info.build_system = "poetry"
    info.package_manager = "poetry"
    return info


# =============================================================================
# Template Tests
# =============================================================================


class TestPromptTemplates:
    """Test prompt template functionality."""

    def test_module_template_exists(self) -> None:
        """Module summary template should be defined."""
        assert MODULE_SUMMARY_TEMPLATE is not None
        assert MODULE_SUMMARY_TEMPLATE.system_prompt
        assert MODULE_SUMMARY_TEMPLATE.user_prompt_template

    def test_architecture_template_exists(self) -> None:
        """Architecture summary template should be defined."""
        assert ARCHITECTURE_SUMMARY_TEMPLATE is not None
        assert ARCHITECTURE_SUMMARY_TEMPLATE.max_tokens == 512

    def test_entry_point_template_exists(self) -> None:
        """Entry point summary template should be defined."""
        assert ENTRY_POINT_SUMMARY_TEMPLATE is not None

    def test_get_template(self) -> None:
        """get_template should return correct template."""
        template = get_template(SummarizationType.MODULE)
        assert template == MODULE_SUMMARY_TEMPLATE

        template = get_template(SummarizationType.ARCHITECTURE)
        assert template == ARCHITECTURE_SUMMARY_TEMPLATE

    def test_format_user_prompt(self) -> None:
        """User prompt should format correctly."""
        template = PromptTemplate(
            system_prompt="System",
            user_prompt_template="Module: {module_name}\n{context}",
        )
        result = template.format_user_prompt(
            module_name="test.py",
            context="Some context here",
        )
        assert "test.py" in result
        assert "Some context here" in result

    def test_adaptive_template_small_utility(self, tmp_path: Path) -> None:
        """Small modules (< 50 LOC) should get UTILITY_MODULE_TEMPLATE."""
        from devwayfinder.summarizers import (
            CORE_MODULE_TEMPLATE,
            UTILITY_MODULE_TEMPLATE,
            get_adaptive_template,
        )

        module = Module(
            name="util.py",
            path=tmp_path / "util.py",
            module_type=ModuleType.FILE,
            language="python",
            loc=30,  # Small utility
            complexity=1.0,
        )
        template = get_adaptive_template(module)
        assert template == UTILITY_MODULE_TEMPLATE
        assert template.max_tokens == 100

    def test_adaptive_template_standard_module(self, tmp_path: Path) -> None:
        """Standard modules (50-500 LOC) should get MODULE_SUMMARY_TEMPLATE."""
        from devwayfinder.summarizers import get_adaptive_template

        module = Module(
            name="core.py",
            path=tmp_path / "core.py",
            module_type=ModuleType.FILE,
            language="python",
            loc=200,  # Standard size
            complexity=2.5,
        )
        template = get_adaptive_template(module)
        assert template == MODULE_SUMMARY_TEMPLATE
        assert template.max_tokens == 200

    def test_adaptive_template_large_module_by_loc(self, tmp_path: Path) -> None:
        """Large modules (> 500 LOC) should get CORE_MODULE_TEMPLATE."""
        from devwayfinder.summarizers import CORE_MODULE_TEMPLATE, get_adaptive_template

        module = Module(
            name="legacy.py",
            path=tmp_path / "legacy.py",
            module_type=ModuleType.FILE,
            language="python",
            loc=800,  # Large
            complexity=3.0,
        )
        template = get_adaptive_template(module)
        assert template == CORE_MODULE_TEMPLATE
        assert template.max_tokens == 300

    def test_adaptive_template_complex_module_by_complexity(self, tmp_path: Path) -> None:
        """Complex modules (complexity > 5) should get CORE_MODULE_TEMPLATE."""
        from devwayfinder.summarizers import CORE_MODULE_TEMPLATE, get_adaptive_template

        module = Module(
            name="complex.py",
            path=tmp_path / "complex.py",
            module_type=ModuleType.FILE,
            language="python",
            loc=300,  # Medium size
            complexity=8.5,  # High complexity
        )
        template = get_adaptive_template(module)
        assert template == CORE_MODULE_TEMPLATE
        assert template.max_tokens == 300

    def test_adaptive_template_handles_none_loc(self, tmp_path: Path) -> None:
        """Should handle modules with None LOC gracefully."""
        from devwayfinder.summarizers import get_adaptive_template

        module = Module(
            name="unknown.py",
            path=tmp_path / "unknown.py",
            module_type=ModuleType.FILE,
            language="python",
            loc=None,  # No LOC data
            complexity=None,
        )
        template = get_adaptive_template(module)
        # Should default to MODULE_SUMMARY_TEMPLATE for unknowns
        assert template == MODULE_SUMMARY_TEMPLATE

    def test_adaptive_template_boundary_at_50_loc(self, tmp_path: Path) -> None:
        """Boundary test: 50 LOC should use standard template."""
        from devwayfinder.summarizers import get_adaptive_template

        module = Module(
            name="boundary.py",
            path=tmp_path / "boundary.py",
            module_type=ModuleType.FILE,
            language="python",
            loc=50,  # Exactly at boundary
            complexity=1.0,
        )
        template = get_adaptive_template(module)
        # At 50 LOC, should be standard (not utility)
        assert template == MODULE_SUMMARY_TEMPLATE

    def test_adaptive_template_boundary_at_500_loc(self, tmp_path: Path) -> None:
        """Boundary test: 500 LOC should use standard template."""
        from devwayfinder.summarizers import get_adaptive_template

        module = Module(
            name="boundary.py",
            path=tmp_path / "boundary.py",
            module_type=ModuleType.FILE,
            language="python",
            loc=500,  # Exactly at boundary
            complexity=3.0,
        )
        template = get_adaptive_template(module)
        # At 500 LOC, should be standard (not core)
        assert template == MODULE_SUMMARY_TEMPLATE

    def test_adaptive_template_boundary_above_500_loc(self, tmp_path: Path) -> None:
        """Boundary test: 501 LOC should use core template."""
        from devwayfinder.summarizers import CORE_MODULE_TEMPLATE, get_adaptive_template

        module = Module(
            name="boundary.py",
            path=tmp_path / "boundary.py",
            module_type=ModuleType.FILE,
            language="python",
            loc=501,  # Just above boundary
            complexity=3.0,
        )
        template = get_adaptive_template(module)
        # At 501 LOC, should be core
        assert template == CORE_MODULE_TEMPLATE


# =============================================================================
# Context Builder Tests
# =============================================================================


class TestContextBuilder:
    """Test context building functionality."""

    def test_from_module(self, project_root: Path, sample_module: Module) -> None:
        """Should build context from Module."""
        builder = ContextBuilder(project_root)
        context = builder.from_module(sample_module)

        assert context.module_name == "sample.py"
        assert "os" in context.imports
        assert "SampleClass" in context.exports

    def test_from_module_with_graph(self, project_root: Path, sample_module: Module) -> None:
        """Should include neighbors when graph provided."""
        from devwayfinder.core.graph import DependencyGraph

        graph = DependencyGraph()
        graph.add_module(sample_module)

        # Create a dependency
        dep_module = Module(
            name="utils.py",
            path=project_root / "src" / "utils.py",
            module_type=ModuleType.FILE,
        )
        graph.add_module(dep_module)
        graph.add_dependency(sample_module.path, dep_module.path)

        builder = ContextBuilder(project_root)
        context = builder.from_module(sample_module, graph=graph)

        assert "utils.py" in context.neighbors

    def test_for_architecture(
        self,
        project_root: Path,
        sample_project: Project,
        mock_structure_info: MagicMock,
    ) -> None:
        """Should build architecture context."""
        builder = ContextBuilder(project_root)
        context = builder.for_architecture(sample_project, mock_structure_info)

        assert context.module_name == "TestProject"
        assert context.metadata["build_system"] == "poetry"
        assert context.metadata["module_count"] == 1

    def test_for_entry_point(self, project_root: Path, entry_point_module: Module) -> None:
        """Should build entry point context with special metadata."""
        builder = ContextBuilder(project_root)
        context = builder.for_entry_point(entry_point_module)

        assert context.module_name == "main.py"
        assert context.metadata["is_entry_point"] is True

    def test_relative_name(self, project_root: Path) -> None:
        """Should compute relative names correctly."""
        builder = ContextBuilder(project_root)

        # Path within project
        path = project_root / "src" / "module.py"
        name = builder._relative_name(path)
        assert name == "src\\module.py" or name == "src/module.py"

        # Path outside project uses basename
        external = Path("/other/project/file.py")
        name = builder._relative_name(external)
        assert name == "file.py"


# =============================================================================
# Summarization Controller Tests
# =============================================================================


class TestSummarizationController:
    """Test the SummarizationController orchestrator."""

    @pytest.mark.asyncio
    async def test_summarize_module_with_provider(
        self,
        project_root: Path,
        sample_module: Module,
        mock_provider: MagicMock,
    ) -> None:
        """Should use provider to summarize module."""
        config = SummarizationConfig(providers=[mock_provider])
        controller = SummarizationController(project_root, config)

        result = await controller.summarize_module(sample_module)

        assert result.success
        assert result.summary == "This is a mock summary."
        assert result.provider_used == "mock_provider"
        assert result.summary_type == SummarizationType.MODULE

    @pytest.mark.asyncio
    async def test_fallback_to_heuristic(
        self,
        project_root: Path,
        sample_module: Module,
        failing_provider: MagicMock,
    ) -> None:
        """Should fall back to heuristic when provider fails."""
        config = SummarizationConfig(
            providers=[failing_provider],
            use_heuristic_fallback=True,
            max_retries=1,
        )
        controller = SummarizationController(project_root, config)

        result = await controller.summarize_module(sample_module)

        assert result.success
        assert result.provider_used == "heuristic"
        assert "sample.py" in result.summary

    @pytest.mark.asyncio
    async def test_no_fallback_fails(
        self,
        project_root: Path,
        sample_module: Module,
        failing_provider: MagicMock,
    ) -> None:
        """Should fail when fallback disabled and provider fails."""
        config = SummarizationConfig(
            providers=[failing_provider],
            use_heuristic_fallback=False,
            max_retries=1,
        )
        controller = SummarizationController(project_root, config)

        result = await controller.summarize_module(sample_module)

        assert not result.success
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_provider_chain_fallback(
        self,
        project_root: Path,
        sample_module: Module,
        failing_provider: MagicMock,
        mock_provider: MagicMock,
    ) -> None:
        """Should try next provider when first fails."""
        config = SummarizationConfig(
            providers=[failing_provider, mock_provider],
            max_retries=1,
        )
        controller = SummarizationController(project_root, config)

        result = await controller.summarize_module(sample_module)

        assert result.success
        assert result.provider_used == "mock_provider"

    @pytest.mark.asyncio
    async def test_heuristic_only(
        self,
        project_root: Path,
        sample_module: Module,
    ) -> None:
        """Should work with no providers (heuristic only)."""
        config = SummarizationConfig(
            providers=[],
            use_heuristic_fallback=True,
        )
        controller = SummarizationController(project_root, config)

        result = await controller.summarize_module(sample_module)

        assert result.success
        assert result.provider_used == "heuristic"

    @pytest.mark.asyncio
    async def test_summarize_entry_point(
        self,
        project_root: Path,
        entry_point_module: Module,
        mock_provider: MagicMock,
    ) -> None:
        """Should summarize entry point with correct type."""
        config = SummarizationConfig(providers=[mock_provider])
        controller = SummarizationController(project_root, config)

        result = await controller.summarize_entry_point(entry_point_module)

        assert result.success
        assert result.summary_type == SummarizationType.ENTRY_POINT

    @pytest.mark.asyncio
    async def test_summarize_architecture(
        self,
        project_root: Path,
        sample_project: Project,
        mock_structure_info: MagicMock,
        mock_provider: MagicMock,
    ) -> None:
        """Should summarize architecture with correct type."""
        config = SummarizationConfig(providers=[mock_provider])
        controller = SummarizationController(project_root, config)

        result = await controller.summarize_architecture(sample_project, mock_structure_info)

        assert result.success
        assert result.summary_type == SummarizationType.ARCHITECTURE

    @pytest.mark.asyncio
    async def test_batch_summarization(
        self,
        project_root: Path,
        mock_provider: MagicMock,
    ) -> None:
        """Should summarize multiple modules concurrently."""
        modules = [
            Module(
                name=f"module{i}.py",
                path=project_root / f"module{i}.py",
                module_type=ModuleType.FILE,
            )
            for i in range(5)
        ]

        config = SummarizationConfig(
            providers=[mock_provider],
            max_concurrent_requests=3,
        )
        controller = SummarizationController(project_root, config)

        results = await controller.summarize_modules_batch(modules)

        assert len(results) == 5
        assert all(r.success for r in results.values())

    @pytest.mark.asyncio
    async def test_add_provider(
        self,
        project_root: Path,
        mock_provider: MagicMock,
    ) -> None:
        """Should add provider to chain."""
        controller = SummarizationController(project_root)
        assert len(controller.config.providers) == 0

        controller.add_provider(mock_provider)
        assert len(controller.config.providers) == 1

    @pytest.mark.asyncio
    async def test_clear_providers(
        self,
        project_root: Path,
        mock_provider: MagicMock,
    ) -> None:
        """Should clear all providers."""
        config = SummarizationConfig(providers=[mock_provider])
        controller = SummarizationController(project_root, config)

        controller.clear_providers()
        assert len(controller.config.providers) == 0


# =============================================================================
# Heuristic Summary Tests
# =============================================================================


class TestHeuristicSummaries:
    """Test heuristic (non-LLM) summary generation."""

    @pytest.mark.asyncio
    async def test_module_heuristic_with_docstring(self, project_root: Path) -> None:
        """Heuristic should use docstring when available."""
        Module(
            name="documented.py",
            path=project_root / "documented.py",
            module_type=ModuleType.FILE,
        )

        controller = SummarizationController(project_root)
        context = SummarizationContext(
            module_name="documented.py",
            docstrings=["This module handles user authentication."],
            signatures=["def authenticate(user, password)"],
            imports=["hashlib", "secrets"],
        )

        summary = controller._heuristic_module_summary(context)

        assert "documented.py" in summary
        assert "authentication" in summary.lower()

    @pytest.mark.asyncio
    async def test_module_heuristic_with_signatures(self, project_root: Path) -> None:
        """Heuristic should describe signatures."""
        controller = SummarizationController(project_root)
        context = SummarizationContext(
            module_name="utils.py",
            signatures=["def parse_json(data)", "class Parser"],
            imports=["json"],
        )

        summary = controller._heuristic_module_summary(context)

        assert "def parse_json" in summary or "Provides" in summary

    @pytest.mark.asyncio
    async def test_architecture_heuristic(self, project_root: Path) -> None:
        """Heuristic architecture summary should include key info."""
        controller = SummarizationController(project_root)
        context = SummarizationContext(
            module_name="MyProject",
            metadata={
                "build_system": "poetry",
                "primary_language": "Python",
                "module_count": 42,
                "readme_excerpt": "A powerful framework for...",
            },
        )

        summary = controller._heuristic_architecture_summary(context)

        assert "MyProject" in summary
        assert "poetry" in summary
        assert "42" in summary

    @pytest.mark.asyncio
    async def test_entry_point_heuristic(self, project_root: Path) -> None:
        """Heuristic entry point summary should guide exploration."""
        controller = SummarizationController(project_root)
        context = SummarizationContext(
            module_name="main.py",
            docstrings=["Main entry point for the CLI."],
            neighbors=["cli", "config", "app"],
            metadata={"has_main": True},
        )

        summary = controller._heuristic_entry_point_summary(context)

        assert "main.py" in summary
        assert "__main__" in summary or "directly" in summary


# =============================================================================
# SummarizationResult Tests
# =============================================================================


class TestSummarizationResult:
    """Test the SummarizationResult dataclass."""

    def test_successful_result(self) -> None:
        """Should create successful result."""
        result = SummarizationResult(
            summary="Test summary",
            provider_used="openai",
            summary_type=SummarizationType.MODULE,
            module_name="test.py",
            success=True,
        )

        assert result.success
        assert result.error is None
        assert result.summary == "Test summary"

    def test_failed_result(self) -> None:
        """Should create failed result with error."""
        result = SummarizationResult(
            summary="",
            provider_used="none",
            summary_type=SummarizationType.MODULE,
            module_name="test.py",
            success=False,
            error="Provider unavailable",
        )

        assert not result.success
        assert result.error == "Provider unavailable"


# =============================================================================
# SummarizationConfig Tests
# =============================================================================


class TestSummarizationConfig:
    """Test the SummarizationConfig dataclass."""

    def test_default_config(self) -> None:
        """Should have sensible defaults."""
        config = SummarizationConfig()

        assert config.providers == []
        assert config.use_heuristic_fallback is True
        assert config.max_concurrent_requests == 5
        assert config.max_retries == 2

    def test_custom_config(self, mock_provider: MagicMock) -> None:
        """Should accept custom values."""
        config = SummarizationConfig(
            providers=[mock_provider],
            use_heuristic_fallback=False,
            max_concurrent_requests=10,
            max_retries=5,
        )

        assert len(config.providers) == 1
        assert config.use_heuristic_fallback is False
        assert config.max_concurrent_requests == 10
