"""Summarization module for DevWayfinder.

This module provides LLM-powered and heuristic summarization of code,
transforming analysis results into natural-language descriptions.
"""

from devwayfinder.summarizers.concurrency import ConcurrencyPool
from devwayfinder.summarizers.context_builder import ContextBuilder
from devwayfinder.summarizers.controller import (
    SummarizationConfig,
    SummarizationController,
    SummarizationResult,
)
from devwayfinder.summarizers.provider_chain import ProviderChain
from devwayfinder.summarizers.retry import RetryManager
from devwayfinder.summarizers.templates import (
    ARCHITECTURE_SUMMARY_TEMPLATE,
    ENTRY_POINT_SUMMARY_TEMPLATE,
    MODULE_SUMMARY_TEMPLATE,
    PromptTemplate,
    SummarizationType,
    get_template,
)

__all__ = [
    "ARCHITECTURE_SUMMARY_TEMPLATE",
    "ENTRY_POINT_SUMMARY_TEMPLATE",
    "MODULE_SUMMARY_TEMPLATE",
    "ContextBuilder",
    "PromptTemplate",
    "SummarizationConfig",
    "SummarizationController",
    "SummarizationResult",
    "SummarizationType",
    "get_template",
]
