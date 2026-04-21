"""Permission Dialogs - Permission confirmation dialogs."""

from __future__ import annotations
from textual.widget import Widget
from textual.widgets import Static, Button, Input
from textual.reactive import reactive
from textual.message import Message
from textual.screen import ModalScreen
from rich.text import Text


class PermissionDialog(ModalScreen):
    """Modal permission confirmation dialog."""

    CSS = """
    PermissionDialog {
        align: center middle;
    }

    PermissionDialog > Container {
        width: 60;
        height: 15;
        background: $surface;
        border: solid yellow;
        padding: 2;
    }
    """

    tool_name: reactive[str] = reactive("")
    tool_input: reactive[dict] = reactive({})
    risk_level: reactive[str] = reactive("medium")
    explanation: reactive[str] = reactive("")
    command_preview: reactive[str] = reactive("")
    pattern_suggestion: reactive[str] = reactive("")
    allow_pattern: reactive[bool] = reactive(False)

    class Approved(Message):
        """Permission approved."""
        tool_name: str
        remember_pattern: str | None

        def __init__(self, tool_name: str, remember_pattern: str | None = None):
            self.tool_name = tool_name
            self.remember_pattern = remember_pattern
            super().__init__()

    class Rejected(Message):
        """Permission rejected."""
        tool_name: str

        def __init__(self, tool_name: str):
            self.tool_name = tool_name
            super().__init__()

    def compose(self):
        """Compose dialog."""
        risk_colors = {"low": "green", "medium": "yellow", "high": "red"}
        color = risk_colors.get(self.risk_level, "yellow")

        yield Static(f"[bold {color}]Permission Required[/]", classes="title")
        yield Static(f"[cyan]Tool:[/] {self.tool_name}")
        yield Static(f"[{color}]Risk: {self.risk_level.upper()}[/]")
        yield Static(self.explanation)
        yield Static(f"[dim]Preview: {self.command_preview[:80]}[/]")
        yield Static("")
        yield Static(f"[dim]Pattern: {self.pattern_suggestion}[/]")
        yield Static("")
        yield Button("Approve", id="approve", variant="success")
        yield Button("Reject", id="reject", variant="error")
        yield Button("Always Allow", id="always", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "approve":
            self.post_message(self.Approved(self.tool_name))
            self.dismiss()
        elif event.button.id == "reject":
            self.post_message(self.Rejected(self.tool_name))
            self.dismiss()
        elif event.button.id == "always":
            pattern = self.pattern_suggestion or self.tool_name
            self.post_message(self.Approved(self.tool_name, pattern))
            self.dismiss()


class BashPermissionDialog(PermissionDialog):
    """Permission dialog for Bash commands."""

    command: reactive[str] = reactive("")
    sandbox_mode: reactive[bool] = reactive(False)
    timeout_seconds: reactive[int] = reactive(120)

    def compose(self):
        """Compose Bash permission dialog."""
        self._analyze_command()

        risk_colors = {"low": "green", "medium": "yellow", "high": "red"}
        color = risk_colors.get(self.risk_level, "yellow")

        yield Static(f"[bold {color}]Bash Command[/]", classes="title")
        yield Static(f"[cyan]Command:[/] {self.command[:100]}")
        yield Static(f"[{color}]Risk: {self.risk_level.upper()}[/]")
        yield Static(f"[dim]Sandbox: {self.sandbox_mode} | Timeout: {self.timeout_seconds}s[/]")
        yield Static(self.explanation)
        yield Static("")
        yield Button("Execute", id="approve", variant="success")
        yield Button("Cancel", id="reject", variant="error")
        yield Button("Always Allow", id="always", variant="primary")

    def _analyze_command(self) -> None:
        """Analyze command for risk level."""
        dangerous_patterns = [
            "rm -rf", "sudo", "chmod", "chown", "mkfs", "dd",
            "> /dev/", "curl | bash", "wget | bash", "format",
        ]

        for pattern in dangerous_patterns:
            if pattern in self.command:
                self.risk_level = "high"
                self.explanation = f"[red]Contains dangerous pattern: {pattern}[/]"
                return

        write_patterns = ["write", "save", "create", "mkdir", "touch", "mv", "cp"]
        for pattern in write_patterns:
            if pattern in self.command.lower():
                self.risk_level = "medium"
                self.explanation = "Command may modify files"
                return

        self.risk_level = "low"
        self.explanation = "[green]Command appears safe[/]"

        # Generate pattern suggestion
        cmd_parts = self.command.split()
        if cmd_parts:
            self.pattern_suggestion = f"Bash({cmd_parts[0]} *)"


class MCPPermissionDialog(PermissionDialog):
    """Permission dialog for MCP server connections."""

    server_name: reactive[str] = reactive("")
    server_command: reactive[str] = reactive("")
    server_args: reactive[list] = reactive([])
    capabilities: reactive[list] = reactive([])

    def compose(self):
        """Compose MCP permission dialog."""
        yield Static("[bold yellow]MCP Server Connection[/]", classes="title")
        yield Static(f"[cyan]Server:[/] {self.server_name}")
        yield Static(f"[dim]Command: {self.server_command}[/]")
        yield Static("")
        yield Static("[cyan]Capabilities:[/]")
        for cap in self.capabilities[:5]:
            yield Static(f"  • {cap}")
        yield Static("")
        yield Static("[yellow]This server can access files and execute tools[/]")
        yield Static("")
        yield Button("Connect", id="approve", variant="success")
        yield Button("Reject", id="reject", variant="error")
        yield Button("Always Allow", id="always", variant="primary")


__all__ = [
    "PermissionDialog",
    "BashPermissionDialog",
    "MCPPermissionDialog",
]