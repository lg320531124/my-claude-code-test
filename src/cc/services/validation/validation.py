"""Validation Service - Input validation utilities."""

from __future__ import annotations
import re
from pathlib import Path
from typing import Any, Dict, Optional, List, Callable
from pydantic import BaseModel, Field


class ValidationRule(BaseModel):
    """Validation rule."""
    name: str
    pattern: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    required: bool = False
    custom_validator: Optional[str] = None


class ValidationResult(BaseModel):
    """Validation result."""
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ValidationService:
    """Input validation service."""

    def __init__(self):
        self._validators: Dict[str, Callable] = {}
        self._rules: Dict[str, ValidationRule] = {}
        self._load_default_validators()

    def _load_default_validators(self) -> None:
        """Load default validators."""
        # Email
        self._validators["email"] = self._validate_email

        # URL
        self._validators["url"] = self._validate_url

        # Phone
        self._validators["phone"] = self._validate_phone

        # Path
        self._validators["path"] = self._validate_path

        # Integer
        self._validators["integer"] = self._validate_integer

        # Float
        self._validators["float"] = self._validate_float

        # Date
        self._validators["date"] = self._validate_date

        # JSON
        self._validators["json"] = self._validate_json

    def validate(self, value: Any, validator_name: str) -> ValidationResult:
        """Validate value with named validator."""
        validator = self._validators.get(validator_name)
        if not validator:
            return ValidationResult(
                valid=False,
                errors=[f"Unknown validator: {validator_name}"],
            )

        return validator(value)

    def validate_with_rule(self, value: Any, rule: ValidationRule) -> ValidationResult:
        """Validate with a rule."""
        errors = []
        warnings = []

        # Required check
        if rule.required and value is None:
            errors.append(f"{rule.name} is required")
            return ValidationResult(valid=False, errors=errors)

        # Length checks
        if isinstance(value, str):
            if rule.min_length and len(value) < rule.min_length:
                errors.append(f"{rule.name} too short: {len(value)} < {rule.min_length}")
            if rule.max_length and len(value) > rule.max_length:
                errors.append(f"{rule.name} too long: {len(value)} > {rule.max_length}")

        # Value checks
        if isinstance(value, (int, float)):
            if rule.min_value and value < rule.min_value:
                errors.append(f"{rule.name} too small: {value} < {rule.min_value}")
            if rule.max_value and value > rule.max_value:
                errors.append(f"{rule.name} too large: {value} > {rule.max_value}")

        # Pattern check
        if rule.pattern and isinstance(value, str):
            if not re.match(rule.pattern, value):
                errors.append(f"{rule.name} does not match pattern: {rule.pattern}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def register_validator(self, name: str, validator: Callable) -> None:
        """Register custom validator."""
        self._validators[name] = validator

    def _validate_email(self, value: Any) -> ValidationResult:
        """Validate email."""
        if not isinstance(value, str):
            return ValidationResult(valid=False, errors=["Email must be string"])

        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, value):
            return ValidationResult(valid=False, errors=["Invalid email format"])

        return ValidationResult(valid=True)

    def _validate_url(self, value: Any) -> ValidationResult:
        """Validate URL."""
        if not isinstance(value, str):
            return ValidationResult(valid=False, errors=["URL must be string"])

        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        if not re.match(pattern, value):
            return ValidationResult(valid=False, errors=["Invalid URL format"])

        return ValidationResult(valid=True)

    def _validate_phone(self, value: Any) -> ValidationResult:
        """Validate phone number."""
        if not isinstance(value, str):
            return ValidationResult(valid=False, errors=["Phone must be string"])

        # Simple phone validation
        digits = re.sub(r'[^\d]', '', value)
        if len(digits) < 10 or len(digits) > 15:
            return ValidationResult(valid=False, errors=["Invalid phone number length"])

        return ValidationResult(valid=True)

    def _validate_path(self, value: Any) -> ValidationResult:
        """Validate file path."""
        if not isinstance(value, str):
            return ValidationResult(valid=False, errors=["Path must be string"])

        try:
            Path(value)
            # Check if path has valid characters
            if not value:
                return ValidationResult(valid=False, errors=["Path cannot be empty"])
            return ValidationResult(valid=True)
        except Exception as e:
            return ValidationResult(valid=False, errors=[f"Invalid path: {e}"])

    def _validate_integer(self, value: Any) -> ValidationResult:
        """Validate integer."""
        try:
            int(value)
            return ValidationResult(valid=True)
        except (ValueError, TypeError):
            return ValidationResult(valid=False, errors=["Not a valid integer"])

    def _validate_float(self, value: Any) -> ValidationResult:
        """Validate float."""
        try:
            float(value)
            return ValidationResult(valid=True)
        except (ValueError, TypeError):
            return ValidationResult(valid=False, errors=["Not a valid float"])

    def _validate_date(self, value: Any) -> ValidationResult:
        """Validate date."""
        from datetime import datetime

        if isinstance(value, datetime):
            return ValidationResult(valid=True)

        if isinstance(value, str):
            patterns = [
                r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
                r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$',  # ISO
                r'^\d{2}/\d{2}/\d{4}$',  # MM/DD/YYYY
            ]

            for pattern in patterns:
                if re.match(pattern, value):
                    return ValidationResult(valid=True)

            return ValidationResult(valid=False, errors=["Invalid date format"])

        return ValidationResult(valid=False, errors=["Date must be string or datetime"])

    def _validate_json(self, value: Any) -> ValidationResult:
        """Validate JSON."""
        import json

        if isinstance(value, str):
            try:
                json.loads(value)
                return ValidationResult(valid=True)
            except json.JSONDecodeError as e:
                return ValidationResult(valid=False, errors=[f"Invalid JSON: {e}"])

        # If it's already parsed, it's valid
        if isinstance(value, (dict, list)):
            return ValidationResult(valid=True)

        return ValidationResult(valid=False, errors=["Not JSON format"])


# Singleton
_validation_service: Optional[ValidationService] = None


def get_validation_service() -> ValidationService:
    """Get validation service singleton."""
    global _validation_service
    if _validation_service is None:
        _validation_service = ValidationService()
    return _validation_service


def validate(value: Any, validator_name: str) -> ValidationResult:
    """Convenience validate function."""
    return get_validation_service().validate(value, validator_name)


__all__ = [
    "ValidationRule",
    "ValidationResult",
    "ValidationService",
    "get_validation_service",
    "validate",
]