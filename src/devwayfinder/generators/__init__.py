"""Generators module for DevWayfinder.

This module provides output generation capabilities, transforming
OnboardingGuide models into various output formats.
"""

from devwayfinder.generators.guide_generator import (
    GenerationConfig,
    GenerationResult,
    GuideGenerator,
    MarkdownGenerator,
    ProgressCallback,
)
from devwayfinder.generators.guide_template import (
    BUILTIN_GUIDE_TEMPLATES,
    GuideTemplate,
    SectionTemplate,
    load_guide_template,
)
from devwayfinder.generators.mermaid import (
    DiagramDirection,
    DiagramEdge,
    DiagramNode,
    MermaidConfig,
    MermaidDiagram,
    MermaidGenerator,
    NodeShape,
    generate_mermaid_diagram,
    generate_mermaid_markdown,
)

__all__ = [
    "BUILTIN_GUIDE_TEMPLATES",
    "DiagramDirection",
    "DiagramEdge",
    "DiagramNode",
    "GenerationConfig",
    "GenerationResult",
    "GuideGenerator",
    "GuideTemplate",
    "MarkdownGenerator",
    "MermaidConfig",
    "MermaidDiagram",
    "MermaidGenerator",
    "NodeShape",
    "ProgressCallback",
    "SectionTemplate",
    "generate_mermaid_diagram",
    "generate_mermaid_markdown",
    "load_guide_template",
]
