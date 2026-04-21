"""Enhanced Doctor command with asyncio and comprehensive checks."""

from __future__ import annotations
import asyncio
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Optional, ClassVar
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel


@dataclass
class DiagnosticResult:
    """Diagnostic check result."""
    name: str
    category: str
    ok: bool
    status: str
    details: str
    suggestion: Optional[str] = None


async def run_command_async(cmd: List[str], timeout: float = 5.0, cwd: Optional[Path] = None) -> tuple[str, str, int]:
    """Run command asynchronously."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd) if cwd else None,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )
            return stdout.decode(), stderr.decode(), proc.returncode or 0
        except asyncio.TimeoutError:
            # Kill the process on timeout
            proc.kill()
            await proc.wait()
            return "", "Timeout", -1
    except FileNotFoundError:
        return "", "Not found", -1
    except Exception:
        return "", "Error", -1


async def check_python_async() -> DiagnosticResult:
    """Check Python version."""
    version = platform.python_version()
    implementation = platform.python_implementation()

    # Check if version is sufficient (3.9+)
    major, minor = map(int, version.split(".")[:2])
    ok = major >= 3 and minor >= 9

    return DiagnosticResult(
        name="Python",
        category="runtime",
        ok=ok,
        status="OK" if ok else "WARNING",
        details=f"{implementation} {version}",
        suggestion="Python 3.9+ recommended" if not ok else None,
    )


async def check_git_async() -> DiagnosticResult:
    """Check git installation."""
    stdout, stderr, code = await run_command_async(["git", "--version"])

    if code == 0:
        version = stdout.strip().split()[-1]
        return DiagnosticResult(
            name="Git",
            category="tools",
            ok=True,
            status="OK",
            details=f"v{version}",
        )

    return DiagnosticResult(
        name="Git",
        category="tools",
        ok=False,
        status="MISSING",
        details="Not installed",
        suggestion="brew install git",
    )


async def check_ripgrep_async() -> DiagnosticResult:
    """Check ripgrep."""
    stdout, stderr, code = await run_command_async(["rg", "--version"])

    if code == 0:
        version = stdout.strip().split()[1]
        return DiagnosticResult(
            name="Ripgrep",
            category="tools",
            ok=True,
            status="OK",
            details=f"v{version}",
        )

    return DiagnosticResult(
        name="Ripgrep",
        category="tools",
        ok=False,
        status="MISSING",
        details="Not installed",
        suggestion="brew install ripgrep",
    )


async def check_api_key_async() -> DiagnosticResult:
    """Check API key."""
    key = os.environ.get("ANTHROPIC_API_KEY")

    if key:
        # Validate format (starts with sk-ant-)
        valid = key.startswith("sk-ant-") if len(key) > 10 else True
        return DiagnosticResult(
            name="API Key",
            category="auth",
            ok=valid,
            status="OK" if valid else "INVALID",
            details=f"Set ({len(key)} chars)",
            suggestion="Check key format" if not valid else None,
        )

    return DiagnosticResult(
        name="API Key",
        category="auth",
        ok=False,
        status="MISSING",
        details="Not set",
        suggestion="export ANTHROPIC_API_KEY=your-key",
    )


async def check_base_url_async() -> DiagnosticResult:
    """Check base URL."""
    base_url = os.environ.get("ANTHROPIC_BASE_URL")

    if base_url:
        return DiagnosticResult(
            name="Base URL",
            category="config",
            ok=True,
            status="CUSTOM",
            details=base_url,
        )

    return DiagnosticResult(
        name="Base URL",
        category="config",
        ok=True,
        status="DEFAULT",
        details="api.anthropic.com",
    )


async def check_config_file_async(cwd: Path) -> DiagnosticResult:
    """Check config file."""
    config_path = cwd / ".claude" / "config.json"
    global_config = Path.home() / ".claude" / "config.json"

    if config_path.exists():
        return DiagnosticResult(
            name="Config (Project)",
            category="config",
            ok=True,
            status="OK",
            details=str(config_path),
        )

    if global_config.exists():
        return DiagnosticResult(
            name="Config (Global)",
            category="config",
            ok=True,
            status="OK",
            details=str(global_config),
        )

    return DiagnosticResult(
        name="Config",
        category="config",
        ok=True,
        status="DEFAULT",
        details="Using defaults",
        suggestion="Run 'cc init' to create config",
    )


async def check_mcp_config_async(cwd: Path) -> DiagnosticResult:
    """Check MCP config."""
    mcp_path = cwd / ".claude" / "mcp.json"

    if mcp_path.exists():
        import json
        try:
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(None, mcp_path.read_text)
            data = json.loads(content)
            servers = len(data.get("mcpServers", {}))
            return DiagnosticResult(
                name="MCP Config",
                category="mcp",
                ok=True,
                status="OK",
                details=f"{servers} servers configured",
            )
        except Exception:
            return DiagnosticResult(
                name="MCP Config",
                category="mcp",
                ok=False,
                status="INVALID",
                details="Parse error",
                suggestion="Fix JSON format",
            )

    return DiagnosticResult(
        name="MCP Config",
        category="mcp",
        ok=True,
        status="NONE",
        details="No MCP servers",
    )


async def check_python_deps_async(cwd: Path) -> DiagnosticResult:
    """Check Python dependencies."""
    # Check pyproject.toml
    pyproject = cwd / "pyproject.toml"

    if pyproject.exists():
        loop = asyncio.get_event_loop()
        try:
            content = await loop.run_in_executor(None, pyproject.read_text)

            # Check for key dependencies
            required = ["anthropic", "rich", "textual", "httpx"]
            missing = []

            for dep in required:
                if dep not in content.lower():
                    missing.append(dep)

            if missing:
                return DiagnosticResult(
                    name="Dependencies",
                    category="deps",
                    ok=False,
                    status="MISSING",
                    details=f"Missing: {', '.join(missing)}",
                    suggestion=f"pip install {', '.join(missing)}",
                )

            return DiagnosticResult(
                name="Dependencies",
                category="deps",
                ok=True,
                status="OK",
                details="All required deps",
            )
        except Exception:
            pass

    return DiagnosticResult(
        name="Dependencies",
        category="deps",
        ok=True,
        status="UNKNOWN",
        details="No pyproject.toml",
    )


async def check_lsp_async() -> DiagnosticResult:
    """Check LSP servers."""
    lsp_servers = {
        "pylsp": "python",
        "pyright": "python",
        "typescript-language-server": "javascript",
        "gopls": "go",
        "rust-analyzer": "rust",
    }

    installed = []

    for server, lang in lsp_servers.items():
        stdout, _, code = await run_command_async([server, "--version"], timeout=2.0)
        if code == 0:
            installed.append(lang)

    if installed:
        return DiagnosticResult(
            name="LSP Servers",
            category="tools",
            ok=True,
            status="OK",
            details=f"Installed: {', '.join(installed)}",
        )

    return DiagnosticResult(
        name="LSP Servers",
        category="tools",
        ok=True,
        status="NONE",
        details="No LSP servers",
        suggestion="Install LSP servers for better code intelligence",
    )


async def check_memory_async(cwd: Path) -> DiagnosticResult:
    """Check memory directory."""
    memory_dir = cwd / ".claude" / "memory"

    if memory_dir.exists():
        files = list(memory_dir.glob("*.md"))
        return DiagnosticResult(
            name="Memory",
            category="memory",
            ok=True,
            status="OK",
            details=f"{len(files)} memory files",
        )

    return DiagnosticResult(
        name="Memory",
        category="memory",
        ok=True,
        status="NONE",
        details="No memory directory",
    )


async def check_skills_async(cwd: Path) -> DiagnosticResult:
    """Check skills directory."""
    skills_dir = cwd / "skills"

    if skills_dir.exists():
        files = list(skills_dir.glob("*.md"))
        return DiagnosticResult(
            name="Skills",
            category="skills",
            ok=True,
            status="OK",
            details=f"{len(files)} custom skills",
        )

    return DiagnosticResult(
        name="Skills",
        category="skills",
        ok=True,
        status="DEFAULT",
        details="Using built-in skills",
    )


async def check_git_repo_async(cwd: Path) -> DiagnosticResult:
    """Check git repository."""
    stdout, _, code = await run_command_async(["git", "rev-parse", "--git-dir"], cwd=cwd)

    if code == 0:
        # Get branch
        stdout2, _, _ = await run_command_async(["git", "branch", "--show-current"], cwd=cwd)
        branch = stdout2.strip()

        return DiagnosticResult(
            name="Git Repo",
            category="git",
            ok=True,
            status="OK",
            details=f"Branch: {branch}",
        )

    return DiagnosticResult(
        name="Git Repo",
        category="git",
        ok=False,
        status="NONE",
        details="Not a git repo",
        suggestion="git init",
    )


async def run_all_checks_async(cwd: Path) -> List[DiagnosticResult]:
    """Run all diagnostic checks."""
    tasks = [
        check_python_async(),
        check_git_async(),
        check_ripgrep_async(),
        check_api_key_async(),
        check_base_url_async(),
        check_config_file_async(cwd),
        check_mcp_config_async(cwd),
        check_python_deps_async(cwd),
        check_lsp_async(),
        check_memory_async(cwd),
        check_skills_async(cwd),
        check_git_repo_async(cwd),
    ]

    return await asyncio.gather(*tasks)


def display_results(console: Console, results: List[DiagnosticResult]) -> None:
    """Display results in tables."""
    # Group by category
    categories = {}
    for result in results:
        cat = result.category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(result)

    for category, checks in categories.items():
        table = Table(title=f"{category.upper()} Checks")
        table.add_column("Check", style="cyan")
        table.add_column("Status")
        table.add_column("Details")
        table.add_column("Suggestion")

        for check in checks:
            status_style = "green" if check.ok else "red" if check.status == "MISSING" else "yellow"
            suggestion = check.suggestion or ""

            table.add_row(
                check.name,
                f"[{status_style}]{check.status}[/]",
                check.details,
                f"[dim]{suggestion}[/]" if suggestion else "",
            )

        console.print(table)
        console.print()

    # Summary
    ok_count = sum(1 for r in results if r.ok)
    total = len(results)

    console.print(Panel(
        f"Passed: {ok_count}/{total}\n"
        f"Failed: {total - ok_count}",
        title="Diagnostic Summary",
        border_style="green" if ok_count == total else "yellow",
    ))


async def run_doctor_async(console: Console, cwd: Path) -> None:
    """Run async diagnostics."""
    console.print("[bold]Running diagnostics...[/bold]\n")

    results = await run_all_checks_async(cwd)

    display_results(console, results)


def run_doctor(console: Console, cwd: Path = None) -> None:
    """Sync wrapper for doctor."""
    cwd = cwd or Path.cwd()
    asyncio.run(run_doctor_async(console, cwd))
