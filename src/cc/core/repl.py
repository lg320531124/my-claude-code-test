"""REPL implementation with streaming and progress."""

import asyncio
import sys
from pathlib import Path
from typing import Callable

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.text import Text

from ..core.engine import QueryEngine
from ..core.session import Session
from ..tools import get_default_tools
from ..utils.config import Config
from ..types.message import create_user_message
from ..context import get_git_context, get_system_prompt


console = Console()


class REPL:
    """Interactive REPL with streaming output."""

    def __init__(
        self,
        config: Config,
        session: Session,
        on_command: Callable | None = None,
    ):
        self.config = config
        self.session = session
        self.on_command = on_command
        self.running = True

        # Initialize engine
        tools = get_default_tools()
        git_info = get_git_context(session.cwd)

        self.engine = QueryEngine(
            model=config.api.model,
            tools=tools,
            base_url=config.api.base_url,
            system_prompt=get_system_prompt(
                "developer",
                session.cwd,
                git_info,
            ),
        )

    def run(self) -> None:
        """Run the REPL."""
        self._show_welcome()
        asyncio.run(self._async_loop())

    def _show_welcome(self) -> None:
        """Show welcome message."""
        console.print(
            Panel.fit(
                "[bold green]Claude Code Python[/bold green]\n"
                f"[dim]Model: {self.config.api.model}[/dim]\n"
                f"[dim]CWD: {self.session.cwd}[/dim]\n"
                "[dim]/help for commands[/dim]",
                title="Ready",
            )
        )

    async def _async_loop(self) -> None:
        """Async REPL loop."""
        while self.running:
            try:
                # Get input
                user_input = Prompt.ask("[bold cyan]>[/]")

                if not user_input.strip():
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    self._handle_command(user_input)
                    continue

                # Handle exit
                if user_input.lower() in ("exit", "quit", "q"):
                    console.print("[yellow]Goodbye![/yellow]")
                    self.running = False
                    break

                # Process query
                await self._process_query(user_input)

            except KeyboardInterrupt:
                console.print("\n[yellow]Press 'exit' to quit[/yellow]")
            except EOFError:
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

    async def _process_query(self, text: str) -> None:
        """Process user query with streaming."""
        # Add user message
        msg = create_user_message(text)
        self.session.add_message(msg)

        # Get context
        ctx = self.session.get_context()

        # Stream response
        response_text = ""
        tool_calls = []

        console.print()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("Thinking...", total=None)

            try:
                async for chunk in self.engine.query(self.session.messages, ctx):
                    if isinstance(chunk, str):
                        response_text += chunk
                        progress.update(task, description="Streaming...")
                        console.print(Text(chunk), end="")

                    elif isinstance(chunk, dict):
                        chunk_type = chunk.get("type", "")

                        if chunk_type == "text_delta":
                            text = chunk.get("text", "")
                            response_text += text
                            console.print(Text(text), end="")

                        elif chunk_type == "tool_use_start":
                            tool_name = chunk.get("name", "")
                            progress.update(task, description=f"Executing {tool_name}...")

                        elif chunk_type == "retry":
                            attempt = chunk.get("attempt", 0)
                            delay = chunk.get("delay", 1)
                            progress.update(task, description=f"Retrying ({attempt})...")

                        elif chunk_type == "error":
                            error = chunk.get("error", "")
                            console.print(f"\n[red]Error: {error}[/red]")

                console.print()  # New line after streaming

            except Exception as e:
                progress.stop()
                console.print(f"\n[red]Query error: {e}[/red]")

        # Show usage
        stats = self.engine.client.get_usage_stats()
        if stats["total_tokens"] > 0:
            console.print(
                f"[dim]Tokens: {stats['input_tokens']} in / {stats['output_tokens']} out[/dim]",
            )

    def _handle_command(self, command: str) -> None:
        """Handle slash command."""
        if self.on_command:
            asyncio.run(self.on_command(command))
        else:
            from ..commands import handle_command
            asyncio.run(handle_command(command, self.session, self.config))

    def stop(self) -> None:
        """Stop the REPL."""
        self.running = False


def run_repl(
    config: Config,
    session: Session,
    initial_prompt: str | None = None,
) -> None:
    """Run REPL with optional initial prompt."""
    repl = REPL(config, session)

    if initial_prompt:
        asyncio.run(repl._process_query(initial_prompt))

    repl.run()


class StreamingDisplay:
    """Handles streaming text display."""

    def __init__(self, console: Console):
        self.console = console
        self.buffer = ""
        self.in_code_block = False

    def add(self, text: str) -> None:
        """Add text to display."""
        self.buffer += text

        # Handle code blocks
        if "```" in text:
            self.in_code_block = not self.in_code_block

        if self.in_code_block:
            self.console.print(text, end="", highlight=False)
        else:
            self.console.print(Text(text), end="")

    def finalize(self) -> str:
        """Finalize and return full text."""
        return self.buffer