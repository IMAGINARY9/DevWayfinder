"""Analyzers module for DevWayfinder.

This module provides code analysis capabilities:
- BaseAnalyzer: Abstract base class for all analyzers
- AnalyzerRegistry: Registry for language-specific analyzers
- StructureAnalyzer: Project structure and build system detection
- RegexAnalyzer: Language-agnostic import/export extraction
- PythonASTAnalyzer: Python-specific analysis using AST
- GraphBuilder: Builds dependency graphs from analysis results
- MetricsAnalyzer: Code complexity metrics (LOC, cyclomatic complexity)
- GitAnalyzer: Git history analysis (contributors, change frequency)
- StartHereRecommender: "Start Here" recommendation algorithm
"""

from devwayfinder.analyzers.base import (
    EXTENSION_TO_LANGUAGE,
    LANGUAGE_TO_EXTENSIONS,
    AnalyzerRegistry,
    BaseAnalyzer,
)
from devwayfinder.analyzers.git_analyzer import (
    ContributorInfo,
    FileGitInfo,
    GitAnalyzer,
    RepoGitInfo,
    is_git_available,
)
from devwayfinder.analyzers.graph_builder import (
    GraphBuilder,
    ImportResolver,
    build_dependency_graph,
)
from devwayfinder.analyzers.metrics import (
    AggregateMetrics,
    FileMetrics,
    FunctionMetrics,
    LOCMetrics,
    MetricsAnalyzer,
)
from devwayfinder.analyzers.python_analyzer import (
    ClassInfo,
    FunctionInfo,
    PythonASTAnalyzer,
    PythonExtractionResult,
    analyze_python,
    get_python_imports,
)
from devwayfinder.analyzers.regex_extractor import (
    ExtractionResult,
    RegexAnalyzer,
    analyze_with_regex,
)
from devwayfinder.analyzers.start_here import (
    RecommendationConfig,
    StartHereRecommender,
    StartingPoint,
    get_start_here_recommendations,
)
from devwayfinder.analyzers.structure import (
    DEFAULT_EXCLUDES,
    StructureAnalyzer,
    StructureInfo,
    analyze_structure,
)

__all__ = [
    "DEFAULT_EXCLUDES",
    "EXTENSION_TO_LANGUAGE",
    "LANGUAGE_TO_EXTENSIONS",
    "AggregateMetrics",
    "AnalyzerRegistry",
    "BaseAnalyzer",
    "ClassInfo",
    "ContributorInfo",
    "ExtractionResult",
    "FileGitInfo",
    "FileMetrics",
    "FunctionInfo",
    "FunctionMetrics",
    "GitAnalyzer",
    "GraphBuilder",
    "ImportResolver",
    "LOCMetrics",
    "MetricsAnalyzer",
    "PythonASTAnalyzer",
    "PythonExtractionResult",
    "RecommendationConfig",
    "RegexAnalyzer",
    "RepoGitInfo",
    "StartHereRecommender",
    "StartingPoint",
    "StructureAnalyzer",
    "StructureInfo",
    "analyze_python",
    "analyze_structure",
    "analyze_with_regex",
    "build_dependency_graph",
    "get_python_imports",
    "get_start_here_recommendations",
    "is_git_available",
]
