"""Regex Tool - Regular expression operations."""

from __future__ import annotations
import re
from pathlib import Path
from typing import ClassVar, Dict, Optional, List, Any
from pydantic import BaseModel, Field

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class RegexInput(ToolInput):
    """Input for RegexTool."""
    action: str = Field(description="Action: match, search, findall, replace, validate")
    pattern: Optional[str] = Field(default=None, description="Regex pattern")
    text: Optional[str] = Field(default=None, description="Text to process")
    replacement: Optional[str] = Field(default=None, description="Replacement for replace action")
    flags: Optional[List[str]] = Field(default=None, description="Flags: i, m, s, g")


class RegexMatch(BaseModel):
    """Regex match result."""
    match: str
    start: int
    end: int
    groups: List[str] = []


class RegexTool(ToolDef):
    """Regular expression operations."""

    name: ClassVar[str] = "Regex"
    description: ClassVar[str] = "Regex matching and replacement"
    input_schema: ClassVar[type] = RegexInput

    async def execute(self, input: RegexInput, ctx: ToolUseContext) -> ToolResult:
        """Execute regex operation."""
        action = input.action

        # Get text
        text = input.text
        if text:
            path = Path(text)
            if not path.is_absolute():
                path = Path(ctx.cwd) / path
            if path.exists():
                text = path.read_text()

        if not text:
            return ToolResult(content="Text required", is_error=True)

        if not input.pattern:
            return ToolResult(content="Pattern required", is_error=True)

        # Build flags
        flags = 0
        if input.flags:
            if "i" in input.flags:
                flags |= re.IGNORECASE
            if "m" in input.flags:
                flags |= re.MULTILINE
            if "s" in input.flags:
                flags |= re.DOTALL

        try:
            pattern = re.compile(input.pattern, flags)
        except re.error as e:
            return ToolResult(content=f"Invalid pattern: {e}", is_error=True)

        if action == "match":
            return self._match(pattern, text)
        elif action == "search":
            return self._search(pattern, text)
        elif action == "findall":
            return self._findall(pattern, text)
        elif action == "replace":
            return self._replace(pattern, text, input.replacement, "g" in (input.flags or []))
        elif action == "validate":
            return self._validate(input.pattern)
        else:
            return ToolResult(content=f"Unknown action: {action}", is_error=True)

    def _match(self, pattern: re.Pattern, text: str) -> ToolResult:
        """Match at start."""
        m = pattern.match(text)
        if not m:
            return ToolResult(content="No match at start")

        match_result = RegexMatch(
            match=m.group(0),
            start=m.start(),
            end=m.end(),
            groups=list(m.groups()),
        )

        return ToolResult(
            content=f"Match: {match_result.match}\nGroups: {match_result.groups}",
            metadata=match_result.model_dump(),
        )

    def _search(self, pattern: re.Pattern, text: str) -> ToolResult:
        """Search for first match."""
        m = pattern.search(text)
        if not m:
            return ToolResult(content="No match found")

        match_result = RegexMatch(
            match=m.group(0),
            start=m.start(),
            end=m.end(),
            groups=list(m.groups()),
        )

        return ToolResult(
            content=f"Match at {match_result.start}: {match_result.match}\nGroups: {match_result.groups}",
            metadata=match_result.model_dump(),
        )

    def _findall(self, pattern: re.Pattern, text: str) -> ToolResult:
        """Find all matches."""
        matches = pattern.findall(text)

        if not matches:
            return ToolResult(content="No matches found")

        # Format results
        lines = []
        for i, m in enumerate(matches, 1):
            if isinstance(m, tuple):
                lines.append(f"{i}: {m}")
            else:
                lines.append(f"{i}: {m}")

        return ToolResult(
            content="\n".join(lines),
            metadata={"count": len(matches), "matches": matches},
        )

    def _replace(self, pattern: re.Pattern, text: str, replacement: Optional[str], global_replace: bool) -> ToolResult:
        """Replace matches."""
        if replacement is None:
            return ToolResult(content="Replacement required", is_error=True)

        count = 0 if global_replace else 1
        result = pattern.sub(replacement, text, count=count)

        # Count replacements
        replacements = len(pattern.findall(text))
        if not global_replace:
            replacements = min(1, replacements)

        return ToolResult(
            content=result,
            metadata={"replacements": replacements, "original_length": len(text), "result_length": len(result)},
        )

    def _validate(self, pattern_str: str) -> ToolResult:
        """Validate pattern."""
        try:
            re.compile(pattern_str)
            return ToolResult(
                content=f"Pattern is valid: {pattern_str}",
                metadata={"valid": True},
            )
        except re.error as e:
            return ToolResult(
                content=f"Invalid pattern: {e}",
                is_error=True,
                metadata={"valid": False, "error": str(e)},
            )


__all__ = ["RegexTool", "RegexInput", "RegexMatch"]