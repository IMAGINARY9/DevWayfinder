# DevWayfinder — Requirements Specification

> **Version:** 1.1.0  
> **Status:** Active  
> **Last Updated:** 2026-03-09  
> **Authoritative Source:** This document is the single source of truth for project requirements.

---

## 1. Overview

DevWayfinder is an AI-powered developer onboarding generator that transforms repository exploration from manual investigation into guided discovery. The system analyzes codebases to produce structured onboarding guides, architecture overviews, and navigable knowledge bases.

### 1.1 Product Vision

> Clone a repository → run the tool → get a structured onboarding guide with architecture overview, key modules, contribution guidelines, setup instructions, and "where to start" recommendations.

### 1.2 Target Users

| User | Need | Value Delivered |
|------|------|-----------------|
| **New team members** | Understand unfamiliar codebase quickly | Structured onboarding path, reduced ramp-up time |
| **Senior engineers** | Dive into unfamiliar modules | Module summaries, dependency graphs, key entry points |
| **Architects** | Audit codebase structure | Complexity metrics, dependency analysis, coverage gaps |
| **Open source contributors** | Navigate new projects | "Start here" recommendations, key file identification |

---

## 2. Functional Requirements

### 2.1 Code Analysis Engine

| ID | Requirement | Priority | MVP |
|----|-------------|----------|-----|
| FR-001 | Parse directory structure and identify project layout | Must | 1 |
| FR-002 | Detect build system and package manager (npm, pip, cargo, etc.) | Must | 1 |
| FR-003 | Extract README, CONTRIBUTING, CHANGELOG content | Must | 1 |
| FR-004 | Build dependency graph from imports/requires | Must | 1 |
| FR-005 | Identify entry points (main files, CLI commands, exports) | Must | 1 |
| FR-006 | Compute file-level complexity metrics (LOC, cyclomatic) | Should | 2 |
| FR-007 | Analyze git log for change frequency and contributors | Should | 2 |
| FR-008 | Support layered parsing: Python AST → regex heuristics → LLM fallback | Must | 1 |
| FR-009 | Gracefully degrade when parsers unavailable | Must | 1 |
| FR-010 | Cache analysis results for incremental updates | Should | 2 |

### 2.2 Language Support

| ID | Requirement | Priority | MVP |
|----|-------------|----------|-----|
| FR-020 | Support Python import/export extraction | Must | 1 |
| FR-021 | Support TypeScript/JavaScript import/export extraction | Should | 2 |
| FR-022 | Support generic file structure analysis (any language) | Must | 1 |
| FR-023 | Plugin system for adding new language analyzers | Should | 3 |
| FR-024 | Tree-sitter integration for accurate parsing (optional enhancement) | Could | 3 |
| FR-025 | Fallback to regex/LLM for unsupported languages | Must | 1 |

### 2.3 Summarization Engine

| ID | Requirement | Priority | MVP |
|----|-------------|----------|-----|
| FR-030 | Generate natural-language module descriptions | Must | 1 |
| FR-031 | Produce architecture overview from dependency graph | Must | 1 |
| FR-032 | Identify and describe key entry points | Must | 1 |
| FR-033 | Generate "Start Here" recommendations based on activity | Should | 2 |
| FR-034 | Create setup/build instructions from detected config | Should | 2 |
| FR-035 | Support multiple LLM backends (local, API, containerized) | Must | 1 |
| FR-036 | Cache LLM responses per file hash | Must | 1 |
| FR-037 | Work without LLM using heuristic summaries | Must | 1 |

### 2.4 Output Generation

| ID | Requirement | Priority | MVP |
|----|-------------|----------|-----|
| FR-040 | Generate Markdown onboarding document | Must | 1 |
| FR-041 | Include dependency graph visualization (Mermaid/ASCII) | Should | 2 |
| FR-042 | Generate module-by-module reference guide | Must | 1 |
| FR-043 | Export to multiple formats (MD, HTML, PDF) | Could | 3 |
| FR-044 | Include complexity metrics per module | Should | 2 |
| FR-045 | Generate interactive HTML with collapsible sections | Won't | — |

### 2.5 CLI Interface

| ID | Requirement | Priority | MVP |
|----|-------------|----------|-----|
| FR-050 | `devwayfinder analyze <path>` — run full analysis | Must | 1 |
| FR-051 | `devwayfinder generate <path>` — generate onboarding guide | Must | 1 |
| FR-052 | `devwayfinder init` — create .devwayfinder config directory | Should | 2 |
| FR-053 | ~~`devwayfinder serve` — local server for interactive viewing~~ | Won't | — |
| FR-054 | Support YAML/TOML configuration file | Must | 1 |
| FR-055 | Override config via CLI flags | Must | 1 |
| FR-056 | Rich progress display with status indicators | Should | 2 |
| FR-057 | `devwayfinder test-model` — verify LLM connection | Must | 1 |

### 2.6 VS Code Extension (Future MVP)

| ID | Requirement | Priority | MVP |
|----|-------------|----------|-----|
| FR-060 | Tree view showing module structure | Should | 3 |
| FR-061 | Graph panel with navigable dependency visualization | Should | 3 |
| FR-062 | Hover summaries for files/modules | Could | 3 |
| FR-063 | "Explain this module" context menu command | Could | 3 |
| FR-064 | Guides catalog with editable notes | Could | 4 |
| FR-065 | File watcher for incremental re-analysis | Could | 4 |
| FR-066 | Export guide from extension | Could | 3 |

### 2.7 Template & Configuration System

| ID | Requirement | Priority | MVP |
|----|-------------|----------|-----|
| FR-070 | Support `.devwayfinder/config.yaml` for project settings | Must | 1 |
| FR-071 | Support `.devwayfinder/template.yaml` for guide structure | Should | 2 |
| FR-072 | Allow custom onboarding checklists | Should | 2 |
| FR-073 | User-level config in `~/.devwayfinder/` | Should | 2 |
| FR-074 | Template inheritance and overrides | Could | 3 |

---

## 3. Non-Functional Requirements

### 3.1 Performance

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-001 | Analysis of 100-file project | < 30 seconds (excluding LLM) |
| NFR-002 | Analysis of 1000-file project | < 3 minutes (excluding LLM) |
| NFR-003 | Incremental re-analysis on file change | < 5 seconds |
| NFR-004 | LLM summary caching hit rate | > 80% on repeated runs |
| NFR-005 | Memory usage for large repos | < 500 MB |

### 3.2 Reliability

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-010 | Graceful handling of malformed code | 100% (skip with warning) |
| NFR-011 | LLM unavailability fallback | Heuristic summaries generated |
| NFR-012 | Recovery from interrupted analysis | Resume from cache |
| NFR-013 | Binary file detection and skip | > 99% accuracy |

### 3.3 Usability

| ID | Requirement | Description |
|----|-------------|-------------|
| NFR-020 | Zero configuration for basic use | Works with just `devwayfinder generate .` |
| NFR-021 | Clear error messages | Include cause, location, and suggested fix |
| NFR-022 | Progress indication | Show current phase and estimated time |
| NFR-023 | Help text for all commands | `--help` flag comprehensive |

### 3.4 Maintainability

| ID | Requirement | Description |
|----|-------------|-------------|
| NFR-030 | Test coverage | > 80% for core modules |
| NFR-031 | Type annotations | 100% public API typed |
| NFR-032 | Documentation | All public functions documented |
| NFR-033 | Modular architecture | New analyzers without core changes |

### 3.5 Security

| ID | Requirement | Description |
|----|-------------|-------------|
| NFR-040 | No code execution | Never execute analyzed code |
| NFR-041 | Path sanitization | Prevent directory traversal |
| NFR-042 | API key handling | Environment variables only |
| NFR-043 | Local-first | Default to local models, no data leaving machine |

---

## 4. Constraints

### 4.1 Technical Constraints

| Constraint | Description |
|------------|-------------|
| Python 3.11+ | Required for modern async features |
| Cross-platform | Windows, macOS, Linux support |
| Offline-capable | Core features work without network |
| LLM agnostic | Support local (Ollama/llama.cpp) and API (OpenAI-compatible) |

### 4.2 Resource Constraints

| Constraint | Description |
|------------|-------------|
| No bundled models | Users provide their own LLM |
| Single-machine | No distributed processing required |
| Standard hardware | Run on typical developer laptop |

---

## 5. Acceptance Criteria

### 5.1 MVP 1 Acceptance

- [ ] Analyze a mid-size Python project (~50 files)
- [ ] Generate Markdown onboarding document with:
  - [ ] Architecture overview section
  - [ ] Module descriptions for top-level packages
  - [ ] Dependency list per module
  - [ ] Entry points identified
- [ ] CLI works with zero configuration
- [ ] LLM integration functions with Ollama
- [ ] Heuristic mode works without LLM (offline fallback)

### 5.2 MVP 2 Acceptance

- [ ] Support TypeScript/JavaScript projects
- [ ] Include complexity metrics in output
- [ ] Include git activity analysis
- [ ] Configuration file support
- [ ] "Start Here" recommendations working

### 5.3 MVP 3 Acceptance

- [ ] Basic VS Code extension functional
- [ ] Dependency graph visualization
- [ ] Multiple export formats
- [ ] Template customization

---

## 6. Out of Scope

The following are explicitly **not** in scope for this project:

- Real-time collaboration features
- Cloud hosting or SaaS deployment
- Supporting every programming language from day one
- Interactive code generation
- Code modification or refactoring suggestions
- IDE plugins beyond VS Code

---

## 7. Dependencies

### 7.1 External Dependencies

| Dependency | Purpose | Required |
|------------|---------|----------|
| LLM (Ollama/API) | Natural language summaries | Yes (degraded mode without) |
| Git | Change history analysis | No (optional features) |
| Tree-sitter | Accurate parsing | No (fallback to regex) |
| Node.js | VS Code extension | No (extension only) |

### 7.2 Python Dependencies

| Package | Purpose |
|---------|---------|
| `typer` | CLI framework |
| `pydantic` | Data validation, settings |
| `httpx` | Async HTTP client |
| `rich` | Terminal formatting |
| `networkx` | Graph algorithms |
| `tree-sitter` | Language parsing (optional) |
| `aiofiles` | Async file I/O |
| `pyyaml` | YAML config parsing |
| `gitpython` | Git integration |

---

## 8. Architectural Decisions

### AD-001: Hybrid Parsing Strategy (2026-03-09)

**Decision:** Adopt a hybrid approach — universal heuristic/AST core with well-defined interface hooks for future specialized parsers.

**Context:** Analysis of parser strategy requirements revealed a scope creep risk with Tree-sitter integration. Each new language grammar constitutes a sub-project with ongoing maintenance burden. For an onboarding tool, the accuracy of regex + Python AST + LLM summaries is sufficient to deliver value.

**Approach (3-phase evolutionary architecture):**
1. **MVP 1 (Core):** Python AST + regex heuristics + LLM fallback + basic heuristics. Define stable `Analyzer` protocol interface with plugin hooks.
2. **MVP 2-3 (Enhancement):** Add specialized analyzers (TypeScript regex, git history). Tree-sitter as optional enhancement, not a requirement.
3. **MVP 4+ (Scaling):** Full plugin registry, community language analyzers, Tree-sitter where it delivers measurable value.

**Rationale:** Regex + LLM produces 'good enough' analysis for onboarding use cases. Tree-sitter investment deferred until user feedback confirms demand for higher-accuracy parsing.

---

## 9. Glossary

| Term | Definition |
|------|------------|
| **Module** | A logical unit of code (file, directory, or package) |
| **Entry point** | A file that serves as a starting point (main.py, index.ts) |
| **Dependency graph** | Directed graph showing import relationships |
| **Onboarding guide** | Generated document helping developers understand a codebase |
| **Summary** | Natural-language description of a code module |
| **Provider** | Abstraction layer for LLM backends |
