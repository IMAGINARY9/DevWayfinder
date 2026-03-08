# DevWayfinder — Implementation Plan

> **Version:** 1.0.0  
> **Status:** Planning  
> **Last Updated:** 2026-03-08  
> **Authoritative Source:** This document is the single source of truth for development roadmap and milestones.

---

## 1. Overview

This document outlines the phased implementation plan for DevWayfinder. Development proceeds through multiple MVP versions, each delivering demonstrable value while building toward the complete system.

---

## 2. Product Strategy

DevWayfinder prioritizes **working software over feature breadth**. Each MVP must:

1. **Demonstrate clear value** — solve a real onboarding pain point
2. **Be fully functional** — no half-implemented features
3. **Maintain quality** — tested, documented, clean code
4. **Enable extension** — architecture supports future growth

This means each phase completes with a deployable artifact that can be demoed and evaluated.

---

## 3. MVP Versions

### 🔲 MVP 1: Core CLI & Python Analysis (Foundation)
**Goal:** Working command-line tool that analyzes Python projects and generates basic onboarding guides

**Timeline:** Week 1-3

**Deliverables:**
- Core domain models (Module, Project, DependencyGraph, OnboardingGuide)
- Python import/export extraction (regex + AST)
- Directory structure analyzer
- Basic dependency graph builder
- LLM provider abstraction with Ollama support
- Heuristic fallback summarizer
- Markdown guide generator
- CLI interface with `analyze`, `generate`, `test-model` commands
- Configuration file support (YAML)
- Cache layer for analysis results
- Basic test suite

**Success Criteria:**
- [ ] `devwayfinder generate ./python-project` produces valid Markdown guide
- [ ] Guide includes: architecture overview, module descriptions, entry points
- [ ] Works with Ollama local model
- [ ] Works without LLM (heuristic mode)
- [ ] Analysis completes in < 30s for 50-file project

### 🔲 MVP 2: Enhanced Analysis & Multi-Language
**Goal:** Richer analysis with metrics, git integration, and TypeScript support

**Timeline:** Week 4-6

**Deliverables:**
- Complexity metrics (LOC, cyclomatic complexity)
- Git history analyzer (change frequency, contributors)
- TypeScript/JavaScript analyzer
- "Start Here" recommendation algorithm
- Setup instructions detection (from build files)
- Mermaid dependency graph in output
- Configuration templates
- Tree-sitter integration (optional enhancement)
- Improved caching with incremental updates
- Extended test coverage

**Success Criteria:**
- [ ] Analyze mixed Python/TypeScript projects
- [ ] Include complexity metrics in output
- [ ] "Start Here" section with activity-based recommendations
- [ ] Dependency graph rendered as Mermaid diagram
- [ ] Incremental re-analysis on file change

### 🔲 MVP 3: VS Code Extension (Basic)
**Goal:** Bring DevWayfinder into the IDE with visual navigation

**Timeline:** Week 7-9

**Deliverables:**
- VS Code extension package
- Module tree view panel
- Dependency graph webview
- "Generate Guide" command
- Status bar integration
- Basic hover summaries
- Export guide from extension

**Success Criteria:**
- [ ] Extension installable from VSIX
- [ ] Tree view shows module structure
- [ ] Graph view navigable
- [ ] Guide generation works from command palette

### 🔲 MVP 4: Interactive Features
**Goal:** Make the extension a live onboarding companion

**Timeline:** Week 10-12

**Deliverables:**
- Editable guides catalog
- File watcher for live updates
- "Explain this module" context menu
- Custom onboarding checklists
- Template customization
- Multi-format export (HTML, PDF)

**Success Criteria:**
- [ ] Notes persist in workspace
- [ ] Live re-analysis on save
- [ ] Context menu commands work
- [ ] Checklists editable and saveable

### 🔲 MVP 5: Polish & Distribution
**Goal:** Production-ready tool for public release

**Timeline:** Week 13-15

**Deliverables:**
- VS Code marketplace publication
- PyPI package publication
- Documentation website
- Benchmark suite
- Performance optimization
- Additional language support (Rust, Go, Java)

**Success Criteria:**
- [ ] Available on VS Code Marketplace
- [ ] Installable via `pip install devwayfinder`
- [ ] Documentation site live
- [ ] Performance benchmarks published

---

## 4. MVP 1 Detailed Plan

### Phase 1.1: Project Setup ⏳
- [ ] Create project structure
- [ ] Set up pyproject.toml with dependencies
- [ ] Configure development tools (ruff, mypy, pytest)
- [ ] Initialize git repository
- [ ] Connect to GitHub remote
- [ ] Create CI/CD pipeline skeleton
- [ ] Write documentation structure (this file, ARCHITECTURE.md, etc.)

### Phase 1.2: Core Domain Models ⏳
- [ ] Implement `Module` model with Pydantic
- [ ] Implement `Project` model
- [ ] Implement `DependencyGraph` with networkx
- [ ] Implement `OnboardingGuide` and `Section` models
- [ ] Define Protocol interfaces (Analyzer, Provider, Generator)
- [ ] Implement custom exception hierarchy
- [ ] Write unit tests for all models

### Phase 1.3: Configuration System ⏳
- [ ] Implement Pydantic config schema
- [ ] Implement YAML config loader
- [ ] Support environment variable overrides
- [ ] Support CLI argument overrides
- [ ] Create example config file
- [ ] Write config validation tests

### Phase 1.4: Python Analyzer ⏳
- [ ] Implement base Analyzer abstract class
- [ ] Implement Python import extractor (AST-based)
- [ ] Implement Python export extractor
- [ ] Implement entry point detection
- [ ] Implement directory structure scanner
- [ ] Build dependency graph from imports
- [ ] Write analyzer unit tests

### Phase 1.5: LLM Providers 🔄
- [x] Implement base Provider abstract class
- [x] Implement Ollama provider with httpx
- [x] Implement OpenAI-compatible provider
- [x] Implement heuristic fallback provider
- [x] Add official OpenAI provider support
- [ ] Add retry logic with exponential backoff
- [x] Add health check functionality
- [x] Write provider tests with mocks

### Phase 1.6: Summarization Engine ⏳
- [ ] Design summarization prompt templates
- [ ] Implement SummarizationContext builder
- [ ] Implement summary caching layer
- [ ] Create module summarizer
- [ ] Create architecture summarizer
- [ ] Write summarization tests

### Phase 1.7: Guide Generator ⏳
- [ ] Implement GuideGenerator orchestrator
- [ ] Implement Markdown renderer
- [ ] Create section templates (Overview, Modules, etc.)
- [ ] Implement guide assembly logic
- [ ] Write generator tests

### Phase 1.8: CLI Interface 🔄
- [ ] Set up Typer application
- [ ] Implement `analyze` command
- [ ] Implement `generate` command
- [x] Implement `test-model` command
- [ ] Add rich progress display
- [ ] Write CLI integration tests

### Phase 1.9: Caching Layer ⏳
- [ ] Implement cache storage backend
- [ ] Implement cache key generation (content hash)
- [ ] Add cache hit/miss logging
- [ ] Create cache directory structure
- [ ] Write caching tests

### Phase 1.10: Testing & Documentation ⏳
- [ ] Achieve 80% test coverage
- [ ] Create sample test repositories
- [ ] Write usage documentation
- [ ] Create demo script
- [ ] Performance benchmarking

---

## 5. MVP 2 Detailed Plan

### Phase 2.1: Complexity Metrics ⏳
- [ ] Implement LOC counter
- [ ] Implement cyclomatic complexity calculator
- [ ] Add metrics to Module model
- [ ] Display metrics in guide output
- [ ] Write metrics tests

### Phase 2.2: Git Integration ⏳
- [ ] Implement GitPython wrapper
- [ ] Extract change frequency per file
- [ ] Extract contributor list
- [ ] Add last modified date
- [ ] Graceful handling when not a git repo
- [ ] Write git analyzer tests

### Phase 2.3: TypeScript Analyzer ⏳
- [ ] Implement TypeScript import extractor
- [ ] Implement export extractor
- [ ] Handle ES modules and CommonJS
- [ ] Add to analyzer registry
- [ ] Write TypeScript analyzer tests

### Phase 2.4: "Start Here" Algorithm ⏳
- [ ] Define recommendation scoring function
- [ ] Weight by: entry point, change frequency, connectivity
- [ ] Generate ordered list of starting files
- [ ] Add to guide output
- [ ] Write recommendation tests

### Phase 2.5: Graph Visualization ⏳
- [ ] Implement Mermaid diagram generator
- [ ] Handle large graphs (clustering)
- [ ] Optional ASCII fallback
- [ ] Include in Markdown output
- [ ] Write visualization tests

### Phase 2.6: Tree-sitter Integration (Optional) ⏳
- [ ] Add tree-sitter-python dependency
- [ ] Create Tree-sitter analyzer layer
- [ ] Fallback chain: Tree-sitter → AST → Regex
- [ ] Performance comparison
- [ ] Write Tree-sitter tests

---

## 6. Technical Debt Register

Track known issues that need future attention:

| ID | Description | Severity | Target MVP |
|----|-------------|----------|------------|
| TD-001 | No Windows path handling edge cases | Medium | MVP 1 |
| TD-002 | Large file memory consumption | Low | MVP 2 |
| TD-003 | Circular import edge cases | Medium | MVP 1 |

---

## 7. Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| 7B models produce low-quality summaries | Medium | High | Focused context, signature+docstring only |
| Tree-sitter grammars difficult to integrate | Low | Medium | Regex fallback always available |
| Performance on large repos | Medium | Medium | Incremental analysis, caching |
| VS Code extension API complexity | Medium | Medium | Start with minimal features |

---

## 8. Definition of Done

A feature/phase is considered complete when:

- [ ] Code implemented and passing all tests
- [ ] Test coverage meets minimum (80% for core modules)
- [ ] Type annotations complete (mypy passes)
- [ ] Linting passes (ruff)
- [ ] Documentation updated
- [ ] Manual testing completed
- [ ] Code reviewed (self-review minimum)
- [ ] Committed with descriptive message

---

## 9. Progress Tracking

Update this section as phases complete:

### MVP 1 Progress

| Phase | Status | Completion Date | Notes |
|-------|--------|-----------------|-------|
| 1.1 Project Setup | 🔲 Not Started | - | - |
| 1.2 Core Domain | 🔲 Not Started | - | - |
| 1.3 Configuration | 🔲 Not Started | - | - |
| 1.4 Python Analyzer | 🔲 Not Started | - | - |
| 1.5 LLM Providers | 🔄 In Progress | Base provider, Ollama, OpenAI-compatible, official OpenAI, heuristic, tests | Retry logic |
| 1.6 Summarization | 🔲 Not Started | - | - |
| 1.7 Guide Generator | 🔲 Not Started | - | - |
| 1.8 CLI Interface | 🔲 Not Started | - | - |
| 1.9 Caching Layer | 🔲 Not Started | - | - |
| 1.10 Testing & Docs | 🔲 Not Started | - | - |

**Status Legend:**
- 🔲 Not Started
- 🔄 In Progress  
- ✅ Complete
- ⏸️ Blocked
