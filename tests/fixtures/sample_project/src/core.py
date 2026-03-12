"""Core processing module."""

from dataclasses import dataclass
from typing import Any


@dataclass
class ProcessedData:
    """Container for processed data."""

    content: str
    metadata: dict[str, Any]


def process_data(input_data: str) -> ProcessedData:
    """
    Process the input data and return processed result.

    Args:
        input_data: Raw input string

    Returns:
        ProcessedData with content and metadata
    """
    return ProcessedData(
        content=input_data.upper(),
        metadata={"length": len(input_data), "processed": True},
    )


def validate_data(data: ProcessedData) -> bool:
    """
    Validate processed data.

    Args:
        data: ProcessedData to validate

    Returns:
        True if valid
    """
    return bool(data.content and data.metadata.get("processed"))
