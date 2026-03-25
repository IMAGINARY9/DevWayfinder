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
    CORE_MODULE_TEMPLATE,
    ENTRY_POINT_SUMMARY_TEMPLATE,
    MODULE_SUMMARY_TEMPLATE,
    UTILITY_MODULE_TEMPLATE,
    PromptTemplate,
    SummarizationType,
    get_adaptive_template,
    get_template,
)

__all__ = [
    "ARCHITECTURE_SUMMARY_TEMPLATE",
    "CORE_MODULE_TEMPLATE",
    "ENTRY_POINT_SUMMARY_TEMPLATE",
    "MODULE_SUMMARY_TEMPLATE",
    "UTILITY_MODULE_TEMPLATE",
    "ConcurrencyPool",
    "ContextBuilder",
    "PromptTemplate",
    "ProviderChain",
    "RetryManager",
    "SummarizationConfig",
    "SummarizationController",
    "SummarizationResult",
    "SummarizationType",
    "get_adaptive_template",
    "get_template",
]
