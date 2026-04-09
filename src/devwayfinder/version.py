"""Version helpers for DevWayfinder.

Keeps runtime version reporting aligned with packaging metadata.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def _read_pyproject_version() -> str | None:
    """Best-effort fallback for source checkouts that are not installed."""
    try:
        import tomllib

        pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        project = data.get("project", {})
        project_version = project.get("version")
        if isinstance(project_version, str) and project_version.strip():
            return project_version.strip()
    except (OSError, ValueError, TypeError):
        return None

    return None


def get_version() -> str:
    """Return the current package version from a single source of truth."""
    local_version = _read_pyproject_version()
    if local_version:
        return local_version

    try:
        return version("devwayfinder")
    except PackageNotFoundError:
        return "0.0.0"
