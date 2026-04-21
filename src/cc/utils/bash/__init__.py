"""Bash Utils - Sandbox and readonly validation."""

from __future__ import annotations
import re
import asyncio
from typing import Dict, List, Set, Optional, Any
from pathlib import Path
from dataclasses import dataclass

# Import from submodules
from .sandbox import (
    SandboxMode,
    SandboxConfig as DetailedSandboxConfig,
    SandboxResult,
    BashSandbox as DetailedBashSandbox,
    get_sandbox,
    check_command,
)
from .parse import (
    CommandType,
    ParsedCommand,
    CommandParser,
    get_parser,
    parse_command as parse_command_detailed,
)
from .readonly import (
    RiskLevel,
    ReadonlyCheck,
    ReadonlyValidator,
    get_readonly_validator,
    is_readonly_command,
)
from .execute import (
    ExecuteResult,
    BashExecutor,
    get_executor,
    run_command,
)


@dataclass
class SandboxConfig:
    """Sandbox configuration."""
    enabled: bool = True
    allowed_paths: List[Path] = None
    blocked_commands: Set[str] = None
    readonly_commands: Set[str] = None
    max_timeout: int = 60000


# Read-only commands (never mutate state)
READONLY_COMMANDS: Set[str] = {
    "ls", "cat", "head", "tail", "wc", "stat", "file",
    "grep", "egrep", "fgrep", "rg", "find", "locate",
    "pwd", "whoami", "id", "uname", "hostname", "date",
    "git status", "git log", "git diff", "git show",
    "git branch", "git tag", "git remote", "git config --get",
    "gh pr view", "gh pr list", "gh issue view",
    "docker ps", "docker images", "docker logs",
    "kubectl get", "kubectl describe",
    "npm list", "pip list", "pip show",
    "python --version", "node --version",
}

# Dangerous commands (always blocked)
DANGEROUS_COMMANDS: Set[str] = {
    "rm -rf", "rm -fr", "rmdir /s",
    "dd if=/dev/zero", "dd if=/dev/random",
    "> /dev/sda", "> /dev/hda",
    "chmod -R 777", "chown -R",
    "killall", "pkill -9",
    "shutdown", "reboot", "init 0",
    "mkfs", "fdisk", "format",
    ":(){:|:&};:",  # Fork bomb
}


class BashSandbox:
    """Sandbox for Bash command execution."""

    def __init__(self, config: SandboxConfig = None):
        self.config = config or SandboxConfig()
        self.config.allowed_paths = self.config.allowed_paths or []
        self.config.blocked_commands = self.config.blocked_commands or DANGEROUS_COMMANDS
        self.config.readonly_commands = self.config.readonly_commands or READONLY_COMMANDS

    def is_safe(self, command: str) -> bool:
        """Check if command is safe."""
        # Parse command
        cmd_parts = self._parse_command(command)
        if not cmd_parts:
            return False

        cmd_parts[0]

        # Check dangerous
        for dangerous in self.config.blocked_commands:
            if command.lower().startswith(dangerous.lower()):
                return False

        # Check readonly
        for readonly in self.config.readonly_commands:
            if command.lower().startswith(readonly.lower()):
                return True

        # Check write patterns
        write_patterns = [
            r">\s*",  # Redirect write
            r">>\s*",  # Append
            r"mv\s+",  # Move
            r"cp\s+",  # Copy
            r"mkdir\s+",  # Create dir
            r"touch\s+",  # Create file
            r"chmod\s+",  # Change mode
            r"chown\s+",  # Change owner
            r"rm\s+",  # Remove
            r"rmdir\s+",  # Remove dir
            r"kill\s+",  # Kill process
            r"apt\s+install",  # Install
            r"yum\s+install",
            r"brew\s+install",
            r"pip\s+install",
            r"npm\s+install",
            r"git\s+push",  # Push
            r"git\s+commit",  # Commit
        ]

        for pattern in write_patterns:
            if re.search(pattern, command):
                return False

        return True

    def is_readonly(self, command: str) -> bool:
        """Check if command is read-only."""
        for readonly in self.config.readonly_commands:
            if command.lower().startswith(readonly.lower()):
                return True
        return False

    def get_risk_level(self, command: str) -> str:
        """Get risk level: low, medium, high, critical."""
        if self.is_readonly(command):
            return "low"

        # Check dangerous patterns
        dangerous_patterns = [
            (r"rm\s+-rf", "critical"),
            (r"rm\s+-fr", "critical"),
            (r">\s*/dev/", "critical"),
            (r"sudo\s+", "high"),
            (r"chmod\s+777", "high"),
            (r"pip\s+install", "medium"),
            (r"npm\s+install", "medium"),
            (r"git\s+push", "medium"),
            (r"git\s+commit", "medium"),
            (r"rm\s+", "high"),
            (r"mv\s+", "medium"),
            (r"cp\s+", "medium"),
        ]

        for pattern, level in dangerous_patterns:
            if re.search(pattern, command):
                return level

        return "medium"

    def validate_path(self, path: Path) -> bool:
        """Validate path is in allowed area."""
        if not self.config.allowed_paths:
            return True

        for allowed in self.config.allowed_paths:
            try:
                path.resolve().relative_to(allowed.resolve())
                return True
            except ValueError:
                pass

        return False

    def _parse_command(self, command: str) -> List[str]:
        """Parse command into parts."""
        # Handle sudo, timeout, env vars
        parts = command.strip().split()

        # Skip sudo, timeout, etc.
        skip_prefixes = ["sudo", "timeout", "env", "nice", "ionice", "nohup"]

        while parts and parts[0] in skip_prefixes:
            parts = parts[1:]
            # Handle timeout number
            if parts and parts[0].isdigit():
                parts = parts[1:]

        return parts


def parse_command(command: str) -> Dict[str, Any]:
    """Parse command details."""
    parts = command.strip().split()

    result = {
        "raw": command,
        "base": "",
        "args": [],
        "flags": [],
        "has_pipe": "|" in command,
        "has_redirect": ">" in command or ">>" in command,
        "has_and": "&&" in command,
        "is_sudo": command.lower().startswith("sudo"),
        "is_timeout": command.lower().startswith("timeout"),
    }

    # Get base command
    cmd_parts = parts.copy()
    skip_prefixes = ["sudo", "timeout"]

    while cmd_parts and cmd_parts[0].lower() in skip_prefixes:
        cmd_parts = cmd_parts[1:]
        if cmd_parts and cmd_parts[0].isdigit():
            cmd_parts = cmd_parts[1:]

    if cmd_parts:
        result["base"] = cmd_parts[0]
        result["args"] = cmd_parts[1:]

        # Extract flags
        result["flags"] = [a for a in cmd_parts[1:] if a.startswith("-")]

    return result


async def validate_command(command: str, sandbox: BashSandbox = None) -> Dict[str, Any]:
    """Validate command async."""
    sandbox = sandbox or BashSandbox()

    return {
        "command": command,
        "is_safe": sandbox.is_safe(command),
        "is_readonly": sandbox.is_readonly(command),
        "risk_level": sandbox.get_risk_level(command),
        "parsed": parse_command(command),
    }


__all__ = [
    # Legacy API
    "SandboxConfig",
    "READONLY_COMMANDS",
    "DANGEROUS_COMMANDS",
    "BashSandbox",
    "parse_command",
    "validate_command",
    # New API
    "SandboxMode",
    "DetailedSandboxConfig",
    "SandboxResult",
    "DetailedBashSandbox",
    "get_sandbox",
    "check_command",
    "CommandType",
    "ParsedCommand",
    "CommandParser",
    "get_parser",
    "parse_command_detailed",
    "RiskLevel",
    "ReadonlyCheck",
    "ReadonlyValidator",
    "get_readonly_validator",
    "is_readonly_command",
    "ExecuteResult",
    "BashExecutor",
    "get_executor",
    "run_command",
]