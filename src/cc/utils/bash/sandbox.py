"""Bash Sandbox - Secure command execution sandbox."""

from __future__ import annotations
import asyncio
import os
import re
from typing import Any, Dict, Optional, List, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class SandboxMode(Enum):
    """Sandbox execution modes."""
    STRICT = "strict"
    MODERATE = "moderate"
    PERMISSIVE = "permissive"


@dataclass
class SandboxConfig:
    """Sandbox configuration."""
    mode: SandboxMode = SandboxMode.MODERATE
    allowed_commands: Set[str] = field(default_factory=lambda: {
        "ls", "cat", "head", "tail", "wc", "grep", "find", "echo",
        "pwd", "whoami", "date", "git", "gh", "npm", "node",
        "python", "python3", "pip", "pip3",
    })
    denied_commands: Set[str] = field(default_factory=lambda: {
        "rm", "dd", "mkfs", "format", "shutdown", "reboot",
        "passwd", "useradd", "userdel", "chmod", "chown",
    })
    allowed_paths: Set[str] = field(default_factory=lambda: {"."})
    denied_paths: Set[str] = field(default_factory=set)
    max_timeout: float = 300.0
    max_output_size: int = 1024 * 1024
    log_commands: bool = True


@dataclass
class SandboxResult:
    """Sandbox execution result."""
    allowed: bool
    command: str
    reason: Optional[str] = None
    sanitized_command: Optional[str] = None
    risk_level: str = "unknown"


class BashSandbox:
    """Secure bash command sandbox."""

    def __init__(self, config: SandboxConfig = None):
        self._config = config or SandboxConfig()
        self._command_log: List[str] = []

    def check_command(self, command: str) -> SandboxResult:
        """Check if command is allowed."""
        tokens = self._parse_command(command)
        if not tokens:
            return SandboxResult(
                allowed=False,
                command=command,
                reason="Empty command",
                risk_level="low",
            )

        main_command = tokens[0]

        if main_command in self._config.denied_commands:
            return SandboxResult(
                allowed=False,
                command=command,
                reason=f"Command '{main_command}' is denied",
                risk_level="critical",
            )

        if self._config.mode == SandboxMode.STRICT:
            if main_command not in self._config.allowed_commands:
                return SandboxResult(
                    allowed=False,
                    command=command,
                    reason=f"Command '{main_command}' not in allowed list",
                    risk_level="high",
                )

        dangerous_patterns = [
            r"rm\s+-rf", r">\s*/dev/", r"\|\s*sh", r"\$\(", r"`",
            r"sudo", r"chmod\s+777", r"&&.*rm", r"&&.*sudo",
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, command):
                return SandboxResult(
                    allowed=False,
                    command=command,
                    reason=f"Dangerous pattern: {pattern}",
                    risk_level="critical",
                )

        for token in tokens:
            if self._looks_like_path(token):
                if not self._check_path_allowed(token):
                    return SandboxResult(
                        allowed=False,
                        command=command,
                        reason=f"Path '{token}' not allowed",
                        risk_level="medium",
                    )

        sanitized = self._sanitize_command(command)

        if self._config.log_commands:
            self._command_log.append(command)

        return SandboxResult(
            allowed=True,
            command=command,
            sanitized_command=sanitized,
            risk_level="low",
        )

    def _parse_command(self, command: str) -> List[str]:
        """Parse command into tokens."""
        tokens = []
        current = ""
        in_quote = False
        quote_char = None

        for char in command:
            if char in ('"', "'") and not in_quote:
                in_quote = True
                quote_char = char
            elif char == quote_char and in_quote:
                in_quote = False
                quote_char = None
            elif char == ' ' and not in_quote:
                if current:
                    tokens.append(current)
                    current = ""
            else:
                current += char

        if current:
            tokens.append(current)

        return [t for t in tokens if t and not t.startswith('-')]

    def _looks_like_path(self, token: str) -> bool:
        """Check if token looks like a path."""
        return (
            token.startswith('/') or token.startswith('./') or
            token.startswith('../') or token.startswith('~') or
            token.endswith('/') or '/' in token or
            (token.startswith('.') and len(token) > 1)
        )

    def _check_path_allowed(self, path: str) -> bool:
        """Check if path is allowed."""
        expanded = os.path.expanduser(path)
        try:
            normalized = os.path.normpath(expanded)
        except Exception:
            return False

        for denied in self._config.denied_paths:
            if normalized.startswith(denied):
                return False

        for allowed in self._config.allowed_paths:
            if normalized.startswith(allowed):
                return True

        return False

    def _sanitize_command(self, command: str) -> str:
        """Sanitize command for execution."""
        sanitized = re.sub(r'\$\([^)]*\)', '', command)
        sanitized = re.sub(r'`[^`]*`', '', sanitized)
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        return sanitized

    async def execute_safe(
        self,
        command: str,
        cwd: str = None,
        timeout: float = None,
    ) -> tuple:
        """Execute command in sandbox."""
        result = self.check_command(command)
        if not result.allowed:
            raise PermissionError(f"Command denied: {result.reason}")

        cmd = result.sanitized_command or command
        timeout = min(timeout or 60, self._config.max_timeout)

        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            raise TimeoutError(f"Command timed out after {timeout}s")

        if len(stdout) > self._config.max_output_size:
            stdout = stdout[:self._config.max_output_size]

        return stdout.decode(), stderr.decode(), proc.returncode

    def get_log(self) -> List[str]:
        """Get command log."""
        return self._command_log.copy()

    def clear_log(self) -> None:
        """Clear command log."""
        self._command_log.clear()


_sandbox: Optional[BashSandbox] = None

def get_sandbox() -> BashSandbox:
    """Get global sandbox."""
    global _sandbox
    if _sandbox is None:
        _sandbox = BashSandbox()
    return _sandbox

def check_command(command: str) -> SandboxResult:
    """Check command against sandbox."""
    return get_sandbox().check_command(command)


__all__ = [
    "SandboxMode", "SandboxConfig", "SandboxResult", "BashSandbox",
    "get_sandbox", "check_command",
]
