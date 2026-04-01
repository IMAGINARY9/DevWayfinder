"""Deterministic benchmark fixture generation.

Fixtures are synthetic Python projects sized for repeatable benchmarking.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import Path

FixtureSize = Literal["small", "medium", "large"]


@dataclass(frozen=True)
class FixtureDefinition:
    """Definition of a synthetic benchmark fixture."""

    size: FixtureSize
    module_count: int
    package_count: int


FIXTURE_DEFINITIONS: dict[FixtureSize, FixtureDefinition] = {
    "small": FixtureDefinition(size="small", module_count=10, package_count=2),
    "medium": FixtureDefinition(size="medium", module_count=100, package_count=8),
    "large": FixtureDefinition(size="large", module_count=1000, package_count=20),
}


def create_fixture(root_dir: Path, size: FixtureSize, *, force: bool = False) -> Path:
    """Create a synthetic project fixture of the requested size.

    Args:
        root_dir: Directory where fixture directories are created
        size: Fixture size key
        force: Recreate fixture if it already exists

    Returns:
        Path to the fixture project directory
    """
    definition = FIXTURE_DEFINITIONS[size]
    fixture_dir = root_dir / size

    if fixture_dir.exists() and force:
        shutil.rmtree(fixture_dir)

    if fixture_dir.exists():
        return fixture_dir

    src_dir = fixture_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    package_dirs: list[Path] = []
    for package_index in range(definition.package_count):
        package_dir = src_dir / f"pkg_{package_index:02d}"
        package_dir.mkdir(parents=True, exist_ok=True)
        (package_dir / "__init__.py").write_text(
            f'"""Synthetic package {package_index}."""\n',
            encoding="utf-8",
        )
        package_dirs.append(package_dir)

    module_paths: list[Path] = []
    for module_index in range(definition.module_count):
        package_dir = package_dirs[module_index % len(package_dirs)]
        module_path = package_dir / f"module_{module_index:04d}.py"
        module_paths.append(module_path)

    for module_index, module_path in enumerate(module_paths):
        imports: list[str] = []

        if module_index > 0:
            previous_module = module_paths[module_index - 1]
            previous_import = _to_import_path(previous_module, src_dir)
            imports.append(f"from {previous_import} import fn_{module_index - 1:04d}")

        if module_index >= 5 and module_index % 7 == 0:
            helper_index = module_index - 5
            helper_module = module_paths[helper_index]
            helper_import = _to_import_path(helper_module, src_dir)
            imports.append(f"from {helper_import} import fn_{helper_index:04d}")

        module_lines = [f'"""Synthetic benchmark module {module_index}."""', ""]
        module_lines.extend(imports)
        if imports:
            module_lines.append("")
        module_lines.extend(
            [
                f"def fn_{module_index:04d}() -> int:",
                f"    return {module_index}",
                "",
            ]
        )
        module_path.write_text("\n".join(module_lines), encoding="utf-8")

    entry_imports = [
        f"from {_to_import_path(module_paths[index], src_dir)} import fn_{index:04d}"
        for index in range(min(3, len(module_paths)))
    ]
    (src_dir / "main.py").write_text(
        "\n".join(
            [
                '"""Synthetic benchmark entry point."""',
                "",
                *entry_imports,
                "",
                "def main() -> int:",
                "    total = 0",
                *[f"    total += fn_{index:04d}()" for index in range(min(3, len(module_paths)))],
                "    return total",
                "",
                'if __name__ == "__main__":',
                "    raise SystemExit(main())",
                "",
            ]
        ),
        encoding="utf-8",
    )

    (fixture_dir / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                f'name = "benchmark-{size}"',
                'version = "0.0.0"',
                'description = "Synthetic benchmark fixture"',
                "",
            ]
        ),
        encoding="utf-8",
    )

    (fixture_dir / "README.md").write_text(
        "\n".join(
            [
                f"# Benchmark Fixture ({size})",
                "",
                f"Generated module count: {definition.module_count}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    metadata = {
        "size": size,
        "module_count": definition.module_count,
        "package_count": definition.package_count,
    }
    (fixture_dir / "fixture.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    return fixture_dir


def create_fixtures(
    root_dir: Path, sizes: list[FixtureSize], *, force: bool = False
) -> dict[str, Path]:
    """Create multiple fixtures and return their paths."""
    return {size: create_fixture(root_dir, size, force=force) for size in sizes}


def _to_import_path(module_path: Path, src_root: Path) -> str:
    """Convert a module path into a Python import path."""
    rel_parts = list(module_path.relative_to(src_root).parts)
    rel_parts[-1] = rel_parts[-1].removesuffix(".py")
    return ".".join(rel_parts)
