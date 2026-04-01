"""Progress tracking for CLI operations.

Provides rich progress display with per-phase status indicators.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from devwayfinder.cli.console import create_console

if TYPE_CHECKING:
    from types import TracebackType


class PhaseStatus(StrEnum):
    """Status of a generation phase."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Phase:
    """A single phase in the generation pipeline."""

    name: str
    description: str
    status: PhaseStatus = PhaseStatus.PENDING
    progress: str = ""
    duration_seconds: float | None = None
    start_time: float | None = None

    @property
    def status_icon(self) -> str:
        """Get icon for current status."""
        if self.status == PhaseStatus.IN_PROGRESS:
            # Animated spinner frame; Live refresh makes this visibly rotate.
            frames = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
            idx = int(time.perf_counter() * 10) % len(frames)
            return frames[idx]

        icons = {
            PhaseStatus.PENDING: "○",
            PhaseStatus.COMPLETE: "●",
            PhaseStatus.FAILED: "✗",
            PhaseStatus.SKIPPED: "◌",
        }
        return icons.get(self.status, "○")

    @property
    def status_color(self) -> str:
        """Get color for current status."""
        colors = {
            PhaseStatus.PENDING: "dim",
            PhaseStatus.IN_PROGRESS: "cyan",
            PhaseStatus.COMPLETE: "green",
            PhaseStatus.FAILED: "red",
            PhaseStatus.SKIPPED: "yellow",
        }
        return colors.get(self.status, "dim")


@dataclass
class ProgressTracker:
    """Tracks progress across multiple phases.

    Usage:
        tracker = ProgressTracker()
        tracker.start_phase("analysis")
        # ... do work ...
        tracker.update_progress("analysis", "50 files processed")
        tracker.complete_phase("analysis")
    """

    phases: dict[str, Phase] = field(default_factory=dict)
    console: Console = field(default_factory=Console)
    _live: Live | None = field(default=None, repr=False)

    def add_phase(self, key: str, name: str, description: str = "") -> None:
        """Add a phase to track.

        Args:
            key: Unique identifier for the phase
            name: Display name for the phase
            description: Optional description
        """
        self.phases[key] = Phase(
            name=name,
            description=description,
        )

    def start_phase(self, key: str, progress: str = "") -> None:
        """Mark a phase as started.

        Args:
            key: Phase identifier
            progress: Optional progress text
        """
        if key in self.phases:
            phase = self.phases[key]
            phase.status = PhaseStatus.IN_PROGRESS
            phase.progress = progress
            phase.start_time = time.perf_counter()
            self._render()

    def update_progress(self, key: str, progress: str) -> None:
        """Update progress text for a phase.

        Args:
            key: Phase identifier
            progress: Progress text to display
        """
        if key in self.phases:
            self.phases[key].progress = progress
            self._render()

    def complete_phase(self, key: str, progress: str = "") -> None:
        """Mark a phase as complete.

        Args:
            key: Phase identifier
            progress: Final progress text
        """
        if key in self.phases:
            phase = self.phases[key]
            phase.status = PhaseStatus.COMPLETE
            if progress:
                phase.progress = progress
            if phase.start_time:
                phase.duration_seconds = time.perf_counter() - phase.start_time
            self._render()

    def fail_phase(self, key: str, error: str = "") -> None:
        """Mark a phase as failed.

        Args:
            key: Phase identifier
            error: Error message
        """
        if key in self.phases:
            phase = self.phases[key]
            phase.status = PhaseStatus.FAILED
            phase.progress = error or "Failed"
            if phase.start_time:
                phase.duration_seconds = time.perf_counter() - phase.start_time
            self._render()

    def skip_phase(self, key: str, reason: str = "") -> None:
        """Mark a phase as skipped.

        Args:
            key: Phase identifier
            reason: Reason for skipping
        """
        if key in self.phases:
            phase = self.phases[key]
            phase.status = PhaseStatus.SKIPPED
            phase.progress = reason or "Skipped"
            self._render()

    def _build_display(self) -> Panel:
        """Build the progress display panel."""
        table = Table(
            show_header=False,
            show_edge=False,
            box=None,
            padding=(0, 1),
        )
        table.add_column("Status", width=3)
        table.add_column("Phase", min_width=20)
        table.add_column("Progress", min_width=25)
        table.add_column("Time", width=8, justify="right")

        for phase in self.phases.values():
            status_text = Text(phase.status_icon, style=phase.status_color)

            name_style = phase.status_color
            if phase.status == PhaseStatus.IN_PROGRESS:
                name_style = "bold cyan"

            name_text = Text(phase.name, style=name_style)

            progress_text = Text(phase.progress, style="dim")

            duration = ""
            if phase.duration_seconds is not None:
                duration = f"{phase.duration_seconds:.1f}s"
            elif phase.status == PhaseStatus.IN_PROGRESS and phase.start_time:
                elapsed = time.perf_counter() - phase.start_time
                duration = f"{elapsed:.1f}s"

            time_text = Text(duration, style="dim")

            table.add_row(status_text, name_text, progress_text, time_text)

        return Panel(
            table,
            title="[bold blue]Generation Progress[/bold blue]",
            border_style="blue",
            padding=(0, 1),
        )

    def _render(self) -> None:
        """Render the progress display."""
        if self._live:
            self._live.update(self._build_display())

    def __enter__(self) -> ProgressTracker:
        """Start live display."""
        self._live = Live(
            self._build_display(),
            console=self.console,
            refresh_per_second=4,
            transient=True,
        )
        self._live.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Stop live display and show final state."""
        if self._live:
            # Show final state before closing
            self._live.update(self._build_display())
            self._live.__exit__(exc_type, exc_val, exc_tb)
            # Print final summary
            self.console.print(self._build_display())


def create_generation_tracker(console: Console | None = None) -> ProgressTracker:
    """Create a progress tracker for guide generation.

    Pre-configured with standard generation phases.

    Args:
        console: Optional Rich console to use

    Returns:
        ProgressTracker configured for generation
    """
    tracker = ProgressTracker(console=console or create_console())

    tracker.add_phase(
        "analysis",
        "Analyzing Code",
        "Scanning project structure and extracting imports",
    )
    tracker.add_phase(
        "graph",
        "Building Graph",
        "Constructing dependency graph",
    )
    tracker.add_phase(
        "metrics",
        "Computing Metrics",
        "Calculating complexity metrics",
    )
    tracker.add_phase(
        "summarization",
        "Summarizing",
        "Generating module descriptions",
    )
    tracker.add_phase(
        "assembly",
        "Assembling Guide",
        "Creating onboarding document",
    )

    return tracker
