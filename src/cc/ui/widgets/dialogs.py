"""Dialog Components - Modal dialogs for user interaction."""

from __future__ import annotations
from textual.widget import Widget
from textual.containers import Center, Middle
from textual.widgets import Static, Button, Input
from textual.reactive import reactive
from textual.message import Message
from rich.text import Text


class ConfirmDialog(Widget):
    """Confirmation dialog."""

    DEFAULT_CSS = """
    ConfirmDialog {
        dock: top;
        height: 7;
        width: 50;
        background: $surface-darken-2;
        border: solid $accent;
    }

    ConfirmDialog .message {
        text-align: center;
        padding: 1;
    }

    ConfirmDialog .buttons {
        dock: bottom;
        height: 2;
    }

    ConfirmDialog Button {
        margin: 1;
    }
    """

    title: reactive[str] = reactive("")
    message: reactive[str] = reactive("")
    confirm_text: reactive[str] = reactive("Confirm")
    cancel_text: reactive[str] = reactive("Cancel")

    class Confirmed(Message):
        """User confirmed action."""
        pass

    class Cancelled(Message):
        """User cancelled action."""
        pass

    def compose(self):
        """Compose dialog."""
        yield Static(self.title, classes="title")
        yield Static(self.message, classes="message")
        yield Button(self.confirm_text, id="confirm")
        yield Button(self.cancel_text, id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "confirm":
            self.post_message(self.Confirmed())
        else:
            self.post_message(self.Cancelled())

    def render(self) -> Text:
        """Render dialog."""
        return Text.from_markup(
            f"[bold]{self.title}[/]\n\n"
            f"{self.message}\n\n"
            f"[green]{self.confirm_text}[/] / [red]{self.cancel_text}[/]"
        )


class InputDialog(Widget):
    """Input dialog for text entry."""

    DEFAULT_CSS = """
    InputDialog {
        dock: top;
        height: 5;
        width: 40;
        background: $surface-darken-2;
        border: solid $primary;
    }

    InputDialog Input {
        width: 30;
        margin: 1;
    }
    """

    title: reactive[str] = reactive("")
    placeholder: reactive[str] = reactive("")
    default_value: reactive[str] = reactive("")

    class Submitted(Message):
        """User submitted input."""
        value: str

        def __init__(self, value: str):
            self.value = value
            super().__init__()

    def compose(self):
        """Compose dialog."""
        yield Static(self.title)
        yield Input(value=self.default_value, placeholder=self.placeholder)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        self.post_message(self.Submitted(event.value))


class ProgressDialog(Widget):
    """Progress dialog for long operations."""

    DEFAULT_CSS = """
    ProgressDialog {
        dock: top;
        height: 5;
        width: 50;
        background: $surface-darken-2;
        border: solid $secondary;
    }
    """

    title: reactive[str] = reactive("")
    progress: reactive[int] = reactive(0)
    total: reactive[int] = reactive(100)
    status: reactive[str] = reactive("")

    def render(self) -> Text:
        """Render progress."""
        percent = int(self.progress / self.total * 100) if self.total > 0 else 0
        bar_width = 30
        filled = int(bar_width * percent / 100)

        bar = "[" + "=" * filled + " " * (bar_width - filled) + "]"

        return Text.from_markup(
            f"[bold]{self.title}[/]\n\n"
            f"{bar} [cyan]{percent}%[/]\n\n"
            f"[dim]{self.status}[/]"
        )


class ErrorDialog(Widget):
    """Error dialog for displaying errors."""

    DEFAULT_CSS = """
    ErrorDialog {
        dock: top;
        height: 7;
        width: 50;
        background: $surface-darken-3;
        border: solid red;
    }
    """

    title: reactive[str] = reactive("Error")
    error_type: reactive[str] = reactive("")
    message: reactive[str] = reactive("")
    suggestion: reactive[str] = reactive("")

    class Dismissed(Message):
        """User dismissed error."""
        pass

    def render(self) -> Text:
        """Render error."""
        parts = [
            f"[bold red]{self.title}[/]",
            f"[red]{self.error_type}[/]",
            f"{self.message}",
        ]

        if self.suggestion:
            parts.append(f"\n[dim]Suggestion: {self.suggestion}[/]")

        parts.append("\n[press any key to dismiss]")

        return Text.from_markup("\n".join(parts))


class HelpDialog(Widget):
    """Help dialog for displaying help information."""

    DEFAULT_CSS = """
    HelpDialog {
        dock: top;
        height: 15;
        width: 60;
        background: $surface-darken-2;
        border: solid $accent;
    }
    """

    topic: reactive[str] = reactive("")
    content: reactive[str] = reactive("")

    def render(self) -> Text:
        """Render help."""
        return Text.from_markup(
            f"[bold]Help: {self.topic}[/]\n\n"
            f"{self.content}\n\n"
            f"[dim]Press Escape to close[/]"
        )


class SettingsDialog(Widget):
    """Settings dialog for configuration."""

    DEFAULT_CSS = """
    SettingsDialog {
        dock: top;
        height: 20;
        width: 50;
        background: $surface-darken-2;
        border: solid $primary;
    }
    """

    settings: reactive[dict] = reactive({})
    current_category: reactive[str] = reactive("general")

    def render(self) -> Text:
        """Render settings."""
        lines = [f"[bold]Settings: {self.current_category}[/]"]

        category_settings = self.settings.get(self.current_category, {})
        for key, value in category_settings.items():
            lines.append(f"  [cyan]{key}[/]: {value}")

        return Text.from_markup("\n".join(lines))


class SelectDialog(Widget):
    """Select dialog for choosing from options."""

    DEFAULT_CSS = """
    SelectDialog {
        dock: top;
        height: 10;
        width: 40;
        background: $surface-darken-2;
        border: solid $secondary;
    }
    """

    title: reactive[str] = reactive("")
    options: reactive[list] = reactive([])
    selected: reactive[int] = reactive(0)

    class Selected(Message):
        """User selected option."""
        option: str

        def __init__(self, option: str):
            self.option = option
            super().__init__()

    def render(self) -> Text:
        """Render select dialog."""
        lines = [f"[bold]{self.title}[/]"]

        for i, option in enumerate(self.options):
            if i == self.selected:
                lines.append(f"  [reverse]{option}[/]")
            else:
                lines.append(f"  {option}")

        return Text.from_markup("\n".join(lines))

    def move_selection(self, delta: int) -> None:
        """Move selection."""
        self.selected = max(0, min(len(self.options) - 1, self.selected + delta))

    def confirm_selection(self) -> None:
        """Confirm current selection."""
        if self.selected < len(self.options):
            self.post_message(self.Selected(self.options[self.selected]))


__all__ = [
    "ConfirmDialog",
    "InputDialog",
    "ProgressDialog",
    "ErrorDialog",
    "HelpDialog",
    "SettingsDialog",
    "SelectDialog",
]
