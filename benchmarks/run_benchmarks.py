"""Run DevWayfinder benchmark suite for synthetic fixture sizes."""

from __future__ import annotations

import argparse
from pathlib import Path

from devwayfinder.benchmarks.runner import (
    format_markdown_report,
    run_benchmark_suite_sync,
    write_results_json,
)


def _parse_sizes(raw: str) -> list[str]:
    """Parse comma-separated size list from CLI input."""
    parts = [item.strip() for item in raw.split(",") if item.strip()]
    if not parts:
        return ["small", "medium", "large"]
    return parts


def main() -> int:
    """Run benchmark suite and persist reports."""
    parser = argparse.ArgumentParser(description="Run DevWayfinder benchmark suite")
    parser.add_argument(
        "--sizes",
        default="small,medium,large",
        help="Comma-separated sizes to run (small,medium,large)",
    )
    parser.add_argument(
        "--fixtures-dir",
        default="benchmarks/fixtures/generated",
        help="Directory used for generated benchmark fixtures",
    )
    parser.add_argument(
        "--json-out",
        default="benchmarks/results/latest.json",
        help="Path for JSON benchmark output",
    )
    parser.add_argument(
        "--markdown-out",
        default="benchmarks/results/latest.md",
        help="Path for Markdown benchmark report",
    )
    parser.add_argument(
        "--analysis-only",
        action="store_true",
        help="Skip generation stage and only benchmark analysis",
    )
    parser.add_argument(
        "--force-regenerate",
        action="store_true",
        help="Regenerate fixtures even if they already exist",
    )

    args = parser.parse_args()

    raw_sizes = _parse_sizes(args.sizes)
    valid_sizes = {"small", "medium", "large"}
    invalid = [item for item in raw_sizes if item not in valid_sizes]
    if invalid:
        parser.error(f"Invalid sizes: {', '.join(invalid)}")

    sizes = [item for item in raw_sizes if item in valid_sizes]

    results = run_benchmark_suite_sync(
        fixture_root=Path(args.fixtures_dir),
        sizes=sizes,  # type: ignore[arg-type]
        include_generation=not args.analysis_only,
        force_regenerate=args.force_regenerate,
    )

    json_path = Path(args.json_out)
    write_results_json(results, json_path)

    markdown_report = format_markdown_report(results)
    markdown_path = Path(args.markdown_out)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown_report, encoding="utf-8")

    print(f"Benchmark run complete. JSON: {json_path}")
    print(f"Benchmark run complete. Markdown: {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
