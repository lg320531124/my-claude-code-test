"""Team Memory Sync - Synchronize team memories."""

from __future__ import annotations
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SyncStatus(Enum):
    """Sync status."""
    PENDING = "pending"
    SYNCING = "syncing"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"


@dataclass
class TeamMemory:
    """Team memory entry."""
    id: str
    team_id: str
    user_id: str
    content: str
    type: str = "observation"  # observation, decision, feedback
    created_at: datetime = None
    updated_at: datetime = None
    synced: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SyncBatch:
    """Batch of memories to sync."""
    team_id: str
    memories: List[TeamMemory] = field(default_factory=list)
    status: SyncStatus = SyncStatus.PENDING
    created_at: datetime = None
    completed_at: datetime = None


class TeamMemorySync:
    """Team memory synchronization service."""
    
    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path.home() / ".claude-code-py" / "team"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._pending: Dict[str, TeamMemory] = {}
        self._batches: Dict[str, SyncBatch] = {}
    
    def add_memory(self, memory: TeamMemory) -> None:
        """Add memory to pending sync."""
        self._pending[memory.id] = memory
    
    async def sync_batch(self, team_id: str) -> SyncBatch:
        """Create and process sync batch."""
        # Collect pending memories for team
        team_memories = [
            m for m in self._pending.values()
            if m.team_id == team_id
        ]
        
        batch = SyncBatch(
            team_id=team_id,
            memories=team_memories,
            status=SyncStatus.SYNCING,
            created_at=datetime.now(),
        )
        
        # Simulate sync (would call API in real implementation)
        await asyncio.sleep(0.5)
        
        batch.status = SyncStatus.COMPLETED
        batch.completed_at = datetime.now()
        
        # Clear pending
        for m in team_memories:
            m.synced = True
            if m.id in self._pending:
                del self._pending[m.id]
        
        # Save batch
        self._save_batch(batch)
        
        return batch
    
    def _save_batch(self, batch: SyncBatch) -> None:
        """Save batch to storage."""
        batch_file = self.storage_path / f"batch_{batch.team_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        data = {
            "team_id": batch.team_id,
            "status": batch.status.value,
            "memories": [
                {
                    "id": m.id,
                    "content": m.content,
                    "type": m.type,
                }
                for m in batch.memories
            ],
            "created_at": str(batch.created_at),
            "completed_at": str(batch.completed_at),
        }
        
        batch_file.write_text(json.dumps(data, indent=2))
    
    def get_pending_count(self, team_id: str = None) -> int:
        """Get count of pending memories."""
        if team_id:
            return sum(1 for m in self._pending.values() if m.team_id == team_id)
        return len(self._pending)
    
    def get_team_memories(self, team_id: str) -> List[TeamMemory]:
        """Get all memories for team."""
        # Load from storage
        memories = []
        
        for batch_file in self.storage_path.glob(f"batch_{team_id}_*.json"):
            try:
                data = json.loads(batch_file.read_text())
                for m in data.get("memories", []):
                    memories.append(TeamMemory(
                        id=m["id"],
                        team_id=team_id,
                        user_id="",
                        content=m["content"],
                        type=m["type"],
                    ))
            except:
                pass
        
        return memories


__all__ = [
    "SyncStatus",
    "TeamMemory",
    "SyncBatch",
    "TeamMemorySync",
]
