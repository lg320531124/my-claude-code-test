"""Team Memory Sync - Sync memories with team."""

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


class TeamSyncStatus(Enum):
    """Team sync status."""
    SYNCED = "synced"
    PENDING = "pending"
    ERROR = "error"
    OFFLINE = "offline"
    UNAUTHORIZED = "unauthorized"


class MemoryVisibility(Enum):
    """Memory visibility."""
    PRIVATE = "private"
    TEAM = "team"
    PUBLIC = "public"


@dataclass
class TeamMemory:
    """Team memory."""
    id: str
    content: str
    type: str
    visibility: MemoryVisibility
    author: str
    team_id: str
    created_at: datetime
    updated_at: datetime
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TeamSyncConfig:
    """Team sync configuration."""
    enabled: bool = True
    auto_sync: bool = True
    sync_interval: float = 120.0
    team_id: Optional[str] = None
    visibility_default: MemoryVisibility = MemoryVisibility.TEAM
    max_memories: int = 500


@dataclass
class TeamSyncState:
    """Team sync state."""
    status: TeamSyncStatus
    team_id: Optional[str] = None
    last_sync: Optional[datetime] = None
    pending_count: int = 0
    synced_count: int = 0


class TeamMemorySync:
    """Sync memories with team."""

    def __init__(self, config: Optional[TeamSyncConfig] = None):
        self.config = config or TeamSyncConfig()
        self._state = TeamSyncState(status=TeamSyncStatus.OFFLINE)
        self._local_memories: Dict[str, TeamMemory] = {}
        self._remote_memories: Dict[str, TeamMemory] = {}
        self._pending_sync: List[str] = []

    async def connect(
        self,
        team_id: str
    ) -> bool:
        """Connect to team."""
        self._state.team_id = team_id

        # Simulate connection
        await asyncio.sleep(0.5)

        self._state.status = TeamSyncStatus.SYNCED
        self.config.team_id = team_id

        logger.info(f"Connected to team: {team_id}")
        return True

    async def disconnect(self) -> None:
        """Disconnect from team."""
        self._state.team_id = None
        self._state.status = TeamSyncStatus.OFFLINE

        logger.info("Disconnected from team")

    async def sync(self) -> Dict[str, Any]:
        """Sync memories."""
        if not self.config.enabled:
            return {"status": "disabled"}

        if self._state.status == TeamSyncStatus.OFFLINE:
            return {"status": "offline"}

        self._state.status = TeamSyncStatus.PENDING

        # Push local memories
        pushed = await self._push_memories()

        # Pull remote memories
        pulled = await self._pull_memories()

        self._state.last_sync = datetime.now()
        self._state.status = TeamSyncStatus.SYNCED
        self._state.synced_count = len(self._local_memories)

        return {
            "status": self._state.status.value,
            "pushed": pushed,
            "pulled": pulled,
            "total": len(self._local_memories),
        }

    async def _push_memories(self) -> int:
        """Push local memories."""
        count = 0

        for memory_id in self._pending_sync:
            memory = self._local_memories.get(memory_id)

            if memory and memory.visibility != MemoryVisibility.PRIVATE:
                # Simulate push
                self._remote_memories[memory_id] = memory
                count += 1

        self._pending_sync.clear()
        logger.info(f"Pushed {count} memories")
        return count

    async def _pull_memories(self) -> int:
        """Pull remote memories."""
        # Simulate pull
        count = 0

        logger.info(f"Pulled {count} memories")
        return count

    async def add_memory(
        self,
        content: str,
        type: str,
        visibility: Optional[MemoryVisibility] = None,
        tags: Optional[List[str]] = None
    ) -> TeamMemory:
        """Add memory."""
        import uuid

        memory_id = str(uuid.uuid4())[:8]
        now = datetime.now()

        use_visibility = visibility or self.config.visibility_default
        use_tags = tags or []

        memory = TeamMemory(
            id=memory_id,
            content=content,
            type=type,
            visibility=use_visibility,
            author="local",
            team_id=self._state.team_id or "",
            created_at=now,
            updated_at=now,
            tags=use_tags,
        )

        self._local_memories[memory_id] = memory
        self._pending_sync.append(memory_id)

        return memory

    async def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        visibility: Optional[MemoryVisibility] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[TeamMemory]:
        """Update memory."""
        memory = self._local_memories.get(memory_id)

        if not memory:
            return None

        if content:
            memory.content = content
        if visibility:
            memory.visibility = visibility
        if tags:
            memory.tags = tags

        memory.updated_at = datetime.now()
        self._pending_sync.append(memory_id)

        return memory

    async def delete_memory(
        self,
        memory_id: str
    ) -> bool:
        """Delete memory."""
        if memory_id in self._local_memories:
            del self._local_memories[memory_id]

            if memory_id in self._remote_memories:
                del self._remote_memories[memory_id]

            logger.info(f"Deleted memory: {memory_id}")
            return True

        return False

    async def get_memory(
        self,
        memory_id: str
    ) -> Optional[TeamMemory]:
        """Get memory."""
        # Check local first
        if memory_id in self._local_memories:
            return self._local_memories[memory_id]

        # Check remote
        return self._remote_memories.get(memory_id)

    async def get_memories(
        self,
        type: Optional[str] = None,
        visibility: Optional[MemoryVisibility] = None,
        author: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[TeamMemory]:
        """Get memories with filters."""
        memories = list(self._local_memories.values())

        # Apply filters
        if type:
            memories = [m for m in memories if m.type == type]

        if visibility:
            memories = [m for m in memories if m.visibility == visibility]

        if author:
            memories = [m for m in memories if m.author == author]

        if tags:
            memories = [
                m for m in memories
                if any(tag in m.tags for tag in tags)
            ]

        # Limit
        memories = memories[:self.config.max_memories]

        return memories

    async def search(
        self,
        query: str
    ) -> List[TeamMemory]:
        """Search memories."""
        results = []

        for memory in self._local_memories.values():
            if query.lower() in memory.content.lower():
                results.append(memory)
            elif any(query.lower() in tag.lower() for tag in memory.tags):
                results.append(memory)

        return results

    async def get_state(self) -> TeamSyncState:
        """Get sync state."""
        return self._state

    async def get_pending(self) -> List[TeamMemory]:
        """Get pending memories."""
        return [
            self._local_memories[id]
            for id in self._pending_sync
            if id in self._local_memories
        ]

    async def export(
        self,
        path: Path,
        visibility: Optional[MemoryVisibility] = None
    ) -> int:
        """Export memories."""
        memories = await self.get_memories(visibility=visibility)

        data = [
            {
                "id": m.id,
                "content": m.content,
                "type": m.type,
                "visibility": m.visibility.value,
                "tags": m.tags,
            }
            for m in memories
        ]

        path.write_text(json.dumps(data, indent=2))
        logger.info(f"Exported {len(memories)} memories")

        return len(memories)

    async def import_memories(
        self,
        path: Path
    ) -> int:
        """Import memories."""
        if not path.exists():
            return 0

        data = json.loads(path.read_text())
        imported = 0

        for item in data:
            await self.add_memory(
                content=item.get("content", ""),
                type=item.get("type", "note"),
                visibility=MemoryVisibility(item.get("visibility", "team")),
                tags=item.get("tags", []),
            )
            imported += 1

        logger.info(f"Imported {imported} memories")
        return imported


__all__ = [
    "TeamSyncStatus",
    "MemoryVisibility",
    "TeamMemory",
    "TeamSyncConfig",
    "TeamSyncState",
    "TeamMemorySync",
]