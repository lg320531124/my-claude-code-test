"""Shared tool validation.

Common validation logic for tool inputs.
"""

from __future__ import annotations
import asyncio
import re
from pathlib import Path
from typing import Dict, Any, Optional

from ..types.tool import ValidationResult
from ..utils.async_io import exists_async, is_file_async, is_dir_async


def validate_file_path(
    file_path: str,
    must_exist: bool = True,
    must_be_file: bool = True,
) -> ValidationResult:
    """Validate file path input."""
    if not file_path:
        return ValidationResult(
            result=False,
            message="File path is required",
            error_code=1,
        )

    # Expand path
    if file_path.startswith("~"):
        file_path = str(Path(file_path).expanduser())

    if must_exist:
        path = Path(file_path)
        if not path.exists():
            # Try to find similar file
            similar = find_similar_file(file_path)
            msg = f"File does not exist: {file_path}"
            if similar:
                msg += f" Did you mean {similar}?"
            return ValidationResult(
                result=False,
                message=msg,
                error_code=2,
            )

        if must_be_file and not path.is_file():
            return ValidationResult(
                result=False,
                message=f"Path is not a file: {file_path}",
                error_code=3,
            )

    return ValidationResult(result=True)


async def async_validate_file_path(
    file_path: str,
    must_exist: bool = True,
    must_be_file: bool = True,
) -> ValidationResult:
    """Async validate file path."""
    if not file_path:
        return ValidationResult(
            result=False,
            message="File path is required",
            error_code=1,
        )

    # Expand path
    if file_path.startswith("~"):
        file_path = str(Path(file_path).expanduser())

    if must_exist:
        exists = await exists_async(file_path)
        if not exists:
            similar = await asyncio.get_event_loop().run_in_executor(
                None, lambda: find_similar_file(file_path)
            )
            msg = f"File does not exist: {file_path}"
            if similar:
                msg += f" Did you mean {similar}?"
            return ValidationResult(
                result=False,
                message=msg,
                error_code=2,
            )

        if must_be_file:
            is_file = await is_file_async(file_path)
            if not is_file:
                return ValidationResult(
                    result=False,
                    message=f"Path is not a file: {file_path}",
                    error_code=3,
                )

    return ValidationResult(result=True)


def validate_directory_path(
    dir_path: str,
    must_exist: bool = True,
) -> ValidationResult:
    """Validate directory path input."""
    if not dir_path:
        return ValidationResult(
            result=False,
            message="Directory path is required",
            error_code=1,
        )

    if dir_path.startswith("~"):
        dir_path = str(Path(dir_path).expanduser())

    if must_exist:
        path = Path(dir_path)
        if not path.exists():
            return ValidationResult(
                result=False,
                message=f"Directory does not exist: {dir_path}",
                error_code=2,
            )
        if not path.is_dir():
            return ValidationResult(
                result=False,
                message=f"Path is not a directory: {dir_path}",
                error_code=3,
            )

    return ValidationResult(result=True)


async def async_validate_directory_path(
    dir_path: str,
    must_exist: bool = True,
) -> ValidationResult:
    """Async validate directory path."""
    if not dir_path:
        return ValidationResult(
            result=False,
            message="Directory path is required",
            error_code=1,
        )

    if dir_path.startswith("~"):
        dir_path = str(Path(dir_path).expanduser())

    if must_exist:
        exists = await exists_async(dir_path)
        if not exists:
            return ValidationResult(
                result=False,
                message=f"Directory does not exist: {dir_path}",
                error_code=2,
            )

        is_dir = await is_dir_async(dir_path)
        if not is_dir:
            return ValidationResult(
                result=False,
                message=f"Path is not a directory: {dir_path}",
                error_code=3,
            )

    return ValidationResult(result=True)


def validate_pattern(pattern: str) -> ValidationResult:
    """Validate search pattern."""
    if not pattern:
        return ValidationResult(
            result=False,
            message="Pattern is required",
            error_code=1,
        )

    # Check for valid regex (if pattern looks like regex)
    if any(char in pattern for char in ["(", "[", "*", "+", "?"]):
        try:
            re.compile(pattern)
        except re.error as e:
            return ValidationResult(
                result=False,
                message=f"Invalid regex pattern: {e}",
                error_code=2,
            )

    return ValidationResult(result=True)


def find_similar_file(file_path: str, cwd: str = "") -> Optional[str]:
    """Find similar file name (typo correction)."""
    import os
    from pathlib import Path

    path = Path(file_path)
    parent = path.parent
    name = path.name.lower()

    if not parent.exists():
        return None

    # List files in parent directory
    try:
        files = list(parent.iterdir())
    except OSError:
        return None

    # Find similar names
    for f in files:
        if f.name.lower() == name:
            return str(f)
        # Check for common typos (missing extension, etc.)
        if f.name.lower().startswith(name[:5]):
            return str(f)

    return None


def validate_url(url: str) -> ValidationResult:
    """Validate URL."""
    if not url:
        return ValidationResult(
            result=False,
            message="URL is required",
            error_code=1,
        )

    # Simple URL validation
    pattern = r"^https?://[^\s/$.?#].[^\s]*$"
    if not re.match(pattern, url):
        return ValidationResult(
            result=False,
            message=f"Invalid URL format: {url}",
            error_code=2,
        )

    return ValidationResult(result=True)


__all__ = [
    "validate_file_path",
    "async_validate_file_path",
    "validate_directory_path",
    "async_validate_directory_path",
    "validate_pattern",
    "validate_url",
    "find_similar_file",
]