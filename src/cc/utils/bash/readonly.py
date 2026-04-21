"""Bash Readonly - Read-only command validation."""

from __future__ import annotations
import re
from typing import Dict, Optional, List, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(Enum):
    """Command risk levels."""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ReadonlyCheck:
    """Readonly check result."""
    command: str
    is_readonly: bool
    risk_level: RiskLevel
    reason: str = ""
    main_command: str = ""
    suggestions: List[str] = field(default_factory=list)


ALWAYS_SAFE: Set[str] = {
    "cal", "uptime", "cat", "head", "tail", "wc", "stat",
    "strings", "hexdump", "od", "nl", "id", "uname",
    "free", "df", "du", "locale", "groups", "nproc",
    "basename", "dirname", "realpath", "cut", "paste",
    "tr", "column", "tac", "rev", "fold", "expand",
    "unexpand", "fmt", "comm", "cmp", "numfmt", "readlink",
    "diff", "true", "false", "sleep", "which", "type",
    "expr", "test", "getconf", "seq", "tsort", "pr",
    "echo", "printf", "ls", "cd", "find", "pwd", "whoami",
    "alias", "history", "arch",
}

SAFE_WITH_ARGS: Dict[str, Set[str]] = {
    "git": {
        "status", "log", "diff", "show", "blame", "branch",
        "tag", "remote", "ls-files", "ls-remote", "config",
        "rev-parse", "describe", "stash", "reflog",
    },
    "gh": {
        "pr", "issue", "repo", "release", "run", "workflow",
        "auth", "api", "browse", "gist",
    },
    "docker": {
        "ps", "images", "logs", "inspect", "top", "stats",
    },
}

NEVER_SAFE: Set[str] = {
    "rm", "dd", "mkfs", "format", "shutdown", "reboot",
    "passwd", "useradd", "userdel", "groupadd",
    "chmod", "chown", "chgrp", "umount", "mount",
    "kill", "killall", "pkill", "xkill",
    "iptables", "ufw", "firewall-cmd",
    "sudo", "su", "doas",
    "eval", "exec", "source",
    "crontab", "at", "batch",
    "systemctl", "service",
    "apt", "yum", "dnf", "pacman", "brew",
}

DANGER_PATTERNS: List[str] = [
    r"rm\s+-[rf]", r">\s*/dev/", r"\|\s*sh",
    r"\$\(", r"`[^`]*`", r"sudo\s+",
    r"chmod\s+[0-7]", r"chown\s+",
    r"mkfs", r"dd\s+if=", r"shutdown",
    r"reboot", r"kill\s+-9",
]


class ReadonlyValidator:
    """Validate commands as read-only."""

    def __init__(self):
        self._always_safe = ALWAYS_SAFE.copy()
        self._safe_with_args = SAFE_WITH_ARGS.copy()
        self._never_safe = NEVER_SAFE.copy()
        self._danger_patterns = DANGER_PATTERNS.copy()

    def check(self, command: str) -> ReadonlyCheck:
        """Check if command is read-only."""
        main_cmd, args = self._extract_command(command)

        if not main_cmd:
            return ReadonlyCheck(
                command=command,
                is_readonly=False,
                risk_level=RiskLevel.LOW,
                reason="Empty command",
            )

        for pattern in self._danger_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return ReadonlyCheck(
                    command=command,
                    is_readonly=False,
                    risk_level=RiskLevel.CRITICAL,
                    reason=f"Dangerous pattern: {pattern}",
                    main_command=main_cmd,
                )

        if main_cmd in self._never_safe:
            return ReadonlyCheck(
                command=command,
                is_readonly=False,
                risk_level=RiskLevel.CRITICAL,
                reason=f"Command '{main_cmd}' is never safe",
                main_command=main_cmd,
            )

        if main_cmd in self._always_safe:
            return ReadonlyCheck(
                command=command,
                is_readonly=True,
                risk_level=RiskLevel.SAFE,
                reason=f"Command '{main_cmd}' is always safe",
                main_command=main_cmd,
            )

        if main_cmd in self._safe_with_args:
            safe_args = self._safe_with_args[main_cmd]
            first_arg = args[0] if args else ""

            if first_arg in safe_args:
                return ReadonlyCheck(
                    command=command,
                    is_readonly=True,
                    risk_level=RiskLevel.LOW,
                    reason=f"'{main_cmd} {first_arg}' is safe",
                    main_command=main_cmd,
                )

        if self._looks_readonly(command):
            return ReadonlyCheck(
                command=command,
                is_readonly=True,
                risk_level=RiskLevel.LOW,
                reason="Command appears read-only",
                main_command=main_cmd,
            )

        return ReadonlyCheck(
            command=command,
            is_readonly=False,
            risk_level=RiskLevel.MEDIUM,
            reason=f"Command '{main_cmd}' requires review",
            main_command=main_cmd,
            suggestions=self._get_suggestions(main_cmd),
        )

    def _extract_command(self, command: str) -> Tuple[str, List[str]]:
        """Extract main command and args."""
        tokens = command.strip().split()
        if not tokens:
            return "", []

        skip_prefixes = {"sudo", "timeout", "env", "time", "nohup"}
        while tokens and tokens[0] in skip_prefixes:
            tokens = tokens[1:]

        if not tokens:
            return "", []

        main = tokens[0]
        args = [a for a in tokens[1:] if not a.startswith("-") and "=" not in a]

        return main, args

    def _looks_readonly(self, command: str) -> bool:
        """Check if command looks read-only."""
        readonly_indicators = [
            "--help", "-h", "--version", "-V",
            "list", "show", "view", "status", "info",
            "get", "describe", "inspect", "check",
        ]
        return any(ind in command for ind in readonly_indicators)

    def _get_suggestions(self, main_cmd: str) -> List[str]:
        """Get safe alternatives."""
        suggestions = {
            "rm": ["Use 'ls' to view files first"],
            "curl": ["Use 'WebFetch' tool"],
            "wget": ["Use 'WebFetch' tool"],
            "apt": ["Use specific package commands"],
            "npm": ["Use 'npm run' for scripts"],
        }
        return suggestions.get(main_cmd, [])


_validator: Optional[ReadonlyValidator] = None

def get_readonly_validator() -> ReadonlyValidator:
    """Get global validator."""
    global _validator
    if _validator is None:
        _validator = ReadonlyValidator()
    return _validator

def is_readonly_command(command: str) -> bool:
    """Check if command is read-only."""
    result = get_readonly_validator().check(command)
    return result.is_readonly


__all__ = [
    "RiskLevel", "ReadonlyCheck", "ReadonlyValidator",
    "get_readonly_validator", "is_readonly_command",
]
