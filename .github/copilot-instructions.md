# DevWayfinder Copilot Instructions

Project: AI-Powered Developer Onboarding Generator
Status: MVP 2.5+

## 1. Documentation Authority

Single source of truth per topic. Update only the authoritative file.

- Architecture and component design: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Functional/non-functional requirements: [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md)
- Roadmap, milestones, progress: [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)
- Configuration options and templates: [docs/CONFIGURATION.md](docs/CONFIGURATION.md)
- Development standards and contribution rules: [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)
- LLM/provider setup and usage: [docs/USAGE.md](docs/USAGE.md)

Rules:
- Do not duplicate documentation across files.
- Keep README minimal: quick start + links to authoritative docs.
- Record milestone completion in [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md).
- Avoid creating temporary report documents unless explicitly requested.

## 2. Development Quality Gates

Before committing:

1. Run tests:
   - `.venv\\Scripts\\python.exe -m pytest tests/ -v`
2. Run lint:
   - `.venv\\Scripts\\python.exe -m ruff check src tests`
3. Run format check:
   - `.venv\\Scripts\\python.exe -m ruff format --check src tests`
4. Run type checks:
   - `.venv\\Scripts\\python.exe -m mypy src`
5. Run packaging and install smoke checks when CLI, release, or packaging behavior changes:
   - `.venv\\Scripts\\python.exe -m pytest tests/test_packaging.py -q`
   - `.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -q`
   - Verify the GitHub Actions smoke workflows on `ubuntu-latest`, `windows-latest`, and `macos-latest` when workflow logic changes.
6. Run the full CI-like test suite for release-sensitive changes:
   - `.venv\\Scripts\\python.exe -m pytest tests/ -v --cov=devwayfinder --cov-report=xml`

Quality requirements:
- Public functions must be typed.
- Maintain >= 80% test coverage.
- Add or update tests for functional changes.
- Fix discovered technical debt in touched areas when safe.

## 3. Architecture Constraints

- Prefer clean abstractions and separation of concerns.
- Use provider abstraction for LLM backends.
- Keep orchestration logic in summarizer/controller layers.
- Keep analyzers language-focused and composable.
- Favor local-first provider flows; support cloud fallbacks.

## 4. Commit and Change Hygiene

Commit format: Conventional Commits

`<type>(<scope>): <description>`

Allowed types:
- feat, fix, refactor, docs, test, chore, perf, style

Common scopes:
- core, analyzers, providers, cli, generators, config, tests, docs, summarizers, cache

Rules:
- Do not commit generated junk or temporary files.
- Keep commits focused and atomic.
- Do not add broad, redundant documentation.

## 5. Preferred Commands

- Full CI-like test run:
  - `.venv\\Scripts\\python.exe -m pytest tests/ -v --cov=devwayfinder --cov-report=xml`
- Quick sanity:
  - `.venv\\Scripts\\python.exe -m pytest tests/test_cli.py -q`
- Release and smoke validation:
   - `.venv\\Scripts\\python.exe -m pytest tests/test_packaging.py -q`
   - Re-run `.github/workflows/package-smoke.yml` after workflow changes.
   - Re-run `.github/workflows/release.yml` with `publish_target` set to `none` or `testpypi` before production publish changes.

## 6. Current Priorities

- Keep MVP 2.5 stable and green in CI.
- Ensure CLI help tests remain deterministic across environments.
- Maintain provider integration tests with environment-aware skips.
- Continue documentation updates only in authoritative files.
