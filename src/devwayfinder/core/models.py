"""Core domain models for DevWayfinder."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ModuleType(str, Enum):
    """Type of code module."""
    
    FILE = "file"
    DIRECTORY = "directory"
    PACKAGE = "package"


class Module(BaseModel):
    """
    Represents a logical unit of code (file, directory, or package).
    
    This is the core data model for analyzed code units.
    """
    
    name: str = Field(description="Module name (filename or package name)")
    path: Path = Field(description="Absolute path to the module")
    module_type: ModuleType = Field(description="Type of module")
    language: str | None = Field(default=None, description="Detected programming language")
    description: str | None = Field(default=None, description="Natural-language description")
    
    # Analysis results
    imports: list[str] = Field(default_factory=list, description="List of imported modules")
    exports: list[str] = Field(default_factory=list, description="List of exported symbols")
    entry_point: bool = Field(default=False, description="Whether this is an entry point")
    
    # Metrics (optional, computed in MVP 2)
    loc: int | None = Field(default=None, description="Lines of code")
    complexity: float | None = Field(default=None, description="Cyclomatic complexity")
    
    # Git metadata (optional, computed in MVP 2)
    last_modified: datetime | None = Field(default=None, description="Last modification date")
    contributors: list[str] = Field(default_factory=list, description="List of contributors")
    change_frequency: float | None = Field(default=None, description="Changes per month")
    
    model_config = {"frozen": False, "extra": "allow"}
    
    def __hash__(self) -> int:
        """Hash by path for set/dict usage."""
        return hash(self.path)
    
    def __eq__(self, other: object) -> bool:
        """Compare by path."""
        if not isinstance(other, Module):
            return NotImplemented
        return self.path == other.path


class Project(BaseModel):
    """
    Represents an analyzed codebase.
    
    Contains all modules, dependency information, and metadata.
    """
    
    name: str = Field(description="Project name")
    root_path: Path = Field(description="Root directory path")
    
    # Detected configuration
    build_system: str | None = Field(default=None, description="Detected build system")
    package_manager: str | None = Field(default=None, description="Detected package manager")
    primary_language: str | None = Field(default=None, description="Primary programming language")
    
    # Documentation content
    readme_content: str | None = Field(default=None, description="README file content")
    contributing_content: str | None = Field(default=None, description="CONTRIBUTING file content")
    
    # Analysis results
    modules: dict[str, Module] = Field(
        default_factory=dict,
        description="Map of path string to Module"
    )
    
    # Metadata
    analyzed_at: datetime = Field(default_factory=datetime.now)
    analysis_config: dict[str, Any] = Field(default_factory=dict)
    
    model_config = {"frozen": False, "extra": "allow"}
    
    @property
    def entry_points(self) -> list[Module]:
        """Get all entry point modules."""
        return [m for m in self.modules.values() if m.entry_point]
    
    @property
    def module_count(self) -> int:
        """Total number of analyzed modules."""
        return len(self.modules)
