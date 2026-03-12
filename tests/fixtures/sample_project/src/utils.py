"""Utility functions for formatting."""

from typing import Any


def format_output(data: Any) -> str:
    """
    Format data for display.

    Args:
        data: Data to format

    Returns:
        Formatted string representation
    """
    if hasattr(data, "content"):
        return f"Result: {data.content}"
    return str(data)


def truncate(text: str, max_length: int = 100) -> str:
    """
    Truncate text to maximum length.

    Args:
        text: Input text
        max_length: Maximum output length

    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
