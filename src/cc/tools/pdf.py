"""PDF Tool - PDF file reading."""

from __future__ import annotations
from pathlib import Path
from typing import ClassVar, Optional
from pydantic import BaseModel, Field

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class PDFInput(ToolInput):
    """Input for PDFTool."""
    file_path: str = Field(description="PDF file path")
    pages: Optional[str] = Field(default=None, description="Page range (e.g., '1-5', '3', '10-20')")
    max_pages: int = Field(default=20, description="Maximum pages to read")


class PDFTool(ToolDef):
    """Read PDF files."""

    name: ClassVar[str] = "PDF"
    description: ClassVar[str] = "Read PDF files with optional page range"
    input_schema: ClassVar[type] = PDFInput

    async def execute(self, input: PDFInput, ctx: ToolUseContext) -> ToolResult:
        """Read the PDF file."""
        try:
            path = Path(input.file_path)
            if not path.is_absolute():
                path = Path(ctx.cwd) / path

            if not path.exists():
                return ToolResult(
                    content=f"PDF not found: {path}",
                    is_error=True,
                )

            if not path.is_file() or path.suffix.lower() != ".pdf":
                return ToolResult(
                    content=f"Not a PDF file: {path}",
                    is_error=True,
                )

            # In production, would use pdfplumber or PyPDF2
            # For now, return metadata
            size = path.stat().st_size

            result_content = f"PDF: {path}\n"
            result_content += f"Size: {self._format_size(size)}\n"
            result_content += f"\nNote: PDF content extraction requires pdfplumber or PyPDF2 library.\n"
            result_content += f"Install with: pip install pdfplumber\n"
            result_content += f"\nTo extract content, use:\n"
            result_content += f"  pages: {input.pages or 'all'} (max {input.max_pages})\n"

            return ToolResult(
                content=result_content,
                metadata={
                    "path": str(path),
                    "size": size,
                    "pages_requested": input.pages,
                    "max_pages": input.max_pages,
                },
            )

        except Exception as e:
            return ToolResult(
                content=f"Error reading PDF: {e}",
                is_error=True,
            )

    def _format_size(self, size: int) -> str:
        """Format file size."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"


__all__ = ["PDFTool", "PDFInput"]