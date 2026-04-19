"""Permission persistence - Save decisions to file."""

from __future__ import annotations
import json
import time
from pathlib import Path
from typing import ClassVar

from ..types.permission import PermissionDecision


class PermissionPersistence:
    """Manages persistent permission decisions."""

    FILENAME: ClassVar[str] = ".claude/permissions.json"

    def __init__(self, project_dir: Optional[Path] = None):
        self.project_dir = project_dir or Path.cwd()
        self.file_path = self.project_dir / self.FILENAME
        self.decisions: Dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        """Load saved decisions."""
        if self.file_path.exists():
            try:
                with open(self.file_path) as f:
                    self.decisions = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.decisions = {}

    def _save(self) -> None:
        """Save decisions to file."""
        # Ensure directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.file_path, "w") as f:
            json.dump(self.decisions, f, indent=2)

    def get_decision(self, pattern: str) -> PermissionDecision | None:
        """Get saved decision for a pattern."""
        entry = self.decisions.get(pattern)
        if entry:
            # Check if still valid (not expired)
            if entry.get("expires", 0) > time.time():
                return PermissionDecision(entry["decision"])
        return None

    def save_decision(
        self,
        pattern: str,
        decision: PermissionDecision,
        expires_days: int = 30,
    ) -> None:
        """Save a decision for future use."""
        self.decisions[pattern] = {
            "decision": decision.value,
            "timestamp": time.time(),
            "expires": time.time() + (expires_days * 86400),
        }
        self._save()

    def clear_expired(self) -> int:
        """Remove expired decisions."""
        now = time.time()
        expired = [k for k, v in self.decisions.items() if v.get("expires", 0) < now]
        for key in expired:
            del self.decisions[key]
        if expired:
            self._save()
        return len(expired)

    def clear_all(self) -> None:
        """Clear all saved decisions."""
        self.decisions = {}
        self._save()

    def list_decisions(self) -> List[dict]:
        """List all saved decisions."""
        now = time.time()
        result = []
        for pattern, entry in self.decisions.items():
            is_expired = entry.get("expires", 0) < now
            result.append({
                "pattern": pattern,
                "decision": entry["decision"],
                "timestamp": entry.get("timestamp", 0),
                "expires": entry.get("expires", 0),
                "expired": is_expired,
            })
        return sorted(result, key=lambda x: x["timestamp"], reverse=True)


class SessionMemory:
    """Session-level permission memory."""

    def __init__(self):
        self.decisions: Dict[str, PermissionDecision] = {}
        self.pattern_decisions: Dict[str, PermissionDecision] = {}

    def get(self, tool_name: str, input_hash: str) -> PermissionDecision | None:
        """Get session decision."""
        key = f"{tool_name}:{input_hash}"
        return self.decisions.get(key)

    def set(self, tool_name: str, input_hash: str, decision: PermissionDecision) -> None:
        """Set session decision."""
        key = f"{tool_name}:{input_hash}"
        self.decisions[key] = decision

    def get_pattern(self, pattern: str) -> PermissionDecision | None:
        """Get pattern decision."""
        return self.pattern_decisions.get(pattern)

    def set_pattern(self, pattern: str, decision: PermissionDecision) -> None:
        """Set pattern decision."""
        self.pattern_decisions[pattern] = decision

    def clear(self) -> None:
        """Clear all session decisions."""
        self.decisions = {}
        self.pattern_decisions = {}


def hash_input(tool_name: str, tool_input: dict) -> str:
    """Create a hash for tool input."""
    import hashlib

    # Normalize input
    if tool_name == "Bash":
        # Hash command only
        key = tool_input.get("command", "")
    elif tool_name in ("Read", "Write", "Edit"):
        # Hash file path
        key = tool_input.get("file_path", "")
    else:
        # Hash full input
        key = json.dumps(tool_input, sort_keys=True)

    return hashlib.md5(key.encode()).hexdigest()[:16]
