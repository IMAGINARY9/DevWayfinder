"""Tests for provider implementations."""

from __future__ import annotations

import httpx
import pytest
from typer.testing import CliRunner

from devwayfinder.cli.app import app
from devwayfinder.core.protocols import SummarizationContext
from devwayfinder.providers import create_provider
from devwayfinder.providers.config import ProviderConfig, normalize_provider_name
from devwayfinder.providers.heuristic import HeuristicProvider
from devwayfinder.providers.ollama import OllamaProvider
from devwayfinder.providers.openai import OpenAIProvider
from devwayfinder.providers.openai_compat import OpenAICompatProvider

runner = CliRunner()


@pytest.mark.asyncio
async def test_heuristic_provider_summarize() -> None:
    """Heuristic provider should generate a deterministic summary."""
    provider = HeuristicProvider()
    summary = await provider.summarize(
        SummarizationContext(
            module_name="project.main",
            docstrings=["Application bootstrap module."],
            signatures=["main() -> None"],
            imports=["sys", "config"],
            exports=["main"],
        )
    )

    assert "project.main" in summary
    assert "Application bootstrap module." in summary


@pytest.mark.asyncio
async def test_openai_compat_health_check(respx_mock: object) -> None:
    """OpenAI-compatible provider should use the models endpoint for health checks."""
    respx_mock.get("http://127.0.0.1:5000/v1/models").mock(
        return_value=httpx.Response(
            200,
            json={"data": [{"id": "local-model"}]},
        )
    )
    provider = OpenAICompatProvider(ProviderConfig(provider="openai_compat"))

    health = await provider.health_check()

    assert health.healthy is True
    assert health.model_info["models"] == ["local-model"]
    await provider.close()


@pytest.mark.asyncio
async def test_ollama_health_check(respx_mock: object) -> None:
    """Ollama provider should report available models from the tags endpoint."""
    respx_mock.get("http://localhost:11434/api/tags").mock(
        return_value=httpx.Response(
            200,
            json={"models": [{"name": "mistral:7b"}]},
        )
    )
    provider = OllamaProvider(ProviderConfig(provider="ollama"))

    health = await provider.health_check()

    assert health.healthy is True
    assert health.model_info["models"] == ["mistral:7b"]
    await provider.close()


def test_factory_creates_official_openai_provider() -> None:
    """Factory should create the official provider when requested."""
    provider = create_provider(
        ProviderConfig(
            provider="openai",
            model_name="gpt-4o-mini",
            api_key="test-key",
        )
    )

    assert isinstance(provider, OpenAIProvider)


def test_provider_alias_normalization() -> None:
    """Known provider aliases should map to canonical provider names."""
    assert normalize_provider_name("openai-compatible") == "openai_compat"
    assert normalize_provider_name("vllm") == "openai_compat"


def test_cli_test_model_heuristic() -> None:
    """The CLI model test should work in offline heuristic mode."""
    result = runner.invoke(app, ["test-model", "--provider", "heuristic", "--no-completion"])

    assert result.exit_code == 0
    assert "Provider is healthy" in result.stdout
