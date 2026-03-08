"""Protocol definitions for DevWayfinder components."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from devwayfinder.core.models import Module, Project
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
    
    def to_prompt_context(self, max_chars: int = 4000) -> str:
        """Format context for LLM prompt."""
        parts = [f"Module: {self.module_name}"]
        
        if self.docstrings:
            parts.append(f"\nDocstrings:\n" + "\n".join(self.docstrings[:5]))
        
        if self.signatures:
            parts.append(f"\nKey Signatures:\n" + "\n".join(self.signatures[:10]))
        
        if self.imports:
            parts.append(f"\nImports: {', '.join(self.imports[:10])}")
        
        if self.exports:
            parts.append(f"\nExports: {', '.join(self.exports[:10])}")
        
        result = "\n".join(parts)
        if len(result) > max_chars:
            result = result[:max_chars] + "\n...(truncated)"
        
        return result


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
