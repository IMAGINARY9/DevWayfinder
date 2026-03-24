"""SummarizationController orchestrates the summarization pipeline.

This module coordinates analysis results, context building, and
provider selection to generate natural-language descriptions.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from devwayfinder.core.exceptions import ProviderError
from devwayfinder.summarizers.context_builder import ContextBuilder
from devwayfinder.summarizers.templates import (
    ARCHITECTURE_SUMMARY_TEMPLATE,
    ENTRY_POINT_SUMMARY_TEMPLATE,
    MODULE_SUMMARY_TEMPLATE,
    PromptTemplate,
    SummarizationType,
)
from devwayfinder.utils.tokens import (
    estimate_cost_for_context,
    estimate_output_tokens,
    estimate_total_tokens,
)

if TYPE_CHECKING:
    from pathlib import Path

    from devwayfinder.analyzers.python_analyzer import PythonExtractionResult
    from devwayfinder.analyzers.structure import StructureInfo
    from devwayfinder.core.graph import DependencyGraph
    from devwayfinder.core.models import Module, Project
    from devwayfinder.core.protocols import ModelProvider, SummarizationContext


logger = logging.getLogger(__name__)


@dataclass
class SummarizationResult:
    """Result of a summarization operation."""

    summary: str
    provider_used: str
    summary_type: SummarizationType
    module_name: str
    success: bool = True
    error: str | None = None
    tokens_used: int | None = None


@dataclass
class SummarizationConfig:
    """Configuration for summarization behavior."""

    # Provider chain (in order of preference)
    providers: list[ModelProvider] = field(default_factory=list)

    # Fallback behavior
    use_heuristic_fallback: bool = True

    # Concurrency control
    max_concurrent_requests: int = 5

    # Retry behavior
    max_retries: int = 2
    retry_delay: float = 1.0


class SummarizationController:
    """Orchestrates summarization of code modules.

    The controller coordinates:
    1. Building context from analysis results
    2. Selecting and calling providers (with fallback chain)
    3. Managing concurrency for batch operations
    4. Handling errors and retries
    """

    def __init__(
        self,
        project_root: Path,
        config: SummarizationConfig | None = None,
    ) -> None:
        """Initialize controller.

        Args:
            project_root: Root path for relative name computation
            config: Summarization configuration
        """
        self.project_root = project_root
        self.config = config or SummarizationConfig()
        self.context_builder = ContextBuilder(project_root)
        self._semaphore: asyncio.Semaphore | None = None

    @property
    def semaphore(self) -> asyncio.Semaphore:
        """Lazy semaphore initialization for concurrency control."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
        return self._semaphore

    # =========================================================================
    # Module-Level Summarization
    # =========================================================================

    async def summarize_module(
        self,
        module: Module,
        *,
        graph: DependencyGraph | None = None,
        file_content: str | None = None,
    ) -> SummarizationResult:
        """Generate summary for a single module.

        Args:
            module: Module to summarize
            graph: Optional dependency graph for context
            file_content: Optional source content

        Returns:
            SummarizationResult with generated summary
        """
        context = self.context_builder.from_module(module, graph=graph, file_content=file_content)
        return await self._summarize_with_fallback(
            context=context,
            template=MODULE_SUMMARY_TEMPLATE,
            summary_type=SummarizationType.MODULE,
        )

    async def summarize_module_from_analysis(
        self,
        file_path: Path,
        analysis: PythonExtractionResult,
        *,
        graph: DependencyGraph | None = None,
    ) -> SummarizationResult:
        """Generate summary from Python AST analysis.

        Args:
            file_path: Path to the analyzed file
            analysis: Python analysis result
            graph: Optional dependency graph

        Returns:
            SummarizationResult with generated summary
        """
        context = self.context_builder.from_python_analysis(file_path, analysis, graph=graph)
        return await self._summarize_with_fallback(
            context=context,
            template=MODULE_SUMMARY_TEMPLATE,
            summary_type=SummarizationType.MODULE,
        )

    async def summarize_modules_batch(
        self,
        modules: list[Module],
        *,
        graph: DependencyGraph | None = None,
    ) -> dict[str, SummarizationResult]:
        """Summarize multiple modules concurrently.

        Args:
            modules: List of modules to summarize
            graph: Optional dependency graph

        Returns:
            Dict mapping module path to SummarizationResult
        """

        async def _summarize_one(module: Module) -> tuple[str, SummarizationResult]:
            async with self.semaphore:
                result = await self.summarize_module(module, graph=graph)
                return str(module.path), result

        tasks = [_summarize_one(m) for m in modules]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output: dict[str, SummarizationResult] = {}
        for i, result in enumerate(results):
            module_path = str(modules[i].path)
            if isinstance(result, BaseException):
                output[module_path] = SummarizationResult(
                    summary="",
                    provider_used="none",
                    summary_type=SummarizationType.MODULE,
                    module_name=modules[i].name,
                    success=False,
                    error=str(result),
                )
            else:
                # result is tuple[str, SummarizationResult]
                path, summ_result = result
                output[path] = summ_result

        return output

    # =========================================================================
    # Architecture-Level Summarization
    # =========================================================================

    async def summarize_architecture(
        self,
        project: Project,
        structure: StructureInfo,
        *,
        graph: DependencyGraph | None = None,
    ) -> SummarizationResult:
        """Generate high-level architecture overview.

        Args:
            project: Project with all modules
            structure: Structure analysis result
            graph: Optional dependency graph

        Returns:
            SummarizationResult with architecture overview
        """
        context = self.context_builder.for_architecture(project, structure, graph=graph)
        return await self._summarize_with_fallback(
            context=context,
            template=ARCHITECTURE_SUMMARY_TEMPLATE,
            summary_type=SummarizationType.ARCHITECTURE,
        )

    # =========================================================================
    # Entry Point Summarization
    # =========================================================================

    async def summarize_entry_point(
        self,
        module: Module,
        *,
        graph: DependencyGraph | None = None,
        file_content: str | None = None,
    ) -> SummarizationResult:
        """Generate 'start here' summary for an entry point.

        Args:
            module: Entry point module
            graph: Optional dependency graph
            file_content: Optional source content

        Returns:
            SummarizationResult with entry point guidance
        """
        context = self.context_builder.for_entry_point(
            module, graph=graph, file_content=file_content
        )
        return await self._summarize_with_fallback(
            context=context,
            template=ENTRY_POINT_SUMMARY_TEMPLATE,
            summary_type=SummarizationType.ENTRY_POINT,
        )

    async def summarize_entry_points_batch(
        self,
        modules: list[Module],
        *,
        graph: DependencyGraph | None = None,
    ) -> dict[str, SummarizationResult]:
        """Summarize multiple entry points concurrently.

        Args:
            modules: List of entry point modules
            graph: Optional dependency graph

        Returns:
            Dict mapping module path to SummarizationResult
        """

        async def _summarize_one(module: Module) -> tuple[str, SummarizationResult]:
            async with self.semaphore:
                result = await self.summarize_entry_point(module, graph=graph)
                return str(module.path), result

        tasks = [_summarize_one(m) for m in modules]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output: dict[str, SummarizationResult] = {}
        for i, result in enumerate(results):
            module_path = str(modules[i].path)
            if isinstance(result, BaseException):
                output[module_path] = SummarizationResult(
                    summary="",
                    provider_used="none",
                    summary_type=SummarizationType.ENTRY_POINT,
                    module_name=modules[i].name,
                    success=False,
                    error=str(result),
                )
            else:
                # result is tuple[str, SummarizationResult]
                path, summ_result = result
                output[path] = summ_result

        return output

    # =========================================================================
    # Provider Chain and Fallback
    # =========================================================================

    async def _summarize_with_fallback(
        self,
        context: SummarizationContext,
        template: PromptTemplate,  # noqa: ARG002 - reserved for provider template customization
        summary_type: SummarizationType,
    ) -> SummarizationResult:
        """Try providers in order with fallback chain.

        Args:
            context: Summarization context
            template: Prompt template to use
            summary_type: Type of summary being generated

        Returns:
            SummarizationResult from first successful provider
        """
        last_error: str | None = None

        # Try each configured provider in order
        for provider in self.config.providers:
            try:
                summary = await self._call_provider_with_retry(provider, context)
                
                # Estimate tokens for successful provider call
                total_tokens = estimate_total_tokens(context)
                
                return SummarizationResult(
                    summary=summary,
                    provider_used=provider.name,
                    summary_type=summary_type,
                    module_name=context.module_name,
                    success=True,
                    tokens_used=total_tokens,
                )
            except Exception as e:
                last_error = f"{provider.name}: {e}"
                logger.warning("Provider %s failed: %s", provider.name, e)
                continue

        # Fall back to heuristic if enabled
        if self.config.use_heuristic_fallback:
            summary = self._generate_heuristic_summary(context, summary_type)
            # Heuristic uses no tokens (no LLM call)
            return SummarizationResult(
                summary=summary,
                provider_used="heuristic",
                summary_type=summary_type,
                module_name=context.module_name,
                success=True,
                tokens_used=0,
            )

        # All providers failed
        return SummarizationResult(
            summary="",
            provider_used="none",
            summary_type=summary_type,
            module_name=context.module_name,
            success=False,
            error=last_error or "No providers available",
            tokens_used=0,
        )

    async def _call_provider_with_retry(
        self,
        provider: ModelProvider,
        context: SummarizationContext,
    ) -> str:
        """Call provider with retry logic.

        Args:
            provider: Provider to call
            context: Summarization context

        Returns:
            Generated summary

        Raises:
            ProviderError: If all retries fail
        """
        last_error: Exception | None = None

        for attempt in range(self.config.max_retries):
            try:
                return await provider.summarize(context)
            except Exception as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)

        raise ProviderError(
            f"{provider.name}: Failed after {self.config.max_retries} attempts: {last_error}"
        )

    def _generate_heuristic_summary(
        self,
        context: SummarizationContext,
        summary_type: SummarizationType,
    ) -> str:
        """Generate a rule-based summary without LLM.

        Args:
            context: Summarization context
            summary_type: Type of summary

        Returns:
            Heuristic-generated summary
        """
        if summary_type == SummarizationType.MODULE:
            return self._heuristic_module_summary(context)
        elif summary_type == SummarizationType.ARCHITECTURE:
            return self._heuristic_architecture_summary(context)
        elif summary_type == SummarizationType.ENTRY_POINT:
            return self._heuristic_entry_point_summary(context)
        else:
            return self._heuristic_module_summary(context)

    def _heuristic_module_summary(self, context: SummarizationContext) -> str:
        """Generate heuristic summary for a module."""
        parts = [f"**{context.module_name}**"]

        # Use docstring if available
        if context.docstrings:
            lead = context.docstrings[0].strip().split("\n")[0]
            if lead:
                parts.append(f"— {lead}")

        # Describe key signatures
        if context.signatures:
            funcs = [s for s in context.signatures[:3] if s.startswith("def ")]
            classes = [s for s in context.signatures[:3] if s.startswith("class ")]
            if classes:
                parts.append(f"Defines: {', '.join(classes)}.")
            if funcs:
                parts.append(f"Provides: {', '.join(funcs)}.")

        # Add dependency info
        if context.imports:
            parts.append(f"Depends on {len(context.imports)} module(s).")

        if context.exports:
            parts.append(f"Exports: {', '.join(context.exports[:5])}.")

        return " ".join(parts)

    def _heuristic_architecture_summary(self, context: SummarizationContext) -> str:
        """Generate heuristic architecture overview."""
        parts = [f"# {context.module_name} Architecture\n"]

        meta = context.metadata

        # Build system info
        if meta.get("build_system"):
            parts.append(f"**Build System:** {meta['build_system']}")
        if meta.get("primary_language"):
            parts.append(f"**Primary Language:** {meta['primary_language']}")
        if meta.get("module_count"):
            parts.append(f"**Modules:** {meta['module_count']}")

        # Directory structure
        if meta.get("directory_structure"):
            parts.append("\n**Structure:**\n" + meta["directory_structure"])

        # README excerpt
        if meta.get("readme_excerpt"):
            excerpt = meta["readme_excerpt"][:300].strip()
            parts.append(f"\n**From README:**\n{excerpt}...")

        return "\n".join(parts)

    def _heuristic_entry_point_summary(self, context: SummarizationContext) -> str:
        """Generate heuristic entry point summary."""
        parts = [f"**Start Here: {context.module_name}**"]

        if context.docstrings:
            parts.append(context.docstrings[0].strip().split("\n")[0])

        if context.metadata.get("has_main"):
            parts.append("This module contains a `__main__` block and can be run directly.")

        if context.neighbors:
            parts.append(f"Next, explore: {', '.join(context.neighbors[:3])}.")

        if context.metadata.get("suggested_exploration"):
            suggestions = context.metadata["suggested_exploration"][:3]
            if suggestions:
                parts.append(f"Related modules: {', '.join(suggestions)}.")

        return " ".join(parts)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def add_provider(self, provider: ModelProvider) -> None:
        """Add a provider to the chain.

        Args:
            provider: Provider to add
        """
        self.config.providers.append(provider)

    def clear_providers(self) -> None:
        """Remove all providers from the chain."""
        self.config.providers.clear()

    async def close(self) -> None:
        """Close all provider connections."""
        for provider in self.config.providers:
            if hasattr(provider, "close"):
                await provider.close()
