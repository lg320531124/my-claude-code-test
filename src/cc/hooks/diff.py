"""Diff Hook - Async diff operations."""

from __future__ import annotations
import asyncio
import difflib
from typing import Any, Dict, List, Optional, Tuple, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class DiffType(Enum):
    """Diff types."""
    UNIFIED = "unified"
    CONTEXT = "context"
    SIDE_BY_SIDE = "side_by_side"
    HTML = "html"


class DiffOperation(Enum):
    """Diff operations."""
    EQUAL = "equal"
    INSERT = "insert"
    DELETE = "delete"
    REPLACE = "replace"


@dataclass
class DiffLine:
    """Single diff line."""
    operation: DiffOperation
    old_line: Optional[str] = None
    new_line: Optional[str] = None
    old_number: Optional[int] = None
    new_number: Optional[int] = None


@dataclass
class DiffResult:
    """Diff result."""
    old_path: str
    new_path: str
    lines: List[DiffLine] = field(default_factory=list)
    additions: int = 0
    deletions: int = 0
    changes: int = 0

    @property
    def summary(self) -> str:
        """Get diff summary."""
        return f"{self.additions} additions, {self.deletions} deletions"


class DiffHook:
    """Async diff operations hook."""

    def __init__(self):
        self._diff_cache: Dict[str, DiffResult] = {}

    async def diff_files(
        self,
        old_path: str,
        new_path: str,
        diff_type: DiffType = DiffType.UNIFIED,
    ) -> DiffResult:
        """Diff two files.

        Args:
            old_path: Path to old file
            new_path: Path to new file
            diff_type: Diff output type

        Returns:
            DiffResult
        """
        # Read files
        try:
            async with asyncio.Lock():
                old_content = await self._read_file(old_path)
                new_content = await self._read_file(new_path)
        except Exception as e:
            return DiffResult(
                old_path=old_path,
                new_path=new_path,
            )

        # Compute diff
        return await self.diff_strings(
            old_content,
            new_content,
            old_path,
            new_path,
            diff_type,
        )

    async def diff_strings(
        self,
        old_content: str,
        new_content: str,
        old_name: str = "old",
        new_name: str = "new",
        diff_type: DiffType = DiffType.UNIFIED,
    ) -> DiffResult:
        """Diff two strings.

        Args:
            old_content: Old content
            new_content: New content
            old_name: Old content name
            new_name: New content name
            diff_type: Diff output type

        Returns:
            DiffResult
        """
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        # Use difflib
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

        result = DiffResult(
            old_path=old_name,
            new_path=new_name,
        )

        old_line_num = 0
        new_line_num = 0

        for op, i1, i2, j1, j2 in matcher.get_opcodes():
            if op == "equal":
                for i in range(i1, i2):
                    result.lines.append(DiffLine(
                        operation=DiffOperation.EQUAL,
                        old_line=old_lines[i],
                        new_line=new_lines[j1 + (i - i1)],
                        old_number=old_line_num + 1,
                        new_number=new_line_num + 1,
                    ))
                    old_line_num += 1
                    new_line_num += 1

            elif op == "delete":
                for i in range(i1, i2):
                    result.lines.append(DiffLine(
                        operation=DiffOperation.DELETE,
                        old_line=old_lines[i],
                        old_number=old_line_num + 1,
                    ))
                    old_line_num += 1
                result.deletions += i2 - i1

            elif op == "insert":
                for j in range(j1, j2):
                    result.lines.append(DiffLine(
                        operation=DiffOperation.INSERT,
                        new_line=new_lines[j],
                        new_number=new_line_num + 1,
                    ))
                    new_line_num += 1
                result.additions += j2 - j1

            elif op == "replace":
                for i in range(i1, i2):
                    result.lines.append(DiffLine(
                        operation=DiffOperation.DELETE,
                        old_line=old_lines[i],
                        old_number=old_line_num + 1,
                    ))
                    old_line_num += 1

                for j in range(j1, j2):
                    result.lines.append(DiffLine(
                        operation=DiffOperation.INSERT,
                        new_line=new_lines[j],
                        new_number=new_line_num + 1,
                    ))
                    new_line_num += 1

                result.deletions += i2 - i1
                result.additions += j2 - j1

        result.changes = result.additions + result.deletions
        return result

    async def diff_git(
        self,
        repo_path: str,
        commit1: str = "HEAD",
        commit2: str = None,
        file_path: str = None,
    ) -> List[DiffResult]:
        """Diff git commits.

        Args:
            repo_path: Path to git repo
            commit1: First commit
            commit2: Second commit (None for staged diff)
            file_path: Optional file path filter

        Returns:
            List of DiffResult
        """
        import asyncio

        # Build git command
        if commit2:
            cmd = ["git", "-C", repo_path, "diff", commit1, commit2]
        else:
            cmd = ["git", "-C", repo_path, "diff", commit1]

        if file_path:
            cmd.append("--")
            cmd.append(file_path)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                return []

            # Parse git diff output
            return await self._parse_git_diff(stdout.decode())

        except Exception:
            return []

    async def _parse_git_diff(self, diff_output: str) -> List[DiffResult]:
        """Parse git diff output.

        Args:
            diff_output: Git diff output

        Returns:
            List of DiffResult
        """
        results = []
        current_result = None

        for line in diff_output.splitlines():
            if line.startswith("diff --git"):
                # New file diff
                parts = line.split()
                if len(parts) >= 4:
                    old_path = parts[2].lstrip("a/")
                    new_path = parts[3].lstrip("b/")
                    if current_result:
                        results.append(current_result)
                    current_result = DiffResult(
                        old_path=old_path,
                        new_path=new_path,
                    )

            elif current_result:
                if line.startswith("+++"):
                    pass
                elif line.startswith("---"):
                    pass
                elif line.startswith("+"):
                    current_result.lines.append(DiffLine(
                        operation=DiffOperation.INSERT,
                        new_line=line[1:] + "\n",
                    ))
                    current_result.additions += 1
                elif line.startswith("-"):
                    current_result.lines.append(DiffLine(
                        operation=DiffOperation.DELETE,
                        old_line=line[1:] + "\n",
                    ))
                    current_result.deletions += 1
                elif line.startswith(" "):
                    current_result.lines.append(DiffLine(
                        operation=DiffOperation.EQUAL,
                        old_line=line[1:] + "\n",
                        new_line=line[1:] + "\n",
                    ))

        if current_result:
            current_result.changes = current_result.additions + current_result.deletions
            results.append(current_result)

        return results

    async def _read_file(self, path: str) -> str:
        """Read file async.

        Args:
            path: File path

        Returns:
            File content
        """
        from ..utils.async_io import read_file_async
        return await read_file_async(path)

    def format_unified(self, result: DiffResult) -> str:
        """Format diff as unified diff.

        Args:
            result: DiffResult

        Returns:
            Unified diff string
        """
        output = []
        output.append(f"--- {result.old_path}")
        output.append(f"+++ {result.new_path}")

        for line in result.lines:
            if line.operation == DiffOperation.EQUAL:
                output.append(f" {line.old_line or ''}")
            elif line.operation == DiffOperation.DELETE:
                output.append(f"-{line.old_line or ''}")
            elif line.operation == DiffOperation.INSERT:
                output.append(f"+{line.new_line or ''}")

        return "\n".join(output)

    def format_side_by_side(
        self,
        result: DiffResult,
        width: int = 80,
    ) -> str:
        """Format diff side-by-side.

        Args:
            result: DiffResult
            width: Column width

        Returns:
            Side-by-side diff string
        """
        output = []
        half_width = width // 2

        output.append(f"{result.old_path:^{half_width}} | {result.new_path:^{half_width}}")
        output.append("-" * width)

        for line in result.lines:
            if line.operation == DiffOperation.EQUAL:
                old = (line.old_line or "").strip()[:half_width - 1]
                new = (line.new_line or "").strip()[:half_width - 1]
                output.append(f"{old:<{half_width}} | {new:<{half_width}}")
            elif line.operation == DiffOperation.DELETE:
                old = (line.old_line or "").strip()[:half_width - 1]
                output.append(f"[red]{old:<{half_width}}[/] | {'':<{half_width}}")
            elif line.operation == DiffOperation.INSERT:
                new = (line.new_line or "").strip()[:half_width - 1]
                output.append(f"{'':<{half_width}} | [green]{new:<{half_width}}[/]")

        return "\n".join(output)


# Global diff hook
_diff_hook: Optional[DiffHook] = None


def get_diff_hook() -> DiffHook:
    """Get global diff hook."""
    global _diff_hook
    if _diff_hook is None:
        _diff_hook = DiffHook()
    return _diff_hook


async def use_diff() -> Dict[str, Any]:
    """Diff hook for hooks module.

    Returns diff functions.
    """
    hook = get_diff_hook()

    return {
        "diff_files": hook.diff_files,
        "diff_strings": hook.diff_strings,
        "diff_git": hook.diff_git,
        "format_unified": hook.format_unified,
        "format_side_by_side": hook.format_side_by_side,
    }


__all__ = [
    "DiffType",
    "DiffOperation",
    "DiffLine",
    "DiffResult",
    "DiffHook",
    "get_diff_hook",
    "use_diff",
]