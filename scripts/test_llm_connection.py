#!/usr/bin/env python
"""DevWayfinder - LLM connection test."""

from __future__ import annotations

import argparse
import asyncio
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


async def test_connection(
    provider: str,
    base_url: str | None,
    model: str | None,
    api_key: str | None,
    timeout: float,
) -> bool:
    """Validate provider health and a sample summary generation call."""
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
    print(f"Model: {config.model_name or 'provider default'}")
    print()

    try:
        print("[1/3] Health check...")
        health = await llm_provider.health_check()
        if not health.healthy:
            print(f"  Failed: {health.message}")
            return False
        print(f"  Passed: {health.message}")

        print()
        print("[2/3] Sample completion...")
        summary = await llm_provider.summarize(
            SummarizationContext(
                module_name="devwayfinder.providers.factory",
                docstrings=["Creates provider instances from runtime configuration."],
                signatures=["create_provider(config: ProviderConfig) -> ModelProvider"],
                imports=["devwayfinder.providers.ollama", "devwayfinder.providers.openai_compat"],
                exports=["create_provider", "supported_providers"],
            )
        )
        if not summary:
            print("  Failed: provider returned an empty summary")
            return False
        print(f"  Passed: {summary[:120]}")

        print()
        print("[3/3] Provider abstraction check...")
        print("  Passed: provider was created through the shared factory")
        return True
    except Exception as exc:
        print(f"  Failed: {exc}")
        return False
    finally:
        close_method = getattr(llm_provider, "close", None)
        if callable(close_method):
            await close_method()


def main() -> None:
    """Parse arguments and execute the connection test."""
    parser = argparse.ArgumentParser(
        description="Test DevWayfinder LLM connectivity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/test_llm_connection.py
    python scripts/test_llm_connection.py --provider ollama --base-url http://localhost:11434
    python scripts/test_llm_connection.py --provider openai --model gpt-4o-mini --api-key sk-...
        """,
    )
    parser.add_argument(
        "--provider",
        default="openai_compat",
        choices=supported_providers(),
        help="Provider to test (default: openai_compat)",
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
