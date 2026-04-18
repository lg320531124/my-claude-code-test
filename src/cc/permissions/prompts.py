"""Permission prompts - User interaction for permission decisions."""

import asyncio
from typing import Callable

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from ..types.permission import PermissionDecision, PermissionResult


console = Console()


class PermissionPrompter:
    """Handles user prompts for permission decisions."""

    def __init__(self, auto_approve: bool = False):
        self.auto_approve = auto_approve
        self.session_decisions: dict[str, PermissionDecision] = {}

    async def prompt(
        self,
        tool_name: str,
        tool_input: dict,
        reason: str | None = None,
    ) -> PermissionDecision:
        """Prompt user for permission decision."""
        # Check if already decided this session
        key = f"{tool_name}:{str(tool_input)[:50]}"
        if key in self.session_decisions:
            return self.session_decisions[key]

        # Auto approve if enabled
        if self.auto_approve:
            return PermissionDecision.ALLOW

        # Show prompt
        return await self._show_prompt(tool_name, tool_input, reason)

    async def _show_prompt(
        self,
        tool_name: str,
        tool_input: dict,
        reason: str | None,
    ) -> PermissionDecision:
        """Show interactive prompt."""
        console.print()
        console.print(f"[bold yellow]Permission Required[/bold yellow]")
        console.print(f"[cyan]Tool:[/cyan] {tool_name}")

        # Show input summary
        if tool_name == "Bash" and "command" in tool_input:
            console.print(f"[cyan]Command:[/cyan] {tool_input['command']}")
        elif tool_name == "Write" and "file_path" in tool_input:
            console.print(f"[cyan]File:[/cyan] {tool_input['file_path']}")
            console.print(f"[cyan]Size:[/cyan] {len(tool_input.get('content', ''))} chars")
        elif tool_name == "Edit" and "file_path" in tool_input:
            console.print(f"[cyan]File:[/cyan] {tool_input['file_path']}")
            console.print(f"[cyan]Old:[/cyan] {tool_input.get('old_string', '')[:50]}...")
        else:
            console.print(f"[cyan]Input:[/cyan] {str(tool_input)[:100]}")

        if reason:
            console.print(f"[dim]Reason: {reason}[/dim]")

        console.print()

        # Options
        options = ["y", "n", "a", "d"]
        response = Prompt.ask(
            "Allow this action?",
            choices=options,
            default="y",
            show_choices=True,
        )

        decision = self._parse_response(response)

        # Remember for this session
        key = f"{tool_name}:{str(tool_input)[:50]}"
        self.session_decisions[key] = decision

        return decision

    def _parse_response(self, response: str) -> PermissionDecision:
        """Parse user response to decision."""
        response = response.lower()

        if response == "y":
            console.print("[green]✓ Allowed[/green]")
            return PermissionDecision.ALLOW
        elif response == "n":
            console.print("[red]✗ Denied[/red]")
            return PermissionDecision.DENY
        elif response == "a":
            console.print("[green]✓ Always allowed[/green]")
            return PermissionDecision.ALLOW
        elif response == "d":
            console.print("[red]✗ Always denied[/red]")
            return PermissionDecision.DENY

        return PermissionDecision.ASK


def show_permission_rules(console: Console) -> None:
    """Show current permission rules."""
    from ..utils.config import Config
    config = Config.load()

    table = Table(title="Permission Rules")
    table.add_column("Decision", style="cyan")
    table.add_column("Pattern")

    for pattern in config.permissions.deny:
        table.add_row("[red]DENY[/]", pattern)

    for pattern in config.permissions.ask:
        table.add_row("[yellow]ASK[/]", pattern)

    for pattern in config.permissions.allow:
        table.add_row("[green]ALLOW[/]", pattern)

    console.print(table)


def add_permission_rule(
    pattern: str,
    decision: PermissionDecision,
    save: bool = True,
) -> None:
    """Add a permission rule."""
    from ..utils.config import Config
    config = Config.load()

    # Remove from other lists first
    config.permissions.allow = [p for p in config.permissions.allow if p != pattern]
    config.permissions.deny = [p for p in config.permissions.deny if p != pattern]
    config.permissions.ask = [p for p in config.permissions.ask if p != pattern]

    # Add to appropriate list
    if decision == PermissionDecision.ALLOW:
        config.permissions.allow.append(pattern)
    elif decision == PermissionDecision.DENY:
        config.permissions.deny.append(pattern)
    elif decision == PermissionDecision.ASK:
        config.permissions.ask.append(pattern)

    if save:
        config.save()


# Permission mode descriptions
PERMISSION_MODES = {
    "default": "Prompt for dangerous operations",
    "auto": "Auto-approve safe operations, prompt for risky",
    "bypass": "Allow all operations without prompting",
    "plan": "Plan mode - restricted operations",
}