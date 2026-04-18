"""CLI entry point for Claude Code Python."""

import asyncio
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from . import __version__
from .core.engine import QueryEngine
from .core.session import Session
from .tools import get_default_tools
from .utils.config import Config


console = Console()


@click.group(invoke_without_command=True)
@click.option("--version", "-v", is_flag=True, help="Show version")
@click.option("--model", "-m", help="Model to use")
@click.option("--cwd", type=click.Path(), help="Working directory")
@click.option("--base-url", help="API base URL (for compatible APIs)")
@click.pass_context
def main(ctx: click.Context, version: bool, model: str | None, cwd: str | None, base_url: str | None) -> None:
    """Claude Code Python - AI-powered coding assistant for terminal."""
    if version:
        console.print(f"claude-code-py version {__version__}")
        return

    # Load config
    config = Config.load()

    # Override from CLI options
    if model:
        config.api.model = model
    if base_url:
        config.api.base_url = base_url

    # Apply environment overrides
    env_overrides = config.get_env_overrides()
    if "model" in env_overrides:
        config.api.model = env_overrides["model"]
    if "base_url" in env_overrides:
        config.api.base_url = env_overrides["base_url"]

    # Initialize session
    session = Session(cwd=Path(cwd) if cwd else None)

    # Store in context
    ctx.obj = {"config": config, "session": session}

    # If no subcommand, enter REPL mode
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


@main.command()
@click.argument("prompt", required=False)
@click.pass_context
def repl(ctx: click.Context, prompt: str | None) -> None:
    """Start interactive REPL session."""
    config: Config = ctx.obj["config"]
    session: Session = ctx.obj["session"]

    # Check API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        console.print("[red]Warning: ANTHROPIC_API_KEY not set[/red]")
        console.print("[dim]Set it with: export ANTHROPIC_API_KEY=your-key[/dim]")

    console.print(
        Panel.fit(
            f"[bold green]Claude Code Python[/bold green] v{__version__}\n"
            f"[dim]Model: {config.api.model}[/dim]\n"
            f"[dim]Base URL: {config.api.base_url or 'api.anthropic.com'}[/dim]\n"
            f"[dim]Working directory: {session.cwd}[/dim]",
            title="Welcome",
        )
    )
    console.print("[dim]Type your question, or use /help for commands[/dim]")

    # Initialize tools and engine
    tools = get_default_tools()
    engine = QueryEngine(
        model=config.api.model,
        tools=tools,
        base_url=config.api.base_url,
    )

    # Run async REPL
    asyncio.run(_run_repl(engine, session, config, prompt))


async def _run_repl(
    engine: QueryEngine,
    session: Session,
    config: Config,
    initial_prompt: str | None,
) -> None:
    """Async REPL loop with streaming."""
    from .types.message import create_user_message

    # Handle initial prompt if provided
    if initial_prompt:
        await _process_query(engine, session, initial_prompt)

    # REPL loop
    while True:
        try:
            user_input = Prompt.ask("[bold blue]You:[/bold blue]")
            if user_input.strip() == "":
                continue

            # Handle special commands
            if user_input.startswith("/"):
                await _handle_command(user_input, session, config)
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                console.print("[yellow]Goodbye![/yellow]")
                break

            # Process query
            await _process_query(engine, session, user_input)

        except KeyboardInterrupt:
            console.print("\n[yellow]Use 'exit' to quit[/yellow]")
        except EOFError:
            break


async def _process_query(engine: QueryEngine, session: Session, prompt: str) -> None:
    """Process a user query with streaming output."""
    from .types.message import create_user_message

    # Create user message
    msg = create_user_message(prompt)
    session.add_message(msg)

    # Stream response
    ctx = session.get_context()
    response_text = ""

    console.print()  # New line before response

    try:
        async for chunk in engine.query(session.messages, ctx):
            if isinstance(chunk, str):
                # Stream text
                response_text += chunk
                console.print(Text(chunk), end="")

        console.print()  # New line after response

        if response_text:
            console.print()  # Spacing

    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")


async def _handle_command(command: str, session: Session, config: Config) -> None:
    """Handle slash commands."""
    cmd = command.strip().lower()

    if cmd == "/help":
        show_help(console)
    elif cmd == "/doctor":
        from .commands.doctor import run_doctor
        run_doctor(console)
    elif cmd == "/clear":
        session.clear_messages()
        console.print("[green]Session cleared[/green]")
    elif cmd == "/config":
        show_config(console, config)
    elif cmd == "/tasks":
        show_tasks(console)
    elif cmd == "/exit":
        console.print("[yellow]Goodbye![/yellow]")
        raise SystemExit(0)
    elif cmd == "/model":
        console.print(f"[dim]Current model: {config.api.model}[/dim]")
    elif cmd.startswith("/model "):
        new_model = command.split(maxsplit=1)[1]
        config.api.model = new_model
        console.print(f"[green]Model changed to: {new_model}[/green]")
    else:
        console.print(f"[red]Unknown command: {command}[/red]")
        show_help(console)


def show_help(console: Console) -> None:
    """Show help for commands."""
    from rich.table import Table

    table = Table(title="Available Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description")

    commands = [
        ("/help", "Show this help"),
        ("/doctor", "Run diagnostics"),
        ("/clear", "Clear session"),
        ("/config", "Show configuration"),
        ("/tasks", "Show tasks"),
        ("/model", "Show current model"),
        ("/model <name>", "Change model"),
        ("/exit", "Exit REPL"),
    ]

    for cmd, desc in commands:
        table.add_row(cmd, desc)

    console.print(table)


def show_config(console: Console, config: Config) -> None:
    """Show current configuration."""
    from rich.table import Table

    table = Table(title="Configuration")
    table.add_column("Key", style="cyan")
    table.add_column("Value")

    table.add_row("Model", config.api.model)
    table.add_row("Base URL", config.api.base_url or "api.anthropic.com")
    table.add_row("Provider", config.api.provider)
    table.add_row("Max Tokens", str(config.api.max_tokens))
    table.add_row("Allow Rules", str(config.permissions.allow))
    table.add_row("Ask Rules", str(config.permissions.ask))
    table.add_row("Deny Rules", str(config.permissions.deny))

    console.print(table)


def show_tasks(console: Console) -> None:
    """Show current tasks."""
    from .tools.task import _tasks

    if not _tasks:
        console.print("[dim]No tasks[/dim]")
        return

    from rich.table import Table
    table = Table(title="Tasks")
    table.add_column("ID", style="cyan")
    table.add_column("Subject")
    table.add_column("Status")

    for task_id, task in sorted(_tasks.items(), key=lambda x: int(x[0])):
        status_color = {
            "pending": "yellow",
            "in_progress": "blue",
            "completed": "green",
        }.get(task["status"], "white")
        table.add_row(task_id, task["subject"], f"[{status_color}]{task['status']}[/]")

    console.print(table)


# Subcommands
@main.command()
@click.argument("message")
@click.pass_context
def ask(ctx: click.Context, message: str) -> None:
    """Ask a single question and exit."""
    config: Config = ctx.obj["config"]
    session: Session = ctx.obj["session"]

    console.print(f"[bold]Question:[/bold] {message}")

    tools = get_default_tools()
    engine = QueryEngine(model=config.api.model, tools=tools)

    asyncio.run(_process_query(engine, session, message))


@main.command()
def doctor() -> None:
    """Run environment diagnostics."""
    from .commands.doctor import run_doctor
    run_doctor(console)


@main.command()
@click.option("--message", "-m", help="Commit message")
@click.pass_context
def commit(ctx: click.Context, message: str | None) -> None:
    """Create a git commit."""
    config: Config = ctx.obj["config"]
    console.print("[yellow]Commit feature coming soon[/yellow]")


@main.command()
@click.pass_context
def review(ctx: click.Context) -> None:
    """Review current changes."""
    console.print("[yellow]Review feature coming soon[/yellow]")


@main.command()
@click.argument("key", required=False)
@click.argument("value", required=False)
@click.pass_context
def config_cmd(ctx: click.Context, key: str | None, value: str | None) -> None:
    """Manage configuration."""
    config: Config = ctx.obj["config"]

    if key and value:
        # Set config value
        if key == "model":
            config.api.model = value
        elif key == "base_url":
            config.api.base_url = value
        else:
            console.print(f"[red]Unknown config key: {key}[/red]")
            return
        config.save()
        console.print(f"[green]Set {key} = {value}[/green]")
    elif key:
        # Show specific config
        console.print(f"[dim]{key}[/dim]")
    else:
        # Show all config
        show_config(console, config)


if __name__ == "__main__":
    main()