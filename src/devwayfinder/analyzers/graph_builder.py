"""Dependency graph builder from analysis results."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from devwayfinder.analyzers.base import AnalyzerRegistry
from devwayfinder.analyzers.python_analyzer import PythonASTAnalyzer
from devwayfinder.analyzers.regex_extractor import RegexAnalyzer
from devwayfinder.analyzers.structure import StructureAnalyzer, StructureInfo
from devwayfinder.core.graph import DependencyGraph
from devwayfinder.core.models import Module, ModuleType, Project

if TYPE_CHECKING:
    from pathlib import Path

    from devwayfinder.core.protocols import AnalysisResult

logger = logging.getLogger(__name__)


class ImportResolver:
    """
    Resolves import strings to file paths.

    Maps import names (e.g., 'mypackage.module') to actual files
    within the project.
    """

    def __init__(self, project_root: Path, source_files: list[Path]) -> None:
        """
        Initialize import resolver.

        Args:
            project_root: Root directory of the project
            source_files: List of all source files
        """
        self.project_root = project_root
        self.source_files = source_files
        self._module_map: dict[str, Path] = {}
        self._build_module_map()

    def _build_module_map(self) -> None:
        """Build mapping from module names to file paths."""
        for file_path in self.source_files:
            try:
                rel_path = file_path.relative_to(self.project_root)
            except ValueError:
                continue

            # Convert path to module name
            parts = list(rel_path.parts)
            if not parts:
                continue

            # Remove extension from last part
            parts[-1] = parts[-1].rsplit(".", 1)[0]

            # Build module name
            module_name = ".".join(parts)
            self._module_map[module_name] = file_path

            # Also map without src/ prefix if present
            if parts and parts[0] == "src":
                alt_name = ".".join(parts[1:])
                if alt_name:
                    self._module_map[alt_name] = file_path

            # Handle __init__.py - also map the package name
            if parts[-1] == "__init__":
                package_name = ".".join(parts[:-1])
                if package_name:
                    self._module_map[package_name] = file_path

    def resolve(self, import_name: str, from_file: Path | None = None) -> Path | None:
        """
        Resolve an import name to a file path.

        Args:
            import_name: Import string (e.g., 'mypackage.module')
            from_file: File making the import (for relative imports)

        Returns:
            Resolved file path or None
        """
        # Direct lookup
        if import_name in self._module_map:
            return self._module_map[import_name]

        # Try with submodule resolution
        # e.g., 'package.submodule.func' -> 'package.submodule'
        parts = import_name.split(".")
        for i in range(len(parts), 0, -1):
            partial = ".".join(parts[:i])
            if partial in self._module_map:
                return self._module_map[partial]

        # Handle relative imports
        if import_name.startswith(".") and from_file:
            resolved = self._resolve_relative(import_name, from_file)
            if resolved:
                return resolved

        return None

    def _resolve_relative(self, import_name: str, from_file: Path) -> Path | None:
        """Resolve a relative import."""
        # Count leading dots
        dots = 0
        for char in import_name:
            if char == ".":
                dots += 1
            else:
                break

        remaining = import_name[dots:]

        try:
            rel_path = from_file.relative_to(self.project_root)
        except ValueError:
            return None

        # Get package directory
        parts = list(rel_path.parent.parts)

        # Go up based on dots (1 dot = current, 2 = parent, etc.)
        up_count = dots - 1
        if up_count > len(parts):
            return None

        if up_count > 0:
            parts = parts[:-up_count]

        # Add remaining import parts
        if remaining:
            parts.extend(remaining.split("."))

        # Try to find the module
        module_name = ".".join(parts)
        return self._module_map.get(module_name)

    def get_module_name(self, file_path: Path) -> str:
        """Get module name for a file path."""
        try:
            rel_path = file_path.relative_to(self.project_root)
        except ValueError:
            return file_path.stem

        parts = list(rel_path.parts)
        if parts:
            parts[-1] = parts[-1].rsplit(".", 1)[0]
        return ".".join(parts)

    @property
    def module_map(self) -> dict[str, Path]:
        """Get the module map (for debugging)."""
        return dict(self._module_map)


class GraphBuilder:
    """
    Builds dependency graph from analysis results.

    Coordinates analyzers, resolves imports, and constructs the graph.
    """

    def __init__(
        self,
        exclude_patterns: list[str] | None = None,
        respect_gitignore: bool = True,
    ) -> None:
        """
        Initialize graph builder.

        Args:
            exclude_patterns: Patterns to exclude from analysis
            respect_gitignore: Whether to respect .gitignore
        """
        self.exclude_patterns = exclude_patterns
        self.respect_gitignore = respect_gitignore
        self._setup_analyzers()

    def _setup_analyzers(self) -> None:
        """Set up analyzer registry with available analyzers."""
        self.registry = AnalyzerRegistry()

        # Register Python analyzer (AST-based)
        python_analyzer = PythonASTAnalyzer(self.exclude_patterns)
        self.registry.register("python", python_analyzer)

        # Register regex analyzer as default for other languages
        regex_analyzer = RegexAnalyzer(self.exclude_patterns)
        self.registry.register_default(regex_analyzer)

        # Register regex for all other supported languages
        for language in regex_analyzer.supported_languages:
            if language != "python":
                self.registry.register(language, regex_analyzer)

        # Structure analyzer
        self.structure_analyzer = StructureAnalyzer(
            exclude_patterns=self.exclude_patterns,
            respect_gitignore=self.respect_gitignore,
        )

    async def build(self, root_path: Path) -> tuple[Project, DependencyGraph]:
        """
        Build project and dependency graph from a directory.

        Args:
            root_path: Root directory to analyze

        Returns:
            Tuple of (Project, DependencyGraph)
        """
        root_path = root_path.resolve()

        # Analyze structure
        logger.info(f"Analyzing project structure: {root_path}")
        structure = await self.structure_analyzer.analyze(root_path)

        # Create project
        project = self._create_project(structure)

        # Create import resolver
        resolver = ImportResolver(root_path, structure.source_files)

        # Create dependency graph
        graph = DependencyGraph()

        # Analyze each source file
        logger.info(f"Analyzing {len(structure.source_files)} source files")
        analysis_results: dict[Path, AnalysisResult] = {}

        for file_path in structure.source_files:
            result = await self._analyze_file(file_path)
            if result:
                analysis_results[file_path] = result

        # Build modules and graph
        for file_path, result in analysis_results.items():
            module = self._create_module(file_path, result, structure)
            project.modules[str(file_path)] = module
            graph.add_module(module)

        # Add dependency edges
        for file_path, result in analysis_results.items():
            for import_name in result.imports:
                target_path = resolver.resolve(import_name, file_path)
                if target_path and target_path in analysis_results:
                    graph.add_dependency(file_path, target_path, kind="import")

        # Log stats
        logger.info(
            f"Built graph: {graph.node_count} modules, {graph.edge_count} dependencies"
        )

        if graph.has_cycles():
            cycles = graph.find_cycles()
            logger.warning(f"Circular dependencies detected: {len(cycles)} cycles")

        return project, graph

    async def _analyze_file(self, file_path: Path) -> AnalysisResult | None:
        """Analyze a single file."""
        analyzer = self.registry.get_analyzer_for_file(file_path)

        if not analyzer:
            logger.debug(f"No analyzer for: {file_path}")
            return None

        try:
            return await analyzer.analyze(file_path)
        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}: {e}")
            return None

    def _create_project(self, structure: StructureInfo) -> Project:
        """Create Project from structure info."""
        return Project(
            name=structure.root_path.name,
            root_path=structure.root_path,
            build_system=structure.build_system,
            package_manager=structure.package_manager,
            primary_language=structure.primary_language,
            readme_content=structure.readme_content,
            contributing_content=structure.contributing_content,
        )

    def _create_module(
        self, file_path: Path, result: AnalysisResult, structure: StructureInfo
    ) -> Module:
        """Create Module from analysis result."""
        is_entry = result.is_entry_point or file_path in structure.entry_points

        return Module(
            name=file_path.stem,
            path=file_path,
            module_type=ModuleType.FILE,
            language=result.language,
            imports=result.imports,
            exports=result.exports,
            entry_point=is_entry,
        )


async def build_dependency_graph(
    root_path: Path,
    exclude_patterns: list[str] | None = None,
    respect_gitignore: bool = True,
) -> tuple[Project, DependencyGraph]:
    """
    Build project and dependency graph from a directory.

    Convenience function for the common use case.

    Args:
        root_path: Root directory to analyze
        exclude_patterns: Patterns to exclude
        respect_gitignore: Whether to respect .gitignore

    Returns:
        Tuple of (Project, DependencyGraph)
    """
    builder = GraphBuilder(
        exclude_patterns=exclude_patterns,
        respect_gitignore=respect_gitignore,
    )
    return await builder.build(root_path)
