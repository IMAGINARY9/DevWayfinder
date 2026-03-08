"""Pytest configuration and shared fixtures for DevWayfinder tests."""

from pathlib import Path

import pytest


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a temporary project directory with sample files."""
    project = tmp_path / "sample_project"
    project.mkdir()

    # Create a simple Python project structure
    (project / "src").mkdir()
    (project / "src" / "__init__.py").write_text("")
    (project / "src" / "main.py").write_text('''"""Main entry point."""

from src.utils import helper

def main():
    """Run the application."""
    result = helper()
    print(result)

if __name__ == "__main__":
    main()
''')
    (project / "src" / "utils.py").write_text('''"""Utility functions."""

def helper() -> str:
    """A helper function."""
    return "Hello, World!"
''')

    # Create README
    (project / "README.md").write_text("# Sample Project\n\nA sample project for testing.")

    # Create pyproject.toml
    (project / "pyproject.toml").write_text("""[project]
name = "sample-project"
version = "0.1.0"
""")

    return project


@pytest.fixture
def sample_module() -> dict:
    """Create sample module data for testing."""
    return {
        "name": "main.py",
        "path": Path("/project/src/main.py"),
        "module_type": "file",
        "language": "python",
        "imports": ["src.utils"],
        "exports": ["main"],
        "entry_point": True,
    }
