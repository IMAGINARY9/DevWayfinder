"""Sample project for testing DevWayfinder."""

from src.core import process_data
from src.utils import format_output

__version__ = "0.1.0"
__all__ = ["format_output", "main", "process_data"]


def main() -> None:
    """Entry point for the sample project."""
    data = process_data("Hello, World!")
    output = format_output(data)
    print(output)


if __name__ == "__main__":
    main()
