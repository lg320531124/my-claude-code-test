"""ReadTool - File reading with comprehensive format support.

Ported from TypeScript FileReadTool/FileReadTool.ts patterns:
- Input schema with file_path, offset, limit, pages (for PDF)
- Image handling with token budget compression
- PDF handling with page extraction
- Notebook (.ipynb) handling
- File deduplication logic
- Blocked device paths
- macOS screenshot path resolution
- Permission checking
- Token validation
"""

from __future__ import annotations
import base64
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable, Dict, Any, Optional, Set, List, Tuple
from enum import Enum

from pydantic import BaseModel, Field

from ..types.tool import Tool, ToolInput, ToolResult, ToolUseContext, ValidationResult
from ..types.permission import PermissionResult, PermissionDecision
from ..types.message import ToolResultBlock
from ..utils.async_io import read_file_async, read_file_binary_async, stat_async


# Constants
THIN_SPACE = chr(8239)  # macOS screenshot thin space
DEFAULT_MAX_TOKENS = 50000
DEFAULT_MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
PDF_MAX_PAGES_PER_READ = 20
PDF_AT_MENTION_INLINE_THRESHOLD = 20
PDF_EXTRACT_SIZE_THRESHOLD = 2 * 1024 * 1024  # 2MB

# Blocked device paths (infinite output or blocking input)
BLOCKED_DEVICE_PATHS: Set[str] = {
    "/dev/zero",
    "/dev/random",
    "/dev/urandom",
    "/dev/full",
    "/dev/stdin",
    "/dev/tty",
    "/dev/console",
    "/dev/stdout",
    "/dev/stderr",
    "/dev/fd/0",
    "/dev/fd/1",
    "/dev/fd/2",
}

# Image extensions
IMAGE_EXTENSIONS: Set[str] = {"png", "jpg", "jpeg", "gif", "webp"}

# Binary extensions (not readable by this tool)
BINARY_EXTENSIONS: Set[str] = {
    "exe", "dll", "so", "dylib", "bin", "dat",
    "db", "sqlite", "sqlite3", "pyc", "pyd",
    "class", "jar", "war", "aar",
}


class FileType(str, Enum):
    """File type classification."""

    TEXT = "text"
    IMAGE = "image"
    PDF = "pdf"
    NOTEBOOK = "notebook"
    BINARY = "binary"


def is_blocked_device_path(file_path: str) -> bool:
    """Check if path is a blocked device file."""
    if file_path in BLOCKED_DEVICE_PATHS:
        return True
    # Check /proc/self/fd paths
    if file_path.startswith("/proc/") and (
        file_path.endswith("/fd/0") or
        file_path.endswith("/fd/1") or
        file_path.endswith("/fd/2")
    ):
        return True
    return False


def has_binary_extension(file_path: str) -> bool:
    """Check if file has binary extension."""
    ext = Path(file_path).suffix.lower().lstrip(".")
    return ext in BINARY_EXTENSIONS


def is_image_extension(ext: str) -> bool:
    """Check if extension is an image type."""
    return ext.lower().lstrip(".") in IMAGE_EXTENSIONS


def is_pdf_extension(ext: str) -> bool:
    """Check if extension is PDF."""
    return ext.lower().lstrip(".") == "pdf"


def is_notebook_extension(ext: str) -> bool:
    """Check if extension is Jupyter notebook."""
    return ext.lower().lstrip(".") == "ipynb"


def get_alternate_screenshot_path(file_path: str) -> Optional[str]:
    """Get alternate path for macOS screenshot with different space character."""
    filename = Path(file_path).name
    am_pm_pattern = r"^(.+)([ \u202F])(AM|PM)(\.png)$"
    match = re.match(am_pm_pattern, filename)
    if not match:
        return None

    current_space = match.group(2)
    alternate_space = THIN_SPACE if current_space == " " else " "
    new_filename = f"{match.group(1)}{alternate_space}{match.group(3)}{match.group(4)}"
    return str(Path(file_path).parent / new_filename)


def expand_path(file_path: str) -> str:
    """Expand path (handle ~, environment variables, etc)."""
    # Handle ~
    if file_path.startswith("~"):
        file_path = os.path.expanduser(file_path)
    # Handle environment variables
    file_path = os.path.expandvars(file_path)
    # Normalize
    return os.path.abspath(file_path)


def add_line_numbers(content: str, start_line: int = 1) -> str:
    """Add line numbers to content."""
    lines = content.splitlines()
    return "\n".join(
        f"{i + start_line:6}\t{line}"
        for i, line in enumerate(lines)
    )


def detect_image_format(data: bytes) -> str:
    """Detect image format from binary data."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    elif data[:2] == b"\xff\xd8":
        return "jpeg"
    elif data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return "png"  # Default


def estimate_tokens(content: str) -> int:
    """Estimate token count for content."""
    # Rough estimation: ~4 chars per token for text
    return len(content) // 4


def parse_pdf_page_range(pages: str) -> Optional[Tuple[int, int]]:
    """Parse PDF page range string like "1-5", "3", "10-20"."""
    try:
        if "-" in pages:
            parts = pages.split("-")
            first = int(parts[0])
            last = int(parts[1]) if len(parts) > 1 else first
            return (first, last)
        else:
            page = int(pages)
            return (page, page)
    except ValueError:
        return None


class ReadInput(ToolInput):
    """Input for ReadTool."""

    file_path: str = Field(description="The absolute path to the file to read")
    offset: Optional[int] = Field(
        default=0,
        description="The line number to start reading from"
    )
    limit: Optional[int] = Field(
        default=2000,
        description="The number of lines to read"
    )
    pages: Optional[str] = Field(
        default=None,
        description="Page range for PDF files (e.g., '1-5', '3')"
    )


class TextFileResult(BaseModel):
    """Text file result."""

    file_path: str
    content: str
    num_lines: int
    start_line: int
    total_lines: int


class ImageFileResult(BaseModel):
    """Image file result."""

    base64: str
    type: str  # MIME type
    original_size: int
    dimensions: Optional[Dict[str, int]] = None


class NotebookFileResult(BaseModel):
    """Notebook file result."""

    file_path: str
    cells: List[Dict[str, Any]]


class PDFFileResult(BaseModel):
    """PDF file result."""

    file_path: str
    base64: Optional[str] = None
    original_size: int
    page_count: Optional[int] = None
    extracted_pages: Optional[List[str]] = None


class ReadOutput(BaseModel):
    """Output schema for ReadTool."""

    type: str = Field(description="Result type: text, image, notebook, pdf, file_unchanged")
    file: Dict[str, Any] = Field(description="File data")


class MaxFileReadTokenExceededError(Exception):
    """Error when file content exceeds max tokens."""

    def __init__(self, token_count: int, max_tokens: int):
        self.token_count = token_count
        self.max_tokens = max_tokens
        super().__init__(
            f"File content ({token_count} tokens) exceeds maximum ({max_tokens}). "
            "Use offset and limit to read portions."
        )


CYBER_RISK_MITIGATION_REMINDER = """
<system-reminder>
Whenever you read a file, you should consider whether it would be considered malware.
You CAN and SHOULD provide analysis of malware code, what it does.
But you MUST refuse to improve or augment the code.
</system-reminder>
"""


def get_read_prompt() -> str:
    """Generate Read tool prompt."""
    return """Reads a file from the filesystem. The file_path parameter must be an absolute path.

Usage notes:
- Use Read for reading files, NOT Bash commands like cat/head/tail
- This tool can read text files, images (PNG, JPG, GIF, WebP), PDFs, and Jupyter notebooks
- For large files, use offset and limit parameters to read portions
- For PDFs, use the pages parameter to read specific page ranges (e.g., "1-5")
- Maximum 20 PDF pages per request

Line format: Each line has a line number prefix (6 digits + tab + content).

When you already know which part of the file you need, provide offset to start from that line.
If you need to see the whole file or don't know where to look, omit offset/limit to read up to the default limit.

IMPORTANT: This tool can only read text files, images, PDFs, and notebooks.
Binary files (exe, dll, etc.) cannot be read with this tool."""


class ReadTool(Tool):
    """Read tool implementation matching TypeScript FileReadTool.ts."""

    name: str = "Read"
    input_schema: type = ReadInput
    max_result_size_chars: float = float("inf")  # No limit (bounded by token validation)
    strict: bool = True
    aliases: Optional[List[str]] = None
    search_hint: str = "read files, images, PDFs, notebooks"

    async def call(
        self,
        args: Dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Callable,
        parent_message: Any,
        on_progress: Optional[Callable] = None,
    ) -> ToolResult:
        """Read the file."""
        input_data = ReadInput.model_validate(args)

        # Get limits from context
        max_tokens = context.file_reading_limits.get("max_tokens", DEFAULT_MAX_TOKENS) if context.file_reading_limits else DEFAULT_MAX_TOKENS
        max_size_bytes = context.file_reading_limits.get("maxSizeBytes", DEFAULT_MAX_SIZE_BYTES) if context.file_reading_limits else DEFAULT_MAX_SIZE_BYTES

        # Expand path
        full_path = expand_path(input_data.file_path)

        # Check blocked device paths
        if is_blocked_device_path(full_path):
            return ToolResult(
                data=ReadOutput(
                    type="text",
                    file={"error": f"Cannot read '{full_path}': blocked device file"},
                ),
                is_error=True,
            )

        # Get extension
        ext = Path(full_path).suffix.lower().lstrip(".")

        # Check deduplication
        existing_state = context.read_file_state.get(full_path)
        if existing_state and not existing_state.get("isPartialView", False) and existing_state.get("offset") is not None:
            range_match = existing_state.get("offset") == input_data.offset and existing_state.get("limit") == input_data.limit
            if range_match:
                try:
                    mtime = Path(full_path).stat().st_mtime
                    if mtime == existing_state.get("timestamp"):
                        # File unchanged - return stub
                        return ToolResult(
                            data=ReadOutput(
                                type="file_unchanged",
                                file={"filePath": input_data.file_path},
                            ),
                        )
                except OSError:
                    pass  # Fall through to full read

        # Try alternate screenshot path for macOS
        resolved_path = full_path
        if not Path(full_path).exists():
            alt_path = get_alternate_screenshot_path(full_path)
            if alt_path and Path(alt_path).exists():
                resolved_path = alt_path
            else:
                # Find similar files
                similar = find_similar_file(full_path, context.cwd)
                msg = f"File does not exist: {full_path}"
                if similar:
                    msg += f" Did you mean {similar}?"
                return ToolResult(
                    data=ReadOutput(type="text", file={"error": msg}),
                    is_error=True,
                )

        try:
            # Determine file type and read accordingly
            if is_notebook_extension(ext):
                return await self._read_notebook(
                    input_data.file_path,
                    resolved_path,
                    max_size_bytes,
                    max_tokens,
                    context,
                )
            elif is_image_extension(ext):
                return await self._read_image(
                    input_data.file_path,
                    resolved_path,
                    max_tokens,
                    context,
                )
            elif is_pdf_extension(ext):
                return await self._read_pdf(
                    input_data.file_path,
                    resolved_path,
                    input_data.pages,
                    max_size_bytes,
                    max_tokens,
                    context,
                )
            else:
                return await self._read_text(
                    input_data.file_path,
                    resolved_path,
                    input_data.offset or 0,
                    input_data.limit,
                    max_size_bytes,
                    max_tokens,
                    context,
                )
        except MaxFileReadTokenExceededError as e:
            return ToolResult(
                data=ReadOutput(
                    type="text",
                    file={"error": str(e)},
                ),
                is_error=True,
            )
        except Exception as e:
            return ToolResult(
                data=ReadOutput(type="text", file={"error": f"Error reading file: {e}"}),
                is_error=True,
            )

    async def _read_text(
        self,
        file_path: str,
        resolved_path: str,
        offset: int,
        limit: Optional[int],
        max_size_bytes: int,
        max_tokens: int,
        context: ToolUseContext,
    ) -> ToolResult:
        """Read text file using async I/O."""
        path = Path(resolved_path)

        # Check file size (async)
        stat_result = await stat_async(resolved_path)
        file_size = stat_result.st_size
        if file_size > max_size_bytes and limit is None:
            return ToolResult(
                data=ReadOutput(
                    type="text",
                    file={"error": f"File ({file_size} bytes) exceeds max ({max_size_bytes}). Use offset/limit."},
                ),
                is_error=True,
            )

        # Read content asynchronously
        content = await read_file_async(
            resolved_path,
            encoding="utf-8",
            limit=limit,
            offset=offset,
        )

        # If no limit/offset, read full file
        if limit is None and offset == 0:
            content = await read_file_async(resolved_path, encoding="utf-8")

        lines = content.splitlines()
        total_lines = len(lines) if limit is None else len((await read_file_async(resolved_path)).splitlines())

        # Apply offset (0-indexed internally)
        line_offset = offset if offset == 0 else offset - 1
        if line_offset >= total_lines:
            return ToolResult(
                data=ReadOutput(
                    type="text",
                    file={
                        "filePath": file_path,
                        "content": "",
                        "numLines": 0,
                        "startLine": offset,
                        "totalLines": total_lines,
                    },
                ),
            )

        start_idx = line_offset
        end_idx = total_lines if limit is None else min(start_idx + limit, total_lines)
        read_lines = lines[start_idx:end_idx]

        # Format with line numbers
        numbered_content = add_line_numbers("\n".join(read_lines), offset + 1)

        # Validate tokens
        token_estimate = estimate_tokens(numbered_content)
        if token_estimate > max_tokens:
            raise MaxFileReadTokenExceededError(token_estimate, max_tokens)

        # Add cyber risk reminder
        full_content = numbered_content + CYBER_RISK_MITIGATION_REMINDER

        # Update file state
        if context.read_file_state:
            context.read_file_state[resolved_path] = {
                "content": content,
                "timestamp": path.stat().st_mtime,
                "offset": offset,
                "limit": limit,
            }

        return ToolResult(
            data=ReadOutput(
                type="text",
                file={
                    "filePath": file_path,
                    "content": full_content,
                    "numLines": len(read_lines),
                    "startLine": offset + 1,
                    "totalLines": total_lines,
                },
            ),
        )

    async def _read_image(
        self,
        file_path: str,
        resolved_path: str,
        max_tokens: int,
        context: ToolUseContext,
    ) -> ToolResult:
        """Read image file using async I/O."""
        path = Path(resolved_path)

        # Read binary data asynchronously
        data = await read_file_binary_async(resolved_path)
        original_size = len(data)

        if original_size == 0:
            return ToolResult(
                data=ReadOutput(type="text", file={"error": f"Image file is empty: {file_path}"}),
                is_error=True,
            )

        # Detect format
        media_type = detect_image_format(data)

        # Convert to base64
        base64_data = base64.b64encode(data).decode("utf-8")

        # Check token budget (base64 is ~1.33x larger)
        estimated_tokens = len(base64_data) // 3  # Rough estimate
        if estimated_tokens > max_tokens:
            # Would need compression - simplified for now
            # In TypeScript, uses sharp for compression
            pass

        return ToolResult(
            data=ReadOutput(
                type="image",
                file={
                    "base64": base64_data,
                    "type": f"image/{media_type}",
                    "originalSize": original_size,
                },
            ),
        )

    async def _read_pdf(
        self,
        file_path: str,
        resolved_path: str,
        pages: Optional[str],
        max_size_bytes: int,
        max_tokens: int,
        context: ToolUseContext,
    ) -> ToolResult:
        """Read PDF file using async I/O."""
        path = Path(resolved_path)

        # Check file size asynchronously
        stat_result = await stat_async(resolved_path)
        file_size = stat_result.st_size

        # Parse page range if provided
        if pages:
            parsed = parse_pdf_page_range(pages)
            if not parsed:
                return ToolResult(
                    data=ReadOutput(
                        type="text",
                        file={"error": f"Invalid pages parameter: '{pages}'. Use '1-5', '3', etc."},
                    ),
                    is_error=True,
                )
            first_page, last_page = parsed
            page_count = last_page - first_page + 1
            if page_count > PDF_MAX_PAGES_PER_READ:
                return ToolResult(
                    data=ReadOutput(
                        type="text",
                        file={"error": f"Page range exceeds max {PDF_MAX_PAGES_PER_READ} pages"},
                    ),
                    is_error=True,
                )

        # Read PDF (simplified - in TypeScript uses pdf.js)
        # For now, return metadata - using async binary read
        data = await read_file_binary_async(resolved_path)
        base64_data = base64.b64encode(data).decode("utf-8")

        return ToolResult(
            data=ReadOutput(
                type="pdf",
                file={
                    "filePath": file_path,
                    "base64": base64_data,
                    "originalSize": file_size,
                },
            ),
        )

    async def _read_notebook(
        self,
        file_path: str,
        resolved_path: str,
        max_size_bytes: int,
        max_tokens: int,
        context: ToolUseContext,
    ) -> ToolResult:
        """Read Jupyter notebook using async I/O."""
        path = Path(resolved_path)

        # Read and parse notebook asynchronously
        notebook_content = await read_file_async(resolved_path, encoding="utf-8")
        notebook_data = json.loads(notebook_content)
        cells = notebook_data.get("cells", [])

        # Check size
        cells_json = json.dumps(cells)
        if len(cells_json) > max_size_bytes:
            return ToolResult(
                data=ReadOutput(
                    type="text",
                    file={"error": "Notebook too large. Use Bash with jq to read specific cells."},
                ),
                is_error=True,
            )

        # Validate tokens
        token_estimate = estimate_tokens(cells_json)
        if token_estimate > max_tokens:
            raise MaxFileReadTokenExceededError(token_estimate, max_tokens)

        # Update file state
        if context.read_file_state:
            context.read_file_state[resolved_path] = {
                "content": cells_json,
                "timestamp": path.stat().st_mtime,
                "offset": 0,
                "limit": None,
            }

        return ToolResult(
            data=ReadOutput(
                type="notebook",
                file={
                    "filePath": file_path,
                    "cells": cells,
                },
            ),
        )

    async def description(
        self,
        input: Dict[str, Any],
        options: Dict[str, Any],
    ) -> str:
        """Generate tool description."""
        file_path = input.get("file_path", "")
        if file_path:
            return f"Read {file_path}"
        return "Read file"

    async def prompt(
        self,
        options: Dict[str, Any],
    ) -> str:
        """Generate tool prompt."""
        return get_read_prompt()

    def is_concurrency_safe(self, input: Dict[str, Any]) -> bool:
        """Check if tool is safe for concurrent execution."""
        return True  # Reading is always concurrency-safe

    def is_read_only(self, input: Dict[str, Any]) -> bool:
        """Check if tool is read-only."""
        return True

    def to_auto_classifier_input(self, input: Dict[str, Any]) -> str:
        """Convert input for auto-mode classifier."""
        return input.get("file_path", "")

    def is_search_or_read_command(self, input: Dict[str, Any]) -> Dict[str, bool]:
        """Check if this is a search/read operation."""
        return {"is_search": False, "is_read": True, "is_list": False}

    def get_path(self, input: Dict[str, Any]) -> Optional[str]:
        """Get file path from input."""
        return input.get("file_path")

    def get_tool_use_summary(self, input: Optional[Dict[str, Any]]) -> Optional[str]:
        """Get short summary for compact view."""
        if not input or not input.get("file_path"):
            return None
        return f"Read {Path(input['file_path']).name}"

    def get_activity_description(self, input: Optional[Dict[str, Any]]) -> Optional[str]:
        """Get activity description for spinner."""
        if not input or not input.get("file_path"):
            return "Reading file"
        return f"Reading {Path(input['file_path']).name}"

    def user_facing_name(self, input: Optional[Dict[str, Any]]) -> str:
        """Get user-facing name."""
        return "Read"

    def validate_input(
        self,
        input: Dict[str, Any],
        context: ToolUseContext,
    ) -> ValidationResult:
        """Validate tool input."""
        # Validate pages parameter
        if input.get("pages"):
            parsed = parse_pdf_page_range(input["pages"])
            if not parsed:
                return ValidationResult(
                    result=False,
                    message=f"Invalid pages: '{input['pages']}'. Use '1-5', '3', etc.",
                    error_code=7,
                )
            page_count = parsed[1] - parsed[0] + 1
            if page_count > PDF_MAX_PAGES_PER_READ:
                return ValidationResult(
                    result=False,
                    message=f"Page range exceeds max {PDF_MAX_PAGES_PER_READ} pages",
                    error_code=8,
                )

        # Expand path
        full_path = expand_path(input.get("file_path", ""))

        # Check blocked device paths
        if is_blocked_device_path(full_path):
            return ValidationResult(
                result=False,
                message=f"Cannot read '{full_path}': blocked device file",
                error_code=9,
            )

        # Check binary extension
        ext = Path(full_path).suffix.lower()
        if has_binary_extension(full_path) and not is_pdf_extension(ext) and not is_image_extension(ext.lstrip(".")):
            return ValidationResult(
                result=False,
                message=f"This tool cannot read binary {ext} files.",
                error_code=4,
            )

        return ValidationResult(result=True)

    async def check_permissions(
        self,
        input: Dict[str, Any],
        context: ToolUseContext,
    ) -> PermissionResult:
        """Check tool permissions."""
        file_path = expand_path(input.get("file_path", ""))

        # Check if file is in deny list (simplified)
        # In TypeScript, uses checkReadPermissionForTool

        return PermissionResult(
            decision=PermissionDecision.ALLOW,
            updated_input=input,
        )

    def backfill_observable_input(self, input: Dict[str, Any]) -> None:
        """Backfill input with expanded path."""
        if "file_path" in input:
            input["file_path"] = expand_path(input["file_path"])

    def map_tool_result_to_tool_result_block_param(
        self,
        data: Any,
        tool_use_id: str,
    ) -> ToolResultBlock:
        """Map result to API block."""
        if isinstance(data, ReadOutput):
            if data.type == "image":
                return ToolResultBlock(
                    tool_use_id=tool_use_id,
                    content=[
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "data": data.file["base64"],
                                "media_type": data.file["type"],
                            },
                        }
                    ],
                )
            elif data.type == "file_unchanged":
                return ToolResultBlock(
                    tool_use_id=tool_use_id,
                    content="<file-unchanged>File content unchanged from previous read</file-unchanged>",
                )
            elif data.type == "text":
                file_data = data.file
                if "error" in file_data:
                    return ToolResultBlock(
                        tool_use_id=tool_use_id,
                        content=file_data["error"],
                        is_error=True,
                    )
                return ToolResultBlock(
                    tool_use_id=tool_use_id,
                    content=file_data.get("content", ""),
                )
            elif data.type == "notebook":
                # Format notebook cells
                cells = data.file.get("cells", [])
                content = self._format_notebook_cells(cells)
                return ToolResultBlock(
                    tool_use_id=tool_use_id,
                    content=content,
                )
            elif data.type == "pdf":
                return ToolResultBlock(
                    tool_use_id=tool_use_id,
                    content=f"PDF file read: {data.file.get('filePath')} ({data.file.get('originalSize')} bytes)",
                )

        return ToolResultBlock(
            tool_use_id=tool_use_id,
            content=str(data),
        )

    def _format_notebook_cells(self, cells: List[Dict[str, Any]]) -> str:
        """Format notebook cells for display."""
        lines = []
        for i, cell in enumerate(cells):
            cell_type = cell.get("cell_type", "unknown")
            lines.append(f"\n## Cell {i + 1} ({cell_type})")
            source = cell.get("source", [])
            if isinstance(source, list):
                lines.extend(source)
            else:
                lines.append(source)
            if cell.get("outputs"):
                lines.append("\n### Outputs:")
                for output in cell["outputs"]:
                    if "text" in output:
                        lines.extend(output["text"] if isinstance(output["text"], list) else [output["text"]])
        return "\n".join(lines)


def find_similar_file(file_path: str, cwd: str) -> Optional[str]:
    """Find similar file in current directory."""
    path = Path(file_path)
    filename = path.name
    parent = path.parent

    try:
        for f in parent.iterdir():
            if f.name.lower() == filename.lower() and f.name != filename:
                return str(f)
    except OSError:
        pass

    return None


def build_read_tool() -> ReadTool:
    """Build ReadTool instance."""
    return ReadTool()


__all__ = [
    "ReadTool",
    "ReadInput",
    "ReadOutput",
    "build_read_tool",
    "get_read_prompt",
    "is_blocked_device_path",
    "has_binary_extension",
    "is_image_extension",
    "is_pdf_extension",
    "is_notebook_extension",
    "expand_path",
    "add_line_numbers",
    "detect_image_format",
    "parse_pdf_page_range",
    "MaxFileReadTokenExceededError",
    "DEFAULT_MAX_TOKENS",
    "DEFAULT_MAX_SIZE_BYTES",
    "PDF_MAX_PAGES_PER_READ",
]


# Add execute method to ReadTool
def _add_execute_method():
    async def execute(self, input: ReadInput, ctx: ToolUseContext) -> ToolResult:
        """Execute method for simpler interface."""
        args = input.model_dump() if hasattr(input, 'model_dump') else dict(input)
        return await self.call(args, ctx, lambda *args: True, None)
    ReadTool.execute = execute

_add_execute_method()