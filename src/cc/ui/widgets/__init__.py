"""Enhanced UI widgets - Theme system, Vim mode, and more."""

from __future__ import annotations
from enum import Enum
from typing import Optional, ClassVar
from pathlib import Path

from textual.widget import Widget
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Static, Button, Label, Input, ProgressBar, DataTable
from textual.reactive import reactive
from textual.message import Message
from rich.text import Text
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.table import Table


class ThemeType(Enum):
    """Available themes."""
    DARK = "dark"
    LIGHT = "light"
    MONO = "mono"
    GRUVBOX = "gruvbox"
    NORD = "nord"
    DRACULA = "dracula"
    SOLARIZED = "solarized"


class ThemeManager:
    """Manage UI themes."""

    THEMES: ClassVar[Dict[str, str]] = {
        "dark": """
        $surface: #1e1e2e;
        $surface-darken-1: #181825;
        $surface-darken-2: #11111b;
        $surface-darken-3: #0a0a12;
        $primary: #cba6f7;
        $secondary: #89b4fa;
        $accent: #f9e2af;
        $text: #cdd6f4;
        $text-muted: #6c7086;
        $success: #a6e3a1;
        $warning: #f9e2af;
        $error: #f38ba8;
        """,
        "light": """
        $surface: #eff1f5;
        $surface-darken-1: #e6e9ef;
        $surface-darken-2: #dce0e8;
        $surface-darken-3: #ccd0da;
        $primary: #8839ef;
        $secondary: #1e66f5;
        $accent: #df8e1d;
        $text: #4c4f69;
        $text-muted: #8c8fa1;
        $success: #40a02b;
        $warning: #df8e1d;
        $error: #d20f39;
        """,
        "mono": """
        $surface: #000000;
        $surface-darken-1: #0a0a0a;
        $surface-darken-2: #111111;
        $surface-darken-3: #1a1a1a;
        $primary: #ffffff;
        $secondary: #cccccc;
        $accent: #aaaaaa;
        $text: #ffffff;
        $text-muted: #666666;
        $success: #ffffff;
        $warning: #ffffff;
        $error: #ffffff;
        """,
        "gruvbox": """
        $surface: #282828;
        $surface-darken-1: #1d2021;
        $surface-darken-2: #181818;
        $surface-darken-3: #0d0d0d;
        $primary: #fb4934;
        $secondary: #83a598;
        $accent: #fabd2f;
        $text: #ebdbb2;
        $text-muted: #a89984;
        $success: #b8bb26;
        $warning: #fabd2f;
        $error: #fb4934;
        """,
        "nord": """
        $surface: #2e3440;
        $surface-darken-1: #3b4252;
        $surface-darken-2: #434c5e;
        $surface-darken-3: #4c566a;
        $primary: #88c0d0;
        $secondary: #81a1c1;
        $accent: #bf616a;
        $text: #eceff4;
        $text-muted: #d8dee9;
        $success: #a3be8c;
        $warning: #ebcb8b;
        $error: #bf616a;
        """,
        "dracula": """
        $surface: #282a36;
        $surface-darken-1: #21222c;
        $surface-darken-2: #191a21;
        $surface-darken-3: #0f0f14;
        $primary: #bd93f9;
        $secondary: #8be9fd;
        $accent: #ff79c6;
        $text: #f8f8f2;
        $text-muted: #6272a4;
        $success: #50fa7b;
        $warning: #ffb86c;
        $error: #ff5555;
        """,
        "solarized": """
        $surface: #002b36;
        $surface-darken-1: #073642;
        $surface-darken-2: #094b5b;
        $surface-darken-3: #0c6076;
        $primary: #268bd2;
        $secondary: #2aa198;
        $accent: #cb4b16;
        $text: #839496;
        $text-muted: #586e75;
        $success: #859900;
        $warning: #b58900;
        $error: #dc322f;
        """,
    }

    def __init__(self):
        self._current_theme = "dark"

    def get_theme_css(self, theme_name: str) -> str:
        """Get CSS for a theme."""
        return self.THEMES.get(theme_name, self.THEMES["dark"])

    def set_theme(self, theme_name: str) -> None:
        """Set current theme."""
        self._current_theme = theme_name

    def get_current_theme(self) -> str:
        """Get current theme name."""
        return self._current_theme

    def get_all_themes(self) -> List[str]:
        """Get list of all theme names."""
        return list(self.THEMES.keys())


class VimMode(Enum):
    """Vim editor modes."""
    NORMAL = "normal"
    INSERT = "insert"
    COMMAND = "command"
    VISUAL = "visual"


class VimModeIndicator(Static):
    """Widget to show current Vim mode."""

    DEFAULT_CSS = """
    VimModeIndicator {
        dock: bottom;
        height: 1;
        width: 8;
        padding: 0 1;
        background: $surface-darken-2;
    }

    VimModeIndicator.normal {
        color: $success;
    }

    VimModeIndicator.insert {
        color: $warning;
    }

    VimModeIndicator.command {
        color: $accent;
    }

    VimModeIndicator.visual {
        color: $secondary;
    }
    """

    mode: reactive[VimMode] = reactive(VimMode.NORMAL)
    enabled: reactive[bool] = reactive(False)

    def render(self) -> Text:
        """Render mode indicator."""
        if not self.enabled:
            return Text("")

        mode_text = {
            VimMode.NORMAL: "NORMAL",
            VimMode.INSERT: "INSERT",
            VimMode.COMMAND: "COMMAND",
            VimMode.VISUAL: "VISUAL",
        }

        text = mode_text.get(self.mode, "")
        return Text.from_markup(f"[bold]{text}[/]")

    def set_mode(self, mode: VimMode) -> None:
        """Set current mode and update class."""
        self.mode = mode
        self.set_class(mode.value)


class VimHandler:
    """Handle Vim-style keybindings."""

    def __init__(self, widget: Widget):
        self.widget = widget
        self.mode = VimMode.NORMAL
        self._command_buffer = ""
        self._enabled = False

    def enable(self) -> None:
        """Enable Vim mode."""
        self._enabled = True
        self.mode = VimMode.NORMAL

    def disable(self) -> None:
        """Disable Vim mode."""
        self._enabled = False

    def is_enabled(self) -> bool:
        """Check if Vim mode is enabled."""
        return self._enabled

    def handle_key(self, key: str) -> Optional[str]:
        """Handle a key press and return action if applicable."""
        if not self._enabled:
            return None

        if self.mode == VimMode.NORMAL:
            return self._handle_normal(key)
        elif self.mode == VimMode.INSERT:
            return self._handle_insert(key)
        elif self.mode == VimMode.COMMAND:
            return self._handle_command(key)

        return None

    def _handle_normal(self, key: str) -> Optional[str]:
        """Handle normal mode keys."""
        # Navigation
        if key == "j":
            return "scroll_down"
        elif key == "k":
            return "scroll_up"
        elif key == "g":
            return "scroll_top"
        elif key == "G":
            return "scroll_bottom"
        elif key == "ctrl+d":
            return "scroll_half_down"
        elif key == "ctrl+u":
            return "scroll_half_up"

        # Mode switching
        elif key == "i":
            self.mode = VimMode.INSERT
            return "enter_insert"
        elif key == "colon":
            self.mode = VimMode.COMMAND
            self._command_buffer = ""
            return "enter_command"
        elif key == "v":
            self.mode = VimMode.VISUAL
            return "enter_visual"

        # Actions
        elif key == "dd":
            return "delete_message"
        elif key == "yy":
            return "copy_message"
        elif key == "p":
            return "paste_message"
        elif key == "u":
            return "undo"

        return None

    def _handle_insert(self, key: str) -> Optional[str]:
        """Handle insert mode keys."""
        if key == "escape":
            self.mode = VimMode.NORMAL
            return "exit_insert"
        return None  # Let input handle other keys

    def _handle_command(self, key: str) -> Optional[str]:
        """Handle command mode keys."""
        if key == "escape":
            self.mode = VimMode.NORMAL
            return "exit_command"
        elif key == "enter":
            command = self._command_buffer
            self._command_buffer = ""
            self.mode = VimMode.NORMAL
            return self._execute_command(command)
        elif key == "backspace":
            self._command_buffer = self._command_buffer[:-1]
        else:
            self._command_buffer += key

        return None

    def _execute_command(self, command: str) -> Optional[str]:
        """Execute a Vim command."""
        if command == "q":
            return "quit"
        elif command == "q!":
            return "force_quit"
        elif command == "w":
            return "save"
        elif command == "wq":
            return "save_quit"
        elif command.startswith("theme "):
            theme_name = command[6:].strip()
            return f"set_theme:{theme_name}"
        elif command == "clear":
            return "clear"
        elif command.isdigit():
            return f"goto_line:{command}"

        return None


class StatusWidget(Static):
    """Enhanced status display widget."""

    DEFAULT_CSS = """
    StatusWidget {
        dock: bottom;
        height: 1;
        padding: 0 1;
        background: $surface-darken-3;
    }
    """

    status: reactive[str] = reactive("ready")
    model: reactive[str] = reactive("claude-sonnet-4-6")
    theme: reactive[str] = reactive("dark")
    vim_mode: reactive[str] = reactive("")

    def render(self) -> Text:
        """Render status."""
        status_colors = {
            "ready": "green",
            "thinking": "yellow",
            "streaming": "cyan",
            "error": "red",
        }
        color = status_colors.get(self.status, "white")

        parts = [
            f"[{color}]{self.status}[/]",
            f"Model: [cyan]{self.model}[/]",
            f"Theme: [dim]{self.theme}[/]",
        ]

        if self.vim_mode:
            parts.append(f"Vim: [accent]{self.vim_mode}[/]")

        return Text.from_markup(" │ ".join(parts))


class TokenCounterWidget(Static):
    """Token usage display with progress."""

    DEFAULT_CSS = """
    TokenCounterWidget {
        dock: bottom;
        height: 1;
        width: 20;
        padding: 0 1;
        background: $surface-darken-2;
    }
    """

    input_tokens: reactive[int] = reactive(0)
    output_tokens: reactive[int] = reactive(0)
    max_tokens: reactive[int] = reactive(8192)

    def render(self) -> Text:
        """Render token count."""
        total = self.input_tokens + self.output_tokens
        ratio = total / self.max_tokens if self.max_tokens > 0 else 0

        color = "green" if ratio < 0.5 else "yellow" if ratio < 0.8 else "red"

        return Text.from_markup(
            f"[{color}]{total}[/]/[dim]{self.max_tokens}[/] "
            f"([blue]{self.input_tokens}[/]/[green]{self.output_tokens}[/])"
        )


class ToolProgressWidget(Static):
    """Enhanced tool execution progress display."""

    DEFAULT_CSS = """
    ToolProgressWidget {
        margin: 1;
        padding: 1 2;
        background: $surface-darken-2;
        border: solid $primary;
    }

    ToolProgressWidget.running {
        border: solid yellow;
    }

    ToolProgressWidget.complete {
        border: solid green;
    }

    ToolProgressWidget.error {
        border: solid red;
    }
    """

    tool_name: reactive[str] = reactive("")
    status: reactive[str] = reactive("running")
    progress: reactive[int] = reactive(0)
    result_preview: reactive[str] = reactive("")

    def render(self) -> Text:
        """Render tool progress."""
        if self.status == "running":
            return Text.from_markup(
                f"[yellow]⏳ {self.tool_name}[/] "
                f"[dim]{self.progress}%[/]"
            )
        elif self.status == "complete":
            preview = self.result_preview[:50] if self.result_preview else ""
            return Text.from_markup(
                f"[green]✓ {self.tool_name}[/] "
                f"[dim]{preview}[/]"
            )
        elif self.status == "error":
            return Text.from_markup(
                f"[red]✗ {self.tool_name}[/] "
                f"[dim]{self.result_preview}[/]"
            )
        return Text(self.tool_name)


class MessageListWidget(Static):
    """Enhanced list of messages with formatting."""

    DEFAULT_CSS = """
    MessageListWidget {
        height: 1fr;
        overflow-y: auto;
        padding: 1;
    }
    """

    messages: reactive[list] = reactive([])

    def render(self) -> Text:
        """Render all messages."""
        lines = []
        for msg in self.messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            role_styles = {
                "user": ("blue", "You"),
                "assistant": ("green", "Claude"),
                "tool": ("cyan", "Tool"),
                "system": ("dim", "System"),
                "error": ("red", "Error"),
            }

            style, label = role_styles.get(role, ("white", role))
            lines.append(f"[bold {style}]{label}:[/] {content[:100]}")

        return Text.from_markup("\n".join(lines) if lines else "[dim]No messages[/]")

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the list."""
        self.messages.append({"role": role, "content": content})

    def clear(self) -> None:
        """Clear all messages."""
        self.messages = []


class CodeBlockWidget(Static):
    """Widget to display code with syntax highlighting."""

    DEFAULT_CSS = """
    CodeBlockWidget {
        margin: 1;
        padding: 1;
        background: $surface-darken-2;
        border: solid $secondary;
    }
    """

    code: reactive[str] = reactive("")
    language: reactive[str] = reactive("python")
    line_numbers: reactive[bool] = reactive(True)

    def render(self) -> Text:
        """Render code with syntax highlighting."""
        try:
            syntax = Syntax(
                self.code,
                self.language,
                line_numbers=self.line_numbers,
                theme="monokai",
            )
            return Text(str(syntax))
        except Exception:
            return Text(self.code)


class MarkdownWidget(Static):
    """Widget to render Markdown content."""

    DEFAULT_CSS = """
    MarkdownWidget {
        margin: 1;
        padding: 1 2;
    }
    """

    content: reactive[str] = reactive("")

    def render(self) -> Text:
        """Render Markdown."""
        try:
            md = Markdown(self.content)
            return Text(str(md))
        except Exception:
            return Text(self.content)


class HistoryBrowserWidget(Static):
    """Widget for browsing message history."""

    DEFAULT_CSS = """
    HistoryBrowserWidget {
        height: 1fr;
        overflow-y: auto;
    }
    """

    history: reactive[list] = reactive([])
    cursor: reactive[int] = reactive(0)

    def render(self) -> Text:
        """Render history browser."""
        lines = []
        for i, msg in enumerate(self.history):
            role = msg.get("role", "unknown")
            preview = msg.get("content", "")[:50]

            if i == self.cursor:
                lines.append(f"[reverse][{i}] {role}: {preview}[/]")
            else:
                lines.append(f"[dim][{i}] {role}:[/] {preview}")

        return Text.from_markup("\n".join(lines) if lines else "[dim]Empty history[/]")

    def move_cursor(self, delta: int) -> None:
        """Move cursor up or down."""
        new_cursor = self.cursor + delta
        self.cursor = max(0, min(len(self.history) - 1, new_cursor))

    def select_current(self) -> dict | None:
        """Get current selected message."""
        if self.cursor < len(self.history):
            return self.history[self.cursor]
        return None


class StatsTableWidget(Static):
    """Widget to display statistics in a table."""

    DEFAULT_CSS = """
    StatsTableWidget {
        height: auto;
        padding: 1;
    }
    """

    stats: reactive[dict] = reactive({})

    def render(self) -> Text:
        """Render stats table."""
        if not self.stats:
            return Text("[dim]No stats available[/]")

        table = Table(title="Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        for key, value in self.stats.items():
            table.add_row(key, str(value))

        return Text(str(table))


class ThemeSelectorWidget(Static):
    """Widget to select themes."""

    DEFAULT_CSS = """
    ThemeSelectorWidget {
        height: auto;
        padding: 1;
    }
    """

    current_theme: reactive[str] = reactive("dark")
    available_themes: reactive[list] = reactive(["dark", "light", "mono", "gruvbox", "nord", "dracula", "solarized"])

    def render(self) -> Text:
        """Render theme selector."""
        lines = ["[bold]Available Themes:[/]"]
        for theme in self.available_themes:
            if theme == self.current_theme:
                lines.append(f"  [reverse]{theme}[/]")
            else:
                lines.append(f"  [dim]{theme}[/]")

        return Text.from_markup("\n".join(lines))


class CommandPaletteWidget(Static):
    """Widget for command palette search."""

    DEFAULT_CSS = """
    CommandPaletteWidget {
        dock: top;
        height: 3;
        padding: 1;
        background: $surface-darken-2;
    }
    """

    query: reactive[str] = reactive("")
    results: reactive[list] = reactive([])
    selected: reactive[int] = reactive(0)

    COMMANDS = [
        ("/help", "Show help"),
        ("/clear", "Clear session"),
        ("/commit", "Git commit"),
        ("/review", "Code review"),
        ("/compact", "Compact context"),
        ("/doctor", "Run diagnostics"),
        ("/mcp", "MCP management"),
        ("/memory", "Memory management"),
        ("/sessions", "Session history"),
        ("/settings", "Settings"),
        ("/stats", "Statistics"),
        ("/theme", "Theme settings"),
        ("/vim", "Toggle Vim mode"),
    ]

    def render(self) -> Text:
        """Render command palette."""
        lines = [f"[bold]Command:[/] {self.query}"]

        filtered = [
            (cmd, desc)
            for cmd, desc in self.COMMANDS
            if cmd.startswith(self.query) or desc.lower().startswith(self.query.lower())
        ]

        for i, (cmd, desc) in enumerate(filtered[:5]):
            if i == self.selected:
                lines.append(f"  [reverse]{cmd}[/] - {desc}")
            else:
                lines.append(f"  {cmd} - [dim]{desc}[/]")

        return Text.from_markup("\n".join(lines))

    def update_query(self, query: str) -> None:
        """Update search query."""
        self.query = query
        self.selected = 0

    def move_selection(self, delta: int) -> None:
        """Move selection."""
        filtered = [
            cmd for cmd, _ in self.COMMANDS
            if cmd.startswith(self.query)
        ]
        self.selected = max(0, min(len(filtered) - 1, self.selected + delta))

    def get_selected_command(self) -> Optional[str]:
        """Get the selected command."""
        filtered = [
            cmd for cmd, _ in self.COMMANDS
            if cmd.startswith(self.query)
        ]
        if self.selected < len(filtered):
            return filtered[self.selected]
        return None


__all__ = [
    "ThemeType",
    "ThemeManager",
    "VimMode",
    "VimModeIndicator",
    "VimHandler",
    "StatusWidget",
    "TokenCounterWidget",
    "ToolProgressWidget",
    "MessageListWidget",
    "CodeBlockWidget",
    "MarkdownWidget",
    "HistoryBrowserWidget",
    "StatsTableWidget",
    "ThemeSelectorWidget",
    "CommandPaletteWidget",
]

# Import additional widgets
from .dialogs import (
    ConfirmDialog,
    InputDialog,
    ProgressDialog,
    ErrorDialog,
    HelpDialog,
    SettingsDialog,
    SelectDialog,
)

from .progress import (
    SpinnerProgress,
    BarProgress,
    MultiProgress,
    CircularProgress,
    StepProgress,
    AgentProgress,
    TaskProgress,
)

from .display import (
    MessageDisplay,
    CodeDisplay,
    MarkdownDisplay,
    TableDisplay,
    PanelDisplay,
    LogDisplay,
    StatsDisplay,
    CompactSummary,
)

__all__.extend([
    # Dialogs
    "ConfirmDialog",
    "InputDialog",
    "ProgressDialog",
    "ErrorDialog",
    "HelpDialog",
    "SettingsDialog",
    "SelectDialog",
    # Progress
    "SpinnerProgress",
    "BarProgress",
    "MultiProgress",
    "CircularProgress",
    "StepProgress",
    "AgentProgress",
    "TaskProgress",
    # Display
    "MessageDisplay",
    "CodeDisplay",
    "MarkdownDisplay",
    "TableDisplay",
    "PanelDisplay",
    "LogDisplay",
    "StatsDisplay",
    "CompactSummary",
])
