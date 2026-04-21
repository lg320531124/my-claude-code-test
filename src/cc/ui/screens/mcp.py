"""MCP Screen - MCP server management interface."""

from __future__ import annotations
from textual.widgets import Static, DataTable, Tree
from textual.reactive import reactive
from textual.message import Message
from textual.screen import Screen
from textual.binding import Binding
from textual.containers import Container


class MCPScreen(Screen):
    """Screen for MCP server management."""

    CSS = """
    MCPScreen {
        layout: vertical;
    }

    #server-list {
        height: 8;
    }

    #server-tools {
        height: 1fr;
    }

    #server-info {
        height: 5;
        dock: bottom;
        background: $surface-darken-2;
        padding: 1;
    }
    """

    BINDINGS = [
        Binding("a", "add", "Add Server"),
        Binding("r", "remove", "Remove"),
        Binding("c", "connect", "Connect"),
        Binding("d", "disconnect", "Disconnect"),
        Binding("t", "tools", "Tools"),
        Binding("escape", "back", "Back"),
    ]

    servers: reactive[list] = reactive([])
    selected_server: reactive[str] = reactive("")
    server_status: reactive[dict] = reactive({})
    available_tools: reactive[list] = reactive([])

    class ServerAdded(Message):
        """Server added."""
        config: dict

        def __init__(self, config: dict):
            self.config = config
            super().__init__()

    class ServerRemoved(Message):
        """Server removed."""
        server_name: str

        def __init__(self, server_name: str):
            self.server_name = server_name
            super().__init__()

    class ServerConnected(Message):
        """Server connected."""
        server_name: str

        def __init__(self, server_name: str):
            self.server_name = server_name
            super().__init__()

    class ServerDisconnected(Message):
        """Server disconnected."""
        server_name: str

        def __init__(self, server_name: str):
            self.server_name = server_name
            super().__init__()

    def compose(self):
        """Compose screen."""
        yield Static("[bold cyan]MCP Server Management[/]")
        yield DataTable(id="server-list")
        yield Static("[bold cyan]Available Tools[/]")
        yield Tree("Tools", id="server-tools")
        yield Container(
            Static("", id="server-info"),
            id="server-info-container"
        )
        yield Static("[dim]A: Add | R: Remove | C: Connect | D: Disconnect | T: Tools[/]")

    def on_mount(self) -> None:
        """Populate screen."""
        self._populate_servers()

    def _populate_servers(self) -> None:
        """Populate server list."""
        table = self.query_one("#server-list", DataTable)
        table.add_columns("Name", "Command", "Status", "Tools", "Connected")

        for server in self.servers:
            name = server.get("name", "")
            status = self.server_status.get(name, "stopped")
            tools_count = len(server.get("tools", []))
            connected = "✓" if status == "connected" else ""

            table.add_row(name, server.get("command", ""), status, tools_count, connected)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection."""
        if event.row_index >= 0 and event.row_index < len(self.servers):
            self.selected_server = self.servers[event.row_index].get("name", "")
            self._show_server_info()

    def _show_server_info(self) -> None:
        """Show selected server info."""
        info = self.query_one("#server-info", Static)

        if self.selected_server:
            server = next(
                (s for s in self.servers if s.get("name") == self.selected_server),
                {}
            )
            status = self.server_status.get(self.selected_server, "stopped")
            tools = server.get("tools", [])

            info_text = f"""
[cyan]Server: {self.selected_server}[/]
[dim]Status: {status}[/]
[dim]Tools: {len(tools)}[/]
[dim]Command: {server.get('command', '')}[/]
"""
            info.update(info_text)

            # Update tools tree
            self._populate_tools(tools)

    def _populate_tools(self, tools: list) -> None:
        """Populate tools tree."""
        tree = self.query_one("#server-tools", Tree)
        tree.clear()

        for tool in tools:
            name = tool.get("name", "")
            description = tool.get("description", "")
            tree.root.add(f"[cyan]{name}[/]", data=description)

    def action_add(self) -> None:
        """Add server action."""
        # Would open add dialog
        pass

    def action_remove(self) -> None:
        """Remove server."""
        if self.selected_server:
            self.post_message(self.ServerRemoved(self.selected_server))
            self.selected_server = ""
            self._populate_servers()

    def action_connect(self) -> None:
        """Connect server."""
        if self.selected_server:
            self.post_message(self.ServerConnected(self.selected_server))

    def action_disconnect(self) -> None:
        """Disconnect server."""
        if self.selected_server:
            self.post_message(self.ServerDisconnected(self.selected_server))

    def action_tools(self) -> None:
        """Show tools."""
        # Would expand tools tree
        pass

    def action_back(self) -> None:
        """Go back."""
        self.app.pop_screen()


class MCPToolExplorerScreen(Screen):
    """Screen for exploring MCP tools."""

    CSS = """
    MCPToolExplorerScreen {
        layout: vertical;
    }

    #tools-list {
        height: 1fr;
    }

    #tool-detail {
        height: 10;
        dock: bottom;
        background: $surface-darken-2;
        padding: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("enter", "select", "Select"),
    ]

    tools: reactive[list] = reactive([])
    selected_tool: reactive[str] = reactive("")
    server_name: reactive[str] = reactive("")

    def compose(self):
        """Compose screen."""
        yield Static(f"[bold cyan]MCP Tools: {self.server_name}[/]")
        yield DataTable(id="tools-list")
        yield Container(
            Static("", id="tool-detail"),
            id="tool-detail-container"
        )

    def on_mount(self) -> None:
        """Populate tools."""
        table = self.query_one("#tools-list", DataTable)
        table.add_columns("Tool", "Description", "Input Schema")

        for tool in self.tools:
            name = tool.get("name", "")
            description = tool.get("description", "")[:50]
            schema_type = tool.get("inputSchema", {}).get("type", "object")

            table.add_row(name, description, schema_type)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle selection."""
        if event.row_index >= 0 and event.row_index < len(self.tools):
            self.selected_tool = self.tools[event.row_index].get("name", "")
            self._show_tool_detail()

    def _show_tool_detail(self) -> None:
        """Show tool details."""
        detail = self.query_one("#tool-detail", Static)

        tool = next(
            (t for t in self.tools if t.get("name") == self.selected_tool),
            {}
        )

        description = tool.get("description", "")
        schema = tool.get("inputSchema", {})

        required = schema.get("required", [])
        properties = schema.get("properties", {})

        detail_text = f"""
[bold cyan]Tool: {self.selected_tool}[/]
[dim]{description}[/]

[bold]Parameters:[/]
"""
        for prop_name, prop_info in properties.items():
            required_marker = "*" if prop_name in required else ""
            prop_type = prop_info.get("type", "any")
            detail_text += f"  [cyan]{prop_name}{required_marker}[/]: {prop_type}\n"

        detail.update(detail_text)

    def action_back(self) -> None:
        """Go back."""
        self.app.pop_screen()


__all__ = [
    "MCPScreen",
    "MCPToolExplorerScreen",
]