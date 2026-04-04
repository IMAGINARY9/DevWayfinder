"""Code complexity metrics analyzer.

Provides metrics calculation including:
- Lines of Code (LOC): total, code, comments, blank
- Cyclomatic Complexity: Python AST-based
- Function/Class counts
"""

from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path  # noqa: TC003 - needed at runtime for dataclasses
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


@dataclass
class LOCMetrics:
    """Lines of code metrics."""

    total: int = 0
    code: int = 0
    comments: int = 0
    blank: int = 0
    docstrings: int = 0

    @property
    def code_ratio(self) -> float:
        """Ratio of code to total lines."""
        return self.code / self.total if self.total > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total": self.total,
            "code": self.code,
            "comments": self.comments,
            "blank": self.blank,
            "docstrings": self.docstrings,
            "code_ratio": round(self.code_ratio, 3),
        }


@dataclass
class FunctionMetrics:
    """Metrics for a single function."""

    name: str
    lineno: int
    complexity: int
    parameters: int
    is_method: bool = False
    class_name: str | None = None


@dataclass
class ClassMetrics:
    """Metrics for a single class."""

    name: str
    lineno: int
    method_count: int
    complexity: int  # Sum of method complexities


@dataclass
class FileMetrics:
    """Complete metrics for a file."""

    path: Path
    language: str | None = None
    loc: LOCMetrics = field(default_factory=LOCMetrics)
    cyclomatic_complexity: float = 1.0
    max_complexity: int = 0
    function_count: int = 0
    class_count: int = 0
    functions: list[FunctionMetrics] = field(default_factory=list)
    classes: list[ClassMetrics] = field(default_factory=list)
    halstead_volume: float | None = None
    maintainability_index: float | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def average_complexity(self) -> float:
        """Average complexity per function."""
        if not self.function_count:
            return self.cyclomatic_complexity
        return self.cyclomatic_complexity / self.function_count

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "path": str(self.path),
            "language": self.language,
            "loc": self.loc.to_dict(),
            "cyclomatic_complexity": round(self.cyclomatic_complexity, 2),
            "max_complexity": self.max_complexity,
            "average_complexity": round(self.average_complexity, 2),
            "function_count": self.function_count,
            "class_count": self.class_count,
            "maintainability_index": (
                round(self.maintainability_index, 2)
                if self.maintainability_index is not None
                else None
            ),
            "functions": [
                {
                    "name": f.name,
                    "lineno": f.lineno,
                    "complexity": f.complexity,
                    "parameters": f.parameters,
                }
                for f in self.functions
            ],
        }


class CyclomaticComplexityVisitor(ast.NodeVisitor):
    """AST visitor to calculate cyclomatic complexity.

    Cyclomatic complexity = E - N + 2P
    Where E = edges, N = nodes, P = connected components

    Simplified: Count decision points + 1
    Decision points: if, elif, for, while, except, with, assert,
                     comprehensions, boolean operators (and, or)
    """

    def __init__(self) -> None:
        """Initialize visitor."""
        self.complexity = 1  # Base complexity
        self._function_complexities: list[tuple[str, int, int, int, bool, str | None]] = []
        self._class_complexities: list[tuple[str, int, int]] = []
        self._current_class: str | None = None
        self._base_complexity = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition."""
        self._visit_function(node, is_method=self._current_class is not None)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition."""
        self._visit_function(node, is_method=self._current_class is not None)

    def _visit_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, *, is_method: bool
    ) -> None:
        """Common function visiting logic."""
        old_base = self._base_complexity
        func_start_complexity = self.complexity

        # Visit function body
        self.generic_visit(node)

        func_complexity = self.complexity - func_start_complexity + 1
        param_count = len(node.args.args)

        # Exclude 'self' from parameter count for methods
        if is_method and param_count > 0:
            param_count -= 1

        self._function_complexities.append(
            (
                node.name,
                node.lineno,
                func_complexity,
                param_count,
                is_method,
                self._current_class,
            )
        )
        self._base_complexity = old_base

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition."""
        old_class = self._current_class
        self._current_class = node.name

        self.generic_visit(node)

        method_count = sum(
            1 for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        )

        self._class_complexities.append((node.name, node.lineno, method_count))
        self._current_class = old_class

    # Decision point visitors - each adds 1 to complexity

    def visit_If(self, node: ast.If) -> None:
        """If statement."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        """For loop."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        """Async for loop."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        """While loop."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        """Exception handler."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        """With statement (context manager)."""
        # Each context manager is a potential decision point
        self.complexity += len(node.items)
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        """Async with statement."""
        self.complexity += len(node.items)
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        """Assert statement."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        """Boolean operations (and, or)."""
        # Each additional operand adds a branch
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        """Ternary if expression."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        """List comprehension."""
        self.complexity += len(node.generators)
        for gen in node.generators:
            self.complexity += len(gen.ifs)
        self.generic_visit(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        """Set comprehension."""
        self.complexity += len(node.generators)
        for gen in node.generators:
            self.complexity += len(gen.ifs)
        self.generic_visit(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        """Dict comprehension."""
        self.complexity += len(node.generators)
        for gen in node.generators:
            self.complexity += len(gen.ifs)
        self.generic_visit(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        """Generator expression."""
        self.complexity += len(node.generators)
        for gen in node.generators:
            self.complexity += len(gen.ifs)
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        """Match statement (Python 3.10+)."""
        # Each case is a decision point
        self.complexity += len(node.cases) - 1  # -1 because first case is "free"
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        """Try statement - handlers counted separately."""
        # else branch is a decision point
        if node.orelse:
            self.complexity += 1
        # finally is not a decision point, always runs
        self.generic_visit(node)

    @property
    def function_metrics(self) -> list[FunctionMetrics]:
        """Get function metrics."""
        return [
            FunctionMetrics(
                name=name,
                lineno=lineno,
                complexity=complexity,
                parameters=params,
                is_method=is_method,
                class_name=class_name,
            )
            for name, lineno, complexity, params, is_method, class_name in self._function_complexities
        ]

    @property
    def class_metrics(self) -> list[ClassMetrics]:
        """Get class metrics."""
        methods = self.function_metrics

        # Match classes with their method complexities
        result = []
        for name, lineno, method_count in self._class_complexities:
            # Sum complexity of methods that belong to this class
            class_complexity = sum(
                f.complexity for f in methods if f.is_method and f.class_name == name
            )
            result.append(
                ClassMetrics(
                    name=name,
                    lineno=lineno,
                    method_count=method_count,
                    complexity=max(class_complexity, 1),
                )
            )
        return result


class MetricsAnalyzer:
    """Analyzer for code complexity metrics.

    Supports:
    - Python: Full AST-based analysis
    - Other languages: Line-based heuristics
    """

    # Comment patterns per language
    COMMENT_PATTERNS: ClassVar[dict[str, tuple[str, str | None, str | None]]] = {
        # Language: (line_comment, block_start, block_end)
        "python": ("#", '"""', '"""'),
        "javascript": ("//", "/*", "*/"),
        "typescript": ("//", "/*", "*/"),
        "java": ("//", "/*", "*/"),
        "c": ("//", "/*", "*/"),
        "cpp": ("//", "/*", "*/"),
        "csharp": ("//", "/*", "*/"),
        "go": ("//", "/*", "*/"),
        "rust": ("//", "/*", "*/"),
        "ruby": ("#", "=begin", "=end"),
        "php": ("//", "/*", "*/"),
        "shell": ("#", None, None),
    }

    def __init__(self, cache_manager: Any | None = None) -> None:
        """Initialize analyzer.

        Args:
            cache_manager: Optional CacheManager for caching metrics
        """
        self.cache_manager = cache_manager

    def analyze_file(self, file_path: Path, language: str | None = None) -> FileMetrics:
        """Analyze a single file.

        Args:
            file_path: Path to the file
            language: Override language detection

        Returns:
            FileMetrics with calculated metrics
        """
        # Check cache first
        if self.cache_manager:
            cached = self.cache_manager.get_metrics(file_path)
            if cached:
                return self._metrics_from_dict(cached, file_path)

        metrics = FileMetrics(path=file_path, language=language)

        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            metrics.errors.append(f"Failed to read file: {e}")
            return metrics

        # Detect language if not provided
        if not language:
            language = self._detect_language(file_path)
            metrics.language = language

        # Calculate LOC
        metrics.loc = self._calculate_loc(content, language)

        # Python: Use AST for accurate metrics
        if language == "python":
            try:
                self._analyze_python(content, metrics)
            except SyntaxError as e:
                metrics.errors.append(f"Syntax error: {e}")
                # Fall back to heuristic
                metrics.cyclomatic_complexity = self._estimate_complexity_heuristic(content)
        else:
            # Other languages: Use heuristic
            metrics.cyclomatic_complexity = self._estimate_complexity_heuristic(content)

        # Calculate maintainability index
        metrics.maintainability_index = self._calculate_maintainability_index(metrics)

        # Cache the result
        if self.cache_manager:
            self.cache_manager.set_metrics(file_path, metrics.to_dict())

        return metrics

    def _detect_language(self, file_path: Path) -> str | None:
        """Detect language from file extension."""
        ext_to_lang = {
            ".py": "python",
            ".pyi": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
            ".c": "c",
            ".h": "c",
            ".cpp": "cpp",
            ".cxx": "cpp",
            ".cc": "cpp",
            ".hpp": "cpp",
            ".cs": "csharp",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".sh": "shell",
            ".bash": "shell",
        }
        return ext_to_lang.get(file_path.suffix.lower())

    def _calculate_loc(self, content: str, language: str | None) -> LOCMetrics:
        """Calculate lines of code metrics."""
        lines = content.split("\n")
        loc = LOCMetrics(total=len(lines))

        comment_info = self.COMMENT_PATTERNS.get(language or "", ("#", None, None))
        line_comment, block_start, block_end = comment_info

        in_block_comment = False
        in_docstring = False

        for line in lines:
            stripped = line.strip()

            # Handle blank lines
            if not stripped:
                loc.blank += 1
                continue

            # Handle Python docstrings
            if language == "python" and block_start and block_end:
                docstring_marker = (
                    '"""' if '"""' in stripped else "'''" if "'''" in stripped else None
                )
                if docstring_marker:
                    # Count occurrences
                    count = stripped.count(docstring_marker)
                    if count == 2:  # Single-line docstring
                        loc.docstrings += 1
                        continue
                    elif count == 1:  # Start or end of multi-line
                        in_docstring = not in_docstring
                        loc.docstrings += 1
                        continue

                if in_docstring:
                    loc.docstrings += 1
                    continue

            # Handle block comments
            if block_start and block_end and not in_docstring:
                if block_start in stripped:
                    in_block_comment = True
                    if block_end in stripped[stripped.index(block_start) + len(block_start) :]:
                        in_block_comment = False
                    loc.comments += 1
                    continue
                elif in_block_comment:
                    if block_end in stripped:
                        in_block_comment = False
                    loc.comments += 1
                    continue

            # Handle line comments
            if line_comment and stripped.startswith(line_comment):
                loc.comments += 1
                continue

            # It's code
            loc.code += 1

        return loc

    def _analyze_python(self, content: str, metrics: FileMetrics) -> None:
        """Analyze Python code using AST."""
        tree = ast.parse(content)

        # Calculate cyclomatic complexity
        visitor = CyclomaticComplexityVisitor()
        visitor.visit(tree)

        metrics.cyclomatic_complexity = visitor.complexity
        metrics.functions = visitor.function_metrics
        metrics.classes = visitor.class_metrics
        metrics.function_count = len(metrics.functions)
        metrics.class_count = len(metrics.classes)

        if metrics.functions:
            metrics.max_complexity = max(f.complexity for f in metrics.functions)

    def _estimate_complexity_heuristic(self, content: str) -> float:
        """Estimate complexity using keyword heuristics.

        This is a rough estimate for non-Python languages.
        """
        complexity = 1.0

        # Decision point keywords (common across many languages)
        decision_keywords = [
            r"\bif\b",
            r"\belse\b",
            r"\belif\b",
            r"\belse if\b",
            r"\bfor\b",
            r"\bwhile\b",
            r"\bdo\b",
            r"\bswitch\b",
            r"\bcase\b",
            r"\bmatch\b",
            r"\bcatch\b",
            r"\bexcept\b",
            r"\b\?\b",  # ternary operator
            r"\band\b",
            r"\bor\b",
            r"\|\|",
            r"&&",
        ]

        for pattern in decision_keywords:
            complexity += len(re.findall(pattern, content, re.IGNORECASE))

        return complexity

    def _calculate_maintainability_index(self, metrics: FileMetrics) -> float:
        """Calculate Maintainability Index (0-100 scale).

        MI = 171 - 5.2 * ln(HV) - 0.23 * CC - 16.2 * ln(LOC)

        Where:
        - HV = Halstead Volume (estimated)
        - CC = Cyclomatic Complexity
        - LOC = Lines of Code

        Since we don't calculate full Halstead metrics, we use
        a simplified formula.
        """
        import math

        loc = max(metrics.loc.code, 1)
        cc = max(metrics.cyclomatic_complexity, 1)

        # Simplified MI without Halstead Volume
        # MI = 171 - 0.23 * CC - 16.2 * ln(LOC)
        mi = 171 - 0.23 * cc - 16.2 * math.log(loc)

        # Normalize to 0-100 scale
        mi = max(0, min(100, mi * 100 / 171))

        return mi

    def _metrics_from_dict(self, data: dict[str, Any], path: Path) -> FileMetrics:
        """Reconstruct FileMetrics from cached dictionary."""
        loc_data = data.get("loc", {})
        loc = LOCMetrics(
            total=loc_data.get("total", 0),
            code=loc_data.get("code", 0),
            comments=loc_data.get("comments", 0),
            blank=loc_data.get("blank", 0),
            docstrings=loc_data.get("docstrings", 0),
        )

        functions = [
            FunctionMetrics(
                name=f["name"],
                lineno=f["lineno"],
                complexity=f["complexity"],
                parameters=f.get("parameters", 0),
            )
            for f in data.get("functions", [])
        ]

        return FileMetrics(
            path=path,
            language=data.get("language"),
            loc=loc,
            cyclomatic_complexity=data.get("cyclomatic_complexity", 1),
            max_complexity=data.get("max_complexity", 0),
            function_count=data.get("function_count", 0),
            class_count=data.get("class_count", 0),
            functions=functions,
            maintainability_index=data.get("maintainability_index"),
        )

    def analyze_directory(
        self,
        directory: Path,
        *,
        recursive: bool = True,
        exclude_patterns: list[str] | None = None,
    ) -> Iterator[FileMetrics]:
        """Analyze all files in a directory.

        Args:
            directory: Directory to analyze
            recursive: Whether to recurse into subdirectories
            exclude_patterns: Glob patterns to exclude

        Yields:
            FileMetrics for each analyzed file
        """
        exclude_patterns = exclude_patterns or [
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "node_modules",
            "*.egg-info",
            "dist",
            "build",
        ]

        def should_exclude(path: Path) -> bool:
            return any(path.match(pattern) or pattern in str(path) for pattern in exclude_patterns)

        pattern = "**/*" if recursive else "*"

        for file_path in directory.glob(pattern):
            if not file_path.is_file():
                continue
            if should_exclude(file_path):
                continue

            # Only analyze known source files
            language = self._detect_language(file_path)
            if language:
                yield self.analyze_file(file_path, language)


@dataclass
class AggregateMetrics:
    """Aggregated metrics for a project or directory."""

    total_files: int = 0
    total_loc: LOCMetrics = field(default_factory=LOCMetrics)
    average_complexity: float = 0.0
    max_complexity: int = 0
    max_complexity_file: str | None = None
    total_functions: int = 0
    total_classes: int = 0
    average_maintainability: float = 0.0
    files_by_language: dict[str, int] = field(default_factory=dict)

    def add_file(self, metrics: FileMetrics) -> None:
        """Add file metrics to aggregate."""
        self.total_files += 1
        self.total_loc.total += metrics.loc.total
        self.total_loc.code += metrics.loc.code
        self.total_loc.comments += metrics.loc.comments
        self.total_loc.blank += metrics.loc.blank
        self.total_loc.docstrings += metrics.loc.docstrings

        self.total_functions += metrics.function_count
        self.total_classes += metrics.class_count

        if metrics.max_complexity > self.max_complexity:
            self.max_complexity = metrics.max_complexity
            self.max_complexity_file = str(metrics.path)

        if metrics.language:
            self.files_by_language[metrics.language] = (
                self.files_by_language.get(metrics.language, 0) + 1
            )

    def finalize(self, all_metrics: list[FileMetrics]) -> None:
        """Calculate final aggregate values."""
        if not all_metrics:
            return

        total_complexity = sum(m.cyclomatic_complexity for m in all_metrics)
        self.average_complexity = total_complexity / len(all_metrics)

        mi_values = [m.maintainability_index for m in all_metrics if m.maintainability_index]
        if mi_values:
            self.average_maintainability = sum(mi_values) / len(mi_values)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_files": self.total_files,
            "total_loc": self.total_loc.to_dict(),
            "average_complexity": round(self.average_complexity, 2),
            "max_complexity": self.max_complexity,
            "max_complexity_file": self.max_complexity_file,
            "total_functions": self.total_functions,
            "total_classes": self.total_classes,
            "average_maintainability": round(self.average_maintainability, 2),
            "files_by_language": self.files_by_language,
        }
