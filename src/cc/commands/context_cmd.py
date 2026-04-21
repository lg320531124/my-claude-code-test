"""Context Command - Context visualization."""

from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from ..core.session import Session
from ..services.token_estimation import estimate_tokens, estimate_messages_tokens


async def run_context(console: Console, session: Session, action: str, args: list) -> None:
    """Run context command."""
    if action == "show":
        await show_context(console, session)
    elif action == "stats":
        await context_stats(console, session)
    elif action == "tree":
        await context_tree(console, session)
    elif action == "analyze":
        await analyze_context(console, session)
    elif action == "optimize":
        await optimize_context(console, session)
    else:
        show_context_help(console)


async def show_context(console: Console, session: Session) -> None:
    """Show current context."""
    console.print("[bold cyan]Current Context[/]")
    console.print(f"  Session ID: {session.session_id}")
    console.print(f"  Working Dir: {session.cwd}")
    console.print(f"  Messages: {len(session.messages)}")

    # Estimate tokens
    usage = await estimate_messages_tokens(session.messages)
    console.print(f"  Input Tokens: ~{usage.input_tokens}")

    # Show message types
    message_types = {}
    for msg in session.messages:
        role = msg.get("role", "unknown")
        message_types[role] = message_types.get(role, 0) + 1

    console.print("\n[bold]Message Types:[/]")
    for role, count in message_types.items():
        console.print(f"  {role}: {count}")


async def context_stats(console: Console, session: Session) -> None:
    """Show context statistics."""
    table = Table(title="Context Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    # Calculate stats
    total_messages = len(session.messages)
    total_tokens = await estimate_messages_tokens(session.messages)

    user_messages = sum(1 for m in session.messages if m.get("role") == "user")
    assistant_messages = sum(1 for m in session.messages if m.get("role") == "assistant")
    tool_messages = sum(1 for m in session.messages if m.get("role") == "tool")

    # Average message length
    avg_tokens = total_tokens.input_tokens // total_messages if total_messages > 0 else 0

    table.add_row("Total Messages", str(total_messages))
    table.add_row("Total Tokens (est)", str(total_tokens.input_tokens))
    table.add_row("Avg Tokens/Message", str(avg_tokens))
    table.add_row("User Messages", str(user_messages))
    table.add_row("Assistant Messages", str(assistant_messages))
    table.add_row("Tool Messages", str(tool_messages))

    console.print(table)


async def context_tree(console: Console, session: Session) -> None:
    """Show context as tree."""
    tree = Tree(f"[cyan]Session: {session.session_id}[/]")

    for i, msg in enumerate(session.messages):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        # Truncate content for display
        preview = content[:30] if isinstance(content, str) else str(content)[:30]

        role_colors = {
            "user": "blue",
            "assistant": "green",
            "tool": "cyan",
            "system": "dim",
        }
        color = role_colors.get(role, "white")

        msg_node = tree.add(f"[{color}][{i}] {role}[/]")
        msg_node.add(f"[dim]{preview}[/]")

        # Add tool calls if present
        if role == "assistant" and isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_name = block.get("name", "unknown")
                    msg_node.add(f"[yellow]Tool: {tool_name}[/]")

    console.print(tree)


async def analyze_context(console: Console, session: Session) -> None:
    """Analyze context for optimization opportunities."""
    console.print("[bold cyan]Context Analysis[/]")

    # Find large messages
    large_messages = []
    for i, msg in enumerate(session.messages):
        content = msg.get("content", "")
        if isinstance(content, str) and len(content) > 1000:
            large_messages.append((i, len(content)))

    if large_messages:
        console.print("\n[yellow]Large Messages (could be compacted):[/]")
        for idx, size in large_messages[:5]:
            console.print(f"  Message {idx}: {size} chars")

    # Find repeated patterns
    console.print("\n[dim]Checking for repeated content...[/]")

    # Tool usage summary
    tool_usage = {}
    for msg in session.messages:
        content = msg.get("content", "")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_name = block.get("name", "unknown")
                    tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1

    if tool_usage:
        console.print("\n[bold]Tool Usage:[/")
        for tool, count in sorted(tool_usage.items(), key=lambda x: -x[1]):
            console.print(f"  {tool}: {count} calls")


async def optimize_context(console: Console, session: Session) -> None:
    """Suggest context optimizations."""
    console.print("[bold cyan]Context Optimization[/]")

    # Analyze
    await analyze_context(console, session)

    console.print("\n[bold]Suggestions:[/]")

    # Check if compacting needed
    usage = await estimate_messages_tokens(session.messages)
    if usage.input_tokens > 100000:
        console.print("[yellow]• Context is large, consider /compact[/]")

    if len(session.messages) > 50:
        console.print("[yellow]• Many messages, consider /compact[/]")

    # Check for old messages
    if len(session.messages) > 20:
        console.print("[dim]• Older messages could be summarized[/]")

    console.print("\n[dim]Run /compact to reduce context size[/]")


def show_context_help(console: Console) -> None:
    """Show context command help."""
    table = Table(title="Context Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description")

    commands = [
        ("context show", "Show current context"),
        ("context stats", "Context statistics"),
        ("context tree", "Context tree view"),
        ("context analyze", "Analyze context"),
        ("context optimize", "Optimization suggestions"),
    ]

    for cmd, desc in commands:
        table.add_row(cmd, desc)

    console.print(table)


__all__ = ["run_context"]