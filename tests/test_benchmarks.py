"""Tests for benchmark fixture and runner modules."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from devwayfinder.benchmarks.fixtures import create_fixture
from devwayfinder.benchmarks.runner import format_markdown_report, run_benchmark_suite

if TYPE_CHECKING:
    from pathlib import Path


def test_create_small_fixture_generates_expected_files(tmp_path: Path) -> None:
    """Small fixture should contain expected module count and metadata."""
    fixture_path = create_fixture(tmp_path, "small")

    modules = list((fixture_path / "src").rglob("module_*.py"))
    assert len(modules) == 10
    assert (fixture_path / "fixture.json").exists()
    assert (fixture_path / "pyproject.toml").exists()


@pytest.mark.asyncio
async def test_run_benchmark_suite_analysis_only(tmp_path: Path) -> None:
    """Benchmark suite should produce metrics in analysis-only mode."""
    results = await run_benchmark_suite(
        fixture_root=tmp_path,
        sizes=["small"],
        include_generation=False,
    )

    assert len(results) == 1
    result = results[0]
    assert result.size == "small"
    assert result.modules_detected >= 10
    assert result.analysis_seconds > 0
    assert result.generation_seconds == 0.0


def test_format_markdown_report_contains_table(tmp_path: Path) -> None:
    """Markdown report should include benchmark table rows for each result."""
    fixture_path = create_fixture(tmp_path, "small")

    from devwayfinder.benchmarks.runner import BenchmarkResult

    report = format_markdown_report(
        [
            BenchmarkResult(
                size="small",
                fixture_path=str(fixture_path),
                modules_detected=10,
                dependencies_detected=9,
                analysis_seconds=0.12,
                generation_seconds=0.45,
                total_seconds=0.57,
                peak_memory_mb=3.4,
                llm_calls=0,
                generated_sections=5,
                measured_at_utc="2026-04-01T00:00:00+00:00",
            )
        ]
    )

    assert "| Size | Modules |" in report
    assert "| small | 10 | 9 |" in report
