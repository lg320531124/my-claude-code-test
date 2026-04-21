"""Attachments Utils - Handle file attachments."""

from __future__ import annotations
import base64
import mimetypes
from pathlib import Path
from typing import Dict, Any, Optional, List


async def read_attachment(path: Path) -> Dict[str, Any]:
    """Read file attachment."""
    import aiofiles

    if not path.exists():
        return {"error": f"File not found: {path}"}

    # Detect type
    mime_type, _ = mimetypes.guess_type(str(path))

    # Read content
    if mime_type and mime_type.startswith("image/"):
        # Binary - encode as base64
        async with aiofiles.open(path, "rb") as f:
            content = await f.read()
        encoded = base64.b64encode(content).decode()
        return {
            "type": "image",
            "mime_type": mime_type,
            "data": encoded,
            "path": str(path),
        }
    else:
        # Text
        async with aiofiles.open(path, "r", errors="replace") as f:
            content = await f.read()
        return {
            "type": "text",
            "mime_type": mime_type or "text/plain",
            "data": content,
            "path": str(path),
        }


async def detect_image_type(content: bytes) -> Optional[str]:
    """Detect image type from bytes."""
    # Check magic bytes
    magic_bytes = {
        b"\xff\xd8\xff": "image/jpeg",
        b"\x89PNG\r\n\x1a\n": "image/png",
        b"GIF87a": "image/gif",
        b"GIF89a": "image/gif",
        b"BM": "image/bmp",
        b"\x00\x00\x00\x0c": "image/webp",
    }

    for magic, mime in magic_bytes.items():
        if content.startswith(magic):
            return mime

    return None


def get_file_info(path: Path) -> Dict[str, Any]:
    """Get file info."""
    stat = path.stat()

    return {
        "path": str(path),
        "name": path.name,
        "size": stat.st_size,
        "modified": stat.st_mtime,
        "is_dir": path.is_dir(),
        "extension": path.suffix,
        "mime_type": mimetypes.guess_type(str(path))[0],
    }


async def process_attachments(paths: List[Path]) -> List[Dict[str, Any]]:
    """Process multiple attachments."""
    results = []
    for path in paths:
        result = await read_attachment(path)
        results.append(result)
    return results


def create_image_block(data: str, mime_type: str) -> Dict[str, Any]:
    """Create image content block."""
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": mime_type,
            "data": data,
        },
    }


def create_file_block(content: str, path: str) -> Dict[str, Any]:
    """Create file content block."""
    return {
        "type": "text",
        "text": f"File: {path}\n\n{content}",
    }


__all__ = [
    "read_attachment",
    "detect_image_type",
    "get_file_info",
    "process_attachments",
    "create_image_block",
    "create_file_block",
]