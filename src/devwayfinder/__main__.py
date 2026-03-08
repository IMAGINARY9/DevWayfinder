"""CLI entry point for DevWayfinder."""

import sys


def main() -> int:
    """Main entry point."""
    from devwayfinder.cli.app import app

    app()
    return 0


if __name__ == "__main__":
    sys.exit(main())
