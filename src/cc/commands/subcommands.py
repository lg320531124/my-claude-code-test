"""CLI subcommands: init, config, version."""

from __future__ import annotations
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from ..utils.config import Config
from ..types.permission import PermissionDecision

console = Console()


@click.command()
@click.option("--force", "-f", is_flag=True, help="Overwrite existing config")
@click.option("--template", "-t", type=click.Choice(["default", "minimal", "full"]), default="default")
def init_cmd(force: bool, template: str) -> None:
    """Initialize project configuration."""
    cwd = Path.cwd()
    config_dir = cwd / ".claude"
    config_file = config_dir / "config.json"

    if config_file.exists() and not force:
        console.print("[yellow]Configuration already exists[/yellow]")
        console.print("Use --force to overwrite")
        return

    # Create directory
    config_dir.mkdir(parents=True, exist_ok=True)

    # Generate config based on template
    config = Config()

    if template == "minimal":
        config.permissions.allow = ["Read", "Glob", "Grep"]
        config.permissions.ask = ["Write", "Edit", "Bash"]
        config.permissions.deny = ["Bash(rm -rf /*)"]
    elif template == "full":
        config.permissions.allow = [
            "Read", "Glob", "Grep", "WebFetch", "WebSearch",
            "TaskCreate", "TaskList",
            "Bash(ls *)", "Bash(cat *)", "Bash(git status *)",
        ]
        config.permissions.ask = ["Write", "Edit"]
        config.permissions.deny = ["Bash(rm -rf /*)", "Bash(sudo *)"]
    else:  # default
        pass  # Use defaults from Config class

    # Interactive model selection
    console.print("\n[bold]Model Selection[/bold]")
    models = [
        ("claude-sonnet-4-6", "Sonnet 4.6 (recommended for coding)"),
        ("claude-opus-4-5", "Opus 4.5 (most capable)"),
        ("claude-haiku-4-5", "Haiku 4.5 (fastest)"),
        ("glm-4-plus", "GLM-4 Plus (智谱)"),
        ("deepseek-chat", "DeepSeek Chat"),
    ]

    table = Table(title="Available Models")
    table.add_column("#", style="cyan")
    table.add_column("Model")
    table.add_column("Description")

    for i, (model, desc) in enumerate(models, 1):
        table.add_row(str(i), model, desc)

    console.print(table)

    choice = Prompt.ask(
        "Select model",
        choices=[str(i) for i in range(1, len(models) + 1)],
        default="1",
    )

    config.api.model = models[int(choice) - 1][0]

    # API key setup
    console.print("\n[bold]API Key[/bold]")
    console.print("Set your API key via environment variable:")
    if config.api.model.startswith("claude"):
        console.print("  export ANTHROPIC_API_KEY=your-key")
    elif config.api.model.startswith("glm"):
        console.print("  export ZHIPU_API_KEY=your-key")
    else:
        console.print("  export OPENAI_API_KEY=your-key")

    # Save config
    config.save_to_file(config_file)

    console.print(f"\n[green]✓ Configuration created: {config_file}[/green]")
    console.print("\n[dim]Next steps:[/dim]")
    console.print("  1. Set your API key")
    console.print("  2. Run 'cc' to start the REPL")
    console.print("  3. Use '/help' for commands")


@click.command()
@click.argument("key", required=False)
@click.argument("value", required=False)
@click.option("--list", "-l", "list_all", is_flag=True, help="List all config")
@click.option("--unset", "-u", is_flag=True, help="Unset a key")
@click.option("--global", "-g", "global_config", is_flag=True, help="Use global config")
def config_cmd(key: Optional[str], value: Optional[str], list_all: bool, unset: bool, global_config: bool) -> None:
    """Manage configuration."""
    config_path = Path.home() / ".claude" / "config.json" if global_config else Path.cwd() / ".claude" / "config.json"

    if list_all:
        config = Config.load_from_file(config_path) if config_path.exists() else Config()
        show_config_table(config)
        return

    if not key:
        # Interactive mode
        interactive_config()
        return

    config = Config.load_from_file(config_path) if config_path.exists() else Config()

    if unset:
        # Unset key
        if key == "model":
            config.api.model = "claude-sonnet-4-6"
        elif key == "base_url":
            config.api.base_url = None
        elif key == "theme":
            config.ui.theme = "dark"
        else:
            console.print(f"[red]Unknown key: {key}[/red]")
            return

        config.save_to_file(config_path)
        console.print(f"[green]Unset {key}[/green]")
        return

    if value:
        # Set value
        if key == "model":
            config.api.model = value
        elif key == "base_url":
            config.api.base_url = value
        elif key == "max_tokens":
            config.api.max_tokens = int(value)
        elif key == "theme":
            config.ui.theme = value
        elif key == "output_style":
            config.ui.output_style = value
        elif key.startswith("allow."):
            pattern = value
            config.permissions.allow.append(pattern)
        elif key.startswith("deny."):
            pattern = value
            config.permissions.deny.append(pattern)
        elif key.startswith("ask."):
            pattern = value
            config.permissions.ask.append(pattern)
        else:
            console.print(f"[red]Unknown key: {key}[/red]")
            return

        config.save_to_file(config_path)
        console.print(f"[green]Set {key} = {value}[/green]")
    else:
        # Show value
        if key == "model":
            console.print(f"[cyan]model[/cyan] = {config.api.model}")
        elif key == "base_url":
            console.print(f"[cyan]base_url[/cyan] = {config.api.base_url or 'default'}")
        elif key == "theme":
            console.print(f"[cyan]theme[/cyan] = {config.ui.theme}")
        else:
            console.print(f"[red]Unknown key: {key}[/red]")


def show_config_table(config: Config) -> None:
    """Show configuration as table."""
    table = Table(title="Configuration")
    table.add_column("Key", style="cyan")
    table.add_column("Value")

    table.add_row("api.model", config.api.model)
    table.add_row("api.base_url", config.api.base_url or "default")
    table.add_row("api.max_tokens", str(config.api.max_tokens))
    table.add_row("ui.theme", config.ui.theme)
    table.add_row("ui.output_style", config.ui.output_style)
    table.add_row("permissions.allow", str(config.permissions.allow[:3]) + "...")
    table.add_row("permissions.deny", str(config.permissions.deny[:3]) + "...")

    console.print(table)


def interactive_config() -> None:
    """Interactive configuration wizard."""
    console.print("[bold]Configuration Wizard[/bold]")

    config = Config.load()

    # Model
    model = Prompt.ask(
        "Model",
        default=config.api.model,
    )
    config.api.model = model

    # Base URL (optional)
    base_url = Prompt.ask(
        "API Base URL (optional, for compatible APIs)",
        default=config.api.base_url or "",
    )
    if base_url:
        config.api.base_url = base_url

    # Theme
    theme = Prompt.ask(
        "Theme",
        choices=["dark", "light", "mono"],
        default=config.ui.theme,
    )
    config.ui.theme = theme

    # Save
    config.save()
    console.print("[green]Configuration saved[/green]")


@click.command()
@click.option("--short", "-s", is_flag=True, help="Show only version number")
def version_cmd(short: bool) -> None:
    """Show version."""
    from .. import __version__

    if short:
        print(__version__)
    else:
        console.print(f"[bold green]Claude Code Python[/bold green] v{__version__}")
        console.print("[dim]Python rewrite of Claude Code CLI[/dim]")
        console.print("[dim]https://github.com/lg320531124/my-claude-code-test[/dim]")


@click.command()
@click.argument("pattern", required=False)
@click.option("--allow", "-a", is_flag=True, help="Allow pattern")
@click.option("--deny", "-d", is_flag=True, help="Deny pattern")
@click.option("--ask", "-k", is_flag=True, help="Ask for pattern")
@click.option("--remove", "-r", is_flag=True, help="Remove pattern")
@click.option("--list", "-l", "list_all", is_flag=True, help="List all rules")
def permission_cmd(pattern: Optional[str], allow: bool, deny: bool, ask: bool, remove: bool, list_all: bool) -> None:
    """Manage permission rules."""
    config = Config.load()

    if list_all:
        show_permission_rules(config)
        return

    if not pattern:
        console.print("[red]Pattern required[/red]")
        console.print("Example: cc permission 'Bash(rm *)' --deny")
        return

    # Remove from all lists first
    config.permissions.allow = [p for p in config.permissions.allow if p != pattern]
    config.permissions.deny = [p for p in config.permissions.deny if p != pattern]
    config.permissions.ask = [p for p in config.permissions.ask if p != pattern]

    if remove:
        config.save()
        console.print(f"[green]Removed: {pattern}[/green]")
        return

    # Add to appropriate list
    if allow:
        config.permissions.allow.append(pattern)
        decision = "ALLOW"
    elif deny:
        config.permissions.deny.append(pattern)
        decision = "DENY"
    elif ask:
        config.permissions.ask.append(pattern)
        decision = "ASK"
    else:
        console.print("[red]Specify --allow, --deny, or --ask[/red]")
        return

    config.save()
    console.print(f"[green]Added: {pattern} → {decision}[/green]")


def show_permission_rules(config: Config) -> None:
    """Show permission rules."""
    table = Table(title="Permission Rules")
    table.add_column("Decision", style="cyan")
    table.add_column("Pattern")

    for pattern in config.permissions.deny:
        table.add_row("[red]DENY[/red]", pattern)

    for pattern in config.permissions.ask:
        table.add_row("[yellow]ASK[/yellow]", pattern)

    for pattern in config.permissions.allow:
        table.add_row("[green]ALLOW[/green]", pattern)

    console.print(table)


# Export commands
__all__ = [
    "init_cmd",
    "config_cmd",
    "version_cmd",
    "permission_cmd",
]
