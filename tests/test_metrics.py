"""Tests for code complexity metrics analyzer."""

from __future__ import annotations

from pathlib import Path

import pytest

from devwayfinder.analyzers.metrics import (
    AggregateMetrics,
    CyclomaticComplexityVisitor,
    FileMetrics,
    LOCMetrics,
    MetricsAnalyzer,
)

# =============================================================================
# LOCMetrics Tests
# =============================================================================


class TestLOCMetrics:
    """Tests for LOCMetrics dataclass."""

    def test_default_values(self) -> None:
        """Test default construction."""
        loc = LOCMetrics()
        assert loc.total == 0
        assert loc.code == 0
        assert loc.comments == 0
        assert loc.blank == 0
        assert loc.docstrings == 0

    def test_code_ratio(self) -> None:
        """Test code ratio calculation."""
        loc = LOCMetrics(total=100, code=80)
        assert loc.code_ratio == 0.8

    def test_code_ratio_zero_total(self) -> None:
        """Test code ratio with zero total lines."""
        loc = LOCMetrics(total=0, code=0)
        assert loc.code_ratio == 0.0

    def test_to_dict(self) -> None:
        """Test dictionary conversion."""
        loc = LOCMetrics(total=100, code=80, comments=10, blank=10)
        d = loc.to_dict()
        assert d["total"] == 100
        assert d["code"] == 80
        assert d["code_ratio"] == 0.8


# =============================================================================
# CyclomaticComplexityVisitor Tests
# =============================================================================


class TestCyclomaticComplexityVisitor:
    """Tests for cyclomatic complexity calculation."""

    def _get_complexity(self, code: str) -> int:
        """Helper to get complexity of code."""
        import ast

        tree = ast.parse(code)
        visitor = CyclomaticComplexityVisitor()
        visitor.visit(tree)
        return visitor.complexity

    def test_simple_function(self) -> None:
        """Test complexity of simple function."""
        code = """
def hello():
    print("Hello")
"""
        assert self._get_complexity(code) == 1

    def test_if_statement(self) -> None:
        """Test complexity with if statement."""
        code = """
def check(x):
    if x > 0:
        return True
    return False
"""
        assert self._get_complexity(code) == 2

    def test_if_elif_else(self) -> None:
        """Test complexity with if-elif-else."""
        code = """
def classify(x):
    if x > 0:
        return "positive"
    elif x < 0:
        return "negative"
    else:
        return "zero"
"""
        # 2 decision points: if and elif
        assert self._get_complexity(code) == 3

    def test_for_loop(self) -> None:
        """Test complexity with for loop."""
        code = """
def sum_list(items):
    total = 0
    for item in items:
        total += item
    return total
"""
        assert self._get_complexity(code) == 2

    def test_while_loop(self) -> None:
        """Test complexity with while loop."""
        code = """
def countdown(n):
    while n > 0:
        print(n)
        n -= 1
"""
        assert self._get_complexity(code) == 2

    def test_boolean_operators(self) -> None:
        """Test complexity with boolean operators."""
        code = """
def check(a, b, c):
    if a and b:
        return True
    if a or b or c:
        return True
    return False
"""
        # 2 ifs + 1 'and' + 2 'or's = 5 decision points
        assert self._get_complexity(code) == 6

    def test_try_except(self) -> None:
        """Test complexity with try-except."""
        code = """
def safe_divide(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return None
    except TypeError:
        return None
"""
        # 2 except handlers = 2 decision points
        assert self._get_complexity(code) == 3

    def test_list_comprehension(self) -> None:
        """Test complexity with list comprehension."""
        code = """
def filter_positive(items):
    return [x for x in items if x > 0]
"""
        # 1 generator + 1 if filter
        assert self._get_complexity(code) == 3

    def test_nested_comprehension(self) -> None:
        """Test complexity with nested comprehension."""
        code = """
def flatten(matrix):
    return [x for row in matrix for x in row]
"""
        # 2 generators
        assert self._get_complexity(code) == 3

    def test_ternary_operator(self) -> None:
        """Test complexity with ternary operator."""
        code = """
def abs_val(x):
    return x if x >= 0 else -x
"""
        assert self._get_complexity(code) == 2

    def test_with_statement(self) -> None:
        """Test complexity with context manager."""
        code = """
def read_file(path):
    with open(path) as f:
        return f.read()
"""
        assert self._get_complexity(code) == 2

    def test_multiple_with(self) -> None:
        """Test complexity with multiple context managers."""
        code = """
def copy_file(src, dst):
    with open(src) as f1, open(dst, 'w') as f2:
        f2.write(f1.read())
"""
        # 2 context managers
        assert self._get_complexity(code) == 3

    def test_complex_function(self) -> None:
        """Test complexity of a more complex function."""
        code = """
def process_data(items, threshold):
    results = []
    for item in items:
        if item is None:
            continue
        if item > threshold:
            if item % 2 == 0:
                results.append(item * 2)
            else:
                results.append(item)
        elif item == threshold:
            results.append(item)
    return results
"""
        # for + 4 ifs
        assert self._get_complexity(code) >= 5

    def test_function_metrics(self) -> None:
        """Test that function metrics are collected."""
        import ast

        code = """
def func1(a, b):
    if a > b:
        return a
    return b

def func2(x):
    return x * 2
"""
        tree = ast.parse(code)
        visitor = CyclomaticComplexityVisitor()
        visitor.visit(tree)

        metrics = visitor.function_metrics
        assert len(metrics) == 2
        assert metrics[0].name == "func1"
        assert metrics[0].parameters == 2
        assert metrics[1].name == "func2"
        assert metrics[1].parameters == 1


# =============================================================================
# MetricsAnalyzer Tests
# =============================================================================


class TestMetricsAnalyzer:
    """Tests for MetricsAnalyzer."""

    @pytest.fixture
    def analyzer(self) -> MetricsAnalyzer:
        """Create a metrics analyzer."""
        return MetricsAnalyzer()

    @pytest.fixture
    def sample_python_file(self, tmp_path: Path) -> Path:
        """Create a sample Python file."""
        content = '''"""Sample module."""

import os
from typing import List


def process(items: List[int]) -> int:
    """Process a list of items."""
    total = 0
    for item in items:
        if item > 0:
            total += item
    return total


class Calculator:
    """A simple calculator."""

    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    def divide(self, a: int, b: int) -> float:
        """Divide two numbers."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b


# A comment
if __name__ == "__main__":
    print(process([1, 2, 3]))
'''
        file_path = tmp_path / "sample.py"
        file_path.write_text(content)
        return file_path

    def test_analyze_python_file(self, analyzer: MetricsAnalyzer, sample_python_file: Path) -> None:
        """Test analyzing a Python file."""
        metrics = analyzer.analyze_file(sample_python_file)

        assert metrics.language == "python"
        assert metrics.loc.total > 0
        assert metrics.loc.code > 0
        assert metrics.loc.comments >= 1
        assert metrics.function_count >= 3  # process, add, divide
        assert metrics.class_count == 1
        assert metrics.cyclomatic_complexity > 1  # Has some complexity

    def test_loc_calculation(self, analyzer: MetricsAnalyzer, tmp_path: Path) -> None:
        """Test LOC calculation."""
        content = '''"""Module docstring."""

# A comment
def hello():
    pass

# Another comment
x = 1
'''
        file_path = tmp_path / "loc_test.py"
        file_path.write_text(content)

        metrics = analyzer.analyze_file(file_path)

        assert metrics.loc.total == 9
        assert metrics.loc.blank >= 2
        assert metrics.loc.comments >= 2
        assert metrics.loc.docstrings >= 1

    def test_maintainability_index(
        self, analyzer: MetricsAnalyzer, sample_python_file: Path
    ) -> None:
        """Test maintainability index calculation."""
        metrics = analyzer.analyze_file(sample_python_file)

        assert metrics.maintainability_index is not None
        assert 0 <= metrics.maintainability_index <= 100

    def test_max_complexity(self, analyzer: MetricsAnalyzer, tmp_path: Path) -> None:
        """Test max complexity tracking."""
        content = """
def simple():
    pass

def complex_func(a, b, c):
    if a:
        if b:
            if c:
                return True
    return False
"""
        file_path = tmp_path / "complex.py"
        file_path.write_text(content)

        metrics = analyzer.analyze_file(file_path)

        # Find the complex function
        complex_func = next((f for f in metrics.functions if f.name == "complex_func"), None)
        assert complex_func is not None
        assert complex_func.complexity > 1
        assert metrics.max_complexity == complex_func.complexity

    def test_nonexistent_file(self, analyzer: MetricsAnalyzer) -> None:
        """Test analyzing a missing file."""
        metrics = analyzer.analyze_file(Path("/nonexistent/file.py"))

        assert len(metrics.errors) > 0
        assert "Failed to read file" in metrics.errors[0]

    def test_syntax_error_fallback(self, analyzer: MetricsAnalyzer, tmp_path: Path) -> None:
        """Test fallback on syntax error."""
        content = """
def broken
    print("bad syntax")
"""
        file_path = tmp_path / "broken.py"
        file_path.write_text(content)

        metrics = analyzer.analyze_file(file_path)

        assert len(metrics.errors) > 0
        assert "Syntax error" in metrics.errors[0]
        # Should still calculate LOC and heuristic complexity
        assert metrics.loc.total > 0

    def test_heuristic_complexity(self, analyzer: MetricsAnalyzer, tmp_path: Path) -> None:
        """Test heuristic complexity for non-Python files."""
        content = """
function process(items) {
    let total = 0;
    for (let item of items) {
        if (item > 0) {
            total += item;
        }
    }
    return total;
}
"""
        file_path = tmp_path / "sample.js"
        file_path.write_text(content)

        metrics = analyzer.analyze_file(file_path, language="javascript")

        assert metrics.language == "javascript"
        assert metrics.cyclomatic_complexity > 1  # Has for and if

    def test_to_dict(self, analyzer: MetricsAnalyzer, sample_python_file: Path) -> None:
        """Test dictionary conversion."""
        metrics = analyzer.analyze_file(sample_python_file)
        d = metrics.to_dict()

        assert "path" in d
        assert "language" in d
        assert "loc" in d
        assert "cyclomatic_complexity" in d
        assert "functions" in d

    def test_analyze_directory(self, analyzer: MetricsAnalyzer, tmp_path: Path) -> None:
        """Test analyzing a directory."""
        # Create some files
        (tmp_path / "main.py").write_text("def main(): pass")
        (tmp_path / "utils.py").write_text("def helper(): return 42")
        (tmp_path / "readme.txt").write_text("Not analyzed")

        results = list(analyzer.analyze_directory(tmp_path))

        assert len(results) == 2  # Only .py files
        assert all(m.language == "python" for m in results)

    def test_analyze_directory_exclusions(self, analyzer: MetricsAnalyzer, tmp_path: Path) -> None:
        """Test directory analysis with exclusions."""
        (tmp_path / "main.py").write_text("def main(): pass")

        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        (pycache / "main.cpython-311.pyc").write_bytes(b"binary")

        results = list(analyzer.analyze_directory(tmp_path))

        # Should not include __pycache__ files
        assert len(results) == 1


# =============================================================================
# AggregateMetrics Tests
# =============================================================================


class TestAggregateMetrics:
    """Tests for AggregateMetrics."""

    def test_add_file(self) -> None:
        """Test adding file metrics."""
        agg = AggregateMetrics()

        metrics1 = FileMetrics(
            path=Path("file1.py"),
            language="python",
            loc=LOCMetrics(total=100, code=80),
            function_count=5,
            class_count=2,
            max_complexity=10,
        )
        metrics2 = FileMetrics(
            path=Path("file2.py"),
            language="python",
            loc=LOCMetrics(total=50, code=40),
            function_count=3,
            class_count=1,
            max_complexity=5,
        )

        agg.add_file(metrics1)
        agg.add_file(metrics2)

        assert agg.total_files == 2
        assert agg.total_loc.total == 150
        assert agg.total_loc.code == 120
        assert agg.total_functions == 8
        assert agg.total_classes == 3
        assert agg.max_complexity == 10
        assert agg.max_complexity_file == "file1.py"

    def test_finalize(self) -> None:
        """Test finalize calculations."""
        agg = AggregateMetrics()

        metrics1 = FileMetrics(
            path=Path("file1.py"),
            cyclomatic_complexity=10,
            maintainability_index=80.0,
        )
        metrics2 = FileMetrics(
            path=Path("file2.py"),
            cyclomatic_complexity=20,
            maintainability_index=60.0,
        )

        agg.add_file(metrics1)
        agg.add_file(metrics2)
        agg.finalize([metrics1, metrics2])

        assert agg.average_complexity == 15.0
        assert agg.average_maintainability == 70.0

    def test_to_dict(self) -> None:
        """Test dictionary conversion."""
        agg = AggregateMetrics()
        agg.total_files = 5
        agg.files_by_language = {"python": 3, "javascript": 2}

        d = agg.to_dict()

        assert d["total_files"] == 5
        assert d["files_by_language"]["python"] == 3


# =============================================================================
# Integration Tests
# =============================================================================


class TestMetricsIntegration:
    """Integration tests for metrics analyzer."""

    @pytest.fixture
    def complex_project(self, tmp_path: Path) -> Path:
        """Create a project with various files."""
        project = tmp_path / "project"
        project.mkdir()

        # Main module
        (project / "main.py").write_text('''
"""Main entry point."""

import sys
from utils import helper


def main(args):
    """Run the application."""
    if len(args) < 2:
        print("Usage: main.py <input>")
        return 1

    result = helper(args[1])
    print(f"Result: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
''')

        # Utils module
        (project / "utils.py").write_text('''
"""Utility functions."""

from typing import Any


def helper(value: str) -> str:
    """Process a value."""
    if not value:
        return ""
    return value.upper()


def process_list(items):
    """Process a list with multiple conditions."""
    results = []
    for item in items:
        if item is None:
            continue
        if isinstance(item, str) and item.strip():
            results.append(item.strip())
        elif isinstance(item, int) and item > 0:
            results.append(str(item))
    return results
''')

        return project

    def test_project_analysis(self, complex_project: Path) -> None:
        """Test analyzing a complete project."""
        analyzer = MetricsAnalyzer()

        all_metrics = list(analyzer.analyze_directory(complex_project))

        assert len(all_metrics) == 2

        # Check main.py
        main_metrics = next(m for m in all_metrics if "main" in str(m.path))
        assert main_metrics.function_count >= 1
        assert main_metrics.cyclomatic_complexity > 1

        # Check utils.py
        utils_metrics = next(m for m in all_metrics if "utils" in str(m.path))
        assert utils_metrics.function_count >= 2

    def test_aggregate_project_metrics(self, complex_project: Path) -> None:
        """Test aggregating project metrics."""
        analyzer = MetricsAnalyzer()

        all_metrics = list(analyzer.analyze_directory(complex_project))

        agg = AggregateMetrics()
        for m in all_metrics:
            agg.add_file(m)
        agg.finalize(all_metrics)

        assert agg.total_files == 2
        assert agg.total_loc.code > 0
        assert agg.total_functions >= 3
        assert agg.files_by_language.get("python") == 2
