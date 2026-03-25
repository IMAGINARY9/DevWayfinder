# Troubleshooting Guide

Common issues and solutions for DevWayfinder.

---

## Provider Connection Issues

### "Connection refused" / "Failed to connect"

**Symptom:**
```
Error: Failed to connect to http://localhost:11434
Connection refused
```

**Cause:** LLM provider (Ollama, local server) is not running or unreachable

**Solutions:**

1. **For Ollama:**
   ```bash
   # Check if running
   curl http://localhost:11434/api/tags
   
   # If not running, start it:
   ollama serve
   ```

2. **For OpenAI-compatible endpoint (text-generation-webui, vLLM):**
   ```bash
   # Verify endpoint is running
   curl http://127.0.0.1:5000/api/tags
   
   # Common ports: 5000, 8000, 8001
   # Check your server logs for actual port
   ```

3. **Network/Firewall:**
   - Verify firewall allows connection to port
   - Test with `ping localhost:port` (if supported on your system)
   - Check VPN isn't blocking local connections

4. **Wrong URL:**
   ```bash
   # Try different ports
   devwayfinder test-model --base-url http://127.0.0.1:5000/v1  # vLLM
   devwayfinder test-model --base-url http://127.0.0.1:8000/v1  # Alternative
   ```

---

### "Invalid API key"

**Symptom:**
```
Error: Invalid API key provided
openai.error.AuthenticationError
```

**Cause:** API key is wrong, missing, or revoked

**Solutions:**

1. **Verify key is set:**
   ```bash
   # Windows
   echo $env:OPENAI_API_KEY
   
   # Linux/macOS
   echo $OPENAI_API_KEY
   ```

2. **Get a fresh key:**
   - Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
   - Click "Create new secret key"
   - Copy immediately (not viewable again)

3. **Set environment variable correctly:**
   ```bash
   # Windows PowerShell
   $env:OPENAI_API_KEY = "sk-..."
   
   # Linux/macOS
   export OPENAI_API_KEY="sk-..."
   ```

4. **Verify key is active:**
   - Log into OpenAI dashboard
   - Check key hasn't been revoked
   - Verify no usage limits exceeded

---

### "Model not found"

**Symptom:**
```
Error: Model 'mistral' not found
Error: Could not find model named 'gpt-4o'
```

**Cause:** Model not installed or doesn't exist

**Solutions:**

1. **For Ollama - pull the model:**
   ```bash
   ollama pull mistral
   ollama pull llama2
   ollama list  # See installed models
   ```

2. **For OpenAI - verify model exists:**
   - Check [platform.openai.com/docs/models](https://platform.openai.com/docs/models)
   - Your account might not have access to `gpt-4` (requires separate signup)
   - Use `gpt-4o-mini` instead (available to all accounts)

3. **For local endpoints - check documentation:**
   - Verify model name matches what server exposes
   - Test with: `curl http://localhost:5000/v1/models`

---

## Insufficient Quota / Rate Limits

### "Insufficient quota"

**Symptom:**
```
Error: You exceeded your current quota
RateLimitError
```

**Cause:** API usage quota exceeded or credits expired

**Solutions:**

**For OpenAI:**
1. Check if free trial credits expired (3-month limit)
2. Add payment method: [platform.openai.com/account/billing/overview](https://platform.openai.com/account/billing/overview)
3. Set usage limits to avoid unexpected charges

**For Ollama:**
- Ollama has no quotas (it's local)
- Try reinstalling: `ollama pull <model>`

---

### Rate limit errors

**Symptom:**
```
Error: Rate limit exceeded
429 Too Many Requests
```

**Cause:** Making requests faster than API allows

**Solutions:**
1. Wait 30-60 seconds
2. Try again
3. For high volume: use batch processing or upgrade plan

---

## Performance Issues

### "Analysis is very slow"

**Symptom:** Running `devwayfinder generate` takes 5+ minutes

**Causes & Solutions:**

1. **Using Ollama on CPU (no GPU):**
   ```bash
   # Switch to faster Ollama model
   ollama pull phi3:mini
   devwayfinder generate . --model phi3:mini
   
   # Or use cloud provider instead
   devwayfinder generate . --provider openai --model gpt-4o-mini
   ```

2. **Network latency to cloud API:**
   - Try again (might be temporary)
   - Check internet connection
   - Switch to local Ollama

3. **Slow project scanning:**
   - Large project with many files?
   - Check excluded patterns in config:
     ```yaml
     analysis:
       exclude_patterns:
         - "**/.git/**"
         - "**/node_modules/**"
         - "**/.venv/**"
         - "**/__pycache__/**"
     ```

4. **Verify GPU is being used (Ollama):**
   ```bash
   # Check Ollama server logs
   # Should show "GPU" if CUDA/Metal is working
   ```

---

### "Out of memory" error

**Symptom:**
```
Error: cuda out of memory
RuntimeError: out of memory
```

**Cause:** Model is too large for available GPU/RAM

**Solutions:**

1. **Use smaller model:**
   ```bash
   # Ollama example: Use Phi-3 Mini instead of Mistral
   ollama pull phi3:mini
   devwayfinder generate . --model phi3:mini
   ```

2. **Close other applications** to free up memory

3. **Increase GPU memory:**
   - For NVIDIA: Update drivers, allocate more VRAM
   - For Apple Silicon: Automatic (uses unified memory)

4. **Use cloud provider** instead:
   ```bash
   devwayfinder generate . --provider openai --model gpt-4o-mini
   ```

---

## Output & Results Issues

### "Summary quality is poor"

**Symptom:** Generated summaries are generic or unhelpful

**Causes & Solutions:**

1. **Using heuristic mode (no LLM):**
   ```bash
   # Make sure LLM is actually being used
   devwayfinder generate . --use-llm --provider ollama
   
   # Check output for [LLM] or [heuristic] badges
   ```

2. **Using wrong template:**
   - Heuristic templates are less detailed than LLM
   - LLM summaries are better for complex code
   - Try with different providers for comparison

3. **Project structure issue:**
   - Make sure files are properly formatted
   - Check file naming conventions match analyzer expectations
   - Try: `devwayfinder analyze .` to see what's detected

---

### "Missing modules in output"

**Symptom:** Some files appear to be analyzed but are missing from guide

**Cause:** Excluded by pattern or not recognized as analyzable

**Solutions:**

```bash
# Check what was actually analyzed
devwayfinder analyze . --verbose

# Review exclude patterns in config
cat .devwayfinder/config.yaml

# Add file patterns if needed
# .devwayfinder/config.yaml:
analysis:
  include_patterns:
    - "**/*.py"
    - "**/*.ts"
    - "**/*.js"
  exclude_patterns:
    - "**/__pycache__/**"
    - "**/node_modules/**"
```

---

### "Dependency graph not showing connections"

**Symptom:** Modules exist but dependency connections are missing

**Cause:** Imports not recognized or dependencies are external

**Solutions:**

1. **Check import styles:**
   - Relative imports: `from . import module` ✓
   - Absolute imports: `from myproject import module` ✓
   - Highly nested relative: `from .... import module` ✓

2. **Verify intra-project dependencies:**
   ```bash
   # Run analysis to inspect detected imports
   devwayfinder analyze . --verbose
   ```

3. **External packages are filtered:**
   - Dependencies on external libraries don't show in graph
   - Only internal project dependencies shown
   - This is by design (reduces noise)

---

## Configuration Issues

### "Configuration not being read"

**Symptom:** Config file exists but settings aren't applied

**Cause:** Config file in wrong location or wrong format

**Solutions:**

1. **Verify config file location:**
   ```bash
   # Check if file exists and is valid YAML
   cat .devwayfinder/config.yaml
   
   # Or in home directory
   cat ~/.devwayfinder/config.yaml
   ```

2. **Validate YAML syntax:**
   ```bash
   # Test with Python
   python -c "import yaml; yaml.safe_load(open('.devwayfinder/config.yaml'))"
   # Should succeed with no output
   ```

3. **Priority order (first found wins):**
   1. CLI arguments (highest priority)
   2. Environment variables
   3. `.devwayfinder/config.yaml` in project
   4. `~/.devwayfinder/config.yaml` in home
   5. Built-in defaults (lowest priority)

4. **Explicitly specify config:**
   ```bash
   devwayfinder generate . --config ./my-config.yaml
   ```

---

### "Environment variables not working"

**Symptom:** `OPENAI_API_KEY` or other env var not recognized

**Solutions:**

1. **Verify variable is set:**
   ```bash
   # Windows PowerShell
   dir env:OPENAI_API_KEY
   
   # Linux/macOS
   env | grep OPENAI_API_KEY
   ```

2. **Set in current session (temporary):**
   ```bash
   # Windows PowerShell
   $env:OPENAI_API_KEY = "sk-..."
   devwayfinder generate .
   
   # Linux/macOS
   export OPENAI_API_KEY="sk-..."
   devwayfinder generate .
   ```

3. **Set permanently:**
   - **Windows:** System Properties → Environment Variables → New
   - **Linux/macOS:** Add to `~/.bashrc` or `~/.zshrc`

4. **Restart terminal** after changing environment variables

---

## Installation Issues

### "devwayfinder command not found"

**Symptom:**
```
Command 'devwayfinder' not found
```

**Cause:** DevWayfinder not installed or not in PATH

**Solutions:**

1. **Verify installation:**
   ```bash
   pip list | grep devwayfinder
   ```

2. **Install if missing:**
   ```bash
   pip install git+https://github.com/IMAGINARY9/DevWayfinder.git
   ```

3. **Install in development mode (if cloned):**
   ```bash
   cd DevWayfinder
   pip install -e .
   ```

4. **Check virtual environment:**
   ```bash
   # Make sure venv is activated
   # Should see (venv) or (.venv) in prompt
   
   # If not, activate:
   source .venv/bin/activate      # Linux/macOS
   .\.venv\Scripts\Activate.ps1     # Windows PowerShell
   ```

---

### "Python version error"

**Symptom:**
```
Error: Python 3.11+ required
```

**Cause:** Running with wrong Python version

**Solutions:**

1. **Check Python version:**
   ```bash
   python --version
   ```

2. **Install Python 3.11+:**
   - Download from [python.org](https://www.python.org/downloads/)
   - Or use package manager: `brew install python@3.11`, `apt install python3.11`

3. **Use specific Python version:**
   ```bash
   /usr/bin/python3.11 -m pip install devwayfinder
   /usr/bin/python3.11 -m devwayfinder generate .
   ```

---

## Getting Help

If issue isn't listed above:

1. **Run with verbose logging:**
   ```bash
   export DEVWAYFINDER_DEBUG=true
   devwayfinder generate . --verbose
   ```

2. **Check provider connectivity:**
   ```bash
   devwayfinder test-model
   ```

3. **Verify configuration:**
   ```bash
   cat .devwayfinder/config.yaml
   env | grep DEVWAYFINDER
   ```

4. **Check documentation:**
   - [USAGE.md](USAGE.md) — LLM setup
   - [CONFIGURATION.md](../CONFIGURATION.md) — Config options
   - [SETUP_OLLAMA.md](SETUP_OLLAMA.md) — Ollama guide
   - [SETUP_OPENAI_OFFICIAL.md](SETUP_OPENAI_OFFICIAL.md) — OpenAI guide

5. **Report issue with context:**
   - Python version: `python --version`
   - DevWayfinder version: `pip show devwayfinder`
   - OS: Windows/Linux/macOS
   - Error message (full stack trace)
   - Steps to reproduce

---

**Last Updated:** March 2026
