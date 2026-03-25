"""Token counting utilities for LLM efficiency tracking - MVP 2.5.

Provides token estimation and cost calculation for various LLM providers.
Based on common tokenization patterns and published token metrics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from devwayfinder.core.protocols import SummarizationContext


# ============================================================================
# TOKEN ESTIMATION CONSTANTS
# ============================================================================

# Average characters per token (varies by model, this is a reasonable average)
AVERAGE_CHARS_PER_TOKEN = 4  # English text typically 3-4 chars/token

# Model-specific token limits and pricing
MODEL_PRICING = {
    # OpenAI models (https://openai.com/pricing)
    "gpt-4o": {
        "input_cost_per_1m": 15.00,  # $0.015 per 1K tokens
        "output_cost_per_1m": 60.00,  # $0.060 per 1K tokens
        "context_window": 128000,
    },
    "gpt-4o-mini": {
        "input_cost_per_1m": 0.15,  # $0.00015 per 1K tokens
        "output_cost_per_1m": 0.60,  # $0.00060 per 1K tokens
        "context_window": 128000,
    },
    "gpt-4-turbo": {
        "input_cost_per_1m": 10.00,
        "output_cost_per_1m": 30.00,
        "context_window": 128000,
    },
    "gpt-4": {
        "input_cost_per_1m": 30.00,
        "output_cost_per_1m": 60.00,
        "context_window": 8192,
    },
    "gpt-3.5-turbo": {
        "input_cost_per_1m": 1.50,
        "output_cost_per_1m": 2.00,
        "context_window": 4096,
    },
    # Local models (typically free)
    "mistral:7b": {
        "input_cost_per_1m": 0.0,
        "output_cost_per_1m": 0.0,
        "context_window": 32000,
    },
    "llama2": {
        "input_cost_per_1m": 0.0,
        "output_cost_per_1m": 0.0,
        "context_window": 4096,
    },
    "neural-chat": {
        "input_cost_per_1m": 0.0,
        "output_cost_per_1m": 0.0,
        "context_window": 4096,
    },
}


@dataclass
class TokenEstimate:
    """Estimated token usage for a text."""

    input_tokens: int
    output_tokens: int
    total_tokens: int

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class CostEstimate:
    """Estimated cost for token usage."""

    input_cost: float
    output_cost: float
    total_cost: float
    currency: str = "USD"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "input_cost": round(self.input_cost, 6),
            "output_cost": round(self.output_cost, 6),
            "total_cost": round(self.total_cost, 6),
            "currency": self.currency,
        }

    def __str__(self) -> str:
        """Format as string for display."""
        if self.total_cost < 0.0001:
            return f"~${self.total_cost:.6f}"
        elif self.total_cost < 0.01:
            return f"~${self.total_cost:.4f}"
        else:
            return f"${self.total_cost:.4f}"


# ============================================================================
# TOKEN ESTIMATION FUNCTIONS
# ============================================================================


def estimate_tokens_for_text(text: str | None) -> int:
    """Estimate token count for text using character ratio.

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count
    """
    if not text:
        return 0

    # Simple estimation: characters / avg_chars_per_token
    return max(1, len(text) // AVERAGE_CHARS_PER_TOKEN)


def estimate_context_tokens(context: SummarizationContext) -> int:
    """Estimate token count for a summarization context.

    Args:
        context: Summarization context with module info

    Returns:
        Estimated tokens in context
    """
    total = 0

    # Module name and metadata
    total += estimate_tokens_for_text(context.module_name)

    # File content (if present)
    if context.file_content:
        total += estimate_tokens_for_text(context.file_content)

    # Code signatures
    for sig in context.signatures:
        total += estimate_tokens_for_text(sig)

    # Docstrings
    for doc in context.docstrings:
        total += estimate_tokens_for_text(doc)

    # Imports/exports/neighbors
    total += len(context.imports) * 4  # ~4 tokens per import
    total += len(context.exports) * 4  # ~4 tokens per export
    total += len(context.neighbors) * 4  # ~4 tokens per neighbor

    # System prompt baseline
    system_baseline = 50  # ~50 tokens for system prompt
    total += system_baseline

    return total


def estimate_output_tokens() -> int:
    """Estimate typical output tokens for a summary.

    Returns:
        Estimated output tokens (based on max_tokens from templates)
    """
    # Module summaries are typically 200-256 tokens
    # Architecture summaries are typically 512 tokens
    # Entry point summaries are typically 256 tokens
    # Return a reasonable middle ground
    return 256


def estimate_total_tokens(
    context: SummarizationContext,
    output_tokens: int | None = None,
) -> TokenEstimate:
    """Estimate total tokens for context + response.

    Args:
        context: Summarization context
        output_tokens: Expected output tokens (defaults to estimate)

    Returns:
        TokenEstimate with input, output, total
    """
    input_tok = estimate_context_tokens(context)
    output_tok = output_tokens or estimate_output_tokens()

    return TokenEstimate(
        input_tokens=input_tok,
        output_tokens=output_tok,
        total_tokens=input_tok + output_tok,
    )


def estimate_cost(
    token_estimate: TokenEstimate,
    model_name: str | None = None,
) -> CostEstimate:
    """Estimate cost for token usage based on model pricing.

    Args:
        token_estimate: Token usage estimate
        model_name: Name of the model (for pricing lookup)

    Returns:
        CostEstimate with input, output, total costs
    """
    if not model_name:
        model_name = "gpt-4o-mini"  # Default model

    # Get pricing for model (default to free if unknown)
    pricing = MODEL_PRICING.get(model_name, {"input_cost_per_1m": 0.0, "output_cost_per_1m": 0.0})

    # Calculate costs (pricing per 1M tokens, convert to per 1K)
    input_cost = (token_estimate.input_tokens / 1_000_000) * pricing["input_cost_per_1m"]
    output_cost = (token_estimate.output_tokens / 1_000_000) * pricing["output_cost_per_1m"]
    total_cost = input_cost + output_cost

    return CostEstimate(
        input_cost=input_cost,
        output_cost=output_cost,
        total_cost=total_cost,
    )


def estimate_cost_for_context(
    context: SummarizationContext,
    model_name: str | None = None,
) -> CostEstimate:
    """Estimate cost directly from context.

    Args:
        context: Summarization context
        model_name: Model name for pricing

    Returns:
        CostEstimate
    """
    tokens = estimate_total_tokens(context)
    return estimate_cost(tokens, model_name)


# ============================================================================
# BATCH COST REPORTING
# ============================================================================


@dataclass
class BatchCostSummary:
    """Summary of costs for a batch of operations."""

    total_tokens: int
    input_tokens: int
    output_tokens: int
    total_cost: float
    operations_count: int
    cost_per_operation: float
    free_operations: int  # Heuristic or cached
    llm_operations: int  # Real LLM calls

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_tokens": self.total_tokens,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_cost": round(self.total_cost, 6),
            "operations_count": self.operations_count,
            "cost_per_operation": round(self.cost_per_operation, 6),
            "free_operations": self.free_operations,
            "llm_operations": self.llm_operations,
        }

    def __str__(self) -> str:
        """Format summary for display."""
        lines = [
            "Generation Summary",
            "─" * 40,
            f"Modules analyzed:    {self.operations_count}",
            f"LLM summaries:       {self.llm_operations}",
            f"Heuristic/cached:    {self.free_operations}",
            "",
            f"Tokens used:         {self.total_tokens:,}",
            f"├─ Input:            {self.input_tokens:,}",
            f"└─ Output:           {self.output_tokens:,}",
            "",
            f"Estimated cost:      ${self.total_cost:.6f}",
            f"Cost per summary:    ${self.cost_per_operation:.6f}",
        ]
        return "\n".join(lines)
