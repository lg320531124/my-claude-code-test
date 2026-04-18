"""Commands module - All slash commands."""

from pathlib import Path
from rich.console import Console

from ..core.session import Session
from ..utils.config import Config


async def handle_command(command: str, session: Session, config: Config) -> None:
    """Handle a slash command."""
    parts = command.strip().split()
    cmd = parts[0].lower()
    args = parts[1:] if len(parts) > 1 else []

    console = Console()

    # Core commands
    if cmd == "/help":
        show_help(console)
    elif cmd == "/doctor":
        from .doctor import run_doctor
        run_doctor(console)
    elif cmd == "/clear":
        session.clear_messages()
        console.print("[green]Session cleared[/green]")
    elif cmd == "/compact":
        from .compact import run_compact
        run_compact(console, session)
    elif cmd == "/config":
        show_config(console, config)
    elif cmd == "/tasks":
        show_tasks(console)
    elif cmd == "/todos":
        show_todos(console)

    # Git commands
    elif cmd == "/commit":
        from .commit import run_commit
        message = args[0] if args else None
        run_commit(console, session.cwd, message)
    elif cmd == "/review":
        from .review import run_review
        run_review(console, session.cwd)
    elif cmd == "/diff":
        from .diff import run_diff
        file = args[0] if args else None
        staged = "--unstaged" not in args
        run_diff(console, session.cwd, file, staged)

    # MCP/Memory/Skills
    elif cmd == "/mcp":
        from .mcp import run_mcp
        action = args[0] if args else "list"
        run_mcp(console, action)
    elif cmd == "/memory":
        from .memory import run_memory
        action = args[0] if args else "list"
        name = args[1] if len(args) > 1 else None
        run_memory(console, action, name)
    elif cmd == "/skills":
        from .skills import run_skills
        action = args[0] if args else "list"
        name = args[1] if len(args) > 1 else None
        run_skills(console, action, name)

    # Auth commands
    elif cmd == "/login":
        from .login import run_login
        run_login(console)
    elif cmd == "/logout":
        from .login import run_logout
        run_logout(console)

    # UI commands
    elif cmd == "/theme":
        from .theme import run_theme
        theme = args[0] if args else None
        run_theme(console, theme)
    elif cmd == "/vim":
        from .vim import run_vim
        enable = None
        if args and args[0] in ["on", "enable", "true"]:
            enable = True
        elif args and args[0] in ["off", "disable", "false"]:
            enable = False
        run_vim(console, enable)

    # Usage commands
    elif cmd == "/cost":
        from .cost import run_cost
        run_cost(console)
    elif cmd == "/usage":
        from .usage import run_usage
        period = args[0] if args else "session"
        run_usage(console, period)

    # Session commands
    elif cmd == "/resume":
        from .resume import run_resume
        session_id = args[0] if args else None
        resumed = run_resume(console, session_id)
        if resumed:
            session.messages = resumed.messages
            session.session_id = resumed.session_id
    elif cmd == "/save":
        from .resume import save_session
        path = save_session(session)
        console.print(f"[green]Session saved to {path}[/green]")

    # Init
    elif cmd == "/init":
        from .init import run_init
        run_init(console, session.cwd)

    # Model
    elif cmd == "/model":
        if args:
            config.api.model = args[0]
            console.print(f"[green]Model changed to: {args[0]}[/green]")
        else:
            console.print(f"[dim]Current model: {config.api.model}[/dim]")

    # Exit
    elif cmd == "/exit" or cmd == "/quit":
        console.print("[yellow]Goodbye![/yellow]")
        raise SystemExit(0)

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
        # Core
        ("/help", "Show this help"),
        ("/doctor", "Run diagnostics"),
        ("/clear", "Clear session"),
        ("/compact", "Compress context"),
        ("/config", "Show configuration"),
        ("/tasks", "Show tasks"),
        ("/todos", "Show todo list"),
        # Git
        ("/commit [msg]", "Create git commit"),
        ("/review", "Review changes"),
        ("/diff [file]", "View diff"),
        # MCP/Memory/Skills
        ("/mcp [list]", "MCP servers"),
        ("/memory [list]", "Persistent memories"),
        ("/skills [list]", "Available skills"),
        # Auth
        ("/login", "Set API credentials"),
        ("/logout", "Clear credentials"),
        # UI
        ("/theme [name]", "Change theme"),
        ("/vim [on|off]", "Toggle vim mode"),
        # Usage
        ("/cost", "Show usage cost"),
        ("/usage [period]", "Detailed usage"),
        # Session
        ("/resume [id]", "Resume session"),
        ("/save", "Save session"),
        ("/init", "Initialize project"),
        ("/model [name]", "Change model"),
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
    table.add_row("Theme", config.ui.theme)
    table.add_row("Vim Mode", str(getattr(config.ui, "vim_mode", False)))
    table.add_row("Allow Rules", str(config.permissions.allow))
    table.add_row("Ask Rules", str(config.permissions.ask))
    table.add_row("Deny Rules", str(config.permissions.deny))

    console.print(table)


def show_tasks(console: Console) -> None:
    """Show current tasks."""
    from ..tools.task import _tasks

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


def show_todos(console: Console) -> None:
    """Show todo list."""
    from ..tools.todo import get_todos

    todos = get_todos()

    if not todos:
        console.print("[dim]No todos[/dim]")
        return

    console.print("[bold]Todo List[/bold]")
    for todo in todos:
        status_icon = "○" if todo["status"] == "pending" else "●"
        console.print(f"{status_icon} {todo['id']}. {todo['content']}")