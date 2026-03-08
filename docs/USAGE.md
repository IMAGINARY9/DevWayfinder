# DevWayfinder — LLM Usage & Model Configuration

> **Version:** 1.0.0  
> **Status:** Active  
> **Last Updated:** 2026-03-08  
> **Authoritative Source:** This document is the single source of truth for LLM setup and model configuration.

---

## 1. Overview

DevWayfinder uses large language models (LLMs) to generate natural-language summaries of code modules. The system is designed to be **model-agnostic** and **offline-first**, supporting:

- **Local models** via Ollama or llama.cpp
- **Self-hosted APIs** via text-generation-webui, vLLM
- **Cloud APIs** via OpenAI-compatible endpoints

The tool works without an LLM by using heuristic summaries, but LLM-generated descriptions are significantly more useful.

---

## 2. Recommended Setup: Ollama

[Ollama](https://ollama.ai/) is the recommended backend for local LLM inference.

### 2.1 Installation

**Windows:**
```powershell
# Download and install from https://ollama.ai/download
# Or via winget:
winget install Ollama.Ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**macOS:**
```bash
brew install ollama
```

### 2.2 Pull a Model

DevWayfinder works best with 7B parameter models:

```bash
# Recommended: Mistral 7B (best quality/speed tradeoff)
ollama pull mistral:7b

# Alternative: Llama 3.2 8B
ollama pull llama3.2:8b

# Smaller option: Phi-3 Mini (faster, lower quality)
ollama pull phi3:mini
```

### 2.3 Start Ollama Server

```bash
# Ollama runs as a background service by default
# Verify it's running:
ollama list

# If needed, start manually:
ollama serve
```

### 2.4 Verify Connection

```bash
# Using DevWayfinder CLI
devwayfinder test-model

# Or directly test Ollama
curl http://localhost:11434/api/tags
```

---

## 3. Configuration

### 3.1 Default Configuration

If no configuration is provided, DevWayfinder uses:

```yaml
model:
  provider: ollama
  model_name: mistral:7b
  base_url: http://localhost:11434
  timeout: 120
  max_tokens: 512
```

### 3.2 Configuration File

Create `.devwayfinder/config.yaml` in your project:

```yaml
model:
  provider: ollama           # ollama | openai | heuristic
  model_name: mistral:7b     # Model identifier
  base_url: http://localhost:11434
  timeout: 120               # Request timeout in seconds
  max_tokens: 512            # Max tokens per summary
  temperature: 0.3           # Lower = more deterministic
```

### 3.3 Environment Variables

Override config with environment variables:

```bash
# Windows PowerShell
$env:DEVWAYFINDER_MODEL_PROVIDER = "ollama"
$env:DEVWAYFINDER_MODEL_NAME = "mistral:7b"
$env:DEVWAYFINDER_MODEL_BASE_URL = "http://localhost:11434"

# Linux/macOS
export DEVWAYFINDER_MODEL_PROVIDER=ollama
export DEVWAYFINDER_MODEL_NAME=mistral:7b
export DEVWAYFINDER_MODEL_BASE_URL=http://localhost:11434
```

### 3.4 CLI Override

```bash
devwayfinder generate ./project \
  --model-provider ollama \
  --model-name mistral:7b \
  --base-url http://localhost:11434
```

---

## 4. Alternative Backends

### 4.1 text-generation-webui (OpenAI-compatible)

[text-generation-webui](https://github.com/oobabooga/text-generation-webui) provides an OpenAI-compatible API.

**Setup:**
```bash
# In text-generation-webui directory
python server.py --api --api-port 5000
```

**Configuration:**
```yaml
model:
  provider: openai
  model_name: default        # Ignored by TGWUI
  base_url: http://localhost:5000/v1
  api_key: ""                # Not required for local
```

### 4.2 vLLM

[vLLM](https://github.com/vllm-project/vllm) provides high-throughput inference.

**Setup:**
```bash
python -m vllm.entrypoints.openai.api_server \
  --model mistralai/Mistral-7B-Instruct-v0.2 \
  --port 8000
```

**Configuration:**
```yaml
model:
  provider: openai
  model_name: mistralai/Mistral-7B-Instruct-v0.2
  base_url: http://localhost:8000/v1
```

### 4.3 Cloud APIs (OpenAI, Anthropic)

For cloud APIs, set the API key via environment variable:

```bash
# OpenAI
export DEVWAYFINDER_API_KEY=sk-...

# Configuration
model:
  provider: openai
  model_name: gpt-4o-mini
  base_url: https://api.openai.com/v1
```

> ⚠️ **Privacy Warning:** Cloud APIs send code snippets to external servers. Use local models for sensitive codebases.

---

## 5. Model Recommendations

| Use Case | Model | Notes |
|----------|-------|-------|
| **General use** | `mistral:7b` | Best quality/speed balance |
| **Large projects** | `llama3.2:8b` | Better context handling |
| **Low resources** | `phi3:mini` | 3.8B params, faster |
| **Offline/airgapped** | `mistral:7b-q4_K_M` | Quantized, 4.1GB |
| **Maximum quality** | `mixtral:8x7b` | Best results, 26GB+ |

### Hardware Requirements

| Model | VRAM | RAM (CPU) | Notes |
|-------|------|-----------|-------|
| Phi-3 Mini | 4GB | 8GB | Runs on most laptops |
| Mistral 7B | 6GB | 16GB | Recommended minimum |
| Llama 3.2 8B | 8GB | 16GB | Good for larger contexts |
| Mixtral 8x7B | 24GB | 48GB | Requires high-end GPU |

---

## 6. Offline / Heuristic Mode

DevWayfinder can operate without an LLM:

```bash
devwayfinder generate ./project --no-llm
```

In this mode:
- Module descriptions are generated from docstrings and function signatures
- Architecture overview uses directory structure heuristics
- "Start Here" recommendations still work (based on metrics)

Quality is lower but the tool remains functional for basic exploration.

---

## 7. Troubleshooting

### Connection Issues

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running, start it
ollama serve

# Check firewall isn't blocking port 11434
```

### Slow Generation

- Use a quantized model: `ollama pull mistral:7b-q4_K_M`
- Reduce `max_tokens` in config
- Consider CPU-only mode if GPU is insufficient

### Out of Memory

- Use a smaller model (Phi-3 Mini)
- Increase swap space
- Try quantized variants (q4_K_M, q5_K_M)

### Inaccurate Summaries

- Ensure model has enough context (signatures + docstrings)
- Try a larger model
- Lower temperature for more deterministic output
- Submit feedback to improve prompts

---

## 8. Provider Interface

DevWayfinder abstracts LLM backends behind a `ModelProvider` protocol:

```python
class ModelProvider(Protocol):
    @property
    def name(self) -> str: ...
    
    @property
    def available(self) -> bool: ...
    
    async def summarize(self, context: SummarizationContext) -> str: ...
    
    async def health_check(self) -> HealthStatus: ...
```

To add a new provider, see [ARCHITECTURE.md](ARCHITECTURE.md) § Extension Points.

---

## 9. Caching

LLM responses are cached to avoid redundant API calls:

- Cache key: `content_hash + model_id + prompt_version`
- Location: `.devwayfinder/cache/summaries/`
- Invalidation: On content change or config change

To clear cache:
```bash
devwayfinder cache clear
# Or manually:
rm -rf .devwayfinder/cache/summaries/
```
