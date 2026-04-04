# DevWayfinder

AI-powered developer onboarding guide generator.

## Quick Start

### 1. Install (from source)

```bash
git clone https://github.com/IMAGINARY9/DevWayfinder.git
cd DevWayfinder
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### 2. Verify Provider (optional)

```bash
devwayfinder test-model --provider ollama --model mistral:7b
```

### 3. Generate Guide

```bash
devwayfinder generate ./my-project --no-llm
# or
# devwayfinder generate ./my-project --model-provider openai_compat --base-url http://127.0.0.1:11434/v1
```

---

## Core Commands

- `devwayfinder analyze <path>`
- `devwayfinder generate <path>`
- `devwayfinder test-model`
- `devwayfinder init`

---

## Status

- MVP 1: complete
- MVP 2: complete
- MVP 2.5: complete
- MVP 3: in progress

See roadmap details in [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md).

---

## Documentation (Authoritative)

- Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Requirements: [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md)
- Roadmap and milestone status: [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)
- Configuration: [docs/CONFIGURATION.md](docs/CONFIGURATION.md)
- Provider setup and runtime usage: [docs/USAGE.md](docs/USAGE.md)
- Development and contribution standards: [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)
- Performance benchmarks: [docs/PERFORMANCE.md](docs/PERFORMANCE.md)

---

## License

MIT - see [LICENSE](LICENSE).
