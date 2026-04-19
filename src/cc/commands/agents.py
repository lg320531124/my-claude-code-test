"""Agents Command - Manage and run agents."""

from __future__ import annotations
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


@click.group("agents")
def agents_group():
    """Manage agents."""
    pass


@agents_group.command("list")
@click.option("--type", "-t", default=None, help="Filter by agent type")
def list_agents(type: Optional[str]):
    """List available agents."""
    from cc.tools.agent import get_agent_types

    agent_types = get_agent_types()

    if type:
        agent_types = {k: v for k, v in agent_types.items() if k == type}

    table = Table(title="Available Agents")
    table.add_column("Type", style="cyan")
    table.add_column("Description", style="white")

    for agent_type, description in agent_types.items():
        table.add_row(agent_type, description)

    console.print(table)


@agents_group.command("run")
@click.argument("agent_type")
@click.argument("prompt")
@click.option("--model", "-m", default="haiku", help="Model to use")
@click.option("--timeout", "-t", default=300, help="Timeout in seconds")
def run_agent(agent_type: str, prompt: str, model: str, timeout: int):
    """Run an agent."""
    import asyncio
    from cc.tools.agent import AgentExecutor, AgentConfig, AGENT_TYPES

    if agent_type not in AGENT_TYPES:
        console.print(f"[red]Unknown agent type: {agent_type}[/red]")
        console.print(f"Available types: {', '.join(AGENT_TYPES.keys())}")
        return

    console.print(Panel(
        f"[bold]Running Agent[/bold]\n\n"
        f"Type: {agent_type}\n"
        f"Prompt: {prompt[:100]}...\n"
        f"Model: {model}\n"
        f"Timeout: {timeout}s",
        title="Agent Execution",
        border_style="green",
    ))

    async def execute():
        config = AgentConfig(
            agent_type=agent_type,
            model=model,
            timeout_seconds=timeout,
        )

        executor = AgentExecutor(config)

        try:
            result = await executor.run(prompt)

            console.print("\n[bold green]Agent Result:[/bold green]")
            console.print(result.output)

            console.print(f"\n[dim]Tokens: {result.tokens_used}, Duration: {result.duration_ms}ms[/dim]")

        except Exception as e:
            console.print(f"[red]Agent failed: {str(e)}[/red]")

    asyncio.run(execute())


@agents_group.command("info")
@click.argument("agent_type")
def agent_info(agent_type: str):
    """Show agent information."""
    from cc.tools.agent import AGENT_TYPES, AGENT_DESCRIPTIONS

    if agent_type not in AGENT_TYPES:
        console.print(f"[red]Unknown agent type: {agent_type}[/red]")
        return

    description = AGENT_DESCRIPTIONS.get(agent_type, "No description available")

    console.print(Panel(
        f"[bold]{agent_type}[/bold]\n\n{description}",
        title="Agent Information",
        border_style="cyan",
    ))


__all__ = ["agents_group"]
