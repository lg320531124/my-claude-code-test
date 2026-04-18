"""Screens for TUI."""

from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Static, Button, Label


class DoctorScreen(Screen):
    """Diagnostic screen."""

    def compose(self):
        yield Header()
        yield Container(
            Static("Running diagnostics...", id="diagnostic-output"),
            id="doctor-content",
        )
        yield Footer()


class ConfigScreen(Screen):
    """Configuration screen."""

    def compose(self):
        yield Header()
        yield Container(
            Label("Configuration"),
            Static("Edit configuration here"),
            id="config-content",
        )
        yield Footer()


class HelpScreen(Screen):
    """Help screen."""

    def compose(self):
        yield Header()
        yield Container(
            Static(self._get_help_content()),
            id="help-content",
        )
        yield Footer()

    def _get_help_content(self) -> str:
        return """
# Claude Code Python Help

## Commands
- /help - Show help
- /commit [msg] - Create git commit
- /review - Review changes
- /compact - Compress context
- /doctor - Diagnostics
- /mcp - MCP management
- /memory - Memory management
- /skills - Skill management
- /clear - Clear session
- /exit - Exit

## Shortcuts
- Ctrl+C - Quit
- Ctrl+L - Clear
- Ctrl+D - Doctor
- Ctrl+H - Help

## Tools Available
- Bash - Run shell commands
- Read - Read files
- Write - Write files
- Edit - Edit files
- Glob - Find files
- Grep - Search content
- WebFetch - Fetch URLs
- WebSearch - Search web
- Task - Task management
"""