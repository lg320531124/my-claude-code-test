"""Enhanced Permission Prompter with persistence."""

from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Callable, Optional

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from rich.panel import Panel

from ..types.permission import PermissionDecision, PermissionResult
from .persistence import PermissionPersistence, SessionMemory, hash_input


console = Console()


class EnhancedPermissionPrompter:
    """Permission prompter with persistence and session memory."""

    def __init__(
        self,
        auto_approve: bool = False,
        project_dir: Optional[Path] = None,
        save_decisions: bool = True,
    ):
        self.auto_approve = auto_approve
        self.persistence = PermissionPersistence(project_dir)
        self.session_memory = SessionMemory()
        self.save_decisions = save_decisions

        # Callbacks
        self._on_decision: Optional[Callable, Optional] = None

    async def prompt(
        self,
        tool_name: str,
        tool_input: dict,
        reason: Optional[str] = None,
    ) -> PermissionDecision:
        """Prompt for permission with persistence."""
        input_hash = hash_input(tool_name, tool_input)

        # 1. Check session memory (highest priority)
        session_decision = self.session_memory.get(tool_name, input_hash)
        if session_decision:
            return session_decision

        # 2. Check persistence
        pattern = f"{tool_name}*"
        saved_decision = self.persistence.get_decision(pattern)
        if saved_decision:
            self.session_memory.set(tool_name, input_hash, saved_decision)
            return saved_decision

        # 3. Auto approve if enabled
        if self.auto_approve:
            return PermissionDecision.ALLOW

        # 4. Show prompt
        return await self._show_prompt(tool_name, tool_input, reason, input_hash)

    async def _show_prompt(
        self,
        tool_name: str,
        tool_input: dict,
        reason: Optional[str],
        input_hash: str,
    ) -> PermissionDecision:
        """Show interactive prompt with more options."""
        console.print()
        console.print(Panel(
            f"[cyan]Tool:[/cyan] {tool_name}\n"
            f"{self._format_input(tool_name, tool_input)}\n"
            f"[dim]Reason: {reason or 'No matching rule'}[/dim]",
            title="[bold yellow]Permission Required[/bold yellow]",
            border_style="yellow",
        ))

        # Extended options
        console.print()
        console.print("[dim]Options:[/dim]")
        console.print("  [green]y[/green] - Allow once")
        console.print("  [green]Y[/green] - Always allow (save)")
        console.print("  [red]n[/red] - Deny once")
        console.print("  [red]N[/red] - Always deny (save)")
        console.print("  [yellow]s[/yellow] - Allow for session")
        console.print("  [cyan]i[/cyan] - Show more info")

        response = Prompt.ask("Your choice?", default="y")

        decision = self._parse_response(response, tool_name, input_hash)

        if self._on_decision:
            self._on_decision(tool_name, tool_input, decision)

        return decision

    def _format_input(self, tool_name: str, tool_input: dict) -> str:
        """Format tool input for display."""
        if tool_name == "Bash":
            cmd = tool_input.get("command", "")
            return f"[cyan]Command:[/cyan] {cmd}"
        elif tool_name == "Write":
            path = tool_input.get("file_path", "")
            size = len(tool_input.get("content", ""))
            return f"[cyan]File:[/cyan] {path}\n[cyan]Size:[/cyan] {size} chars"
        elif tool_name == "Edit":
            path = tool_input.get("file_path", "")
            old = tool_input.get("old_string", "")[:50]
            new = tool_input.get("new_string", "")[:50]
            return f"[cyan]File:[/cyan] {path}\n[cyan]Old:[/cyan] {old}...\n[cyan]New:[/cyan] {new}..."
        elif tool_name == "Read":
            path = tool_input.get("file_path", "")
            return f"[cyan]File:[/cyan] {path}"
        else:
            return f"[cyan]Input:[/cyan] {str(tool_input)[:100]}"

    def _parse_response(
        self,
        response: str,
        tool_name: str,
        input_hash: str,
    ) -> PermissionDecision:
        """Parse user response."""
        response = response.lower()

        pattern = f"{tool_name}*"

        if response == "y":
            console.print("[green]✓ Allowed[/green]")
            self.session_memory.set(tool_name, input_hash, PermissionDecision.ALLOW)
            return PermissionDecision.ALLOW
        elif response == "yy" or response == "Y":
            console.print("[green]✓ Always allowed (saved)[/green]")
            if self.save_decisions:
                self.persistence.save_decision(pattern, PermissionDecision.ALLOW)
            self.session_memory.set(tool_name, input_hash, PermissionDecision.ALLOW)
            return PermissionDecision.ALLOW
        elif response == "n":
            console.print("[red]✗ Denied[/red]")
            self.session_memory.set(tool_name, input_hash, PermissionDecision.DENY)
            return PermissionDecision.DENY
        elif response == "nn" or response == "N":
            console.print("[red]✗ Always denied (saved)[/red]")
            if self.save_decisions:
                self.persistence.save_decision(pattern, PermissionDecision.DENY)
            self.session_memory.set(tool_name, input_hash, PermissionDecision.DENY)
            return PermissionDecision.DENY
        elif response == "s":
            console.print("[yellow]✓ Allowed for this session[/yellow]")
            self.session_memory.set(tool_name, input_hash, PermissionDecision.ALLOW)
            return PermissionDecision.ALLOW
        elif response == "i":
            # Show more info - then ask again
            console.print("[dim]This action requires permission because it may modify files or execute commands.[/dim]")
            return PermissionDecision.ASK

        return PermissionDecision.ASK

    def set_callback(self, callback: Callable, Optional) -> None:
        """Set decision callback."""
        self._on_decision = callback

    def get_stats(self) -> dict:
        """Get permission stats."""
        return {
            "session_decisions": len(self.session_memory.decisions),
            "saved_decisions": len(self.persistence.decisions),
            "auto_approve": self.auto_approve,
        }


def show_saved_permissions(console: Console, project_dir: Optional[Path] = None) -> None:
    """Show saved permission decisions."""
    persistence = PermissionPersistence(project_dir)
    decisions = persistence.list_decisions()

    if not decisions:
        console.print("[dim]No saved permission decisions[/dim]")
        return

    table = Table(title="Saved Permission Decisions")
    table.add_column("Pattern", style="cyan")
    table.add_column("Decision")
    table.add_column("Expires")
    table.add_column("Status")

    for entry in decisions:
        status = "[red]Expired[/red]" if entry["expired"] else "[green]Active[/green]"
        decision_color = "green" if entry["decision"] == "allow" else "red"
        expires_str = time.strftime(
            "%Y-%m-%d",
            time.localtime(entry["expires"]),
        )

        table.add_row(
            entry["pattern"],
            f"[{decision_color}]{entry['decision']}[/]",
            expires_str,
            status,
        )

    console.print(table)


def clear_permissions(console: Console, project_dir: Optional[Path] = None) -> None:
    """Clear all saved permissions."""
    persistence = PermissionPersistence(project_dir)
    cleared = persistence.clear_expired()
    console.print(f"[green]Cleared {cleared} expired permissions[/green]")


# Keep old PermissionPrompter for backward compatibility
PermissionPrompter = EnhancedPermissionPrompter


import time  # Add at top of file
