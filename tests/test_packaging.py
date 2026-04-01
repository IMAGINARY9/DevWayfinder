"""Packaging verification tests for MVP 3.2."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

import pytest


def test_pyproject_metadata_contains_release_fields() -> None:
    """Pyproject should include metadata required for distribution."""
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    project = data["project"]
    assert project["name"] == "devwayfinder"
    assert isinstance(project["version"], str)
    assert project["description"]
    assert project["readme"] == "README.md"
    assert "classifiers" in project
    assert any("Development Status" in classifier for classifier in project["classifiers"])
    assert "scripts" in project
    assert "devwayfinder" in project["scripts"]
    assert project["scripts"]["devwayfinder"] == "devwayfinder.__main__:main"


@pytest.mark.slow
def test_build_distributions_produce_installable_artifacts(tmp_path: Path) -> None:
    """Build sdist/wheel and validate key packaging metadata in artifacts."""
    if importlib.util.find_spec("build") is None:
        pytest.skip("build module is not installed; skipping distribution build test")

    repo_root = Path(__file__).resolve().parents[1]
    dist_dir = tmp_path / "dist"

    subprocess.run(
        [sys.executable, "-m", "build", "--sdist", "--wheel", "--outdir", str(dist_dir)],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    wheels = sorted(dist_dir.glob("devwayfinder-*.whl"))
    sdists = sorted(dist_dir.glob("devwayfinder-*.tar.gz"))

    assert wheels, "Wheel artifact was not produced"
    assert sdists, "Source distribution artifact was not produced"

    with zipfile.ZipFile(wheels[0]) as wheel_zip:
        names = wheel_zip.namelist()
        metadata_files = [name for name in names if name.endswith("METADATA")]
        entry_points = [name for name in names if name.endswith("entry_points.txt")]

        assert metadata_files, "Wheel METADATA file is missing"
        assert entry_points, "Wheel entry_points.txt is missing"

        entry_point_text = wheel_zip.read(entry_points[0]).decode("utf-8")
        assert "devwayfinder" in entry_point_text
        assert "devwayfinder.__main__:main" in entry_point_text
