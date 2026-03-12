"""
Start Here recommendation algorithm.

Identifies the best starting files for developers onboarding to a project
by analyzing entry points, change frequency, connectivity, and complexity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from devwayfinder.analyzers.git_analyzer import FileGitInfo, RepoGitInfo
    from devwayfinder.analyzers.metrics import AggregateMetrics, FileMetrics
    from devwayfinder.core.graph import DependencyGraph
    from devwayfinder.core.models import Module


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class StartingPoint:
    """A recommended starting point for onboarding."""

    path: Path
    score: float
    reasons: list[str] = field(default_factory=list)
    category: str = "general"  # entry_point, high_traffic, core, config

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "path": str(self.path),
            "score": round(self.score, 2),
            "reasons": self.reasons,
            "category": self.category,
        }


@dataclass
class RecommendationConfig:
    """Configuration for the recommendation algorithm."""

    # Weight factors for scoring (sum should be ~1.0)
    entry_point_weight: float = 0.30
    connectivity_weight: float = 0.25
    change_frequency_weight: float = 0.20
    complexity_weight: float = 0.15
    documentation_weight: float = 0.10

    # Thresholds
    min_score: float = 0.3
    max_recommendations: int = 10

    # Entry point bonuses
    main_entry_bonus: float = 1.0
    cli_entry_bonus: float = 0.8
    test_entry_bonus: float = 0.5

    # Category bonuses
    readme_bonus: float = 0.6
    config_bonus: float = 0.4


# =============================================================================
# SCORING FUNCTIONS
# =============================================================================


def score_entry_point(
    module: Module,
    *,
    main_bonus: float = 1.0,
    cli_bonus: float = 0.8,
) -> tuple[float, list[str]]:
    """
    Score a module based on entry point characteristics.

    Args:
        module: Module to score
        main_bonus: Bonus for main entry points
        cli_bonus: Bonus for CLI entry points

    Returns:
        Score and reasons
    """
    score = 0.0
    reasons: list[str] = []

    if module.entry_point:
        score += main_bonus
        reasons.append("Main entry point (has `if __name__ == '__main__'` or equivalent)")

    # Check for CLI indicators
    path_str = str(module.path).lower()
    if any(x in path_str for x in ["cli", "main", "__main__", "app"]):
        score += cli_bonus * 0.5
        reasons.append("CLI/application entry")

    return min(score, 1.0), reasons


def score_connectivity(
    module: Module,
    graph: DependencyGraph,
) -> tuple[float, list[str]]:
    """
    Score a module based on its connectivity in the dependency graph.

    High in-degree = many modules depend on it (core module)
    High out-degree = imports many modules (integration point)

    Args:
        module: Module to score
        graph: Dependency graph

    Returns:
        Score and reasons
    """
    reasons: list[str] = []

    # Get degrees
    in_degree = graph.get_dependents(module.path)
    out_degree = graph.get_dependencies(module.path)

    in_count = len(in_degree) if in_degree else 0
    out_count = len(out_degree) if out_degree else 0

    # Normalize (assume max ~20 dependencies is high)
    max_deps = 20
    in_score = min(in_count / max_deps, 1.0)
    out_score = min(out_count / max_deps, 1.0)

    # Core modules (high in-degree) are more valuable starting points
    score = in_score * 0.6 + out_score * 0.4

    if in_count >= 5:
        reasons.append(f"Core module ({in_count} dependents)")
    if out_count >= 5:
        reasons.append(f"Integration point ({out_count} imports)")

    return score, reasons


def score_change_frequency(
    module_path: Path,
    git_info: RepoGitInfo | None,
) -> tuple[float, list[str]]:
    """
    Score based on how frequently the file is changed.

    Higher frequency = more actively developed = worth understanding.

    Args:
        module_path: Path to the module
        git_info: Repository git information

    Returns:
        Score and reasons
    """
    if not git_info or not git_info.is_git_repo:
        return 0.0, []

    reasons: list[str] = []

    # Find file info
    path_str = str(module_path)
    file_info: FileGitInfo | None = None

    for fpath, info in git_info.files.items():
        if fpath.endswith(path_str) or path_str.endswith(fpath):
            file_info = info
            break

    if not file_info:
        return 0.0, []

    # Score based on commit count relative to repo average
    if git_info.total_commits and file_info.commit_count:
        avg_commits_per_file = git_info.total_commits / max(len(git_info.files), 1)
        ratio = file_info.commit_count / max(avg_commits_per_file, 1)

        score = min(ratio / 3.0, 1.0)  # Normalize, 3x average = perfect score

        if ratio >= 2.0:
            reasons.append(f"Actively developed ({file_info.commit_count} commits)")

        return score, reasons

    return 0.0, []


def score_complexity(
    module_path: Path,
    metrics: AggregateMetrics | dict[Path, FileMetrics] | None,
) -> tuple[float, list[str]]:
    """
    Score based on code complexity.

    Lower complexity = easier to understand = better starting point.

    Args:
        module_path: Path to the module
        metrics: Aggregate metrics or file metrics dict

    Returns:
        Score and reasons
    """
    if not metrics:
        return 0.5, []  # Neutral score if no metrics

    reasons: list[str] = []

    # Get file metrics
    file_metrics: FileMetrics | None = None

    if isinstance(metrics, dict):
        file_metrics = metrics.get(module_path)
    elif hasattr(metrics, "file_metrics"):
        file_metrics = metrics.file_metrics.get(module_path)

    if not file_metrics:
        return 0.5, []

    # Lower complexity is better (inverse scoring)
    # Maintainability Index: higher is better (0-100 scale typically)
    if file_metrics.maintainability_index is not None:
        mi = file_metrics.maintainability_index
        score = min(mi / 100.0, 1.0)
        if mi >= 70:
            reasons.append(f"High maintainability (MI: {mi:.0f})")
        return score, reasons

    # Fallback to cyclomatic complexity
    if file_metrics.cyclomatic_complexity:
        avg_cc = file_metrics.average_complexity or 5.0
        # CC 1-5 = simple, 6-10 = moderate, 11+ = complex
        if avg_cc <= 5:
            score = 1.0
            reasons.append("Simple code structure")
        elif avg_cc <= 10:
            score = 0.7
        else:
            score = 0.4
            reasons.append("Complex code structure")
        return score, reasons

    return 0.5, []


def score_documentation(module: Module) -> tuple[float, list[str]]:
    """
    Score based on presence of documentation.

    Args:
        module: Module to score

    Returns:
        Score and reasons
    """
    reasons: list[str] = []
    score = 0.0

    if module.description:
        score += 0.6
        reasons.append("Has module description")

    # Check if has exports
    if module.exports:
        score += 0.2
        if len(module.exports) >= 3:
            reasons.append(f"Well-structured ({len(module.exports)} exports)")

    # Check for imports indicating integration
    if module.imports:
        score += 0.1

    return min(score, 1.0), reasons


# =============================================================================
# RECOMMENDATION ENGINE
# =============================================================================


class StartHereRecommender:
    """
    Recommends starting points for project onboarding.

    Combines multiple signals to identify the best files
    for developers to start reading when onboarding.
    """

    def __init__(self, config: RecommendationConfig | None = None) -> None:
        """
        Initialize recommender.

        Args:
            config: Recommendation configuration
        """
        self.config = config or RecommendationConfig()

    def recommend(
        self,
        modules: list[Module],
        graph: DependencyGraph,
        git_info: RepoGitInfo | None = None,
        metrics: AggregateMetrics | dict[Path, FileMetrics] | None = None,
    ) -> list[StartingPoint]:
        """
        Generate starting point recommendations.

        Args:
            modules: List of modules in the project
            graph: Dependency graph
            git_info: Git repository information
            metrics: Code complexity metrics

        Returns:
            Ordered list of starting points
        """
        recommendations: list[StartingPoint] = []

        for module in modules:
            point = self._score_module(module, graph, git_info, metrics)
            if point.score >= self.config.min_score:
                recommendations.append(point)

        # Sort by score descending
        recommendations.sort(key=lambda x: x.score, reverse=True)

        # Limit to max recommendations
        return recommendations[: self.config.max_recommendations]

    def _score_module(
        self,
        module: Module,
        graph: DependencyGraph,
        git_info: RepoGitInfo | None,
        metrics: AggregateMetrics | dict[Path, FileMetrics] | None,
    ) -> StartingPoint:
        """
        Calculate score for a single module.

        Args:
            module: Module to score
            graph: Dependency graph
            git_info: Git information
            metrics: Complexity metrics

        Returns:
            StartingPoint with calculated score
        """
        all_reasons: list[str] = []
        weighted_score = 0.0

        # Entry point scoring
        entry_score, entry_reasons = score_entry_point(
            module,
            main_bonus=self.config.main_entry_bonus,
            cli_bonus=self.config.cli_entry_bonus,
        )
        weighted_score += entry_score * self.config.entry_point_weight
        all_reasons.extend(entry_reasons)

        # Connectivity scoring
        conn_score, conn_reasons = score_connectivity(module, graph)
        weighted_score += conn_score * self.config.connectivity_weight
        all_reasons.extend(conn_reasons)

        # Change frequency scoring
        change_score, change_reasons = score_change_frequency(module.path, git_info)
        weighted_score += change_score * self.config.change_frequency_weight
        all_reasons.extend(change_reasons)

        # Complexity scoring
        complexity_score, complexity_reasons = score_complexity(module.path, metrics)
        weighted_score += complexity_score * self.config.complexity_weight
        all_reasons.extend(complexity_reasons)

        # Documentation scoring
        doc_score, doc_reasons = score_documentation(module)
        weighted_score += doc_score * self.config.documentation_weight
        all_reasons.extend(doc_reasons)

        # Determine category
        category = self._determine_category(module, entry_score, conn_score)

        return StartingPoint(
            path=module.path,
            score=weighted_score,
            reasons=all_reasons,
            category=category,
        )

    def _determine_category(
        self,
        module: Module,
        entry_score: float,
        conn_score: float,
    ) -> str:
        """Determine the category of a starting point."""
        path_lower = str(module.path).lower()

        if module.entry_point or entry_score > 0.5:
            return "entry_point"

        if "config" in path_lower or "settings" in path_lower:
            return "config"

        if conn_score > 0.5:
            return "core"

        if "test" in path_lower:
            return "test"

        return "general"

    def format_recommendations(
        self,
        recommendations: list[StartingPoint],
        include_reasons: bool = True,
    ) -> str:
        """
        Format recommendations as Markdown.

        Args:
            recommendations: List of starting points
            include_reasons: Whether to include reason details

        Returns:
            Markdown string
        """
        if not recommendations:
            return "No recommended starting points found."

        lines = ["## Start Here", ""]
        lines.append("The following files are recommended for getting started:\n")

        for i, point in enumerate(recommendations, 1):
            path_str = str(point.path.name)
            lines.append(f"### {i}. `{path_str}`")
            lines.append(f"**Score:** {point.score:.2f} | **Category:** {point.category}")

            if include_reasons and point.reasons:
                lines.append("")
                for reason in point.reasons:
                    lines.append(f"- {reason}")

            lines.append("")

        return "\n".join(lines)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def get_start_here_recommendations(
    modules: list[Module],
    graph: DependencyGraph,
    git_info: RepoGitInfo | None = None,
    metrics: AggregateMetrics | dict[Path, FileMetrics] | None = None,
    max_recommendations: int = 5,
) -> list[StartingPoint]:
    """
    Get starting point recommendations for a project.

    Args:
        modules: List of project modules
        graph: Dependency graph
        git_info: Git repository information (optional)
        metrics: Code complexity metrics (optional)
        max_recommendations: Maximum recommendations to return

    Returns:
        List of recommended starting points
    """
    config = RecommendationConfig(max_recommendations=max_recommendations)
    recommender = StartHereRecommender(config)
    return recommender.recommend(modules, graph, git_info, metrics)
