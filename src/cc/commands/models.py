"""Models Command - Model management."""

from __future__ import annotations
from pathlib import Path
from rich.console import Console
from rich.table import Table

from ..utils.config import Config


AVAILABLE_MODELS = [
    ("claude-opus-4-7", "Opus 4.7", "Most powerful, best for complex tasks"),
    ("claude-opus-4-5", "Opus 4.5", "Previous Opus version"),
    ("claude-sonnet-4-6", "Sonnet 4.6", "Best for coding, balanced performance"),
    ("claude-haiku-4-5", "Haiku 4.5", "Fastest, good for simple tasks"),
    ("claude-haiku-3.5", "Haiku 3.5", "Legacy Haiku"),
]

MODEL_PRICING = {
    "claude-opus-4-7": {"input": 15.0, "output": 75.0},
    "claude-opus-4-5": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5": {"input": 0.25, "output": 1.25},
    "claude-haiku-3.5": {"input": 0.25, "output": 1.25},
}


def run_models(console: Console, action: str = "list", model: str = None) -> None:
    """Run models command."""
    if action == "list":
        list_models(console)
    elif action == "current":
        show_current_model(console)
    elif action == "set":
        set_model(console, model)
    elif action == "compare":
        compare_models(console)
    else:
        console.print(f"[red]Unknown action: {action}[/red]")


def list_models(console: Console) -> None:
    """List available models."""
    table = Table(title="Available Models")
    table.add_column("Model ID", style="cyan")
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Input $/M")
    table.add_column("Output $/M")

    for model_id, name, desc in AVAILABLE_MODELS:
        pricing = MODEL_PRICING.get(model_id, {"input": 0, "output": 0})
        table.add_row(
            model_id,
            name,
            desc,
            f"${pricing['input']}",
            f"${pricing['output']}",
        )

    console.print(table)


def show_current_model(console: Console) -> None:
    """Show current model."""
    config = Config()
    current = config.api.model

    # Find model info
    for model_id, name, desc in AVAILABLE_MODELS:
        if model_id == current:
            console.print("[bold]Current Model[/bold]")
            console.print(f"  ID: {model_id}")
            console.print(f"  Name: {name}")
            console.print(f"  Description: {desc}")
            return

    console.print(f"[bold]Current Model[/bold]: {current}")
    console.print("[dim]Unknown model[/dim]")


def set_model(console: Console, model: str) -> None:
    """Set model."""
    if not model:
        console.print("[red]Model ID required[/red]")
        return

    # Validate model
    valid_ids = [m[0] for m in AVAILABLE_MODELS]
    if model not in valid_ids:
        console.print(f"[red]Unknown model: {model}[/red]")
        console.print(f"[dim]Valid models: {', '.join(valid_ids)}[/dim]")
        return

    config = Config()
    config.api.model = model

    console.print(f"[green]Model set to: {model}[/green]")

    # Save to config
    config_path = Path.home() / ".claude" / "settings.json"
    import json
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps({"api": {"model": model}}, indent=2))


def compare_models(console: Console) -> None:
    """Compare model capabilities."""
    table = Table(title="Model Comparison")
    table.add_column("Feature", style="cyan")
    table.add_column("Opus")
    table.add_column("Sonnet")
    table.add_column("Haiku")

    features = [
        ("Coding Quality", "★★★★★", "★★★★★", "★★★★☆"),
        ("Speed", "★★☆☆☆", "★★★☆☆", "★★★★★"),
        ("Complex Tasks", "★★★★★", "★★★★☆", "★★☆☆☆"),
        ("Cost Efficiency", "★☆☆☆☆", "★★★★☆", "★★★★★"),
        ("Best For", "Architecture", "Development", "Quick tasks"),
    ]

    for feature, opus, sonnet, haiku in features:
        table.add_row(feature, opus, sonnet, haiku)

    console.print(table)


__all__ = ["run_models", "AVAILABLE_MODELS", "MODEL_PRICING"]