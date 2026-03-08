"""Base classes for LLM providers."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import httpx

from devwayfinder.core.exceptions import ConnectionError, MissingConfigError, RateLimitError
from devwayfinder.providers.config import ProviderConfig

if TYPE_CHECKING:
    from devwayfinder.core.protocols import HealthStatus, SummarizationContext
    from devwayfinder.providers.config import ProviderConfig


class BaseProvider(ABC):
    """Shared functionality for concrete provider implementations."""

    provider_name: str

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        """Provider identifier."""
        return self.provider_name

    @property
    def available(self) -> bool:
        """Whether the provider appears configurable enough to use."""
        return True

    async def close(self) -> None:
        """Release underlying HTTP resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Create or return the cached async HTTP client."""
        if self._client is None:
            base_url = self.config.resolved_base_url()
            headers = self._headers()
            self._client = httpx.AsyncClient(
                base_url=base_url or "",
                headers=headers,
                timeout=self.config.timeout,
            )
        return self._client

    def _headers(self) -> dict[str, str]:
        """Build request headers for the provider."""
        headers = {"Content-Type": "application/json"}
        headers.update(self.config.extra_headers)
        return headers

    def _require_base_url(self) -> str:
        """Validate and return the provider base URL."""
        base_url = self.config.resolved_base_url()
        if not base_url:
            raise MissingConfigError(
                "model.base_url",
                f"Set DEVWAYFINDER_MODEL_BASE_URL or provide --base-url for {self.name}.",
            )
        return base_url

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Perform an HTTP request with consistent error handling."""
        client = await self._get_client()
        self._require_base_url()

        try:
            response = await client.request(method, path, json=json_body)
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                raise RateLimitError(self.name, float(retry_after) if retry_after else None)
            response.raise_for_status()
            return response
        except RateLimitError:
            raise
        except httpx.HTTPError as exc:
            raise ConnectionError(self.name, str(client.base_url), str(exc)) from exc

    async def _timed_health_request(self, method: str, path: str) -> tuple[httpx.Response, float]:
        """Execute a health request and return response with latency."""
        start = time.perf_counter()
        response = await self._request(method, path)
        latency_ms = (time.perf_counter() - start) * 1000
        return response, latency_ms

    def _prompt_messages(self, context: SummarizationContext) -> list[dict[str, str]]:
        """Build a consistent prompt for chat-completion style providers."""
        return [
            {
                "role": "system",
                "content": (
                    "You are generating concise onboarding summaries for developers. "
                    "Explain the role of a code module, its responsibilities, and why it matters."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Summarize this module in 2-4 sentences for a developer new to the project.\n\n"
                    f"{context.to_prompt_context()}"
                ),
            },
        ]

    @abstractmethod
    async def summarize(self, context: SummarizationContext) -> str:
        """Generate a natural-language summary."""

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Verify provider connectivity and status."""
