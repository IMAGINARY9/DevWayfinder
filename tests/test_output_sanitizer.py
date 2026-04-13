"""Tests for provider output sanitization."""

from __future__ import annotations

from devwayfinder.summarizers.output_sanitizer import sanitize_summary_text


def test_sanitizer_removes_reasoning_dump() -> None:
    """Reasoning-only payloads should be removed entirely."""
    raw = (
        "Thinking Process:\n"
        "1. Analyze the request\n"
        "2. Task: produce summary\n"
        "3. Constraints: avoid filler"
    )

    cleaned = sanitize_summary_text(raw)
    assert cleaned == ""


def test_sanitizer_extracts_final_summary_section() -> None:
    """Final summary sections should be preserved when present."""
    raw = (
        "Thinking Process:\n"
        "1. Analyze inputs\n\n"
        "Final Summary:\n"
        "This module orchestrates startup and delegates initialization tasks to services."
    )

    cleaned = sanitize_summary_text(raw)
    assert cleaned.startswith("This module orchestrates startup")


def test_sanitizer_deduplicates_paragraphs() -> None:
    """Duplicate paragraphs should collapse to one copy."""
    raw = (
        "The module validates incoming requests and normalizes payloads.\n\n"
        "The module validates incoming requests and normalizes payloads."
    )

    cleaned = sanitize_summary_text(raw)
    assert cleaned.count("validates incoming requests") == 1
