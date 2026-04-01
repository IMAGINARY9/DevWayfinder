"""Tests for guide template customization (MVP 3.1)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from devwayfinder.core.guide import SectionType
from devwayfinder.generators import GenerationConfig, GuideGenerator, load_guide_template

if TYPE_CHECKING:
    from pathlib import Path


def _create_minimal_project(root: Path) -> None:
    """Create a minimal Python project used by template tests."""
    src = root / "src"
    src.mkdir(parents=True)
    (src / "main.py").write_text(
        '"""Entry module."""\n\n'
        "def main() -> None:\n"
        "    pass\n\n"
        'if __name__ == "__main__":\n'
        "    main()\n",
        encoding="utf-8",
    )
    (src / "utils.py").write_text(
        '"""Utilities."""\n\ndef helper() -> str:\n    return "ok"\n',
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text('[project]\nname = "template-test"\n', encoding="utf-8")


def test_load_template_default_when_missing(tmp_path: Path) -> None:
    """Missing template file should resolve to built-in default."""
    _create_minimal_project(tmp_path)

    template = load_guide_template(tmp_path)

    assert [section.section_type for section in template.sections] == [
        SectionType.OVERVIEW,
        SectionType.ARCHITECTURE,
        SectionType.MODULES,
        SectionType.DEPENDENCIES,
        SectionType.START_HERE,
    ]


def test_load_template_reorders_and_excludes_sections(tmp_path: Path) -> None:
    """Project template should support reordering and section exclusion."""
    _create_minimal_project(tmp_path)

    template_file = tmp_path / ".devwayfinder" / "template.yaml"
    template_file.parent.mkdir(parents=True)
    template_file.write_text(
        """
name: custom-order
extends: default
sections:
  - type: start_here
    title: Read This First
  - type: dependencies
    enabled: false
""".strip()
        + "\n",
        encoding="utf-8",
    )

    template = load_guide_template(tmp_path)

    assert template.name == "custom-order"
    assert template.sections[0].section_type == SectionType.START_HERE
    assert template.sections[0].title == "Read This First"
    deps_section = next(s for s in template.sections if s.section_type == SectionType.DEPENDENCIES)
    assert deps_section.enabled is False


def test_load_template_invalid_section_type_raises(tmp_path: Path) -> None:
    """Invalid section types should fail with a clear error."""
    _create_minimal_project(tmp_path)

    template_file = tmp_path / ".devwayfinder" / "template.yaml"
    template_file.parent.mkdir(parents=True)
    template_file.write_text(
        """
extends: default
sections:
  - type: not_a_real_section
""".strip()
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unknown section type"):
        load_guide_template(tmp_path)


@pytest.mark.asyncio
async def test_generator_applies_template_order_titles_and_exclusion(tmp_path: Path) -> None:
    """Guide generation should honor project-level template customization."""
    _create_minimal_project(tmp_path)

    template_file = tmp_path / ".devwayfinder" / "template.yaml"
    template_file.parent.mkdir(parents=True)
    template_file.write_text(
        """
name: custom-render
extends: default
sections:
  - type: start_here
    title: Read This First
  - type: dependencies
    enabled: false
""".strip()
        + "\n",
        encoding="utf-8",
    )

    generator = GuideGenerator(
        project_path=tmp_path,
        config=GenerationConfig(use_llm=False),
    )

    result = await generator.generate()
    section_titles = [section.title for section in result.guide.sections]
    section_types = [section.section_type for section in result.guide.sections]

    assert section_titles[0] == "Read This First"
    assert SectionType.DEPENDENCIES not in section_types


@pytest.mark.asyncio
async def test_generator_supports_explicit_template_path(tmp_path: Path) -> None:
    """Generation config should allow explicit template path overrides."""
    _create_minimal_project(tmp_path)

    custom_template = tmp_path / "custom-template.yaml"
    custom_template.write_text(
        """
name: compact-custom
extends: compact
sections:
  - type: modules
    title: Core Modules
""".strip()
        + "\n",
        encoding="utf-8",
    )

    generator = GuideGenerator(
        project_path=tmp_path,
        config=GenerationConfig(
            use_llm=False,
            template_path=custom_template,
        ),
    )

    result = await generator.generate()
    titles = [section.title for section in result.guide.sections]

    assert "Core Modules" in titles
    assert len(result.guide.sections) == 3
