"""Build SummarizationContext from analysis results.

This module transforms raw analysis output into structured context
suitable for LLM prompts.
"""

from __future__ import annotations

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
        neighbors: list[str] = []
        if graph is not None:
            # Get direct dependencies (both imports and dependents)
            deps = graph.get_dependencies(module.path)
            dependents = graph.get_dependents(module.path)
            neighbors = [m.name for m in deps[:10]]
            neighbors.extend([m.name for m in dependents[:5]])
            neighbors = list(dict.fromkeys(neighbors))[:10]  # Dedupe, limit

        return SummarizationContext(
            module_name=module.name,
            file_content=file_content,
            imports=module.imports[:20],
            exports=module.exports[:20],
            neighbors=neighbors,
            metadata={
                "language": module.language,
                "entry_point": module.entry_point,
                "module_type": str(module.module_type),
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
        # Build function signatures
        signatures = [f"def {f.name}({', '.join(f.parameters)})" for f in analysis.functions[:15]]

        # Add class signatures
        for cls in analysis.classes[:10]:
            methods = cls.methods[:5]  # methods is already list[str]
            sig = f"class {cls.name}"
            if cls.bases:
                sig += f"({', '.join(cls.bases[:3])})"
            if methods:
                sig += f" [{', '.join(methods)}]"
            signatures.append(sig)

        # Collect docstrings
        docstrings = []
        if analysis.module_docstring:
            docstrings.append(analysis.module_docstring)
        for cls in analysis.classes[:5]:
            if cls.docstring:
                docstrings.append(f"{cls.name}: {cls.docstring[:200]}")
        for func in analysis.functions[:5]:
            if func.docstring:
                docstrings.append(f"{func.name}: {func.docstring[:200]}")

        # Get neighbors from graph
        neighbors: list[str] = []
        if graph is not None:
            deps = graph.get_dependencies(file_path)
            neighbors = [m.name for m in deps[:10]]

        return SummarizationContext(
            module_name=self._relative_name(file_path),
            signatures=signatures,
            docstrings=docstrings,
            imports=analysis.imports[:20],
            exports=analysis.exports[:20],
            neighbors=neighbors,
            metadata={
                "language": "python",
                "function_count": len(analysis.functions),
                "class_count": len(analysis.classes),
                "has_main": analysis.has_main_block,
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
            neighbors = [m.name for m in deps[:10]]

        return SummarizationContext(
            module_name=self._relative_name(file_path),
            imports=extraction.imports[:20],
            exports=extraction.exports[:20],
            neighbors=neighbors,
            metadata={
                "extraction_method": "regex",
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
        # Summarize module structure
        modules_by_dir: dict[str, list[str]] = {}
        for module in project.modules.values():
            parent = str(module.path.parent.relative_to(project.root_path))
            if parent not in modules_by_dir:
                modules_by_dir[parent] = []
            modules_by_dir[parent].append(module.name)

        # Build structure summary
        structure_lines = []
        for directory, modules in sorted(modules_by_dir.items())[:15]:
            count = len(modules)
            samples = ", ".join(modules[:3])
            if count > 3:
                samples += f", ... ({count} files)"
            structure_lines.append(f"  {directory}: {samples}")

        # Build imports summary for architecture
        all_imports: set[str] = set()
        for module in project.modules.values():
            all_imports.update(module.imports[:5])

        # Get entry points
        entry_points = [m.name for m in project.entry_points[:5]]

        # Get graph insights if available
        core_modules: list[str] = []
        has_cycles = False
        if graph is not None:
            core_modules = [m.name for m in graph.get_core_modules(threshold=3)[:5]]
            has_cycles = graph.has_cycles()

        return SummarizationContext(
            module_name=project.name,
            imports=sorted(all_imports)[:20],
            exports=entry_points,  # Entry points as "exports" for architecture context
            neighbors=core_modules,  # Core modules as "neighbors" in architecture context
            metadata={
                "build_system": structure.build_system,
                "package_manager": structure.package_manager,
                "primary_language": project.primary_language,
                "module_count": project.module_count,
                "directory_structure": "\n".join(structure_lines),
                "readme_excerpt": (project.readme_content or "")[:500],
                "has_circular_deps": has_cycles,
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
