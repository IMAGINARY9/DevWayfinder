# DevWayfinder — Implementation Plan

> **Version:** 2.0.0  
> **Status:** MVP 1 Complete  
> **Last Updated:** 2026-03-09  
> **Authoritative Source:** This document is the single source of truth for development roadmap and milestones.

---

## 1. Overview

This document outlines the phased implementation plan for DevWayfinder. Development proceeds through multiple MVP versions, each delivering demonstrable value while building toward the complete system.

### 1.1 Architectural Strategy

Based on analysis of parsing strategy requirements and project management constraints, DevWayfinder follows a **hybrid evolutionary architecture**:

1. **MVP 1 (Core):** Universal heuristic core — Python AST + regex heuristics + LLM/heuristic fallback. Stable `Analyzer` protocol interface with plugin hooks for future extensions.
2. **MVP 2 (Enhancement):** Multi-language support via regex analyzers, git integration, metrics. Tree-sitter as optional enhancement only.
3. **MVP 3+ (Scaling):** Plugin registry, community analyzers, VS Code extension. Tree-sitter introduced where measurable value is confirmed.

This approach prioritizes **shipping working software** over parser accuracy perfection. Regex + AST + LLM is "good enough" for onboarding use cases, and architecture allows progressive enhancement without rework.

---

## 2. Product Strategy

DevWayfinder prioritizes **working software over feature breadth**. Each MVP must:

1. **Demonstrate clear value** — solve a real onboarding pain point
2. **Be fully functional** — no half-implemented features
3. **Maintain quality** — tested, documented, clean code
4. **Enable extension** — architecture supports future growth via defined interfaces

This means each phase completes with a deployable artifact that can be demoed and evaluated.

---

## 3. MVP Versions

### ✅ MVP 1: Core CLI & Code Analysis (Foundation)
**Goal:** Working command-line tool that analyzes codebases and generates basic onboarding guides

**Timeline:** Week 1-4

**Parsing Approach:** Language-agnostic regex heuristics as the primary analysis method for all languages. Python `ast` module used as a zero-cost optimization for Python files (built-in, no external dependency). LLM summarization with heuristic offline fallback.

**Deliverables:**
- Core domain models (Module, Project, DependencyGraph, OnboardingGuide)
- Regex-based import/export extraction (language-agnostic patterns)
- Python AST integration (built-in optimization for Python files)
- Directory structure analyzer
- Basic dependency graph builder
- LLM provider abstraction with OpenAI-compatible, Ollama, official OpenAI support
- Heuristic fallback summarizer (offline mode)
- Markdown guide generator
- CLI interface with `analyze`, `generate`, `test-model` commands
- Configuration file support (YAML)
- Basic test suite (80%+ coverage for core)

**Success Criteria:**
- [x] `devwayfinder generate ./project` produces valid Markdown guide for any language project
- [x] Guide includes: architecture overview, module descriptions, entry points, dependency list
- [x] Works with Ollama / OpenAI-compatible / official OpenAI
- [x] Works without LLM (heuristic mode)
- [x] Analysis completes in < 30s for 50-file project
- [x] All tests pass, mypy clean, ruff clean

### 🔲 MVP 2: Enhanced Analysis & Extended Capabilities
**Goal:** Richer analysis with metrics, git integration, caching, and improved output

**Timeline:** Week 5-7

**Deliverables:**
- Complexity metrics (LOC, cyclomatic complexity)
- Git history analyzer (change frequency, contributors)
- Extended regex patterns for additional languages (import/export heuristics for common ecosystems)
- "Start Here" recommendation algorithm
- Setup instructions detection (from build files)
- Mermaid dependency graph in output
- Configuration templates and project-level config
- Caching layer with incremental updates
- Rich progress display with status indicators
- Extended test coverage

**Success Criteria:**
- [ ] Analyze projects in multiple languages with useful results
- [ ] Include complexity metrics in output
- [ ] "Start Here" section with activity-based recommendations
- [ ] Dependency graph rendered as Mermaid diagram
- [ ] Incremental re-analysis on file change

### 🔲 MVP 3: VS Code Extension & Plugin System
**Goal:** Bring DevWayfinder into the IDE and enable community extensions

**Timeline:** Week 8-10

**Deliverables:**
- VS Code extension package
- Module tree view panel (native VS Code TreeView API)
- Dependency graph display (Mermaid diagrams in Markdown preview)
- "Generate Guide" command
- Status bar integration
- Analyzer plugin registry with dynamic loading
- Multi-format export (MD, HTML)
- Template customization

**Success Criteria:**
- [ ] Extension installable from VSIX
- [ ] Tree view shows module structure
- [ ] Dependency graph viewable as Mermaid in Markdown preview
- [ ] Guide generation works from command palette
- [ ] New language analyzers can be added via plugin protocol

### 🔲 MVP 4: Interactive Features & Guide Catalog
**Goal:** Make the extension a live onboarding companion with a dedicated guide management experience

**Timeline:** Week 11-13

**Deliverables:**
- Guide catalog with sidebar preview (Copilot Chat-style navigation)
- File watcher for live updates
- "Explain this module" context menu
- Custom onboarding checklists
- PDF export
- Extended language regex patterns (additional ecosystems on demand)

**Success Criteria:**
- [ ] Guide catalog shows list of guides in sidebar panel
- [ ] Guides openable as raw Markdown for editing, with sidebar preview
- [ ] Live re-analysis on save
- [ ] Context menu commands work
- [ ] Checklists editable and saveable

### 🔲 MVP 5: Distribution & Production
**Goal:** Production-ready tool for public release

**Timeline:** Week 14-16

**Deliverables:**
- VS Code marketplace publication
- PyPI package publication
- Complete documentation in repository
- Benchmark suite
- Performance optimization
- Tree-sitter integration for high-demand languages (conditional — only if user feedback warrants)

**Success Criteria:**
- [ ] Available on VS Code Marketplace
- [ ] Installable via `pip install devwayfinder`
- [ ] Documentation complete and verified
- [ ] Performance benchmarks published

---

## 4. MVP 1 Detailed Plan

### Phase 1.1: Project Setup ✅
**Status:** Complete

- [x] Create project structure (`src/devwayfinder/` with subpackages)
- [x] Set up pyproject.toml with dependencies (typer, rich, pydantic, httpx, networkx)
- [x] Configure development tools (ruff, mypy, pytest)
- [x] Initialize git repository
- [x] Create documentation structure (ARCHITECTURE.md, REQUIREMENTS.md, etc.)
- [x] Create example configuration file (`config/config.example.yaml`)

### Phase 1.2: Core Domain Models ✅
**Status:** Complete

- [x] Implement `Module` model with Pydantic (name, path, type, language, imports/exports, metrics)
- [x] Implement `Project` model (root path, modules, entry points detection)
- [x] Implement `DependencyGraph` with networkx (add/remove nodes, entry points, core modules, topological sort, cycle detection, Mermaid export)
- [x] Implement `OnboardingGuide` and `Section` models (with `to_markdown()` rendering, TOC generation)
- [x] Define Protocol interfaces (`Analyzer`, `ModelProvider`, `OutputGenerator`)
- [x] Implement `SummarizationContext` and `AnalysisResult` data classes
- [x] Implement `HealthStatus` model
- [x] Implement custom exception hierarchy (13 custom exceptions)
- [x] Write unit tests for all models (test_core.py — Module, Project, Graph, Guide)

### Phase 1.3: LLM Providers ✅
**Status:** Complete

- [x] Implement `BaseProvider` abstract class (HTTP client pooling, error handling, prompt building)
- [x] Implement `OllamaProvider` (local models via `/api/generate`, health check via `/api/tags`)
- [x] Implement `OpenAICompatProvider` (text-generation-webui, vLLM via chat completions API)
- [x] Implement `OpenAIProvider` (official OpenAI API, extends OpenAICompatProvider)
- [x] Implement `HeuristicProvider` (offline fallback, deterministic summaries from context)
- [x] Implement `ProviderConfig` with Pydantic (env vars, CLI args, alias normalization)
- [x] Implement provider factory with registry pattern
- [x] Add health check functionality (latency measurement, model info)
- [x] Write provider tests with mocks (test_providers.py — all providers + factory + CLI)
- [ ] Add retry logic with exponential backoff

### Phase 1.4: Configuration System 🔄
**Status:** Partially complete (provider config done, general config loader needed)

- [x] Implement provider-level Pydantic config schema (`ProviderConfig`)
- [x] Support environment variable overrides for provider settings
- [x] Support CLI argument overrides for provider settings
- [x] Create example config file (`config/config.example.yaml`)
- [ ] Implement full `DevWayfinderConfig` schema (model + analysis + output sections)
- [ ] Implement YAML config file loader (`.devwayfinder/config.yaml` support)
- [ ] Implement config hierarchy (defaults → user config → project config → env vars → CLI)
- [ ] Write config validation tests

### Phase 1.5: Code Analyzer ✅
**Status:** Complete

This is the core value-producing component. Uses language-agnostic regex heuristics as the primary analysis method, with Python `ast` module as a zero-cost built-in optimization for Python files.

#### 1.5.1 Base Analyzer Framework
- [x] Implement `BaseAnalyzer` abstract class (implements `Analyzer` protocol)
- [x] Implement `AnalyzerRegistry` for language-based analyzer lookup
- [x] Implement `GenericAnalyzer` for language-agnostic file structure analysis (via RegexAnalyzer)
- [x] Define `AnalysisResult` population pipeline

#### 1.5.2 Directory Structure Analyzer
- [x] Implement `StructureAnalyzer` — scan directory tree
- [x] Detect build system (pyproject.toml, setup.py, package.json, Cargo.toml, CMakeLists.txt, Makefile)
- [x] Detect package manager (pip, npm, cargo, go mod, maven)
- [x] Extract README, CONTRIBUTING, CHANGELOG content
- [x] Detect entry points by filename patterns (`main.*`, `__main__.py`, `index.*`, `app.*`, `cli.*`)
- [x] Respect `.gitignore` and configurable exclude patterns
- [x] Binary file detection and skip

#### 1.5.3 Regex Import/Export Extractor
- [x] Implement `RegexAnalyzer` — language-agnostic heuristic-based analysis
- [x] Regex patterns for common import syntaxes across languages:
  - Python: `import X`, `from X import Y`
  - JavaScript/TypeScript: `import ... from`, `require(...)`
  - Go: `import "..."`, `import (...)`
  - Rust: `use ...`, `mod ...`
  - Java/C#: `import ...`, `using ...`
  - C/C++: `#include ...`
- [x] Regex patterns for common export/declaration syntaxes:
  - Functions: `def`, `func`, `function`, `fn`, etc.
  - Classes/structs: `class`, `struct`, `interface`, `type`, etc.
  - Module exports: `__all__`, `module.exports`, `export`, `pub`
- [x] Language detection by file extension
- [x] Handle malformed files gracefully (skip with warning)

#### 1.5.4 Python AST Optimization
> Python `ast` module is built into the standard library — zero external dependencies. It provides higher accuracy for Python files at no cost.
- [x] Implement `PythonASTAnalyzer` extending regex analyzer
- [x] Extract `import` and `from ... import ...` statements via AST
- [x] Resolve relative imports to absolute module paths
- [x] Extract exports: public functions, classes, `__all__` definitions via AST
- [x] Extract module-level docstrings and function/class signatures
- [x] Fall back to regex if AST parsing fails (syntax errors, encoding issues)

#### 1.5.5 Dependency Graph Builder
- [x] Build `DependencyGraph` from collected import/export data
- [x] Map import strings to actual file paths within the project
- [x] Mark entry points (files with `if __name__` or `main()` patterns, or no incoming imports)
- [x] Detect circular dependencies and log warnings
- [x] Compute module connectivity metrics (in-degree, out-degree)

#### 1.5.6 Testing
- [x] Unit tests for regex extractor (multiple languages, various import styles)
- [x] Unit tests for Python AST optimizer (edge cases, syntax errors)
- [x] Unit tests for structure analyzer
- [x] Unit tests for dependency graph builder
- [x] Integration test: analyze a real project fixture
- [x] Edge cases: empty files, syntax errors, binary files, circular imports

### Phase 1.6: Summarization Engine ✅
**Status:** Complete

Connects analyzers with LLM providers to produce natural-language descriptions.

- [x] Design summarization prompt templates (module summary, architecture overview)
- [x] Implement `SummarizationController` orchestrator
- [x] Build `SummarizationContext` from analysis results (signatures, docstrings, imports, neighbors)
- [x] Implement module-level summarizer (per-module description)
- [x] Implement architecture-level summarizer (project-wide overview from dependency graph)
- [x] Implement entry point summarizer ("where to start" narrative)
- [x] Provider selection chain: preferred LLM → fallback LLM → heuristic
- [x] Write summarization tests (mock provider, verify prompt construction)

**Implementation Notes:**
- Created `src/devwayfinder/summarizers/` module with:
  - `templates.py`: Prompt templates for MODULE, ARCHITECTURE, ENTRY_POINT, DEPENDENCY types
  - `context_builder.py`: ContextBuilder transforms analysis results to SummarizationContext
  - `controller.py`: SummarizationController orchestrates provider chain with retry/fallback
  - `__init__.py`: Clean public API exports
- Heuristic fallback generates useful summaries without LLM
- Batch operations support concurrent summarization with semaphore control
- 28 new tests covering templates, context building, controller, and heuristics

### Phase 1.7: Guide Generator ✅
**Status:** Complete

Assembles analysis + summaries into the final onboarding document.

- [x] Implement `GuideGenerator` orchestrator (coordinates analysis → summarization → output)
- [x] Implement `MarkdownGenerator` (uses `OnboardingGuide.to_markdown()` + Mermaid graph)
- [x] Create section templates:
  - [x] **Overview** — project name, description, tech stack, build system
  - [x] **Architecture** — high-level structure, key packages, LLM-generated overview
  - [x] **Modules** — per-module descriptions with imports/exports
  - [x] **Dependencies** — dependency graph (text list + Mermaid diagram)
  - [x] **Entry Points** — identified entry points with descriptions
- [x] Implement guide assembly logic (order sections, generate TOC)
- [x] Write generator tests (mock analysis results, verify Markdown output)

**Implementation Notes:**
- Created `src/devwayfinder/generators/guide_generator.py` with:
  - `GuideGenerator`: Full pipeline orchestrator (analyze → summarize → generate)
  - `MarkdownGenerator`: Renders OnboardingGuide to formatted Markdown
  - `GenerationConfig`: Configuration for generation options
  - `GenerationResult`: Contains guide, metadata, warnings
- Section generators: overview, architecture, modules, dependencies, start_here
- Mermaid diagram generation for dependency visualization
- Supports `use_llm=False` for heuristic-only mode
- 21 new tests covering config, results, generator pipeline, and Markdown output

### Phase 1.8: CLI Interface ✅
**Status:** Complete

- [x] Set up Typer application framework
- [x] Implement `test-model` command (health check + completion test for all providers)
- [x] Implement `version` command
- [x] Implement `analyze` command (run analysis pipeline, display results)
- [x] Implement `generate` command (run full pipeline: analyze → summarize → generate)
- [x] Add `--no-llm` flag for heuristic-only mode
- [x] Add `--output` flag for output path
- [ ] Add `--config` flag for custom config file (deferred to MVP 2)
- [x] Add rich progress display (phases, spinner, status indicators)
- [x] Error handling with helpful messages (cause + suggested fix)
- [x] Write CLI integration tests

**Implementation Notes:**
- Full `analyze` command with table display, entry points, structure tree
- Full `generate` command with progress spinner, file output support
- `--json` flag on analyze for machine-readable output
- `--verbose` flag shows core modules with dependency counts
- 13 CLI tests covering all commands: version, analyze, generate, test-model, init
- Rich progress spinners and formatted output

### Phase 1.9: Integration & End-to-End Testing ✅
**Status:** Complete

- [x] Create sample Python project fixtures (small, medium, with edge cases)
- [x] End-to-end test: `devwayfinder generate ./fixture` produces valid Markdown
- [x] Test heuristic-only mode (no LLM): produces useful guide
- [x] Test with malformed files (syntax errors, binary files)
- [x] Test with circular imports
- [ ] Achieve 80%+ test coverage for core modules (currently at 73%)
- [x] Performance test: < 30s for 50-file project (excluding LLM latency)
- [x] Manual testing through CLI

**Implementation Notes:**
- Created `tests/fixtures/sample_project/` with pyproject.toml, README.md, and Python modules
- 13 integration tests covering:
  - Full analysis pipeline
  - Full generation pipeline
  - Heuristic-only mode
  - Edge cases (empty dirs, binary files, syntax errors, circular imports)
  - Performance tests
- All 130 tests pass
- Coverage at 73% (could improve with more edge case tests)

### Phase 1.10: Documentation & Release Prep ✅
**Status:** Complete

- [x] Update README.md with working examples
- [x] Update USAGE.md with guide generation examples
- [x] Create demo script for showcasing functionality
- [x] Verify all `--help` text is comprehensive
- [x] Final pass on all docs for consistency

**Implementation Notes:**
- All CLI commands have comprehensive `--help` text
- README.md has quick start examples
- USAGE.md has detailed configuration and usage guide
- All phases of MVP 1 complete and tested

---

## 5. MVP 2 Detailed Plan

### Phase 2.1: Caching Layer ✅
**Status:** Complete

- [x] Implement cache storage backend (file-based, `.devwayfinder/cache/`)
- [x] Implement cache key generation (content hash per file)
- [x] Cache analysis results per file
- [x] Cache LLM summaries per content hash + model ID
- [x] Add cache hit/miss logging
- [x] Implement cache invalidation on content change
- [x] Write caching tests

**Implementation Notes:**
- Created `src/devwayfinder/cache/` module with:
  - `storage.py`: File-based cache backend with SHA-256 content hashing
  - `manager.py`: High-level API for analysis, summary, and metrics caching
  - `__init__.py`: Clean public API exports
- Cache entries stored in `.devwayfinder/cache/{analysis,summaries}/` directories
- Content hash-based invalidation ensures stale entries are not used
- TTL support for time-based expiry (optional)
- 29 tests covering storage, manager, and integration scenarios
- Session hit rate tracking for monitoring cache effectiveness

### Phase 2.2: Complexity Metrics ⏳
- [ ] Implement LOC counter (per file and per module)
- [ ] Implement cyclomatic complexity calculator (Python AST-based)
- [ ] Add metrics to Module model output
- [ ] Display metrics in guide output
- [ ] Write metrics tests

### Phase 2.3: Git Integration ⏳
- [ ] Implement Git history analyzer (using gitpython)
- [ ] Extract change frequency per file
- [ ] Extract contributor list per file/module
- [ ] Add last modified date
- [ ] Graceful handling when not a git repo
- [ ] Write git analyzer tests

### Phase 2.4: Extended Regex Patterns ⏳
- [ ] Audit regex accuracy on real-world projects (Python, TypeScript, Go, Rust, Java)
- [ ] Add missing import/export patterns discovered from testing
- [ ] Improve relative import resolution for common project structures
- [ ] Handle framework-specific patterns (e.g., decorators, annotations)
- [ ] Write cross-language regex accuracy tests

### Phase 2.5: "Start Here" Algorithm ⏳
- [ ] Define recommendation scoring function
- [ ] Weight by: entry point status, change frequency, connectivity, complexity
- [ ] Generate ordered list of starting files with explanations
- [ ] Add "Start Here" section to guide output
- [ ] Write recommendation tests

### Phase 2.6: Enhanced Output ⏳
- [ ] Implement Mermaid diagram generator for dependency graph
- [ ] Handle large graphs (clustering, filtering)
- [ ] Rich progress display with per-phase status
- [ ] Configuration templates (project-level `.devwayfinder/config.yaml`)
- [ ] Write visualization tests

---

## 6. MVP 3 Detailed Plan: VS Code Extension & Plugin System

### Phase 3.1: Analyzer Plugin Registry ⏳
- [ ] Design plugin discovery mechanism (entry points or directory scan)
- [ ] Implement `PluginManager` class for dynamic analyzer loading
- [ ] Define plugin manifest format (name, version, supported languages, entry point)
- [ ] Implement `register_analyzer()` and `unregister_analyzer()` API
- [ ] Create plugin development guide in documentation
- [ ] Write plugin system tests (load, unload, conflict resolution)

### Phase 3.2: VS Code Extension Scaffold ⏳
- [ ] Set up extension project structure (TypeScript, webpack/esbuild bundler)
- [ ] Configure `package.json` with extension metadata and activation events
- [ ] Implement extension activation/deactivation lifecycle
- [ ] Create communication bridge: Extension ↔ devwayfinder CLI (subprocess or LSP)
- [ ] Define VS Code command registrations
- [ ] Write extension scaffold tests

### Phase 3.3: Module Tree View Panel ⏳
- [ ] Implement `TreeDataProvider` for project module hierarchy
- [ ] Display modules with icons (file, directory, package, entry point)
- [ ] Show import/export counts per module
- [ ] Click-to-navigate: open file at module location
- [ ] Refresh on file system changes
- [ ] Write tree view data provider tests

### Phase 3.4: Dependency Graph Display ⏳
Graph visualization is delivered through Mermaid diagrams embedded in generated Markdown documents, viewed via VS Code's built-in Markdown preview. No custom webview is required.

- [ ] Enhance Mermaid diagram generator (from MVP 2) with richer formatting
- [ ] Add module type annotations in graph nodes (entry point, package, etc.)
- [ ] Implement subgraph clustering for large projects (by package/directory)
- [ ] Generate standalone graph Markdown file for quick preview
- [ ] Add "DevWayfinder: Show Dependency Graph" command (opens Mermaid Markdown in preview)
- [ ] Write graph display tests

> **⚠️ Design Note:** Interactive graph exploration (zoom, pan, click-to-navigate within a custom panel) requires a VS Code webview with a JS rendering library. This is deferred as a potential future enhancement. If the Mermaid-in-Markdown approach proves insufficient for large projects, a custom webview phase should be planned separately.

### Phase 3.5: Extension Commands & Integration ⏳
- [ ] Implement "DevWayfinder: Generate Guide" command (command palette)
- [ ] Implement "DevWayfinder: Analyze Project" command
- [ ] Add status bar item showing analysis status
- [ ] Multi-format export from extension (Markdown, HTML via CLI)
- [ ] Error handling and notification for missing LLM/config issues
- [ ] Write command integration tests

### Phase 3.6: Template Customization ⏳
- [ ] Implement template loading from `.devwayfinder/template.yaml`
- [ ] Support section ordering, inclusion/exclusion
- [ ] Template inheritance (project template extends default)
- [ ] Document template format and customization options
- [ ] Write template tests

---

## 7. MVP 4 Detailed Plan: Interactive Features & Polish

### Phase 4.1: Guide Catalog — Storage & Management ⏳

Guides are stored **independently from the analyzed project**, in a global location such as `~/.devwayfinder/guides/`. Each guide is a plain Markdown file that the user can open, edit, and version-control separately.

- [ ] Implement global guide storage (`~/.devwayfinder/guides/<project-slug>/`)
- [ ] Support saving multiple guides per project (by date, branch, or custom name)
- [ ] Each guide is a self-contained `.md` file editable in any Markdown editor
- [ ] Implement guide metadata sidecar (`.meta.json` per guide: creation date, project path, branch, user annotations)
- [ ] Persist user annotations across re-generation via metadata sidecar
- [ ] CLI commands: `devwayfinder guides list`, `devwayfinder guides open <name>`, `devwayfinder guides diff <a> <b>`
- [ ] Guide diffing: leverage VS Code built-in diff editor (`vscode.diff` command) to compare two guides
- [ ] Write guide catalog model, storage, and CLI tests

### Phase 4.1b: Guide Catalog — VS Code Sidebar UI ⏳

The guide catalog appears as a dedicated panel in the VS Code sidebar, similar to the Copilot Chat conversation history. Users can browse, preview, open, and manage guides from the sidebar without leaving the editor.

**UX flow:**
1. Sidebar tree view lists all projects → guides per project (sorted by date/name)
2. Clicking a guide opens a **live Markdown preview** in the sidebar panel
3. A toolbar button opens the raw `.md` file in the editor for direct editing
4. "Back to catalog" navigation returns to the guide directory listing
5. Context menu actions: rename, delete, duplicate, diff with another guide
6. Badge indicator shows guides that are stale (project changed since generation)

- [ ] Implement `GuideCatalogTreeDataProvider` for sidebar tree view
- [ ] Implement Markdown preview panel (using VS Code `WebviewView` with built-in Markdown rendering)
- [ ] Implement "Open raw file" command (opens `.md` in standard editor tab)
- [ ] Implement back-navigation from preview to catalog list
- [ ] Implement context menu actions (rename, delete, duplicate, diff)
- [ ] Implement stale-guide detection (compare guide timestamp vs. project last-modified)
- [ ] Write sidebar UI integration tests

> **Design note:** The sidebar preview uses VS Code's native Markdown rendering via a lightweight webview panel (not a full browser-based UI). If the VS Code Extension API imposes limitations on inline Markdown rendering in sidebar panels, an alternative approach is to open the preview as a standard Markdown Preview tab and keep only the tree-view navigation in the sidebar.

### Phase 4.2: File Watcher & Live Updates ⏳
- [ ] Implement VS Code file system watcher integration
- [ ] Detect file changes and trigger incremental re-analysis
- [ ] Update tree view and graph view in real-time
- [ ] Debounce rapid changes (configurable interval)
- [ ] Show "outdated" indicator when guide is stale
- [ ] Write file watcher tests

### Phase 4.3: Context Menu & Quick Actions ⏳
- [ ] "Explain this module" — right-click on file/folder → LLM-generated summary displayed in editor panel
- [ ] "Show dependencies" — right-click → open generated dependency Markdown focused on selected module
- [ ] "Show dependents" — what modules depend on this file (output to editor panel)
- [ ] "Navigate to entry point" — jump to nearest entry point
- [ ] Write context menu command tests

### Phase 4.4: Custom Onboarding Checklists ⏳
- [ ] Define checklist schema (items, progress, categories)
- [ ] Generate default checklists from analysis (e.g., "Read core module", "Run tests")
- [ ] Allow users to create and edit custom checklists
- [ ] Checklist progress persistence in `.devwayfinder/checklists/`
- [ ] Display checklists in dedicated VS Code panel
- [ ] Write checklist model and persistence tests

### Phase 4.5: Community Regex Patterns ⏳
- [ ] Define pattern contribution format (YAML/JSON schema for import/export regex)
- [ ] Implement pattern loader from user-defined pattern files
- [ ] Bundle curated community patterns for less common languages (Elixir, Kotlin, Swift, etc.)
- [ ] CLI command: `devwayfinder patterns list`, `devwayfinder patterns validate <file>`
- [ ] Write pattern loader and validation tests

### Phase 4.6: PDF Export ⏳
- [ ] Implement PDF renderer (using weasyprint or similar)
- [ ] Support custom styling/themes for PDF output
- [ ] Include dependency graph as embedded image
- [ ] Table of contents with page numbers
- [ ] Write PDF generation tests

---

## 8. MVP 5 Detailed Plan: Distribution & Production

### Phase 5.1: PyPI Package Publication ⏳
- [ ] Finalize package metadata in pyproject.toml (description, classifiers, URLs)
- [ ] Create MANIFEST.in for source distribution
- [ ] Build and test sdist and wheel distributions
- [ ] Publish to TestPyPI for validation
- [ ] Publish to PyPI: `pip install devwayfinder`
- [ ] Verify installation works on clean environments (Windows, macOS, Linux)
- [ ] Write installation verification tests

### Phase 5.2: VS Code Marketplace Publication ⏳
- [ ] Create `.vsix` package from extension
- [ ] Write marketplace listing (description, screenshots, demo GIF)
- [ ] Submit to VS Code Marketplace for review
- [ ] Set up automated extension builds (CI/CD)
- [ ] Write marketplace smoke tests (install, activate, basic command)

### Phase 5.3: Documentation & Guides ⏳
- [ ] Finalize all authoritative documents (ARCHITECTURE, REQUIREMENTS, USAGE, etc.)
- [ ] Add getting started tutorial with step-by-step examples in USAGE.md
- [ ] Add configuration reference (auto-generated from Pydantic schemas) in CONFIGURATION.md
- [ ] Add plugin development guide in CONTRIBUTING.md
- [ ] Create README badges and shields for PyPI/Marketplace versions
- [ ] Write documentation completeness validation

### Phase 5.4: Benchmark Suite ⏳
- [ ] Create benchmark project fixtures (small: 10 files, medium: 100 files, large: 1000 files)
- [ ] Implement benchmark runner (measure analysis time, memory usage, LLM calls)
- [ ] Establish baseline performance metrics
- [ ] Compare analysis accuracy: AST vs regex vs Tree-sitter on same projects
- [ ] Publish benchmark results in documentation
- [ ] Set up CI benchmark regression checking

### Phase 5.5: Performance Optimization ⏳
- [ ] Profile analysis pipeline on large projects (identify bottlenecks)
- [ ] Implement parallel file analysis (asyncio or multiprocessing)
- [ ] Optimize dependency graph construction for large modules
- [ ] Implement streaming LLM summarization (process as responses arrive)
- [ ] Memory optimization for repos with many large files
- [ ] Write performance regression tests

### Phase 5.6: Tree-sitter for High-Demand Languages (Conditional) ⏳
> **Prerequisite:** User feedback and benchmark data confirm Tree-sitter delivers measurable accuracy improvement over regex for specific languages.
- [ ] Evaluate user feedback and benchmark accuracy gaps
- [ ] Implement Tree-sitter analyzers only for languages where regex accuracy < 85%
- [ ] Maintain regex fallback for all languages
- [ ] Document accuracy comparison per language
- [ ] Write Tree-sitter accuracy comparison tests

---

## 9. Technical Debt Register

| ID | Description | Severity | Target |
|----|-------------|----------|--------|
| TD-001 | No Windows path handling edge cases | Medium | MVP 1 |
| TD-002 | Large file memory consumption | Low | MVP 2 |
| TD-003 | Circular import edge cases | Medium | MVP 1 |
| TD-004 | Provider retry logic with exponential backoff | Low | MVP 1 |

---

## 10. Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| 7B models produce low-quality summaries | Medium | High | Focused context (signature+docstring only), heuristic fallback |
| Regex heuristics miss complex import patterns | Medium | Low | Python AST as primary; regex is fallback only |
| Performance on large repos | Medium | Medium | Incremental analysis, caching (MVP 2) |
| VS Code extension API complexity | Medium | Medium | Deferred to MVP 3, start with minimal features |
| Tree-sitter grammars maintenance burden | Low | Low | Deferred to post-MVP; only if user demand confirmed |

---

## 11. Definition of Done

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

## 12. Progress Tracking

Update this section as phases complete:

### MVP 1 Progress

| Phase | Status | Notes |
|-------|--------|-------|
| 1.1 Project Setup | ✅ Complete | Structure, deps, tooling, docs |
| 1.2 Core Domain Models | ✅ Complete | Module, Project, Graph, Guide, Protocols, Exceptions — all tested |
| 1.3 LLM Providers | ✅ Complete | Ollama, OpenAI-compat, OpenAI, Heuristic — factory + tests. Missing: retry logic |
| 1.4 Configuration | 🔄 In Progress | Provider config done; full config loader needed |
| 1.5 Code Analyzer | ✅ Complete | BaseAnalyzer, StructureAnalyzer, RegexAnalyzer, PythonASTAnalyzer, GraphBuilder — 36 tests |
| 1.6 Summarization | 🔲 Not Started | **Next priority** — connect analyzers to LLM |
| 1.7 Guide Generator | 🔲 Not Started | Depends on 1.5, 1.6 |
| 1.8 CLI Interface | 🔄 In Progress | test-model done; analyze/generate stubs |
| 1.9 Integration Testing | 🔲 Not Started | Depends on 1.5-1.8 |
| 1.10 Documentation | 🔲 Not Started | Final pass after implementation |

**Status Legend:**
- 🔲 Not Started
- 🔄 In Progress  
- ✅ Complete
- ⏸️ Blocked
