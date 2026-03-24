# DevWayfinder — Configuration Reference

> **Version:** 1.0.0  
> **Status:** Active  
> **Last Updated:** 2026-03-24  
> **Authoritative Source:** This document is the single source of truth for configuration options.

---

## 1. Overview

Current runtime configuration (MVP 2) is resolved with the following precedence (highest to lowest):

1. **CLI arguments** — e.g. `--model-provider openai_compat`
2. **Environment variables** — e.g. `DEVWAYFINDER_MODEL_PROVIDER=openai_compat`
3. **Built-in provider defaults**

`devwayfinder init` scaffolds `.devwayfinder/config.yaml` templates, but full project/user YAML config loading hierarchy is planned work (see [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md), Phase 1.4 follow-up).

---

## 2. Configuration File Format

Configuration files use YAML format:

```yaml
# .devwayfinder/config.yaml

model:
  provider: openai_compat
  model_name: null
  base_url: http://127.0.0.1:5000/v1
  api_key: local
  timeout: 120
  max_tokens: 512
  temperature: 0.3

analysis:
  include_patterns:
    - "**/*.py"
    - "**/*.ts"
    - "**/*.js"
  exclude_patterns:
    - "**/node_modules/**"
    - "**/.venv/**"
    - "**/dist/**"
    - "**/build/**"
    - "**/__pycache__/**"
  max_file_size: 100000
  enable_git_analysis: true
  enable_metrics: true
  analysis_layers:
    - ast
    - regex
    - llm

output:
  format: markdown
  output_path: null
  include_graph: true
  include_metrics: true
  graph_format: mermaid

cache:
  enabled: true
  directory: .devwayfinder/cache
  ttl_days: 30

logging:
  level: INFO
  file: null
```

---

## 3. Configuration Sections

### 3.1 Model Configuration (Runtime Supported)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `model.provider` | `string` | `openai_compat` | LLM provider: `openai_compat`, `openai`, `ollama`, `heuristic` |
| `model.model_name` | `string \| null` | `null` | Model identifier; required for official OpenAI |
| `model.base_url` | `string` | `http://127.0.0.1:5000/v1` | API endpoint URL |
| `model.api_key` | `string \| null` | `local` | API key or local placeholder token |
| `model.timeout` | `int` | `120` | Request timeout in seconds |
| `model.max_tokens` | `int` | `512` | Maximum tokens per response |
| `model.temperature` | `float` | `0.3` | Sampling temperature (0.0-1.0) |

### 3.2 Analysis Configuration (Template/Planned)

Analysis and output keys in generated templates are intended for upcoming config-loader integration. Current runtime behavior for analysis/output is primarily controlled by CLI flags and built-in defaults.


| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `analysis.include_patterns` | `list[str]` | `["**/*.py"]` | Glob patterns for files to analyze |
| `analysis.exclude_patterns` | `list[str]` | See defaults | Glob patterns to exclude |
| `analysis.max_file_size` | `int` | `100000` | Max file size in bytes |
| `analysis.enable_git_analysis` | `bool` | `true` | Analyze git history |
| `analysis.enable_metrics` | `bool` | `true` | Compute complexity metrics |
| `analysis.analysis_layers` | `list[str]` | `[ast, regex, llm]` | Analysis methods in priority order. `tree_sitter` available as optional extra. |

### 3.3 Output Configuration (Template/Planned)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `output.format` | `string` | `markdown` | Output format: `markdown`, `html`, `json` |
| `output.output_path` | `string` | `null` | Output file path (null = stdout) |
| `output.include_graph` | `bool` | `true` | Include dependency graph |
| `output.include_metrics` | `bool` | `true` | Include complexity metrics |
| `output.graph_format` | `string` | `mermaid` | Graph format: `mermaid`, `ascii`, `dot` |

### 3.4 Cache Configuration (Partially Runtime)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `cache.enabled` | `bool` | `true` | Enable caching |
| `cache.directory` | `string` | `.devwayfinder/cache` | Cache directory path |
| `cache.ttl_days` | `int` | `30` | Cache entry time-to-live |

### 3.5 Logging Configuration (Planned)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `logging.level` | `string` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `logging.file` | `string` | `null` | Log file path (null = stderr) |

---

## 4. Environment Variables

The following environment variables are currently consumed at runtime by provider configuration:

```bash
# Format: DEVWAYFINDER_{SECTION}_{KEY} (uppercase, underscores)

# Model configuration
DEVWAYFINDER_MODEL_PROVIDER=openai_compat
DEVWAYFINDER_MODEL_NAME=
DEVWAYFINDER_MODEL_BASE_URL=http://127.0.0.1:5000/v1
DEVWAYFINDER_API_KEY=local

DEVWAYFINDER_MODEL_TIMEOUT=120
DEVWAYFINDER_MODEL_MAX_TOKENS=512
DEVWAYFINDER_MODEL_TEMPERATURE=0.3
```

---

## 5. CLI Arguments

CLI arguments override all other configuration:

```bash
devwayfinder generate ./project \
  --model-provider openai_compat \
  --base-url http://127.0.0.1:5000/v1 \
  --no-llm \
  --output ./ONBOARDING.md \
  --no-graph \
  --no-metrics \
  --verbose
```

---

## 6. Default Exclude Patterns

The following patterns are excluded by default:

```yaml
exclude_patterns:
  # Dependencies
  - "**/node_modules/**"
  - "**/.venv/**"
  - "**/venv/**"
  - "**/vendor/**"
  
  # Build outputs
  - "**/dist/**"
  - "**/build/**"
  - "**/__pycache__/**"
  - "**/*.egg-info/**"
  
  # IDE/editor
  - "**/.idea/**"
  - "**/.vscode/**"
  
  # Version control
  - "**/.git/**"
  
  # Misc
  - "**/.devwayfinder/**"
  - "**/coverage/**"
```

---

## 7. Templates

### 7.1 Guide Templates

Custom guide templates can be defined in `.devwayfinder/templates/`:

```yaml
# .devwayfinder/templates/guide.yaml
name: "Custom Onboarding Guide"
sections:
  - type: overview
    title: "Project Overview"
    include_readme: true
    
  - type: architecture
    title: "Architecture"
    include_graph: true
    
  - type: modules
    title: "Key Modules"
    max_modules: 20
    sort_by: connectivity  # connectivity | complexity | alphabetical
    
  - type: start_here
    title: "Where to Start"
    recommendations: 5
    
  - type: custom
    title: "Getting Started"
    content: |
      ## Setup Instructions
      1. Clone the repository
      2. Run `pip install -e .`
      3. ...
```

### 7.2 Template Discovery

Templates are searched in order:
1. `.devwayfinder/templates/` (project)
2. `~/.devwayfinder/templates/` (user)
3. Built-in templates

---

## 8. Profiles (Planned)

Named profile activation is a planned capability and is not currently exposed as a stable CLI/runtime feature.

Pre-configured profiles for common use cases:

```yaml
# .devwayfinder/config.yaml

# Use a predefined profile
profile: slow-local

# Or define custom profiles
profiles:
  slow-local:
    model:
      timeout: 300
      max_tokens: 256
    analysis:
      enable_metrics: false
      
  thorough:
    model:
      max_tokens: 1024
      temperature: 0.1
    analysis:
      enable_git_analysis: true
      enable_metrics: true
      
  quick:
    model:
      provider: heuristic
    analysis:
      enable_git_analysis: false
      enable_metrics: false
```

Activate a profile via CLI:
```bash
devwayfinder generate ./project --profile thorough
```

---

## 9. Validation (Planned)

Dedicated `devwayfinder validate` command support is planned and not currently available in MVP 2.

Validate configuration without running analysis:

Planned validation scope:
- Config file syntax
- Model provider connectivity
- Directory permissions
- Pattern validity

---

## 10. Example Configurations

### 10.1 Minimal Configuration

```yaml
# Works with all defaults
model:
  provider: ollama
```

### 10.2 Offline / Air-gapped Environment

```yaml
model:
  provider: heuristic
  
analysis:
  enable_git_analysis: false
  analysis_layers:
    - ast
    - regex
```

### 10.3 Large Project

```yaml
model:
  timeout: 300
  max_tokens: 256    # Shorter summaries for speed
  
analysis:
  max_file_size: 50000    # Smaller files only
  exclude_patterns:
    - "**/tests/**"
    - "**/docs/**"
    
cache:
  enabled: true
  ttl_days: 7
```

### 10.4 TypeScript Project

```yaml
analysis:
  include_patterns:
    - "**/*.ts"
    - "**/*.tsx"
    - "**/*.js"
    - "**/*.jsx"
  exclude_patterns:
    - "**/node_modules/**"
    - "**/dist/**"
    - "**/*.d.ts"    # Skip declaration files
```
