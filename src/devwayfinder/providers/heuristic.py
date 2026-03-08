"""Heuristic fallback provider."""

from __future__ import annotations

from devwayfinder.core.protocols import HealthStatus, SummarizationContext
from devwayfinder.providers.base import BaseProvider
from devwayfinder.providers.config import ProviderConfig


class HeuristicProvider(BaseProvider):
    """Generate lightweight summaries without calling an external LLM."""

    provider_name = "heuristic"

    def __init__(self, config: ProviderConfig | None = None) -> None:
        super().__init__(config or ProviderConfig(provider="heuristic"))

    async def summarize(self, context: SummarizationContext) -> str:
        """Return a deterministic summary based on known static signals."""
        sentences = [f"{context.module_name} is part of the project onboarding surface."]

        if context.docstrings:
            lead = context.docstrings[0].strip().splitlines()[0]
            sentences.append(f"Its available documentation suggests: {lead}")

        if context.signatures:
            sentences.append("Key entry points include " + ", ".join(context.signatures[:3]) + ".")

        if context.imports:
            sentences.append("It depends on " + ", ".join(context.imports[:5]) + ".")

        if context.exports:
            sentences.append("It exposes " + ", ".join(context.exports[:5]) + ".")

        if len(sentences) == 1:
            sentences.append(
                "No provider-specific model is required, so this fallback remains available offline."
            )

        return " ".join(sentences)

    async def health_check(self) -> HealthStatus:
        """Heuristic mode is always available."""
        return HealthStatus(
            healthy=True,
            message="Heuristic fallback is available without network access.",
            model_info={"mode": "offline"},
        )
