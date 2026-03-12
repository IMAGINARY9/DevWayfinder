# DevWayfinder

> **AI-Powered Developer Onboarding Generator**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: MVP 1 Complete](https://img.shields.io/badge/Status-MVP%201%20Complete-green.svg)]()

---

## Overview

Clone a repository → run the tool → get a structured onboarding guide.

DevWayfinder analyzes codebases to produce:
- **Architecture overview** — high-level system structure
- **Module descriptions** — natural-language summaries of each component
- **Dependency graph** — visual map of relationships
- **Entry points** — where to start reading
- **"Start Here" recommendations** — activity-based navigation hints

The tool automates the hours-long process of manually exploring unfamiliar codebases.

---

## Quick Links — Authoritative Documentation

| Document | Purpose | Status |
|----------|---------|--------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, component interactions, data flow | **Primary** |
| [REQUIREMENTS.md](docs/REQUIREMENTS.md) | Functional & non-functional requirements | **Primary** |
| [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) | MVP roadmap, milestones, task breakdown | **Primary** |
| [CONTRIBUTING.md](docs/CONTRIBUTING.md) | Development rules, documentation hygiene, code standards | **Primary** |
| [USAGE.md](docs/USAGE.md) | LLM setup, model configuration | **Primary** |
| [CONFIGURATION.md](docs/CONFIGURATION.md) | Configuration options, templates | **Primary** |

> ⚠️ **Single Source of Truth Principle**: Each topic has exactly ONE authoritative document. Never duplicate information — always reference the canonical source.

---

## Installation

### Prerequisites

- Python 3.11+
- Local OpenAI-compatible LLM endpoint or Ollama — see [USAGE.md](docs/USAGE.md) for provider setup

### Install from Source

```bash
# Clone repository
git clone git@github.com:IMAGINARY9/DevWayfinder.git
cd DevWayfinder

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows PowerShell
# source .venv/bin/activate   # Linux/macOS

# Install in development mode
pip install -e ".[dev]"
```

---

## Quick Start

```bash
# Verify a local OpenAI-compatible endpoint (text-generation-webui, vLLM)
devwayfinder test-model --provider openai_compat --base-url http://127.0.0.1:5000/v1

# Verify Ollama
devwayfinder test-model --provider ollama --model mistral:7b

# Verify official OpenAI
devwayfinder test-model --provider openai --model gpt-4o-mini --api-key $DEVWAYFINDER_API_KEY

# Generate onboarding guide for a project
devwayfinder generate ./path/to/project

# Analyze without generating (inspect structure)
devwayfinder analyze ./path/to/project

# Use heuristic mode (no LLM required)
devwayfinder generate ./path/to/project --no-llm
```

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `devwayfinder generate <path>` | Generate onboarding guide |
| `devwayfinder analyze <path>` | Analyze project structure |
| `devwayfinder test-model` | Verify LLM connection |
| `devwayfinder init` | Create `.devwayfinder/` config directory |

Use `devwayfinder --help` for full command reference.

---

## Configuration

Configuration is loaded from (in order of precedence):
1. CLI arguments
2. Environment variables (`DEVWAYFINDER_*`)
3. Project config (`.devwayfinder/config.yaml`)
4. User config (`~/.devwayfinder/config.yaml`)
5. Built-in defaults

See [CONFIGURATION.md](docs/CONFIGURATION.md) for all options.

### Example Config

```yaml
# .devwayfinder/config.yaml
model:
  provider: openai_compat
  model_name: null
  base_url: http://127.0.0.1:5000/v1
  api_key: local

analysis:
  include_patterns:
    - "**/*.py"
    - "**/*.ts"
  exclude_patterns:
    - "**/node_modules/**"
    - "**/.venv/**"
  enable_git_analysis: true

output:
  format: markdown
  include_graph: true
  include_metrics: true
```

---

## How It Works

1. **Ingest** — Scan directory structure, detect build system, extract documentation
2. **Analyze** — Parse imports/exports, build dependency graph, compute metrics
3. **Summarize** — Generate natural-language descriptions via LLM (or heuristics)
4. **Compose** — Assemble sections into structured onboarding document
5. **Output** — Render as Markdown (or other formats)

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed component design.

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| **CLI** | Python 3.11+, Typer, Rich |
| **Analysis** | Python AST, regex heuristics, networkx |
| **LLM** | OpenAI-compatible APIs, Ollama, official OpenAI |
| **Configuration** | Pydantic, YAML |
| **Testing** | pytest, pytest-asyncio |

---

## Development

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for:
- Documentation hygiene rules (Single Source of Truth)
- Code quality requirements
- Architecture principles
- Development workflow

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=devwayfinder

# Run specific test file
pytest tests/unit/test_analyzers.py
```

### Code Quality

```bash
# Linting
ruff check src tests

# Type checking
mypy src

# Format check
ruff format --check src tests
```

---

## Roadmap

| MVP | Focus | Status |
|-----|-------|--------|
| **MVP 1** | Core CLI & Python Analysis | 🔄 In Progress |
| **MVP 2** | Metrics, Git, TypeScript, Caching | 🔲 Planned |
| **MVP 3** | VS Code Extension & Plugin System | 🔲 Planned |
| **MVP 4** | Interactive Features & Polish | 🔲 Planned |
| **MVP 5** | Distribution & Production | 🔲 Planned |

See [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for detailed breakdown.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

This project is part of a Bachelor's thesis on AI-powered developer tools.
