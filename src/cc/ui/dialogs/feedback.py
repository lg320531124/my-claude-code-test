"""Feedback Dialog - User feedback collection."""

from __future__ import annotations
from dataclasses import dataclass
from textual.widget import Widget
from textual.widgets import Static, Button, TextArea
from textual.reactive import reactive
from textual.message import Message
from textual.screen import ModalScreen
from textual.binding import Binding
from rich.text import Text


@dataclass
class FeedbackResult:
    """Feedback submission result."""
    feedback_type: str  # "bug", "feature", "general"
    rating: int  # 1-5
    message: str
    email: str | None
    session_context: dict | None


class FeedbackDialog(ModalScreen):
    """Dialog for collecting user feedback."""

    CSS = """
    FeedbackDialog {
        align: center middle;
    }

    FeedbackDialog > Container {
        width: 70;
        height: 25;
        background: $surface;
        border: solid cyan;
        padding: 2;
    }

    TextArea {
        height: 6;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "submit", "Submit"),
    ]

    feedback_type: reactive[str] = reactive("general")
    rating: reactive[int] = reactive(0)
    message: reactive[str] = reactive("")
    email: reactive[str] = reactive("")
    show_email_field: reactive[bool] = reactive(False)

    class Submitted(Message):
        """Feedback submitted."""
        result: FeedbackResult

        def __init__(self, result: FeedbackResult):
            self.result = result
            super().__init__()

    class Cancelled(Message):
        """Feedback cancelled."""

    def compose(self):
        """Compose dialog."""
        yield Static("[bold cyan]Send Feedback[/]")
        yield Static("")
        yield Static("[cyan]Feedback Type:[/]")
        yield Button("Bug Report", id="bug", variant="error")
        yield Button("Feature Request", id="feature", variant="primary")
        yield Button("General Feedback", id="general", variant="success")
        yield Static("")
        yield Static("[cyan]Rating (1-5):[/]")
        yield Horizontal(
            *[Button(f"{i}", id=f"rating-{i}") for i in range(1, 6)]
        )
        yield Static("")
        yield Static("[cyan]Message:[/]")
        yield TextArea(id="message")
        yield Static("")
        yield Button("Submit", id="submit", variant="success")
        yield Button("Cancel", id="cancel", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id in ["bug", "feature", "general"]:
            self.feedback_type = event.button.id
        elif event.button.id.startswith("rating-"):
            self.rating = int(event.button.id.split("-")[1])
        elif event.button.id == "submit":
            self._submit()
        elif event.button.id == "cancel":
            self.post_message(self.Cancelled())
            self.dismiss()

    def _submit(self) -> None:
        """Submit feedback."""
        message = self.query_one("#message", TextArea).text

        result = FeedbackResult(
            feedback_type=self.feedback_type,
            rating=self.rating,
            message=message,
            email=self.email if self.show_email_field else None,
            session_context=None,
        )

        self.post_message(self.Submitted(result))
        self.dismiss()

    def action_cancel(self) -> None:
        """Cancel action."""
        self.dismiss()


class BugReportDialog(FeedbackDialog):
    """Specialized dialog for bug reports."""

    error_message: reactive[str] = reactive("")
    stack_trace: reactive[str] = reactive("")
    reproduction_steps: reactive[str] = reactive("")
    system_info: reactive[dict] = reactive({})

    def compose(self):
        """Compose bug report dialog."""
        yield Static("[bold red]Report Bug[/]")
        yield Static("")
        yield Static("[cyan]Error Message:[/]")
        yield Static(f"[dim]{self.error_message[:100]}[/]")
        yield Static("")
        yield Static("[cyan]What were you trying to do?[/]")
        yield TextArea(id="reproduction", placeholder="Describe what happened...")
        yield Static("")
        yield Static("[cyan]Include system info?[/]")
        yield Button("Yes", id="include-sysinfo", variant="primary")
        yield Button("No", id="no-sysinfo", variant="default")
        yield Static("")
        yield Button("Send Report", id="submit", variant="success")
        yield Button("Cancel", id="cancel", variant="error")

    def _submit(self) -> None:
        """Submit bug report."""
        reproduction = self.query_one("#reproduction", TextArea).text

        result = FeedbackResult(
            feedback_type="bug",
            rating=0,
            message=f"Error: {self.error_message}\n\nSteps: {reproduction}",
            email=None,
            session_context={
                "error_message": self.error_message,
                "system_info": self.system_info,
            },
        )

        self.post_message(self.Submitted(result))
        self.dismiss()


class QuickRatingWidget(Widget):
    """Quick rating widget for inline feedback."""

    DEFAULT_CSS = """
    QuickRatingWidget {
        width: 30;
        height: 2;
        padding: 1;
        background: $surface-darken-2;
    }
    """

    prompt: reactive[str] = reactive("How was this response?")

    class Rated(Message):
        """User rated."""
        rating: int

        def __init__(self, rating: int):
            self.rating = rating
            super().__init__()

    def render(self) -> Text:
        """Render rating widget."""
        stars = "⭐" * 5
        return Text.from_markup(
            f"[dim]{self.prompt}[/] [yellow]{stars}[/]"
        )

    def on_key(self, event) -> None:
        """Handle key press."""
        key = event.key
        if key.isdigit() and 1 <= int(key) <= 5:
            self.post_message(self.Rated(int(key)))


__all__ = [
    "FeedbackResult",
    "FeedbackDialog",
    "BugReportDialog",
    "QuickRatingWidget",
]