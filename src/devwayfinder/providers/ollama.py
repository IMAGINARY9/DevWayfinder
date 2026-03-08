"""Ollama provider implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from devwayfinder.core.protocols import HealthStatus, SummarizationContext
from devwayfinder.providers.base import BaseProvider

if TYPE_CHECKING:
    from devwayfinder.providers.config import ProviderConfig


class OllamaProvider(BaseProvider):
    """Provider for Ollama's local inference API."""

    provider_name = "ollama"

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)

    @property
    def available(self) -> bool:
        """Ollama requires only a local or remote API base URL."""
        return self.config.resolved_base_url() is not None

    def _model_name(self) -> str:
        return self.config.model_name or "mistral:7b"

    async def summarize(self, context: SummarizationContext) -> str:
        """Generate a summary using Ollama's generate API."""
        response = await self._request(
            "POST",
            "/api/generate",
            json_body={
                "model": self._model_name(),
                "prompt": (
                    "Summarize this code module for developer onboarding in 2-4 sentences.\n\n"
                    f"{context.to_prompt_context()}"
                ),
                "stream": False,
                "options": {
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_tokens,
                },
            },
        )
        payload = response.json()
        result = payload.get("response", "")
        return result.strip() if isinstance(result, str) else ""

    async def health_check(self) -> HealthStatus:
        """Check that the Ollama API is reachable and returns tags."""
        response, latency_ms = await self._timed_health_request("GET", "/api/tags")
        payload = response.json()
        models = [item.get("name") for item in payload.get("models", []) if isinstance(item, dict)]
        message = "Ollama endpoint reachable"
        if models:
            message += f" ({len(models)} model(s) available)"
        return HealthStatus(
            healthy=True,
            message=message,
            latency_ms=latency_ms,
            model_info={"models": models[:10]},
        )
