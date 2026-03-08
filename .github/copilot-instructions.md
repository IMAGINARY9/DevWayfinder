# DevWayfinder — Copilot Instructions

> **Project:** AI-Powered Developer Onboarding Generator  
> **Status:** MVP 1 In Progress  
> **Last Updated:** 2026-03-08

---

## 🚨 CRITICAL: Documentation Rules

### Single Source of Truth Principle

**Every piece of information has exactly ONE authoritative location.**

Before creating or updating documentation:
1. Check the [Authoritative Sources Table](#authoritative-sources-table)
2. Update ONLY the authoritative document
3. Reference (never duplicate) information from other documents

### Authoritative Sources Table

| Topic | Authoritative Document | DO NOT document elsewhere |
|-------|----------------------|---------------------------|
| System architecture, components, data flow | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | ❌ README, code comments |
| Functional & non-functional requirements | [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) | ❌ Implementation plan, issues |
| MVP roadmap, milestones, task breakdown | [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) | ❌ README, project boards |
| Configuration options, templates | [docs/CONFIGURATION.md](docs/CONFIGURATION.md) | ❌ Code comments, README |
| Development rules, coding standards | [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | ❌ README, Wiki |
| LLM setup, model configuration | [docs/USAGE.md](docs/USAGE.md) | ❌ README, config files |

### When Completing Work

1. **Update IMPLEMENTATION_PLAN.md** — Mark completed tasks, update status
2. **Keep README.md minimal** — Only quick start, link to authoritative docs
3. **Never duplicate** — If info exists elsewhere, link to it

---

## 📋 Project Overview

DevWayfinder analyzes codebases to produce structured onboarding guides with:
- Architecture overview
- Module descriptions (LLM-generated)
- Dependency graph visualization
- Entry points and "Start Here" recommendations

### Tech Stack

| Component | Technology |
|-----------|------------|
| CLI | Python 3.11+, Typer, Rich |
| Analysis | AST, Tree-sitter (optional), networkx |
| LLM | OpenAI-compatible APIs, Ollama, official OpenAI |
| Config | Pydantic, YAML |
| Testing | pytest, pytest-asyncio |

---

## 🏗️ Architecture Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interfaces                          │
│               (CLI / VS Code Extension / Python API)            │
├─────────────────────────────────────────────────────────────────┤
│                      Orchestration Layer                         │
│           (Guide Generator, Pipeline Controller)                 │
├───────────────┬──────────────────┬──────────────────────────────┤
│   Analyzers   │   Summarizers    │         Providers            │
├───────────────┴──────────────────┴──────────────────────────────┤
│                         Core Domain                              │
│     (Module, DependencyGraph, Project, OnboardingGuide)         │
├─────────────────────────────────────────────────────────────────┤
│                      Infrastructure                              │
│       (Config, Caching, File System, Git Client, HTTP)          │
└─────────────────────────────────────────────────────────────────┘
```

**Full architecture details:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## 📁 Package Structure

```
src/devwayfinder/
├── core/           # Domain models, protocols, exceptions
├── analyzers/      # Language-specific code analyzers
├── generators/     # Output generation (Markdown, etc.)
├── providers/      # LLM backend adapters
├── cli/            # Command-line interface
├── config/         # Configuration loading
├── cache/          # Caching layer
└── utils/          # Shared utilities
```

---

## 🔧 Development Workflow

### Before Starting Work

1. Read current phase in [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)
2. Check requirements in [REQUIREMENTS.md](docs/REQUIREMENTS.md)
3. Review architecture in [ARCHITECTURE.md](docs/ARCHITECTURE.md)

### Code Quality Requirements

1. **Type Safety:** Full type annotations on all public functions
2. **Testing:** Write tests alongside code, maintain 80%+ coverage
3. **Patterns:** Use Factory, Strategy, Adapter patterns as per architecture
4. **Abstraction:** High-level abstraction for reusability
5. **Proactive Improvement:** Fix issues immediately when discovered

### Running Quality Checks

```bash
# Tests
pytest tests/ -v

# Linting
ruff check src tests

# Type checking
mypy src

# Coverage
pytest --cov=devwayfinder --cov-report=html
```

### Commit Workflow

1. Run tests: `pytest`
2. Run linting: `ruff check src tests`
3. Run type check: `mypy src`
4. Update documentation if needed
5. Commit: `git commit -m "type(scope): description"`

---

## 📌 Current MVP Status

**MVP 1: Core CLI & Python Analysis**

Status: In Progress

Key deliverables:
- [x] Project structure and configuration
- [x] Core domain models (Module, Project, DependencyGraph, Guide)
- [x] Protocol definitions (Analyzer, Provider, Generator)
- [ ] Python import/export analyzer
- [x] LLM providers (OpenAI-compatible, Ollama, official OpenAI)
- [x] Heuristic fallback provider
- [ ] Guide generator
- [ ] CLI commands (analyze, generate)
- [x] CLI command (test-model)
- [ ] Caching layer

**Next steps:** Implement Python analyzer and guide generation pipeline

---

## 🔌 LLM Configuration

Default configuration for the validated local OpenAI-compatible setup:

```yaml
model:
  provider: openai_compat
  model_name: null
  base_url: http://127.0.0.1:5000/v1
  api_key: local
  timeout: 120
  max_tokens: 512
```

**Full LLM setup:** [docs/USAGE.md](docs/USAGE.md)

Test connection:
```bash
devwayfinder test-model --provider openai_compat --base-url http://127.0.0.1:5000/v1
```

---

## ⚠️ Common Pitfalls

1. **Don't duplicate documentation** — Always reference authoritative source
2. **Don't skip tests** — Every feature needs tests
3. **Don't hard-code dependencies** — Use dependency injection
4. **Don't forget type annotations** — mypy must pass
5. **Don't defer technical debt** — Fix issues when found

---

## 📚 Key Documents

| Purpose | Document |
|---------|----------|
| **What to build** | [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) |
| **How to build** | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| **When to build** | [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) |
| **How to code** | [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) |
| **How to configure** | [docs/CONFIGURATION.md](docs/CONFIGURATION.md) |
| **How to use LLM** | [docs/USAGE.md](docs/USAGE.md) |
