"""Screens package - Multiple screens for different functionality."""

from __future__ import annotations
from textual.binding import Binding
from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.widgets import Header, Footer, Static, Button, Label

from .screens import (
    HelpScreen,
    SessionsScreen,
    SessionLoadRequest,
    PluginsScreen,
    HooksScreen,
    SettingsScreen,
    StatsScreen,
    MessageHistoryScreen,
)


class DoctorScreen(Screen):
    """Diagnostic screen."""

    CSS = """
    DoctorScreen {
        layout: vertical;
    }

    #diagnostic-output {
        height: 1fr;
        overflow-y: auto;
        padding: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    def compose(self):
        yield Header()
        yield Container(
            VerticalScroll(
                Static("Running diagnostics...", id="diagnostic-output"),
            ),
            id="doctor-content",
        )
        yield Footer()

    def action_back(self) -> None:
        self.app.pop_screen()


class ConfigScreen(Screen):
    """Configuration screen."""

    CSS = """
    ConfigScreen {
        layout: vertical;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    def compose(self):
        yield Header()
        yield Container(
            Label("Configuration"),
            Static("Edit configuration here"),
            id="config-content",
        )
        yield Footer()

    def action_back(self) -> None:
        self.app.pop_screen()


__all__ = [
    "HelpScreen",
    "SessionsScreen",
    "SessionLoadRequest",
    "PluginsScreen",
    "HooksScreen",
    "SettingsScreen",
    "StatsScreen",
    "MessageHistoryScreen",
    "DoctorScreen",
    "ConfigScreen",
]
