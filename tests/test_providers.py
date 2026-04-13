"""Tests for provider implementations."""

from __future__ import annotations

import json

import httpx
import pytest
from typer.testing import CliRunner

from devwayfinder.cli.app import app
from devwayfinder.core.exceptions import ConnectionError as ProviderConnectionError
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
async def test_openai_compat_uses_discovered_model_for_completion(respx_mock: object) -> None:
    """Completion should use model discovered during health-check when no model is configured."""
    captured_payload: dict[str, object] = {}

    respx_mock.get("http://127.0.0.1:5000/v1/models").mock(
        return_value=httpx.Response(200, json={"data": [{"id": "discovered-model"}]})
    )

    def _capture(request: httpx.Request) -> httpx.Response:
        captured_payload.update(json.loads(request.content.decode("utf-8")))
        return httpx.Response(200, json={"choices": [{"message": {"content": "summary"}}]})

    respx_mock.post("http://127.0.0.1:5000/v1/chat/completions").mock(side_effect=_capture)

    provider = OpenAICompatProvider(ProviderConfig(provider="openai_compat", model_name=None))
    await provider.health_check()
    summary = await provider.summarize(SummarizationContext(module_name="src/main.py"))

    assert summary == "summary"
    assert captured_payload.get("model") == "discovered-model"
    await provider.close()


@pytest.mark.asyncio
async def test_openai_compat_extracts_nested_content_blocks(respx_mock: object) -> None:
    """Completion parsing should support content arrays used by some local providers."""
    respx_mock.post("http://127.0.0.1:5000/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": [{"type": "text", "text": "Detailed onboarding summary."}]
                        }
                    }
                ]
            },
        )
    )

    provider = OpenAICompatProvider(ProviderConfig(provider="openai_compat"))
    summary = await provider.summarize(SummarizationContext(module_name="src/main.py"))

    assert summary == "Detailed onboarding summary."
    await provider.close()


@pytest.mark.asyncio
async def test_openai_compat_extracts_responses_api_shape(respx_mock: object) -> None:
    """Completion parsing should support response-style output payloads."""
    respx_mock.post("http://127.0.0.1:5000/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Responses summary text."}],
                    }
                ]
            },
        )
    )

    provider = OpenAICompatProvider(ProviderConfig(provider="openai_compat"))
    summary = await provider.summarize(SummarizationContext(module_name="src/main.py"))

    assert summary == "Responses summary text."
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


@pytest.mark.asyncio
async def test_ollama_uses_discovered_model_for_completion(respx_mock: object) -> None:
    """Ollama completion should default to the model discovered during health-check."""
    captured_payload: dict[str, object] = {}

    respx_mock.get("http://localhost:11434/api/tags").mock(
        return_value=httpx.Response(200, json={"models": [{"name": "qwen2.5:7b"}]})
    )

    def _capture(request: httpx.Request) -> httpx.Response:
        captured_payload.update(json.loads(request.content.decode("utf-8")))
        return httpx.Response(200, json={"response": "ok"})

    respx_mock.post("http://localhost:11434/api/generate").mock(side_effect=_capture)

    provider = OllamaProvider(ProviderConfig(provider="ollama", model_name=None))
    await provider.health_check()
    summary = await provider.summarize(SummarizationContext(module_name="src/main.py"))

    assert summary == "ok"
    assert captured_payload.get("model") == "qwen2.5:7b"
    assert captured_payload.get("think") is False
    await provider.close()


@pytest.mark.asyncio
async def test_ollama_extracts_message_content_fallback(respx_mock: object) -> None:
    """Ollama parsing should support chat-style message.content fallback."""
    respx_mock.post("http://localhost:11434/api/generate").mock(
        return_value=httpx.Response(200, json={"message": {"content": "chat variant summary"}})
    )

    provider = OllamaProvider(ProviderConfig(provider="ollama"))
    summary = await provider.summarize(SummarizationContext(module_name="src/main.py"))

    assert summary == "chat variant summary"
    await provider.close()


@pytest.mark.asyncio
async def test_ollama_extracts_thinking_fallback(respx_mock: object) -> None:
    """Ollama parsing should use thinking text when response text is missing."""
    respx_mock.post("http://localhost:11434/api/generate").mock(
        return_value=httpx.Response(200, json={"response": "", "thinking": "summary fallback"})
    )

    provider = OllamaProvider(ProviderConfig(provider="ollama"))
    summary = await provider.summarize(SummarizationContext(module_name="src/main.py"))

    assert summary == "summary fallback"
    await provider.close()


@pytest.mark.asyncio
async def test_openai_compat_error_includes_method_path_and_status(respx_mock: object) -> None:
    """Provider errors should include HTTP method, path, and status code for diagnostics."""
    respx_mock.post("http://127.0.0.1:5000/v1/chat/completions").mock(
        return_value=httpx.Response(404, json={"error": "not found"})
    )

    provider = OpenAICompatProvider(ProviderConfig(provider="openai_compat", model_name="missing"))

    with pytest.raises(ProviderConnectionError) as exc:
        await provider.summarize(SummarizationContext(module_name="src/main.py"))

    message = str(exc.value)
    assert "POST /chat/completions -> HTTP 404" in message
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
