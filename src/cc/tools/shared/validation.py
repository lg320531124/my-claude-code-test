"""Tool Validation - Input validation for tools."""

from __future__ import annotations
import asyncio
import re
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum


class ValidationSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationError:
    field: str
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    value: Any = None


@dataclass  
class ValidationResult:
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    sanitized_args: Dict[str, Any] = field(default_factory=dict)


class ToolValidator:
    def __init__(self):
        self._validators: Dict[str, Dict[str, Callable]] = {}
        self._global_validators: List[Callable] = []

    def register_validator(self, tool_name: str, field_name: str, validator: Callable) -> None:
        if tool_name not in self._validators:
            self._validators[tool_name] = {}
        self._validators[tool_name][field_name] = validator

    async def validate(self, tool_name: str, args: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult(valid=True, sanitized_args=args.copy())
        
        field_validators = self._validators.get(tool_name, {})
        for field_name, validator in field_validators.items():
            value = args.get(field_name)
            try:
                if asyncio.iscoroutinefunction(validator):
                    valid, error_msg, sanitized = await validator(value)
                else:
                    valid, error_msg, sanitized = validator(value)
                if not valid:
                    result.errors.append(ValidationError(field=field_name, message=error_msg, value=value))
                    result.valid = False
                elif sanitized is not None:
                    result.sanitized_args[field_name] = sanitized
            except Exception as e:
                result.errors.append(ValidationError(field=field_name, message=str(e), value=value))
                result.valid = False
        return result

    def validate_path(self, value: Any) -> tuple:
        if value is None:
            return False, "Path is required", None
        if not isinstance(value, str):
            return False, "Path must be string", None
        dangerous = [r"\.\./", r"/etc/", r"\.ssh/", r"\.gnupg/"]
        for pattern in dangerous:
            if re.search(pattern, value):
                return False, f"Dangerous pattern: {pattern}", None
        import os
        return True, "", os.path.normpath(value)

    def validate_command(self, value: Any) -> tuple:
        if value is None:
            return False, "Command required", None
        if not isinstance(value, str):
            return False, "Command must be string", None
        dangerous = ["rm -rf", "dd if=", "mkfs", "format", "> /dev/", "chmod 777"]
        for cmd in dangerous:
            if cmd in value:
                return False, f"Dangerous: {cmd}", None
        return True, "", value

    def validate_url(self, value: Any) -> tuple:
        if value is None:
            return False, "URL required", None
        if not isinstance(value, str):
            return False, "URL must be string", None
        if not re.match(r"^https?://[^\s]+$", value):
            return False, "Invalid URL", None
        dangerous = ["localhost", "127.0.0.1", "0.0.0.0", "internal"]
        for domain in dangerous:
            if domain in value.lower():
                return False, f"Dangerous domain: {domain}", None
        return True, "", value


_validator: Optional[ToolValidator] = None

def get_validator() -> ToolValidator:
    global _validator
    if _validator is None:
        _validator = ToolValidator()
        _validator.register_validator("Read", "file_path", _validator.validate_path)
        _validator.register_validator("Write", "file_path", _validator.validate_path)
        _validator.register_validator("Bash", "command", _validator.validate_command)
        _validator.register_validator("WebFetch", "url", _validator.validate_url)
    return _validator

async def validate_tool_args(tool_name: str, args: Dict) -> ValidationResult:
    return await get_validator().validate(tool_name, args)

__all__ = ["ValidationSeverity", "ValidationError", "ValidationResult", "ToolValidator", "get_validator", "validate_tool_args"]
