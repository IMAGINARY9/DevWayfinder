"""SummarizationController orchestrates the summarization pipeline.

This module coordinates analysis results, context building, and
provider selection to generate natural-language descriptions.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from devwayfinder.summarizers.concurrency import ConcurrencyPool
from devwayfinder.summarizers.context_builder import ContextBuilder
from devwayfinder.summarizers.provider_chain import ProviderChain
from devwayfinder.summarizers.retry import RetryManager
from devwayfinder.summarizers.templates import (
    ARCHITECTURE_SUMMARY_TEMPLATE,
    ENTRY_POINT_SUMMARY_TEMPLATE,
    PromptTemplate,
    SummarizationType,
    get_adaptive_template,
)
from devwayfinder.utils.tokens import (
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
    input_tokens: int | None = None
    output_tokens: int | None = None


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

    # Quality behavior
    quality_profile: str = "balanced"
    minimum_summary_words: int = 0
    minimum_architecture_words: int = 0
    minimum_entry_point_words: int = 0


class SummarizationController:
    """Orchestrates summarization of code modules.

    Delegates to specialized managers:
    - ProviderChain: Provider selection and fallback
    - RetryManager: Retry logic with exponential backoff
    - ConcurrencyPool: Semaphore-based concurrency control

    Single responsibility: Coordinate orchestration of summarization pipeline.
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

        # Initialize specialized managers
        self.retry_manager = RetryManager(
            max_retries=self.config.max_retries,
            retry_delay=self.config.retry_delay,
        )
        self.concurrency_pool = ConcurrencyPool(
            max_concurrent=self.config.max_concurrent_requests,
        )
        self.provider_chain = ProviderChain(
            providers=self.config.providers,
            use_heuristic_fallback=self.config.use_heuristic_fallback,
            retry_manager=self.retry_manager,
        )

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

        Uses adaptive prompting: template selection is based on module
        characteristics (LOC, complexity) to balance quality vs. tokens.

        Args:
            module: Module to summarize
            graph: Optional dependency graph for context
            file_content: Optional source content

        Returns:
            SummarizationResult with generated summary
        """
        context = self.context_builder.from_module(module, graph=graph, file_content=file_content)
        template = get_adaptive_template(module)
        return await self._summarize_with_fallback(
            context=context,
            template=template,
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

        Uses adaptive prompting: template selection is based on
        analysis results (LOC, complexity metrics).

        Args:
            file_path: Path to the analyzed file
            analysis: Python analysis result
            graph: Optional dependency graph

        Returns:
            SummarizationResult with generated summary
        """
        context = self.context_builder.from_python_analysis(file_path, analysis, graph=graph)

        # Create a temporary module object for adaptive templating
        # Extract metrics from analysis results
        loc = len(context.file_content.splitlines()) if context.file_content else 0

        # Estimate complexity from number of classes and functions
        complexity = float(len(analysis.classes) + len(analysis.functions)) / max(1, loc // 50)

        # Create minimal module for template selection
        from devwayfinder.core.models import Module, ModuleType

        temp_module = Module(
            name=file_path.stem,
            path=file_path,
            module_type=ModuleType.FILE,
            language="python",
            loc=loc,
            complexity=complexity,
        )

        template = get_adaptive_template(temp_module)
        return await self._summarize_with_fallback(
            context=context,
            template=template,
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

        async def _summarize_one(module: Module) -> SummarizationResult:
            """Summarize a single module."""
            return await self.summarize_module(module, graph=graph)

        # Create tasks: (module_path, coroutine)
        tasks = tuple((str(m.path), (lambda m=m: _summarize_one(m))) for m in modules)

        # Run with concurrency control
        results = await self.concurrency_pool.run_concurrent(tasks)

        # Convert results to dict
        output: dict[str, SummarizationResult] = {}
        for module in modules:
            module_path = str(module.path)
            result = results.get(module_path)

            if result is None:
                output[module_path] = SummarizationResult(
                    summary="",
                    provider_used="none",
                    summary_type=SummarizationType.MODULE,
                    module_name=module.name,
                    success=False,
                    error="No result returned for module",
                )
            elif isinstance(result, BaseException):
                output[module_path] = SummarizationResult(
                    summary="",
                    provider_used="none",
                    summary_type=SummarizationType.MODULE,
                    module_name=module.name,
                    success=False,
                    error=str(result),
                )
            else:
                output[module_path] = result

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
            async with self.concurrency_pool.semaphore:
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
        self._apply_quality_metadata(context, summary_type)
        self._apply_template_guidance(context, summary_type)

        # Call provider chain
        provider_name, summary = await self.provider_chain.call_provider_chain(
            None,  # Not used since retry_manager is in chain
            context,
        )

        # If a provider succeeded
        if summary is not None and summary.strip():
            total_tokens = estimate_total_tokens(context)
            return SummarizationResult(
                summary=summary.strip(),
                provider_used=provider_name,
                summary_type=summary_type,
                module_name=context.module_name,
                success=True,
                tokens_used=total_tokens.total_tokens,
                input_tokens=total_tokens.input_tokens,
                output_tokens=total_tokens.output_tokens,
            )

        # All providers failed, try heuristic fallback
        if self.provider_chain.should_use_heuristic():
            heuristic_summary = self._generate_heuristic_summary(context, summary_type)
            # Heuristic uses no tokens (no LLM call)
            return SummarizationResult(
                summary=heuristic_summary,
                provider_used="heuristic",
                summary_type=summary_type,
                module_name=context.module_name,
                success=True,
                tokens_used=0,
                input_tokens=0,
                output_tokens=0,
            )

        # All providers and heuristic failed
        return SummarizationResult(
            summary="",
            provider_used="none",
            summary_type=summary_type,
            module_name=context.module_name,
            success=False,
            error="All providers failed and heuristic fallback is disabled",
            tokens_used=0,
            input_tokens=0,
            output_tokens=0,
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

    def _apply_quality_metadata(
        self,
        context: SummarizationContext,
        summary_type: SummarizationType,
    ) -> None:
        """Inject quality profile and threshold metadata into context."""
        context.metadata.setdefault("quality_profile", self.config.quality_profile)

        minimum_words = self._minimum_words_for(summary_type)
        if minimum_words <= 0:
            return

        existing = context.metadata.get("minimum_summary_words")
        if isinstance(existing, int) and existing > 0:
            context.metadata["minimum_summary_words"] = max(existing, minimum_words)
            return

        context.metadata["minimum_summary_words"] = minimum_words

    def _minimum_words_for(self, summary_type: SummarizationType) -> int:
        """Resolve minimum summary length by summary type."""
        if summary_type == SummarizationType.ARCHITECTURE:
            return max(0, self.config.minimum_architecture_words)
        if summary_type == SummarizationType.ENTRY_POINT:
            return max(0, self.config.minimum_entry_point_words)
        return max(0, self.config.minimum_summary_words)

    def _apply_template_guidance(
        self,
        context: SummarizationContext,
        summary_type: SummarizationType,
    ) -> None:
        """Add lightweight prompt hints tuned by summary type."""
        existing = context.metadata.get("prompt_hints")
        hints = [
            str(item).strip()
            for item in (existing if isinstance(existing, list) else [])
            if str(item).strip()
        ]

        if summary_type == SummarizationType.ARCHITECTURE:
            hints.append(
                "Describe component interactions and runtime flow, not just directory layout."
            )
        elif summary_type == SummarizationType.ENTRY_POINT:
            hints.append("Include concrete first steps and the next modules to read.")
        else:
            hints.append("Explain purpose, responsibilities, and practical onboarding relevance.")

        context.metadata["prompt_hints"] = hints

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def add_provider(self, provider: ModelProvider) -> None:
        """Add a provider to the chain.

        Args:
            provider: Provider to add
        """
        self.provider_chain.add_provider(provider)
        self.config.providers.append(provider)

    def remove_provider(self, provider_name: str) -> bool:
        """Remove a provider from the chain by name.

        Args:
            provider_name: Name of provider to remove

        Returns:
            True if provider was removed, False if not found
        """
        return self.provider_chain.remove_provider(provider_name)

    def clear_providers(self) -> None:
        """Remove all providers from the chain."""
        self.provider_chain.clear()
        self.config.providers.clear()

    async def close(self) -> None:
        """Close all provider connections."""
        await self.provider_chain.close_all()
