"""Settings Sync - Sync settings across devices."""

from __future__ import annotations
import asyncio
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pathlib import Path

from ...utils.log import get_logger

logger = get_logger(__name__)


class SyncStatus(Enum):
    """Sync status."""
    SYNCED = "synced"
    PENDING = "pending"
    ERROR = "error"
    CONFLICT = "conflict"
    OFFLINE = "offline"


class SyncDirection(Enum):
    """Sync direction."""
    PUSH = "push"
    PULL = "pull"
    BOTH = "both"


@dataclass
class SettingsChange:
    """Settings change record."""
    key: str
    old_value: Any
    new_value: Any
    timestamp: datetime
    source: str = "local"
    conflict: bool = False


@dataclass
class SyncConfig:
    """Sync configuration."""
    enabled: bool = True
    auto_sync: bool = True
    sync_interval: float = 60.0  # seconds
    conflict_strategy: str = "prefer_local"  # or "prefer_remote", "merge"
    sync_path: Optional[Path] = None


@dataclass
class SyncState:
    """Sync state."""
    status: SyncStatus
    last_sync: Optional[datetime] = None
    pending_changes: List[SettingsChange] = field(default_factory=list)
    conflicts: List[SettingsChange] = field(default_factory=list)


class SettingsSync:
    """Sync settings across devices."""

    def __init__(self, config: Optional[SyncConfig] = None):
        self.config = config or SyncConfig()
        self._state = SyncState(status=SyncStatus.OFFLINE)
        self._local_settings: Dict[str, Any] = {}
        self._remote_settings: Dict[str, Any] = {}
        self._change_history: List[SettingsChange] = []

    async def initialize(
        self,
        settings_path: Optional[Path] = None
    ) -> bool:
        """Initialize sync."""
        use_path = settings_path or self.config.sync_path

        if use_path and use_path.exists():
            try:
                self._local_settings = json.loads(use_path.read_text())
                self._state.status = SyncStatus.SYNCED
                return True
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
                self._state.status = SyncStatus.ERROR
                return False

        return True

    async def sync(
        self,
        direction: SyncDirection = SyncDirection.BOTH
    ) -> Dict[str, Any]:
        """Perform sync."""
        if not self.config.enabled:
            return {"status": "disabled"}

        self._state.status = SyncStatus.PENDING

        # Simulate sync
        await asyncio.sleep(0.5)

        # Push local changes
        if direction in [SyncDirection.PUSH, SyncDirection.BOTH]:
            await self._push_changes()

        # Pull remote changes
        if direction in [SyncDirection.PULL, SyncDirection.BOTH]:
            await self._pull_changes()

        # Check for conflicts
        conflicts = await self._detect_conflicts()

        if conflicts:
            self._state.conflicts = conflicts
            self._state.status = SyncStatus.CONFLICT

            # Resolve conflicts
            await self._resolve_conflicts()
        else:
            self._state.status = SyncStatus.SYNCED
            self._state.last_sync = datetime.now()

        return {
            "status": self._state.status.value,
            "changes": len(self._state.pending_changes),
            "conflicts": len(self._state.conflicts),
        }

    async def _push_changes(self) -> int:
        """Push local changes."""
        # Simulate push
        count = len(self._state.pending_changes)

        logger.info(f"Pushed {count} changes")
        return count

    async def _pull_changes(self) -> int:
        """Pull remote changes."""
        # Simulate pull
        count = 0

        logger.info(f"Pulled {count} changes")
        return count

    async def _detect_conflicts(self) -> List[SettingsChange]:
        """Detect conflicts."""
        conflicts = []

        # Check for key differences
        for key in self._local_settings:
            if key in self._remote_settings:
                local_val = self._local_settings[key]
                remote_val = self._remote_settings[key]

                if local_val != remote_val:
                    change = SettingsChange(
                        key=key,
                        old_value=remote_val,
                        new_value=local_val,
                        timestamp=datetime.now(),
                        conflict=True,
                    )
                    conflicts.append(change)

        return conflicts

    async def _resolve_conflicts(self) -> None:
        """Resolve conflicts."""
        for conflict in self._state.conflicts:
            if self.config.conflict_strategy == "prefer_local":
                self._remote_settings[conflict.key] = conflict.new_value
            elif self.config.conflict_strategy == "prefer_remote":
                self._local_settings[conflict.key] = conflict.old_value
            elif self.config.conflict_strategy == "merge":
                # Simple merge - prefer newest
                self._local_settings[conflict.key] = conflict.new_value

    async def get_setting(
        self,
        key: str
    ) -> Optional[Any]:
        """Get setting."""
        return self._local_settings.get(key)

    async def set_setting(
        self,
        key: str,
        value: Any
    ) -> None:
        """Set setting."""
        old_value = self._local_settings.get(key)

        self._local_settings[key] = value

        # Record change
        change = SettingsChange(
            key=key,
            old_value=old_value,
            new_value=value,
            timestamp=datetime.now(),
        )

        self._state.pending_changes.append(change)
        self._change_history.append(change)

    async def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings."""
        return self._local_settings.copy()

    async def apply_remote_settings(
        self,
        settings: Dict[str, Any]
    ) -> int:
        """Apply remote settings."""
        self._remote_settings = settings.copy()

        # Merge with local
        applied = 0

        for key, value in settings.items():
            if key not in self._local_settings:
                self._local_settings[key] = value
                applied += 1

        return applied

    async def get_state(self) -> SyncState:
        """Get sync state."""
        return self._state

    async def get_pending_changes(self) -> List[SettingsChange]:
        """Get pending changes."""
        return self._state.pending_changes

    async def get_history(self) -> List[SettingsChange]:
        """Get change history."""
        return self._change_history

    async def clear_pending(self) -> int:
        """Clear pending changes."""
        count = len(self._state.pending_changes)
        self._state.pending_changes.clear()
        return count

    async def export(
        self,
        path: Optional[Path] = None
    ) -> bool:
        """Export settings."""
        use_path = path or self.config.sync_path

        if use_path:
            use_path.parent.mkdir(parents=True, exist_ok=True)
            use_path.write_text(json.dumps(self._local_settings, indent=2))
            logger.info(f"Exported settings to {use_path}")
            return True

        return False

    async def import_settings(
        self,
        settings: Dict[str, Any]
    ) -> int:
        """Import settings."""
        imported = 0

        for key, value in settings.items():
            if key not in self._local_settings:
                self._local_settings[key] = value
                imported += 1

        return imported

    async def reset(self) -> None:
        """Reset settings."""
        self._local_settings.clear()
        self._remote_settings.clear()
        self._state.pending_changes.clear()
        self._state.conflicts.clear()
        self._change_history.clear()
        self._state.status = SyncStatus.OFFLINE


__all__ = [
    "SyncStatus",
    "SyncDirection",
    "SettingsChange",
    "SyncConfig",
    "SyncState",
    "SettingsSync",
]