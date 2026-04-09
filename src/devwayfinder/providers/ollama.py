"""Ollama provider implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from devwayfinder.core.protocols import HealthStatus, SummarizationContext
from devwayfinder.providers.base import BaseProvider

if TYPE_CHECKING:
    from devwayfinder.providers.config import ProviderConfig


class OllamaProvider(BaseProvider):
    """Provider for Ollama's local inference API."""

    provider_name = "ollama"

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        self._discovered_model: str | None = None

    @property
    def available(self) -> bool:
        """Ollama requires only a local or remote API base URL."""
        return self.config.resolved_base_url() is not None

    def _model_name(self) -> str:
        return self.config.model_name or self._discovered_model or "mistral:7b"

    async def summarize(self, context: SummarizationContext) -> str:
        """Generate a summary using Ollama's generate API."""
        quality_profile = context.metadata.get("quality_profile", "balanced")
        minimum_words = context.metadata.get("minimum_summary_words", 0)
        min_words_value = 0
        if isinstance(minimum_words, int):
            min_words_value = max(0, minimum_words)
        elif isinstance(minimum_words, str) and minimum_words.strip().isdigit():
            min_words_value = max(0, int(minimum_words.strip()))

        length_instruction = (
            f"Write at least {min_words_value} words."
            if min_words_value > 0
            else "Write 2-4 sentences."
        )

        response = await self._request(
            "POST",
            "/api/generate",
            json_body={
                "model": self._model_name(),
                "prompt": (
                    "You generate onboarding summaries for developers joining an unfamiliar"
                    " codebase. Focus on responsibilities, runtime behavior, and practical"
                    " navigation guidance. "
                    f"Quality profile: {quality_profile}. {length_instruction}\n\n"
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
        return _extract_ollama_content(payload)

    async def health_check(self) -> HealthStatus:
        """Check that the Ollama API is reachable and returns tags."""
        response, latency_ms = await self._timed_health_request("GET", "/api/tags")
        payload = response.json()
        models = [item.get("name") for item in payload.get("models", []) if isinstance(item, dict)]
        discovered = next(
            (str(model) for model in models if isinstance(model, str) and model), None
        )
        if discovered:
            self._discovered_model = discovered

        message = "Ollama endpoint reachable"
        if models:
            message += f" ({len(models)} model(s) available)"
        return HealthStatus(
            healthy=True,
            message=message,
            latency_ms=latency_ms,
            model_info={"models": models[:10]},
        )


def _extract_ollama_content(payload: dict[str, Any]) -> str:
    """Extract best-effort completion text from Ollama response payloads."""
    candidates: list[str] = []

    # Ollama /api/generate shape.
    candidates.extend(_collect_text_candidates(payload.get("response")))

    # Ollama /api/chat shape.
    candidates.extend(_collect_text_candidates(payload.get("message")))

    # OpenAI-compatible proxy variants.
    candidates.extend(_collect_text_candidates(payload.get("choices")))
    candidates.extend(_collect_text_candidates(payload.get("output_text")))
    candidates.extend(_collect_text_candidates(payload.get("text")))

    for candidate in candidates:
        cleaned = candidate.strip()
        if cleaned:
            return cleaned

    return ""


def _collect_text_candidates(value: Any) -> list[str]:
    """Collect candidate text fragments from nested payload values."""
    if value is None:
        return []

    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []

    if isinstance(value, list):
        list_collected: list[str] = []
        for item in value:
            list_collected.extend(_collect_text_candidates(item))
        return list_collected

    if isinstance(value, dict):
        dict_collected: list[str] = []
        for key in (
            "response",
            "content",
            "text",
            "output_text",
            "message",
            "reasoning",
            "reasoning_content",
        ):
            if key in value:
                dict_collected.extend(_collect_text_candidates(value.get(key)))
        return dict_collected

    return []
