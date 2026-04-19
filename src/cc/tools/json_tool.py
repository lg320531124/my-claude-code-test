"""JSON Tool - JSON processing."""

from __future__ import annotations
import json
from pathlib import Path
from typing import ClassVar, Dict, Optional, Any
from pydantic import BaseModel, Field

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class JSONInput(ToolInput):
    """Input for JSONTool."""
    action: str = Field(description="Action: parse, format, validate, extract, merge, diff")
    data: Optional[str] = Field(default=None, description="JSON data or file path")
    key: Optional[str] = Field(default=None, description="Key to extract")
    indent: int = Field(default=2, description="Indentation for formatting")
    strict: bool = Field(default=False, description="Strict validation")


class JSONTool(ToolDef):
    """JSON processing."""

    name: ClassVar[str] = "JSON"
    description: ClassVar[str] = "Parse, format, and manipulate JSON"
    input_schema: ClassVar[type] = JSONInput

    async def execute(self, input: JSONInput, ctx: ToolUseContext) -> ToolResult:
        """Execute JSON operation."""
        action = input.action

        # Get data
        data = input.data
        if data:
            # Check if it's a file path
            path = Path(data)
            if not path.is_absolute():
                path = Path(ctx.cwd) / path
            if path.exists() and path.suffix.lower() == ".json":
                data = path.read_text()

        if not data:
            return ToolResult(content="JSON data required", is_error=True)

        if action == "parse":
            return self._parse_json(data, input.strict)
        elif action == "format":
            return self._format_json(data, input.indent)
        elif action == "validate":
            return self._validate_json(data, input.strict)
        elif action == "extract":
            return self._extract_key(data, input.key)
        elif action == "merge":
            return ToolResult(content="Merge requires two JSON inputs", is_error=True)
        elif action == "diff":
            return ToolResult(content="Diff requires two JSON inputs", is_error=True)
        else:
            return ToolResult(content=f"Unknown action: {action}", is_error=True)

    def _parse_json(self, data: str, strict: bool) -> ToolResult:
        """Parse JSON."""
        try:
            parsed = json.loads(data)
            return ToolResult(
                content=f"Parsed JSON: {type(parsed).__name__}",
                metadata={"type": type(parsed).__name__, "parsed": parsed},
            )
        except json.JSONDecodeError as e:
            return ToolResult(
                content=f"JSON parse error: {e.msg} at line {e.lineno}",
                is_error=True,
            )

    def _format_json(self, data: str, indent: int) -> ToolResult:
        """Format JSON."""
        try:
            parsed = json.loads(data)
            formatted = json.dumps(parsed, indent=indent, ensure_ascii=False)
            return ToolResult(content=formatted)
        except json.JSONDecodeError as e:
            return ToolResult(
                content=f"JSON parse error: {e.msg}",
                is_error=True,
            )

    def _validate_json(self, data: str, strict: bool) -> ToolResult:
        """Validate JSON."""
        try:
            parsed = json.loads(data)

            issues = []

            if strict:
                # Check for common issues
                if isinstance(parsed, dict):
                    # Check for null keys
                    for key in parsed:
                        if parsed[key] is None:
                            issues.append(f"Null value for key: {key}")

                    # Check for empty strings
                    for key, value in parsed.items():
                        if isinstance(value, str) and not value:
                            issues.append(f"Empty string for key: {key}")

            if issues:
                return ToolResult(
                    content="Validation issues:\n" + "\n".join(issues),
                    metadata={"valid": False, "issues": issues},
                )

            return ToolResult(
                content="JSON is valid",
                metadata={"valid": True, "type": type(parsed).__name__},
            )
        except json.JSONDecodeError as e:
            return ToolResult(
                content=f"JSON validation failed: {e.msg}",
                is_error=True,
                metadata={"valid": False, "error": str(e)},
            )

    def _extract_key(self, data: str, key: Optional[str]) -> ToolResult:
        """Extract key from JSON."""
        if not key:
            return ToolResult(content="Key required", is_error=True)

        try:
            parsed = json.loads(data)

            # Navigate nested keys
            keys = key.split(".")
            value = parsed
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                elif isinstance(value, list) and k.isdigit():
                    idx = int(k)
                    if idx < len(value):
                        value = value[idx]
                    else:
                        return ToolResult(
                            content=f"Index {idx} out of range",
                            is_error=True,
                        )
                else:
                    return ToolResult(
                        content=f"Key not found: {key}",
                        is_error=True,
                    )

            if isinstance(value, (dict, list)):
                return ToolResult(content=json.dumps(value, indent=2))
            else:
                return ToolResult(content=str(value), metadata={"key": key, "value": value})

        except json.JSONDecodeError as e:
            return ToolResult(content=f"JSON parse error: {e.msg}", is_error=True)

    @classmethod
    def merge_json(cls, data1: str, data2: str) -> ToolResult:
        """Merge two JSON objects."""
        try:
            obj1 = json.loads(data1)
            obj2 = json.loads(data2)

            if not isinstance(obj1, dict) or not isinstance(obj2, dict):
                return ToolResult(
                    content="Both inputs must be JSON objects",
                    is_error=True,
                )

            # Deep merge
            def deep_merge(a: dict, b: dict) -> dict:
                result = a.copy()
                for key, value in b.items():
                    if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                        result[key] = deep_merge(result[key], value)
                    else:
                        result[key] = value
                return result

            merged = deep_merge(obj1, obj2)
            return ToolResult(
                content=json.dumps(merged, indent=2),
                metadata={"merged": merged},
            )
        except json.JSONDecodeError as e:
            return ToolResult(content=f"JSON parse error: {e.msg}", is_error=True)


__all__ = ["JSONTool", "JSONInput"]