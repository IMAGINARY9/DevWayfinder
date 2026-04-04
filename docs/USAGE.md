# DevWayfinder - Usage Guide

> **Version:** 1.1.1  
> **Status:** Active  
> **Last Updated:** 2026-04-04  
> **Authoritative Source:** This document is the single source of truth for runtime usage and provider setup.

---

## 1. Quick Start

```bash
# Analyze without generating a guide
devwayfinder analyze ./my-project

# Generate guide in heuristic mode (no LLM calls)
devwayfinder generate ./my-project --no-llm

# Generate guide with provider
devwayfinder generate ./my-project \
  --model-provider openai_compat \
  --base-url http://127.0.0.1:11434/v1
```

---

## 2. Commands

### 2.1 `generate`

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
| `--guide-template PATH` | Use a custom guide template YAML |
| `-v, --verbose` | Show verbose CLI diagnostics |

### 2.2 `analyze`

Run analysis only (no guide generation):

```bash
devwayfinder analyze PATH [--json] [--verbose]
```

### 2.3 `test-model`

Validate provider health and completion:

```bash
devwayfinder test-model --provider ollama --model mistral:7b
```

### 2.4 `init`

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

### 3.2 Ollama

```bash
ollama pull mistral:7b
devwayfinder test-model --provider ollama --model mistral:7b
```

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
