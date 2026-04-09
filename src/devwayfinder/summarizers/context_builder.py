"""Build SummarizationContext from analysis results.

This module transforms raw analysis output into structured context
suitable for LLM prompts.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from devwayfinder.core.protocols import SummarizationContext

if TYPE_CHECKING:
    from pathlib import Path

    from devwayfinder.analyzers.python_analyzer import PythonExtractionResult
    from devwayfinder.analyzers.regex_extractor import ExtractionResult
    from devwayfinder.analyzers.structure import StructureInfo
    from devwayfinder.core.graph import DependencyGraph
    from devwayfinder.core.models import Module, Project


class ContextBuilder:
    """Builds SummarizationContext from various analysis results."""

    _IMPORT_LIMIT = 20
    _EXPORT_LIMIT = 20
    _NEIGHBOR_LIMIT = 10
    _SIGNATURE_LIMIT = 10
    _DOCSTRING_LIMIT = 8
    _FILE_EXCERPT_CHARS = 2000

    _COMMAND_PREFIX = re.compile(
        r"^(?:\$\s*)?"
        r"(python|pytest|pip|poetry|uv|npm|pnpm|yarn|node|bun|"
        r"make|docker|go|cargo|dotnet|java|mvn|gradle)\b",
        re.IGNORECASE,
    )

    def __init__(self, project_root: Path) -> None:
        """Initialize builder with project root for relative path computation."""
        self.project_root = project_root

    def from_module(
        self,
        module: Module,
        *,
        graph: DependencyGraph | None = None,
        file_content: str | None = None,
    ) -> SummarizationContext:
        """Build context from a Module model.

        Args:
            module: The module to build context for
            graph: Optional dependency graph for neighbor information
            file_content: Optional source file content

        Returns:
            SummarizationContext ready for LLM prompt
        """
        dependencies: list[Module] = []
        dependents: list[Module] = []
        neighbors: list[str] = []
        if graph is not None:
            dependencies = graph.get_dependencies(module.path)
            dependents = graph.get_dependents(module.path)
            neighbors = [m.name for m in dependencies[:6]]
            neighbors.extend([m.name for m in dependents[:4]])
            neighbors = list(dict.fromkeys(neighbors))[: self._NEIGHBOR_LIMIT]

        excerpt = file_content
        if excerpt is None:
            excerpt = self._read_file_excerpt(module.path)

        risk_markers = self._module_risk_markers(module, dependencies, dependents)
        prompt_hints = [
            "Describe responsibilities and why this module exists.",
            "Mention how this module is used by nearby modules.",
        ]
        if module.entry_point:
            prompt_hints.append("Explain startup flow and first files to inspect next.")
        if risk_markers:
            prompt_hints.append("Call out risks and coupling boundaries explicitly.")

        return SummarizationContext(
            module_name=module.name,
            file_content=excerpt,
            imports=module.imports[: self._IMPORT_LIMIT],
            exports=module.exports[: self._EXPORT_LIMIT],
            neighbors=neighbors,
            metadata={
                "language": module.language,
                "entry_point": module.entry_point,
                "module_type": module.module_type.value,
                "relative_path": self._relative_name(module.path),
                "loc": module.loc,
                "complexity": module.complexity,
                "dependency_count": len(dependencies),
                "dependent_count": len(dependents),
                "risk_markers": risk_markers,
                "prompt_hints": prompt_hints,
            },
        )

    def from_python_analysis(
        self,
        file_path: Path,
        analysis: PythonExtractionResult,
        *,
        graph: DependencyGraph | None = None,
    ) -> SummarizationContext:
        """Build context from Python AST analysis result.

        Args:
            file_path: Path to the analyzed file
            analysis: Result from PythonASTAnalyzer
            graph: Optional dependency graph

        Returns:
            SummarizationContext with rich Python-specific info
        """
        signatures = [
            f"def {f.name}({', '.join(f.parameters)})"
            for f in analysis.functions[: self._SIGNATURE_LIMIT]
        ]

        for cls in analysis.classes[: self._SIGNATURE_LIMIT]:
            methods = cls.methods[:4]
            sig = f"class {cls.name}"
            if cls.bases:
                sig += f"({', '.join(cls.bases[:3])})"
            if methods:
                sig += f" [{', '.join(methods)}]"
            signatures.append(sig)

        docstrings = []
        if analysis.module_docstring:
            docstrings.append(analysis.module_docstring)
        for cls in analysis.classes[:4]:
            if cls.docstring:
                docstrings.append(f"{cls.name}: {cls.docstring[:220]}")

        for fn in analysis.functions[:3]:
            if fn.docstring:
                docstrings.append(f"{fn.name}: {fn.docstring[:180]}")

        docstrings = docstrings[: self._DOCSTRING_LIMIT]

        neighbors: list[str] = []
        dependencies: list[Module] = []
        if graph is not None:
            dependencies = graph.get_dependencies(file_path)
            neighbors = [m.name for m in dependencies[: self._NEIGHBOR_LIMIT]]

        return SummarizationContext(
            module_name=self._relative_name(file_path),
            signatures=signatures,
            docstrings=docstrings,
            file_content=self._read_file_excerpt(file_path),
            imports=analysis.imports[: self._IMPORT_LIMIT],
            exports=analysis.exports[: self._EXPORT_LIMIT],
            neighbors=neighbors,
            metadata={
                "language": "python",
                "function_count": len(analysis.functions),
                "class_count": len(analysis.classes),
                "has_main": analysis.has_main_block,
                "relative_path": self._relative_name(file_path),
                "dependency_count": len(dependencies),
                "prompt_hints": [
                    "Highlight key classes/functions and their interactions.",
                    "Mention expected runtime usage for this module.",
                ],
            },
        )

    def from_regex_extraction(
        self,
        file_path: Path,
        extraction: ExtractionResult,
        *,
        graph: DependencyGraph | None = None,
    ) -> SummarizationContext:
        """Build context from regex-based extraction.

        Args:
            file_path: Path to the analyzed file
            extraction: Result from RegexAnalyzer
            graph: Optional dependency graph

        Returns:
            SummarizationContext with import/export info
        """
        neighbors: list[str] = []
        if graph is not None:
            deps = graph.get_dependencies(file_path)
            neighbors = [m.name for m in deps[: self._NEIGHBOR_LIMIT]]

        return SummarizationContext(
            module_name=self._relative_name(file_path),
            file_content=self._read_file_excerpt(file_path),
            imports=extraction.imports[: self._IMPORT_LIMIT],
            exports=extraction.exports[: self._EXPORT_LIMIT],
            neighbors=neighbors,
            metadata={
                "extraction_method": "regex",
                "relative_path": self._relative_name(file_path),
                "prompt_hints": [
                    "Infer purpose from imports, exports, and naming patterns.",
                ],
            },
        )

    def for_architecture(
        self,
        project: Project,
        structure: StructureInfo,
        *,
        graph: DependencyGraph | None = None,
    ) -> SummarizationContext:
        """Build context for architecture-level summarization.

        Args:
            project: Project model with all analyzed modules
            structure: Structure analysis with detected patterns
            graph: Optional dependency graph for structure insights

        Returns:
            SummarizationContext for architecture overview
        """
        modules_by_dir: dict[str, list[str]] = {}
        for module in project.modules.values():
            parent = str(module.path.parent.relative_to(project.root_path))
            if parent not in modules_by_dir:
                modules_by_dir[parent] = []
            modules_by_dir[parent].append(module.name)

        structure_lines = []
        for directory, modules in sorted(modules_by_dir.items())[:12]:
            count = len(modules)
            samples = ", ".join(modules[:3])
            if count > 2:
                samples += f", ... ({count} files)"
            structure_lines.append(f"  {directory}: {samples}")

        all_imports: set[str] = set()
        for module in project.modules.values():
            all_imports.update(module.imports[:4])

        entry_points = [m.name for m in project.entry_points[:5]]

        core_modules: list[str] = []
        has_cycles = False
        runtime_flows: list[str] = []
        if graph is not None:
            core_modules = [m.name for m in graph.get_core_modules(threshold=3)[:5]]
            has_cycles = graph.has_cycles()
            runtime_flows = self._runtime_flow_samples(project, graph)

        readme_excerpt = (project.readme_content or "")[:500]
        run_commands = self._extract_command_candidates(project.readme_content or "")
        architecture_hints = [
            "Explain major runtime flow from entry points into core modules.",
            "Call out where data boundaries or persistence occur if detectable.",
        ]
        if run_commands:
            architecture_hints.append("Anchor guidance in concrete run or test commands.")

        return SummarizationContext(
            module_name=project.name,
            imports=sorted(all_imports)[: self._IMPORT_LIMIT],
            exports=entry_points,
            neighbors=core_modules,
            metadata={
                "build_system": structure.build_system,
                "package_manager": structure.package_manager,
                "primary_language": project.primary_language,
                "module_count": project.module_count,
                "directory_structure": "\n".join(structure_lines),
                "readme_excerpt": readme_excerpt,
                "has_circular_deps": has_cycles,
                "runtime_flow_samples": runtime_flows,
                "run_commands": run_commands,
                "prompt_hints": architecture_hints,
                "risk_markers": ["Circular dependencies detected"] if has_cycles else [],
            },
        )

    def for_entry_point(
        self,
        module: Module,
        *,
        graph: DependencyGraph | None = None,
        file_content: str | None = None,
    ) -> SummarizationContext:
        """Build context for entry point summarization.

        Entry points get special treatment with focus on
        "what does this start" and "where does it lead".

        Args:
            module: The entry point module
            graph: Optional dependency graph
            file_content: Optional source content

        Returns:
            SummarizationContext optimized for entry point description
        """
        context = self.from_module(module, graph=graph, file_content=file_content)

        # Enhance metadata for entry point focus
        context.metadata["is_entry_point"] = True
        context.metadata["suggested_exploration"] = self._suggest_next_steps(module, graph)
        call_path = self._build_call_path(module, graph)
        if call_path:
            context.metadata["call_path"] = " -> ".join(call_path)
        context.metadata["prompt_hints"] = [
            "Describe where execution starts and what this bootstraps.",
            "Provide a practical first-reading sequence for onboarding.",
            "Suggest one safe first change after understanding this entry point.",
        ]

        return context

    def _relative_name(self, path: Path) -> str:
        """Get a clean relative name for display."""
        try:
            return str(path.relative_to(self.project_root))
        except ValueError:
            return path.name

    def _suggest_next_steps(
        self,
        module: Module,
        graph: DependencyGraph | None,
    ) -> list[str]:
        """Suggest modules to explore after this entry point."""
        suggestions: list[str] = []

        if graph is not None:
            # Direct dependencies are logical next steps
            deps = graph.get_dependencies(module.path)
            suggestions.extend([m.name for m in deps[:5]])

        return suggestions

    def _read_file_excerpt(self, path: Path, max_chars: int | None = None) -> str | None:
        """Read a bounded file excerpt for prompt grounding."""
        limit = max_chars or self._FILE_EXCERPT_CHARS
        if not path.is_file():
            return None

        try:
            content = path.read_text(encoding="utf-8", errors="ignore").strip()
        except OSError:
            return None

        if not content:
            return None

        if len(content) > limit:
            content = content[:limit] + "\n...(truncated)"
        return content

    def _module_risk_markers(
        self,
        module: Module,
        dependencies: list[Module],
        dependents: list[Module],
    ) -> list[str]:
        """Infer lightweight risk markers for onboarding guidance."""
        markers: list[str] = []

        if len(dependents) >= 8:
            markers.append("Hot file with high fan-in")
        if len(dependencies) >= 10:
            markers.append("High fan-out integration surface")
        if module.entry_point:
            markers.append("Startup boundary")

        suffix = module.path.suffix.lower()
        if suffix in {".json", ".yaml", ".yml", ".toml", ".ini"}:
            markers.append("Configuration boundary")

        return markers

    def _runtime_flow_samples(
        self,
        project: Project,
        graph: DependencyGraph,
        max_samples: int = 4,
    ) -> list[str]:
        """Build simple runtime-flow samples from entry points into dependencies."""
        samples: list[str] = []
        candidates = project.entry_points[:max_samples]
        if not candidates:
            candidates = graph.get_entry_points()[:max_samples]

        for module in candidates:
            path_parts = self._build_call_path(module, graph)
            if len(path_parts) >= 2:
                samples.append(" -> ".join(path_parts))

        return samples

    def _build_call_path(
        self,
        module: Module,
        graph: DependencyGraph | None,
        max_depth: int = 3,
    ) -> list[str]:
        """Build a shallow dependency walk for onboarding context."""
        if graph is None:
            return []

        chain = [module.name]
        current = module
        visited = {str(module.path)}

        for _ in range(max_depth):
            deps = graph.get_dependencies(current.path)
            if not deps:
                break

            next_module = deps[0]
            next_key = str(next_module.path)
            if next_key in visited:
                break

            chain.append(next_module.name)
            visited.add(next_key)
            current = next_module

        return chain

    def _extract_command_candidates(self, text: str, max_items: int = 8) -> list[str]:
        """Extract likely run/test commands from README-style text."""
        commands: list[str] = []
        seen: set[str] = set()

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            # Strip common markdown prefixes and wrappers.
            line = line.lstrip("-*0123456789. ")
            line = line.strip("`")

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
