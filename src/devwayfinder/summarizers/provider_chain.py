"""Provider chain and fallback orchestration.

This module manages the provider chain strategy for fallback when
primary providers fail.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from devwayfinder.core.protocols import ModelProvider, SummarizationContext
    from devwayfinder.summarizers.retry import RetryManager

    ProviderCall = Callable[[ModelProvider, SummarizationContext], Awaitable[str]]


logger = logging.getLogger(__name__)


class ProviderChain:
    """Orchestrates provider selection and fallback chain.

    Handles:
    - Provider chain configuration and ordering
    - Fallback logic when providers fail
    - Provider health and error tracking
    """

    def __init__(
        self,
        providers: list[ModelProvider] | None = None,
        use_heuristic_fallback: bool = True,
        retry_manager: RetryManager | None = None,
    ) -> None:
        """Initialize provider chain.

        Args:
            providers: Ordered list of providers to try
            use_heuristic_fallback: Whether to use heuristic fallback
            retry_manager: Optional retry manager for API calls
        """
        self.providers = providers or []
        self.use_heuristic_fallback = use_heuristic_fallback
        self.retry_manager = retry_manager

    async def call_provider_chain(
        self,
        provider_call: ProviderCall | None,
        context: SummarizationContext,
    ) -> tuple[str, str | None]:
        """Call providers in order with fallback.

        Args:
            provider_call: Async callable that takes (provider, context) and returns summary
            context: Summarization context

        Returns:
            Tuple of (provider_name, summary or None if all failed)
        """
        last_error: str | None = None

        # Try each configured provider in order
        for provider in self.providers:
            try:
                if provider_call is not None:
                    summary = await provider_call(provider, context)
                    if not self._has_text(summary):
                        raise ValueError("Provider returned empty summary")
                    logger.info("Provider %s succeeded", provider.name)
                    return provider.name, summary.strip()

                if self.retry_manager:
                    summary = await self.retry_manager.call_with_retry(provider, context)
                else:
                    summary = await provider.summarize(context)

                if not self._has_text(summary):
                    raise ValueError("Provider returned empty summary")

                logger.info("Provider %s succeeded", provider.name)
                return provider.name, summary.strip()

            except Exception as e:
                last_error = f"{provider.name}: {e}"
                logger.warning("Provider %s failed: %s", provider.name, e)
                continue

        # All providers failed - return None summary
        logger.error("All providers failed. Last error: %s", last_error)
        return "none", None

    @staticmethod
    def _has_text(summary: str | None) -> bool:
        """Check whether a provider response contains useful content."""
        return bool(summary and summary.strip())

    def should_use_heuristic(self) -> bool:
        """Check if heuristic fallback is enabled.

        Returns:
            True if heuristic fallback should be used
        """
        return self.use_heuristic_fallback

    def add_provider(self, provider: ModelProvider) -> None:
        """Add provider to chain.

        Args:
            provider: Provider to add
        """
        self.providers.append(provider)
        logger.debug("Added provider: %s", provider.name)

    def remove_provider(self, provider_name: str) -> bool:
        """Remove provider from chain by name.

        Args:
            provider_name: Name of provider to remove

        Returns:
            True if provider was removed, False if not found
        """
        for i, provider in enumerate(self.providers):
            if provider.name == provider_name:
                self.providers.pop(i)
                logger.debug("Removed provider: %s", provider_name)
                return True
        return False

    def clear(self) -> None:
        """Clear all providers from chain."""
        self.providers.clear()
        logger.debug("Cleared all providers from chain")

    async def close_all(self) -> None:
        """Close all provider connections."""
        for provider in self.providers:
            if hasattr(provider, "close"):
                try:
                    await provider.close()
                    logger.debug("Closed provider: %s", provider.name)
                except Exception as e:
                    logger.warning("Error closing provider %s: %s", provider.name, e)

    def get_provider_names(self) -> list[str]:
        """Get names of all providers in chain.

        Returns:
            List of provider names
        """
        return [p.name for p in self.providers]
