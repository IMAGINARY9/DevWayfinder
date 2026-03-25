# Setting Up Ollama with DevWayfinder

**Status:** Recommended (Free, Fast, Local)  
**Setup Time:** ~5 minutes  
**Cost:** Free  
**Best For:** Local development, testing, cost-free analysis

---

## Overview

[Ollama](https://ollama.ai/) is the recommended way to run LLMs locally. It provides:

- ✅ **Free** — No API costs
- ✅ **Offline** — Runs completely locally
- ✅ **Fast** — Optimized inference engine
- ✅ **Simple** — Single command to get started
- ✅ **No limits** — Run as many analyses as you want

---

## Installation

### Windows

**Option 1: Download Installer (Recommended)**
1. Visit [ollama.ai/download](https://ollama.ai/download/windows)
2. Click "Download for Windows"
3. Run the installer and complete setup
4. Ollama will run in background automatically

**Option 2: Chocolatey**
```powershell
choco install ollama
```

**Option 3: WinGet**
```powershell
winget install Ollama.Ollama
```

**Verify Installation:**
```powershell
ollama --version
```

### Linux

**Ubuntu/Debian:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Arch Linux:**
```bash
pacman -S ollama
```

**Verify Installation:**
```bash
ollama --version
```

### macOS

**Using Homebrew (Recommended):**
```bash
brew install ollama
```

**Or download directly:**
1. Visit [ollama.ai/download](https://ollama.ai/download/mac)
2. Download the appropriate version (Intel or Apple Silicon)
3. Run the installer

**Verify Installation:**
```bash
ollama --version
```

---

## Model Selection

Ollama comes with pre-trained models. Choose one based on your needs:

### Recommended Models

| Model | Size | Speed | Quality | RAM Needed | Command |
|-------|------|-------|---------|-----------|---------|
| **Mistral 7B** | 4.1GB | Fast | Good | 8GB | `ollama pull mistral` |
| **Llama 2 7B** | 3.8GB | Fast | Good | 8GB | `ollama pull llama2` |
| **Llama 3.2 8B** | 4.7GB | Fast | Good | 8GB | `ollama pull llama3.2:8b` |
| **Phi-3 Mini** | 2.3GB | Very Fast | Fair | 4GB | `ollama pull phi3:mini` |

### For GPU Acceleration

| Model | VRAM Needed (NVIDIA) | Speed Improvement |
|-------|---------------------|------------------|
| Mistral 7B | 6GB+ | 3-5x faster |
| Llama 2 7B | 6GB+ | 3-5x faster |
| Phi-3 Mini | 4GB+ | 2-3x faster |

**Best Value:** Mistral 7B = excellent quality/speed tradeoff

---

## Getting Started

### 1. Pull a Model

Choose a model and download it:

```bash
# Recommended: Mistral 7B
ollama pull mistral

# Or other options:
ollama pull llama2
ollama pull llama3.2:8b
ollama pull phi3:mini
```

First pull may take 2-10 minutes depending on your internet speed.

**Verify:**
```bash
ollama list
# Output:
# NAME              ID              SIZE    MODIFIED
# mistral:latest    2e405c30...     4.1GB   2 hours ago
```

### 2. Start the Server

Ollama runs as a background service automatically on Windows/macOS. To manually start:

```bash
# macOS/Linux
ollama serve

# Windows (usually not needed - runs in background)
# But if needed:
ollama serve
```

**Verify Server is Running:**
```bash
curl http://localhost:11434/api/tags
# Output: {"models":[{"name":"mistral:latest",...}]}
```

### 3. Test with DevWayfinder

```bash
# Test the connection
devwayfinder test-model --provider ollama --model mistral

# If successful, you'll see:
# ✓ Ollama (http://localhost:11434)
# - Model: mistral:latest
# - Status: Ready
```

### 4. Generate Your First Guide

```bash
# Generate onboarding guide for a local project
devwayfinder generate ./path/to/your/project
```

---

## Configuration

### Environment Variables

```bash
# Optional: Set default model (if not specified in CLI)
export DEVWAYFINDER_OLLAMA_MODEL=mistral

# Optional: Set custom Ollama endpoint (non-standard port)
export OLLAMA_HOST=http://localhost:11435

# Optional: Enable debug logging
export DEVWAYFINDER_DEBUG=true
```

### Configuration File

Create `.devwayfinder/config.yaml` in your project:

```yaml
model:
  provider: ollama
  model_name: mistral
  base_url: http://localhost:11434
  timeout: 120
  max_tokens: 512
  temperature: 0.3

analysis:
  include_patterns:
    - "**/*.py"
  exclude_patterns:
    - "**/node_modules/**"
    - "**/.venv/**"
```

---

## Performance Optimization

### CPU vs GPU

**With GPU (NVIDIA CUDA):**
- Mistral: ~4-6 tokens/sec
- Fast enough for interactive use

**With GPU (Apple Silicon):**
- Mistral: ~8-12 tokens/sec
- Very fast

**CPU Only:**
- Mistral: ~0.5-2 tokens/sec (depending on CPU)
- Slower but works

**To use GPU, you need:**
- NVIDIA: CUDA toolkit installed
- macOS: Apple Silicon (M1/M2+) - automatic
- Linux: NVIDIA GPU drivers

### Speed Tips

1. **Use smaller models for testing:** Phi-3 Mini is 2x faster than Mistral
2. **Close other applications** to free up RAM
3. **Enable GPU acceleration** if available
4. **Run on fast SSD** (improves model loading)

---

## Troubleshooting

### "Connection refused" error

```
Error: Failed to connect to http://localhost:11434
```

**Fix:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running, start it:
ollama serve

# On Windows, check taskbar for Ollama icon
# Right-click → "Verify installation was successful"
```

### "Model not found" error

```
Error: Model 'mistral' not found
```

**Fix:**
```bash
# Pull the model
ollama pull mistral

# List available models
ollama list
```

### "Out of memory" error

```
Error: cuda out of memory
```

**Fix:**
- Use smaller model: `ollama pull phi3:mini`
- Reduce other applications' GPU usage
- Increase GPU memory if available

### "Too slow" / "Taking forever"

**If using CPU only:**
- Install NVIDIA drivers for GPU acceleration
- Or use Phi-3 Mini for faster CPU inference
- Or use cloud provider (OpenAI, Anthropic)

**Check what's using resources:**
```bash
# View model info
ollama list

# Check server logs (macOS/Linux):
journalctl -u ollama -f
```

### Server stops after inactivity

**Normal behavior:** Ollama unloads models after 5 min inactivity to free RAM.

**To keep model loaded:**
```bash
# Set environment variable (Windows PowerShell)
$env:OLLAMA_KEEP_ALIVE = "-1"

# Or in Linux/macOS
export OLLAMA_KEEP_ALIVE=-1
```

---

## Advanced Configuration

### Using Multiple Models

```bash
# Pull multiple models
ollama pull mistral
ollama pull llama2
ollama pull phi3:mini

# Switch models in CLI
devwayfinder generate ./project --model llama2
```

### Custom Model Paths

By default, models are stored in:
- **Windows:** `C:\Users\<username>\.ollama\models`
- **Linux:** `~/.ollama/models`
- **macOS:** `~/.ollama/models`

To use custom location:
```bash
# Windows
set OLLAMA_MODELS=C:\custom\path

# Linux/macOS
export OLLAMA_MODELS=/custom/path
```

### Non-Standard Port

If port 11434 is already in use:

```bash
# Windows
set OLLAMA_HOST=127.0.0.1:11435

# Linux/macOS
export OLLAMA_HOST=127.0.0.1:11435

# Then start server:
ollama serve

# Tell DevWayfinder about the custom port:
devwayfinder generate ./project --provider ollama --base-url http://127.0.0.1:11435
```

---

## Examples

### Quick Start (Copy & Paste)

```bash
# 1. Install
# (Download from ollama.ai or use package manager above)

# 2. Pull model
ollama pull mistral

# 3. Verify
curl http://localhost:11434/api/tags

# 4. Install DevWayfinder
pip install -e git+https://github.com/IMAGINARY9/DevWayfinder.git#egg=devwayfinder

# 5. Generate guide
devwayfinder generate ./your-project

# Done! Check ONBOARDING.md
```

### Analyzing a Real Project

```bash
# Clone a project
git clone https://github.com/pallets/flask.git
cd flask

# Generate guide with Ollama
devwayfinder generate . --provider ollama --output FLASK_ONBOARDING.md

# View the result
cat FLASK_ONBOARDING.md
```

---

## Next Steps

- **Want more quality?** See [SETUP_OPENAI_OFFICIAL.md](SETUP_OPENAI_OFFICIAL.md) for using OpenAI API
- **Need private cloud?** See [SETUP_AZURE_OPENAI.md](SETUP_AZURE_OPENAI.md) for Azure integration
- **Want detailed config?** See [CONFIGURATION.md](../CONFIGURATION.md)
- **Troubleshooting?** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## FAQ

**Q: Is Ollama really free?**  
A: Yes, completely free. It's open-source software that runs locally.

**Q: Can I use Ollama on a laptop without GPU?**  
A: Yes, but it will be slower (typically 0.5-2 tokens/sec vs 4-6 with GPU). Still usable for learning/exploration.

**Q: How much disk space do I need?**  
A: ~5GB for one model. Models are shared between projects, so additional analyses don't use more disk.

**Q: Can I run multiple models simultaneously?**  
A: Yes, pull multiple models. Ollama will swap them as needed.

**Q: Should I keep Ollama running all the time?**  
A: No, it's fine to stop it. Models are persistent on disk and reload quickly.

**Q: What if I want to use a different backend (vLLM, text-generation-webui)?**  
A: They expose OpenAI-compatible APIs. Use `--provider openai_compat --base-url <your-url>` to point to them.

---

**Status:** ✅ Ollama setup complete and verified  
**Last Updated:** March 2026
