# Benchmark Suite

This directory contains reproducible benchmark tooling for DevWayfinder MVP 3.

## Run

```bash
# From repository root (PowerShell)
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe benchmarks/run_benchmarks.py --force-regenerate
```

## Outputs

- `benchmarks/results/latest.json`
- `benchmarks/results/latest.md`
- `benchmarks/fixtures/generated/{small,medium,large}`

Published baseline interpretation is documented in [docs/PERFORMANCE.md](../docs/PERFORMANCE.md).
