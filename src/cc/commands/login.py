"""Login command - Authentication."""

from __future__ import annotations
import os
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt


AUTH_FILE = Path.home() / ".claude-code-py" / "auth.json"


def run_login(console: Console) -> None:
    """Run login flow."""
    console.print("[bold]Authentication[/bold]")

    # Check existing
    if AUTH_FILE.exists():
        console.print("[dim]Existing auth found[/dim]")
        overwrite = Prompt.ask("Overwrite?", choices=["y", "n"], default="n")
        if overwrite != "y":
            console.print("[yellow]Keeping existing auth[/yellow]")
            return

    # Get API key
    console.print("\n[bold]API Key[/bold]")
    console.print("Get your API key from: https://console.anthropic.com")
    console.print("Or use compatible API (智谱): https://dashscope.aliyuncs.com")

    api_key = Prompt.ask("API Key (leave empty to use env var)")

    # Get base URL (optional)
    console.print("\n[bold]API Base URL[/bold]")
    console.print("[dim]Default: api.anthropic.com[/dim]")
    console.print("[dim]For 智谱: https://coding.dashscope.aliyuncs.com/apps/anthropic[/dim]")

    base_url = Prompt.ask("Base URL (optional)", default="")
    model = Prompt.ask("Model", default="claude-sonnet-4-6")

    # Save auth
    AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)

    import json
    auth_data = {
        "api_key": api_key if api_key else "USE_ENV_VAR",
        "base_url": base_url if base_url else None,
        "model": model,
    }
    AUTH_FILE.write_text(json.dumps(auth_data, indent=2))

    console.print(f"\n[green]✓ Auth saved to {AUTH_FILE}[/green]")

    if api_key:
        console.print("[dim]Tip: You can also set ANTHROPIC_API_KEY environment variable[/dim]")


def run_logout(console: Console) -> None:
    """Logout - clear auth."""
    if AUTH_FILE.exists():
        AUTH_FILE.unlink()
        console.print("[green]✓ Auth cleared[/green]")
    else:
        console.print("[yellow]No auth file found[/yellow]")

    # Clear env var
    if "ANTHROPIC_API_KEY" in os.environ:
        console.print("[dim]Note: ANTHROPIC_API_KEY env var still set[/dim]")


def get_auth_info() -> dict:
    """Get current auth info."""
    import json

    info = {
        "api_key_set": False,
        "base_url": None,
        "model": None,
    }

    # Check auth file
    if AUTH_FILE.exists():
        try:
            auth_data = json.loads(AUTH_FILE.read_text())
            info["api_key_set"] = auth_data.get("api_key") not in ["USE_ENV_VAR", None, ""]
            info["base_url"] = auth_data.get("base_url")
            info["model"] = auth_data.get("model")
        except json.JSONDecodeError:
            pass

    # Check env
    if os.environ.get("ANTHROPIC_API_KEY"):
        info["api_key_set"] = True
        info["env_key"] = True

    if os.environ.get("ANTHROPIC_BASE_URL"):
        info["base_url"] = os.environ["ANTHROPIC_BASE_URL"]

    if os.environ.get("ANTHROPIC_MODEL"):
        info["model"] = os.environ["ANTHROPIC_MODEL"]

    return info
