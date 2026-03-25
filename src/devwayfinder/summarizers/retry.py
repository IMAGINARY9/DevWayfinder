"""Retry logic for provider calls.

This module provides exponential backoff retry management for API calls
that may be transient or rate-limited.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from devwayfinder.core.exceptions import ProviderError

if TYPE_CHECKING:
    from devwayfinder.core.protocols import ModelProvider, SummarizationContext


logger = logging.getLogger(__name__)


class RetryManager:
    """Manages retry logic for provider calls with exponential backoff.
    
    Handles:
    - Retry configuration (max attempts, delays)
    - Exponential backoff calculation
    - Logging and error aggregation
    """

    def __init__(
        self,
        max_retries: int = 2,
        retry_delay: float = 1.0,
        backoff_factor: float = 2.0,
    ) -> None:
        """Initialize retry manager.

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (seconds)
            backoff_factor: Multiplier for exponential backoff
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor

    async def call_with_retry(
        self,
        provider: ModelProvider,
        context: SummarizationContext,
    ) -> str:
        """Call provider with automatic retry and exponential backoff.

        Args:
            provider: Provider to call
            context: Summarization context

        Returns:
            Generated summary

        Raises:
            ProviderError: If all retries fail
        """
        last_error: Exception | None = None
        delay = self.retry_delay

        for attempt in range(self.max_retries):
            try:
                result = await provider.summarize(context)
                if attempt > 0:
                    logger.info(
                        "Provider %s succeeded on retry attempt %d",
                        provider.name,
                        attempt,
                    )
                return result
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    logger.warning(
                        "Provider %s failed (attempt %d/%d), retrying in %.2fs: %s",
                        provider.name,
                        attempt + 1,
                        self.max_retries,
                        delay,
                        e,
                    )
                    await asyncio.sleep(delay)
                    delay *= self.backoff_factor
                else:
                    logger.error(
                        "Provider %s failed (final attempt %d/%d)",
                        provider.name,
                        attempt + 1,
                        self.max_retries,
                    )

        raise ProviderError(
            f"{provider.name}: Failed after {self.max_retries} attempts: {last_error}"
        )
