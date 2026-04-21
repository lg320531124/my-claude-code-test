"""Model Picker - Model selection dialog."""

from __future__ import annotations
from dataclasses import dataclass
from textual.widget import Widget
from textual.widgets import Static, Button, DataTable
from textual.reactive import reactive
from textual.message import Message
from textual.screen import ModalScreen
from textual.binding import Binding
from rich.text import Text


@dataclass
class ModelInfo:
    """Model information."""
    name: str
    display_name: str
    family: str  # "opus", "sonnet", "haiku"
    max_tokens: int
    input_price: float  # per 1M tokens
    output_price: float  # per 1M tokens
    features: list  # ["vision", "code", "extended_thinking"]
    recommended_for: list  # ["coding", "analysis", "fast_response"]


AVAILABLE_MODELS = [
    ModelInfo(
        name="claude-opus-4-7",
        display_name="Claude Opus 4.7",
        family="opus",
        max_tokens=200000,
        input_price=15.0,
        output_price=75.0,
        features=["vision", "code", "extended_thinking", "tools"],
        recommended_for=["complex_reasoning", "analysis", "architecture"],
    ),
    ModelInfo(
        name="claude-sonnet-4-6",
        display_name="Claude Sonnet 4.6",
        family="sonnet",
        max_tokens=200000,
        input_price=3.0,
        output_price=15.0,
        features=["vision", "code", "extended_thinking", "tools"],
        recommended_for=["coding", "development", "multi_agent"],
    ),
    ModelInfo(
        name="claude-haiku-4-5",
        display_name="Claude Haiku 4.5",
        family="haiku",
        max_tokens=200000,
        input_price=0.80,
        output_price=4.0,
        features=["vision", "code", "tools"],
        recommended_for=["fast_response", "lightweight_agents", "pair_programming"],
    ),
    ModelInfo(
        name="claude-3-5-sonnet",
        display_name="Claude 3.5 Sonnet",
        family="sonnet",
        max_tokens=200000,
        input_price=3.0,
        output_price=15.0,
        features=["vision", "code", "tools"],
        recommended_for=["coding", "general"],
    ),
]


class ModelPickerDialog(ModalScreen):
    """Dialog for selecting a Claude model."""

    CSS = """
    ModelPickerDialog {
        align: center middle;
    }

    ModelPickerDialog > Container {
        width: 80;
        height: 30;
        background: $surface;
        border: solid cyan;
        padding: 2;
    }

    DataTable {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "select", "Select"),
        Binding("j", "down", "Down"),
        Binding("k", "up", "Up"),
    ]

    current_model: reactive[str] = reactive("claude-sonnet-4-6")
    models: reactive[list] = reactive([])
    selected_index: reactive[int] = reactive(0)

    class Selected(Message):
        """Model selected."""
        model_name: str

        def __init__(self, model_name: str):
            self.model_name = model_name
            super().__init__()

    def __init__(self, current_model: str = None):
        super().__init__()
        if current_model:
            self.current_model = current_model
        self.models = AVAILABLE_MODELS

    def compose(self):
        """Compose dialog."""
        yield Static("[bold cyan]Select Model[/]")
        yield DataTable(id="models-table")
        yield Static("")
        yield Static("[dim]Press Enter to select, Escape to cancel[/]")

    def on_mount(self) -> None:
        """Populate table."""
        table = self.query_one("#models-table", DataTable)
        table.add_columns("Model", "Max Tokens", "Input Price", "Output Price", "Features")

        for i, model in enumerate(self.models):
            # Highlight current model
            if model.name == self.current_model:
                self.selected_index = i

            table.add_row(
                f"{model.display_name} {'✓' if model.name == self.current_model else ''}",
                str(model.max_tokens),
                f"${model.input_price}/M",
                f"${model.output_price}/M",
                ", ".join(model.features[:3]),
            )

        table.cursor_row = self.selected_index

    def action_select(self) -> None:
        """Select current row."""
        table = self.query_one("#models-table", DataTable)
        if table.cursor_row >= 0 and table.cursor_row < len(self.models):
            model = self.models[table.cursor_row]
            self.post_message(self.Selected(model.name))
            self.dismiss()

    def action_cancel(self) -> None:
        """Cancel selection."""
        self.dismiss()

    def action_down(self) -> None:
        """Move down."""
        table = self.query_one("#models-table", DataTable)
        table.action_cursor_down()

    def action_up(self) -> None:
        """Move up."""
        table = self.query_one("#models-table", DataTable)
        table.action_cursor_up()


class ModelInfoWidget(Widget):
    """Widget displaying current model info."""

    DEFAULT_CSS = """
    ModelInfoWidget {
        width: 30;
        height: auto;
        padding: 1;
        background: $surface-darken-2;
    }
    """

    model_name: reactive[str] = reactive("claude-sonnet-4-6")

    def render(self) -> Text:
        """Render model info."""
        # Find model
        model = None
        for m in AVAILABLE_MODELS:
            if m.name == self.model_name:
                model = m
                break

        if not model:
            return Text(f"[dim]{self.model_name}[/]")

        # Family color
        family_colors = {
            "opus": "purple",
            "sonnet": "cyan",
            "haiku": "green",
        }

        color = family_colors.get(model.family, "white")

        lines = [
            f"[bold {color}]{model.display_name}[/]",
            f"[dim]Max: {model.max_tokens} tokens[/]",
            f"[dim]In: ${model.input_price}/M[/]",
            f"[dim]Out: ${model.output_price}/M[/]",
        ]

        return Text.from_markup("\n".join(lines))


__all__ = [
    "ModelInfo",
    "ModelPickerDialog",
    "ModelInfoWidget",
    "AVAILABLE_MODELS",
]