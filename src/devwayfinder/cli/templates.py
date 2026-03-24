"""Configuration templates for project initialization.

Provides template configurations for different project types
and languages, stored in `.devwayfinder/` directory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# Default configuration template
DEFAULT_CONFIG_YAML = """\
# DevWayfinder Configuration
# Place this file at .devwayfinder/config.yaml in your project root

# =============================================================================
# Analysis Settings
# =============================================================================
analysis:
  # Patterns to exclude from analysis (glob patterns)
  exclude_patterns:
    - "__pycache__"
    - ".git"
    - ".venv"
    - "venv"
    - "node_modules"
    - "*.egg-info"
    - "dist"
    - "build"
    - ".tox"
    - ".pytest_cache"
    - ".mypy_cache"
    - "*.pyc"
    - "*.pyo"

  # Include hidden files/directories (starting with .)
  include_hidden: false

  # Maximum file size to analyze (in bytes, 0 = no limit)
  max_file_size: 1048576  # 1MB

# =============================================================================
# LLM Provider Settings
# =============================================================================
model:
  # Provider type: openai_compat, ollama, openai, heuristic
  provider: openai_compat

  # Model name (provider-specific, null = provider default)
  model_name: null

  # API base URL (for openai_compat/ollama providers)
  base_url: http://127.0.0.1:5000/v1

  # API key (can also be set via DEVWAYFINDER_API_KEY env var)
  # api_key: sk-xxx

  # Request timeout in seconds
  timeout: 120

  # Maximum tokens for generation
  max_tokens: 512

# =============================================================================
# Output Settings
# =============================================================================
output:
  # Include Mermaid dependency diagram
  include_mermaid: true

  # Maximum modules to show in dependency graph
  max_modules_in_graph: 50

  # Include complexity metrics in output
  include_metrics: true

  # Include file listing
  include_file_list: true

# =============================================================================
# Caching Settings
# =============================================================================
cache:
  # Enable analysis result caching
  enabled: true

  # Cache directory (relative to .devwayfinder/)
  directory: cache

  # Time-to-live for cache entries in seconds (0 = no expiry)
  ttl: 86400  # 24 hours

# =============================================================================
# Start Here Recommendations
# =============================================================================
recommendations:
  # Maximum number of starting point recommendations
  max_recommendations: 5

  # Scoring weights (0-1, must sum to 1)
  weights:
    entry_point: 0.25
    connectivity: 0.20
    change_frequency: 0.20
    complexity: 0.15
    documentation: 0.20
"""


PYTHON_CONFIG_YAML = """\
# DevWayfinder Configuration for Python Projects

analysis:
  exclude_patterns:
    - "__pycache__"
    - ".git"
    - ".venv"
    - "venv"
    - "*.egg-info"
    - "dist"
    - "build"
    - ".tox"
    - ".pytest_cache"
    - ".mypy_cache"
    - "*.pyc"
    - "*.pyo"
    - ".coverage"
    - "htmlcov"

model:
  provider: openai_compat
  base_url: http://127.0.0.1:5000/v1
  timeout: 120
  max_tokens: 512

output:
  include_mermaid: true
  include_metrics: true

cache:
  enabled: true
  ttl: 86400
"""


JAVASCRIPT_CONFIG_YAML = """\
# DevWayfinder Configuration for JavaScript/TypeScript Projects

analysis:
  exclude_patterns:
    - "node_modules"
    - ".git"
    - "dist"
    - "build"
    - "coverage"
    - ".next"
    - ".nuxt"
    - ".cache"
    - "*.min.js"
    - "*.bundle.js"

model:
  provider: openai_compat
  base_url: http://127.0.0.1:5000/v1
  timeout: 120
  max_tokens: 512

output:
  include_mermaid: true
  include_metrics: true

cache:
  enabled: true
  ttl: 86400
"""


JAVA_CONFIG_YAML = """\
# DevWayfinder Configuration for Java Projects

analysis:
  exclude_patterns:
    - ".git"
    - "target"
    - "build"
    - ".gradle"
    - ".idea"
    - "*.class"
    - "*.jar"
    - "*.war"
    - "out"

model:
  provider: openai_compat
  base_url: http://127.0.0.1:5000/v1
  timeout: 120
  max_tokens: 512

output:
  include_mermaid: true
  include_metrics: true

cache:
  enabled: true
  ttl: 86400
"""


RUST_CONFIG_YAML = """\
# DevWayfinder Configuration for Rust Projects

analysis:
  exclude_patterns:
    - ".git"
    - "target"
    - "*.rlib"
    - "*.rmeta"

model:
  provider: openai_compat
  base_url: http://127.0.0.1:5000/v1
  timeout: 120
  max_tokens: 512

output:
  include_mermaid: true
  include_metrics: true

cache:
  enabled: true
  ttl: 86400
"""


GO_CONFIG_YAML = """\
# DevWayfinder Configuration for Go Projects

analysis:
  exclude_patterns:
    - ".git"
    - "vendor"
    - "bin"
    - "*.exe"
    - "*.test"

model:
  provider: openai_compat
  base_url: http://127.0.0.1:5000/v1
  timeout: 120
  max_tokens: 512

output:
  include_mermaid: true
  include_metrics: true

cache:
  enabled: true
  ttl: 86400
"""


GITIGNORE_TEMPLATE = """\
# DevWayfinder cache
cache/
*.cache
"""


@dataclass
class ConfigTemplate:
    """A configuration template."""

    name: str
    description: str
    config_content: str
    file_indicators: list[str] = field(default_factory=list)

    def matches_project(self, project_path: Path) -> bool:
        """Check if this template matches the project."""
        return any((project_path / indicator).exists() for indicator in self.file_indicators)


# Available templates
TEMPLATES: dict[str, ConfigTemplate] = {
    "default": ConfigTemplate(
        name="default",
        description="Universal default configuration",
        config_content=DEFAULT_CONFIG_YAML,
        file_indicators=[],
    ),
    "python": ConfigTemplate(
        name="python",
        description="Python project configuration",
        config_content=PYTHON_CONFIG_YAML,
        file_indicators=["pyproject.toml", "setup.py", "requirements.txt", "Pipfile"],
    ),
    "javascript": ConfigTemplate(
        name="javascript",
        description="JavaScript/TypeScript project configuration",
        config_content=JAVASCRIPT_CONFIG_YAML,
        file_indicators=["package.json", "tsconfig.json"],
    ),
    "java": ConfigTemplate(
        name="java",
        description="Java project configuration",
        config_content=JAVA_CONFIG_YAML,
        file_indicators=["pom.xml", "build.gradle", "build.gradle.kts"],
    ),
    "rust": ConfigTemplate(
        name="rust",
        description="Rust project configuration",
        config_content=RUST_CONFIG_YAML,
        file_indicators=["Cargo.toml"],
    ),
    "go": ConfigTemplate(
        name="go",
        description="Go project configuration",
        config_content=GO_CONFIG_YAML,
        file_indicators=["go.mod"],
    ),
}


def detect_project_type(project_path: Path) -> str:
    """Detect project type based on indicator files.

    Args:
        project_path: Path to project root

    Returns:
        Template name that best matches the project
    """
    # Check each template (except default) in order
    for name, template in TEMPLATES.items():
        if name == "default":
            continue
        if template.matches_project(project_path):
            return name

    return "default"


def get_template(template_name: str) -> ConfigTemplate:
    """Get a configuration template by name.

    Args:
        template_name: Name of the template

    Returns:
        ConfigTemplate instance

    Raises:
        ValueError: If template doesn't exist
    """
    if template_name not in TEMPLATES:
        available = ", ".join(TEMPLATES.keys())
        msg = f"Unknown template '{template_name}'. Available: {available}"
        raise ValueError(msg)

    return TEMPLATES[template_name]


def initialize_config(
    project_path: Path,
    template_name: str | None = None,
    *,
    force: bool = False,
) -> tuple[Path, str]:
    """Initialize DevWayfinder configuration for a project.

    Creates `.devwayfinder/` directory with config.yaml and .gitignore.

    Args:
        project_path: Path to project root
        template_name: Template to use (auto-detected if None)
        force: Overwrite existing configuration

    Returns:
        Tuple of (config_path, template_used)

    Raises:
        FileExistsError: If config exists and force=False
    """
    devwayfinder_dir = project_path / ".devwayfinder"
    config_path = devwayfinder_dir / "config.yaml"
    gitignore_path = devwayfinder_dir / ".gitignore"

    # Check existing
    if config_path.exists() and not force:
        msg = f"Configuration already exists at {config_path}"
        raise FileExistsError(msg)

    # Auto-detect template if not specified
    if template_name is None:
        template_name = detect_project_type(project_path)

    template = get_template(template_name)

    # Create directory
    devwayfinder_dir.mkdir(parents=True, exist_ok=True)

    # Write config
    config_path.write_text(template.config_content, encoding="utf-8")

    # Write .gitignore
    gitignore_path.write_text(GITIGNORE_TEMPLATE, encoding="utf-8")

    return config_path, template_name


def available_templates() -> list[str]:
    """Get list of available template names."""
    return list(TEMPLATES.keys())
