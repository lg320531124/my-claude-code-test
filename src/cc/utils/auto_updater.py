"""Auto Updater - Check and apply updates."""

from __future__ import annotations
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class UpdateInfo:
    """Update information."""
    current_version: str
    latest_version: str
    update_available: bool
    release_notes: str
    download_url: str
    published_at: datetime


class AutoUpdater:
    """Auto update checker."""

    def __init__(self, current_version: str = "0.1.0"):
        self.current_version = current_version
        self._last_check: Optional[datetime] = None
        self._update_info: Optional[UpdateInfo] = None

    async def check_update(self, force: bool = False) -> Optional[UpdateInfo]:
        """Check for updates."""
        # Skip if recently checked
        if not force and self._last_check:
            hours_since = (datetime.now() - self._last_check).total_seconds() / 3600
            if hours_since < 24:
                return self._update_info

        try:
            # Fetch latest version
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.github.com/repos/anthropics/claude-code/releases/latest",
                    timeout=10.0,
                )
                data = response.json()

            latest_version = data.get("tag_name", "").replace("v", "")
            update_available = latest_version != self.current_version

            self._update_info = UpdateInfo(
                current_version=self.current_version,
                latest_version=latest_version,
                update_available=update_available,
                release_notes=data.get("body", ""),
                download_url=data.get("html_url", ""),
                published_at=datetime.fromisoformat(
                    data.get("published_at", "").replace("Z", "+00:00")
                ),
            )

            self._last_check = datetime.now()
            return self._update_info

        except Exception as e:
            return None

    async def apply_update(self, version: str = None) -> bool:
        """Apply update."""
        if not self._update_info or not self._update_info.update_available:
            return False

        # Would implement actual update logic
        # For now, just return status
        return True

    def get_update_status(self) -> Dict[str, Any]:
        """Get update status."""
        return {
            "current_version": self.current_version,
            "update_available": self._update_info.update_available if self._update_info else False,
            "latest_version": self._update_info.latest_version if self._update_info else self.current_version,
            "last_check": self._last_check.isoformat() if self._last_check else None,
        }


# Global updater
_updater: Optional[AutoUpdater] = None


def get_updater() -> AutoUpdater:
    """Get global updater."""
    if _updater is None:
        _updater = AutoUpdater()
    return _updater


async def check_for_updates() -> Optional[UpdateInfo]:
    """Check for updates."""
    return await get_updater().check_update()


__all__ = [
    "UpdateInfo",
    "AutoUpdater",
    "get_updater",
    "check_for_updates",
]