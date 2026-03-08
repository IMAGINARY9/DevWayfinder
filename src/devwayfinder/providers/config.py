"""Provider configuration helpers."""

from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProviderName = Literal["ollama", "openai", "openai_compat", "heuristic"]


class ProviderConfig(BaseModel):
    """Runtime configuration for an LLM provider."""

    model_config = ConfigDict(str_strip_whitespace=True)

    provider: ProviderName = "openai_compat"
    model_name: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    timeout: float = 120.0
    max_tokens: int = 512
    temperature: float = 0.3
    extra_headers: dict[str, str] = Field(default_factory=dict)

    def resolved_base_url(self) -> str | None:
        """Return the effective base URL for the configured provider."""
        if self.base_url:
            return self.base_url.rstrip("/")

        defaults: dict[ProviderName, str | None] = {
            "openai_compat": "http://127.0.0.1:5000/v1",
            "openai": "https://api.openai.com/v1",
            "ollama": "http://localhost:11434",
            "heuristic": None,
        }
        return defaults[self.provider]


def load_provider_config(
    *,
    provider: str | None = None,
    model_name: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    timeout: float | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> ProviderConfig:
    """Load provider configuration from explicit values and environment variables."""

    env_provider = os.getenv("DEVWAYFINDER_MODEL_PROVIDER")
    env_model_name = os.getenv("DEVWAYFINDER_MODEL_NAME")
    env_base_url = os.getenv("DEVWAYFINDER_MODEL_BASE_URL")
    env_api_key = os.getenv("DEVWAYFINDER_API_KEY")
    env_timeout = os.getenv("DEVWAYFINDER_MODEL_TIMEOUT")
    env_max_tokens = os.getenv("DEVWAYFINDER_MODEL_MAX_TOKENS")
    env_temperature = os.getenv("DEVWAYFINDER_MODEL_TEMPERATURE")

    resolved_provider = normalize_provider_name(provider or env_provider or "openai_compat")

    return ProviderConfig(
        provider=resolved_provider,
        model_name=model_name if model_name is not None else env_model_name,
        base_url=base_url if base_url is not None else env_base_url,
        api_key=api_key if api_key is not None else env_api_key,
        timeout=float(timeout if timeout is not None else env_timeout or 120.0),
        max_tokens=int(max_tokens if max_tokens is not None else env_max_tokens or 512),
        temperature=float(temperature if temperature is not None else env_temperature or 0.3),
    )


def normalize_provider_name(provider: str) -> ProviderName:
    """Normalize provider aliases to canonical provider names."""
    normalized = provider.strip().lower().replace("-", "_")
    aliases = {
        "textgen": "openai_compat",
        "text_generation_webui": "openai_compat",
        "openai_compatible": "openai_compat",
        "compat": "openai_compat",
        "vllm": "openai_compat",
    }
    canonical = aliases.get(normalized, normalized)
    valid_providers = {"ollama", "openai", "openai_compat", "heuristic"}
    if canonical not in valid_providers:
        valid_display = ", ".join(sorted(valid_providers))
        raise ValueError(f"Unsupported provider '{provider}'. Supported providers: {valid_display}")
    return canonical  # type: ignore[return-value]
