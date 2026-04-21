"""State Manager - Manage application state."""

from __future__ import annotations
import asyncio
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ...utils.log import get_logger

logger = get_logger(__name__)


class StateScope(Enum):
    """State scope."""
    GLOBAL = "global"
    SESSION = "session"
    PROJECT = "project"
    USER = "user"


class StateType(Enum):
    """State types."""
    CONFIG = "config"
    CACHE = "cache"
    RUNTIME = "runtime"
    PERSISTENT = "persistent"


@dataclass
class StateEntry:
    """State entry."""
    key: str
    value: Any
    scope: StateScope
    type: StateType
    timestamp: float = 0.0
    ttl: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StateConfig:
    """State configuration."""
    persist: bool = True
    storage_path: Optional[Path] = None
    max_entries: int = 1000
    auto_cleanup: bool = True
    cleanup_interval: float = 300.0


class StateManager:
    """Manage application state."""

    def __init__(self, config: Optional[StateConfig] = None):
        self.config = config or StateConfig()
        self._state: Dict[str, StateEntry] = {}
        self._watchers: Dict[str, List[callable]] = {}
        self._last_cleanup: float = 0.0

    async def get(
        self,
        key: str,
        default: Any = None
    ) -> Any:
        """Get state value."""
        if key not in self._state:
            return default

        entry = self._state[key]

        # Check TTL
        if entry.ttl and entry.timestamp + entry.ttl < asyncio.get_event_loop().time():
            del self._state[key]
            return default

        return entry.value

    async def set(
        self,
        key: str,
        value: Any,
        scope: StateScope = StateScope.GLOBAL,
        type: StateType = StateType.RUNTIME,
        ttl: Optional[float] = None
    ) -> bool:
        """Set state value."""
        import time

        # Check limit
        if len(self._state) >= self.config.max_entries and key not in self._state:
            return False

        old_value = await self.get(key)

        entry = StateEntry(
            key=key,
            value=value,
            scope=scope,
            type=type,
            timestamp=time.time(),
            ttl=ttl,
        )

        self._state[key] = entry

        # Notify watchers
        await self._notify_watchers(key, old_value, value)

        # Persist if needed
        if self.config.persist and type == StateType.PERSISTENT:
            await self._persist_state(key, entry)

        return True

    async def _notify_watchers(
        self,
        key: str,
        old_value: Any,
        new_value: Any
    ) -> None:
        """Notify watchers of state change."""
        watchers = self._watchers.get(key, [])

        for watcher in watchers:
            try:
                if asyncio.iscoroutinefunction(watcher):
                    await watcher(key, old_value, new_value)
                else:
                    watcher(key, old_value, new_value)
            except Exception as e:
                logger.error(f"Watcher error: {e}")

    async def _persist_state(
        self,
        key: str,
        entry: StateEntry
    ) -> None:
        """Persist state to file."""
        if not self.config.storage_path:
            return

        path = self.config.storage_path

        try:
            # Load existing
            data = {}
            if path.exists():
                data = json.loads(path.read_text())

            # Update
            data[key] = {
                "value": entry.value,
                "scope": entry.scope.value,
                "type": entry.type.value,
                "timestamp": entry.timestamp,
                "ttl": entry.ttl,
            }

            # Save
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Persist error: {e}")

    async def _load_state(self) -> None:
        """Load persisted state."""
        if not self.config.storage_path:
            return

        path = self.config.storage_path

        if not path.exists():
            return

        try:
            data = json.loads(path.read_text())

            import time

            for key, entry_data in data.items():
                entry = StateEntry(
                    key=key,
                    value=entry_data["value"],
                    scope=StateScope(entry_data["scope"]),
                    type=StateType(entry_data["type"]),
                    timestamp=entry_data.get("timestamp", time.time()),
                    ttl=entry_data.get("ttl"),
                )

                self._state[key] = entry

            logger.info(f"Loaded {len(data)} state entries")
        except Exception as e:
            logger.error(f"Load error: {e}")

    async def delete(
        self,
        key: str
    ) -> bool:
        """Delete state entry."""
        if key not in self._state:
            return False

        old_value = self._state[key].value
        del self._state[key]

        # Notify watchers
        await self._notify_watchers(key, old_value, None)

        return True

    async def exists(
        self,
        key: str
    ) -> bool:
        """Check if key exists."""
        return key in self._state

    async def clear(
        self,
        scope: Optional[StateScope] = None
    ) -> int:
        """Clear state."""
        if scope:
            keys = [
                k for k, e in self._state.items()
                if e.scope == scope
            ]
            count = len(keys)

            for key in keys:
                del self._state[key]

        else:
            count = len(self._state)
            self._state.clear()

        return count

    async def get_all(
        self,
        scope: Optional[StateScope] = None
    ) -> Dict[str, Any]:
        """Get all state."""
        if scope:
            return {
                k: e.value
                for k, e in self._state.items()
                if e.scope == scope
            }

        return {k: e.value for k, e in self._state.items()}

    async def watch(
        self,
        key: str,
        callback: callable
    ) -> None:
        """Watch state key."""
        if key not in self._watchers:
            self._watchers[key] = []

        self._watchers[key].append(callback)

    async def unwatch(
        self,
        key: str,
        callback: callable
    ) -> bool:
        """Unwatch state key."""
        if key not in self._watchers:
            return False

        try:
            self._watchers[key].remove(callback)
            return True
        except ValueError:
            return False

    async def cleanup(self) -> int:
        """Cleanup expired entries."""
        import time

        now = time.time()
        count = 0

        expired_keys = [
            k for k, e in self._state.items()
            if e.ttl and e.timestamp + e.ttl < now
        ]

        for key in expired_keys:
            del self._state[key]
            count += 1

        self._last_cleanup = now
        return count

    async def get_stats(self) -> Dict[str, Any]:
        """Get state statistics."""
        by_scope: Dict[str, int] = {}
        by_type: Dict[str, int] = {}

        for entry in self._state.values():
            by_scope[entry.scope.value] = by_scope.get(entry.scope.value, 0) + 1
            by_type[entry.type.value] = by_type.get(entry.type.value, 0) + 1

        return {
            "total_entries": len(self._state),
            "by_scope": by_scope,
            "by_type": by_type,
            "watchers": len(self._watchers),
        }

    async def export(self) -> str:
        """Export state."""
        data = {
            k: {
                "value": e.value,
                "scope": e.scope.value,
            }
            for k, e in self._state.items()
        }

        return json.dumps(data, indent=2)


__all__ = [
    "StateScope",
    "StateType",
    "StateEntry",
    "StateConfig",
    "StateManager",
]