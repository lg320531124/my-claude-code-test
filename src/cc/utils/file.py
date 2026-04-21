"""File utilities."""

from __future__ import annotations
from typing import Optional
from pathlib import Path
from datetime import datetime


def get_file_info(path: Path) -> dict:
    """Get file metadata."""
    if not path.exists():
        return {"exists": False}

    stat = path.stat()
    return {
        "exists": True,
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
        "size": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "permissions": oct(stat.st_mode)[-3:],
    }


def ensure_dir(path: Path) -> None:
    """Ensure directory exists."""
    path.mkdir(parents=True, exist_ok=True)


def safe_read(path: Path, max_size: int = 10_000_000) -> Optional[str]:
    """Read file safely with size limit."""
    if not path.exists() or not path.is_file():
        return None

    size = path.stat().st_size
    if size > max_size:
        return None

    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
