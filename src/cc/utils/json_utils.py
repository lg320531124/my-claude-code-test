"""JSON Utils - JSON handling utilities."""

from __future__ import annotations
import json
import re
from typing import Dict, Any, Optional, List, Union, TypeVar
from dataclasses import dataclass, field
from pathlib import Path
from io import StringIO

T = TypeVar('T')


@dataclass
class JSONConfig:
    """JSON configuration."""
    indent: Optional[int] = 2
    ensure_ascii: bool = False
    sort_keys: bool = False
    allow_comments: bool = True
    allow_trailing_commas: bool = True
    allow_single_quotes: bool = True
    max_depth: int = 100


class JSONError(Exception):
    """JSON parsing error."""
    pass


class JSONParser:
    """Extended JSON parser with comment support."""

    def __init__(self, config: Optional[JSONConfig] = None):
        self.config = config or JSONConfig()

    def parse(self, text: str) -> Any:
        """Parse JSON text with extensions."""
        if self.config.allow_comments:
            text = self._remove_comments(text)

        if self.config.allow_trailing_commas:
            text = self._remove_trailing_commas(text)

        if self.config.allow_single_quotes:
            text = self._convert_single_quotes(text)

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise JSONError(f"JSON parse error: {e}")

    def _remove_comments(self, text: str) -> str:
        """Remove // and /* */ comments."""
        # Remove single-line comments
        text = re.sub(r'//.*$', '', text, flags=re.MULTILINE)
        # Remove multi-line comments
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
        return text

    def _remove_trailing_commas(self, text: str) -> str:
        """Remove trailing commas."""
        # In arrays
        text = re.sub(r',\s*\]', ']', text)
        # In objects
        text = re.sub(r',\s*\}', '}', text)
        return text

    def _convert_single_quotes(self, text: str) -> str:
        """Convert single quotes to double quotes."""
        # Simple conversion (not fully accurate for all cases)
        # This is a simplified approach
        result = []
        i = 0
        while i < len(text):
            if text[i] == "'" and (i == 0 or text[i-1] not in '"\''):
                # Find closing quote
                j = i + 1
                while j < len(text):
                    if text[j] == "'":
                        if j + 1 < len(text) and text[j+1] == "'":
                            j += 2  # Skip escaped quote
                        else:
                            break
                    j += 1
                # Convert to double quotes
                result.append('"')
                result.append(text[i+1:j].replace("'", "\\'").replace('"', '\\"'))
                result.append('"')
                i = j + 1
            else:
                result.append(text[i])
                i += 1
        return ''.join(result)


class JSONFormatter:
    """JSON formatter."""

    def __init__(self, config: Optional[JSONConfig] = None):
        self.config = config or JSONConfig()

    def format(self, data: Any) -> str:
        """Format data as JSON."""
        return json.dumps(
            data,
            indent=self.config.indent,
            ensure_ascii=self.config.ensure_ascii,
            sort_keys=self.config.sort_keys,
        )

    def format_compact(self, data: Any) -> str:
        """Format data as compact JSON."""
        return json.dumps(data, separators=(',', ':'))

    def format_pretty(self, data: Any) -> str:
        """Format data as pretty JSON."""
        return json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        )


class JSONValidator:
    """JSON validator."""

    def __init__(self, config: Optional[JSONConfig] = None):
        self.config = config or JSONConfig()

    def validate(self, text: str) -> bool:
        """Validate JSON text."""
        try:
            json.loads(text)
            return True
        except json.JSONDecodeError:
            return False

    def validate_structure(
        self,
        data: Any,
        schema: Dict[str, Any],
    ) -> bool:
        """Validate data against simple schema."""
        # Simple schema validation
        if schema.get("type"):
            expected_type = schema["type"]
            if expected_type == "object":
                if not isinstance(data, dict):
                    return False
            elif expected_type == "array":
                if not isinstance(data, list):
                    return False
            elif expected_type == "string":
                if not isinstance(data, str):
                    return False
            elif expected_type == "number":
                if not isinstance(data, (int, float)):
                    return False
            elif expected_type == "boolean":
                if not isinstance(data, bool):
                    return False
            elif expected_type == "null":
                if data is not None:
                    return False

        # Check required fields
        if schema.get("required") and isinstance(data, dict):
            for field in schema["required"]:
                if field not in data:
                    return False

        # Check properties
        if schema.get("properties") and isinstance(data, dict):
            for key, prop_schema in schema["properties"].items():
                if key in data:
                    if not self.validate_structure(data[key], prop_schema):
                        return False

        return True


class JSONPath:
    """JSONPath-like access."""

    def __init__(self):
        pass

    def get(self, data: Any, path: str) -> Any:
        """Get value at path."""
        parts = self._parse_path(path)
        current = data

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    idx = int(part)
                    current = current[idx]
                except (ValueError, IndexError):
                    return None
            else:
                return None

        return current

    def set(self, data: Any, path: str, value: Any) -> Any:
        """Set value at path."""
        parts = self._parse_path(path)
        if not parts:
            return value

        current = data
        for i, part in enumerate(parts[:-1]):
            if isinstance(current, dict):
                if part not in current:
                    current[part] = {}
                current = current[part]
            elif isinstance(current, list):
                try:
                    idx = int(part)
                    current = current[idx]
                except (ValueError, IndexError):
                    return data

        # Set final value
        last = parts[-1]
        if isinstance(current, dict):
            current[last] = value
        elif isinstance(current, list):
            try:
                idx = int(last)
                current[idx] = value
            except (ValueError, IndexError):
                pass

        return data

    def _parse_path(self, path: str) -> List[str]:
        """Parse JSON path."""
        # Simple path parsing: "a.b.c" or "a[0].b"
        parts = []
        current = ""
        in_bracket = False

        for char in path:
            if char == '.' and not in_bracket:
                if current:
                    parts.append(current)
                    current = ""
            elif char == '[':
                if current:
                    parts.append(current)
                    current = ""
                in_bracket = True
            elif char == ']':
                in_bracket = False
            else:
                current += char

        if current:
            parts.append(current)

        return parts


def parse_json(text: str, allow_comments: bool = True) -> Any:
    """Parse JSON text."""
    config = JSONConfig(allow_comments=allow_comments)
    parser = JSONParser(config)
    return parser.parse(text)


def format_json(data: Any, indent: int = 2) -> str:
    """Format data as JSON."""
    return json.dumps(data, indent=indent, ensure_ascii=False)


def validate_json(text: str) -> bool:
    """Validate JSON text."""
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False


def read_json_file(path: Union[str, Path]) -> Any:
    """Read JSON file."""
    with open(path, 'r') as f:
        return json.load(f)


def write_json_file(path: Union[str, Path], data: Any, indent: int = 2) -> None:
    """Write JSON file."""
    with open(path, 'w') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def merge_json(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two JSON objects."""
    result = base.copy()

    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_json(result[key], value)
        else:
            result[key] = value

    return result


def diff_json(a: Any, b: Any) -> Dict[str, Any]:
    """Diff two JSON values."""
    if a == b:
        return {"equal": True}

    if type(a) != type(b):
        return {"equal": False, "type_diff": True}

    if isinstance(a, dict):
        added = {k: b[k] for k in b if k not in a}
        removed = {k: a[k] for k in a if k not in b}
        changed = {}
        for k in a:
            if k in b and a[k] != b[k]:
                changed[k] = {"old": a[k], "new": b[k]}
        return {
            "equal": False,
            "added": added,
            "removed": removed,
            "changed": changed,
        }

    if isinstance(a, list):
        return {
            "equal": False,
            "old_len": len(a),
            "new_len": len(b),
        }

    return {"equal": False, "old": a, "new": b}


def json_path_get(data: Any, path: str) -> Any:
    """Get value at JSON path."""
    jp = JSONPath()
    return jp.get(data, path)


def json_path_set(data: Any, path: str, value: Any) -> Any:
    """Set value at JSON path."""
    jp = JSONPath()
    return jp.set(data, path, value)


__all__ = [
    "JSONConfig",
    "JSONError",
    "JSONParser",
    "JSONFormatter",
    "JSONValidator",
    "JSONPath",
    "parse_json",
    "format_json",
    "validate_json",
    "read_json_file",
    "write_json_file",
    "merge_json",
    "diff_json",
    "json_path_get",
    "json_path_set",
]