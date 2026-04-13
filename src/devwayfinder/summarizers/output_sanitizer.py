"""Utilities for cleaning provider outputs before they reach reports."""

from __future__ import annotations

import re

_REASONING_MARKERS = (
    "thinking process",
    "analyze the request",
    "task:",
    "constraints:",
    "context:",
    "drafting",
    "system instruction",
    "developer instruction",
)

_FINAL_SECTION_RE = re.compile(
    r"(?im)^\s*(?:#+\s*)?(?:final answer|final summary|summary|answer)\s*:?\s*$"
)

_NUMBERED_STEP_RE = re.compile(r"(?m)^\s*\d+\.\s+(?:\*\*)?[A-Za-z]")


def sanitize_summary_text(text: str) -> str:
    """Remove reasoning traces and duplicate fragments from provider text."""
    cleaned = text.replace("\r\n", "\n").strip()
    if not cleaned:
        return ""

    cleaned = _strip_think_tags(cleaned)
    cleaned = _extract_final_section(cleaned)

    if _looks_like_reasoning_dump(cleaned):
        return ""

    lines: list[str] = []
    for raw_line in cleaned.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            lines.append("")
            continue

        if _is_trace_line(stripped):
            continue

        lines.append(raw_line.rstrip())

    collapsed = _collapse_blank_lines("\n".join(lines)).strip()
    if not collapsed:
        return ""

    return _dedupe_paragraphs(collapsed)


def _strip_think_tags(text: str) -> str:
    """Drop XML-like think tags emitted by some local models."""
    without_tags = re.sub(r"(?is)<think>.*?</think>", "", text)
    return without_tags.strip()


def _extract_final_section(text: str) -> str:
    """Use explicit final-summary markers when they exist."""
    match = _FINAL_SECTION_RE.search(text)
    if not match:
        return text

    tail = text[match.end() :].strip()
    if tail:
        return tail
    return text


def _looks_like_reasoning_dump(text: str) -> bool:
    """Detect chain-of-thought style responses that should not be published."""
    lowered = text.lower()
    marker_hits = sum(1 for marker in _REASONING_MARKERS if marker in lowered)
    numbered_steps = bool(_NUMBERED_STEP_RE.search(text))
    return marker_hits >= 2 and numbered_steps


def _is_trace_line(line: str) -> bool:
    """Detect individual lines that expose internal reasoning/process metadata."""
    lowered = line.lower()
    normalized = re.sub(r"^[>\-*\d\.)\s]+", "", lowered)

    prefixes = (
        "thinking process",
        "analysis:",
        "task:",
        "constraints:",
        "context:",
        "focus:",
        "focus areas:",
        "input:",
        "drafting",
        "quality profile:",
        "context signals:",
        "iterate:",
    )
    if normalized.startswith(prefixes):
        return True

    contains_markers = (
        "analyze the request" in normalized
        or "chain of thought" in normalized
        or "system prompt" in normalized
        or "developer instruction" in normalized
        or "reasoning:" in normalized
    )
    if contains_markers:
        return True

    return bool(normalized.startswith("attempt "))


def _collapse_blank_lines(text: str) -> str:
    """Reduce noisy spacing while preserving paragraph boundaries."""
    return re.sub(r"\n{3,}", "\n\n", text)


def _dedupe_paragraphs(text: str) -> str:
    """Remove repeated paragraphs from model responses."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return ""

    unique: list[str] = []
    seen: set[str] = set()
    for paragraph in paragraphs:
        key = re.sub(r"\s+", " ", paragraph.lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(paragraph)

    return "\n\n".join(unique)
