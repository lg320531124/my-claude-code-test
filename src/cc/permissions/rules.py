"""Permission rules - Define permission patterns."""

from __future__ import annotations
from typing import Callable

from ..types.permission import PermissionDecision, PermissionRule


# Dangerous command patterns (always ask)
DANGEROUS_BASH_PATTERNS = [
    "rm *",
    "rmdir *",
    "sudo *",
    "chmod *",
    "chown *",
    "mv *",
    "cp *",
    "git push *",
    "git reset --hard *",
    "npm publish",
    "pip install *",
    "docker run *",
    "kubectl delete *",
]

# Safe commands (auto-allow)
SAFE_BASH_PATTERNS = [
    "ls *",
    "cat *",
    "head *",
    "tail *",
    "grep *",
    "find *",
    "git status",
    "git log *",
    "git diff *",
    "git branch",
    "pwd",
    "echo *",
    "which *",
    "file *",
]


def get_default_rules() -> List[PermissionRule]:
    """Get default permission rules."""
    rules = []

    # Dangerous commands -> ASK
    for pattern in DANGEROUS_BASH_PATTERNS:
        rules.append(PermissionRule(
            pattern=f"Bash({pattern})",
            decision=PermissionDecision.ASK,
            priority=100,
        ))

    # Safe commands -> ALLOW
    for pattern in SAFE_BASH_PATTERNS:
        rules.append(PermissionRule(
            pattern=f"Bash({pattern})",
            decision=PermissionDecision.ALLOW,
            priority=50,
        ))

    # Read operations -> ALLOW
    rules.append(PermissionRule(
        pattern="Read",
        decision=PermissionDecision.ALLOW,
        priority=10,
    ))
    rules.append(PermissionRule(
        pattern="Glob",
        decision=PermissionDecision.ALLOW,
        priority=10,
    ))
    rules.append(PermissionRule(
        pattern="Grep",
        decision=PermissionDecision.ALLOW,
        priority=10,
    ))

    # Write operations -> ASK
    rules.append(PermissionRule(
        pattern="Write",
        decision=PermissionDecision.ASK,
        priority=20,
    ))
    rules.append(PermissionRule(
        pattern="Edit",
        decision=PermissionDecision.ASK,
        priority=20,
    ))

    # Web operations -> ALLOW (read-only)
    rules.append(PermissionRule(
        pattern="WebFetch",
        decision=PermissionDecision.ALLOW,
        priority=10,
    ))
    rules.append(PermissionRule(
        pattern="WebSearch",
        decision=PermissionDecision.ALLOW,
        priority=10,
    ))

    # Task operations -> ALLOW
    rules.append(PermissionRule(
        pattern="TaskCreate",
        decision=PermissionDecision.ALLOW,
        priority=5,
    ))
    rules.append(PermissionRule(
        pattern="TaskUpdate",
        decision=PermissionDecision.ALLOW,
        priority=5,
    ))
    rules.append(PermissionRule(
        pattern="TaskList",
        decision=PermissionDecision.ALLOW,
        priority=5,
    ))

    return sorted(rules, key=lambda r: -r.priority)


def matches_pattern(tool_name: str, input_dict: dict, pattern: str) -> bool:
    """Check if tool call matches pattern."""
    # Parse pattern: "ToolName" or "ToolName(subpattern)"
    if "(" in pattern:
        base, subpattern = pattern.split("(")
        subpattern = subpattern.rstrip(")")

        if tool_name != base:
            return False

        # Check subpattern
        return _matches_subpattern(subpattern, input_dict)
    else:
        # Simple tool name match
        return tool_name == pattern


def _matches_subpattern(subpattern: str, input_dict: dict) -> bool:
    """Match subpattern against input."""
    if subpattern == "*":
        return True

    # For Bash tool
    if "command" in input_dict:
        cmd = input_Dict["command"]
        if subpattern.endswith("*"):
            return cmd.startswith(subpattern[:-1])
        return cmd == subpattern

    # For file tools
    if "file_path" in input_dict:
        path = input_Dict["file_path"]
        if subpattern.endswith("*"):
            return path.startswith(subpattern[:-1])
        return path == subpattern or path.endswith(subpattern)

    return False
