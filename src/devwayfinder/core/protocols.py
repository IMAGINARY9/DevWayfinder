"""Protocol definitions for DevWayfinder components."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path

    from devwayfinder.core.guide import OnboardingGuide


# ============================================================================
# ANALYZER PROTOCOLS
# ============================================================================


class AnalysisResult:
    """Result of analyzing a single file or directory."""

    def __init__(
        self,
        path: Path,
        imports: list[str] | None = None,
        exports: list[str] | None = None,
        is_entry_point: bool = False,
        language: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.path = path
        self.imports = imports or []
        self.exports = exports or []
        self.is_entry_point = is_entry_point
        self.language = language
        self.metadata = metadata or {}


@runtime_checkable
class Analyzer(Protocol):
    """
    Interface for code analyzers.

    Analyzers extract structural information from source files.
    """

    @property
    def supported_languages(self) -> list[str]:
        """Languages this analyzer supports."""
        ...

    def can_analyze(self, path: Path) -> bool:
        """
        Check if this analyzer can handle the given path.

        Args:
            path: File or directory path

        Returns:
            True if this analyzer can process the path
        """
        ...

    async def analyze(self, path: Path) -> AnalysisResult:
        """
        Analyze a file or directory.

        Args:
            path: Path to analyze

        Returns:
            Analysis result with extracted information
        """
        ...


# ============================================================================
# PROVIDER PROTOCOLS
# ============================================================================


class SummarizationContext:
    """Context provided to LLM for summarization."""

    def __init__(
        self,
        module_name: str,
        file_content: str | None = None,
        signatures: list[str] | None = None,
        docstrings: list[str] | None = None,
        imports: list[str] | None = None,
        exports: list[str] | None = None,
        neighbors: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.module_name = module_name
        self.file_content = file_content
        self.signatures = signatures or []
        self.docstrings = docstrings or []
        self.imports = imports or []
        self.exports = exports or []
        self.neighbors = neighbors or []
        self.metadata = metadata or {}

    def with_updated_metadata(self, **updates: Any) -> SummarizationContext:
        """Return a copy of this context with metadata updates applied."""
        merged_metadata = dict(self.metadata)
        merged_metadata.update(updates)
        return SummarizationContext(
            module_name=self.module_name,
            file_content=self.file_content,
            signatures=list(self.signatures),
            docstrings=list(self.docstrings),
            imports=list(self.imports),
            exports=list(self.exports),
            neighbors=list(self.neighbors),
            metadata=merged_metadata,
        )

    def to_prompt_context(self, max_chars: int = 4000) -> str:
        """Format context for LLM prompt."""
        parts = [f"Module: {self.module_name}"]

        relative_path = self.metadata.get("relative_path")
        if isinstance(relative_path, str) and relative_path:
            parts.append(f"Path: {relative_path}")

        language = self.metadata.get("language")
        if isinstance(language, str) and language:
            parts.append(f"Language: {language}")

        if self.docstrings:
            parts.append("\nDocstrings:\n" + "\n".join(self.docstrings[:5]))

        if self.signatures:
            parts.append("\nKey Signatures:\n" + "\n".join(self.signatures[:10]))

        if self.imports:
            parts.append(f"\nImports: {', '.join(self.imports[:10])}")

        if self.exports:
            parts.append(f"\nExports: {', '.join(self.exports[:10])}")

        if self.neighbors:
            parts.append(f"\nRelated Modules: {', '.join(self.neighbors[:10])}")

        risk_markers = self.metadata.get("risk_markers")
        if isinstance(risk_markers, list):
            markers = [str(marker).strip() for marker in risk_markers if str(marker).strip()]
            if markers:
                parts.append(
                    "\nRisk Markers:\n" + "\n".join(f"- {marker}" for marker in markers[:6])
                )

        prompt_hints = self.metadata.get("prompt_hints")
        if isinstance(prompt_hints, list):
            hints = [str(hint).strip() for hint in prompt_hints if str(hint).strip()]
            if hints:
                parts.append("\nFocus:\n" + "\n".join(f"- {hint}" for hint in hints[:6]))

        metadata_lines = self._render_metadata_lines()
        if metadata_lines:
            parts.append("\nContext Signals:\n" + "\n".join(metadata_lines))

        if self.file_content:
            excerpt = self.file_content.strip()
            if excerpt:
                snippet = excerpt[:1200]
                if len(excerpt) > len(snippet):
                    snippet += "\n...(truncated)"
                parts.append("\nCode Excerpt:\n" + snippet)

        result = "\n".join(parts)
        if len(result) > max_chars:
            result = result[:max_chars] + "\n...(truncated)"

        return result

    def _render_metadata_lines(self) -> list[str]:
        """Render concise metadata key/value lines for prompt context."""
        skipped = {
            "relative_path",
            "language",
            "prompt_hints",
            "risk_markers",
            "minimum_summary_words",
            "quality_profile",
        }
        lines: list[str] = []
        for key, value in self.metadata.items():
            if key in skipped or value in (None, "", [], {}):
                continue

            rendered = self._render_metadata_value(value)
            if rendered:
                label = key.replace("_", " ")
                lines.append(f"- {label}: {rendered}")

            if len(lines) >= 12:
                break

        return lines

    def _render_metadata_value(self, value: Any) -> str:
        """Render metadata values into concise strings."""
        if isinstance(value, bool):
            return "yes" if value else "no"

        if isinstance(value, (int, float, str)):
            text = str(value).strip()
            return text[:160]

        if isinstance(value, list):
            list_items = [str(item).strip() for item in value if str(item).strip()]
            if not list_items:
                return ""
            joined = ", ".join(list_items[:6])
            if len(list_items) > 6:
                joined += ", ..."
            return joined[:160]

        if isinstance(value, dict):
            items: list[str] = []
            for idx, (k, v) in enumerate(value.items()):
                if idx >= 4:
                    items.append("...")
                    break
                items.append(f"{k}={v}")
            return ", ".join(items)[:160]

        return str(value).strip()[:160]


class HealthStatus:
    """Health check result for a provider."""

    def __init__(
        self,
        healthy: bool,
        message: str = "",
        latency_ms: float | None = None,
        model_info: dict[str, Any] | None = None,
    ) -> None:
        self.healthy = healthy
        self.message = message
        self.latency_ms = latency_ms
        self.model_info = model_info or {}


@runtime_checkable
class ModelProvider(Protocol):
    """
    Interface for LLM backends.

    Providers generate natural-language summaries from code context.
    """

    @property
    def name(self) -> str:
        """Provider identifier."""
        ...

    @property
    def available(self) -> bool:
        """Check if provider is currently accessible."""
        ...

    async def summarize(self, context: SummarizationContext) -> str:
        """
        Generate a natural-language summary.

        Args:
            context: Code context to summarize

        Returns:
            Natural-language description
        """
        ...

    async def health_check(self) -> HealthStatus:
        """
        Verify provider connectivity and status.

        Returns:
            Health status with details
        """
        ...


# ============================================================================
# GENERATOR PROTOCOLS
# ============================================================================


@runtime_checkable
class OutputGenerator(Protocol):
    """
    Interface for output generators.

    Generators render OnboardingGuide to various formats.
    """

    @property
    def format_name(self) -> str:
        """Output format identifier (e.g., 'markdown', 'html')."""
        ...

    @property
    def file_extension(self) -> str:
        """File extension for output (e.g., '.md', '.html')."""
        ...

    def generate(self, guide: OnboardingGuide) -> str:
        """
        Render guide to output format.

        Args:
            guide: Guide to render

        Returns:
            Formatted output string
        """
        ...


# ============================================================================
# CACHE PROTOCOLS
# ============================================================================


@runtime_checkable
class CacheStore(Protocol):
    """
    Interface for cache storage.

    Caches store analysis results and LLM responses.
    """

    def get(self, key: str) -> Any | None:
        """
        Retrieve cached value.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        ...

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """
        Store value in cache.

        Args:
            key: Cache key
            value: Value to store
            ttl_seconds: Time-to-live in seconds (None = no expiry)
        """
        ...

    def delete(self, key: str) -> bool:
        """
        Remove value from cache.

        Args:
            key: Cache key

        Returns:
            True if key existed and was deleted
        """
        ...

    def clear(self) -> int:
        """
        Clear all cached values.

        Returns:
            Number of entries cleared
        """
        ...
