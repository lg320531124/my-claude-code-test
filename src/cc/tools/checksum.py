"""Checksum Tool - File checksum calculation."""

from __future__ import annotations
import hashlib
from pathlib import Path
from typing import ClassVar, Optional
from pydantic import Field

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class ChecksumInput(ToolInput):
    """Input for ChecksumTool."""
    file_path: str = Field(description="File path to calculate checksum")
    algorithm: str = Field(default="sha256", description="Algorithm: md5, sha1, sha256, sha512")
    compare: Optional[str] = Field(default=None, description="Expected checksum to compare")


class ChecksumTool(ToolDef):
    """Calculate file checksums."""

    name: ClassVar[str] = "Checksum"
    description: ClassVar[str] = "Calculate checksum for files"
    input_schema: ClassVar[type] = ChecksumInput

    ALGORITHMS = ["md5", "sha1", "sha256", "sha512"]

    async def execute(self, input: ChecksumInput, ctx: ToolUseContext) -> ToolResult:
        """Calculate checksum."""
        try:
            path = Path(input.file_path)
            if not path.is_absolute():
                path = Path(ctx.cwd) / path

            if not path.exists():
                return ToolResult(
                    content=f"File not found: {path}",
                    is_error=True,
                )

            if not path.is_file():
                return ToolResult(
                    content=f"Not a file: {path}",
                    is_error=True,
                )

            algorithm = input.algorithm.lower()
            if algorithm not in self.ALGORITHMS:
                return ToolResult(
                    content=f"Unknown algorithm: {algorithm}. Supported: {self.ALGORITHMS}",
                    is_error=True,
                )

            # Calculate checksum
            checksum = self._calculate_checksum(path, algorithm)

            # Compare if provided
            if input.compare:
                match = checksum.lower() == input.compare.lower()
                result = f"Checksum: {checksum}\nExpected: {input.compare}\nMatch: {match}"
                return ToolResult(
                    content=result,
                    metadata={
                        "checksum": checksum,
                        "expected": input.compare,
                        "match": match,
                    },
                )

            return ToolResult(
                content=f"{algorithm}: {checksum}",
                metadata={
                    "algorithm": algorithm,
                    "checksum": checksum,
                    "file": str(path),
                    "size": path.stat().st_size,
                },
            )

        except Exception as e:
            return ToolResult(
                content=f"Error calculating checksum: {e}",
                is_error=True,
            )

    def _calculate_checksum(self, path: Path, algorithm: str) -> str:
        """Calculate file checksum."""
        if algorithm == "md5":
            hasher = hashlib.md5()
        elif algorithm == "sha1":
            hasher = hashlib.sha1()
        elif algorithm == "sha256":
            hasher = hashlib.sha256()
        elif algorithm == "sha512":
            hasher = hashlib.sha512()
        else:
            hasher = hashlib.sha256()

        # Read in chunks for large files
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)

        return hasher.hexdigest()


__all__ = ["ChecksumTool", "ChecksumInput"]