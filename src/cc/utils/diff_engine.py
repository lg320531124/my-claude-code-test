"""Diff Engine - Generate and apply diffs."""

from __future__ import annotations
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class DiffType(Enum):
    """Diff type."""
    UNIFIED = "unified"
    CONTEXT = "context"
    SIDE_BY_SIDE = "side_by_side"


class ChangeType(Enum):
    """Change type."""
    ADD = "add"
    DELETE = "delete"
    MODIFY = "modify"
    CONTEXT = "context"


@dataclass
class DiffLine:
    """A line in diff."""
    type: ChangeType
    content: str
    old_line: Optional[int] = None
    new_line: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiffHunk:
    """A hunk in diff."""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    header: str = ""
    lines: List[DiffLine] = field(default_factory=list)


@dataclass
class DiffResult:
    """Diff result."""
    hunks: List[DiffHunk] = field(default_factory=list)
    old_path: str = ""
    new_path: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        """Check if there are changes."""
        return len(self.hunks) > 0

    @property
    def additions(self) -> int:
        """Count additions."""
        return sum(
            1 for hunk in self.hunks
            for line in hunk.lines
            if line.type == ChangeType.ADD
        )

    @property
    def deletions(self) -> int:
        """Count deletions."""
        return sum(
            1 for hunk in self.hunks
            for line in hunk.lines
            if line.type == ChangeType.DELETE
        )

    @property
    def modifications(self) -> int:
        """Count modifications (add + delete pairs)."""
        return min(self.additions, self.deletions)


@dataclass
class DiffConfig:
    """Diff configuration."""
    context_lines: int = 3
    ignore_whitespace: bool = False
    ignore_case: bool = False
    show_line_numbers: bool = True
    max_hunks: int = 100


class DiffEngine:
    """Generate and apply diffs."""

    def __init__(self, config: Optional[DiffConfig] = None):
        self.config = config or DiffConfig()

    def diff(
        self,
        old_content: str,
        new_content: str,
        old_path: str = "",
        new_path: str = "",
    ) -> DiffResult:
        """Generate diff between two contents."""
        old_lines = old_content.split("\n")
        new_lines = new_content.split("\n")

        hunks = self._compute_hunks(old_lines, new_lines)

        return DiffResult(
            hunks=hunks,
            old_path=old_path,
            new_path=new_path,
        )

    def _compute_hunks(
        self,
        old_lines: List[str],
        new_lines: List[str],
    ) -> List[DiffHunk]:
        """Compute diff hunks."""
        # Simple line-by-line comparison
        hunks = []
        current_hunk: Optional[DiffHunk] = None

        old_idx = 0
        new_idx = 0

        while old_idx < len(old_lines) or new_idx < len(new_lines):
            old_line = old_lines[old_idx] if old_idx < len(old_lines) else None
            new_line = new_lines[new_idx] if new_idx < len(new_lines) else None

            # Compare lines
            if old_line == new_line:
                # Context line
                if current_hunk is None:
                    old_idx += 1
                    new_idx += 1
                    continue

                diff_line = DiffLine(
                    type=ChangeType.CONTEXT,
                    content=old_line or "",
                    old_line=old_idx + 1,
                    new_line=new_idx + 1,
                )
                current_hunk.lines.append(diff_line)
                current_hunk.old_count += 1
                current_hunk.new_count += 1

                # Check if hunk should end
                context_count = sum(
                    1 for l in current_hunk.lines[-self.config.context_lines:]
                    if l.type == ChangeType.CONTEXT
                )
                if context_count >= self.config.context_lines:
                    hunks.append(current_hunk)
                    current_hunk = None

                old_idx += 1
                new_idx += 1

            elif old_line is not None and new_line is not None:
                # Modification
                if current_hunk is None:
                    current_hunk = DiffHunk(
                        old_start=old_idx + 1,
                        old_count=0,
                        new_start=new_idx + 1,
                        new_count=0,
                    )

                # Delete old line
                diff_line = DiffLine(
                    type=ChangeType.DELETE,
                    content=old_line,
                    old_line=old_idx + 1,
                )
                current_hunk.lines.append(diff_line)
                current_hunk.old_count += 1

                # Add new line
                diff_line = DiffLine(
                    type=ChangeType.ADD,
                    content=new_line,
                    new_line=new_idx + 1,
                )
                current_hunk.lines.append(diff_line)
                current_hunk.new_count += 1

                old_idx += 1
                new_idx += 1

            elif old_line is not None:
                # Deletion only
                if current_hunk is None:
                    current_hunk = DiffHunk(
                        old_start=old_idx + 1,
                        old_count=0,
                        new_start=new_idx + 1,
                        new_count=0,
                    )

                diff_line = DiffLine(
                    type=ChangeType.DELETE,
                    content=old_line,
                    old_line=old_idx + 1,
                )
                current_hunk.lines.append(diff_line)
                current_hunk.old_count += 1
                old_idx += 1

            elif new_line is not None:
                # Addition only
                if current_hunk is None:
                    current_hunk = DiffHunk(
                        old_start=old_idx + 1,
                        old_count=0,
                        new_start=new_idx + 1,
                        new_count=0,
                    )

                diff_line = DiffLine(
                    type=ChangeType.ADD,
                    content=new_line,
                    new_line=new_idx + 1,
                )
                current_hunk.lines.append(diff_line)
                current_hunk.new_count += 1
                new_idx += 1

        # Add remaining hunk
        if current_hunk is not None:
            hunks.append(current_hunk)

        return hunks

    def apply_patch(
        self,
        content: str,
        diff_result: DiffResult,
    ) -> str:
        """Apply patch to content."""
        lines = content.split("\n")

        for hunk in reversed(diff_result.hunks):
            # Apply each hunk
            old_idx = hunk.old_start - 1

            # Remove deleted lines
            delete_count = sum(
                1 for l in hunk.lines if l.type == ChangeType.DELETE
            )

            # Get lines to insert
            insert_lines = [
                l.content for l in hunk.lines
                if l.type == ChangeType.ADD
            ]

            # Apply changes
            lines = (
                lines[:old_idx]
                + insert_lines
                + lines[old_idx + delete_count:]
            )

        return "\n".join(lines)

    def format_diff(self, diff_result: DiffResult) -> str:
        """Format diff as unified diff."""
        lines = []

        # Header
        if diff_result.old_path:
            lines.append(f"--- {diff_result.old_path}")
        if diff_result.new_path:
            lines.append(f"+++ {diff_result.new_path}")

        # Hunks
        for hunk in diff_result.hunks:
            # Hunk header
            lines.append(
                f"@@ -{hunk.old_start},{hunk.old_count} "
                f"+{hunk.new_start},{hunk.new_count} @@"
            )

            # Lines
            for diff_line in hunk.lines:
                if diff_line.type == ChangeType.ADD:
                    lines.append(f"+{diff_line.content}")
                elif diff_line.type == ChangeType.DELETE:
                    lines.append(f"-{diff_line.content}")
                else:
                    lines.append(f" {diff_line.content}")

        return "\n".join(lines)

    def parse_diff(self, diff_text: str) -> DiffResult:
        """Parse unified diff text."""
        lines = diff_text.split("\n")
        hunks = []
        old_path = ""
        new_path = ""

        current_hunk: Optional[DiffHunk] = None

        for line in lines:
            # Parse header
            if line.startswith("---"):
                old_path = line[4:].strip()
            elif line.startswith("+++"):
                new_path = line[4:].strip()
            elif line.startswith("@@"):
                # Parse hunk header
                match = re.match(
                    r"@@ -(\d+),(\d+) \+(\d+),(\d+) @@",
                    line,
                )
                if match:
                    if current_hunk is not None:
                        hunks.append(current_hunk)

                    current_hunk = DiffHunk(
                        old_start=int(match.group(1)),
                        old_count=int(match.group(2)),
                        new_start=int(match.group(3)),
                        new_count=int(match.group(4)),
                    )
            elif current_hunk is not None:
                # Parse diff line
                if line.startswith("+"):
                    current_hunk.lines.append(
                        DiffLine(type=ChangeType.ADD, content=line[1:])
                    )
                elif line.startswith("-"):
                    current_hunk.lines.append(
                        DiffLine(type=ChangeType.DELETE, content=line[1:])
                    )
                elif line.startswith(" ") or line == "":
                    current_hunk.lines.append(
                        DiffLine(type=ChangeType.CONTEXT, content=line[1:] if line else "")
                    )

        if current_hunk is not None:
            hunks.append(current_hunk)

        return DiffResult(
            hunks=hunks,
            old_path=old_path,
            new_path=new_path,
        )

    def reverse_diff(self, diff_result: DiffResult) -> DiffResult:
        """Reverse diff (swap old and new)."""
        reversed_hunks = []

        for hunk in diff_result.hunks:
            reversed_lines = []
            for line in hunk.lines:
                if line.type == ChangeType.ADD:
                    reversed_lines.append(
                        DiffLine(
                            type=ChangeType.DELETE,
                            content=line.content,
                            old_line=line.new_line,
                        )
                    )
                elif line.type == ChangeType.DELETE:
                    reversed_lines.append(
                        DiffLine(
                            type=ChangeType.ADD,
                            content=line.content,
                            new_line=line.old_line,
                        )
                    )
                else:
                    reversed_lines.append(line)

            reversed_hunks.append(
                DiffHunk(
                    old_start=hunk.new_start,
                    old_count=hunk.new_count,
                    new_start=hunk.old_start,
                    new_count=hunk.old_count,
                    lines=reversed_lines,
                )
            )

        return DiffResult(
            hunks=reversed_hunks,
            old_path=diff_result.new_path,
            new_path=diff_result.old_path,
        )

    def merge_diffs(
        self,
        diff1: DiffResult,
        diff2: DiffResult,
    ) -> DiffResult:
        """Merge two diffs."""
        # Simple concatenation of hunks
        merged_hunks = diff1.hunks + diff2.hunks

        return DiffResult(
            hunks=merged_hunks,
            old_path=diff1.old_path,
            new_path=diff2.new_path,
        )


def diff_contents(
    old: str,
    new: str,
    old_path: str = "",
    new_path: str = "",
) -> DiffResult:
    """Generate diff between contents."""
    engine = DiffEngine()
    return engine.diff(old, new, old_path, new_path)


def format_diff(diff_result: DiffResult) -> str:
    """Format diff as text."""
    engine = DiffEngine()
    return engine.format_diff(diff_result)


def apply_patch(content: str, diff_text: str) -> str:
    """Apply patch to content."""
    engine = DiffEngine()
    diff_result = engine.parse_diff(diff_text)
    return engine.apply_patch(content, diff_result)


__all__ = [
    "DiffType",
    "ChangeType",
    "DiffLine",
    "DiffHunk",
    "DiffResult",
    "DiffConfig",
    "DiffEngine",
    "diff_contents",
    "format_diff",
    "apply_patch",
]