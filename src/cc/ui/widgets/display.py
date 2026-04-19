"""Display Components - Content display widgets."""

from __future__ import annotations
from textual.widget import Widget
from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.table import Table
from rich.panel import Panel


class MessageDisplay(Widget):
    """Display a single message."""

    DEFAULT_CSS = """
    MessageDisplay {
        margin: 1;
        padding: 1 2;
    }
    """

    role: reactive[str] = reactive("user")
    content: reactive[str] = reactive("")
    timestamp: reactive[str] = reactive("")
    metadata: reactive[dict] = reactive({})

    def render(self) -> Text:
        """Render message."""
        role_colors = {
            "user": "blue",
            "assistant": "green",
            "system": "dim",
            "tool": "cyan",
            "error": "red",
        }

        color = role_colors.get(self.role, "white")

        lines = [
            f"[bold {color}]{self.role}:[/] {self.content[:200]}",
        ]

        if self.timestamp:
            lines.append(f"[dim]{self.timestamp}[/]")

        return Text.from_markup("\n".join(lines))


class CodeDisplay(Widget):
    """Display code with syntax highlighting."""

    DEFAULT_CSS = """
    CodeDisplay {
        margin: 1;
        padding: 1;
        background: $surface-darken-2;
    }
    """

    code: reactive[str] = reactive("")
    language: reactive[str] = reactive("python")
    filename: reactive[str] = reactive("")
    line_numbers: reactive[bool] = reactive(True)

    def render(self) -> Text:
        """Render code."""
        try:
            syntax = Syntax(
                self.code,
                self.language,
                line_numbers=self.line_numbers,
                theme="monokai",
            )

            if self.filename:
                return Text.from_markup(
                    f"[dim]{self.filename}[/]\n{str(syntax)}"
                )

            return Text(str(syntax))
        except Exception:
            return Text(self.code)


class MarkdownDisplay(Widget):
    """Display Markdown content."""

    DEFAULT_CSS = """
    MarkdownDisplay {
        margin: 1;
        padding: 1 2;
    }
    """

    content: reactive[str] = reactive("")
    render_tables: reactive[bool] = reactive(True)

    def render(self) -> Text:
        """Render Markdown."""
        try:
            md = Markdown(self.content)
            return Text(str(md))
        except Exception:
            return Text(self.content)


class TableDisplay(Widget):
    """Display data in a table."""

    DEFAULT_CSS = """
    TableDisplay {
        height: auto;
        padding: 1;
    }
    """

    data: reactive[list] = reactive([])
    headers: reactive[list] = reactive([])
    title: reactive[str] = reactive("")

    def render(self) -> Text:
        """Render table."""
        if not self.headers and self.data:
            # Extract headers from first row
            self.headers = list(self.data[0].keys()) if isinstance(self.data[0], dict) else []

        table = Table(title=self.title)

        for header in self.headers:
            table.add_column(header, style="cyan")

        for row in self.data:
            if isinstance(row, dict):
                values = [str(row.get(h, "")) for h in self.headers]
            elif isinstance(row, (list, tuple)):
                values = [str(v) for v in row]
            else:
                values = [str(row)]

            table.add_row(*values)

        return Text(str(table))


class PanelDisplay(Widget):
    """Display content in a panel."""

    DEFAULT_CSS = """
    PanelDisplay {
        margin: 1;
        padding: 1;
    }
    """

    title: reactive[str] = reactive("")
    content: reactive[str] = reactive("")
    border_style: reactive[str] = reactive("blue")

    def render(self) -> Text:
        """Render panel."""
        panel = Panel(
            self.content,
            title=self.title,
            border_style=self.border_style,
        )
        return Text(str(panel))


class LogDisplay(Widget):
    """Display log entries."""

    DEFAULT_CSS = """
    LogDisplay {
        height: 10;
        overflow-y: auto;
        padding: 1;
    }
    """

    entries: reactive[list] = reactive([])
    max_entries: reactive[int] = reactive(50)

    def render(self) -> Text:
        """Render log."""
        lines = []
        for entry in self.entries[-self.max_entries:]:
            level = entry.get("level", "info")
            message = entry.get("message", "")
            timestamp = entry.get("timestamp", "")

            level_colors = {
                "debug": "dim",
                "info": "white",
                "warning": "yellow",
                "error": "red",
                "critical": "bold red",
            }

            color = level_colors.get(level, "white")

            if timestamp:
                lines.append(f"[dim]{timestamp}[/] [{color}]{level}[/] {message}")
            else:
                lines.append(f"[{color}]{level}[/] {message}")

        return Text.from_markup("\n".join(lines) if lines else "[dim]No logs[/]")

    def add_entry(self, level: str, message: str, timestamp: str = "") -> None:
        """Add log entry."""
        self.entries.append({
            "level": level,
            "message": message,
            "timestamp": timestamp,
        })


class StatsDisplay(Widget):
    """Display statistics."""

    DEFAULT_CSS = """
    StatsDisplay {
        height: auto;
        padding: 1;
    }
    """

    stats: reactive[dict] = reactive({})
    title: reactive[str] = reactive("Statistics")

    def render(self) -> Text:
        """Render stats."""
        if not self.stats:
            return Text("[dim]No stats[/]")

        lines = [f"[bold]{self.title}[/]"]

        for key, value in self.stats.items():
            if isinstance(value, dict):
                lines.append(f"[cyan]{key}:[/]")
                for k, v in value.items():
                    lines.append(f"  [dim]{k}[/]: {v}")
            elif isinstance(value, list):
                lines.append(f"[cyan]{key}:[/] {len(value)} items")
            else:
                lines.append(f"[cyan]{key}[/]: {value}")

        return Text.from_markup("\n".join(lines))


class CompactSummary(Widget):
    """Display compact summary."""

    DEFAULT_CSS = """
    CompactSummary {
        margin: 1;
        padding: 1;
        background: $surface-darken-1;
    }
    """

    original_tokens: reactive[int] = reactive(0)
    compacted_tokens: reactive[int] = reactive(0)
    messages_compacted: reactive[int] = reactive(0)
    strategy: reactive[str] = reactive("")

    def render(self) -> Text:
        """Render compact summary."""
        saved = self.original_tokens - self.compacted_tokens
        percent = int(saved / self.original_tokens * 100) if self.original_tokens > 0 else 0

        lines = [
            "[bold]Compact Summary[/]",
            f"[cyan]Strategy:[/] {self.strategy}",
            f"[cyan]Messages:[/] {self.messages_compacted}",
            f"[cyan]Tokens:[/] {self.original_tokens} → {self.compacted_tokens}",
            f"[green]Saved: {saved} ({percent}%)[/]",
        ]

        return Text.from_markup("\n".join(lines))


__all__ = [
    "MessageDisplay",
    "CodeDisplay",
    "MarkdownDisplay",
    "TableDisplay",
    "PanelDisplay",
    "LogDisplay",
    "StatsDisplay",
    "CompactSummary",
]
