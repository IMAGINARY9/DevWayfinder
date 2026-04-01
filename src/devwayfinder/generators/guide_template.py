"""Guide template loading and inheritance support.

Templates allow projects to customize section ordering, renaming, and
inclusion/exclusion for generated onboarding guides.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import yaml

from devwayfinder.core.guide import SectionType

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class SectionTemplate:
    """Template configuration for a single guide section."""

    section_type: SectionType
    title: str | None = None
    enabled: bool = True


@dataclass(frozen=True)
class GuideTemplate:
    """Resolved guide template."""

    name: str
    sections: list[SectionTemplate] = field(default_factory=list)


_DEFAULT_TEMPLATE = GuideTemplate(
    name="default",
    sections=[
        SectionTemplate(section_type=SectionType.OVERVIEW, title="Overview"),
        SectionTemplate(section_type=SectionType.ARCHITECTURE, title="Architecture"),
        SectionTemplate(section_type=SectionType.MODULES, title="Modules"),
        SectionTemplate(section_type=SectionType.DEPENDENCIES, title="Dependencies"),
        SectionTemplate(section_type=SectionType.START_HERE, title="Start Here"),
    ],
)

_COMPACT_TEMPLATE = GuideTemplate(
    name="compact",
    sections=[
        SectionTemplate(section_type=SectionType.OVERVIEW, title="Overview"),
        SectionTemplate(section_type=SectionType.MODULES, title="Modules"),
        SectionTemplate(section_type=SectionType.START_HERE, title="Start Here"),
    ],
)

BUILTIN_GUIDE_TEMPLATES: dict[str, GuideTemplate] = {
    _DEFAULT_TEMPLATE.name: _DEFAULT_TEMPLATE,
    _COMPACT_TEMPLATE.name: _COMPACT_TEMPLATE,
}


def load_guide_template(project_path: Path, template_path: Path | None = None) -> GuideTemplate:
    """Load and resolve a guide template for a project.

    Args:
        project_path: Root path of the analyzed project
        template_path: Optional explicit template path. When omitted, this
            function looks for `.devwayfinder/template.yaml` under project root.

    Returns:
        Resolved template. Defaults to built-in `default` when no file exists.

    Raises:
        ValueError: If YAML format or template values are invalid.
    """
    resolved_path = template_path or (project_path / ".devwayfinder" / "template.yaml")

    if not resolved_path.exists():
        return BUILTIN_GUIDE_TEMPLATES["default"]

    try:
        raw = yaml.safe_load(resolved_path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise ValueError(f"Unable to read template file '{resolved_path}': {exc}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in template file '{resolved_path}': {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError("Guide template must be a YAML mapping")

    name = str(raw.get("name", "project-template"))
    extends_name = raw.get("extends", "default")
    if not isinstance(extends_name, str):
        raise ValueError("`extends` must be a string when provided")

    if extends_name not in BUILTIN_GUIDE_TEMPLATES:
        known = ", ".join(sorted(BUILTIN_GUIDE_TEMPLATES.keys()))
        raise ValueError(f"Unknown base template '{extends_name}'. Known templates: {known}")

    base = BUILTIN_GUIDE_TEMPLATES[extends_name]
    overrides = _parse_section_overrides(raw.get("sections", []))
    return _merge_template(base=base, name=name, overrides=overrides)


def _parse_section_overrides(raw_sections: Any) -> list[SectionTemplate]:
    """Parse section overrides from raw YAML nodes."""
    if raw_sections is None:
        return []

    if not isinstance(raw_sections, list):
        raise ValueError("`sections` must be a list")

    parsed: list[SectionTemplate] = []
    for index, node in enumerate(raw_sections):
        if not isinstance(node, dict):
            raise ValueError(f"Section override at index {index} must be a mapping")

        raw_type = node.get("type")
        if not isinstance(raw_type, str):
            raise ValueError(f"Section override at index {index} requires string `type`")

        try:
            section_type = SectionType(raw_type)
        except ValueError as exc:
            valid = ", ".join(member.value for member in SectionType)
            raise ValueError(
                f"Unknown section type '{raw_type}' at index {index}. Valid values: {valid}"
            ) from exc

        raw_title = node.get("title")
        if raw_title is not None and not isinstance(raw_title, str):
            raise ValueError(f"Section override `{raw_type}` has non-string `title`")

        raw_enabled = node.get("enabled", True)
        if not isinstance(raw_enabled, bool):
            raise ValueError(f"Section override `{raw_type}` has non-boolean `enabled`")

        parsed.append(
            SectionTemplate(
                section_type=section_type,
                title=raw_title,
                enabled=raw_enabled,
            )
        )

    return parsed


def _merge_template(
    *,
    base: GuideTemplate,
    name: str,
    overrides: list[SectionTemplate],
) -> GuideTemplate:
    """Merge section overrides into a base template.

    Explicitly listed sections are reordered according to override order.
    Non-listed base sections are appended in base order.
    """
    merged_by_type: dict[SectionType, SectionTemplate] = {
        section.section_type: section for section in base.sections
    }

    explicit_order: list[SectionType] = []
    for override in overrides:
        base_section = merged_by_type.get(override.section_type)

        if base_section is None:
            merged_section = override
        else:
            merged_section = SectionTemplate(
                section_type=override.section_type,
                title=override.title if override.title is not None else base_section.title,
                enabled=override.enabled,
            )

        merged_by_type[override.section_type] = merged_section
        if override.section_type not in explicit_order:
            explicit_order.append(override.section_type)

    ordered_types = explicit_order + [
        section.section_type
        for section in base.sections
        if section.section_type not in explicit_order
    ]

    resolved_sections = [merged_by_type[section_type] for section_type in ordered_types]
    return GuideTemplate(name=name, sections=resolved_sections)
