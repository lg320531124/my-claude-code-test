"""Enhanced Review command with async code analysis."""

from __future__ import annotations
import asyncio
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel


@dataclass
class ReviewIssue:
    """Review finding."""
    severity: str  # "critical", "high", "medium", "low", "info"
    category: str  # "security", "style", "performance", "bug", "docs"
    file: str
    line: Optional[int]
    message: str
    suggestion: Optional[str] = None


async def run_async_command(cmd: List[str], cwd: Path) -> tuple[str, str, int]:
    """Run command asynchronously."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return stdout.decode(), stderr.decode(), proc.returncode


async def get_staged_diff(cwd: Path) -> str:
    """Get staged diff."""
    stdout, _, _ = await run_async_command(
        ["git", "diff", "--cached"],
        cwd,
    )
    return stdout


async def get_unstaged_diff(cwd: Path) -> str:
    """Get unstaged diff."""
    stdout, _, _ = await run_async_command(
        ["git", "diff"],
        cwd,
    )
    return stdout


async def get_changed_files(cwd: Path) -> List[str]:
    """Get changed files."""
    stdout, _, _ = await run_async_command(
        ["git", "diff", "--name-only", "HEAD"],
        cwd,
    )
    return [f for f in stdout.strip().split("\n") if f]


async def analyze_security(content: str) -> List[ReviewIssue]:
    """Basic security analysis."""
    issues = []

    # Check for hardcoded secrets
    secret_patterns = [
        (r"password\s*=\s*['\"]([^'\"]+)['\"]", "Potential hardcoded password"),
        (r"api_key\s*=\s*['\"]([^'\"]+)['\"]", "Potential hardcoded API key"),
        (r"secret\s*=\s*['\"]([^'\"]+)['\"]", "Potential hardcoded secret"),
        (r"token\s*=\s*['\"]([^'\"]+)['\"]", "Potential hardcoded token"),
    ]

    for pattern, message in secret_patterns:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        for match in matches:
            value = match.group(1)
            if value not in ["xxx", "your_key", "placeholder", "****", "..."]:
                line = content[:match.start()].count("\n") + 1
                issues.append(ReviewIssue(
                    severity="critical",
                    category="security",
                    file="",
                    line=line,
                    message=message,
                    suggestion="Use environment variable or secret manager",
                ))

    # Check for SQL injection patterns
    sql_patterns = [
        (r"f\".*SELECT.*FROM.*{.*}\"", "Potential SQL injection"),
        (r"execute\(.*\+.*\)", "Potential SQL injection via concatenation"),
    ]

    for pattern, message in sql_patterns:
        matches = list(re.finditer(pattern, content))
        for match in matches:
            line = content[:match.start()].count("\n") + 1
            issues.append(ReviewIssue(
                severity="high",
                category="security",
                file="",
                line=line,
                message=message,
                suggestion="Use parameterized queries",
            ))

    return issues


async def analyze_style(content: str) -> List[ReviewIssue]:
    """Basic style analysis."""
    issues = []

    # Check for long lines
    for i, line in enumerate(content.split("\n"), 1):
        if len(line) > 120 and not line.strip().startswith("#"):
            issues.append(ReviewIssue(
                severity="low",
                category="style",
                file="",
                line=i,
                message=f"Line too long ({len(line)} chars)",
                suggestion="Break into multiple lines",
            ))

    return issues


async def analyze_file(file_path: Path) -> List[ReviewIssue]:
    """Analyze a single file."""
    issues = []

    try:
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(None, file_path.read_text)

        security = await analyze_security(content)
        style = await analyze_style(content)

        for issue in security + style:
            issue.file = str(file_path)
            issues.append(issue)

    except Exception:
        pass

    return issues


async def run_review_async(console: Console, cwd: Path) -> List[ReviewIssue]:
    """Run complete code review."""
    all_issues = []

    files = await get_changed_files(cwd)

    if not files:
        console.print("[yellow]No changes to review[/yellow]")
        return []

    console.print(f"[bold]Reviewing {len(files)} files[/bold]")

    for file in files:
        path = cwd / file
        if path.exists() and path.suffix in (".py", ".js", ".ts", ".go", ".rs"):
            console.print(f"[dim]Analyzing: {file}[/dim]")
            issues = await analyze_file(path)
            all_issues.extend(issues)

    if all_issues:
        table = Table(title="Review Findings")
        table.add_column("Severity", style="cyan")
        table.add_column("Category")
        table.add_column("File:Line")
        table.add_column("Message")

        for issue in sorted(all_issues, key=lambda i: i.severity):
            severity_colors = {
                "critical": "red",
                "high": "yellow",
                "medium": "orange",
                "low": "blue",
                "info": "dim",
            }
            color = severity_colors.get(issue.severity, "white")

            location = f"{issue.file}:{issue.line}" if issue.line else issue.file
            table.add_row(
                f"[{color}]{issue.severity}[/]",
                issue.category,
                location,
                issue.message,
            )

        console.print(table)

        critical = sum(1 for i in all_issues if i.severity == "critical")
        high = sum(1 for i in all_issues if i.severity == "high")

        console.print(Panel(
            f"Critical: {critical}\nHigh: {high}\nTotal: {len(all_issues)}",
            title="Review Summary",
            border_style="red" if critical > 0 else "yellow" if high > 0 else "green",
        ))

    return all_issues


def run_review(console: Console, cwd: Path) -> None:
    """Sync wrapper for async review."""
    asyncio.run(run_review_async(console, cwd))


def analyze_diff(diff: str) -> dict:
    """Analyze diff content (sync version for backwards compatibility)."""
    changes = {
        "additions": 0,
        "deletions": 0,
        "files": 0,
    }

    for line in diff.split("\n"):
        if line.startswith("+") and not line.startswith("+++"):
            changes["additions"] += 1
        elif line.startswith("-") and not line.startswith("---"):
            changes["deletions"] += 1
        elif line.startswith("diff --git"):
            changes["files"] += 1

    return changes
