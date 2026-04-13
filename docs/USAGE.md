# DevWayfinder - Usage Guide

> **Version:** 1.1.1  
> **Status:** Active  
> **Last Updated:** 2026-04-13  
> **Authoritative Source:** This document is the single source of truth for runtime usage and provider setup.

---

## 1. Quick Start

```bash
# Guided one-command workflow (default: auto provider probe + detailed mode)
devwayfinder guide ./my-project --auto

# Minimal offline workflow (heuristic-only)
devwayfinder guide ./my-project --quality minimal --no-llm

# Advanced/manual generation workflow
devwayfinder generate ./my-project \
  --quality detailed \
  --model-provider openai_compat \
  --base-url http://127.0.0.1:11434/v1
```

---

## 2. Commands

### 2.1 `guide`

Recommended one-command workflow:

```bash
devwayfinder guide PATH [options]
```

Behavior:

1. Uses LLM-first generation by default (`--quality detailed`)
2. Auto-probes local endpoints by default (`--auto`) and validates both health and completion output before selection
3. Writes guide output to `PATH/ONBOARDING_GUIDE.md` unless overridden
4. Writes concise run report to `PATH/.devwayfinder/run_report.md`

Key options:

| Option | Description |
|--------|-------------|
| `-o, --output PATH` | Write guide to custom file path |
| `--quality PROFILE` | `minimal`, `detailed` |
| `--auto / --manual` | Enable/disable provider auto-probing |
| `--no-llm` | Force heuristic-only mode |
| `--model-name NAME` | Optional model override |
| `--base-url URL` | Optional endpoint override |
| `--api-key KEY` | API key (or `DEVWAYFINDER_API_KEY`) |
| `-v, --verbose` | Show probe diagnostics |

### 2.2 `generate`

Run the full pipeline:

1. Structure and dependency analysis
2. Module summarization (LLM or heuristic)
3. Guide assembly and Markdown rendering
4. Cost/token summary reporting

```bash
devwayfinder generate PATH [options]
```

Options:

| Option | Description |
|--------|-------------|
| `-o, --output PATH` | Write Markdown guide to file |
| `--model-provider PROVIDER` | Provider: `openai_compat`, `openai`, `ollama`, `heuristic` |
| `--model-name NAME` | Provider-specific model name |
| `--base-url URL` | Provider endpoint URL |
| `--api-key KEY` | API key (or `DEVWAYFINDER_API_KEY`) |
| `--no-llm` | Force heuristic-only summarization |
| `--quality PROFILE` | `minimal`, `detailed` |
| `--auto` | Auto-probe local providers and use the first endpoint that passes health and completion checks |
| `--guide-template PATH` | Use a custom guide template YAML |
| `-v, --verbose` | Show verbose CLI diagnostics |

### 2.3 `analyze`

Run analysis only (no guide generation):

```bash
devwayfinder analyze PATH [--json] [--verbose]
```

### 2.4 `test-model`

Validate provider health and completion:

```bash
devwayfinder test-model --provider PROVIDER [--model MODEL] [--base-url URL]
```

Behavior notes:

- Health and completion checks run against the same provider family.
- If `--model` is omitted, DevWayfinder will reuse the first discovered model from the health response when possible.
- HTTP failures include method, path, status, and response preview for faster diagnosis.

### 2.5 `init`

Initialize `.devwayfinder/config.yaml` using built-in project templates:

```bash
devwayfinder init .
devwayfinder init . --list
devwayfinder init . --template python --force
```

---

## 3. Provider Setup

### 3.1 OpenAI-Compatible Local Endpoint

Supported local examples:

- `http://127.0.0.1:11434/v1` (Ollama default)
- `http://127.0.0.1:11435/v1` (Ollama alternate)
- `http://127.0.0.1:5000/v1` (text-generation-webui)
- `http://127.0.0.1:1234/v1` (LM Studio)
- `http://127.0.0.1:8000/v1` (vLLM)

```bash
devwayfinder test-model \
  --provider openai_compat \
  --base-url http://127.0.0.1:11434/v1
```

OpenAI-compatible endpoint contract:

- Health probe: `GET /models`
- Completion probe: `POST /chat/completions`

### 3.2 Ollama

```bash
ollama pull mistral:7b
devwayfinder test-model --provider ollama --model mistral:7b
```

Ollama endpoint contract:

- Health probe: `GET /api/tags`
- Completion probe: `POST /api/generate`

### 3.3 Official OpenAI

```bash
# PowerShell
$env:DEVWAYFINDER_API_KEY = "sk-..."

devwayfinder test-model --provider openai --model gpt-4o-mini
```

### 3.4 Heuristic-Only (Offline)

```bash
devwayfinder generate ./my-project --no-llm
```

---

## 4. Guide Template Customization (MVP 3.1)

Use `.devwayfinder/template.yaml` in your project root:

```yaml
name: team-template
extends: default

sections:
  - type: start_here
    title: Read This First
  - type: dependencies
    enabled: false
```

Notes:

- `extends` supports `default` and `compact`
- Listed sections are reordered first
- `enabled: false` removes a section from output
- Use `--guide-template` to test alternative templates without changing project files

---

## 5. Cost and Token Visibility

Generation prints:

- Preflight estimate (`Modules`, estimated operations, estimated tokens, estimated cost)
- Final totals (`Tokens used (estimated)`, `Cost (estimated)`)

This reporting is always enabled in current MVP behavior.

Quality and fallback visibility:

- Guides include a quality banner with `Quality Profile`, `LLM Coverage`, and fallback level.
- Detailed mode runs extra synthesis passes for architecture and start-here guidance.
- Minimal mode is optimized for speed and defaults to heuristic-only behavior.

---

## 6. Benchmarking (MVP 3.3)

Run synthetic benchmark suite:

```bash
# From repository root (ensure PYTHONPATH=src when running from source)
python benchmarks/run_benchmarks.py --force-regenerate
```

Output artifacts:

- `benchmarks/results/latest.json`
- `benchmarks/results/latest.md`
- Generated fixtures in `benchmarks/fixtures/generated/`

For published baseline interpretation, see [PERFORMANCE.md](PERFORMANCE.md).

---

## 7. Troubleshooting

- Provider connection issues: use `devwayfinder test-model` first.
- If generation is slower than expected, run `--no-llm` to isolate analysis throughput.
- If custom template fails, re-run with `--guide-template` and check YAML schema in [CONFIGURATION.md](CONFIGURATION.md).

---

## 8. Target Evaluation Workflow (LLM Agents)

Use this compact sequence when validating changes against a real project target (for example Stonekeep):

```bash
# Minimal baseline (heuristic-only)
devwayfinder guide ../Stonekeep --quality minimal --no-llm \
  -o ../Stonekeep/.devwayfinder/eval/latest/guide_minimal.md -v

# Detailed auto probe (LLM-first, fallback-safe)
devwayfinder guide ../Stonekeep --quality detailed --auto \
  -o ../Stonekeep/.devwayfinder/eval/latest/guide_detailed_auto.md -v
```

Then copy the per-run report immediately after each run:

```bash
cp ../Stonekeep/.devwayfinder/run_report.md \
  ../Stonekeep/.devwayfinder/eval/latest/run_report_<mode>.md
```

Recommended evaluation checklist:

1. Confirm run reports include `Detail Mode`, provider, coverage, and notes.
2. Compare `guide_minimal.md` vs `guide_detailed_auto.md` for LLM coverage and depth differences.
3. Inspect auto-probe diagnostics for completion failures (`empty` or `reasoning-only`).
4. Validate `Start Here` contains unique, non-duplicated onboarding steps.
