"""Search Screen - Codebase search interface."""

from __future__ import annotations
import asyncio
from textual.widget import Widget
from textual.widgets import Static, Button, Input, ListView, ListItem, DataTable
from textual.reactive import reactive
from textual.message import Message
from textual.screen import Screen
from textual.binding import Binding
from textual.containers import Container, VerticalScroll, Horizontal
from rich.text import Text
from rich.syntax import Syntax


class SearchScreen(Screen):
    """Screen for searching codebase."""

    CSS = """
    SearchScreen {
        layout: vertical;
    }

    #search-input {
        height: 3;
        dock: top;
    }

    #search-results {
        height: 1fr;
    }

    #result-preview {
        height: 8;
        dock: bottom;
        background: $surface-darken-2;
        padding: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("enter", "search", "Search"),
        Binding("f", "files", "Files"),
        Binding("c", "content", "Content"),
        Binding("g", "grep", "Grep"),
    ]

    query: reactive[str] = reactive("")
    search_type: reactive[str] = reactive("content")  # files, content, grep
    results: reactive[list] = reactive([])
    selected_result: reactive[dict] = reactive({})
    result_index: reactive[int] = reactive(0)

    class SearchCompleted(Message):
        """Search completed."""
        query: str
        results: list

        def __init__(self, query: str, results: list):
            self.query = query
            self.results = results
            super().__init__()

    class ResultSelected(Message):
        """Result selected."""
        result: dict

        def __init__(self, result: dict):
            self.result = result
            super().__init__()

    def compose(self):
        """Compose screen."""
        yield Container(
            Input(value=self.query, placeholder="Search query...", id="search-input"),
            Horizontal(
                Button("Files", id="files"),
                Button("Content", id="content"),
                Button("Grep", id="grep"),
            ),
            id="search-input-container"
        )
        yield Static(f"[bold cyan]Search Results: {self.search_type}[/]")
        yield DataTable(id="search-results")
        yield Container(
            Static("", id="result-preview"),
            id="result-preview-container"
        )
        yield Static("[dim]Enter: Search | F: Files | C: Content | G: Grep[/]")

    def on_mount(self) -> None:
        """Setup table."""
        table = self.query_one("#search-results", DataTable)
        table.add_columns("File", "Line", "Preview", "Type")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search."""
        self.query = event.value
        self._perform_search()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button."""
        self.search_type = event.button.id

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle selection."""
        if event.row_index >= 0 and event.row_index < len(self.results):
            self.selected_result = self.results[event.row_index]
            self._show_preview()

    async def _perform_search(self) -> None:
        """Perform search."""
        # Would call actual search tools
        # Placeholder results
        self.results = [
            {"file": "src/main.py", "line": 10, "preview": "def main():", "type": "function"},
            {"file": "src/utils.py", "line": 5, "preview": "def helper():", "type": "function"},
        ]

        self._update_results()
        self.post_message(self.SearchCompleted(self.query, self.results))

    def _update_results(self) -> None:
        """Update results table."""
        table = self.query_one("#search-results", DataTable)
        table.clear()

        for result in self.results:
            table.add_row(
                result.get("file", ""),
                str(result.get("line", 0)),
                result.get("preview", "")[:40],
                result.get("type", ""),
            )

    def _show_preview(self) -> None:
        """Show result preview."""
        preview = self.query_one("#result-preview", Static)

        if self.selected_result:
            file_path = self.selected_result.get("file", "")
            line = self.selected_result.get("line", 0)
            preview_text = self.selected_result.get("preview", "")

            preview.update(f"""
[bold cyan]File: {file_path}[/]
[dim]Line: {line}[/]

[cyan]{preview_text}[/]
""")

    def action_search(self) -> None:
        """Search action."""
        self._perform_search()

    def action_files(self) -> None:
        """Files search."""
        self.search_type = "files"

    def action_content(self) -> None:
        """Content search."""
        self.search_type = "content"

    def action_grep(self) -> None:
        """Grep search."""
        self.search_type = "grep"

    def action_back(self) -> None:
        """Go back."""
        self.app.pop_screen()


class QuickSearchWidget(Widget):
    """Quick search widget for inline search."""

    DEFAULT_CSS = """
    QuickSearchWidget {
        dock: top;
        height: 3;
        width: 1fr;
        padding: 1;
        background: $surface-darken-2;
    }
    """

    query: reactive[str] = reactive("")
    results: reactive[list] = reactive([])
    searching: reactive[bool] = reactive(False)

    class SearchRequested(Message):
        """Search requested."""
        query: str

        def __init__(self, query: str):
            self.query = query
            super().__init__()

    class ResultSelected(Message):
        """Quick search result selected."""
        result: dict

        def __init__(self, result: dict):
            self.result = result
            super().__init__()

    def compose(self):
        """Compose widget."""
        yield Input(value=self.query, placeholder="Quick search...", id="quick-search")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input."""
        self.query = event.value
        self.post_message(self.SearchRequested(self.query))


class SearchResultWidget(Widget):
    """Single search result widget."""

    DEFAULT_CSS = """
    SearchResultWidget {
        height: 2;
        padding: 0 1;
        margin: 0 0 1 0;
        background: $surface-darken-1;
    }
    """

    file_path: reactive[str] = reactive("")
    line_number: reactive[int] = reactive(0)
    preview: reactive[str] = reactive("")
    match_type: reactive[str] = reactive("")

    def render(self) -> Text:
        """Render result."""
        return Text.from_markup(
            f"[cyan]{self.file_path}[/] [dim]:{self.line_number}[/]\n"
            f"  {self.preview[:60]}"
        )


__all__ = [
    "SearchScreen",
    "QuickSearchWidget",
    "SearchResultWidget",
]