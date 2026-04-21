"""Tests for JSON Utils."""

import pytest
import tempfile
from pathlib import Path

from cc.utils.json_utils import (
    JSONConfig,
    JSONError,
    JSONParser,
    JSONFormatter,
    JSONValidator,
    JSONPath,
    parse_json,
    format_json,
    validate_json,
    read_json_file,
    write_json_file,
    merge_json,
    diff_json,
    json_path_get,
    json_path_set,
)


class TestJSONConfig:
    """Test JSONConfig."""

    def test_defaults(self):
        """Test default configuration."""
        config = JSONConfig()
        assert config.indent == 2
        assert config.ensure_ascii is False
        assert config.allow_comments is True

    def test_custom(self):
        """Test custom configuration."""
        config = JSONConfig(indent=4, allow_comments=False)
        assert config.indent == 4
        assert config.allow_comments is False


class TestJSONParser:
    """Test JSONParser."""

    def test_init(self):
        """Test initialization."""
        parser = JSONParser()
        assert parser.config is not None

    def test_parse_simple(self):
        """Test parsing simple JSON."""
        parser = JSONParser()
        result = parser.parse('{"key": "value"}')
        assert result["key"] == "value"

    def test_parse_array(self):
        """Test parsing array."""
        parser = JSONParser()
        result = parser.parse('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_parse_with_comments(self):
        """Test parsing JSON with comments."""
        config = JSONConfig(allow_comments=True)
        parser = JSONParser(config)
        result = parser.parse('{"key": "value" // comment\n}')
        assert result["key"] == "value"

    def test_parse_with_trailing_comma(self):
        """Test parsing with trailing comma."""
        config = JSONConfig(allow_trailing_commas=True)
        parser = JSONParser(config)
        result = parser.parse('{"key": "value",}')
        assert result["key"] == "value"

    def test_parse_invalid(self):
        """Test parsing invalid JSON."""
        parser = JSONParser()
        with pytest.raises(JSONError):
            parser.parse('{"invalid"}')


class TestJSONFormatter:
    """Test JSONFormatter."""

    def test_init(self):
        """Test initialization."""
        formatter = JSONFormatter()
        assert formatter.config is not None

    def test_format(self):
        """Test formatting."""
        formatter = JSONFormatter()
        result = formatter.format({"key": "value"})
        assert "key" in result
        assert "value" in result

    def test_format_compact(self):
        """Test compact formatting."""
        formatter = JSONFormatter()
        result = formatter.format_compact({"key": "value"})
        assert result == '{"key":"value"}'

    def test_format_pretty(self):
        """Test pretty formatting."""
        formatter = JSONFormatter()
        result = formatter.format_pretty({"key": "value"})
        assert "  " in result  # Has indentation


class TestJSONValidator:
    """Test JSONValidator."""

    def test_init(self):
        """Test initialization."""
        validator = JSONValidator()
        assert validator.config is not None

    def test_validate_valid(self):
        """Test validating valid JSON."""
        validator = JSONValidator()
        assert validator.validate('{"key": "value"}') is True

    def test_validate_invalid(self):
        """Test validating invalid JSON."""
        validator = JSONValidator()
        assert validator.validate('{"invalid"}') is False

    def test_validate_structure_object(self):
        """Test structure validation for object."""
        validator = JSONValidator()
        schema = {"type": "object"}
        assert validator.validate_structure({}, schema) is True
        assert validator.validate_structure([], schema) is False

    def test_validate_structure_array(self):
        """Test structure validation for array."""
        validator = JSONValidator()
        schema = {"type": "array"}
        assert validator.validate_structure([], schema) is True
        assert validator.validate_structure({}, schema) is False

    def test_validate_structure_string(self):
        """Test structure validation for string."""
        validator = JSONValidator()
        schema = {"type": "string"}
        assert validator.validate_structure("hello", schema) is True
        assert validator.validate_structure(123, schema) is False

    def test_validate_structure_required(self):
        """Test structure validation for required fields."""
        validator = JSONValidator()
        schema = {"required": ["name"]}
        assert validator.validate_structure({"name": "test"}, schema) is True
        assert validator.validate_structure({}, schema) is False


class TestJSONPath:
    """Test JSONPath."""

    def test_get_simple(self):
        """Test simple get."""
        jp = JSONPath()
        data = {"key": "value"}
        assert jp.get(data, "key") == "value"

    def test_get_nested(self):
        """Test nested get."""
        jp = JSONPath()
        data = {"outer": {"inner": "value"}}
        assert jp.get(data, "outer.inner") == "value"

    def test_get_array(self):
        """Test array get."""
        jp = JSONPath()
        data = {"items": ["a", "b", "c"]}
        assert jp.get(data, "items[0]") == "a"
        assert jp.get(data, "items[1]") == "b"

    def test_get_missing(self):
        """Test missing key."""
        jp = JSONPath()
        data = {"key": "value"}
        assert jp.get(data, "missing") is None

    def test_set_simple(self):
        """Test simple set."""
        jp = JSONPath()
        data = {}
        jp.set(data, "key", "value")
        assert data["key"] == "value"

    def test_set_nested(self):
        """Test nested set."""
        jp = JSONPath()
        data = {}
        jp.set(data, "outer.inner", "value")
        assert data["outer"]["inner"] == "value"


class TestHelperFunctions:
    """Test helper functions."""

    def test_parse_json(self):
        """Test parse_json function."""
        result = parse_json('{"key": "value"}')
        assert result["key"] == "value"

    def test_format_json(self):
        """Test format_json function."""
        result = format_json({"key": "value"})
        assert "key" in result

    def test_validate_json(self):
        """Test validate_json function."""
        assert validate_json('{"key": "value"}') is True
        assert validate_json('{"invalid"}') is False

    def test_read_write_json_file(self):
        """Test reading and writing JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.json"
            write_json_file(path, {"key": "value"})
            result = read_json_file(path)
            assert result["key"] == "value"

    def test_merge_json(self):
        """Test merge_json function."""
        base = {"a": 1, "b": {"x": 1}}
        update = {"b": {"y": 2}, "c": 3}
        result = merge_json(base, update)
        assert result["a"] == 1
        assert result["b"]["x"] == 1
        assert result["b"]["y"] == 2
        assert result["c"] == 3

    def test_diff_json_equal(self):
        """Test diff_json for equal values."""
        result = diff_json({"a": 1}, {"a": 1})
        assert result["equal"] is True

    def test_diff_json_not_equal(self):
        """Test diff_json for different values."""
        result = diff_json({"a": 1}, {"a": 2})
        assert result["equal"] is False

    def test_diff_json_type_diff(self):
        """Test diff_json for type difference."""
        result = diff_json({"a": 1}, [1, 2])
        assert result["equal"] is False
        assert result["type_diff"] is True

    def test_json_path_get(self):
        """Test json_path_get function."""
        data = {"outer": {"inner": "value"}}
        result = json_path_get(data, "outer.inner")
        assert result == "value"

    def test_json_path_set(self):
        """Test json_path_set function."""
        data = {}
        json_path_set(data, "key", "value")
        assert data["key"] == "value"