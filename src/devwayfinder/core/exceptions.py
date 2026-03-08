"""Custom exception hierarchy for DevWayfinder."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class DevWayfinderError(Exception):
    """
    Base exception for all DevWayfinder errors.
    
    All custom exceptions inherit from this class.
    """
    
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


# ============================================================================
# CONFIGURATION ERRORS
# ============================================================================

class ConfigurationError(DevWayfinderError):
    """Base class for configuration-related errors."""
    pass


class InvalidConfigError(ConfigurationError):
    """Raised when configuration values are invalid."""
    
    def __init__(self, key: str, value: Any, reason: str) -> None:
        self.key = key
        self.value = value
        self.reason = reason
        super().__init__(
            f"Invalid configuration for '{key}': {reason}",
            {"key": key, "value": value, "reason": reason}
        )


class MissingConfigError(ConfigurationError):
    """Raised when required configuration is missing."""
    
    def __init__(self, key: str, suggestion: str | None = None) -> None:
        self.key = key
        self.suggestion = suggestion
        message = f"Missing required configuration: '{key}'"
        if suggestion:
            message += f". {suggestion}"
        super().__init__(message, {"key": key, "suggestion": suggestion})


# ============================================================================
# ANALYSIS ERRORS
# ============================================================================

class AnalysisError(DevWayfinderError):
    """Base class for analysis-related errors."""
    pass


class ParsingError(AnalysisError):
    """Raised when code parsing fails."""
    
    def __init__(self, path: Path, language: str | None, reason: str) -> None:
        self.path = path
        self.language = language
        self.reason = reason
        lang_str = f" as {language}" if language else ""
        super().__init__(
            f"Failed to parse '{path}'{lang_str}: {reason}",
            {"path": str(path), "language": language, "reason": reason}
        )


class UnsupportedLanguageError(AnalysisError):
    """Raised when a language has no available analyzer."""
    
    def __init__(self, language: str, available: list[str]) -> None:
        self.language = language
        self.available = available
        super().__init__(
            f"Unsupported language: '{language}'. Available: {', '.join(available)}",
            {"language": language, "available": available}
        )


class FileAccessError(AnalysisError):
    """Raised when a file cannot be accessed."""
    
    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(
            f"Cannot access file '{path}': {reason}",
            {"path": str(path), "reason": reason}
        )


# ============================================================================
# PROVIDER ERRORS
# ============================================================================

class ProviderError(DevWayfinderError):
    """Base class for LLM provider errors."""
    pass


class ModelUnavailableError(ProviderError):
    """Raised when an LLM model is not accessible."""
    
    def __init__(
        self, 
        provider: str, 
        model: str | None = None,
        fallback_used: bool = False
    ) -> None:
        self.provider = provider
        self.model = model
        self.fallback_used = fallback_used
        model_str = f" ({model})" if model else ""
        fallback_str = " (fallback used)" if fallback_used else ""
        super().__init__(
            f"Model provider '{provider}'{model_str} unavailable{fallback_str}",
            {"provider": provider, "model": model, "fallback_used": fallback_used}
        )


class ConnectionError(ProviderError):
    """Raised when connection to provider fails."""
    
    def __init__(self, provider: str, url: str, reason: str) -> None:
        self.provider = provider
        self.url = url
        self.reason = reason
        super().__init__(
            f"Connection to '{provider}' at {url} failed: {reason}",
            {"provider": provider, "url": url, "reason": reason}
        )


class RateLimitError(ProviderError):
    """Raised when provider rate limit is exceeded."""
    
    def __init__(self, provider: str, retry_after: float | None = None) -> None:
        self.provider = provider
        self.retry_after = retry_after
        retry_str = f" (retry after {retry_after}s)" if retry_after else ""
        super().__init__(
            f"Rate limit exceeded for '{provider}'{retry_str}",
            {"provider": provider, "retry_after": retry_after}
        )


# ============================================================================
# GENERATION ERRORS
# ============================================================================

class GenerationError(DevWayfinderError):
    """Base class for guide generation errors."""
    pass


class TemplateError(GenerationError):
    """Raised when template rendering fails."""
    
    def __init__(self, template_name: str, reason: str) -> None:
        self.template_name = template_name
        self.reason = reason
        super().__init__(
            f"Template '{template_name}' rendering failed: {reason}",
            {"template_name": template_name, "reason": reason}
        )


class OutputError(GenerationError):
    """Raised when output writing fails."""
    
    def __init__(self, output_path: Path, reason: str) -> None:
        self.output_path = output_path
        self.reason = reason
        super().__init__(
            f"Failed to write output to '{output_path}': {reason}",
            {"output_path": str(output_path), "reason": reason}
        )
