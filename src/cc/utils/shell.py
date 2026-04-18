"""Shell execution utilities."""

import asyncio
import subprocess
from pathlib import Path


async def run_command(
    command: str,
    cwd: Path | None = None,
    timeout: float = 30.0,
) -> tuple[int, str, str]:
    """Run a shell command asynchronously."""
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(cwd) if cwd else None,
    )

    stdout, stderr = await asyncio.wait_for(
        proc.communicate(),
        timeout=timeout,
    )

    return (
        proc.returncode or 0,
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
    )


def run_command_sync(
    command: str,
    cwd: Path | None = None,
    timeout: float = 30.0,
) -> tuple[int, str, str]:
    """Run a shell command synchronously."""
    proc = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
        timeout=timeout,
    )

    return (proc.returncode, proc.stdout, proc.stderr)