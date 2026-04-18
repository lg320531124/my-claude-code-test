"""Doctor command - Environment diagnostics."""

import platform
import subprocess
from pathlib import Path

from rich.console import Console
from rich.table import Table


def run_doctor(console: Console) -> None:
    """Run environment diagnostics."""
    table = Table(title="Environment Diagnostics")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details")

    checks = [
        check_python(),
        check_git(),
        check_ripgrep(),
        check_api_key(),
        check_config(),
    ]

    for check in checks:
        status_style = "green" if check["ok"] else "red"
        table.add_row(check["name"], check["status"], check["details"])

    console.print(table)


def check_python() -> dict:
    """Check Python version."""
    version = platform.python_version()
    return {
        "name": "Python",
        "ok": True,
        "status": "OK",
        "details": f"v{version}",
    }


def check_git() -> dict:
    """Check git installation."""
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, text=True)
        version = result.stdout.strip().split()[-1]
        return {
            "name": "Git",
            "ok": True,
            "status": "OK",
            "details": f"v{version}",
        }
    except FileNotFoundError:
        return {
            "name": "Git",
            "ok": False,
            "status": "MISSING",
            "details": "Install git",
        }


def check_ripgrep() -> dict:
    """Check ripgrep installation."""
    try:
        result = subprocess.run(["rg", "--version"], capture_output=True, text=True)
        version = result.stdout.strip().split()[1]
        return {
            "name": "Ripgrep",
            "ok": True,
            "status": "OK",
            "details": f"v{version}",
        }
    except FileNotFoundError:
        return {
            "name": "Ripgrep",
            "ok": False,
            "status": "MISSING",
            "details": "brew install ripgrep",
        }


def check_api_key() -> dict:
    """Check API key."""
    import os
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return {
            "name": "API Key",
            "ok": True,
            "status": "OK",
            "details": "Set",
        }
    return {
        "name": "API Key",
        "ok": False,
        "status": "MISSING",
        "details": "Set ANTHROPIC_API_KEY",
    }


def check_config() -> dict:
    """Check config file."""
    from ..utils.config import Config
    path = Config.get_default_path()
    if path.exists():
        return {
            "name": "Config",
            "ok": True,
            "status": "OK",
            "details": str(path),
        }
    return {
        "name": "Config",
        "ok": True,
        "status": "DEFAULT",
        "details": "Using defaults",
    }