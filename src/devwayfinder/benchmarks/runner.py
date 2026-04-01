"""Benchmark runner for DevWayfinder analysis and generation pipelines."""

from __future__ import annotations

import asyncio
import json
import time
import tracemalloc
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from devwayfinder.analyzers import GraphBuilder
from devwayfinder.benchmarks.fixtures import FixtureSize, create_fixtures
from devwayfinder.generators import GenerationConfig, GuideGenerator
from devwayfinder.providers import HeuristicProvider

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class BenchmarkResult:
    """Measured benchmark output for one fixture size."""

    size: FixtureSize
    fixture_path: str
    modules_detected: int
    dependencies_detected: int
    analysis_seconds: float
    generation_seconds: float
    total_seconds: float
    peak_memory_mb: float
    llm_calls: int
    generated_sections: int
    measured_at_utc: str


async def run_benchmark_suite(
    fixture_root: Path,
    sizes: list[FixtureSize],
    *,
    include_generation: bool = True,
    force_regenerate: bool = False,
) -> list[BenchmarkResult]:
    """Run benchmarks across requested fixture sizes.

    Args:
        fixture_root: Directory used to create/find fixture projects
        sizes: Fixture sizes to benchmark
        include_generation: Whether to run full guide generation (heuristic mode)
        force_regenerate: Recreate fixture projects even if they already exist

    Returns:
        Ordered benchmark results
    """
    fixture_paths = create_fixtures(fixture_root, sizes, force=force_regenerate)
    results: list[BenchmarkResult] = []

    for size in sizes:
        fixture_path = fixture_paths[size]
        result = await _benchmark_fixture(
            fixture_path=fixture_path,
            size=size,
            include_generation=include_generation,
        )
        results.append(result)

    return results


def write_results_json(results: list[BenchmarkResult], output_path: Path) -> None:
    """Write benchmark results to a JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(result) for result in results]
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def format_markdown_report(results: list[BenchmarkResult]) -> str:
    """Format benchmark results as a Markdown report."""
    lines = [
        "# DevWayfinder Benchmark Results",
        "",
        f"> Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "| Size | Modules | Dependencies | Analysis (s) | Generation (s) | Total (s) | Peak Memory (MB) |",
        "|------|---------|--------------|--------------|----------------|-----------|------------------|",
    ]

    for result in results:
        lines.append(
            "| "
            f"{result.size} | "
            f"{result.modules_detected} | "
            f"{result.dependencies_detected} | "
            f"{result.analysis_seconds:.3f} | "
            f"{result.generation_seconds:.3f} | "
            f"{result.total_seconds:.3f} | "
            f"{result.peak_memory_mb:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Generation mode uses `--no-llm` equivalent behavior (heuristic summarization).",
            "- Peak memory is measured with Python `tracemalloc` during benchmark execution.",
            "",
        ]
    )
    return "\n".join(lines)


def run_benchmark_suite_sync(
    fixture_root: Path,
    sizes: list[FixtureSize],
    *,
    include_generation: bool = True,
    force_regenerate: bool = False,
) -> list[BenchmarkResult]:
    """Synchronous wrapper for benchmark suite execution."""
    return asyncio.run(
        run_benchmark_suite(
            fixture_root=fixture_root,
            sizes=sizes,
            include_generation=include_generation,
            force_regenerate=force_regenerate,
        )
    )


async def _benchmark_fixture(
    *,
    fixture_path: Path,
    size: FixtureSize,
    include_generation: bool,
) -> BenchmarkResult:
    """Run benchmark measurement for a single fixture directory."""
    graph_builder = GraphBuilder()

    tracemalloc.start()
    run_start = time.perf_counter()

    analysis_start = time.perf_counter()
    project, graph = await graph_builder.build(fixture_path)
    analysis_seconds = time.perf_counter() - analysis_start

    generation_seconds = 0.0
    llm_calls = 0
    generated_sections = 0

    if include_generation:
        generator = GuideGenerator(
            project_path=fixture_path,
            config=GenerationConfig(
                use_llm=False,
                providers=[HeuristicProvider()],
                include_mermaid=True,
            ),
        )
        try:
            generation_start = time.perf_counter()
            generation_result = await generator.generate()
            generation_seconds = time.perf_counter() - generation_start
            llm_calls = generation_result.llm_calls_made
            generated_sections = len(generation_result.guide.sections)
        finally:
            await generator.close()

    total_seconds = time.perf_counter() - run_start
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return BenchmarkResult(
        size=size,
        fixture_path=str(fixture_path),
        modules_detected=project.module_count,
        dependencies_detected=graph.edge_count,
        analysis_seconds=analysis_seconds,
        generation_seconds=generation_seconds,
        total_seconds=total_seconds,
        peak_memory_mb=peak / (1024 * 1024),
        llm_calls=llm_calls,
        generated_sections=generated_sections,
        measured_at_utc=datetime.now(UTC).isoformat(),
    )
