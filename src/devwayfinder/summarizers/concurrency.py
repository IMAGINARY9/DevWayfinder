"""Concurrency management for batch operations.

This module provides semaphore-based concurrency control for managing
multiple concurrent summarization tasks with configurable limits.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ConcurrencyPool:
    """Manages concurrent task execution with semaphore limits.

    Handles:
    - Semaphore-based concurrency control
    - Task batching
    - Error collection from concurrent operations
    """

    def __init__(self, max_concurrent: int = 5) -> None:
        """Initialize concurrency pool.

        Args:
            max_concurrent: Maximum number of concurrent tasks
        """
        self.max_concurrent = max_concurrent
        self._semaphore: asyncio.Semaphore | None = None

    @property
    def semaphore(self) -> asyncio.Semaphore:
        """Lazy semaphore initialization."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore

    async def run_concurrent(
        self, tasks: tuple[tuple[str, Callable[[], Awaitable[T]]], ...]
    ) -> dict[str, T | Exception]:
        """Run tasks concurrently with semaphore control.

        Args:
            tasks: List of (key, callable) tuples

        Returns:
            Dict mapping keys to results or exceptions
        """

        async def _run_with_semaphore(
            key: str,
            coro_fn: Callable[[], Awaitable[T]],
        ) -> tuple[str, T | Exception]:
            async with self.semaphore:
                try:
                    result = await coro_fn()
                    return key, result
                except Exception as e:
                    return key, e

        # Create coroutines
        coros = [_run_with_semaphore(key, fn) for key, fn in tasks]

        # Run concurrently
        results = await asyncio.gather(*coros, return_exceptions=False)

        # Convert to dict
        output: dict[str, T | Exception] = {}
        for key, result in results:
            output[key] = result

        return output

    async def run_batch(
        self,
        batch_coros: list[Awaitable[T]],
    ) -> list[T | Exception]:
        """Run a batch of coroutines with semaphore control.

        Args:
            batch_coros: List of coroutines to run

        Returns:
            List of results (may contain exceptions)
        """

        async def _with_semaphore(coro: Awaitable[T]) -> T | Exception:
            async with self.semaphore:
                try:
                    return await coro
                except Exception as e:
                    return e

        semaphore_coros = [_with_semaphore(coro) for coro in batch_coros]
        gathered = await asyncio.gather(*semaphore_coros, return_exceptions=False)
        return gathered

    def reset(self) -> None:
        """Reset the semaphore (mainly for testing)."""
        self._semaphore = None
