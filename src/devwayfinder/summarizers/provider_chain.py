"""Provider chain and fallback orchestration.

This module manages the provider chain strategy for fallback when
primary providers fail.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from devwayfinder.summarizers.output_sanitizer import sanitize_summary_text

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
        if not self.providers:
            logger.debug(
                "No providers configured; skipping provider chain for %s", context.module_name
            )
            return "none", None

        last_error: str | None = None

        # Try each configured provider in order
        for provider in self.providers:
            try:
                raw_summary = await self._invoke_provider(provider_call, provider, context)
                summary = sanitize_summary_text(raw_summary)

                if not self._has_text(summary):
                    raise ValueError("Provider returned empty or non-report-safe summary")

                enriched_summary = await self._enforce_quality_threshold(
                    provider_call,
                    provider,
                    context,
                    summary.strip(),
                )

                logger.info("Provider %s succeeded", provider.name)
                return provider.name, enriched_summary

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

    async def _invoke_provider(
        self,
        provider_call: ProviderCall | None,
        provider: ModelProvider,
        context: SummarizationContext,
    ) -> str:
        """Execute provider call with optional retry manager support."""
        if provider_call is not None:
            return await provider_call(provider, context)

        if self.retry_manager:
            return await self.retry_manager.call_with_retry(provider, context)

        return await provider.summarize(context)

    async def _enforce_quality_threshold(
        self,
        provider_call: ProviderCall | None,
        provider: ModelProvider,
        context: SummarizationContext,
        summary: str,
    ) -> str:
        """Retry once with stronger hints when a summary is below configured quality threshold."""
        minimum_words = self._minimum_words(context)
        if minimum_words <= 0:
            return summary

        if self._word_count(summary) >= minimum_words:
            return summary

        logger.info(
            "Provider %s returned short summary (%d words < %d), retrying with quality hints",
            provider.name,
            self._word_count(summary),
            minimum_words,
        )

        retry_context = self._build_quality_retry_context(context, minimum_words)
        retry_raw_summary = await self._invoke_provider(provider_call, provider, retry_context)
        retry_summary = sanitize_summary_text(retry_raw_summary)
        if not self._has_text(retry_summary):
            raise ValueError("Provider returned empty summary after quality retry")

        cleaned_retry_summary = retry_summary.strip()
        retry_words = self._word_count(cleaned_retry_summary)
        if retry_words < minimum_words:
            raise ValueError(
                f"Provider summary below quality threshold ({retry_words} < {minimum_words} words)"
            )

        return cleaned_retry_summary

    @staticmethod
    def _word_count(text: str) -> int:
        """Count words in a summary."""
        return len([token for token in text.split() if token.strip()])

    @staticmethod
    def _minimum_words(context: SummarizationContext) -> int:
        """Extract minimum summary word threshold from context metadata."""
        value = context.metadata.get("minimum_summary_words", 0)
        if isinstance(value, int):
            return max(0, value)
        if isinstance(value, str) and value.strip().isdigit():
            return max(0, int(value.strip()))
        return 0

    def _build_quality_retry_context(
        self,
        context: SummarizationContext,
        minimum_words: int,
    ) -> SummarizationContext:
        """Add explicit expansion hints for quality retries."""
        existing = context.metadata.get("prompt_hints")
        prompt_hints = [
            str(item).strip()
            for item in (existing if isinstance(existing, list) else [])
            if str(item).strip()
        ]
        prompt_hints.append(
            "Expand with concrete behavior and onboarding guidance. "
            f"Use at least {minimum_words} words."
        )
        prompt_hints.append(
            "Return only the final onboarding summary and omit reasoning steps, task breakdowns, "
            "or system/process commentary."
        )

        return context.with_updated_metadata(
            prompt_hints=prompt_hints,
            quality_retry=True,
        )

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
