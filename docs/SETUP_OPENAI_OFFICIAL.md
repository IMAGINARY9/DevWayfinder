# Setting Up OpenAI with DevWayfinder

**Status:** Production-Ready  
**Setup Time:** ~2 minutes  
**Cost:** ~$0.10-0.50 per analysis  
**Best For:** Cloud use, best quality, scalability

---

## Overview

Using OpenAI's official API provides:

- ✅ **Highest Quality** — GPT-4o models are excellent
- ✅ **Fast** — API responses in seconds
- ✅ **Scalable** — Works for projects of any size
- ✅ **Simple** — Just need an API key
- ✅ **Optional** — Fall back to local Ollama if needed

---

## Cost Estimate

For a 100-module Python project (typical size):

| Model | Tokens | Cost |
|-------|--------|------|
| gpt-4o-mini (Recommended) | 5,000-7,000 | $0.10-0.15 |
| gpt-4o | 5,000-7,000 | $0.30-0.50 |
| gpt-3.5-turbo (Cheapest) | 5,000-7,000 | $0.03-0.05 |

**Budget:** $2-5/month for occasional use on multiple projects

---

## Step 1: Create OpenAI Account

1. Go to [platform.openai.com](https://platform.openai.com)
2. Click "Sign up" (or log in if you have account)
3. Complete email verification
4. Add payment method (credit/debit card)

**Note:** OpenAI offers $5 free credits for new accounts (3-month expiry).

---

## Step 2: Get API Key

1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Click "Create new secret key"
3. Name it "DevWayfinder" (for easy identification)
4. Copy the key immediately (you can't see it again)

**⚠️ Important:** Treat your API key like a password. Never commit it to git.

---

## Step 3: Configure DevWayfinder

### Option A: Environment Variable (Recommended)

```bash
# Windows PowerShell
$env:OPENAI_API_KEY = "sk-..."
devwayfinder test-model --provider openai --model gpt-4o-mini

# Linux/macOS (Bash)
export OPENAI_API_KEY="sk-..."
devwayfinder test-model --provider openai --model gpt-4o-mini
```

### Option B: Configuration File

Create `.devwayfinder/config.yaml`:

```yaml
model:
  provider: openai
  model_name: gpt-4o-mini
  api_key: sk-...  # Copy your key here
  timeout: 30
  max_tokens: 512
```

### Option C: CLI Argument

```bash
devwayfinder generate ./project --provider openai --api-key sk-... --model gpt-4o-mini
```

---

## Step 4: Verify Connection

```bash
devwayfinder test-model --provider openai --model gpt-4o-mini

# Output:
# ✓ OpenAI (https://api.openai.com/v1)
# - Model: gpt-4o-mini
# - Status: Connected
```

---

## Model Selection

### Recommended

**`gpt-4o-mini`** — Best value for code analysis
- **Quality:** Excellent (understands complex code)
- **Speed:** Fast (5-10 seconds per analysis)
- **Cost:** ~$0.10-0.15 per 100-module project
- **Use Case:** General code analysis, onboarding guides

### Premium Options

| Model | Quality | Cost | Use Case |
|-------|---------|------|----------|
| **gpt-4o** | Best | $0.30-0.50 | Complex architecture analysis |
| **gpt-4-turbo** | Great | $0.15-0.30 | Deep technical analysis |
| **gpt-3.5-turbo** | Good | $0.03-0.05 | Quick heuristic-like summaries |

**Recommendation:** Start with `gpt-4o-mini`. Upgrade to `gpt-4o` only if you need better quality for complex projects.

---

## Usage Examples

### Basic Usage

```bash
# Generate guide with gpt-4o-mini (recommended)
devwayfinder generate ./my-project

# Specify model explicitly
devwayfinder generate ./my-project --model gpt-4o

# Estimate cost before running
devwayfinder generate ./my-project --estimate-cost
```

### Advanced: Cost Optimization

```bash
# Analyze once with gpt-4o-mini, save guide
devwayfinder generate ./my-project --model gpt-4o-mini -o GUIDE.md

# Updates with cheaper gpt-3.5-turbo (if minor changes only)
devwayfinder generate ./my-project --model gpt-3.5-turbo

# Archive original for reference
cp GUIDE.md GUIDE_v1.md
```

---

## Security & Best Practices

### Protecting Your API Key

**❌ DO NOT:**
- Commit keys to git
- Share keys in Slack/email
- Hard-code in source files
- Include in screenshots

**✅ DO:**
- Store in environment variables
- Use separate keys for different purposes (local dev vs. CI/CD)
- Rotate keys periodically
- Use key restrictions (optional, in OpenAI dashboard)

### GitHub Actions (CI/CD)

If using DevWayfinder in automated pipelines:

1. Go to repository → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `OPENAI_API_KEY`
4. Value: Paste your OpenAI API key
5. Click "Add secret"

Then in `.github/workflows/*.yml`:

```yaml
env:
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

- name: Generate guide
  run: devwayfinder generate . --model gpt-4o-mini
```

---

## Cost Management

### Monitor Usage

1. Go to [platform.openai.com/account/billing/overview](https://platform.openai.com/account/billing/overview)
2. View usage by date and model
3. Set up alerts (Settings → Billing → Usage limits)

### Cost Limits

Set a hard cap to prevent unexpected charges:

1. Go to [platform.openai.com/account/billing/limits](https://platform.openai.com/account/billing/limits)
2. Set "Hard limit (USD)" to your monthly budget
3. API requests will fail if exceeded (instead of charging)

### Per-Project Cost Tracking

To estimate cost before running:

```bash
# Show token estimate without actually calling API
devwayfinder generate ./project --estimate-cost

# Output:
# Estimated tokens: 6,234
# Estimated cost (gpt-4o-mini): $0.12
```

---

## Rate Limits & Quotas

OpenAI has rate limits to prevent abuse:

| Plan | Requests/min | Tokens/min |
|------|-------------|-----------|
| Free Trial | 20 | 40,000 |
| Pay-as-you-go | 500 | 1,000,000 |

**For DevWayfinder:** These limits are very generous. A single analysis uses ~5-10k tokens (well under limits).

If you hit rate limits, wait a minute and retry.

---

## Troubleshooting

### "Invalid API key" error

```
Error: Invalid API key provided
```

**Fixes:**
1. Verify key is correct: Copy directly from [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Check environment variable is set: `echo $OPENAI_API_KEY`
3. Verify key is active in OpenAI dashboard (not revoked)
4. Try generating a new key

### "Insufficient quota" error

```
Error: You exceeded your current quota
```

**Fixes:**
1. Check if free trial credits expired (3-month limit)
2. Add payment method: go to [platform.openai.com/account/billing/overview](https://platform.openai.com/account/billing/overview)
3. Verify usage isn't excessive: check billing dashboard

### "Connection timeout" error

```
Error: Timeout connecting to api.openai.com
```

**Fixes:**
1. Check internet connection
2. Try again in 30 seconds (temporary API issue)
3. Check OpenAI status: [status.openai.com](https://status.openai.com)

### "Model not found" error

```
Error: Model 'gpt-4o' not found
```

**Fixes:**
1. Verify model name is correct (check [platform.openai.com/docs/models](https://platform.openai.com/docs/models))
2. Ensure your account has access to the model (new accounts might not have access to all models)
3. Use `gpt-4o-mini` as fallback

---

## Advanced Configuration

### Custom API Endpoint (Proxy)

If using a proxy or custom endpoint:

```yaml
model:
  provider: openai
  api_key: sk-...
  base_url: https://api.yourcompany.com/openai  # Custom endpoint
  model_name: gpt-4o-mini
```

### Retry Configuration

DevWayfinder retries failed requests automatically:

```yaml
model:
  provider: openai
  api_key: sk-...
  timeout: 30
  max_retries: 3
```

---

## Fallback Strategy

### Hybrid Approach: Ollama + OpenAI

For cost optimization, use local Ollama normally, fall back to OpenAI for complex projects:

```bash
# First, try local Ollama
devwayfinder generate ./small-project --provider ollama --model mistral

# If Ollama unavailable or slow, use OpenAI
devwayfinder generate ./complex-project --provider openai --model gpt-4o-mini
```

DevWayfinder supports automatic provider detection:

```bash
# Will use first available provider (Ollama preferred)
devwayfinder generate ./project
```

---

## Examples

### Quick Start

```bash
# 1. Set API key
export OPENAI_API_KEY="sk-..."

# 2. Verify
devwayfinder test-model --provider openai

# 3. Generate guide
devwayfinder generate ./my-project

# 4. Check output
cat ONBOARDING.md
```

### Cost-Aware Workflow

```bash
# Estimate cost
devwayfinder generate ./repo --estimate-cost
# Output: Estimated cost (gpt-4o-mini): $0.12

# If acceptable, generate
devwayfinder generate ./repo --model gpt-4o-mini

# Monitor actual usage
# https://platform.openai.com/account/billing/overview
```

---

## Next Steps

- **Want free local alternative?** See [SETUP_OLLAMA.md](SETUP_OLLAMA.md)
- **Need Anthropic Claude?** See [SETUP_ANTHROPIC.md](SETUP_ANTHROPIC.md)
- **Enterprise Azure?** See [SETUP_AZURE_OPENAI.md](SETUP_AZURE_OPENAI.md)
- **Configuration details?** See [CONFIGURATION.md](../CONFIGURATION.md)

---

## FAQ

**Q: Can I use OpenAI API for free?**  
A: New accounts get $5 free credits (3-month expiry). After that, you need a payment method.

**Q: How much does it really cost?**  
A: ~$0.10 per analysis for 100-module project using gpt-4o-mini. Budget $2-5/month for casual use.

**Q: Is my code sent to OpenAI?**  
A: Yes, code is sent to OpenAI API for analysis. Don't use for proprietary/sensitive code. Consider Ollama for privacy.

**Q: Can I use other OpenAI models?**  
A: Yes, any model in [platform.openai.com/docs/models](https://platform.openai.com/docs/models) that your account has access to.

**Q: What if API is down?**  
A: Check [status.openai.com](https://status.openai.com). If down, use local Ollama as fallback.

---

**Status:** ✅ OpenAI setup complete  
**Last Updated:** March 2026
