"""Base analyzer framework and registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from pathlib import Path

    from devwayfinder.core.protocols import AnalysisResult


class BaseAnalyzer(ABC):
    """
    Abstract base class for code analyzers.

    Provides the foundation for all analyzer implementations.
    Subclasses must implement the core analysis methods.
    """

    # Class-level configuration
    SUPPORTED_EXTENSIONS: ClassVar[set[str]] = set()
    SUPPORTED_LANGUAGES: ClassVar[list[str]] = []

    def __init__(self, exclude_patterns: list[str] | None = None) -> None:
        """
        Initialize analyzer.

        Args:
            exclude_patterns: Glob patterns for paths to exclude
        """
        self.exclude_patterns = exclude_patterns or []

    @property
    def supported_languages(self) -> list[str]:
        """Languages this analyzer supports."""
        return list(self.SUPPORTED_LANGUAGES)

    def can_analyze(self, path: Path) -> bool:
        """
        Check if this analyzer can handle the given path.

        Args:
            path: File path to check

        Returns:
            True if this analyzer can process the file
        """
        if not path.is_file():
            return False

        extension = path.suffix.lower()
        return extension in self.SUPPORTED_EXTENSIONS

    @abstractmethod
    async def analyze(self, path: Path) -> AnalysisResult:
        """
        Analyze a file.

        Args:
            path: Path to analyze

        Returns:
            Analysis result with extracted information
        """
        ...

    def _detect_language(self, path: Path) -> str | None:
        """
        Detect programming language from file extension.

        Args:
            path: File path

        Returns:
            Language name or None
        """
        return EXTENSION_TO_LANGUAGE.get(path.suffix.lower())


# Extension to language mapping
EXTENSION_TO_LANGUAGE: dict[str, str] = {
    # Python
    ".py": "python",
    ".pyi": "python",
    ".pyw": "python",
    # JavaScript/TypeScript
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    # Go
    ".go": "go",
    # Rust
    ".rs": "rust",
    # Java
    ".java": "java",
    # Kotlin
    ".kt": "kotlin",
    ".kts": "kotlin",
    # C#
    ".cs": "csharp",
    # C/C++
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".hxx": "cpp",
    # Ruby
    ".rb": "ruby",
    ".rake": "ruby",
    # PHP
    ".php": "php",
    # Swift
    ".swift": "swift",
    # Shell
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    # Others
    ".scala": "scala",
    ".clj": "clojure",
    ".ex": "elixir",
    ".exs": "elixir",
    ".erl": "erlang",
    ".hs": "haskell",
    ".ml": "ocaml",
    ".mli": "ocaml",
    ".lua": "lua",
    ".r": "r",
    ".R": "r",
    ".jl": "julia",
    ".pl": "perl",
    ".pm": "perl",
    ".dart": "dart",
    ".zig": "zig",
    ".nim": "nim",
    ".v": "vlang",
    ".groovy": "groovy",
}

# Language to extensions mapping (reverse)
LANGUAGE_TO_EXTENSIONS: dict[str, set[str]] = {}
for ext, lang in EXTENSION_TO_LANGUAGE.items():
    LANGUAGE_TO_EXTENSIONS.setdefault(lang, set()).add(ext)


class AnalyzerRegistry:
    """
    Registry for code analyzers.

    Manages available analyzers and provides lookup by language or file extension.
    Uses the strategy pattern to select appropriate analyzer for each file.
    """

    _instance: AnalyzerRegistry | None = None

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._analyzers: dict[str, BaseAnalyzer] = {}
        self._default_analyzer: BaseAnalyzer | None = None

    @classmethod
    def get_instance(cls) -> AnalyzerRegistry:
        """Get singleton registry instance."""
        if cls._instance is None:
            cls._instance = AnalyzerRegistry()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing)."""
        cls._instance = None

    def register(self, language: str, analyzer: BaseAnalyzer) -> None:
        """
        Register an analyzer for a language.

        Args:
            language: Language identifier (e.g., 'python', 'javascript')
            analyzer: Analyzer instance
        """
        self._analyzers[language.lower()] = analyzer

    def register_default(self, analyzer: BaseAnalyzer) -> None:
        """
        Register a default/fallback analyzer.

        Args:
            analyzer: Analyzer to use when no language-specific one is found
        """
        self._default_analyzer = analyzer

    def get_analyzer(self, language: str) -> BaseAnalyzer | None:
        """
        Get analyzer for a language.

        Args:
            language: Language identifier

        Returns:
            Registered analyzer or None
        """
        return self._analyzers.get(language.lower())

    def get_analyzer_for_file(self, path: Path) -> BaseAnalyzer | None:
        """
        Get appropriate analyzer for a file.

        Args:
            path: File path

        Returns:
            Analyzer that can handle the file, or default analyzer
        """
        # Detect language from extension
        language = EXTENSION_TO_LANGUAGE.get(path.suffix.lower())

        if language:
            analyzer = self._analyzers.get(language)
            if analyzer:
                return analyzer

        # Try default analyzer
        return self._default_analyzer

    def list_languages(self) -> list[str]:
        """List all registered languages."""
        return list(self._analyzers.keys())

    def has_analyzer(self, language: str) -> bool:
        """Check if an analyzer is registered for a language."""
        return language.lower() in self._analyzers

    def clear(self) -> None:
        """Clear all registered analyzers."""
        self._analyzers.clear()
        self._default_analyzer = None

    @property
    def analyzer_count(self) -> int:
        """Number of registered analyzers."""
        return len(self._analyzers)

    def get_all_analyzers(self) -> dict[str, BaseAnalyzer]:
        """Get all registered analyzers."""
        return dict(self._analyzers)
