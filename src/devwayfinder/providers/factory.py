"""Factory for creating configured model providers."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from devwayfinder.providers.config import ProviderConfig, normalize_provider_name
from devwayfinder.providers.heuristic import HeuristicProvider
from devwayfinder.providers.ollama import OllamaProvider
from devwayfinder.providers.openai import OpenAIProvider
from devwayfinder.providers.openai_compat import OpenAICompatProvider

if TYPE_CHECKING:
    from devwayfinder.core.protocols import ModelProvider


PROVIDER_REGISTRY = {
    "heuristic": HeuristicProvider,
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
    "openai_compat": OpenAICompatProvider,
}


def create_provider(config: ProviderConfig) -> ModelProvider:
    """Create a provider instance for the requested configuration."""
    normalized_provider = normalize_provider_name(config.provider)
    resolved_config = config.model_copy(update={"provider": normalized_provider})
    provider_class = PROVIDER_REGISTRY[normalized_provider]
    return cast("ModelProvider", provider_class(resolved_config))


def supported_providers() -> list[str]:
    """Return the list of canonical provider names."""
    return sorted(PROVIDER_REGISTRY)
