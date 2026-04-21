"""Progress Components - Progress indicators and displays."""

from __future__ import annotations
from textual.widget import Widget
from textual.reactive import reactive
from rich.text import Text


class SpinnerProgress(Widget):
    """Spinner progress indicator."""

    DEFAULT_CSS = """
    SpinnerProgress {
        height: 1;
        width: 15;
    }
    """

    status: reactive[str] = reactive("running")
    message: reactive[str] = reactive("")

    SPINNERS = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def render(self) -> Text:
        """Render spinner."""
        if self.status == "running":
            spinner_char = self.SPINNERS[0]
            return Text.from_markup(f"[cyan]{spinner_char}[/] {self.message}")
        elif self.status == "complete":
            return Text.from_markup(f"[green]✓[/] {self.message}")
        elif self.status == "error":
            return Text.from_markup(f"[red]✗[/] {self.message}")
        return Text(self.message)


class BarProgress(Widget):
    """Bar progress indicator."""

    DEFAULT_CSS = """
    BarProgress {
        height: 1;
        width: 40;
    }
    """

    progress: reactive[int] = reactive(0)
    total: reactive[int] = reactive(100)
    show_percent: reactive[bool] = reactive(True)

    def render(self) -> Text:
        """Render progress bar."""
        percent = int(self.progress / self.total * 100) if self.total > 0 else 0
        bar_width = 30
        filled = int(bar_width * percent / 100)

        bar = "█" * filled + "░" * (bar_width - filled)
        color = "green" if percent < 80 else "yellow" if percent < 95 else "red"

        if self.show_percent:
            return Text.from_markup(f"[{color}]{bar}[/] {percent}%")
        return Text.from_markup(f"[{color}]{bar}[/]")


class MultiProgress(Widget):
    """Multi-item progress display."""

    DEFAULT_CSS = """
    MultiProgress {
        height: auto;
        padding: 1;
    }
    """

    items: reactive[list] = reactive([])

    def render(self) -> Text:
        """Render multi progress."""
        lines = []
        for item in self.items:
            name = item.get("name", "")
            progress = item.get("progress", 0)
            status = item.get("status", "running")

            if status == "complete":
                lines.append(f"[green]✓ {name}[/]")
            elif status == "running":
                lines.append(f"[yellow]⏳ {name} ({progress}%)[/]")
            elif status == "error":
                lines.append(f"[red]✗ {name}[/]")

        return Text.from_markup("\n".join(lines) if lines else "[dim]No items[/]")


class CircularProgress(Widget):
    """Circular progress indicator."""

    DEFAULT_CSS = """
    CircularProgress {
        height: 3;
        width: 5;
    }
    """

    progress: reactive[int] = reactive(0)
    size: reactive[int] = reactive(5)

    def render(self) -> Text:
        """Render circular progress."""
        percent = self.progress
        segments = [
            ("◜", "quarter"),
            ("◠", "half"),
            ("◝", "quarter"),
            ("◞", "half"),
            ("◡", "quarter"),
            ("◟", "half"),
        ]

        # Simplified circular progress
        filled_segments = int(self.size * percent / 100)
        display = "".join(
            segments[i][0] if i < filled_segments else " "
            for i in range(min(6, self.size))
        )

        color = "cyan" if percent < 50 else "yellow" if percent < 80 else "green"

        return Text.from_markup(f"[{color}]{display}[/] {percent}%")


class StepProgress(Widget):
    """Step-by-step progress display."""

    DEFAULT_CSS = """
    StepProgress {
        height: auto;
        padding: 1;
    }
    """

    steps: reactive[list] = reactive([])
    current_step: reactive[int] = reactive(0)

    def render(self) -> Text:
        """Render step progress."""
        lines = []
        for i, step in enumerate(self.steps):
            name = step.get("name", "")
            step.get("status", "pending")

            if i < self.current_step:
                lines.append(f"[green]✓ {name}[/]")
            elif i == self.current_step:
                lines.append(f"[cyan]► {name}[/]")
            else:
                lines.append(f"[dim]○ {name}[/]")

        return Text.from_markup("\n".join(lines))


class AgentProgress(Widget):
    """Agent execution progress display."""

    DEFAULT_CSS = """
    AgentProgress {
        height: auto;
        padding: 1;
        background: $surface-darken-2;
    }
    """

    agent_name: reactive[str] = reactive("")
    task: reactive[str] = reactive("")
    status: reactive[str] = reactive("idle")
    tokens_used: reactive[int] = reactive(0)
    duration_ms: reactive[int] = reactive(0)

    def render(self) -> Text:
        """Render agent progress."""
        status_icons = {
            "idle": "[dim]○[/]",
            "running": "[yellow]⏳[/]",
            "complete": "[green]✓[/]",
            "error": "[red]✗[/]",
        }

        icon = status_icons.get(self.status, "[dim]○[/]")

        lines = [
            f"{icon} [bold]{self.agent_name}[/]",
            f"[dim]Task: {self.task}[/]",
        ]

        if self.status != "idle":
            lines.append(f"[dim]Tokens: {self.tokens_used}, Duration: {self.duration_ms}ms[/]")

        return Text.from_markup("\n".join(lines))


class TaskProgress(Widget):
    """Task execution progress display."""

    DEFAULT_CSS = """
    TaskProgress {
        height: auto;
        padding: 1;
    }
    """

    task_id: reactive[str] = reactive("")
    task_name: reactive[str] = reactive("")
    progress: reactive[int] = reactive(0)
    subtasks: reactive[list] = reactive([])

    def render(self) -> Text:
        """Render task progress."""
        lines = [
            f"[bold]Task: {self.task_name}[/] ({self.task_id})",
            f"[cyan]Progress: {self.progress}%[/]",
        ]

        if self.subtasks:
            lines.append("[dim]Subtasks:[/]")
            for subtask in self.subtasks[:5]:
                status = subtask.get("status", "pending")
                name = subtask.get("name", "")
                status_icon = "✓" if status == "complete" else "⏳" if status == "running" else "○"
                lines.append(f"  [{status}] {status_icon} {name}[/]")

        return Text.from_markup("\n".join(lines))


__all__ = [
    "SpinnerProgress",
    "BarProgress",
    "MultiProgress",
    "CircularProgress",
    "StepProgress",
    "AgentProgress",
    "TaskProgress",
]
