# Contributing to DevWayfinder

> **Version:** 1.0.0  
> **Status:** Active  
> **Last Updated:** 2026-03-24  
> **Authoritative Source:** This document is the single source of truth for development practices and code quality standards.

---

## Table of Contents

1. [Documentation Hygiene Rules](#documentation-hygiene-rules)
2. [Code Quality Requirements](#code-quality-requirements)
3. [Architecture Principles](#architecture-principles)
4. [Development Workflow](#development-workflow)
5. [Testing Standards](#testing-standards)
6. [Development Requirements](#development-requirements)

---

## Documentation Hygiene Rules

### Single Source of Truth Principle

> **Every piece of information has exactly ONE authoritative location.**

Duplication creates drift. Instead of repeating information, **reference the canonical source**.

### Authoritative Sources Table

| Topic | Authoritative Document | DO NOT document elsewhere |
|-------|----------------------|---------------------------|
| System architecture, components, data flow | [ARCHITECTURE.md](ARCHITECTURE.md) | ❌ README, code comments |
| Functional & non-functional requirements | [REQUIREMENTS.md](REQUIREMENTS.md) | ❌ Implementation plan, issues |
| MVP roadmap, milestones, task breakdown | [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | ❌ README, project boards |
| Configuration options, templates | [CONFIGURATION.md](CONFIGURATION.md) | ❌ Code comments, README |
| Development rules, coding standards | **CONTRIBUTING.md** (this file) | ❌ README, Wiki |
| Local LLM setup, model providers | [USAGE.md](USAGE.md) | ❌ README, config files |

### Documentation Update Rules

1. **Before adding information**: Check if it belongs in an existing authoritative document
2. **When updating**: Update ONLY the authoritative source; remove any stale duplicates
3. **Cross-referencing**: Use relative links to the authoritative document, never copy text
4. **Code comments**: Document "why", not "what" — implementation details live in code, not docs
5. **Keep in sync**: When completing an MVP phase, immediately update IMPLEMENTATION_PLAN.md

### Document Maintenance Checklist

When modifying any authoritative document:
- [ ] Update the "Last Updated" timestamp
- [ ] Verify cross-references still resolve
- [ ] Remove any obsolete sections
- [ ] Ensure no information is duplicated from other authoritative docs

---

## Code Quality Requirements

### Proactive Improvement Mandate

> **If potential problems or architectural limitations are discovered during development, improve them immediately to ensure stability and reliability.**

Do not defer technical debt. If you see:
- Code that could cause future bugs → Fix it now
- Architectural patterns that won't scale → Refactor now
- Missing abstractions → Add them now
- Performance bottlenecks → Address them proactively

### Code Standards

#### 1. Patterns & Abstraction

| Principle | Implementation |
|-----------|----------------|
| **DRY (Don't Repeat Yourself)** | Extract common logic into utilities or base classes |
| **Single Responsibility** | Each module/class does ONE thing well |
| **Interface-First Design** | Define abstract interfaces before implementations |
| **Factory Pattern** | Use factories for creating analyzers, generators, providers |
| **Strategy Pattern** | Swap analysis/generation algorithms without changing client code |
| **Adapter Pattern** | Wrap external dependencies (LLM, parsers) behind stable interfaces |
| **Dependency Injection** | Pass dependencies explicitly; avoid global state |
| **Plugin Architecture** | Enable adding new languages/analyzers without modifying core |

#### 2. Type Safety

**Python (Backend/CLI)**
```python
# ✅ GOOD: Full type annotations with Pydantic
from pydantic import BaseModel
from typing import Protocol, Optional, List
from pathlib import Path

class ModuleSummary(BaseModel):
    name: str
    path: Path
    description: str
    complexity: float
    dependencies: List[str]
    
class Analyzer(Protocol):
    """Abstract interface for code analyzers."""
    async def analyze(self, path: Path) -> AnalysisResult:
        ...

def summarize_module(
    module: ModuleSummary, 
    config: SummarizerConfig
) -> str:
    ...

# ❌ BAD: No types, unclear contracts
def analyze(data, opts):
    ...
```

**TypeScript (VS Code Extension)**
```typescript
// ✅ GOOD: Strict types, discriminated unions
interface ModuleNode {
    type: 'module';
    name: string;
    path: string;
    children: ModuleNode[];
}

interface DependencyEdge {
    type: 'dependency';
    from: string;
    to: string;
    kind: 'import' | 'require' | 'dynamic';
}

type GraphElement = ModuleNode | DependencyEdge;

// ❌ BAD: any, unknown, untyped
const analyze = (data: any) => { ... }
```

#### 3. Optimal Data Structures

| Use Case | Data Structure | Why |
|----------|----------------|-----|
| File path lookup | `dict[Path, Module]` | O(1) access by path |
| Dependency graph | `networkx.DiGraph` | Built-in graph algorithms |
| Module registry | `dict[str, Type[Analyzer]]` | Factory pattern support |
| LRU summaries cache | `functools.lru_cache` / `cachetools.LRUCache` | Bounded memory, auto-eviction |
| File change tracking | `set[Path]` | O(1) membership test |
| Ordered results | `list[T]` | Preserve insertion order |

#### 4. Error Handling

```python
# ✅ GOOD: Specific exceptions, clear recovery
class DevWayfinderError(Exception):
    """Base exception for all DevWayfinder errors."""
    pass

class ParsingError(DevWayfinderError):
    """Raised when code parsing fails."""
    def __init__(self, path: Path, language: str, reason: str):
        self.path = path
        self.language = language
        self.reason = reason
        super().__init__(f"Failed to parse {path} as {language}: {reason}")

class ModelUnavailableError(DevWayfinderError):
    """Raised when LLM provider is not accessible."""
    def __init__(self, provider: str, fallback_used: bool = False):
        self.provider = provider
        self.fallback_used = fallback_used
        super().__init__(f"Model provider '{provider}' unavailable")

# Use context managers for resource cleanup
async with aiofiles.open(path) as f:
    content = await f.read()

# ❌ BAD: Bare except, swallowing errors
try:
    result = analyze()
except:
    pass  # Silent failure
```

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Python modules | `snake_case` | `dependency_analyzer.py` |
| Python classes | `PascalCase` | `DependencyGraph` |
| Python functions/vars | `snake_case` | `extract_imports()` |
| TypeScript files | `camelCase.ts` | `graphPanel.ts` |
| TypeScript classes | `PascalCase` | `OnboardingTreeProvider` |
| Constants | `SCREAMING_SNAKE_CASE` | `MAX_FILE_SIZE` |
| Config keys | `snake_case` | `model_provider` |
| CLI commands | `kebab-case` | `generate-guide` |

---

## Architecture Principles

### 1. Loose Coupling

Components communicate through well-defined interfaces, not internal implementation details.

```python
# ✅ GOOD: Interface-based design
from abc import ABC, abstractmethod

class Summarizer(ABC):
    @abstractmethod
    async def summarize(self, context: ModuleContext) -> str:
        ...

class LLMSummarizer(Summarizer):
    def __init__(self, provider: ModelProvider):  # Injected dependency
        self.provider = provider

    async def summarize(self, context: ModuleContext) -> str:
        ...

# ❌ BAD: Hard-coded dependencies, tight coupling
class LLMSummarizer:
    def __init__(self):
        self.client = OpenAI(api_key="...")  # Hard-coded!
```

### 2. Testability

Every component must be testable in isolation.

| Requirement | Implementation |
|-------------|----------------|
| No global state | Pass all dependencies explicitly |
| Mockable external services | Use interfaces for LLM, file system, git |
| Deterministic tests | Seed random generators, fix timestamps |
| Fast unit tests | No network/LLM calls in unit tests (use mocks/fixtures) |

### 3. Extensibility

Adding a new language analyzer should require:
1. Implementing the `LanguageAnalyzer` interface
2. Registering in the analyzer factory
3. Optionally adding Tree-sitter grammar

**No changes to existing code.** Open/Closed Principle.

### 4. Graceful Degradation

The system must work at various capability levels:
- Without LLM: Use heuristic summaries
- Without Tree-sitter: Use regex-based parsing  
- Without git: Skip change frequency analysis
- Offline: Use cached summaries

### 5. Separation of Concerns

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                          │
│   CLI Interface, VS Code Extension UI, Markdown Export          │
├─────────────────────────────────────────────────────────────────┤
│                     APPLICATION LAYER                            │
│   Guide orchestration, caching, incremental updates             │
├─────────────────────────────────────────────────────────────────┤
│                      DOMAIN LAYER                               │
│   Analyzers, Summarizers, Graph builders, Metrics               │
├─────────────────────────────────────────────────────────────────┤
│                     INFRASTRUCTURE LAYER                         │
│   LLM providers, File system, Git client, Tree-sitter           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Development Workflow

### Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Stable releases only |
| `develop` | Integration branch for features |
| `feature/*` | Individual features (`feature/python-analyzer`) |
| `fix/*` | Bug fixes (`fix/import-parsing`) |
| `mvp/*` | MVP milestone branches (`mvp/1-core-engine`) |

### Commit Messages

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

**Examples:**
```
feat(analyzer): add Python import extraction
fix(graph): handle circular dependencies correctly
docs(readme): update installation instructions
refactor(core): extract base analyzer interface
test(summarizer): add LLM mock fixtures
```

### Milestone Workflow

1. Complete implementation
2. Run tests (automated: `pytest`)
3. Test manually through CLI/extension
4. Update documentation (IMPLEMENTATION_PLAN.md status)
5. Plan subsequent stages
6. Commit with descriptive message

---

## Testing Standards

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Fast, isolated tests
│   ├── test_analyzers.py
│   ├── test_graph.py
│   └── test_summarizer.py
├── integration/             # Component interaction tests
│   ├── test_pipeline.py
│   └── test_providers.py
└── fixtures/                # Test data
    ├── sample_repo/
    └── expected_outputs/
```

### Coverage Requirements

| Component | Minimum Coverage |
|-----------|-----------------|
| Core domain models | 90% |
| Analyzers | 85% |
| Providers | 80% |
| CLI | 75% |
| Utils | 90% |

### Test Principles

1. **Unit tests are fast** — no I/O, no network, mock everything external
2. **Integration tests are realistic** — test actual component interaction
3. **Fixtures are reusable** — define once in conftest.py
4. **Assertions are specific** — test exact expected behavior

---

## Development Requirements

### Proactive Quality Assurance

> During development, if you discover potential problems in the code or architectural limitations requiring updates/changes, **improve them immediately** to ensure stability and reliability.

This includes:
- Fixing code smells before they become bugs
- Refactoring when patterns prove inadequate
- Adding missing error handling
- Improving type coverage
- Optimizing performance bottlenecks

### Clean, Reusable Code

The code should be written using:
- **Optimal data structures** appropriate for the use case
- **Programming patterns** (Factory, Strategy, Adapter, etc.)
- **High level of abstraction** to maximize reusability
- **Clear separation of concerns** between layers

### Performance Awareness

- Profile before optimizing
- Cache expensive computations (LLM calls, file parsing)
- Use async I/O for file and network operations
- Implement incremental updates for file changes

### Security Considerations

- No secrets in code or config files
- Sanitize file paths to prevent directory traversal
- Validate all external input
- Rate limit LLM API calls

---

## Quick Reference Card

### Before Starting Work
- [ ] Read IMPLEMENTATION_PLAN.md for current phase
- [ ] Check REQUIREMENTS.md for specifications
- [ ] Review ARCHITECTURE.md for component design

### While Coding
- [ ] Follow type safety rules
- [ ] Use dependency injection
- [ ] Write tests alongside code
- [ ] Handle errors explicitly

### Before Committing
- [ ] Run `pytest` (all tests pass)
- [ ] Run `ruff check` (no lint errors)
- [ ] Run `mypy` (no type errors)
- [ ] Update documentation if needed
- [ ] Write descriptive commit message

### After Completing Feature
- [ ] Update IMPLEMENTATION_PLAN.md status
- [ ] Remove any duplicate documentation
- [ ] Verify cross-references work
