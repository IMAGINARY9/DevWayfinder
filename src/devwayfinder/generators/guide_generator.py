"""Guide Generator orchestrates the full pipeline.

This module coordinates:
1. Code analysis (using analyzers)
2. Summarization (using summarizers)
3. Guide assembly (using generators)
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

from devwayfinder.analyzers.graph_builder import GraphBuilder
from devwayfinder.analyzers.start_here import get_start_here_recommendations
from devwayfinder.core.guide import OnboardingGuide, Section, SectionType
from devwayfinder.generators.guide_template import GuideTemplate, load_guide_template
from devwayfinder.summarizers import SummarizationConfig, SummarizationController

if TYPE_CHECKING:
    from pathlib import Path

    from devwayfinder.analyzers.structure import StructureInfo
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
    quality_profile: str = "detailed"  # detailed | minimal
    minimum_module_words: int = 0
    minimum_architecture_words: int = 0
    minimum_entry_point_words: int = 0
    llm_architecture_pass: bool = True
    llm_entry_point_pass: bool = True

    # Output options
    include_mermaid: bool = True
    max_modules_in_graph: int = 50
    include_file_list: bool = True
    template_path: Path | None = None


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
        self._apply_quality_profile_defaults()
        self.guide_template: GuideTemplate = load_guide_template(
            self.project_path,
            self.config.template_path,
        )

        # Initialize graph builder (handles all analysis)
        self.graph_builder = GraphBuilder(
            exclude_patterns=self.config.exclude_patterns,
        )

        # Initialize summarization
        providers = self.config.providers if self.config.use_llm else []
        summ_config = SummarizationConfig(
            providers=providers,
            use_heuristic_fallback=True,
            max_concurrent_requests=self.config.max_concurrent_requests,
            quality_profile=self.config.quality_profile,
            minimum_summary_words=self.config.minimum_module_words,
            minimum_architecture_words=self.config.minimum_architecture_words,
            minimum_entry_point_words=self.config.minimum_entry_point_words,
        )
        self.summarizer = SummarizationController(self.project_path, summ_config)

        # State
        self._project: Project | None = None
        self._graph: DependencyGraph | None = None
        self._structure_info: StructureInfo | None = None
        self._llm_calls = 0
        self._summary_providers: dict[str, str] = {}
        self._summary_tokens: dict[str, int] = {}
        self._summary_input_tokens: dict[str, int] = {}
        self._summary_output_tokens: dict[str, int] = {}
        self._architecture_summary: str = ""
        self._architecture_provider: str = "none"
        self._entry_point_guidance: dict[str, str] = {}
        self._entry_point_providers: dict[str, str] = {}

    _QUALITY_PROFILE_DEFAULTS: ClassVar[dict[str, dict[str, int | bool]]] = {
        "detailed": {
            "use_llm": True,
            "minimum_module_words": 24,
            "minimum_architecture_words": 90,
            "minimum_entry_point_words": 50,
            "llm_architecture_pass": True,
            "llm_entry_point_pass": True,
        },
        "minimal": {
            "use_llm": False,
            "minimum_module_words": 0,
            "minimum_architecture_words": 0,
            "minimum_entry_point_words": 0,
            "llm_architecture_pass": False,
            "llm_entry_point_pass": False,
        },
    }

    _COMMAND_PREFIX = re.compile(
        r"^(?:\$\s*)?"
        r"(python|pytest|pip|poetry|uv|npm|pnpm|yarn|node|bun|"
        r"make|docker|go|cargo|dotnet|java|mvn|gradle)\b",
        re.IGNORECASE,
    )

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
            heuristic_summaries=sum(
                1 for p in self._summary_providers.values() if p == "heuristic"
            ),
            estimated_cost_usd=self._estimate_generation_cost(),
            errors=errors,
        )

    async def _run_analysis(self) -> None:
        """Run code analysis phase."""
        logger.info("Starting analysis of %s", self.project_path)

        # Use GraphBuilder to do full analysis
        self._project, self._graph = await self.graph_builder.build(self.project_path)
        self._structure_info = self.graph_builder.last_structure

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
                self._summary_input_tokens[path] = result.input_tokens or 0
                self._summary_output_tokens[path] = result.output_tokens or 0
                if result.provider_used != "heuristic":
                    self._llm_calls += 1
            else:
                logger.warning("Failed to summarize %s: %s", path, result.error)

            if progress_callback and i % 5 == 0:  # Update every 5 modules
                progress_callback("summarization", "progress", f"{i}/{total} modules")

        await self._run_higher_level_summaries(progress_callback)

        return summaries

    async def _run_higher_level_summaries(
        self,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        """Run architecture and entry-point LLM passes for richer onboarding output."""
        if not self.config.use_llm or not self.config.providers:
            return

        if self._project and self._structure_info and self.config.llm_architecture_pass:
            if progress_callback:
                progress_callback("summarization", "progress", "Architecture synthesis")

            architecture_result = await self.summarizer.summarize_architecture(
                self._project,
                self._structure_info,
                graph=self._graph,
            )
            if architecture_result.success and architecture_result.summary:
                self._architecture_summary = architecture_result.summary
                self._architecture_provider = architecture_result.provider_used
                self._summary_tokens["__architecture__"] = architecture_result.tokens_used or 0
                self._summary_input_tokens["__architecture__"] = (
                    architecture_result.input_tokens or 0
                )
                self._summary_output_tokens["__architecture__"] = (
                    architecture_result.output_tokens or 0
                )
                if architecture_result.provider_used != "heuristic":
                    self._llm_calls += 1

        if not (self._project and self._graph and self.config.llm_entry_point_pass):
            return

        if progress_callback:
            progress_callback("summarization", "progress", "Entry-point guidance synthesis")

        entry_candidates = self._project.entry_points
        if not entry_candidates:
            entry_candidates = self._graph.get_entry_points()

        for entry_point in entry_candidates[:3]:
            result = await self.summarizer.summarize_entry_point(entry_point, graph=self._graph)
            if not result.success or not result.summary:
                continue

            key = str(entry_point.path)
            self._entry_point_guidance[key] = result.summary
            self._entry_point_providers[key] = result.provider_used
            token_key = f"__entry::{key}"
            self._summary_tokens[token_key] = result.tokens_used or 0
            self._summary_input_tokens[token_key] = result.input_tokens or 0
            self._summary_output_tokens[token_key] = result.output_tokens or 0
            if result.provider_used != "heuristic":
                self._llm_calls += 1

    def _assemble_guide(self, summaries: dict[str, str]) -> OnboardingGuide:
        """Assemble the final guide from analysis and summaries."""
        guide = OnboardingGuide(
            project_name=self._project.name if self._project else self.project_path.name,
            project_path=str(self.project_path),
            model_used=self._get_model_name(),
        )

        section_builders = {
            SectionType.OVERVIEW: self._create_overview_section,
            SectionType.ARCHITECTURE: self._create_architecture_section,
            SectionType.MODULES: lambda: self._create_modules_section(summaries),
            SectionType.DEPENDENCIES: self._create_dependencies_section,
            SectionType.START_HERE: self._create_start_here_section,
        }

        for section_template in self.guide_template.sections:
            if not section_template.enabled:
                continue

            builder = section_builders.get(section_template.section_type)
            if builder is None:
                continue

            section = builder()
            if section_template.title:
                section.title = section_template.title
            guide.add_section(section)

        return guide

    def _create_overview_section(self) -> Section:
        """Create the overview section."""
        lines = []

        quality_banner = self._quality_banner_lines()
        if quality_banner:
            lines.extend(quality_banner)
            lines.append("")

        if self._project:
            if self._project.primary_language:
                lines.append(f"**Primary Language:** {self._project.primary_language}")
            if self._project.build_system:
                lines.append(f"**Build System:** {self._project.build_system}")
            if self._project.package_manager:
                lines.append(f"**Package Manager:** {self._project.package_manager}")
            lines.append(f"**Modules:** {self._project.module_count}")

            readme_summary = self._extract_project_summary(self._project.readme_content or "")
            if readme_summary:
                lines.append("")
                lines.append(readme_summary)

        return Section(
            section_type=SectionType.OVERVIEW,
            title="Overview",
            content="\n".join(lines) if lines else "Project overview not available.",
        )

    def _create_architecture_section(self) -> Section:
        """Create the architecture section."""
        lines = []

        if self._architecture_summary:
            lines.append(
                f"> {self._quality_badge(self._architecture_provider)} {self._architecture_summary}"
            )
            lines.append("")

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

            flow_lines = self._runtime_flow_lines()
            if flow_lines:
                lines.append("### Runtime Flow Map")
                lines.append("")
                lines.extend(flow_lines)
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
                        quality_badge = self._quality_badge(provider_used)
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
        """Create a component-focused dependency section."""
        lines = []

        if self._graph and self._project:
            component_modules, component_edges, internal_edges = (
                self._component_dependency_summary()
            )

            lines.append(f"**Total Modules:** {self._graph.node_count}")
            lines.append(f"**Total Dependencies:** {self._graph.edge_count}")
            lines.append(f"**Components:** {len(component_modules)}")
            if internal_edges:
                lines.append(f"**Within-Component Dependencies:** {internal_edges}")
            lines.append("")

            lines.append("### Component Overview")
            lines.append("")
            for component, modules in sorted(
                component_modules.items(),
                key=lambda item: len(item[1]),
                reverse=True,
            )[:10]:
                sample_names = ", ".join(module.name for module in modules[:3])
                if len(modules) > 3:
                    sample_names += ", ..."
                lines.append(f"- **{component}**: {len(modules)} module(s) ({sample_names})")
            lines.append("")

            if self.config.include_mermaid and component_edges:
                lines.append("### Component Dependency Map")
                lines.append("")
                lines.append("```mermaid")
                lines.append(self._component_dependency_mermaid(component_modules, component_edges))
                lines.append("```")
                lines.append("")

            if component_edges:
                lines.append("### Strongest Component Links")
                lines.append("")
                strongest_links = sorted(
                    component_edges.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )[:8]
                for (source, target), edge_count in strongest_links:
                    lines.append(f"- **{source} -> {target}**: {edge_count} dependency edge(s)")
                lines.append("")

            lines.append("### Dependency Hubs")
            lines.append("")
            for module in self._graph.get_core_modules(threshold=2)[:8]:
                outgoing = len(self._graph.get_dependencies(module.path))
                incoming = len(self._graph.get_dependents(module.path))
                rel_path = self._relative_module_path(module)
                lines.append(
                    f"- **{module.name}** ({rel_path}): {outgoing} outbound, {incoming} inbound"
                )
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
            recommendations = get_start_here_recommendations(
                list(self._project.modules.values()),
                self._graph,
                max_recommendations=3,
            )

            run_commands = self._extract_run_commands(self._project.readme_content or "")

            lines.append("Follow this onboarding sequence:")
            lines.append("")

            step = 1
            if run_commands:
                lines.append(f"{step}. Run `{run_commands[0]}` to validate the local environment.")
                step += 1
            if len(run_commands) > 1:
                lines.append(f"{step}. Run `{run_commands[1]}` to exercise tests or app startup.")
                step += 1

            if recommendations:
                primary = recommendations[0]
                first_module = self._project.modules.get(str(primary.path))
                if first_module is not None:
                    rel = first_module.path.relative_to(self.project_path)
                    lines.append(f"{step}. Read `{rel}` first to understand the control surface.")
                    step += 1

                if len(recommendations) > 1:
                    follow_module = self._project.modules.get(str(recommendations[1].path))
                    if follow_module is not None:
                        rel = follow_module.path.relative_to(self.project_path)
                        lines.append(f"{step}. Continue with `{rel}` to map core dependencies.")
                        step += 1

            while step <= 3:
                lines.append(
                    f"{step}. Review the Architecture section and trace one runtime flow end-to-end."
                )
                step += 1

            lines.append("")

            if recommendations:
                lines.append("### Follow-up Code Paths")
                lines.append("")
                for rec in recommendations[:3]:
                    module = self._project.modules.get(str(rec.path))
                    if module is None:
                        continue

                    rel_path = module.path.relative_to(self.project_path)
                    lines.append(f"- **{module.name}** (`{rel_path}`)")
                    if rec.reasons:
                        lines.append(f"  - Why: {rec.reasons[0]}")

                    guidance = self._entry_point_guidance.get(str(module.path))
                    if guidance:
                        badge = self._quality_badge(
                            self._entry_point_providers.get(str(module.path), "heuristic")
                        )
                        lines.append(f"  - Guidance: {badge} {guidance}")
                lines.append("")

            if not recommendations:
                lines.append("No clear entry points detected.")
                lines.append(
                    "Start with the most-connected modules in the Architecture section, then"
                    " trace their dependencies."
                )

        return Section(
            section_type=SectionType.START_HERE,
            title="Start Here",
            content="\n".join(lines) if lines else "Getting started guide not available.",
        )

    def _apply_quality_profile_defaults(self) -> None:
        """Apply quality-profile defaults while respecting explicit overrides."""
        profile = self.config.quality_profile.strip().lower()
        if profile not in self._QUALITY_PROFILE_DEFAULTS:
            valid = ", ".join(sorted(self._QUALITY_PROFILE_DEFAULTS))
            raise ValueError(
                f"Unsupported quality profile '{self.config.quality_profile}'. Use: {valid}"
            )

        defaults = self._QUALITY_PROFILE_DEFAULTS[profile]
        self.config.quality_profile = profile

        if profile == "minimal":
            self.config.use_llm = False

        if self.config.minimum_module_words == 0:
            self.config.minimum_module_words = int(defaults["minimum_module_words"])
        if self.config.minimum_architecture_words == 0:
            self.config.minimum_architecture_words = int(defaults["minimum_architecture_words"])
        if self.config.minimum_entry_point_words == 0:
            self.config.minimum_entry_point_words = int(defaults["minimum_entry_point_words"])

        self.config.llm_architecture_pass = bool(
            self.config.llm_architecture_pass and defaults["llm_architecture_pass"]
        )
        self.config.llm_entry_point_pass = bool(
            self.config.llm_entry_point_pass and defaults["llm_entry_point_pass"]
        )

    def _quality_banner_lines(self) -> list[str]:
        """Build quality coverage banner lines for the overview section."""
        if not self._summary_providers:
            return []

        total = len(self._summary_providers)
        llm_count = sum(
            1 for p in self._summary_providers.values() if p not in {"heuristic", "none"}
        )
        heuristic_count = sum(1 for p in self._summary_providers.values() if p == "heuristic")
        coverage = (llm_count / total) * 100 if total else 0.0
        fallback_ratio = heuristic_count / total if total else 0.0

        if fallback_ratio >= 0.6:
            fallback_level = "high"
        elif fallback_ratio >= 0.3:
            fallback_level = "moderate"
        else:
            fallback_level = "low"

        lines = [
            f"> Quality Profile: **{self.config.quality_profile}**",
            f"> LLM Coverage: **{coverage:.1f}%** ({llm_count}/{total} module summaries)",
            f"> Heuristic Fallback: **{fallback_level}** ({heuristic_count}/{total})",
        ]

        if self._architecture_provider != "none":
            lines.append(f"> Architecture Synthesis: **{self._architecture_provider}**")

        if fallback_level == "high":
            lines.append(
                "> Warning: output is mostly heuristic. Re-run with `--quality detailed` and auto mode."
            )

        return lines

    def _quality_badge(self, provider_used: str) -> str:
        """Render a quality badge from provider usage."""
        if provider_used == "heuristic":
            return "[heuristic]"
        if provider_used == "none":
            return "[none]"
        return f"[LLM:{provider_used}]"

    def _runtime_flow_lines(self) -> list[str]:
        """Create human-readable runtime flow bullets from graph topology."""
        if not (self._project and self._graph):
            return []

        entry_points = self._project.entry_points
        if not entry_points:
            entry_points = self._graph.get_entry_points()

        lines: list[str] = []
        for entry_point in entry_points[:4]:
            chain = [entry_point.name]
            current = entry_point
            visited = {str(entry_point.path)}

            for _ in range(3):
                deps = self._graph.get_dependencies(current.path)
                if not deps:
                    break
                nxt = deps[0]
                if str(nxt.path) in visited:
                    break
                chain.append(nxt.name)
                visited.add(str(nxt.path))
                current = nxt

            if len(chain) > 1:
                flow = " -> ".join(chain)
                lines.append(f"- `{flow}`")

        return lines

    def _component_dependency_summary(
        self,
    ) -> tuple[dict[str, list[Module]], dict[tuple[str, str], int], int]:
        """Aggregate dependency edges at component granularity."""
        component_modules: dict[str, list[Module]] = {}
        component_edges: dict[tuple[str, str], int] = {}
        internal_edges = 0

        if not (self._project and self._graph):
            return component_modules, component_edges, internal_edges

        for module in self._project.modules.values():
            component = self._component_label(module.path)
            component_modules.setdefault(component, []).append(module)

        for source, target, _kind in self._graph.iter_edges():
            source_component = self._component_label(source.path)
            target_component = self._component_label(target.path)

            if source_component == target_component:
                internal_edges += 1
                continue

            edge_key = (source_component, target_component)
            component_edges[edge_key] = component_edges.get(edge_key, 0) + 1

        return component_modules, component_edges, internal_edges

    def _component_dependency_mermaid(
        self,
        component_modules: dict[str, list[Module]],
        component_edges: dict[tuple[str, str], int],
        max_components: int = 12,
        max_edges: int = 24,
    ) -> str:
        """Render a compact component-level Mermaid graph."""
        lines = ["graph LR"]
        ordered_components = sorted(
            component_modules.items(),
            key=lambda item: len(item[1]),
            reverse=True,
        )[:max_components]
        selected = [name for name, _ in ordered_components]
        selected_set = set(selected)
        node_ids = {name: f"c{index}" for index, name in enumerate(selected)}

        for name in selected:
            label = f"{name} ({len(component_modules[name])})".replace('"', r"\"")
            lines.append(f'    {node_ids[name]}["{label}"]')

        included_edges = 0
        for (source, target), edge_count in sorted(
            component_edges.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            if source not in selected_set or target not in selected_set:
                continue

            lines.append(f"    {node_ids[source]} -->|{edge_count}| {node_ids[target]}")
            included_edges += 1
            if included_edges >= max_edges:
                break

        if included_edges == 0:
            lines.append("    %% No cross-component edges in selected components")

        return "\n".join(lines)

    def _component_label(self, module_path: Path) -> str:
        """Map module paths to stable component labels."""
        try:
            relative = module_path.relative_to(self.project_path)
        except ValueError:
            return "(external)"

        parts = relative.parts
        if not parts:
            return "(root)"
        if len(parts) == 1:
            return "(root)"

        head = parts[0]
        if head in {"src", "lib", "app"} and len(parts) >= 3:
            return f"{head}/{parts[1]}"
        return head

    def _relative_module_path(self, module: Module) -> str:
        """Return module path relative to analyzed project root."""
        try:
            return str(module.path.relative_to(self.project_path))
        except ValueError:
            return str(module.path)

    def _extract_project_summary(self, readme_content: str) -> str | None:
        """Extract a single high-signal project description line from README text."""
        if not readme_content.strip():
            return None

        for paragraph in re.split(r"\n\s*\n", readme_content):
            candidate = " ".join(paragraph.strip().split())
            if len(candidate) < 60:
                continue
            if candidate.startswith("#"):
                continue
            if candidate.startswith(("![", "<img", "<svg")):
                continue

            alpha_chars = sum(1 for char in candidate if char.isalpha())
            if alpha_chars / max(1, len(candidate)) < 0.45:
                continue

            return candidate[:280]

        return None

    def _extract_run_commands(self, text: str, max_items: int = 6) -> list[str]:
        """Extract likely run/test commands from README-like text."""
        commands: list[str] = []
        seen: set[str] = set()

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            line = line.lstrip("-*0123456789. ").strip("`")
            if not line or line.startswith("#"):
                continue

            if not self._COMMAND_PREFIX.match(line):
                continue

            normalized = " ".join(line.split())
            if normalized in seen:
                continue

            seen.add(normalized)
            commands.append(normalized)
            if len(commands) >= max_items:
                break

        return commands

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

        input_tokens = sum(self._summary_input_tokens.values())
        output_tokens = sum(self._summary_output_tokens.values())

        if input_tokens == 0 and output_tokens == 0 and self._summary_tokens:
            # Backward-compatible fallback for older call-sites that only store totals.
            input_tokens = sum(self._summary_tokens.values())

        token_estimate = TokenEstimate(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
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
