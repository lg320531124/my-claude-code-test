"""Update Dialog - Update notification and progress."""

from __future__ import annotations
from dataclasses import dataclass
from textual.widget import Widget
from textual.widgets import Static, Button, ProgressBar
from textual.reactive import reactive
from textual.message import Message
from textual.screen import ModalScreen
from textual.binding import Binding
from textual.containers import Container
from rich.text import Text


@dataclass
class UpdateInfo:
    """Update information."""
    current_version: str
    new_version: str
    release_date: str
    changelog: list  # list of changelog items
    download_url: str
    size_mb: float
    critical: bool  # security update?


class UpdateDialog(ModalScreen):
    """Dialog for update notifications."""

    CSS = """
    UpdateDialog {
        align: center middle;
    }

    UpdateDialog > Container {
        width: 60;
        height: 22;
        background: $surface;
        border: solid green;
        padding: 2;
    }

    UpdateDialog.critical > Container {
        border: solid red;
    }
    """

    BINDINGS = [
        Binding("escape", "skip", "Skip"),
        Binding("enter", "update", "Update"),
        Binding("v", "view_changelog", "Changelog"),
    ]

    current_version: reactive[str] = reactive("1.0.0")
    new_version: reactive[str] = reactive("1.1.0")
    changelog: reactive[list] = reactive([])
    size_mb: reactive[float] = reactive(0)
    critical: reactive[bool] = reactive(False)
    downloading: reactive[bool] = reactive(False)
    download_progress: reactive[int] = reactive(0)

    class UpdateAccepted(Message):
        """User accepted update."""
        pass

    class UpdateSkipped(Message):
        """User skipped update."""
        version: str

        def __init__(self, version: str):
            self.version = version
            super().__init__()

    class ChangelogRequested(Message):
        """User wants to view changelog."""
        pass

    def compose(self):
        """Compose dialog."""
        # Set critical class if needed
        if self.critical:
            self.set_class("critical")

        yield Static(
            "[bold red]Critical Update Available[/]" if self.critical
            else "[bold green]Update Available[/]"
        )
        yield Static("")
        yield Static(f"[cyan]Current:[/] {self.current_version}")
        yield Static(f"[cyan]New:[/] {self.new_version}")
        yield Static(f"[dim]Size: {self.size_mb:.1f} MB[/]")
        yield Static("")
        yield Static("[bold]Changes:[/]")
        for item in self.changelog[:5]:
            yield Static(f"  • {item[:50]}")
        yield Static("")
        if self.downloading:
            yield ProgressBar(total=100, progress=self.download_progress)
        else:
            yield Button("Update Now", id="update", variant="success")
            yield Button("Skip", id="skip", variant="default")
            yield Button("View Changelog", id="changelog", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "update":
            self.post_message(self.UpdateAccepted())
        elif event.button.id == "skip":
            self.post_message(self.UpdateSkipped(self.new_version))
            self.dismiss()
        elif event.button.id == "changelog":
            self.post_message(self.ChangelogRequested())

    def action_update(self) -> None:
        """Update action."""
        self.post_message(self.UpdateAccepted())

    def action_skip(self) -> None:
        """Skip action."""
        self.post_message(self.UpdateSkipped(self.new_version))
        self.dismiss()

    def action_view_changelog(self) -> None:
        """View changelog."""
        self.post_message(self.ChangelogRequested())


class UpdateProgressDialog(ModalScreen):
    """Dialog showing update progress."""

    CSS = """
    UpdateProgressDialog {
        align: center middle;
    }

    UpdateProgressDialog > Container {
        width: 50;
        height: 10;
        background: $surface;
        border: solid cyan;
        padding: 2;
    }
    """

    progress: reactive[int] = reactive(0)
    status: reactive[str] = reactive("Downloading...")
    current_step: reactive[str] = reactive("")

    class Completed(Message):
        """Update completed."""
        pass

    class Failed(Message):
        """Update failed."""
        error: str

        def __init__(self, error: str):
            self.error = error
            super().__init__()

    def compose(self):
        """Compose dialog."""
        yield Static("[bold cyan]Updating Claude Code[/]")
        yield Static(self.status)
        yield ProgressBar(total=100, progress=self.progress)
        yield Static(f"[dim]{self.current_step}[/]")

    def update_progress(self, progress: int, step: str = "") -> None:
        """Update progress."""
        self.progress = progress
        self.current_step = step


class AutoUpdateWidget(Widget):
    """Widget for auto-update status in status bar."""

    DEFAULT_CSS = """
    AutoUpdateWidget {
        width: 20;
        height: 1;
    }
    """

    update_available: reactive[bool] = reactive(False)
    new_version: reactive[str] = reactive("")
    last_check: reactive[str] = reactive("")

    def render(self) -> Text:
        """Render auto-update status."""
        if self.update_available:
            return Text.from_markup(
                f"[green]↑ Update available: {self.new_version}[/]"
            )
        elif self.last_check:
            return Text.from_markup(
                f"[dim]Checked: {self.last_check}[/]"
            )
        return Text("[dim]No updates[/]")


__all__ = [
    "UpdateInfo",
    "UpdateDialog",
    "UpdateProgressDialog",
    "AutoUpdateWidget",
]