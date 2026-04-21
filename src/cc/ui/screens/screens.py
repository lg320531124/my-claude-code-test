"""UI Screens - Multiple screens for different functionality."""

from __future__ import annotations
import asyncio
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.widgets import (
    Header,
    Footer,
    Static,
    Input,
    Button,
    Label,
    ListView,
    ListItem,
    Tree,
    DataTable,
)
from textual.screen import Screen, ModalScreen
from textual.reactive import reactive
from textual.message import Message

from ...core.session import Session, SessionManager
from ...services.plugins.plugin_system import PluginManager
from ...services.hooks.hooks_system import HookManager


class HelpScreen(ModalScreen):
    """Help screen with keybindings and commands."""

    CSS = """
    HelpScreen {
        align: center middle;
    }

    HelpScreen > Container {
        width: 80;
        height: 30;
        background: $surface;
        border: solid $primary;
        padding: 2;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("q", "close", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Container():
            yield Label("[bold]Claude Code CLI Help[/bold]", classes="title")
            yield VerticalScroll(
                Static(self._get_keybindings_text()),
                Static(self._get_commands_text()),
                Static(self._get_vim_text()),
            )

    def _get_keybindings_text(self) -> str:
        return """
[bold cyan]Keybindings:[/bold cyan]

[bold]Navigation[/bold]
  Ctrl+P       Previous message
  Ctrl+N       Next message
  Ctrl+G       Go to message
  Page Up/Down Scroll messages

[bold]Actions[/bold]
  Ctrl+C       Quit
  Ctrl+L       Clear session
  Ctrl+D       Run diagnostics
  Ctrl+S       Show stats
  Ctrl+T       Toggle theme
  Ctrl+O       Toggle options

[bold]Input[/bold]
  Enter        Send message
  Escape       Cancel input/action
  Ctrl+U       Clear input
  Ctrl+W       Delete word
"""

    def _get_commands_text(self) -> str:
        return """
[bold cyan]Slash Commands:[/bold cyan]

  /help        Show this help
  /clear       Clear session
  /commit      Commit changes
  /review      Code review
  /compact     Compact context
  /config      Manage config
  /doctor      Run diagnostics
  /mcp         MCP management
  /memory      Memory management
  /sessions    Session history
  /theme       Theme settings
  /stats       Usage statistics
  /vim         Toggle Vim mode
"""

    def _get_vim_text(self) -> str:
        return """
[bold cyan]Vim Mode (when enabled):[/bold cyan]

  i            Enter insert mode
  Esc          Exit insert mode
  :            Command mode
  j/k          Scroll up/down
  gg/G         Top/bottom
  dd           Delete message
  yy           Copy message
  p            Paste

[bold]Command mode:[/bold]
  :q           Quit
  :w           Save session
  :clear       Clear
  :theme X     Set theme
"""

    def action_close(self) -> None:
        self.dismiss()


class SessionsScreen(Screen):
    """Screen for browsing session history."""

    CSS = """
    SessionsScreen {
        layout: vertical;
    }

    #session-list {
        height: 1fr;
    }

    #session-info {
        height: auto;
        dock: bottom;
        padding: 1;
        background: $surface-darken-2;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("enter", "load", "Load"),
        Binding("d", "delete", "Delete"),
        Binding("e", "export", "Export"),
    ]

    sessions: reactive[list] = reactive([])

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("[bold]Session History[/bold]")
        yield ListView(id="session-list")
        yield Container(
            Label("Select a session to view details", id="session-detail"),
            id="session-info",
        )
        yield Footer()

    def on_mount(self) -> None:
        self._load_sessions()

    def _load_sessions(self) -> None:
        sessions = self.session_manager.list_sessions()
        self.sessions = sessions

        list_view = self.query_one("#session-list", ListView)
        for session in sessions:
            item = ListItem(
                Label(f"{session['id']}: {session['created_at']} ({session['message_count']} msgs)")
            )
            list_view.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx < len(self.sessions):
            session = self.sessions[idx]
            detail = self.query_one("#session-detail", Label)
            detail.update(
                f"Session: {session['id']}\n"
                f"Created: {session['created_at']}\n"
                f"Messages: {session['message_count']}\n"
                f"Last active: {session['last_active']}"
            )

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_load(self) -> None:
        list_view = self.query_one("#session-list", ListView)
        if list_view.index < len(self.sessions):
            session_id = self.sessions[list_view.index]["id"]
            self.app.post_message(SessionLoadRequest(session_id))
            self.app.pop_screen()

    def action_delete(self) -> None:
        list_view = self.query_one("#session-list", ListView)
        if list_view.index < len(self.sessions):
            session_id = self.sessions[list_view.index]["id"]
            self.session_manager.delete_session(session_id)
            self._load_sessions()

    def action_export(self) -> None:
        list_view = self.query_one("#session-list", ListView)
        if list_view.index < len(self.sessions):
            session_id = self.sessions[list_view.index]["id"]
            path = Path(f"session_{session_id}.json")
            self.session_manager.export_session(session_id, path)


class SessionLoadRequest(Message):
    """Request to load a session."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__()


class PluginsScreen(Screen):
    """Screen for managing plugins."""

    CSS = """
    PluginsScreen {
        layout: vertical;
    }

    #plugin-list {
        height: 1fr;
    }

    DataTable {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("r", "reload", "Reload"),
        Binding("e", "enable", "Enable"),
        Binding("d", "disable", "Disable"),
    ]

    def __init__(self, plugin_manager: PluginManager):
        self.plugin_manager = plugin_manager
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("[bold]Plugin Management[/bold]")
        yield DataTable(id="plugin-list")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#plugin-list", DataTable)
        table.add_columns("Name", "Version", "State", "Description")
        self._refresh_plugins()

    def _refresh_plugins(self) -> None:
        table = self.query_one("#plugin-list", DataTable)
        table.clear()

        plugins = self.plugin_manager.list_plugins()
        for plugin in plugins:
            table.add_row(
                plugin["name"],
                plugin["version"],
                plugin["state"],
                plugin["description"],
            )

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_reload(self) -> None:
        asyncio.create_task(self._reload_plugins())

    async def _reload_plugins(self) -> None:
        await self.plugin_manager.reload()
        self._refresh_plugins()

    def action_enable(self) -> None:
        table = self.query_one("#plugin-list", DataTable)
        if table.cursor_row >= 0:
            # Get plugin name from row
            self.plugin_manager.loader.enable("selected_plugin")
            self._refresh_plugins()

    def action_disable(self) -> None:
        table = self.query_one("#plugin-list", DataTable)
        if table.cursor_row >= 0:
            self.plugin_manager.loader.disable("selected_plugin")
            self._refresh_plugins()


class HooksScreen(Screen):
    """Screen for viewing hooks."""

    CSS = """
    HooksScreen {
        layout: vertical;
    }

    #hooks-tree {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    def __init__(self, hook_manager: HookManager):
        self.hook_manager = hook_manager
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("[bold]Hooks Registry[/bold]")
        yield Tree("Hooks", id="hooks-tree")
        yield Footer()

    def on_mount(self) -> None:
        self._build_tree()

    def _build_tree(self) -> None:
        tree = self.query_one("#hooks-tree", Tree)
        stats = self.hook_manager.get_stats()

        root = tree.root
        root.add("[cyan]Total Hooks[/cyan]", data=str(stats["total_hooks"]))

        events = root.add("[yellow]Events[/yellow]")
        for event_name, event_stats in stats.get("events", {}).items():
            event_node = events.add(f"[green]{event_name}[/green]")
            event_node.add(f"Count: {event_stats['count']}")
            event_node.add(f"Calls: {event_stats['total_calls']}")

    def action_back(self) -> None:
        self.app.pop_screen()


class SettingsScreen(Screen):
    """Settings/configuration screen."""

    CSS = """
    SettingsScreen {
        layout: vertical;
    }

    #settings-tabs {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("s", "save", "Save"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(
            Label("[bold]Settings[/bold]"),
            Label(""),
            Label("[cyan]General[/cyan]"),
            Label("Model Selection"),
            Input(placeholder="claude-opus-4-7", id="model-input"),
            Label("Base URL"),
            Input(placeholder="https://api.anthropic.com", id="base-url-input"),
            Label("Max Tokens"),
            Input(placeholder="8192", id="max-tokens-input"),
            Label(""),
            Label("[cyan]Theme[/cyan]"),
            Horizontal(
                Button("Dark", id="theme-dark"),
                Button("Light", id="theme-light"),
                Button("Mono", id="theme-mono"),
                Button("Gruvbox", id="theme-gruvbox"),
            ),
            Label("Font Size"),
            Input(placeholder="14", id="font-size-input"),
            Label(""),
            Label("[cyan]Vim Mode[/cyan]"),
            Horizontal(
                Button("Enable", id="vim-enable"),
                Button("Disable", id="vim-disable"),
            ),
            Label("Vim Keybindings: i: insert, Esc: normal, j/k: scroll"),
            Label(""),
            Label("[cyan]Permissions[/cyan]"),
            Horizontal(
                Button("Ask", id="perm-ask"),
                Button("Auto-approve", id="perm-auto"),
            ),
            Label("Allowed Patterns"),
            Input(placeholder="Bash(ls*)", id="allow-pattern"),
        )
        yield Footer()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_save(self) -> None:
        # Would save to config
        self.app.pop_screen()


class StatsScreen(Screen):
    """Statistics and usage screen."""

    CSS = """
    StatsScreen {
        layout: vertical;
    }

    DataTable {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("[bold]Usage Statistics[/bold]")
        yield DataTable(id="stats-table")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#stats-table", DataTable)
        table.add_columns("Metric", "Value")

        # Add sample stats
        table.add_row("Total Sessions", "5")
        table.add_row("Total Messages", "150")
        table.add_row("Total Tokens (Input)", "45,000")
        table.add_row("Total Tokens (Output)", "12,000")
        table.add_row("Tool Calls", "87")
        table.add_row("Avg Response Time", "2.3s")

    def action_back(self) -> None:
        self.app.pop_screen()


class MessageHistoryScreen(Screen):
    """Screen for browsing message history."""

    CSS = """
    MessageHistoryScreen {
        layout: vertical;
    }

    #history-list {
        height: 1fr;
    }

    #message-preview {
        height: 10;
        dock: bottom;
        background: $surface-darken-2;
        padding: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("enter", "select", "Select"),
        Binding("j", "down", "Down"),
        Binding("k", "up", "Up"),
    ]

    messages: reactive[list] = reactive([])

    def __init__(self, session: Session):
        self.session = session
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("[bold]Message History[/bold]")
        yield ListView(id="history-list")
        yield VerticalScroll(Static("", id="preview-content"), id="message-preview")
        yield Footer()

    def on_mount(self) -> None:
        self._load_messages()

    def _load_messages(self) -> None:
        messages = self.session.messages
        self.messages = messages

        list_view = self.query_one("#history-list", ListView)
        for i, msg in enumerate(messages):
            role = msg.get("role", "unknown")
            preview = self._get_preview(msg)
            item = ListItem(Label(f"[{i}] {role}: {preview}"))
            list_view.append(item)

    def _get_preview(self, msg: dict) -> str:
        content = msg.get("content", "")
        if isinstance(content, str):
            return content[:50] + "..." if len(content) > 50 else content
        return "complex content"

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = event.list_view.index
        if idx < len(self.messages):
            msg = self.messages[idx]
            preview = self.query_one("#preview-content", Static)
            content = msg.get("content", "")
            if isinstance(content, str):
                preview.update(content)
            else:
                preview.update(str(content))

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_select(self) -> None:
        # Jump to selected message
        self.app.pop_screen()

    def action_down(self) -> None:
        list_view = self.query_one("#history-list", ListView)
        list_view.action_cursor_down()

    def action_up(self) -> None:
        list_view = self.query_one("#history-list", ListView)
        list_view.action_cursor_up()


__all__ = [
    "HelpScreen",
    "SessionsScreen",
    "SessionLoadRequest",
    "PluginsScreen",
    "HooksScreen",
    "SettingsScreen",
    "StatsScreen",
    "MessageHistoryScreen",
]
