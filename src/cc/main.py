"""CLI entry point for Claude Code Python."""

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

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
@click.pass_context
def main(ctx: click.Context, version: bool, model: str | None, cwd: str | None) -> None:
    """Claude Code Python - AI-powered coding assistant for terminal."""
    if version:
        console.print(f"claude-code-py version {__version__}")
        return

    # Load config
    config = Config.load()

    # Override model if specified
    if model:
        config.api.model = model

    # Initialize session
    session = Session(cwd=Path(cwd) if cwd else None)

    # If no subcommand, enter REPL mode
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl, config=config, session=session)


@main.command()
@click.argument("prompt", required=False)
@click.pass_obj
def repl(config: Config, session: Session, prompt: str | None) -> None:
    """Start interactive REPL session."""
    console.print(
        Panel.fit(
            f"[bold green]Claude Code Python[/bold green] v{__version__}\n"
            f"[dim]Model: {config.api.model}[/dim]\n"
            f"[dim]Working directory: {session.cwd}[/dim]",
            title="Welcome",
        )
    )

    # Initialize tools and engine
    tools = get_default_tools()
    engine = QueryEngine(
        model=config.api.model,
        tools=tools,
        permission_mode=config.permissions.mode,
    )

    # Run async REPL
    asyncio.run(_run_repl(engine, session, prompt))


async def _run_repl(engine: QueryEngine, session: Session, initial_prompt: str | None) -> None:
    """Async REPL loop."""
    from rich.markdown import Markdown
    from ..types.message import create_user_message

    # Handle initial prompt if provided
    if initial_prompt:
        await _process_query(engine, session, initial_prompt)

    # REPL loop
    while True:
        try:
            user_input = Prompt.ask("[bold blue]>[/bold blue]")
            if user_input.strip() == "":
                continue

            # Handle special commands
            if user_input.startswith("/"):
                await _handle_command(user_input, session)
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
    """Process a user query."""
    from rich.markdown import Markdown
    from rich.spinner import Spinner

    # Create user message
    msg = create_user_message(prompt)
    session.add_message(msg)

    # Show spinner while processing
    with console.status("[bold green]Thinking...", spinner="dots"):
        ctx = session.get_context()
        response_text = ""

        async for block in engine.query(session.messages, ctx):
            if hasattr(block, "text"):
                response_text += block.text

    # Display response
    if response_text:
        console.print(Markdown(response_text))


async def _handle_command(command: str, session: Session) -> None:
    """Handle slash commands."""
    from .commands import handle_command
    await handle_command(command, session, console)


# Subcommands
@main.command()
@click.argument("message")
def ask(message: str) -> None:
    """Ask a single question and exit."""
    console.print(f"[bold]Question:[/bold] {message}")
    # TODO: Implement single query mode


@main.command()
def doctor() -> None:
    """Run environment diagnostics."""
    from .commands.doctor import run_doctor
    run_doctor(console)


@main.command()
@click.option("--message", "-m", help="Commit message")
def commit(message: str | None) -> None:
    """Create a git commit."""
    console.print("[yellow]Commit feature coming soon[/yellow]")


@main.command()
def review() -> None:
    """Review current changes."""
    console.print("[yellow]Review feature coming soon[/yellow]")


@main.command()
def config_cmd() -> None:
    """Manage configuration."""
    console.print("[yellow]Config management coming soon[/yellow]")


if __name__ == "__main__":
    main()