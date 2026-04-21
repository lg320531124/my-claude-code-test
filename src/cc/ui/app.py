"""Complete TUI App with multi-screen, Vim mode, and theme system."""

from __future__ import annotations
import asyncio
import time
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.widgets import Header, Footer, Static, Input, Label
from textual.screen import Screen
from textual.reactive import reactive
from textual.message import Message
from textual.events import Key
from textual.css.query import NoMatches
from rich.text import Text

from ..core.engine import QueryEngine
from ..core.session import Session, SessionManager
from ..tools import get_default_tools
from ..utils.config import Config
from ..types.message import create_user_message
from ..services.plugins.plugin_system import get_plugin_manager
from ..services.hooks.hooks_system import get_hook_manager

from .screens import (
    HelpScreen,
    SessionsScreen,
    PluginsScreen,
    HooksScreen,
    SettingsScreen,
    StatsScreen,
    MessageHistoryScreen,
    DoctorScreen,
)
from .widgets import (
    ThemeManager,
    VimMode,
    VimModeIndicator,
    VimHandler,
    StatusWidget,
    ToolProgressWidget,
)


class UserInput(Message):
    """Message sent when user submits input."""

    def __init__(self, text: str) -> None:
        self.text = text
        super().__init__()


class ToolProgress(Message):
    """Message for tool progress updates."""

    def __init__(self, tool_name: str, status: str, result: Optional[str] = None) -> None:
        self.tool_name = tool_name
        self.status = status  # "running", "complete", "error"
        self.result = result
        super().__init__()


class StreamingUpdate(Message):
    """Message for streaming text updates."""

    def __init__(self, text: str) -> None:
        self.text = text
        super().__init__()


class VimModeChanged(Message):
    """Message when Vim mode changes."""

    def __init__(self, mode: VimMode) -> None:
        self.mode = mode
        super().__init__()


class ThemeChanged(Message):
    """Message when theme changes."""

    def __init__(self, theme: str) -> None:
        self.theme = theme
        super().__init__()


class MessageWidget(Static):
    """Widget to display a single message."""

    DEFAULT_CSS = """
    MessageWidget {
        margin: 1;
        padding: 1 2;
    }

    MessageWidget.user-message {
        background: $surface-darken-1;
    }

    MessageWidget.assistant-message {
        background: $surface;
    }

    MessageWidget.tool-message {
        background: $surface-darken-2;
    }

    MessageWidget.error-message {
        background: $surface-darken-3;
        border: solid $error;
    }
    """

    def __init__(self, role: str, content: str, message_id: str = "", **kwargs) -> None:
        self.role = role
        self.content = content
        self.message_id = message_id
        super().__init__(**kwargs)
        self.set_class(f"{role}-message")

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
        elif self.role == "system":
            return Text.from_markup(f"[dim]System:[/] {self.content}")
        else:
            return Text(self.content)

    def update_content(self, new_content: str) -> None:
        """Update message content."""
        self.content = new_content
        self.refresh()


class InputWidget(Container):
    """Input widget for user messages."""

    DEFAULT_CSS = """
    InputWidget {
        height: auto;
        dock: bottom;
        padding: 1;
        background: $surface;
        border-top: solid $primary;
    }

    InputWidget Input {
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Enter message (Enter to send, Esc to cancel):")
        yield Input(placeholder="Type here... (/help for commands)", id="message-input")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        if event.value.strip():
            self.post_message(UserInput(event.value))
            event.input.value = ""

    def focus_input(self) -> None:
        """Focus the input."""
        try:
            self.query_one(Input).focus()
        except NoMatches:
            pass

    def clear_input(self) -> None:
        """Clear the input."""
        try:
            self.query_one(Input).value = ""
        except NoMatches:
            pass


class MainScreen(Screen):
    """Main chat screen with Vim mode and theme support."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #messages-container {
        height: 1fr;
        overflow-y: auto;
        padding: 1;
    }

    #status-container {
        height: 1;
    }

    #vim-indicator {
        dock: right;
        width: 8;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+l", "clear", "Clear"),
        Binding("ctrl+d", "doctor", "Doctor"),
        Binding("ctrl+h", "help", "Help"),
        Binding("ctrl+t", "toggle_theme", "Theme"),
        Binding("ctrl+s", "stats", "Stats"),
        Binding("ctrl+p", "sessions", "Sessions"),
        Binding("ctrl+o", "settings", "Settings"),
        Binding("ctrl+slash", "command_palette", "Commands"),
        Binding("ctrl+v", "toggle_vim", "Vim"),
        Binding("escape", "cancel", "Cancel"),
        # Vim-style bindings
        Binding("j", "vim_down", "↓", show=False),
        Binding("k", "vim_up", "↑", show=False),
        Binding("g", "vim_top", "Top", show=False),
        Binding("shift+g", "vim_bottom", "Bottom", show=False),
        Binding("colon", "vim_command", ":", show=False),
    ]

    messages: reactive[list] = reactive([])
    current_theme: reactive[str] = reactive("dark")
    streaming_text: reactive[str] = reactive("")
    vim_enabled: reactive[bool] = reactive(False)
    vim_mode: reactive[VimMode] = reactive(VimMode.NORMAL)

    def __init__(
        self,
        engine: QueryEngine,
        session: Session,
        config: Config,
        theme_manager: ThemeManager,
        session_manager: SessionManager,
    ):
        self.engine = engine
        self.session = session
        self.config = config
        self.theme_manager = theme_manager
        self.session_manager = session_manager
        self._streaming_task: asyncio.Task | None = None
        self._vim_handler = VimHandler(self)
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            VerticalScroll(id="messages-container"),
            id="messages-area",
        )
        yield Container(
            VimModeIndicator(id="vim-indicator"),
            StatusWidget(id="status-bar"),
            id="status-container",
        )
        yield Container(
            InputWidget(id="input-widget"),
            id="input-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Set up when screen mounts."""
        self.query_one(InputWidget).focus_input()

        # Set engine callbacks
        self.engine.set_callbacks(
            on_text=self._on_text_callback,
            on_tool_start=self._on_tool_start,
            on_tool_result=self._on_tool_result,
        )

        # Update theme
        self._apply_theme(self.current_theme)

    def _apply_theme(self, theme_name: str) -> None:
        """Apply a theme to the screen."""
        self.theme_manager.set_theme(theme_name)
        self.current_theme = theme_name
        # Would apply CSS variables here
        self._update_status_bar({"theme": theme_name})

    def _on_text_callback(self, text: str) -> None:
        """Callback for streaming text."""
        self.post_message(StreamingUpdate(text))

    def _on_tool_start(self, tool_name: str) -> None:
        """Callback for tool start."""
        self.post_message(ToolProgress(tool_name, "running"))

    def _on_tool_result(self, result: dict) -> None:
        """Callback for tool result."""
        tool_name = result.get("name", "unknown")
        is_error = result.get("is_error", False)
        status = "error" if is_error else "complete"
        content = result.get("content", "")
        self.post_message(ToolProgress(tool_name, status, content))

    def on_key(self, event: Key) -> None:
        """Handle key events for Vim mode."""
        if self.vim_enabled:
            action = self._vim_handler.handle_key(event.key)
            if action:
                self._execute_vim_action(action)
                event.stop()

    def _execute_vim_action(self, action: str) -> None:
        """Execute a Vim action."""
        if action == "scroll_down":
            container = self.query_one("#messages-container")
            container.action_scroll_down()
        elif action == "scroll_up":
            container = self.query_one("#messages-container")
            container.action_scroll_up()
        elif action == "scroll_top":
            container = self.query_one("#messages-container")
            container.action_scroll_home()
        elif action == "scroll_bottom":
            container = self.query_one("#messages-container")
            container.action_scroll_end()
        elif action == "enter_insert":
            self.vim_mode = VimMode.INSERT
            self.query_one(InputWidget).focus_input()
        elif action == "exit_insert":
            self.vim_mode = VimMode.NORMAL
        elif action == "quit":
            self.app.exit()
        elif action == "clear":
            self.action_clear()
        elif action.startswith("set_theme:"):
            theme_name = action.split(":")[1]
            self._apply_theme(theme_name)
        elif action.startswith("goto_line:"):
            line_num = int(action.split(":")[1])
            self._goto_message(line_num)

    def on_user_input(self, message: UserInput) -> None:
        """Handle user input."""
        text = message.text.strip()

        if text.startswith("/"):
            self._handle_command(text)
        elif text.lower() in ("exit", "quit", "q"):
            self.app.exit()
        else:
            self._process_query(text)

    def on_streaming_update(self, message: StreamingUpdate) -> None:
        """Handle streaming update."""
        self.streaming_text += message.text
        self._update_streaming_display()

    def on_tool_progress(self, message: ToolProgress) -> None:
        """Handle tool progress."""
        self._update_tool_display(message)

    def _handle_command(self, command: str) -> None:
        """Handle slash command."""
        cmd_parts = command.split()
        cmd = cmd_parts[0].lower()

        if cmd == "/help":
            self.app.push_screen(HelpScreen())
        elif cmd == "/clear":
            self.action_clear()
        elif cmd == "/doctor":
            self.app.push_screen(DoctorScreen())
        elif cmd == "/sessions":
            self.app.push_screen(SessionsScreen(self.session_manager))
        elif cmd == "/settings":
            self.app.push_screen(SettingsScreen())
        elif cmd == "/stats":
            self.app.push_screen(StatsScreen())
        elif cmd == "/plugins":
            self.app.push_screen(PluginsScreen(get_plugin_manager()))
        elif cmd == "/hooks":
            self.app.push_screen(HooksScreen(get_hook_manager()))
        elif cmd == "/history":
            self.app.push_screen(MessageHistoryScreen(self.session))
        elif cmd == "/model":
            self._add_message("system", f"Current model: {self.config.api.model}")
        elif cmd == "/theme":
            if len(cmd_parts) > 1:
                self._apply_theme(cmd_parts[1])
            else:
                themes = self.theme_manager.get_all_themes()
                self._add_message("system", f"Themes: {', '.join(themes)}")
        elif cmd == "/vim":
            self.action_toggle_vim()
        else:
            self._add_message("error", f"Unknown command: {command}")

    def _process_query(self, text: str) -> None:
        """Process a user query."""
        # Add user message
        self._add_message("user", text)
        self.streaming_text = ""

        # Create message
        msg = create_user_message(text)
        self.session.add_message(msg)

        # Run query async
        self._streaming_task = asyncio.create_task(self._run_query(text))

    async def _run_query(self, text: str) -> None:
        """Run query and stream response."""
        ctx = self.session.get_context()
        response_text = ""
        start_time = time.time()

        try:
            async for chunk in self.engine.query(text, ctx):
                if isinstance(chunk, str):
                    response_text += chunk
                elif isinstance(chunk, dict):
                    if chunk.get("type") == "complete":
                        stats = chunk.get("stats", {})
                        self._update_status_bar(stats)

            # Final message
            self._finalize_assistant_message(response_text)

        except Exception as e:
            self._add_message("error", str(e))
        finally:
            self._streaming_task = None

    def _add_message(self, role: str, content: str) -> None:
        """Add a message to the display."""
        container = self.query_one("#messages-container")
        msg_id = f"msg-{len(self.messages)}"
        widget = MessageWidget(role, content, message_id=msg_id, classes=f"message {role}-message")
        container.mount(widget)
        self.messages.append((role, content, msg_id))

        # Scroll to bottom
        container.scroll_end()

    def _update_streaming_display(self) -> None:
        """Update streaming display."""
        container = self.query_one("#messages-container")

        # Find or create streaming widget
        streaming_id = "streaming-assistant"
        try:
            widget = container.query_one(f"#{streaming_id}", MessageWidget)
            widget.update_content(self.streaming_text)
        except NoMatches:
            widget = MessageWidget(
                "assistant",
                self.streaming_text,
                message_id=streaming_id,
                classes="message assistant-message",
            )
            widget.id = streaming_id
            container.mount(widget)

        container.scroll_end()

    def _finalize_assistant_message(self, content: str) -> None:
        """Finalize assistant message."""
        container = self.query_one("#messages-container")

        # Remove streaming widget and add final
        streaming_id = "streaming-assistant"
        try:
            widget = container.query_one(f"#{streaming_id}", MessageWidget)
            widget.remove()
        except NoMatches:
            pass

        # Add final message
        self._add_message("assistant", content)

    def _update_tool_display(self, progress: ToolProgress) -> None:
        """Update tool display."""
        container = self.query_one("#messages-container")

        tool_id = f"tool-{progress.tool_name}"

        try:
            widget = container.query_one(f"#{tool_id}", ToolProgressWidget)
            widget.status = progress.status
            widget.result_preview = progress.result or ""
            widget.set_class(progress.status)
            widget.refresh()
        except NoMatches:
            widget = ToolProgressWidget()
            widget.tool_name = progress.tool_name
            widget.status = progress.status
            widget.result_preview = progress.result or ""
            widget.id = tool_id
            widget.set_class(progress.status)
            container.mount(widget)

        container.scroll_end()

    def _update_status_bar(self, stats: dict) -> None:
        """Update status bar."""
        try:
            status_bar = self.query_one("#status-bar", StatusWidget)
            if "model" in stats:
                status_bar.model = stats["model"]
            if "status" in stats:
                status_bar.status = stats["status"]
            status_bar.theme = self.current_theme
            if self.vim_enabled:
                status_bar.vim_mode = self.vim_mode.value
        except NoMatches:
            pass

        # Update vim indicator
        if self.vim_enabled:
            try:
                vim_indicator = self.query_one("#vim-indicator", VimModeIndicator)
                vim_indicator.enabled = True
                vim_indicator.set_mode(self.vim_mode)
            except NoMatches:
                pass

    def _goto_message(self, index: int) -> None:
        """Go to a specific message by index."""
        container = self.query_one("#messages-container")
        children = container.children
        if 0 <= index < len(children):
            children[index].scroll_visible()

    def action_clear(self) -> None:
        """Clear messages."""
        self.messages = []
        self.session.clear_messages()
        self.streaming_text = ""
        container = self.query_one("#messages-container")
        container.remove_children()
        self._add_message("system", "Session cleared")

    def action_toggle_theme(self) -> None:
        """Toggle theme."""
        themes = self.theme_manager.get_all_themes()
        current_idx = themes.index(self.current_theme)
        next_idx = (current_idx + 1) % len(themes)
        self._apply_theme(themes[next_idx])
        self._add_message("system", f"Theme: {self.current_theme}")

    def action_toggle_vim(self) -> None:
        """Toggle Vim mode."""
        self.vim_enabled = not self.vim_enabled
        self._vim_handler.enable() if self.vim_enabled else self._vim_handler.disable()

        if self.vim_enabled:
            self.vim_mode = VimMode.NORMAL

        self._update_status_bar({})
        self._add_message("system", f"Vim mode: {self.vim_enabled}")

    def action_cancel(self) -> None:
        """Cancel current operation."""
        if self._streaming_task:
            self._streaming_task.cancel()
            self._streaming_task = None
            self._add_message("system", "Cancelled")

    def action_sessions(self) -> None:
        """Open sessions screen."""
        self.app.push_screen(SessionsScreen(self.session_manager))

    def action_settings(self) -> None:
        """Open settings screen."""
        self.app.push_screen(SettingsScreen())

    def action_stats(self) -> None:
        """Open stats screen."""
        self.app.push_screen(StatsScreen())

    def action_command_palette(self) -> None:
        """Open command palette (placeholder)."""
        self._add_message("system", "Command palette: Type / followed by command name")


class ClaudeCodeApp(App):
    """Main TUI Application with multi-screen, themes, and Vim mode."""

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
        config: Optional[Config] = None,
        session: Optional[Session] = None,
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

        # Initialize managers
        self.theme_manager = ThemeManager()
        self.session_manager = SessionManager()

        super().__init__()

    def on_mount(self) -> None:
        """Mount the main screen."""
        self.push_screen(MainScreen(
            self.engine,
            self.session,
            self.config,
            self.theme_manager,
            self.session_manager,
        ))

    def action_quit(self) -> None:
        """Quit the app."""
        self.exit()


def run_tui() -> None:
    """Run the TUI application."""
    app = ClaudeCodeApp()
    app.run()


__all__ = [
    "ClaudeCodeApp",
    "MainScreen",
    "MessageWidget",
    "InputWidget",
    "UserInput",
    "ToolProgress",
    "StreamingUpdate",
    "VimModeChanged",
    "ThemeChanged",
    "run_tui",
]
