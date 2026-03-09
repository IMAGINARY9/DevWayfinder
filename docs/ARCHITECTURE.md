# DevWayfinder — Architecture Document

> **Version:** 1.1.0  
> **Status:** Active  
> **Last Updated:** 2026-03-09  
> **Authoritative Source:** This document is the single source of truth for system architecture.

---

## 1. Overview

DevWayfinder follows a modular, layered architecture designed for extensibility, testability, and graceful degradation. The system is built around the Strategy pattern for language analysis, Adapter pattern for LLM backends, and Plugin architecture for extensibility.

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interfaces                          │
│               (CLI / VS Code Extension / Python API)            │
├─────────────────────────────────────────────────────────────────┤
│                      Orchestration Layer                         │
│           (Guide Generator, Pipeline Controller)                 │
├───────────────┬──────────────────┬──────────────────────────────┤
│   Analyzers   │   Summarizers    │         Providers            │
│  (Language    │   (LLM-based,    │  (Ollama, OpenAI-compat,     │
│   parsers,    │    Heuristic)    │   llama.cpp)                 │
│   metrics)    │                  │                              │
├───────────────┴──────────────────┴──────────────────────────────┤
│                         Core Domain                              │
│     (Module, DependencyGraph, Project, OnboardingGuide)         │
├─────────────────────────────────────────────────────────────────┤
│                      Infrastructure                              │
│       (Config, Caching, File System, Git Client, HTTP)          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Design Principles

### 2.1 Loose Coupling
- Components communicate through well-defined interfaces (Protocol classes)
- Analyzers, summarizers, and providers are pluggable
- No direct dependencies between horizontal components

### 2.2 Graceful Degradation
- System works without LLM (heuristic summaries)
- System works without Tree-sitter (Python AST + regex parsing)
- System works without Git (skip history analysis)
- Features degrade gracefully based on available capabilities
- Tree-sitter is an optional post-MVP enhancement, not a core dependency

### 2.3 Single Responsibility
- Each module handles one concern
- Analysis logic separate from summarization logic
- Provider communication isolated in adapters

### 2.4 Dependency Inversion
- High-level modules depend on abstractions
- Concrete implementations injected at runtime
- Configuration drives component selection

### 2.5 Testability First
- All components accept dependencies via constructor injection
- Pure functions where possible
- Side effects isolated to adapter boundaries

---

## 3. Package Structure

```
src/devwayfinder/
├── __init__.py              # Public API exports
├── __main__.py              # CLI entry point
├── core/                    # Domain models and interfaces
│   ├── __init__.py
│   ├── models.py            # Module, Project, DependencyEdge
│   ├── graph.py             # DependencyGraph
│   ├── guide.py             # OnboardingGuide, Section, Content
│   ├── protocols.py         # Abstract interfaces
│   └── exceptions.py        # Custom exception hierarchy
├── analyzers/               # Code analysis components
│   ├── __init__.py
│   ├── base.py              # BaseAnalyzer abstract class
│   ├── structure.py         # Directory structure analyzer
│   ├── python/              # Python-specific analyzers
│   │   ├── __init__.py
│   │   ├── imports.py       # Import extraction
│   │   └── metrics.py       # Complexity metrics
│   ├── typescript/          # TypeScript analyzers (MVP 2)
│   │   ├── __init__.py
│   │   └── imports.py       
│   ├── generic.py           # Language-agnostic fallback
│   ├── git.py               # Git history analyzer
│   └── registry.py          # Analyzer factory/registry
├── generators/              # Output generation
│   ├── __init__.py
│   ├── guide.py             # GuideGenerator orchestrator
│   ├── markdown.py          # Markdown output
│   ├── graph_viz.py         # Mermaid/ASCII graph generation
│   └── templates.py         # Template loading and rendering
├── providers/               # LLM backend adapters
│   ├── __init__.py
│   ├── base.py              # BaseProvider abstract class
│   ├── ollama.py            # Ollama local models
│   ├── openai_compat.py     # OpenAI-compatible APIs
│   ├── heuristic.py         # Non-LLM fallback
│   └── factory.py           # Provider factory
├── cli/                     # Command-line interface
│   ├── __init__.py
│   ├── app.py               # Typer application
│   ├── commands/            # Command implementations
│   │   ├── __init__.py
│   │   ├── analyze.py
│   │   ├── generate.py
│   │   ├── init.py
│   │   └── test_model.py
│   └── display.py           # Rich console output
├── config/                  # Configuration management
│   ├── __init__.py
│   ├── schema.py            # Pydantic config models
│   └── loader.py            # Config file loading
├── cache/                   # Caching layer
│   ├── __init__.py
│   ├── store.py             # Cache storage backend
│   └── keys.py              # Cache key generation
└── utils/                   # Shared utilities
    ├── __init__.py
    ├── logging.py           # Structured logging
    ├── paths.py             # Path manipulation
    └── hashing.py           # Content hashing
```

---

## 4. Core Domain Models

### 4.1 Module

```python
from pydantic import BaseModel
from pathlib import Path
from enum import Enum

class ModuleType(str, Enum):
    FILE = "file"
    DIRECTORY = "directory"
    PACKAGE = "package"

class Module(BaseModel):
    """Represents a logical code unit."""
    name: str
    path: Path
    module_type: ModuleType
    language: str | None = None
    description: str | None = None
    
    # Analysis results
    imports: list[str] = []
    exports: list[str] = []
    entry_point: bool = False
    
    # Metrics
    loc: int | None = None
    complexity: float | None = None
    
    # Git metadata
    last_modified: datetime | None = None
    contributors: list[str] = []
    change_frequency: float | None = None
```

### 4.2 DependencyGraph

```python
import networkx as nx

class DependencyGraph:
    """Directed graph of module dependencies."""
    
    def __init__(self):
        self._graph = nx.DiGraph()
    
    def add_module(self, module: Module) -> None:
        """Add a module node."""
        self._graph.add_node(module.path, module=module)
    
    def add_dependency(self, from_path: Path, to_path: Path, kind: str) -> None:
        """Add a dependency edge."""
        self._graph.add_edge(from_path, to_path, kind=kind)
    
    def get_entry_points(self) -> list[Module]:
        """Find modules with no incoming dependencies."""
        ...
    
    def get_core_modules(self, threshold: int = 5) -> list[Module]:
        """Find highly-connected modules."""
        ...
    
    def topological_order(self) -> list[Module]:
        """Return modules in dependency order."""
        ...
    
    def to_mermaid(self) -> str:
        """Export graph as Mermaid diagram."""
        ...
```

### 4.3 Project

```python
class Project(BaseModel):
    """Represents an analyzed codebase."""
    name: str
    root_path: Path
    
    # Detected configuration
    build_system: str | None = None
    package_manager: str | None = None
    primary_language: str | None = None
    
    # Content
    readme_content: str | None = None
    contributing_content: str | None = None
    
    # Analysis results
    modules: dict[Path, Module] = {}
    dependency_graph: DependencyGraph
    
    # Computed properties
    @property
    def entry_points(self) -> list[Module]:
        return [m for m in self.modules.values() if m.entry_point]
```

### 4.4 OnboardingGuide

```python
class SectionType(str, Enum):
    OVERVIEW = "overview"
    ARCHITECTURE = "architecture"
    MODULES = "modules"
    SETUP = "setup"
    START_HERE = "start_here"
    CUSTOM = "custom"

class Section(BaseModel):
    """A section of the onboarding guide."""
    section_type: SectionType
    title: str
    content: str
    subsections: list["Section"] = []
    
class OnboardingGuide(BaseModel):
    """Generated onboarding document."""
    project_name: str
    generated_at: datetime
    sections: list[Section]
    
    def to_markdown(self) -> str:
        """Render guide as Markdown."""
        ...
```

---

## 5. Component Architecture

### 5.1 Analyzer Protocol

```python
from typing import Protocol

class Analyzer(Protocol):
    """Interface for code analyzers."""
    
    @property
    def supported_languages(self) -> list[str]:
        """Languages this analyzer supports."""
        ...
    
    async def analyze(self, path: Path) -> AnalysisResult:
        """Analyze a file or directory."""
        ...
    
    def can_analyze(self, path: Path) -> bool:
        """Check if this analyzer can handle the path."""
        ...
```

### 5.2 Analyzer Layering Strategy

Analysis uses a layered approach, trying each method in order of availability and accuracy:

```
┌──────────────────────────────────────────────────────────────────┐
│  Layer 1: Language AST (Accurate, Built-in for Python)         │
│  - Python: ast module (standard library, zero dependencies)   │
│  - Extracts imports, exports, classes, functions               │
│  - Future: Tree-sitter for multi-language AST (optional)       │
├──────────────────────────────────────────────────────────────────┤
│  Layer 2: Regex Heuristics (Fast, Good Coverage)               │
│  - Pattern matching for imports/exports in any language        │
│  - Works offline, no dependencies                              │
│  - Fallback when AST unavailable for a language                │
├──────────────────────────────────────────────────────────────────┤
│  Layer 3: LLM Semantic Analysis (Universal, Slower)            │
│  - Ask model to identify relationships                        │
│  - Works for any language                                      │
│  - Requires LLM availability                                   │
├──────────────────────────────────────────────────────────────────┤
│  Layer 4: Basic Heuristics (Always Available)                  │
│  - File extension detection                                    │
│  - Directory structure inference                               │
│  - Filename pattern matching                                   │
└──────────────────────────────────────────────────────────────────┘
```

> **Architectural Decision AD-001:** Tree-sitter is deferred to post-MVP as an optional
> enhancement. Python AST + regex heuristics + LLM fallback provide sufficient accuracy
> for onboarding use cases. The `Analyzer` protocol defines stable plugin hooks for
> future specialized parsers. See [REQUIREMENTS.md](REQUIREMENTS.md) for details.

### 5.3 Provider Protocol

```python
class ModelProvider(Protocol):
    """Interface for LLM backends."""
    
    @property
    def name(self) -> str:
        """Provider identifier."""
        ...
    
    @property
    def available(self) -> bool:
        """Check if provider is accessible."""
        ...
    
    async def summarize(self, context: SummarizationContext) -> str:
        """Generate natural-language summary."""
        ...
    
    async def health_check(self) -> HealthStatus:
        """Verify provider connectivity."""
        ...
```

### 5.4 Provider Implementations

| Provider | Backend | Use Case |
|----------|---------|----------|
| `OllamaProvider` | Ollama API | Local models (Mistral, Llama) |
| `OpenAICompatProvider` | OpenAI-compatible APIs | text-generation-webui, vLLM |
| `HeuristicProvider` | No LLM | Offline fallback |

### 5.5 Generator Pipeline

```
Input: Project Path
         │
         ▼
┌─────────────────┐
│  Structure      │──► Directory tree, build system detection
│  Analysis       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Dependency     │──► Import extraction, graph building
│  Analysis       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Metrics        │──► LOC, complexity, git activity
│  Computation    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Summarization  │──► LLM or heuristic descriptions
│                 │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Guide          │──► Markdown output assembly
│  Generation     │
└────────┬────────┘
         │
         ▼
Output: OnboardingGuide (Markdown file)
```

---

## 6. Data Flow

### 6.1 Analysis Flow

```
1. User invokes: devwayfinder analyze ./my-project

2. ConfigLoader reads:
   - .devwayfinder/config.yaml (if exists)
   - CLI arguments
   - Environment variables

3. StructureAnalyzer scans:
   - Directory tree
   - Build files (pyproject.toml, package.json)
   - README, CONTRIBUTING

4. AnalyzerRegistry selects analyzers:
   - Python → PythonAnalyzer
   - TypeScript → TypeScriptAnalyzer
   - Unknown → GenericAnalyzer

5. Each analyzer processes files:
   - Extract imports/exports
   - Compute metrics
   - Return AnalysisResult

6. GraphBuilder constructs:
   - DependencyGraph from all results
   - Entry point identification
   - Cycle detection

7. Results cached:
   - Per-file hash → analysis result
   - Stored in .devwayfinder/cache/
```

### 6.2 Summarization Flow

```
1. SummarizerController receives Project

2. For each module needing summary:
   a. Check cache for existing summary
   b. If cached and file unchanged → use cache
   c. Otherwise:
      - Build SummarizationContext (signatures, docstrings, neighbors)
      - Select provider (Ollama → OpenAI → Heuristic)
      - Generate summary
      - Cache result

3. Aggregate summaries into sections

4. Template engine renders final guide
```

---

## 7. Caching Strategy

### 7.1 Cache Layers

| Layer | Key | Value | Invalidation |
|-------|-----|-------|--------------|
| File Analysis | `file_path + content_hash` | `AnalysisResult` | Content change |
| LLM Summary | `content_hash + model_id` | `str` | Content change |
| Dependency Graph | `project_root + commit_hash` | `DependencyGraph` | Git commit |
| Generated Guide | `project_hash + config_hash` | `OnboardingGuide` | Any input change |

### 7.2 Cache Storage

```
.devwayfinder/
├── cache/
│   ├── analysis/           # Per-file analysis results
│   │   ├── abc123.json     # Hash-based filenames
│   │   └── ...
│   ├── summaries/          # LLM-generated summaries
│   │   ├── def456.txt
│   │   └── ...
│   └── graphs/             # Serialized dependency graphs
│       └── main.pickle
└── config.yaml
```

---

## 8. Configuration Architecture

### 8.1 Configuration Hierarchy (Precedence: Low → High)

1. **Built-in defaults** (hardcoded)
2. **User config** (`~/.devwayfinder/config.yaml`)
3. **Project config** (`.devwayfinder/config.yaml`)
4. **Environment variables** (`DEVWAYFINDER_*`)
5. **CLI arguments** (`--model-provider ollama`)

### 8.2 Configuration Schema

```python
class ModelConfig(BaseModel):
    provider: str = "ollama"
    model_name: str = "mistral:7b"
    base_url: str = "http://localhost:11434"
    timeout: int = 120
    max_tokens: int = 512

class AnalysisConfig(BaseModel):
    include_patterns: list[str] = ["**/*.py", "**/*.ts", "**/*.js"]
    exclude_patterns: list[str] = ["**/node_modules/**", "**/.venv/**"]
    max_file_size: int = 100_000  # bytes
    enable_git_analysis: bool = True
    enable_metrics: bool = True

class OutputConfig(BaseModel):
    format: str = "markdown"
    output_path: Path | None = None
    include_graph: bool = True
    include_metrics: bool = True

class DevWayfinderConfig(BaseModel):
    model: ModelConfig = ModelConfig()
    analysis: AnalysisConfig = AnalysisConfig()
    output: OutputConfig = OutputConfig()
```

---

## 9. Extension Points

### 9.1 Adding a New Language Analyzer

1. Create `analyzers/{language}/` package
2. Implement `LanguageAnalyzer(Analyzer)` protocol
3. Register in `analyzers/registry.py`
4. Optionally add Tree-sitter grammar (post-MVP enhancement)

> **Note:** Tree-sitter integration is deferred to post-MVP. New language analyzers
> should use regex heuristics as the primary approach, with AST parsing added when
> the language's standard tooling supports it.

```python
# analyzers/rust/imports.py
class RustAnalyzer(BaseAnalyzer):
    supported_languages = ["rust"]
    
    async def analyze(self, path: Path) -> AnalysisResult:
        ...

# analyzers/registry.py
ANALYZERS: dict[str, type[Analyzer]] = {
    "python": PythonAnalyzer,
    "typescript": TypeScriptAnalyzer,
    "rust": RustAnalyzer,  # New!
}
```

### 9.2 Adding a New LLM Provider

1. Create `providers/{provider}.py`
2. Implement `ModelProvider` protocol
3. Register in `providers/factory.py`

```python
# providers/anthropic.py
class AnthropicProvider(BaseProvider):
    name = "anthropic"
    
    async def summarize(self, context: SummarizationContext) -> str:
        ...

# providers/factory.py
PROVIDERS: dict[str, type[ModelProvider]] = {
    "ollama": OllamaProvider,
    "openai": OpenAICompatProvider,
    "anthropic": AnthropicProvider,  # New!
}
```

### 9.3 Adding a New Output Format

1. Create `generators/{format}.py`
2. Implement `OutputGenerator` protocol
3. Register in CLI output options

---

## 10. Error Handling

### 10.1 Exception Hierarchy

```
DevWayfinderError (base)
├── ConfigurationError
│   ├── InvalidConfigError
│   └── MissingConfigError
├── AnalysisError
│   ├── ParsingError
│   ├── UnsupportedLanguageError
│   └── FileAccessError
├── ProviderError
│   ├── ModelUnavailableError
│   ├── ConnectionError
│   └── RateLimitError
└── GenerationError
    ├── TemplateError
    └── OutputError
```

### 10.2 Error Recovery Strategy

| Error | Recovery |
|-------|----------|
| `ParsingError` | Log warning, skip file, continue |
| `ModelUnavailableError` | Fall back to heuristic summaries |
| `ConnectionError` | Retry with backoff, then fallback |
| `RateLimitError` | Wait and retry |
| `UnsupportedLanguageError` | Use generic analyzer |

---

## 11. Security Considerations

| Concern | Mitigation |
|---------|------------|
| Code execution | Never execute analyzed code; static analysis only |
| Path traversal | Sanitize all paths; reject absolute paths outside project |
| API keys | Environment variables only; never in config files |
| Data exfiltration | Default to local models; explicit opt-in for cloud APIs |
| Large files | Size limits; skip binary files |

---

## 12. Future Architecture (VS Code Extension)

```
DevWayfinder Extension
├── Extension Host (TypeScript)
│   ├── TreeViewProvider (module tree)
│   ├── MermaidGraphProvider (dependency visualization via Markdown preview)
│   ├── HoverProvider (inline summaries)
│   └── CommandHandlers
│
├── Language Server (Python)
│   ├── Analysis Engine (shared with CLI)
│   ├── Incremental Updater
│   └── Cache Manager
│
└── Communication
    └── JSON-RPC over stdio
```

The extension reuses the same core Python analysis engine, communicating via a Language Server Protocol-style interface. This ensures consistency between CLI and extension outputs.
