"""MCP Server Dialog - MCP server management dialogs."""

from __future__ import annotations
from textual.widgets import Static, Button, Input, DataTable
from textual.reactive import reactive
from textual.message import Message
from textual.screen import ModalScreen, Screen
from textual.binding import Binding


class MCPServerDialog(ModalScreen):
    """Dialog for adding/configuring MCP servers."""

    CSS = """
    MCPServerDialog {
        align: center middle;
    }

    MCPServerDialog > Container {
        width: 70;
        height: 25;
        background: $surface;
        border: solid cyan;
        padding: 2;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "save", "Save"),
    ]

    server_name: reactive[str] = reactive("")
    server_command: reactive[str] = reactive("")
    server_args: reactive[str] = reactive("")
    server_env: reactive[str] = reactive("")
    server_cwd: reactive[str] = reactive("")
    server_timeout: reactive[int] = reactive(30)

    class Saved(Message):
        """Server configuration saved."""
        config: dict

        def __init__(self, config: dict):
            self.config = config
            super().__init__()

    class Cancelled(Message):
        """Dialog cancelled."""

    def compose(self):
        """Compose dialog."""
        yield Static("[bold cyan]Add MCP Server[/]")
        yield Static("")
        yield Static("[cyan]Server Name:[/]")
        yield Input(value=self.server_name, placeholder="my-server")
        yield Static("[cyan]Command:[/]")
        yield Input(value=self.server_command, placeholder="node server.js")
        yield Static("[cyan]Arguments:[/]")
        yield Input(value=self.server_args, placeholder="--port 3000")
        yield Static("[cyan]Environment Variables:[/]")
        yield Input(value=self.server_env, placeholder="KEY=value")
        yield Static("[cyan]Working Directory:[/]")
        yield Input(value=self.server_cwd, placeholder="/path/to/server")
        yield Static("[cyan]Timeout (seconds):[/]")
        yield Input(value=str(self.server_timeout), placeholder="30")
        yield Static("")
        yield Button("Add Server", id="save", variant="success")
        yield Button("Cancel", id="cancel", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "save":
            config = {
                "name": self.query_one(Input).value,
                "command": self.query(Input)[1].value,
                "args": self.query(Input)[2].value.split(),
                "env": self._parse_env(self.query(Input)[3].value),
                "cwd": self.query(Input)[4].value,
                "timeout": int(self.query(Input)[5].value or "30"),
            }
            self.post_message(self.Saved(config))
            self.dismiss()
        else:
            self.post_message(self.Cancelled())
            self.dismiss()

    def _parse_env(self, env_str: str) -> dict:
        """Parse environment string."""
        env = {}
        for part in env_str.split():
            if "=" in part:
                key, value = part.split("=", 1)
                env[key] = value
        return env

    def action_save(self) -> None:
        """Save action."""
        self.on_button_pressed(Button.Pressed(button=self.query_one("#save", Button)))

    def action_cancel(self) -> None:
        """Cancel action."""
        self.dismiss()


class MCPServerApproval(ModalScreen):
    """Approval dialog for MCP server trust."""

    CSS = """
    MCPServerApproval {
        align: center middle;
    }

    MCPServerApproval > Container {
        width: 60;
        height: 18;
        background: $surface;
        border: solid yellow;
        padding: 2;
    }
    """

    server_name: reactive[str] = reactive("")
    server_command: reactive[str] = reactive("")
    tools_count: reactive[int] = reactive(0)
    resources_count: reactive[int] = reactive(0)
    warnings: reactive[list] = reactive([])

    class Approved(Message):
        """Server approved."""
        server_name: str
        trust_level: str  # "full", "limited", "readonly"

        def __init__(self, server_name: str, trust_level: str):
            self.server_name = server_name
            self.trust_level = trust_level
            super().__init__()

    class Rejected(Message):
        """Server rejected."""
        server_name: str

        def __init__(self, server_name: str):
            self.server_name = server_name
            super().__init__()

    def compose(self):
        """Compose approval dialog."""
        yield Static("[bold yellow]MCP Server Trust Request[/]")
        yield Static("")
        yield Static(f"[cyan]Server:[/] {self.server_name}")
        yield Static(f"[dim]Command: {self.server_command}[/]")
        yield Static(f"[cyan]Tools: {self.tools_count} | Resources: {self.resources_count}[/]")
        yield Static("")
        yield Static("[yellow]This server requests access to:[/]")
        yield Static("  • File system read/write")
        yield Static("  • Tool execution")
        yield Static("  • External API calls")
        yield Static("")
        if self.warnings:
            yield Static("[red]Warnings:[/]")
            for warning in self.warnings[:3]:
                yield Static(f"  • {warning}")
        yield Static("")
        yield Button("Full Trust", id="full", variant="success")
        yield Button("Limited Trust", id="limited", variant="warning")
        yield Button("Reject", id="reject", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "reject":
            self.post_message(self.Rejected(self.server_name))
        else:
            self.post_message(self.Approved(self.server_name, event.button.id))
        self.dismiss()


class MCPServerListScreen(Screen):
    """Screen for listing MCP servers."""

    CSS = """
    MCPServerListScreen {
        layout: vertical;
    }

    DataTable {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("a", "add", "Add"),
        Binding("r", "remove", "Remove"),
        Binding("e", "edit", "Edit"),
        Binding("escape", "back", "Back"),
    ]

    servers: reactive[list] = reactive([])

    def compose(self):
        """Compose screen."""
        yield Static("[bold cyan]MCP Servers[/]")
        yield DataTable(id="servers-table")
        yield Static("[dim]Press A to add, R to remove, E to edit[/]")

    def on_mount(self) -> None:
        """Populate table."""
        table = self.query_one("#servers-table", DataTable)
        table.add_columns("Name", "Command", "Status", "Tools", "Resources")
        for server in self.servers:
            table.add_row(
                server.get("name", ""),
                server.get("command", ""),
                server.get("status", "stopped"),
                server.get("tools_count", 0),
                server.get("resources_count", 0),
            )

    def action_add(self) -> None:
        """Add new server."""
        self.app.push_screen(MCPServerDialog())

    def action_remove(self) -> None:
        """Remove selected server."""
        table = self.query_one("#servers-table", DataTable)
        if table.cursor_row >= 0:
            # Would remove server
            pass

    def action_edit(self) -> None:
        """Edit selected server."""
        table = self.query_one("#servers-table", DataTable)
        if table.cursor_row >= 0:
            # Would edit server
            pass

    def action_back(self) -> None:
        """Go back."""
        self.app.pop_screen()


__all__ = [
    "MCPServerDialog",
    "MCPServerApproval",
    "MCPServerListScreen",
]