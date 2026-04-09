"""OpenAI-compatible provider implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from devwayfinder.core.protocols import HealthStatus, SummarizationContext
from devwayfinder.providers.base import BaseProvider

if TYPE_CHECKING:
    from devwayfinder.providers.config import ProviderConfig


class OpenAICompatProvider(BaseProvider):
    """Provider for text-generation-webui, vLLM, and other OpenAI-style APIs."""

    provider_name = "openai_compat"

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        self._discovered_model: str | None = None

    @property
    def available(self) -> bool:
        """OpenAI-compatible providers require only a base URL."""
        return self.config.resolved_base_url() is not None

    def _headers(self) -> dict[str, str]:
        headers = super()._headers()
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def _model_name(self) -> str:
        return self.config.model_name or self._discovered_model or "default"

    async def summarize(self, context: SummarizationContext) -> str:
        """Generate a summary using chat completions."""
        response = await self._request(
            "POST",
            "/chat/completions",
            json_body={
                "model": self._model_name(),
                "messages": self._prompt_messages(context),
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            },
        )
        payload = response.json()
        return _extract_chat_content(payload)

    async def health_check(self) -> HealthStatus:
        """Check model discovery on the configured endpoint."""
        response, latency_ms = await self._timed_health_request("GET", "/models")
        payload = response.json()
        models = [item.get("id") for item in payload.get("data", []) if isinstance(item, dict)]
        discovered = next(
            (str(model) for model in models if isinstance(model, str) and model), None
        )
        if discovered:
            self._discovered_model = discovered

        message = "OpenAI-compatible endpoint reachable"
        if models:
            message += f" ({len(models)} model(s) listed)"
        return HealthStatus(
            healthy=True,
            message=message,
            latency_ms=latency_ms,
            model_info={"models": models[:10]},
        )


def _extract_chat_content(payload: dict[str, Any]) -> str:
    """Extract message text from chat-completion and response-style payloads."""
    candidates: list[str] = []

    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        pass
    else:
        first_choice = choices[0]
        if isinstance(first_choice, dict):
            message = first_choice.get("message")
            candidates.extend(_collect_text_candidates(message))
            candidates.extend(_collect_text_candidates(first_choice.get("text")))
            candidates.extend(_collect_text_candidates(first_choice.get("reasoning")))
            candidates.extend(_collect_text_candidates(first_choice.get("reasoning_content")))
            candidates.extend(_collect_text_candidates(first_choice.get("output_text")))

    # OpenAI Responses API style payloads can expose text at top level.
    candidates.extend(_collect_text_candidates(payload.get("output_text")))
    candidates.extend(_collect_text_candidates(payload.get("text")))
    candidates.extend(_collect_text_candidates(payload.get("response")))
    candidates.extend(_collect_text_candidates(payload.get("output")))

    for candidate in candidates:
        cleaned = candidate.strip()
        if cleaned:
            return cleaned

    return ""


def _collect_text_candidates(value: Any) -> list[str]:
    """Collect candidate text fragments from nested response payload values."""
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

        # Common structured content shapes.
        for key in (
            "content",
            "text",
            "output_text",
            "reasoning",
            "reasoning_content",
            "message",
            "value",
            "arguments",
        ):
            if key in value:
                dict_collected.extend(_collect_text_candidates(value.get(key)))

        # Extract text blocks from response/message arrays.
        nested_type = value.get("type")
        if nested_type in {"text", "output_text", "message", "reasoning"}:
            dict_collected.extend(_collect_text_candidates(value.get("text")))
            dict_collected.extend(_collect_text_candidates(value.get("content")))

        return dict_collected

    return []
