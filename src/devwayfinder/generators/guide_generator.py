"""Guide Generator orchestrates the full pipeline.

This module coordinates:
1. Code analysis (using analyzers)
2. Summarization (using summarizers)
3. Guide assembly (using generators)
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from devwayfinder.analyzers.graph_builder import GraphBuilder
from devwayfinder.core.guide import OnboardingGuide, Section, SectionType
from devwayfinder.summarizers import SummarizationConfig, SummarizationController

if TYPE_CHECKING:
    from pathlib import Path

    from devwayfinder.core.graph import DependencyGraph
    from devwayfinder.core.models import Module, Project
    from devwayfinder.core.protocols import ModelProvider


logger = logging.getLogger(__name__)

# Progress callback type: (phase: str, status: str, detail: str) -> None
ProgressCallback = Callable[[str, str, str], None]


@dataclass
class GenerationConfig:
    """Configuration for guide generation."""

    # Analysis options
    include_hidden: bool = False
    exclude_patterns: list[str] = field(
        default_factory=lambda: [
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "node_modules",
            "*.egg-info",
            "dist",
            "build",
            ".tox",
            ".pytest_cache",
        ]
    )

    # Summarization options
    use_llm: bool = True
    providers: list[ModelProvider] = field(default_factory=list)
    max_concurrent_requests: int = 5

    # Output options
    include_mermaid: bool = True
    max_modules_in_graph: int = 50
    include_file_list: bool = True


@dataclass
class GenerationResult:
    """Result of guide generation."""

    guide: OnboardingGuide
    analysis_time_seconds: float
    summarization_time_seconds: float
    total_time_seconds: float
    modules_analyzed: int
    modules_summarized: int
    llm_calls_made: int
    total_tokens_used: int = 0
    heuristic_summaries: int = 0
    estimated_cost_usd: float = 0.0
    errors: list[str] = field(default_factory=list)


class GuideGenerator:
    """Orchestrates the complete guide generation pipeline.

    Pipeline stages:
    1. Structure analysis - scan directories, detect build systems
    2. Code analysis - extract imports/exports, build dependency graph
    3. Summarization - generate descriptions via LLM or heuristics
    4. Assembly - combine into OnboardingGuide structure
    5. Rendering - convert to Markdown output
    """

    def __init__(
        self,
        project_path: Path,
        config: GenerationConfig | None = None,
    ) -> None:
        """Initialize generator.

        Args:
            project_path: Path to the project to analyze
            config: Generation configuration
        """
        self.project_path = project_path.resolve()
        self.config = config or GenerationConfig()

        # Initialize graph builder (handles all analysis)
        self.graph_builder = GraphBuilder(
            exclude_patterns=self.config.exclude_patterns,
        )

        # Initialize summarization
        summ_config = SummarizationConfig(
            providers=self.config.providers,
            use_heuristic_fallback=True,
            max_concurrent_requests=self.config.max_concurrent_requests,
        )
        self.summarizer = SummarizationController(self.project_path, summ_config)

        # State
        self._project: Project | None = None
        self._graph: DependencyGraph | None = None
        self._llm_calls = 0
        self._summary_providers: dict[str, str] = {}
        self._summary_tokens: dict[str, int] = {}

    async def generate(
        self,
        progress_callback: ProgressCallback | None = None,
    ) -> GenerationResult:
        """Run the full generation pipeline.

        Args:
            progress_callback: Optional callback for progress updates.
                Called with (phase, status, detail) where:
                - phase: "analysis", "graph", "metrics", "summarization", "assembly"
                - status: "start", "progress", "complete", "failed", "skipped"
                - detail: Additional information string

        Returns:
            GenerationResult with guide and metrics
        """
        start_time = time.perf_counter()
        errors: list[str] = []

        def _report(phase: str, status: str, detail: str = "") -> None:
            """Report progress if callback provided."""
            if progress_callback:
                progress_callback(phase, status, detail)

        # Stage 1: Analysis
        _report("analysis", "start", "Scanning project structure")
        analysis_start = time.perf_counter()
        try:
            await self._run_analysis()
            modules_analyzed = self._project.module_count if self._project else 0
            _report("analysis", "complete", f"{modules_analyzed} modules found")
        except Exception as e:
            errors.append(f"Analysis failed: {e}")
            logger.exception("Analysis failed")
            _report("analysis", "failed", str(e))

        analysis_time = time.perf_counter() - analysis_start
        modules_analyzed = self._project.module_count if self._project else 0

        # Mark graph phase complete (handled by analysis)
        _report("graph", "start", "Building dependency graph")
        if self._graph:
            _report("graph", "complete", f"{self._graph.edge_count} dependencies")
        else:
            _report("graph", "skipped", "No graph built")

        # Mark metrics phase
        _report("metrics", "start", "Computing complexity metrics")
        _report("metrics", "complete", "Metrics calculated")

        # Stage 2: Summarization
        summ_start = time.perf_counter()
        summaries: dict[str, str] = {}
        if self._project:
            _report("summarization", "start", "Generating module descriptions")
            try:
                summaries = await self._run_summarization(progress_callback)
                _report("summarization", "complete", f"{len(summaries)} summaries")
            except Exception as e:
                errors.append(f"Summarization failed: {e}")
                logger.exception("Summarization failed")
                _report("summarization", "failed", str(e))
        else:
            _report("summarization", "skipped", "No project modules available")

        summ_time = time.perf_counter() - summ_start

        # Stage 3: Assembly
        _report("assembly", "start", "Creating onboarding document")
        guide = self._assemble_guide(summaries)
        _report("assembly", "complete", f"{len(guide.sections)} sections")

        total_time = time.perf_counter() - start_time
        guide.generation_time_seconds = total_time

        return GenerationResult(
            guide=guide,
            analysis_time_seconds=analysis_time,
            summarization_time_seconds=summ_time,
            total_time_seconds=total_time,
            modules_analyzed=modules_analyzed,
            modules_summarized=len(summaries),
            llm_calls_made=self._llm_calls,
            total_tokens_used=sum(self._summary_tokens.values()),
            heuristic_summaries=sum(1 for p in self._summary_providers.values() if p == "heuristic"),
            estimated_cost_usd=self._estimate_generation_cost(),
            errors=errors,
        )

    async def _run_analysis(self) -> None:
        """Run code analysis phase."""
        logger.info("Starting analysis of %s", self.project_path)

        # Use GraphBuilder to do full analysis
        self._project, self._graph = await self.graph_builder.build(self.project_path)

        logger.info(
            "Analysis complete: %d modules, %d dependencies",
            self._project.module_count,
            self._graph.edge_count,
        )

    async def _run_summarization(
        self,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, str]:
        """Run summarization phase."""
        if not self._project:
            return {}

        logger.info("Starting summarization of %d modules", self._project.module_count)
        summaries: dict[str, str] = {}

        # Summarize modules in batch
        modules = list(self._project.modules.values())
        total = len(modules)

        # Report progress during summarization
        if progress_callback:
            progress_callback("summarization", "progress", f"0/{total} modules")

        results = await self.summarizer.summarize_modules_batch(modules, graph=self._graph)

        for i, (path, result) in enumerate(results.items(), 1):
            if result.success:
                summaries[path] = result.summary
                self._summary_providers[path] = result.provider_used
                self._summary_tokens[path] = result.tokens_used or 0
                if result.provider_used != "heuristic":
                    self._llm_calls += 1
            else:
                logger.warning("Failed to summarize %s: %s", path, result.error)

            if progress_callback and i % 5 == 0:  # Update every 5 modules
                progress_callback("summarization", "progress", f"{i}/{total} modules")

        return summaries

    def _assemble_guide(self, summaries: dict[str, str]) -> OnboardingGuide:
        """Assemble the final guide from analysis and summaries."""
        guide = OnboardingGuide(
            project_name=self._project.name if self._project else self.project_path.name,
            project_path=str(self.project_path),
            model_used=self._get_model_name(),
        )

        # Add sections
        guide.add_section(self._create_overview_section())
        guide.add_section(self._create_architecture_section())
        guide.add_section(self._create_modules_section(summaries))
        guide.add_section(self._create_dependencies_section())
        guide.add_section(self._create_start_here_section())

        return guide

    def _create_overview_section(self) -> Section:
        """Create the overview section."""
        lines = []

        if self._project:
            if self._project.primary_language:
                lines.append(f"**Primary Language:** {self._project.primary_language}")
            if self._project.build_system:
                lines.append(f"**Build System:** {self._project.build_system}")
            if self._project.package_manager:
                lines.append(f"**Package Manager:** {self._project.package_manager}")
            lines.append(f"**Modules:** {self._project.module_count}")

            # README excerpt
            if self._project.readme_content:
                excerpt = self._project.readme_content[:500].strip()
                # Try to find a description paragraph
                paragraphs = excerpt.split("\n\n")
                for para in paragraphs:
                    if not para.startswith("#") and len(para) > 50:
                        lines.append("")
                        lines.append(para)
                        break

        return Section(
            section_type=SectionType.OVERVIEW,
            title="Overview",
            content="\n".join(lines) if lines else "Project overview not available.",
        )

    def _create_architecture_section(self) -> Section:
        """Create the architecture section."""
        lines = []

        if self._project and self._graph:
            # Directory structure summary
            dirs: dict[str, int] = {}
            for module in self._project.modules.values():
                try:
                    rel_parent = module.path.parent.relative_to(self.project_path)
                    dir_str = str(rel_parent) if str(rel_parent) != "." else "(root)"
                except ValueError:
                    dir_str = "(external)"
                dirs[dir_str] = dirs.get(dir_str, 0) + 1

            if dirs:
                lines.append("### Directory Structure")
                lines.append("")
                for directory, count in sorted(dirs.items(), key=lambda x: -x[1])[:10]:
                    lines.append(f"- `{directory}`: {count} file(s)")
                lines.append("")

            # Core modules
            core_modules = self._graph.get_core_modules(threshold=3)
            if core_modules:
                lines.append("### Core Modules")
                lines.append("")
                lines.append("These modules are highly connected and form the backbone:")
                lines.append("")
                for module in core_modules[:5]:
                    lines.append(f"- **{module.name}**: {module.description or 'Core module'}")
                lines.append("")

            # Circular dependencies warning
            if self._graph.has_cycles():
                cycles = self._graph.find_cycles()
                lines.append("### ⚠️ Circular Dependencies")
                lines.append("")
                lines.append(f"Found {len(cycles)} circular dependency chain(s).")
                lines.append("")

        return Section(
            section_type=SectionType.ARCHITECTURE,
            title="Architecture",
            content="\n".join(lines) if lines else "Architecture overview not available.",
        )

    def _create_modules_section(self, summaries: dict[str, str]) -> Section:
        """Create the modules section with descriptions."""
        subsections = []

        if self._project:
            # Group by directory
            by_dir: dict[str, list[Module]] = {}
            for module in self._project.modules.values():
                try:
                    rel_parent = module.path.parent.relative_to(self.project_path)
                    dir_str = str(rel_parent) if str(rel_parent) != "." else "(root)"
                except ValueError:
                    dir_str = "(external)"

                if dir_str not in by_dir:
                    by_dir[dir_str] = []
                by_dir[dir_str].append(module)

            # Create subsection for each directory
            for directory in sorted(by_dir.keys()):
                modules = by_dir[directory]
                module_lines = []

                for module in sorted(modules, key=lambda m: m.name):
                    path_str = str(module.path)
                    summary = summaries.get(path_str, "")
                    module_lines.append(f"**{module.name}**")
                    if summary:
                        provider_used = self._summary_providers.get(path_str, "heuristic")
                        if provider_used == "heuristic":
                            quality_badge = "[heuristic]"
                        elif provider_used == "none":
                            quality_badge = "[none]"
                        else:
                            quality_badge = "[LLM]"
                        module_lines.append(f"> {quality_badge} {summary}")
                    if module.imports:
                        module_lines.append(f"*Imports:* {', '.join(module.imports[:5])}")
                    module_lines.append("")

                subsections.append(
                    Section(
                        section_type=SectionType.CUSTOM,
                        title=f"`{directory}`",
                        content="\n".join(module_lines),
                    )
                )

        return Section(
            section_type=SectionType.MODULES,
            title="Modules",
            content="Detailed module descriptions organized by directory.",
            subsections=subsections,
        )

    def _create_dependencies_section(self) -> Section:
        """Create the dependencies section with graph visualization."""
        lines = []

        if self._graph:
            lines.append(f"**Total Modules:** {self._graph.node_count}")
            lines.append(f"**Total Dependencies:** {self._graph.edge_count}")
            lines.append("")

            # Mermaid diagram
            if self.config.include_mermaid and self._graph.edge_count > 0:
                lines.append("### Dependency Graph")
                lines.append("")
                lines.append("```mermaid")
                lines.append(self._graph.to_mermaid(max_nodes=self.config.max_modules_in_graph))
                lines.append("```")
                lines.append("")

            # Text list of key dependencies
            if self._project:
                entry_points = self._project.entry_points
                if entry_points:
                    lines.append("### Key Entry Points")
                    lines.append("")
                    for ep in entry_points[:5]:
                        deps = self._graph.get_dependencies(ep.path)
                        dep_names = [d.name for d in deps[:3]]
                        if dep_names:
                            lines.append(f"- **{ep.name}** → {', '.join(dep_names)}")
                        else:
                            lines.append(f"- **{ep.name}** (no dependencies)")
                    lines.append("")

        return Section(
            section_type=SectionType.DEPENDENCIES,
            title="Dependencies",
            content="\n".join(lines) if lines else "Dependency information not available.",
        )

    def _create_start_here_section(self) -> Section:
        """Create the 'Start Here' section for new developers."""
        lines = []

        if self._project and self._graph:
            entry_points = self._project.entry_points
            if not entry_points:
                # Use modules with no incoming dependencies
                entry_points = self._graph.get_entry_points()

            if entry_points:
                lines.append("New to this codebase? Start with these entry points:")
                lines.append("")

                for ep in entry_points[:3]:
                    lines.append(f"### {ep.name}")
                    lines.append("")
                    if ep.description:
                        lines.append(ep.description)
                    else:
                        lines.append(f"Located at `{ep.path.relative_to(self.project_path)}`")

                    # Suggest next modules to explore
                    deps = self._graph.get_dependencies(ep.path)
                    if deps:
                        dep_names = [d.name for d in deps[:3]]
                        lines.append(f"After understanding this, explore: {', '.join(dep_names)}")
                    lines.append("")
            else:
                lines.append("No clear entry points detected.")
                lines.append(
                    "Consider starting with the most-connected modules in the Architecture section."
                )

        return Section(
            section_type=SectionType.START_HERE,
            title="Start Here",
            content="\n".join(lines) if lines else "Getting started guide not available.",
        )

    def _detect_primary_language(self, files: list[Path]) -> str | None:
        """Detect the primary programming language."""
        from devwayfinder.analyzers.base import EXTENSION_TO_LANGUAGE

        lang_counts: dict[str, int] = {}
        for f in files:
            lang = EXTENSION_TO_LANGUAGE.get(f.suffix.lower())
            if lang:
                lang_counts[lang] = lang_counts.get(lang, 0) + 1

        if lang_counts:
            return max(lang_counts.items(), key=lambda x: x[1])[0]
        return None

    def _get_model_name(self) -> str | None:
        """Get the name of the LLM model used."""
        if self.config.providers:
            return self.config.providers[0].name
        return "heuristic"

    def _estimate_generation_cost(self) -> float:
        """Estimate generation cost based on tracked token usage and active model."""
        from devwayfinder.utils.tokens import CostEstimate, TokenEstimate, estimate_cost

        token_estimate = TokenEstimate(
            input_tokens=self._summary_tokens and sum(self._summary_tokens.values()) or 0,
            output_tokens=0,
            total_tokens=self._summary_tokens and sum(self._summary_tokens.values()) or 0,
        )
        model_name = self._get_model_name()
        cost: CostEstimate = estimate_cost(token_estimate, model_name=model_name)
        return cost.total_cost

    async def close(self) -> None:
        """Clean up resources."""
        await self.summarizer.close()


class MarkdownGenerator:
    """Generates Markdown output from OnboardingGuide."""

    def generate(self, guide: OnboardingGuide) -> str:
        """Generate Markdown from guide.

        Uses the guide's built-in to_markdown() method.
        """
        return guide.to_markdown()

    def generate_toc(self, guide: OnboardingGuide) -> str:
        """Generate just the table of contents."""
        lines = ["## Table of Contents", ""]
        for i, section in enumerate(guide.sections, 1):
            anchor = section.title.lower().replace(" ", "-")
            lines.append(f"{i}. [{section.title}](#{anchor})")
        return "\n".join(lines)

    def generate_section(self, section: Section, level: int = 2) -> str:
        """Generate Markdown for a single section."""
        lines = []
        prefix = "#" * level
        lines.append(f"{prefix} {section.title}")
        lines.append("")
        if section.content:
            lines.append(section.content)
            lines.append("")
        for sub in section.subsections:
            lines.append(self.generate_section(sub, level + 1))
        return "\n".join(lines)
