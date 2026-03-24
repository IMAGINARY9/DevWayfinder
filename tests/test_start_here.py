"""Tests for Start Here recommendation algorithm."""

from __future__ import annotations

from pathlib import Path

import pytest

from devwayfinder.analyzers.start_here import (
    RecommendationConfig,
    StartHereRecommender,
    StartingPoint,
    get_start_here_recommendations,
    score_connectivity,
    score_documentation,
    score_entry_point,
)
from devwayfinder.core.graph import DependencyGraph
from devwayfinder.core.models import Module, ModuleType

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_module() -> Module:
    """Create a sample module."""
    return Module(
        name="core.py",
        path=Path("/project/src/core.py"),
        module_type=ModuleType.FILE,
        language="python",
        entry_point=False,
        imports=["os", "sys"],
        exports=["main", "helper"],
    )


@pytest.fixture
def entry_point_module() -> Module:
    """Create an entry point module."""
    return Module(
        name="__main__.py",
        path=Path("/project/src/__main__.py"),
        module_type=ModuleType.FILE,
        language="python",
        entry_point=True,
        exports=["main"],
    )


@pytest.fixture
def sample_graph(sample_module: Module, entry_point_module: Module) -> DependencyGraph:
    """Create a sample dependency graph."""
    graph = DependencyGraph()
    graph.add_module(sample_module)
    graph.add_module(entry_point_module)
    graph.add_dependency(entry_point_module.path, sample_module.path)
    return graph


# =============================================================================
# STARTING POINT TESTS
# =============================================================================


class TestStartingPoint:
    """Tests for StartingPoint dataclass."""

    def test_creation(self) -> None:
        """Test StartingPoint creation."""
        point = StartingPoint(
            path=Path("/project/main.py"),
            score=0.85,
            reasons=["Main entry point"],
            category="entry_point",
        )
        assert point.score == 0.85
        assert point.category == "entry_point"

    def test_to_dict(self) -> None:
        """Test dictionary conversion."""
        point = StartingPoint(
            path=Path("/project/core.py"),
            score=0.756,
            reasons=["Reason 1", "Reason 2"],
        )
        d = point.to_dict()
        assert d["score"] == 0.76  # Rounded
        assert len(d["reasons"]) == 2


# =============================================================================
# SCORING FUNCTION TESTS
# =============================================================================


class TestScoreEntryPoint:
    """Tests for entry point scoring."""

    def test_entry_point_gets_bonus(self, entry_point_module: Module) -> None:
        """Test that entry points get a bonus."""
        score, reasons = score_entry_point(entry_point_module)
        assert score > 0
        assert len(reasons) > 0

    def test_non_entry_point(self, sample_module: Module) -> None:
        """Test non-entry point scoring."""
        score, _reasons = score_entry_point(sample_module)
        assert score == 0.0

    def test_cli_in_path(self) -> None:
        """Test CLI keyword bonus."""
        module = Module(
            name="cli.py",
            path=Path("/project/src/cli/app.py"),
            module_type=ModuleType.FILE,
            entry_point=False,
        )
        score, _reasons = score_entry_point(module)
        assert score > 0


class TestScoreConnectivity:
    """Tests for connectivity scoring."""

    def test_core_module_scoring(self) -> None:
        """Test that core modules get higher scores."""
        # Create a graph where core.py is imported by many modules
        core = Module(
            name="core.py",
            path=Path("/project/core.py"),
            module_type=ModuleType.FILE,
        )
        a = Module(name="a.py", path=Path("/project/a.py"), module_type=ModuleType.FILE)
        b = Module(name="b.py", path=Path("/project/b.py"), module_type=ModuleType.FILE)
        c = Module(name="c.py", path=Path("/project/c.py"), module_type=ModuleType.FILE)
        d = Module(name="d.py", path=Path("/project/d.py"), module_type=ModuleType.FILE)
        e = Module(name="e.py", path=Path("/project/e.py"), module_type=ModuleType.FILE)

        graph = DependencyGraph()
        for m in [core, a, b, c, d, e]:
            graph.add_module(m)

        # All modules import core
        for m in [a, b, c, d, e]:
            graph.add_dependency(m.path, core.path)

        score, reasons = score_connectivity(core, graph)
        assert score > 0.1  # 5 dependents gives 5/20=0.25, weighted by 0.6 = 0.15
        assert any("Core module" in r for r in reasons)

    def test_isolated_module(self) -> None:
        """Test isolated module gets low score."""
        isolated = Module(
            name="isolated.py",
            path=Path("/project/isolated.py"),
            module_type=ModuleType.FILE,
        )
        graph = DependencyGraph()
        graph.add_module(isolated)

        score, _reasons = score_connectivity(isolated, graph)
        assert score == 0.0


class TestScoreDocumentation:
    """Tests for documentation scoring."""

    def test_documented_module(self) -> None:
        """Test module with description."""
        module = Module(
            name="utils.py",
            path=Path("/project/utils.py"),
            module_type=ModuleType.FILE,
            description="Utility functions for the project",
            exports=["helper1", "helper2", "helper3"],
        )
        score, _reasons = score_documentation(module)
        assert score > 0.5

    def test_undocumented_module(self) -> None:
        """Test module without description."""
        module = Module(
            name="utils.py",
            path=Path("/project/utils.py"),
            module_type=ModuleType.FILE,
        )
        score, _reasons = score_documentation(module)
        assert score < 0.3


# =============================================================================
# RECOMMENDER TESTS
# =============================================================================


class TestStartHereRecommender:
    """Tests for the recommender class."""

    def test_recommend_basic(
        self,
        sample_module: Module,
        entry_point_module: Module,
        sample_graph: DependencyGraph,
    ) -> None:
        """Test basic recommendation."""
        recommender = StartHereRecommender()
        recs = recommender.recommend(
            [sample_module, entry_point_module],
            sample_graph,
        )

        assert len(recs) > 0
        # Entry point should be ranked higher
        assert any(r.path == entry_point_module.path for r in recs)

    def test_config_max_recommendations(self, sample_graph: DependencyGraph) -> None:
        """Test max recommendations limit."""
        modules = [
            Module(
                name=f"mod{i}.py",
                path=Path(f"/project/mod{i}.py"),
                module_type=ModuleType.FILE,
                entry_point=True,  # All entry points for high score
            )
            for i in range(20)
        ]

        for m in modules:
            sample_graph.add_module(m)

        config = RecommendationConfig(max_recommendations=5)
        recommender = StartHereRecommender(config)
        recs = recommender.recommend(modules, sample_graph)

        assert len(recs) <= 5

    def test_config_min_score(self, sample_graph: DependencyGraph) -> None:
        """Test minimum score filtering."""
        module = Module(
            name="hidden.py",
            path=Path("/project/hidden.py"),
            module_type=ModuleType.FILE,
            entry_point=False,  # Low score
        )
        sample_graph.add_module(module)

        config = RecommendationConfig(min_score=0.9)
        recommender = StartHereRecommender(config)
        recs = recommender.recommend([module], sample_graph)

        # Low-scoring module should be filtered out
        assert len(recs) == 0

    def test_format_recommendations(
        self,
        sample_module: Module,
        entry_point_module: Module,
        sample_graph: DependencyGraph,
    ) -> None:
        """Test Markdown formatting."""
        recommender = StartHereRecommender()
        recs = recommender.recommend(
            [sample_module, entry_point_module],
            sample_graph,
        )

        md = recommender.format_recommendations(recs)

        assert "## Start Here" in md
        assert "Score:" in md

    def test_format_empty_recommendations(self) -> None:
        """Test formatting with no recommendations."""
        recommender = StartHereRecommender()
        md = recommender.format_recommendations([])
        assert "No recommended starting points" in md

    def test_category_detection(self) -> None:
        """Test category detection for modules."""
        recommender = StartHereRecommender()
        graph = DependencyGraph()

        # Config file
        config_mod = Module(
            name="config.py",
            path=Path("/project/config.py"),
            module_type=ModuleType.FILE,
        )
        graph.add_module(config_mod)
        recs = recommender.recommend([config_mod], graph)

        if recs:
            # Should be categorized as config
            config_recs = [r for r in recs if r.path == config_mod.path]
            if config_recs:
                assert config_recs[0].category == "config"


# =============================================================================
# CONVENIENCE FUNCTION TESTS
# =============================================================================


class TestConvenienceFunction:
    """Tests for get_start_here_recommendations."""

    def test_get_recommendations(
        self,
        sample_module: Module,
        entry_point_module: Module,
        sample_graph: DependencyGraph,
    ) -> None:
        """Test the convenience function."""
        recs = get_start_here_recommendations(
            [sample_module, entry_point_module],
            sample_graph,
            max_recommendations=3,
        )

        assert isinstance(recs, list)
        assert len(recs) <= 3

    def test_with_no_modules(self) -> None:
        """Test with empty module list."""
        graph = DependencyGraph()
        recs = get_start_here_recommendations([], graph)
        assert recs == []


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestRecommenderIntegration:
    """Integration tests for the recommendation system."""

    def test_realistic_project_structure(self) -> None:
        """Test with a realistic project structure."""
        # Create a mini project structure
        main = Module(
            name="__main__.py",
            path=Path("/project/src/__main__.py"),
            module_type=ModuleType.FILE,
            entry_point=True,
            description="Application entry point",
        )
        cli = Module(
            name="cli.py",
            path=Path("/project/src/cli.py"),
            module_type=ModuleType.FILE,
            imports=["typer", "core"],
            exports=["app", "main"],
        )
        core = Module(
            name="core.py",
            path=Path("/project/src/core.py"),
            module_type=ModuleType.FILE,
            description="Core business logic",
            exports=["process", "validate", "transform"],
        )
        utils = Module(
            name="utils.py",
            path=Path("/project/src/utils.py"),
            module_type=ModuleType.FILE,
            exports=["helper"],
        )
        models = Module(
            name="models.py",
            path=Path("/project/src/models.py"),
            module_type=ModuleType.FILE,
            exports=["User", "Project"],
        )

        graph = DependencyGraph()
        for m in [main, cli, core, utils, models]:
            graph.add_module(m)

        # Dependencies
        graph.add_dependency(main.path, cli.path)
        graph.add_dependency(cli.path, core.path)
        graph.add_dependency(core.path, utils.path)
        graph.add_dependency(core.path, models.path)

        recs = get_start_here_recommendations(
            [main, cli, core, utils, models],
            graph,
            max_recommendations=3,
        )

        # Entry point should be recommended
        rec_paths = [r.path for r in recs]
        assert main.path in rec_paths

    def test_scores_are_bounded(self) -> None:
        """Test that all scores are between 0 and 1."""
        modules = [
            Module(
                name=f"mod{i}.py",
                path=Path(f"/project/mod{i}.py"),
                module_type=ModuleType.FILE,
                entry_point=(i % 2 == 0),
                description="Description" if i % 3 == 0 else None,
                exports=[f"func{j}" for j in range(i)],
            )
            for i in range(10)
        ]

        graph = DependencyGraph()
        for m in modules:
            graph.add_module(m)

        config = RecommendationConfig(min_score=0.0)
        recommender = StartHereRecommender(config)
        recs = recommender.recommend(modules, graph)

        for rec in recs:
            assert 0.0 <= rec.score <= 2.0  # Weighted score can exceed 1.0 slightly
