"""Hooks Command - Hook management."""

from __future__ import annotations
import asyncio
from typing import Optional, List
from rich.console import Console
from rich.table import Table

from ..services.hooks import HookManager, HookType, get_hook_manager


async def run_hooks(console: Console, action: str, args: List[str]) -> None:
    """Run hooks command."""
    manager = get_hook_manager()

    if action == "list":
        await list_hooks(console, manager)
    elif action == "show":
        await show_hook(console, manager, args[0] if args else None)
    elif action == "stats":
        await hook_stats(console, manager)
    elif action == "enable":
        await enable_hook(console, manager, args[0] if args else None)
    elif action == "disable":
        await disable_hook(console, manager, args[0] if args else None)
    elif action == "run":
        await run_hook(console, manager, args[0] if args else None)
    elif action == "register":
        await register_hook(console, args)
    else:
        show_hooks_help(console)


async def list_hooks(console: Console, manager: HookManager) -> None:
    """List registered hooks."""
    table = Table(title="Registered Hooks")
    table.add_column("ID", style="cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Name", style="green")
    table.add_column("Priority", style="dim")
    table.add_column("Enabled", style="magenta")

    hooks = manager.registry.get_all_hooks()

    for hook_id, hook in enumerate(hooks):
        enabled = "✓" if hook.enabled else "✗"
        table.add_row(
            str(hook_id),
            hook.hook_type.value,
            hook.name,
            str(hook.priority),
            enabled,
        )

    console.print(table)


async def show_hook(console: Console, manager: HookManager, hook_name: Optional[str]) -> None:
    """Show hook details."""
    if not hook_name:
        console.print("[red]Please provide hook name[/red]")
        return

    hook = manager.registry.get_hook(hook_name)
    if not hook:
        console.print(f"[red]Hook not found: {hook_name}[/red]")
        return

    console.print(f"[bold cyan]Hook: {hook_name}[/]")
    console.print(f"  Type: {hook.hook_type.value}")
    console.print(f"  Priority: {hook.priority}")
    console.print(f"  Enabled: {hook.enabled}")
    console.print(f"  Handler: {hook.handler.__name__ if hasattr(hook.handler, '__name__') else 'anonymous'}")


async def hook_stats(console: Console, manager: HookManager) -> None:
    """Show hook statistics."""
    stats = manager.get_stats()

    table = Table(title="Hook Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Hooks", str(stats.get("total_hooks", 0)))
    table.add_row("Total Calls", str(stats.get("total_calls", 0)))
    table.add_row("Total Errors", str(stats.get("total_errors", 0)))

    console.print(table)

    # Show per-type stats
    if stats.get("events"):
        console.print("\n[bold]Hook Events:[/]")
        for event, event_stats in stats["events"].items():
            console.print(f"  {event}: {event_stats.get('calls', 0)} calls")


async def enable_hook(console: Console, manager: HookManager, hook_name: Optional[str]) -> None:
    """Enable a hook."""
    if not hook_name:
        console.print("[red]Please provide hook name[/red]")
        return

    hook = manager.registry.get_hook(hook_name)
    if hook:
        hook.enabled = True
        console.print(f"[green]Hook enabled: {hook_name}[/]")
    else:
        console.print(f"[red]Hook not found: {hook_name}[/red]")


async def disable_hook(console: Console, manager: HookManager, hook_name: Optional[str]) -> None:
    """Disable a hook."""
    if not hook_name:
        console.print("[red]Please provide hook name[/red]")
        return

    hook = manager.registry.get_hook(hook_name)
    if hook:
        hook.enabled = False
        console.print(f"[yellow]Hook disabled: {hook_name}[/]")
    else:
        console.print(f"[red]Hook not found: {hook_name}[/red]")


async def run_hook(console: Console, manager: HookManager, hook_type: Optional[str]) -> None:
    """Manually trigger a hook."""
    if not hook_type:
        console.print("[red]Please provide hook type[/red]")
        return

    try:
        hook_type_enum = HookType(hook_type)
        from ..services.hooks import HookContext

        context = HookContext(
            event=hook_type_enum,
            data={"manual": True},
            timestamp=asyncio.get_event_loop().time(),
        )

        results = await manager.trigger_async(hook_type_enum, context)

        console.print(f"[green]Hook triggered: {hook_type}[/]")
        console.print(f"Results: {len(results)} hooks executed")

        for result in results:
            if result.success:
                console.print(f"  ✓ {result.hook_name}")
            else:
                console.print(f"  ✗ {result.hook_name}: {result.error}")

    except ValueError:
        console.print(f"[red]Unknown hook type: {hook_type}[/]")
        console.print(f"Valid types: {', '.join(h.value for h in HookType)}")


async def register_hook(console: Console, args: List[str]) -> None:
    """Register a new hook."""
    if len(args) < 2:
        console.print("[red]Usage: /hooks register <type> <name>[/red]")
        return

    hook_type_str = args[0]
    hook_name = args[1]

    try:
        hook_type = HookType(hook_type_str)
        manager = get_hook_manager()

        # Create placeholder handler
        async def placeholder_handler(context):
            console.print(f"[dim]Hook {hook_name} triggered[/]")

        manager.register(
            hook_type=hook_type,
            name=hook_name,
            handler=placeholder_handler,
        )

        console.print(f"[green]Hook registered: {hook_name} ({hook_type_str})[/]")

    except ValueError:
        console.print(f"[red]Unknown hook type: {hook_type_str}[/]")


def show_hooks_help(console: Console) -> None:
    """Show hooks command help."""
    table = Table(title="Hooks Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description")

    commands = [
        ("hooks list", "List registered hooks"),
        ("hooks show <name>", "Show hook details"),
        ("hooks stats", "Hook statistics"),
        ("hooks enable <name>", "Enable hook"),
        ("hooks disable <name>", "Disable hook"),
        ("hooks run <type>", "Trigger hook manually"),
        ("hooks register <type> <name>", "Register hook"),
    ]

    for cmd, desc in commands:
        table.add_row(cmd, desc)

    console.print(table)

    # Show hook types
    console.print("\n[bold]Hook Types:[/]")
    for hook_type in HookType:
        console.print(f"  {hook_type.value}")


__all__ = ["run_hooks"]