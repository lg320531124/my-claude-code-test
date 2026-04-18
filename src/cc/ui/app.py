"""Main TUI App using Textual."""

import asyncio
from pathlib import Path
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Static, Input, Button, Label
from textual.screen import Screen
from textual.reactive import reactive
from textual.message import Message
from textual.events import Key
from rich.markdown import Markdown
from rich.text import Text

from ..core.engine import QueryEngine
from ..core.session import Session
from ..tools import get_default_tools
from ..utils.config import Config
from ..types.message import create_user_message


class UserInput(Message):
    """Message sent when user submits input."""

    def __init__(self, text: str) -> None:
        self.text = text
        super().__init__()


class MessageWidget(Static):
    """Widget to display a single message."""

    def __init__(self, role: str, content: str, **kwargs) -> None:
        self.role = role
        self.content = content
        super().__init__(**kwargs)

    def render(self) -> Text:
        """Render the message."""
        if self.role == "user":
            return Text.from_markup(f"[bold blue]You:[/] {self.content}")
        elif self.role == "assistant":
            return Text.from_markup(f"[bold green]Claude:[/] {self.content}")
        elif self.role == "tool":
            return Text.from_markup(f"[dim cyan]Tool:[/] {self.content}")
        elif self.role == "error":
            return Text.from_markup(f"[bold red]Error:[/] {self.content}")
        else:
            return Text(self.content)


class InputWidget(Container):
    """Input widget for user messages."""

    def compose(self) -> ComposeResult:
        yield Label("Enter message (or /command):")
        yield Input(placeholder="Type here...", id="message-input")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        if event.value.strip():
            self.post_message(UserInput(event.value))
            event.input.value = ""


class MainScreen(Screen):
    """Main chat screen."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #messages-container {
        height: 1fr;
        overflow-y: auto;
        padding: 1;
    }

    #input-container {
        height: auto;
        dock: bottom;
        padding: 1;
        border-top: solid $primary;
    }

    .message {
        margin: 1;
        padding: 1;
    }

    .user-message {
        background: $surface;
    }

    .assistant-message {
        background: $surface-darken-1;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+l", "clear", "Clear"),
        Binding("ctrl+d", "doctor", "Doctor"),
        Binding("ctrl+h", "help", "Help"),
    ]

    messages: reactive[list] = reactive([])

    def __init__(self, engine: QueryEngine, session: Session, config: Config):
        self.engine = engine
        self.session = session
        self.config = config
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            VerticalScroll(id="messages-container"),
            id="messages-area",
        )
        yield Container(
            InputWidget(id="input-widget"),
            id="input-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Set up when screen mounts."""
        self.query_one(Input).focus()

    def on_user_input(self, message: UserInput) -> None:
        """Handle user input."""
        text = message.text.strip()

        if text.startswith("/"):
            self._handle_command(text)
        elif text.lower() in ("exit", "quit", "q"):
            self.app.exit()
        else:
            self._process_query(text)

    def _handle_command(self, command: str) -> None:
        """Handle slash command."""
        if command == "/help":
            self._add_message("system", self._get_help_text())
        elif command == "/clear":
            self.messages = []
            self.session.clear_messages()
            self._add_message("system", "Session cleared")
        elif command == "/doctor":
            from ..commands.doctor import run_doctor
            # Run doctor and show results
            self._add_message("system", "Running diagnostics...")
        elif command == "/model":
            self._add_message("system", f"Current model: {self.config.api.model}")
        else:
            self._add_message("error", f"Unknown command: {command}")

    def _process_query(self, text: str) -> None:
        """Process a user query."""
        # Add user message
        self._add_message("user", text)

        # Create message
        msg = create_user_message(text)
        self.session.add_message(msg)

        # Run query async
        asyncio.create_task(self._run_query(text))

    async def _run_query(self, text: str) -> None:
        """Run query and stream response."""
        ctx = self.session.get_context()
        response_text = ""

        try:
            async for chunk in self.engine.query(self.session.messages, ctx):
                if isinstance(chunk, str):
                    response_text += chunk
                    # Update display
                    self._update_last_assistant(response_text)
        except Exception as e:
            self._add_message("error", str(e))

    def _add_message(self, role: str, content: str) -> None:
        """Add a message to the display."""
        container = self.query_one("#messages-container")
        widget = MessageWidget(role, content, classes=f"message {role}-message")
        container.mount(widget)
        self.messages.append((role, content))

        # Scroll to bottom
        container.scroll_end()

    def _update_last_assistant(self, content: str) -> None:
        """Update the last assistant message."""
        container = self.query_one("#messages-container")
        # Find last assistant widget
        children = list(container.children)
        for child in reversed(children):
            if isinstance(child, MessageWidget) and child.role == "assistant":
                child.content = content
                child.refresh()
                break

    def _get_help_text(self) -> str:
        """Get help text."""
        return """
Commands:
/help - Show this help
/clear - Clear session
/model - Show current model
/exit - Quit

Shortcuts:
Ctrl+C - Quit
Ctrl+L - Clear
Ctrl+D - Doctor
Ctrl+H - Help
"""

    def action_clear(self) -> None:
        """Clear messages."""
        self.messages = []
        self.session.clear_messages()
        container = self.query_one("#messages-container")
        container.remove_children()

    def action_doctor(self) -> None:
        """Run doctor."""
        self._add_message("system", "Running diagnostics...")

    def action_help(self) -> None:
        """Show help."""
        self._add_message("system", self._get_help_text())


class ClaudeCodeApp(App):
    """Main TUI Application."""

    CSS = """
    App {
        background: $surface;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
    ]

    def __init__(
        self,
        config: Config | None = None,
        session: Session | None = None,
    ):
        self.config = config or Config.load()
        self.session = session or Session()

        # Initialize engine
        tools = get_default_tools()
        self.engine = QueryEngine(
            model=self.config.api.model,
            tools=tools,
            base_url=self.config.api.base_url,
        )

        super().__init__()

    def on_mount(self) -> None:
        """Mount the main screen."""
        self.push_screen(MainScreen(self.engine, self.session, self.config))

    def action_quit(self) -> None:
        """Quit the app."""
        self.exit()


def run_tui() -> None:
    """Run the TUI application."""
    app = ClaudeCodeApp()
    app.run()