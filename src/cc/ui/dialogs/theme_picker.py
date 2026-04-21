"""Theme Picker - Theme selection dialog."""

from __future__ import annotations
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass
from textual.widget import Widget
from textual.widgets import Static, ListView, ListItem, Label
from textual.reactive import reactive
from textual.message import Message
from textual.screen import ModalScreen
from textual.binding import Binding
from rich.text import Text


@dataclass
class ThemePreview:
    """Theme preview information."""
    name: str
    display_name: str
    description: str
    background_color: str
    primary_color: str
    text_color: str
    accent_color: str


AVAILABLE_THEMES = [
    ThemePreview(
        name="dark",
        display_name="Catppuccin Dark",
        description="Modern dark theme with vibrant colors",
        background_color="#1e1e2e",
        primary_color="#cba6f7",
        text_color="#cdd6f4",
        accent_color="#f9e2af",
    ),
    ThemePreview(
        name="light",
        display_name="Catppuccin Light",
        description="Light theme for daytime use",
        background_color="#eff1f5",
        primary_color="#8839ef",
        text_color="#4c4f69",
        accent_color="#df8e1d",
    ),
    ThemePreview(
        name="mono",
        display_name="Monochrome",
        description="Pure black and white theme",
        background_color="#000000",
        primary_color="#ffffff",
        text_color="#ffffff",
        accent_color="#ffffff",
    ),
    ThemePreview(
        name="gruvbox",
        display_name="Gruvbox Dark",
        description="Warm retro theme",
        background_color="#282828",
        primary_color="#fb4934",
        text_color="#ebdbb2",
        accent_color="#fabd2f",
    ),
    ThemePreview(
        name="nord",
        display_name="Nord",
        description="Arctic, bluish color palette",
        background_color="#2e3440",
        primary_color="#88c0d0",
        text_color="#eceff4",
        accent_color="#bf616a",
    ),
    ThemePreview(
        name="dracula",
        display_name="Dracula",
        description="Dark purple theme",
        background_color="#282a36",
        primary_color="#bd93f9",
        text_color="#f8f8f2",
        accent_color="#ff79c6",
    ),
    ThemePreview(
        name="solarized",
        display_name="Solarized Dark",
        description="Precision color science",
        background_color="#002b36",
        primary_color="#268bd2",
        text_color="#839496",
        accent_color="#cb4b16",
    ),
]


class ThemePickerDialog(ModalScreen):
    """Dialog for selecting a theme."""

    CSS = """
    ThemePickerDialog {
        align: center middle;
    }

    ThemePickerDialog > Container {
        width: 60;
        height: 20;
        background: $surface;
        border: solid cyan;
        padding: 2;
    }

    ListView {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "select", "Select"),
    ]

    current_theme: reactive[str] = reactive("dark")
    themes: reactive[list] = reactive([])
    preview_text: reactive[str] = reactive("")

    class Selected(Message):
        """Theme selected."""
        theme_name: str

        def __init__(self, theme_name: str):
            self.theme_name = theme_name
            super().__init__()

    def __init__(self, current_theme: str = None):
        super().__init__()
        if current_theme:
            self.current_theme = current_theme
        self.themes = AVAILABLE_THEMES

    def compose(self):
        """Compose dialog."""
        yield Static("[bold cyan]Select Theme[/]")
        yield ListView(
            *[ListItem(Label(f"{t.display_name} {'✓' if t.name == self.current_theme else ''}"))
              for t in self.themes],
            id="theme-list"
        )
        yield Static("")
        yield Static(self._get_preview_text(), id="preview")
        yield Static("[dim]Press Enter to apply[/]")

    def _get_preview_text(self) -> str:
        """Get preview text for selected theme."""
        return "Preview: This is how text will look in the selected theme"

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle selection."""
        idx = event.list_view.index
        if idx < len(self.themes):
            theme = self.themes[idx]
            self.post_message(self.Selected(theme.name))
            self.dismiss()

    def action_cancel(self) -> None:
        """Cancel."""
        self.dismiss()


class ThemePreviewWidget(Widget):
    """Widget showing theme preview."""

    DEFAULT_CSS = """
    ThemePreviewWidget {
        width: 40;
        height: 10;
        padding: 1;
    }
    """

    theme_name: reactive[str] = reactive("dark")

    def render(self) -> Text:
        """Render theme preview."""
        # Find theme
        theme = None
        for t in AVAILABLE_THEMES:
            if t.name == self.theme_name:
                theme = t
                break

        if not theme:
            return Text(f"[dim]Unknown theme: {self.theme_name}[/]")

        # Show preview panel
        preview_lines = [
            f"[bold]Theme: {theme.display_name}[/]",
            f"[dim]{theme.description}[/]",
            "",
            "Preview:",
            "  [primary]Primary Color[/]",
            "  [accent]Accent Color[/]",
            "  [success]Success (green)[/]",
            "  [warning]Warning (yellow)[/]",
            "  [error]Error (red)[/]",
        ]

        return Text.from_markup("\n".join(preview_lines))


def get_theme_css(theme_name: str) -> str:
    """Get CSS variables for a theme."""
    theme = None
    for t in AVAILABLE_THEMES:
        if t.name == theme_name:
            theme = t
            break

    if not theme:
        return ""

    return f"""
    $surface: {theme.background_color};
    $primary: {theme.primary_color};
    $text: {theme.text_color};
    $accent: {theme.accent_color};
    """


__all__ = [
    "ThemePreview",
    "ThemePickerDialog",
    "ThemePreviewWidget",
    "AVAILABLE_THEMES",
    "get_theme_css",
]