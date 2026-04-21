"""Bash Parse - Command parsing utilities."""

from __future__ import annotations
import re
import shlex
from typing import Any, Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum


class CommandType(Enum):
    """Command types."""
    SIMPLE = "simple"
    PIPE = "pipe"
    AND = "and"
    OR = "or"
    SUBSHELL = "subshell"
    BACKGROUND = "background"
    REDIRECTION = "redirection"


@dataclass
class ParsedCommand:
    """Parsed command."""
    raw: str
    type: CommandType = CommandType.SIMPLE
    tokens: List[str] = field(default_factory=list)
    main_command: str = ""
    arguments: List[str] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)
    stdin_file: Optional[str] = None
    stdout_file: Optional[str] = None
    stderr_file: Optional[str] = None
    pipe_to: Optional[str] = None
    and_then: Optional[str] = None
    or_else: Optional[str] = None
    env_vars: Dict[str, str] = field(default_factory=dict)
    subshell: bool = False
    background: bool = False


class CommandParser:
    """Parse bash commands."""

    def parse(self, command: str) -> ParsedCommand:
        """Parse command string."""
        result = ParsedCommand(raw=command)

        if command.rstrip().endswith("&"):
            result.background = True
            command = command.rstrip()[:-1].strip()
            result.type = CommandType.BACKGROUND

        if command.startswith("(") and command.endswith(")"):
            result.subshell = True
            command = command[1:-1].strip()
            result.type = CommandType.SUBSHELL

        if "|" in command and "||" not in command:
            parts = self._split_pipe(command)
            if len(parts) > 1:
                result.pipe_to = parts[1].strip()
                command = parts[0].strip()
                result.type = CommandType.PIPE

        if "&&" in command:
            parts = command.split("&&", 1)
            result.and_then = parts[1].strip()
            command = parts[0].strip()
            result.type = CommandType.AND

        if "||" in command:
            parts = command.split("||", 1)
            result.or_else = parts[1].strip()
            command = parts[0].strip()
            result.type = CommandType.OR

        command, env_vars = self._extract_env_vars(command)
        result.env_vars = env_vars

        command, redirs = self._extract_redirections(command)
        result.stdin_file = redirs.get("stdin")
        result.stdout_file = redirs.get("stdout")
        result.stderr_file = redirs.get("stderr")
        if redirs:
            result.type = CommandType.REDIRECTION

        try:
            tokens = shlex.split(command)
        except ValueError:
            tokens = command.split()

        result.tokens = tokens

        if tokens:
            result.main_command = tokens[0]
            for token in tokens[1:]:
                if token.startswith("-"):
                    result.flags.append(token)
                else:
                    result.arguments.append(token)

        return result

    def _split_pipe(self, command: str) -> List[str]:
        """Split on pipe (not ||)."""
        parts = []
        current = ""
        i = 0

        while i < len(command):
            if command[i] == "|":
                if i + 1 < len(command) and command[i + 1] == "|":
                    current += "||"
                    i += 2
                else:
                    parts.append(current)
                    current = ""
                    i += 1
            else:
                current += command[i]
                i += 1

        parts.append(current)
        return parts

    def _extract_env_vars(self, command: str) -> Tuple[str, Dict[str, str]]:
        """Extract environment variable assignments."""
        env_vars = {}
        pattern = r'^([A-Za-z_][A-Za-z0-9_]*)=([^\s]+)\s*'

        while True:
            match = re.match(pattern, command)
            if not match:
                break

            var_name = match.group(1)
            var_value = match.group(2)

            if var_value.startswith('"') and var_value.endswith('"'):
                var_value = var_value[1:-1]
            elif var_value.startswith("'") and var_value.endswith("'"):
                var_value = var_value[1:-1]

            env_vars[var_name] = var_value
            command = command[match.end():]

        return command, env_vars

    def _extract_redirections(self, command: str) -> Tuple[str, Dict[str, str]]:
        """Extract redirections."""
        redirs = {}

        stdout_match = re.search(r'>>?\s*([^\s]+)', command)
        if stdout_match:
            redirs["stdout"] = stdout_match.group(1)
            command = command.replace(stdout_match.group(0), "")

        stderr_match = re.search(r'2>>?\s*([^\s]+)', command)
        if stderr_match:
            redirs["stderr"] = stderr_match.group(1)
            command = command.replace(stderr_match.group(0), "")

        stdin_match = re.search(r'<\s*([^\s]+)', command)
        if stdin_match:
            redirs["stdin"] = stdin_match.group(1)
            command = command.replace(stdin_match.group(0), "")

        combined_match = re.search(r'&>\s*([^\s]+)', command)
        if combined_match:
            redirs["stdout"] = combined_match.group(1)
            redirs["stderr"] = combined_match.group(1)
            command = command.replace(combined_match.group(0), "")

        return command.strip(), redirs

    def is_readonly(self, command: str) -> bool:
        """Check if command is read-only."""
        parsed = self.parse(command)
        main = parsed.main_command

        readonly_commands = {
            "ls", "cat", "head", "tail", "wc", "grep", "egrep", "fgrep",
            "find", "locate", "which", "whereis", "type",
            "echo", "printf", "pwd", "whoami", "id", "uname",
            "date", "cal", "uptime", "hostname",
            "df", "du", "free", "top", "ps", "pgrep",
            "git", "gh", "npm", "node", "python", "python3",
        }

        if main in readonly_commands:
            return True

        if main == "git":
            readonly_git = {
                "status", "log", "diff", "show", "blame", "branch",
                "tag", "remote", "ls-files", "config", "rev-parse",
            }
            subcmd = parsed.arguments[0] if parsed.arguments else ""
            return subcmd in readonly_git

        return False

    def get_command_token(self, command: str) -> str:
        """Get first command token."""
        parsed = self.parse(command)
        if parsed.main_command == "sudo":
            return parsed.arguments[0] if parsed.arguments else ""
        return parsed.main_command


_parser: Optional[CommandParser] = None

def get_parser() -> CommandParser:
    """Get global parser."""
    global _parser
    if _parser is None:
        _parser = CommandParser()
    return _parser

def parse_command(command: str) -> ParsedCommand:
    """Parse command."""
    return get_parser().parse(command)


__all__ = [
    "CommandType", "ParsedCommand", "CommandParser",
    "get_parser", "parse_command",
]
