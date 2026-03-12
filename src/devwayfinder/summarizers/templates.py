"""Prompt templates for summarization tasks.

This module defines structured prompt templates for different types of
code summarization. Templates are designed to produce consistent,
onboarding-focused descriptions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


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
# Module-Level Summarization
# =============================================================================

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
        "Write a 2-4 sentence summary for a new developer.\n\n"
        "Module: {module_name}\n"
        "{context}"
    ),
    max_tokens=200,
)


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
