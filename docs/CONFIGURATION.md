# DevWayfinder - Configuration Reference

> **Version:** 1.1.0  
> **Status:** Active  
> **Last Updated:** 2026-04-01  
> **Authoritative Source:** This document is the single source of truth for configuration options.

---

## 1. Overview

DevWayfinder currently supports two runtime configuration surfaces:

1. **Provider runtime settings** (CLI + environment variables)
2. **Guide layout templates** via `.devwayfinder/template.yaml`

`devwayfinder init` still scaffolds `.devwayfinder/config.yaml`, but full runtime loading of that file hierarchy remains planned follow-up work.

---

## 2. Runtime Precedence

### 2.1 Provider Runtime Settings

For provider settings, precedence is (highest to lowest):

1. CLI options (for example `--model-provider`, `--model-name`, `--base-url`)
2. Environment variables (for example `DEVWAYFINDER_MODEL_PROVIDER`)
3. Built-in defaults

### 2.2 Guide Template Selection

Guide template selection order is:

1. `--guide-template <path>` (if provided)
2. `.devwayfinder/template.yaml` in the analyzed project
3. Built-in `default` template

---

## 3. Provider Configuration

### 3.1 Supported Provider Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `provider` | `string` | `openai_compat` | Provider name: `openai_compat`, `openai`, `ollama`, `heuristic` |
| `model_name` | `string | null` | `null` | Provider-specific model ID |
| `base_url` | `string | null` | provider default | Endpoint URL |
| `api_key` | `string | null` | `null` | API key token |
| `timeout` | `float` | `120.0` | Request timeout in seconds |
| `max_tokens` | `int` | `512` | Max output tokens per summary |
| `temperature` | `float` | `0.3` | Sampling temperature |

### 3.2 Environment Variables

```bash
DEVWAYFINDER_MODEL_PROVIDER=openai_compat
DEVWAYFINDER_MODEL_NAME=
DEVWAYFINDER_MODEL_BASE_URL=http://127.0.0.1:5000/v1
DEVWAYFINDER_API_KEY=
DEVWAYFINDER_MODEL_TIMEOUT=120
DEVWAYFINDER_MODEL_MAX_TOKENS=512
DEVWAYFINDER_MODEL_TEMPERATURE=0.3
```

### 3.3 CLI Overrides

```bash
devwayfinder generate ./project \
  --model-provider openai_compat \
  --model-name mistral \
  --base-url http://127.0.0.1:5000/v1 \
  --api-key local
```

---

## 4. Guide Template Configuration

Guide templates control section order, inclusion/exclusion, and section title overrides.

### 4.1 Template File Location

Project default path:

```text
.devwayfinder/template.yaml
```

Optional override:

```bash
devwayfinder generate ./project --guide-template ./custom-template.yaml
```

### 4.2 Template Schema

```yaml
name: custom-order
extends: default  # default | compact

sections:
  - type: start_here
    title: Read This First
  - type: dependencies
    enabled: false
```

### 4.3 Supported Section Types

- `overview`
- `architecture`
- `modules`
- `dependencies`
- `start_here`

### 4.4 Built-in Base Templates

- `default`: Overview -> Architecture -> Modules -> Dependencies -> Start Here
- `compact`: Overview -> Modules -> Start Here

When using `extends`, listed `sections` are applied as overrides and reordered first; unspecified base sections are appended in base order.

---

## 5. Cost and Token Visibility

Cost and token reporting is currently **always enabled** in generation output:

- Preflight estimate panel before generation
- Post-run totals (`Tokens used`, `Cost (estimated)`)

There is currently no separate toggle flag for cost visibility.

---

## 6. Scaffolded Config File (`devwayfinder init`)

`devwayfinder init` creates `.devwayfinder/config.yaml` templates for project types. This is useful for team conventions and future runtime config expansion, but most non-provider fields are not yet enforced at runtime.

---

## 7. Known Follow-up Items

The following are intentionally pending and tracked in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md):

- Full `DevWayfinderConfig` runtime loader hierarchy
- User-level config merge (`~/.devwayfinder/...`)
- Validation command for config files
- Profile activation via CLI
