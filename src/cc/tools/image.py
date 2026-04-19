"""Image Tool - Image file reading and analysis."""

from __future__ import annotations
import base64
from pathlib import Path
from typing import ClassVar, Optional, List
from pydantic import BaseModel, Field

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class ImageInput(ToolInput):
    """Input for ImageTool."""
    file_path: str = Field(description="Image file path")
    analyze: bool = Field(default=False, description="Analyze image content")
    extract_text: bool = Field(default=False, description="Extract text (OCR)")


class ImageResult(BaseModel):
    """Image analysis result."""
    format: str
    width: Optional[int] = None
    height: Optional[int] = None
    size: int
    has_transparency: bool = False
    colors: List[str] = []
    text_detected: Optional[str] = None


class ImageTool(ToolDef):
    """Read and analyze image files."""

    name: ClassVar[str] = "Image"
    description: ClassVar[str] = "Read image files and optionally analyze content"
    input_schema: ClassVar[type] = ImageInput

    # Supported formats
    SUPPORTED_FORMATS = [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff"]

    async def execute(self, input: ImageInput, ctx: ToolUseContext) -> ToolResult:
        """Read the image file."""
        try:
            path = Path(input.file_path)
            if not path.is_absolute():
                path = Path(ctx.cwd) / path

            if not path.exists():
                return ToolResult(
                    content=f"Image not found: {path}",
                    is_error=True,
                )

            if not path.is_file():
                return ToolResult(
                    content=f"Not a file: {path}",
                    is_error=True,
                )

            # Check format
            ext = path.suffix.lower()
            if ext not in self.SUPPORTED_FORMATS:
                return ToolResult(
                    content=f"Unsupported image format: {ext}",
                    is_error=True,
                    metadata={"supported": self.SUPPORTED_FORMATS},
                )

            # Read image
            data = path.read_bytes()
            size = len(data)

            # Get metadata
            metadata = self._get_metadata(path, data)

            # Base64 encode for API
            b64_data = base64.b64encode(data).decode("utf-8")
            media_type = self._get_media_type(ext)

            result_content = f"Image: {path}\n"
            result_content += f"Format: {metadata.format}\n"
            result_content += f"Size: {self._format_size(size)}\n"
            if metadata.width and metadata.height:
                result_content += f"Dimensions: {metadata.width}x{metadata.height}\n"
            if metadata.has_transparency:
                result_content += "Has transparency: yes\n"

            return ToolResult(
                content=result_content,
                metadata={
                    "path": str(path),
                    "format": metadata.format,
                    "size": size,
                    "width": metadata.width,
                    "height": metadata.height,
                    "base64": b64_data,
                    "media_type": media_type,
                },
            )

        except Exception as e:
            return ToolResult(
                content=f"Error reading image: {e}",
                is_error=True,
            )

    def _get_metadata(self, path: Path, data: bytes) -> ImageResult:
        """Get image metadata."""
        ext = path.suffix.lower()
        size = len(data)

        # Basic metadata extraction (would use PIL in production)
        metadata = ImageResult(
            format=ext.lstrip("."),
            size=size,
        )

        # Try to extract dimensions from header
        try:
            if ext in [".png", ".jpg", ".jpeg", ".gif"]:
                # Simple dimension extraction for common formats
                if ext == ".png":
                    # PNG header: IHDR chunk contains dimensions at offset 16-24
                    if len(data) > 24:
                        metadata.width = int.from_bytes(data[16:20], "big")
                        metadata.height = int.from_bytes(data[20:24], "big")
                        metadata.has_transparency = len(data) > 25 and data[25] == 6
                elif ext in [".jpg", ".jpeg"]:
                    # JPEG: would need proper parsing
                    pass
                elif ext == ".gif":
                    # GIF header: dimensions at offset 6-10
                    if len(data) > 10:
                        metadata.width = int.from_bytes(data[6:8], "little")
                        metadata.height = int.from_bytes(data[8:10], "little")
        except Exception:
            pass

        return metadata

    def _get_media_type(self, ext: str) -> str:
        """Get media type for extension."""
        types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
            ".tiff": "image/tiff",
        }
        return types.get(ext, "image/octet-stream")

    def _format_size(self, size: int) -> str:
        """Format file size."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"


__all__ = ["ImageTool", "ImageInput", "ImageResult"]