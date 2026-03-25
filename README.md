# DevWayfinder

> **AI-Powered Developer Onboarding Generator**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status: MVP 2.5 Complete](https://img.shields.io/badge/Status-MVP%202.5%20Complete-green.svg)](docs/IMPLEMENTATION_PLAN.md)
[![Tests: 369✓](https://img.shields.io/badge/Tests-369%E2%9C%93-brightgreen.svg)]()
[![Coverage: 81.34%](https://img.shields.io/badge/Coverage-81.34%25-brightgreen.svg)]()

---

## What is DevWayfinder?

DevWayfinder automates the hour-long process of understanding an unfamiliar codebase by:

1. **Clone a repository** → `git clone https://github.com/user/project.git`
2. **Run the tool** → `devwayfinder generate ./project`
3. **Get a structured guide** ← Markdown file with architecture, modules, entry points, and recommendations

Perfect for:
- 🚀 **Onboarding new team members** — Get into the codebase in minutes, not hours
- 📚 **Technical documentation** — Auto-generate always up-to-date reference guides
- 🔍 **Code exploration** — Understand relationships between modules instantly
- 🎓 **Learning new projects** — Start from the right place, skip unnecessary code
- 📊 **Architecture review** — Visualize system structure automatically

---

## Key Features

### 🎯 Generated Content
- **Architecture Overview** — High-level system structure and component relationships
- **Module Descriptions** — Natural-language summaries of each code file (LLM-generated)
- **Dependency Graph** — Visual map showing how modules depend on each other
- **Entry Points** — Key files to start reading based on your activity
- **"Start Here" Recommendations** — Guided navigation based on your role

### 💰 Flexible & Affordable
- **Local-First** — Use free Ollama for 100% cost-free analysis
- **Cloud Integration** — Seamlessly fallback to OpenAI, Anthropic, or Azure OpenAI
- **Dynamic Provider Selection** — Auto-detect available services at runtime
- **Cost Transparency** — See estimated cost before generation
- **Heuristic Mode** — Works without LLM for quick structure analysis

### ⚡ Production-Ready
- **Fast** — Analyze 100-module project in seconds
- **Reliable** — 369 tests with 81.34% coverage, real integration tests with live LLMs
- **Smart** — Adaptive prompts reduce token usage 15-20%
- **Transparent** — Shows tokens used, cost breakdown, quality badges ([LLM] vs [heuristic])

---

## Quick Comparison: Which Provider?

| Provider | Cost | Speed | Setup | Quality | Recommended |
|----------|------|-------|-------|---------|------------|
| **Ollama** (Local) | 🟢 Free | 🟢 Fast (GPU) | 🟡 5 min | 🟡 Good | ✅ **Default** |
| **OpenAI** (Cloud) | 🔴 $0.10-1.00* | 🟢 Fast | 🟢 2 min | 🟢 Excellent | If you need best quality |
| **Anthropic** (Cloud) | 🟠 $0.30-3.00* | 🟡 Slower | 🟢 2 min | 🟢 Excellent | Alternative quality |
| **Azure OpenAI** (Cloud) | 🟠 $0.05-0.50* | 🟢 Fast | 🟡 10 min | 🟢 Excellent | Enterprise |
| **Heuristic** (No LLM) | 🟢 Free | 🟢 Fastest | 🟢 Instant | 🟠 Moderate | Quick exploration |

*Estimated per project (100-500 modules). See [USAGE.md](docs/USAGE.md) for detailed cost breakdown.

---

## Use Cases

<details>
<summary><b>📖 Team Onboarding (New Developer)</b></summary>

*"I just joined the team and don't know where to start reading..."*

```bash
devwayfinder generate ./backend --use-llm
# Output: `ONBOARDING.md` with architecture, key modules, entry points
```

**Time Saved:** 4-6 hours of "where is the authentication?" exploration → 5 minutes of reading
</details>

<details>
<summary><b>🔍 Code Review Preparation</b></summary>

*"I'm reviewing unfamiliar code and need to understand the structure first..."*

```bash
devwayfinder generate ./service --no-llm  # Quick heuristic mode
```

**Time Saved:** Skip 1-2 hours of structure analysis, focus on logical review
</details>

<details>
<summary><b>📚 Open Source Investigation</b></summary>

*"I want to contribute to this project but don't know the codebase..."*

```bash
devwayfinder generate ./project --use-llm  # Best quality for understanding
```

**Output:** Structured guide showing where to start, what tests to run, architecture
</details>

<details>
<summary><b>🏗️ Architecture Documentation</b></summary>

*"Our codebase is growing and documentation is outdated..."*

```bash
devwayfinder generate ./src --use-llm  # Generate fresh guide
# Keep it in git, update on major changes
```

**Benefit:** Always up-to-date doc reflecting current code structure
</details>

---

## Installation & Setup

### 1. Prerequisites

- **Python 3.11+**
- **One LLM provider** (pick one; see [Choose Your Provider](#quick-provider-setup) below):
  - Ollama (free, local, recommended)
  - Official OpenAI account + API key
  - Anthropic account + API key
  - Azure OpenAI resource
  - Any OpenAI-compatible endpoint

### 2. Install DevWayfinder

```bash
# Clone
git clone git@github.com:IMAGINARY9/DevWayfinder.git
cd DevWayfinder

# Virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1     # Windows
# source .venv/bin/activate      # Linux/macOS

# Install (development mode)
pip install -e ".[dev]"
```

### 3. Choose Your Provider

<details>
<summary><b>🟢 RECOMMENDED: Ollama (Free, Local)</b></summary>

```bash
# 1. Download & install from https://ollama.ai
# 2. Pull a model
ollama pull mistral:7b
# 3. Start the server (runs in background)
ollama serve
# 4. Verify
devwayfinder test-model --provider ollama --model mistral:7b
```

**Cost:** Free | **Quality:** Good | **Speed:** Fast (if GPU available)
</details>

<details>
<summary><b>🔵 OpenAI API (Best Quality, Costs ~$0.10-0.50 per analysis)</b></summary>

```bash
# 1. Get API key from https://platform.openai.com/api-keys
# 2. Set environment variable
export OPENAI_API_KEY=sk-...
# 3. Verify
devwayfinder test-model --provider openai --model gpt-4o-mini
```

**Cost:** Low | **Quality:** Excellent | **No local setup needed**
</details>

<details>
<summary><b>🟣 Anthropic Claude (Alternative Quality Provider)</b></summary>

```bash
# 1. Get API key from https://console.anthropic.com
# 2. Set environment variable
export ANTHROPIC_API_KEY=sk-ant-...
# 3. Verify
devwayfinder test-model --provider anthropic --model claude-3-haiku
```

**Cost:** Moderate | **Quality:** Excellent | **No local setup needed**
</details>

<details>
<summary><b>☁️ Azure OpenAI (Enterprise)</b></summary>

See [SETUP_AZURE_OPENAI.md](docs/SETUP_AZURE_OPENAI.md) for detailed configuration.

```bash
devwayfinder test-model --provider azure_openai --model gpt-4o-mini
```
</details>

For detailed setup instructions for each provider, see [USAGE.md](docs/USAGE.md).

---

## Usage Examples

### Basic Usage

```bash
# Generate onboarding guide with LLM
devwayfinder generate ./my-project

# Generate without LLM (heuristics only)
devwayfinder generate ./my-project --no-llm

# Specify provider and model
devwayfinder generate ./my-project --provider ollama --model mistral
```

### Advanced Usage

```bash
# Analyze structure without generating (see module breakdown)
devwayfinder analyze ./my-project

# Specify output filename and format
devwayfinder generate ./my-project -o ARCHITECTURE.md

# Show cost estimate before generating
devwayfinder generate ./my-project --estimate-cost

# Use specific config file
devwayfinder generate ./my-project --config ./custom-config.yaml
```

### Example Output

Generated guides include:

```markdown
# Project Onboarding Guide

## Architecture Overview
[System diagram and high-level description]

## Modules
### core/auth.py
Handles user authentication and JWT token management...

### api/routes.py
[Auto-generated description]

## Dependencies
[Dependency graph as visual diagram]

## Getting Started
- Start here: core/main.py
- Run tests: pytest tests/
- Key config: config.yaml
```

---

## Cost & Performance

### Real Numbers (100-module Python project)

| Provider | Setup Time | Analysis Time | Cost | Quality |
|----------|------------|---------------|------|---------|
| Ollama (local GPU) | 5 min | 15-30s | Free | Good |
| Ollama (local CPU) | 5 min | 60-120s | Free | Good |
| OpenAI gpt-4o-mini | 2 min | 5-10s | ~$0.12 | Excellent |
| Anthropic claude-3-haiku | 2 min | 10-15s | ~$0.30 | Excellent |
| Heuristic (no LLM) | Instant | 1-2s | Free | Moderate |

**Rule of Thumb:**
- Projects 10-50 modules: Any provider fine
- Projects 50-200 modules: Ollama recommended (cost-free, good quality)
- Projects 200+ modules: OpenAI or Anthropic (better quality for complexity)

For size 100 modules → 50-70KB of analysis text → 5k-7k tokens with GPT → ~$0.05-0.12 cost

---

## Documentation

| Document | Purpose |
|----------|---------|
| [INSTALLATION.md](docs/INSTALLATION.md) | Step-by-step setup guide |
| [USAGE.md](docs/USAGE.md) | LLM provider configuration & troubleshooting |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design & components |
| [CONFIGURATION.md](docs/CONFIGURATION.md) | All config options |
| [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common issues & fixes |
| [CONTRIBUTING.md](docs/CONTRIBUTING.md) | Development guidelines |

---

## For Contributors

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for:
- Documentation standards (Single Source of Truth principle)
- Code quality requirements (80%+ test coverage, type-checked)
- Development workflow
- Running tests locally

Quick start for development:

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run with coverage
pytest --cov=devwayfinder

# Type check
mypy src

# Lint
ruff check src tests
```

---

## Project Status

**MVP 2.5:** Production-ready with:
- ✅ 369 tests (81.34% coverage)
- ✅ Real LLM integration (not mocked)
- ✅ Multi-provider support (Ollama, OpenAI, Anthropic, Azure)
- ✅ Dynamic provider discovery (auto-detect available services)
- ✅ Cost transparency & quality indicators
- ✅ Performance optimizations (15-20% token reduction)

**Next:** Phase 3 - Documentation & Examples (in progress)

---

## Quick Links — Authoritative Documentation

| Document | Purpose |
|----------|---------|
| [USAGE.md](docs/USAGE.md) | LLM setup, provider configuration, troubleshooting |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, component interactions |
| [CONFIGURATION.md](docs/CONFIGURATION.md) | Configuration options, templates |
| [CONTRIBUTING.md](docs/CONTRIBUTING.md) | Development rules, code standards |
| [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) | MVP roadmap, milestones |

> ⚠️ **Single Source of Truth:** Each topic has exactly ONE authoritative document. See any document for references to others.

---

## Roadmap

| MVP | Focus | Status |
|-----|-------|--------|
| **MVP 1** | Core CLI & Python Analysis | ✅ Complete |
| **MVP 2** | Metrics, Git, TypeScript, Caching | ✅ Complete |
| **MVP 3** | VS Code Extension & Plugin System | 🔲 Planned |
| **MVP 4** | Interactive Features & Polish | 🔲 Planned |
| **MVP 5** | Distribution & Production | 🔲 Planned |

See [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) for detailed breakdown.

## Positioning Snapshot (March 2026)

Based on an external comparative review of DevWayfinder and Architext:

- DevWayfinder is best treated as a **developer-first sister project** in the same ecosystem, not a direct code fork.
- Current strengths are **low operational overhead**, **offline-capable heuristic mode**, and **CLI-focused onboarding UX**.
- Main near-term product risk is **execution on MVP 3-5** (VS Code extension, plugin system, distribution).

Roadmap implications are tracked in [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md), and product requirements are captured in [REQUIREMENTS.md](docs/REQUIREMENTS.md).

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

This project is part of a Bachelor's thesis on AI-powered developer tools.
