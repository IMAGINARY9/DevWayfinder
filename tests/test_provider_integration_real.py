"""Real provider integration tests (Priority 2a).

These tests exercise live provider endpoints and are skipped unless the
required runtime dependencies are configured.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from devwayfinder.core.protocols import SummarizationContext
from devwayfinder.generators.guide_generator import GenerationConfig, GuideGenerator
from devwayfinder.providers.config import ProviderConfig
from devwayfinder.providers.factory import create_provider


def _split_csv_env(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def _ollama_candidate_models(discovered: list[str]) -> list[str]:
    preferred = _split_csv_env("DEVWAYFINDER_OLLAMA_MODELS")
    single = os.getenv("DEVWAYFINDER_OLLAMA_MODEL")
    if single:
        preferred.append(single)
    candidates = preferred + discovered
    seen: set[str] = set()
    ordered: list[str] = []
    for model in candidates:
        if model and model not in seen:
            seen.add(model)
            ordered.append(model)
    return ordered


def _openai_compat_candidate_models(discovered: list[str]) -> list[str]:
    preferred = _split_csv_env("DEVWAYFINDER_OPENAI_COMPAT_MODELS")
    single = os.getenv("DEVWAYFINDER_OPENAI_COMPAT_MODEL")
    if single:
        preferred.append(single)
    candidates = preferred + discovered + ["default"]
    seen: set[str] = set()
    ordered: list[str] = []
    for model in candidates:
        if model and model not in seen:
            seen.add(model)
            ordered.append(model)
    return ordered


async def _try_ollama_summary(
    *,
    base_url: str,
    models: list[str],
    context: SummarizationContext,
) -> tuple[str, str]:
    failures: list[str] = []
    for model_name in models:
        provider = create_provider(
            ProviderConfig(
                provider="ollama",
                base_url=base_url,
                model_name=model_name,
                max_tokens=96,
                temperature=0.1,
                timeout=90,
            )
        )
        try:
            summary = await provider.summarize(context)
            if summary.strip():
                return summary, model_name
            failures.append(f"{model_name}: empty summary")
        except Exception as exc:  # pragma: no cover - environment dependent
            failures.append(f"{model_name}: {exc}")
        finally:
            await provider.close()
    pytest.skip("No Ollama model succeeded: " + " | ".join(failures[:5]))


async def _try_openai_compat_summary(
    *,
    base_url: str,
    api_key: str | None,
    models: list[str],
    context: SummarizationContext,
) -> tuple[str, str]:
    failures: list[str] = []
    for model_name in models:
        provider = create_provider(
            ProviderConfig(
                provider="openai_compat",
                base_url=base_url,
                api_key=api_key,
                model_name=model_name,
                max_tokens=96,
                temperature=0.1,
                timeout=90,
            )
        )
        try:
            summary = await provider.summarize(context)
            if summary.strip():
                return summary, model_name
            failures.append(f"{model_name}: empty summary")
        except Exception as exc:  # pragma: no cover - environment dependent
            failures.append(f"{model_name}: {exc}")
        finally:
            await provider.close()
    pytest.skip("No OpenAI-compatible model succeeded: " + " | ".join(failures[:5]))


@pytest.mark.integration
@pytest.mark.requires_ollama
@pytest.mark.asyncio
async def test_ollama_health_and_summarize_live() -> None:
    """Validate live Ollama health check and summarization flow."""
    base_url = os.getenv("DEVWAYFINDER_OLLAMA_BASE_URL", "http://localhost:11434")
    config = ProviderConfig(provider="ollama", base_url=base_url, model_name="")
    provider = create_provider(config)

    try:
        health = await provider.health_check()
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"Ollama endpoint unavailable: {exc}")

    models = (health.model_info or {}).get("models", []) if health.model_info else []
    if not models:
        pytest.skip("Ollama reachable but no models are installed")

    candidate_models = _ollama_candidate_models([str(m) for m in models if m])

    context = SummarizationContext(
        module_name="sample/module.py",
        imports=["pathlib", "typing"],
        exports=["build_index", "IndexConfig"],
        docstrings=["Builds onboarding index metadata from analyzed modules."],
    )

    summary, _model_name = await _try_ollama_summary(
        base_url=base_url,
        models=candidate_models,
        context=context,
    )

    assert isinstance(summary, str)
    assert summary.strip() != ""


@pytest.mark.integration
@pytest.mark.requires_ollama
@pytest.mark.asyncio
async def test_ollama_full_pipeline_generate_live() -> None:
    """Run full guide generation pipeline against a live Ollama provider."""
    base_url = os.getenv("DEVWAYFINDER_OLLAMA_BASE_URL", "http://localhost:11434")
    project_path = Path(__file__).parent / "fixtures" / "sample_project"

    probe_provider = create_provider(ProviderConfig(provider="ollama", base_url=base_url, model_name=""))
    try:
        health = await probe_provider.health_check()
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"Ollama endpoint unavailable: {exc}")
    finally:
        await probe_provider.close()

    models = (health.model_info or {}).get("models", []) if health.model_info else []
    if not models:
        pytest.skip("Ollama reachable but no models are installed")

    candidate_models = _ollama_candidate_models([str(m) for m in models if m])

    result = None
    failures: list[str] = []
    for model_name in candidate_models:
        live_provider = create_provider(
            ProviderConfig(
                provider="ollama",
                base_url=base_url,
                model_name=model_name,
                max_tokens=128,
                temperature=0.1,
                timeout=120,
            )
        )
        generator = GuideGenerator(
            project_path=project_path,
            config=GenerationConfig(
                use_llm=True,
                providers=[live_provider],
                include_mermaid=True,
            ),
        )
        try:
            result = await generator.generate()
            break
        except Exception as exc:  # pragma: no cover - environment dependent
            failures.append(f"{model_name}: {exc}")
        finally:
            await live_provider.close()

    if result is None:
        pytest.skip("No Ollama model completed full pipeline: " + " | ".join(failures[:5]))

    assert result.guide is not None
    assert result.modules_analyzed > 0
    assert result.modules_summarized > 0
    assert result.total_time_seconds > 0


@pytest.mark.integration
@pytest.mark.requires_openai_compat
@pytest.mark.asyncio
async def test_openai_compat_health_and_summarize_live() -> None:
    """Validate OpenAI-compatible local endpoints (LM Studio/vLLM/textgen-webui)."""
    endpoint_candidates = [
        os.getenv("DEVWAYFINDER_OPENAI_COMPAT_BASE_URL", "").strip(),
        "http://127.0.0.1:5000/v1",  # text-generation-webui
        "http://127.0.0.1:1234/v1",  # LM Studio
        "http://127.0.0.1:8000/v1",  # vLLM
    ]
    endpoint_candidates = [e for e in endpoint_candidates if e]
    api_key = os.getenv("DEVWAYFINDER_OPENAI_COMPAT_API_KEY") or os.getenv("DEVWAYFINDER_API_KEY")

    discovered_models: list[str] = []
    working_base_url: str | None = None
    health_failures: list[str] = []

    for base_url in endpoint_candidates:
        probe = create_provider(
            ProviderConfig(
                provider="openai_compat",
                base_url=base_url,
                api_key=api_key,
                model_name="",
            )
        )
        try:
            health = await probe.health_check()
            models = (health.model_info or {}).get("models", []) if health.model_info else []
            discovered_models = [str(m) for m in models if m]
            working_base_url = base_url
            break
        except Exception as exc:  # pragma: no cover - environment dependent
            health_failures.append(f"{base_url}: {exc}")
        finally:
            await probe.close()

    if not working_base_url:
        pytest.skip("No OpenAI-compatible endpoint reachable: " + " | ".join(health_failures[:5]))

    candidate_models = _openai_compat_candidate_models(discovered_models)
    if not candidate_models:
        candidate_models = ["default"]

    context = SummarizationContext(
        module_name="src/devwayfinder/generators/guide_generator.py",
        imports=["time", "dataclasses", "typing"],
        exports=["GuideGenerator", "GenerationConfig"],
        docstrings=["Coordinates analysis, summarization, and guide assembly."],
    )

    summary, _model_name = await _try_openai_compat_summary(
        base_url=working_base_url,
        api_key=api_key,
        models=candidate_models,
        context=context,
    )

    assert isinstance(summary, str)
    assert summary.strip() != ""


@pytest.mark.integration
@pytest.mark.requires_openai
@pytest.mark.asyncio
async def test_openai_health_and_summarize_live() -> None:
    """Validate live OpenAI health check and summarization flow."""
    api_key = os.getenv("DEVWAYFINDER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OpenAI API key not configured (DEVWAYFINDER_API_KEY or OPENAI_API_KEY)")

    model_name = os.getenv("DEVWAYFINDER_OPENAI_MODEL", "gpt-4o-mini")
    base_url = os.getenv("DEVWAYFINDER_OPENAI_BASE_URL", "https://api.openai.com/v1")

    provider = create_provider(
        ProviderConfig(
            provider="openai",
            api_key=api_key,
            model_name=model_name,
            base_url=base_url,
            max_tokens=96,
            temperature=0.1,
            timeout=90,
        )
    )

    try:
        health = await provider.health_check()
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"OpenAI endpoint unavailable: {exc}")

    assert health.healthy is True

    context = SummarizationContext(
        module_name="src/devwayfinder/summarizers/controller.py",
        imports=["asyncio", "typing", "dataclasses"],
        exports=["SummarizationController", "SummarizationConfig"],
        docstrings=["Coordinates provider selection, retries, and fallbacks for summaries."],
    )

    try:
        summary = await provider.summarize(context)
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"OpenAI summarize failed for model '{model_name}': {exc}")
    finally:
        await provider.close()

    assert isinstance(summary, str)
    assert summary.strip() != ""


@pytest.mark.integration
@pytest.mark.requires_ollama
@pytest.mark.slow
@pytest.mark.asyncio
async def test_ollama_pipeline_performance_baseline_live() -> None:
    """Capture a basic live performance baseline for sample-project generation."""
    base_url = os.getenv("DEVWAYFINDER_OLLAMA_BASE_URL", "http://localhost:11434")
    project_path = Path(__file__).parent / "fixtures" / "sample_project"

    probe_provider = create_provider(ProviderConfig(provider="ollama", base_url=base_url, model_name=""))
    try:
        health = await probe_provider.health_check()
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"Ollama endpoint unavailable: {exc}")
    finally:
        await probe_provider.close()

    models = (health.model_info or {}).get("models", []) if health.model_info else []
    if not models:
        pytest.skip("Ollama reachable but no models are installed")

    candidate_models = _ollama_candidate_models([str(m) for m in models if m])

    result = None
    elapsed = 0.0
    failures: list[str] = []
    for model_name in candidate_models:
        provider = create_provider(
            ProviderConfig(
                provider="ollama",
                base_url=base_url,
                model_name=model_name,
                max_tokens=128,
                temperature=0.1,
                timeout=120,
            )
        )

        generator = GuideGenerator(
            project_path=project_path,
            config=GenerationConfig(
                use_llm=True,
                providers=[provider],
                include_mermaid=True,
            ),
        )

        start = time.perf_counter()
        try:
            result = await generator.generate()
            elapsed = time.perf_counter() - start
            break
        except Exception as exc:  # pragma: no cover - environment dependent
            failures.append(f"{model_name}: {exc}")
        finally:
            await provider.close()

    if result is None:
        pytest.skip("No Ollama model completed baseline run: " + " | ".join(failures[:5]))

    assert result.modules_analyzed > 0
    assert elapsed > 0
    # Baseline guardrail for the sample fixture on local/remote Ollama.
    assert elapsed < 180
