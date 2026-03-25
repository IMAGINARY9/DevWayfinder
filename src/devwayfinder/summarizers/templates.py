"""Prompt templates for summarization tasks.

This module defines structured prompt templates for different types of
code summarization. Templates are designed to produce consistent,
onboarding-focused descriptions.

Adaptive prompting: Templates are selected based on module complexity
(LOC and cyclomatic complexity) to balance quality vs. token usage.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from devwayfinder.core.models import Module


class SummarizationType(StrEnum):
    """Type of summary to generate."""

    MODULE = "module"
    ARCHITECTURE = "architecture"
    ENTRY_POINT = "entry_point"
    DEPENDENCY = "dependency"


@dataclass(frozen=True)
class PromptTemplate:
    """A structured prompt template for LLM summarization."""

    system_prompt: str
    user_prompt_template: str
    max_tokens: int = 256

    def format_user_prompt(self, **kwargs: str) -> str:
        """Format the user prompt with provided context."""
        return self.user_prompt_template.format(**kwargs)


# =============================================================================
# Module-Level Summarization - Adaptive Templates by Size
# =============================================================================

UTILITY_MODULE_TEMPLATE = PromptTemplate(
    system_prompt=(
        "You are an expert code documentarian. Write a concise 1-2 sentence summary "
        "of what this utility module does. Be direct and specific. "
        "Avoid phrases like 'This module' - start with the action/purpose."
    ),
    user_prompt_template=(
        "1-2 sentence summary for a utility module:\n\nModule: {module_name}\n{context}"
    ),
    max_tokens=100,  # Short summary for small utilities
)

MODULE_SUMMARY_TEMPLATE = PromptTemplate(
    system_prompt=(
        "You are an expert code documentarian helping developers onboard to new projects. "
        "Your task is to write clear, concise module summaries that explain:\n"
        "1. What the module does (primary responsibility)\n"
        "2. Why it exists (its role in the system)\n"
        "3. Key concepts a new developer should understand\n\n"
        "Write in active voice. Be specific, not generic. "
        "Avoid phrases like 'This module...' - start directly with what it does."
    ),
    user_prompt_template=(
        "Write a 2-4 sentence summary for a new developer.\n\nModule: {module_name}\n{context}"
    ),
    max_tokens=200,  # Standard summary for typical modules
)

CORE_MODULE_TEMPLATE = PromptTemplate(
    system_prompt=(
        "You are an expert code documentarian. This is a complex, important module. "
        "Write a detailed 4-6 sentence summary that explains:\n"
        "1. Primary responsibility and key abstractions\n"
        "2. How it's used by other modules\n"
        "3. Important patterns or algorithms\n"
        "4. Key classes/functions a developer must understand\n\n"
        "Be thorough but organized. Use semicolons to separate concepts."
    ),
    user_prompt_template=(
        "Write a detailed 4-6 sentence summary for this important module.\n\n"
        "Module: {module_name}\n{context}"
    ),
    max_tokens=300,  # Extended summary for complex/large modules
)


def get_adaptive_template(module: Module) -> PromptTemplate:
    """
    Select prompt template based on module characteristics.

    Uses lines of code (LOC) and cyclomatic complexity to determine
    how much detail the LLM should provide. This reduces token usage
    for simple utilities while providing comprehensive coverage for
    complex, important modules.

    Selection logic:
    - Small utilities (LOC < 50): UTILITY_MODULE_TEMPLATE (100 tokens max)
    - Standard modules (50-500 LOC): MODULE_SUMMARY_TEMPLATE (200 tokens max)
    - Large/complex (LOC > 500 OR complexity > 5): CORE_MODULE_TEMPLATE (300 tokens max)
    - Unknown (LOC is None): MODULE_SUMMARY_TEMPLATE (default to standard)

    Args:
        module: Module to summarize

    Returns:
        PromptTemplate selected for this module's characteristics
    """
    # If no metrics available, use standard template
    if module.loc is None and module.complexity is None:
        return MODULE_SUMMARY_TEMPLATE

    loc = module.loc or 0
    complexity = module.complexity or 0.0

    # Complex modules need detailed coverage
    if complexity > 5 or loc > 500:
        return CORE_MODULE_TEMPLATE

    # Small utilities: concise summary
    if loc < 50:
        return UTILITY_MODULE_TEMPLATE

    # Standard modules: typical coverage
    return MODULE_SUMMARY_TEMPLATE


# =============================================================================
# Architecture-Level Summarization
# =============================================================================

ARCHITECTURE_SUMMARY_TEMPLATE = PromptTemplate(
    system_prompt=(
        "You are an expert software architect helping developers understand system design. "
        "Your task is to write a high-level architecture overview that explains:\n"
        "1. The overall purpose and domain of the system\n"
        "2. Key architectural patterns and design decisions\n"
        "3. How major components interact\n"
        "4. The technology stack and why it was chosen\n\n"
        "Write for a developer who needs to understand the big picture before diving into code."
    ),
    user_prompt_template=(
        "Write a 3-5 paragraph architecture overview for this project.\n\n"
        "Project: {project_name}\n"
        "{context}"
    ),
    max_tokens=512,
)


# =============================================================================
# Entry Point Summarization
# =============================================================================

ENTRY_POINT_SUMMARY_TEMPLATE = PromptTemplate(
    system_prompt=(
        "You are an expert developer mentor helping newcomers find their way into a codebase. "
        "Your task is to write 'where to start' guidance that explains:\n"
        "1. What the entry point does and why it's important\n"
        "2. How it connects to the rest of the system\n"
        "3. What to explore first after understanding this entry point\n\n"
        "Be welcoming and practical. Help the developer feel oriented, not overwhelmed."
    ),
    user_prompt_template=(
        "Write a 'start here' guide paragraph for this entry point.\n\n"
        "Entry Point: {entry_point_name}\n"
        "{context}"
    ),
    max_tokens=256,
)


# =============================================================================
# Dependency Analysis Summarization
# =============================================================================

DEPENDENCY_SUMMARY_TEMPLATE = PromptTemplate(
    system_prompt=(
        "You are an expert software architect analyzing dependency relationships. "
        "Your task is to explain:\n"
        "1. Why components depend on each other\n"
        "2. The flow of data and control between modules\n"
        "3. Potential architectural concerns (circular deps, tight coupling)\n\n"
        "Be analytical and practical. Focus on what developers need to know."
    ),
    user_prompt_template=(
        "Analyze the dependency relationships and explain the module organization.\n\n"
        "Module: {module_name}\n"
        "{context}"
    ),
    max_tokens=200,
)


# =============================================================================
# Template Registry
# =============================================================================

TEMPLATES: dict[SummarizationType, PromptTemplate] = {
    SummarizationType.MODULE: MODULE_SUMMARY_TEMPLATE,
    SummarizationType.ARCHITECTURE: ARCHITECTURE_SUMMARY_TEMPLATE,
    SummarizationType.ENTRY_POINT: ENTRY_POINT_SUMMARY_TEMPLATE,
    SummarizationType.DEPENDENCY: DEPENDENCY_SUMMARY_TEMPLATE,
}


def get_template(summary_type: SummarizationType) -> PromptTemplate:
    """Get the prompt template for a given summarization type."""
    return TEMPLATES[summary_type]
