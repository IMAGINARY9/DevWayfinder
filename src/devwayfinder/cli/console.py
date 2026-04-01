"""Console helpers for CLI output."""

from __future__ import annotations

import sys
from typing import Any, TextIO, cast

from rich.console import Console


class _StdoutProxy:
    """Delegate writes to the active stdout stream."""

    @property
    def encoding(self) -> str:
        return getattr(sys.stdout, "encoding", "utf-8") or "utf-8"

    def write(self, data: str) -> int:
        return sys.stdout.write(data)

    def flush(self) -> None:
        sys.stdout.flush()

    def isatty(self) -> bool:
        return bool(getattr(sys.stdout, "isatty", lambda: False)())

    def __getattr__(self, name: str) -> Any:
        return getattr(sys.stdout, name)


def create_console() -> Console:
    """Create a console configured for Unicode-safe CLI output."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    return Console(file=cast("TextIO", _StdoutProxy()))
