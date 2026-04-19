"""Compact command - Context compression."""

from __future__ import annotations
from rich.console import Console

from ..core.session import Session


def run_compact(console: Console, session: Session) -> None:
    """Compact session context."""
    messages = session.messages

    if not messages:
        console.print("[yellow]No messages to compact[/yellow]")
        return

    # Count tokens (rough estimate)
    total_chars = 0
    for msg in messages:
        for block in msg.content:
            if hasattr(block, "text"):
                total_chars += len(block.text)

    estimated_tokens = total_chars // 4

    console.print(f"[dim]Current: ~{estimated_tokens} tokens ({len(messages)} messages)[/dim]")

    # Keep only last 5 messages
    if len(messages) > 5:
        kept = messages[-5:]
        removed = len(messages) - 5

        # Create summary of removed messages
        summary_parts = []
        for msg in messages[:-5]:
            for block in msg.content:
                if hasattr(block, "text"):
                    # Take first 100 chars
                    text = block.text[:100]
                    if len(block.text) > 100:
                        text += "..."
                    summary_parts.append(text)

        summary = "Previous context: " + "; ".join(summary_parts[:3])
        if len(summary_parts) > 3:
            summary += f" (and {len(summary_parts) - 3} more)"

        # Create compacted message
        from ..types.message import UserMessage, TextBlock
        compacted = UserMessage(content=[TextBlock(text=f"[COMPACTED] {summary}")])

        session.messages = [compacted] + kept

        console.print(f"[green]Compacted: removed {removed} messages[/green]")
        console.print(f"[dim]Now: ~{len(session.messages)} messages[/dim]")
    else:
        console.print("[yellow]Context is already small[/yellow]")


def estimate_context_usage(messages: list) -> dict:
    """Estimate context window usage."""
    total_chars = 0
    tool_calls = 0

    for msg in messages:
        for block in msg.content:
            if hasattr(block, "text"):
                total_chars += len(block.text)
            elif hasattr(block, "name") and block.type == "tool_use":
                tool_calls += 1

    return {
        "estimated_tokens": total_chars // 4,
        "message_count": len(messages),
        "tool_calls": tool_calls,
    }
