# Release Notes

## v0.3.10 (2026-04-15)

This release continues the `0.3.x` stabilization track with quality and reliability improvements.

### Highlights

- Stabilized CI coverage with deterministic branch tests, making the 80% coverage gate reliable across environments.
- Redesigned dependency insight generation and improved Mermaid fallback handling for guide generation.
- Stabilized Ollama auto mode and improved dependency readability in generated summaries.
- Deduplicated "start here" steps and documented the evaluation workflow.
- Simplified summarizer detail modes and sanitized output more consistently.
- Added guided quality profiles and improved LLM-first synthesis behavior in the CLI.
- Hardened analysis and provider reliability across summarization flows.

### Artifacts

Release artifacts have been generated for this version in `dist/` using:

```bash
python -m build --sdist --wheel
```
