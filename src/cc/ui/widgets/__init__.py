"""Widgets for TUI."""

from textual.widget import Widget
from textual.containers import Horizontal
from textual.widgets import Static, Button, Label
from textual.reactive import reactive
from rich.text import Text


class StatusWidget(Static):
    """Status display widget."""

    status: reactive[str] = reactive("ready")
    model: reactive[str] = reactive("claude-sonnet-4-6")

    def render(self) -> Text:
        """Render status."""
        status_colors = {
            "ready": "green",
            "thinking": "yellow",
            "error": "red",
        }
        color = status_colors.get(self.status, "white")
        return Text.from_markup(
            f"[{color}]{self.status}[/] | Model: [cyan]{self.model}[/]"
        )


class TokenCounterWidget(Static):
    """Token usage display."""

    input_tokens: reactive[int] = reactive(0)
    output_tokens: reactive[int] = reactive(0)

    def render(self) -> Text:
        """Render token count."""
        return Text.from_markup(
            f"Tokens: [blue]{self.input_tokens}[/] in / [green]{self.output_tokens}[/] out"
        )


class ToolProgressWidget(Widget):
    """Show tool execution progress."""

    def __init__(self, tool_name: str, status: str = "running"):
        self.tool_name = tool_name
        self.status = status
        super().__init__()

    def compose(self):
        yield Horizontal(
            Static(f"[cyan]{self.tool_name}[/]", classes="tool-name"),
            Static(f"[dim]{self.status}[/]", classes="tool-status"),
        )


class MessageListWidget(Widget):
    """List of messages."""

    DEFAULT_CSS = """
    MessageListWidget {
        height: 1fr;
        overflow-y: scroll;
    }
    """

    def compose(self):
        yield Static("Messages will appear here", id="message-placeholder")