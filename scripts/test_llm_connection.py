#!/usr/bin/env python
"""DevWayfinder - LLM connection test."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from devwayfinder.core.protocols import SummarizationContext
from devwayfinder.providers import create_provider, load_provider_config, supported_providers


def print_header() -> None:
    """Print the script header."""
    print("=" * 60)
    print("DevWayfinder - LLM Connection Test")
    print("=" * 60)
    print()


def print_footer(success: bool) -> None:
    """Print a success or failure footer."""
    print()
    print("=" * 60)
    status = "All tests passed" if success else "Some tests failed"
    print(status)
    print("=" * 60)


def _split_csv_env(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


async def _auto_detect_provider(
    *,
    model: str | None,
    api_key: str | None,
    timeout: float,
) -> tuple[str, str | None]:
    """Detect a reachable provider automatically.

    Preference order favors accessible local setups first:
    openai_compat (LM Studio/textgen-webui/vLLM) -> Ollama -> OpenAI.
    """
    compat_endpoints = [
        os.getenv("DEVWAYFINDER_OPENAI_COMPAT_BASE_URL", "").strip(),
        os.getenv("DEVWAYFINDER_MODEL_BASE_URL", "").strip(),
        "http://127.0.0.1:1234/v1",  # LM Studio
        "http://127.0.0.1:5000/v1",  # text-generation-webui
        "http://127.0.0.1:8000/v1",  # vLLM
    ]
    compat_endpoints = [url for url in compat_endpoints if url]

    for endpoint in compat_endpoints:
        try:
            cfg = load_provider_config(
                provider="openai_compat",
                model_name=model,
                base_url=endpoint,
                api_key=api_key,
                timeout=timeout,
            )
            provider = create_provider(cfg)
            try:
                await provider.health_check()
                return "openai_compat", endpoint
            finally:
                close_method = getattr(provider, "close", None)
                if callable(close_method):
                    await close_method()
        except Exception:
            continue

    ollama_url = os.getenv("DEVWAYFINDER_OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        cfg = load_provider_config(
            provider="ollama",
            model_name=model,
            base_url=ollama_url,
            api_key=api_key,
            timeout=timeout,
        )
        provider = create_provider(cfg)
        try:
            await provider.health_check()
            return "ollama", ollama_url
        finally:
            close_method = getattr(provider, "close", None)
            if callable(close_method):
                await close_method()
    except Exception:
        pass

    if api_key:
        return "openai", os.getenv("DEVWAYFINDER_OPENAI_BASE_URL", "https://api.openai.com/v1")

    return "openai_compat", compat_endpoints[0] if compat_endpoints else None


async def _dynamic_model_summary(
    *,
    provider_name: str,
    base_url: str | None,
    api_key: str | None,
    preferred_model: str | None,
    timeout: float,
    discovered_models: list[str],
) -> tuple[bool, str | None]:
    """Try multiple model candidates until one returns a non-empty summary."""
    candidates: list[str] = []
    if preferred_model:
        candidates.append(preferred_model)

    if provider_name == "ollama":
        env_models = _split_csv_env("DEVWAYFINDER_OLLAMA_MODELS")
        single = os.getenv("DEVWAYFINDER_OLLAMA_MODEL")
        if single:
            env_models.append(single)
        candidates.extend(env_models)
    elif provider_name == "openai_compat":
        env_models = _split_csv_env("DEVWAYFINDER_OPENAI_COMPAT_MODELS")
        single = os.getenv("DEVWAYFINDER_OPENAI_COMPAT_MODEL")
        if single:
            env_models.append(single)
        candidates.extend(env_models)

    candidates.extend([m for m in discovered_models if m])

    if not candidates:
        candidates = [preferred_model or "default"]

    seen: set[str] = set()
    ordered = [m for m in candidates if not (m in seen or seen.add(m))]

    errors: list[str] = []
    for candidate in ordered:
        config = load_provider_config(
            provider=provider_name,
            model_name=candidate,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
        )
        llm_provider = create_provider(config)
        try:
            summary = await llm_provider.summarize(
                SummarizationContext(
                    module_name="devwayfinder.providers.factory",
                    docstrings=["Creates provider instances from runtime configuration."],
                    signatures=["create_provider(config: ProviderConfig) -> ModelProvider"],
                    imports=["devwayfinder.providers.ollama", "devwayfinder.providers.openai_compat"],
                    exports=["create_provider", "supported_providers"],
                )
            )
            if summary.strip():
                print(f"  Passed with model: {candidate}")
                print(f"  Summary: {summary[:120]}")
                return True, candidate
            errors.append(f"{candidate}: empty summary")
        except Exception as exc:
            errors.append(f"{candidate}: {exc}")
        finally:
            close_method = getattr(llm_provider, "close", None)
            if callable(close_method):
                await close_method()

    print("  Failed: no model succeeded")
    for err in errors[:5]:
        print(f"    - {err}")
    return False, ordered[0] if ordered else None


async def _run_single_provider_check(
    *,
    provider: str,
    base_url: str | None,
    model: str | None,
    api_key: str | None,
    timeout: float,
) -> bool:
    """Run health + summarize checks for a single provider config."""
    config = load_provider_config(
        provider=provider,
        model_name=model,
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
    )
    llm_provider = create_provider(config)

    print(f"Provider: {llm_provider.name}")
    print(f"Endpoint: {config.resolved_base_url() or 'n/a'}")
    print(f"Model: {config.model_name or 'provider/default auto'}")
    print()

    try:
        print("[1/3] Health check...")
        health = await llm_provider.health_check()
        if not health.healthy:
            print(f"  Failed: {health.message}")
            return False
        print(f"  Passed: {health.message}")

        discovered_models = []
        if health.model_info:
            discovered_models = [str(m) for m in health.model_info.get("models", []) if m]

        print()
        print("[2/3] Sample completion (dynamic model fallback)...")
        model_ok, selected_model = await _dynamic_model_summary(
            provider_name=provider,
            base_url=base_url,
            api_key=api_key,
            preferred_model=model,
            timeout=timeout,
            discovered_models=discovered_models,
        )
        if not model_ok:
            return False

        print()
        print("[3/3] Provider abstraction check...")
        print(f"  Passed: provider was created through the shared factory (model: {selected_model})")
        return True
    except Exception as exc:
        print(f"  Failed: {exc}")
        return False
    finally:
        close_method = getattr(llm_provider, "close", None)
        if callable(close_method):
            await close_method()


def _auto_provider_attempts(*, api_key: str | None) -> list[tuple[str, str | None]]:
    """Build ordered auto attempts across popular local and remote providers."""
    compat_endpoints = [
        os.getenv("DEVWAYFINDER_OPENAI_COMPAT_BASE_URL", "").strip(),
        os.getenv("DEVWAYFINDER_MODEL_BASE_URL", "").strip(),
        "http://127.0.0.1:1234/v1",  # LM Studio
        "http://127.0.0.1:5000/v1",  # text-generation-webui
        "http://127.0.0.1:8000/v1",  # vLLM
    ]
    compat_endpoints = [u for u in compat_endpoints if u]

    attempts: list[tuple[str, str | None]] = []
    attempts.extend(("openai_compat", endpoint) for endpoint in compat_endpoints)
    attempts.append(("ollama", os.getenv("DEVWAYFINDER_OLLAMA_BASE_URL", "http://localhost:11434")))
    if api_key:
        attempts.append(("openai", os.getenv("DEVWAYFINDER_OPENAI_BASE_URL", "https://api.openai.com/v1")))

    seen: set[tuple[str, str | None]] = set()
    ordered: list[tuple[str, str | None]] = []
    for item in attempts:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


async def test_connection(
    provider: str,
    base_url: str | None,
    model: str | None,
    api_key: str | None,
    timeout: float,
) -> bool:
    """Validate provider health and a sample summary generation call."""
    if provider != "auto":
        return await _run_single_provider_check(
            provider=provider,
            base_url=base_url,
            model=model,
            api_key=api_key,
            timeout=timeout,
        )

    print("Auto mode: trying available providers in order...")
    attempts = _auto_provider_attempts(api_key=api_key)
    failures: list[str] = []

    for candidate_provider, candidate_base_url in attempts:
        effective_base_url = base_url or candidate_base_url
        print(f"\nAttempt: {candidate_provider} @ {effective_base_url or 'default'}")
        ok = await _run_single_provider_check(
            provider=candidate_provider,
            base_url=effective_base_url,
            model=model,
            api_key=api_key,
            timeout=timeout,
        )
        if ok:
            return True
        failures.append(f"{candidate_provider}@{effective_base_url or 'default'}")

    print("\nAll auto attempts failed:")
    for failure in failures[:8]:
        print(f"  - {failure}")
    return False


def main() -> None:
    """Parse arguments and execute the connection test."""
    parser = argparse.ArgumentParser(
        description="Test DevWayfinder LLM connectivity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/test_llm_connection.py
    python scripts/test_llm_connection.py --provider auto
    python scripts/test_llm_connection.py --provider ollama --base-url http://localhost:11434
    python scripts/test_llm_connection.py --provider openai_compat --base-url http://127.0.0.1:1234/v1
    python scripts/test_llm_connection.py --provider openai_compat --base-url http://127.0.0.1:8000/v1
    python scripts/test_llm_connection.py --provider openai --model gpt-4o-mini --api-key sk-...
        """,
    )
    parser.add_argument(
        "--provider",
        default="auto",
        choices=["auto", *supported_providers()],
        help="Provider to test (default: auto; detects openai_compat/ollama/openai)",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Provider base URL (default depends on provider)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model name (uses provider default when supported)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API key for remote official providers",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Timeout for provider calls in seconds",
    )

    args = parser.parse_args()

    print_header()
    success = asyncio.run(
        test_connection(
            provider=args.provider,
            base_url=args.base_url,
            model=args.model,
            api_key=args.api_key,
            timeout=args.timeout,
        )
    )
    print_footer(success)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
