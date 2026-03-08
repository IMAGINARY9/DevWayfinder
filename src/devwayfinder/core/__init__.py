"""Core domain models and interfaces."""

from devwayfinder.core.models import Module, ModuleType, Project
from devwayfinder.core.graph import DependencyGraph
from devwayfinder.core.guide import OnboardingGuide, Section, SectionType
from devwayfinder.core.protocols import Analyzer, ModelProvider, OutputGenerator
from devwayfinder.core.exceptions import (
    DevWayfinderError,
    ConfigurationError,
    AnalysisError,
    ProviderError,
    GenerationError,
)

__all__ = [
    # Models
    "Module",
    "ModuleType",
    "Project",
    "DependencyGraph",
    "OnboardingGuide",
    "Section",
    "SectionType",
    # Protocols
    "Analyzer",
    "ModelProvider",
    "OutputGenerator",
    # Exceptions
    "DevWayfinderError",
    "ConfigurationError",
    "AnalysisError",
    "ProviderError",
    "GenerationError",
]
