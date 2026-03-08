"""Official OpenAI provider implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from devwayfinder.core.exceptions import MissingConfigError
from devwayfinder.providers.openai_compat import OpenAICompatProvider

if TYPE_CHECKING:
    from devwayfinder.providers.config import ProviderConfig


class OpenAIProvider(OpenAICompatProvider):
    """Provider targeting the official OpenAI API."""

    provider_name = "openai"

    def __init__(self, config: ProviderConfig) -> None:
        if not config.api_key:
            raise MissingConfigError(
                "model.api_key",
                "Set DEVWAYFINDER_API_KEY or provide --api-key for official OpenAI access.",
            )
        super().__init__(config)

    def _model_name(self) -> str:
        if not self.config.model_name:
            raise MissingConfigError(
                "model.model_name",
                "Provide --model or set DEVWAYFINDER_MODEL_NAME for official OpenAI access.",
            )
        return self.config.model_name
