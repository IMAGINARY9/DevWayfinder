# DevWayfinder — Configuration Reference

> **Version:** 1.0.0  
> **Status:** Active  
> **Last Updated:** 2026-03-08  
> **Authoritative Source:** This document is the single source of truth for configuration options.

---

## 1. Overview

DevWayfinder configuration is loaded from multiple sources with the following precedence (highest to lowest):

1. **CLI arguments** — `--model-provider ollama`
2. **Environment variables** — `DEVWAYFINDER_MODEL_PROVIDER=ollama`
3. **Project config** — `.devwayfinder/config.yaml`
4. **User config** — `~/.devwayfinder/config.yaml`
5. **Built-in defaults**

---

## 2. Configuration File Format

Configuration files use YAML format:

```yaml
# .devwayfinder/config.yaml

model:
  provider: ollama
  model_name: mistral:7b
  base_url: http://localhost:11434
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
    - tree_sitter
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

### 3.1 Model Configuration

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `model.provider` | `string` | `ollama` | LLM provider: `ollama`, `openai`, `heuristic` |
| `model.model_name` | `string` | `mistral:7b` | Model identifier |
| `model.base_url` | `string` | `http://localhost:11434` | API endpoint URL |
| `model.api_key` | `string` | `null` | API key (for cloud providers) |
| `model.timeout` | `int` | `120` | Request timeout in seconds |
| `model.max_tokens` | `int` | `512` | Maximum tokens per response |
| `model.temperature` | `float` | `0.3` | Sampling temperature (0.0-1.0) |

### 3.2 Analysis Configuration

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `analysis.include_patterns` | `list[str]` | `["**/*.py"]` | Glob patterns for files to analyze |
| `analysis.exclude_patterns` | `list[str]` | See defaults | Glob patterns to exclude |
| `analysis.max_file_size` | `int` | `100000` | Max file size in bytes |
| `analysis.enable_git_analysis` | `bool` | `true` | Analyze git history |
| `analysis.enable_metrics` | `bool` | `true` | Compute complexity metrics |
| `analysis.analysis_layers` | `list[str]` | `[tree_sitter, ast, regex, llm]` | Analysis methods in priority order |

### 3.3 Output Configuration

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `output.format` | `string` | `markdown` | Output format: `markdown`, `html`, `json` |
| `output.output_path` | `string` | `null` | Output file path (null = stdout) |
| `output.include_graph` | `bool` | `true` | Include dependency graph |
| `output.include_metrics` | `bool` | `true` | Include complexity metrics |
| `output.graph_format` | `string` | `mermaid` | Graph format: `mermaid`, `ascii`, `dot` |

### 3.4 Cache Configuration

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `cache.enabled` | `bool` | `true` | Enable caching |
| `cache.directory` | `string` | `.devwayfinder/cache` | Cache directory path |
| `cache.ttl_days` | `int` | `30` | Cache entry time-to-live |

### 3.5 Logging Configuration

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `logging.level` | `string` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `logging.file` | `string` | `null` | Log file path (null = stderr) |

---

## 4. Environment Variables

All configuration options can be set via environment variables:

```bash
# Format: DEVWAYFINDER_{SECTION}_{KEY} (uppercase, underscores)

# Model configuration
DEVWAYFINDER_MODEL_PROVIDER=ollama
DEVWAYFINDER_MODEL_NAME=mistral:7b
DEVWAYFINDER_MODEL_BASE_URL=http://localhost:11434
DEVWAYFINDER_API_KEY=sk-...

# Analysis configuration
DEVWAYFINDER_ANALYSIS_ENABLE_GIT=true
DEVWAYFINDER_ANALYSIS_ENABLE_METRICS=true

# Output configuration
DEVWAYFINDER_OUTPUT_FORMAT=markdown
DEVWAYFINDER_OUTPUT_INCLUDE_GRAPH=true

# Cache configuration
DEVWAYFINDER_CACHE_ENABLED=true

# Logging configuration
DEVWAYFINDER_LOGGING_LEVEL=DEBUG
```

---

## 5. CLI Arguments

CLI arguments override all other configuration:

```bash
devwayfinder generate ./project \
  --model-provider ollama \
  --model-name mistral:7b \
  --base-url http://localhost:11434 \
  --no-llm \                      # Use heuristic mode
  --output ./ONBOARDING.md \
  --no-graph \
  --no-metrics \
  --include "**/*.py" \
  --exclude "**/tests/**" \
  --verbose \                     # DEBUG logging
  --quiet                         # WARNING logging only
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

## 8. Profiles

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

## 9. Validation

Validate configuration without running analysis:

```bash
devwayfinder validate
# Checks:
# - Config file syntax
# - Model provider connectivity
# - Directory permissions
# - Pattern validity
```

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
