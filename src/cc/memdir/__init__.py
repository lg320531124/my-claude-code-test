"""MemDir Module - Team memory directory service.

Provides team memory management:
- Shared memory storage
- Team collaboration
- Memory sync
- Memory search
"""

from __future__ import annotations
import asyncio
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class MemoryType(Enum):
    """Memory types."""
    DECISION = "decision"
    LEARNING = "learning"
    PATTERN = "pattern"
    FEEDBACK = "feedback"
    CONTEXT = "context"
    REFERENCE = "reference"


@dataclass
class MemoryEntry:
    """Memory entry."""
    id: str
    type: MemoryType
    content: str
    author: str
    project: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    access_count: int = 0
    expires_at: Optional[datetime] = None


@dataclass
class TeamMember:
    """Team member."""
    id: str
    name: str
    email: str
    role: str  # admin, member, viewer
    joined_at: datetime = field(default_factory=datetime.now)


@dataclass
class Team:
    """Team definition."""
    id: str
    name: str
    members: List[TeamMember] = field(default_factory=list)
    shared_memories: List[str] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)


class MemDirService:
    """Team memory directory service."""

    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path.home() / ".claude" / "memdir"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self._memories: Dict[str, MemoryEntry] = {}
        self._teams: Dict[str, Team] = {}
        self._current_team: Optional[str] = None
        self._lock = asyncio.Lock()

    async def create_memory(
        self,
        type: MemoryType,
        content: str,
        author: str,
        project: str,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
        expires_days: int = None,
    ) -> MemoryEntry:
        """Create memory entry."""
        async with self._lock:
            # Generate ID
            hash_input = f"{type.value}:{content}:{datetime.now().isoformat()}"
            memory_id = hashlib.md5(hash_input.encode()).hexdigest()[:12]

            expires_at = None
            if expires_days:
                expires_at = datetime.now() + asyncio.timedelta(days=expires_days)

            memory = MemoryEntry(
                id=memory_id,
                type=type,
                content=content,
                author=author,
                project=project,
                tags=tags or [],
                metadata=metadata or {},
                expires_at=expires_at,
            )

            self._memories[memory_id] = memory
            await self._save_memory(memory)

            # Add to current team if set
            if self._current_team and self._current_team in self._teams:
                self._teams[self._current_team].shared_memories.append(memory_id)
                await self._save_team(self._teams[self._current_team])

            return memory

    async def get_memory(self, memory_id: str) -> Optional[MemoryEntry]:
        """Get memory by ID."""
        memory = self._memories.get(memory_id)
        if memory:
            memory.access_count += 1
            memory.updated_at = datetime.now()
        return memory

    async def update_memory(
        self,
        memory_id: str,
        content: str = None,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> Optional[MemoryEntry]:
        """Update memory."""
        async with self._lock:
            memory = self._memories.get(memory_id)
            if not memory:
                return None

            if content:
                memory.content = content
            if tags:
                memory.tags = tags
            if metadata:
                memory.metadata.update(metadata)

            memory.updated_at = datetime.now()
            await self._save_memory(memory)

            return memory

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete memory."""
        async with self._lock:
            if memory_id not in self._memories:
                return False

            self._memories.pop(memory_id)

            # Remove from teams
            for team in self._teams.values():
                if memory_id in team.shared_memories:
                    team.shared_memories.remove(memory_id)
                    await self._save_team(team)

            # Delete file
            filepath = self.storage_path / "memories" / f"{memory_id}.json"
            if filepath.exists():
                filepath.unlink()

            return True

    async def search_memories(
        self,
        query: str,
        type: MemoryType = None,
        project: str = None,
        tags: List[str] = None,
        author: str = None,
    ) -> List[MemoryEntry]:
        """Search memories."""
        results = []
        query_lower = query.lower()

        for memory in self._memories.values():
            # Check filters
            if type and memory.type != type:
                continue
            if project and memory.project != project:
                continue
            if author and memory.author != author:
                continue
            if tags and not all(t in memory.tags for t in tags):
                continue

            # Check expiration
            if memory.expires_at and memory.expires_at < datetime.now():
                continue

            # Check content match
            if query_lower in memory.content.lower() or query_lower in " ".join(memory.tags).lower():
                results.append(memory)

        # Sort by access count
        results.sort(key=lambda m: m.access_count, reverse=True)
        return results

    async def create_team(
        self,
        name: str,
        members: List[Dict[str, str]] = None,
    ) -> Team:
        """Create team."""
        async with self._lock:
            team_id = hashlib.md5(f"{name}:{datetime.now().isoformat()}".encode()).hexdigest()[:12]

            team_members = []
            for m in members or []:
                member = TeamMember(
                    id=m.get("id", ""),
                    name=m.get("name", ""),
                    email=m.get("email", ""),
                    role=m.get("role", "member"),
                )
                team_members.append(member)

            team = Team(
                id=team_id,
                name=name,
                members=team_members,
            )

            self._teams[team_id] = team
            await self._save_team(team)

            return team

    async def get_team(self, team_id: str) -> Optional[Team]:
        """Get team."""
        return self._teams.get(team_id)

    async def join_team(self, team_id: str, member: Dict[str, str]) -> bool:
        """Join team."""
        async with self._lock:
            team = self._teams.get(team_id)
            if not team:
                return False

            new_member = TeamMember(
                id=member.get("id", ""),
                name=member.get("name", ""),
                email=member.get("email", ""),
                role=member.get("role", "member"),
            )

            team.members.append(new_member)
            await self._save_team(team)

            return True

    async def set_current_team(self, team_id: str) -> bool:
        """Set current team context."""
        if team_id in self._teams:
            self._current_team = team_id
            return True
        return False

    async def share_memory(self, memory_id: str, team_id: str) -> bool:
        """Share memory with team."""
        async with self._lock:
            team = self._teams.get(team_id)
            if not team:
                return False

            if memory_id not in self._memories:
                return False

            if memory_id not in team.shared_memories:
                team.shared_memories.append(memory_id)
                await self._save_team(team)

            return True

    async def get_team_memories(self, team_id: str) -> List[MemoryEntry]:
        """Get all memories shared with team."""
        team = self._teams.get(team_id)
        if not team:
            return []

        memories = []
        for memory_id in team.shared_memories:
            memory = self._memories.get(memory_id)
            if memory:
                memories.append(memory)

        return memories

    async def sync_memories(self) -> Dict[str, Any]:
        """Sync memories (placeholder for remote sync)."""
        # This would sync with remote team memory service
        # For now, just return local stats
        return {
            "memories_count": len(self._memories),
            "teams_count": len(self._teams),
            "last_sync": datetime.now().isoformat(),
        }

    async def cleanup_expired(self) -> int:
        """Remove expired memories."""
        async with self._lock:
            expired_ids = []
            for memory_id, memory in self._memories.items():
                if memory.expires_at and memory.expires_at < datetime.now():
                    expired_ids.append(memory_id)

            for memory_id in expired_ids:
                await self.delete_memory(memory_id)

            return len(expired_ids)

    async def _save_memory(self, memory: MemoryEntry) -> None:
        """Save memory to file."""
        import aiofiles

        memories_dir = self.storage_path / "memories"
        memories_dir.mkdir(exist_ok=True)

        filepath = memories_dir / f"{memory.id}.json"
        data = {
            "id": memory.id,
            "type": memory.type.value,
            "content": memory.content,
            "author": memory.author,
            "project": memory.project,
            "createdAt": memory.created_at.isoformat(),
            "updatedAt": memory.updated_at.isoformat(),
            "tags": memory.tags,
            "metadata": memory.metadata,
            "accessCount": memory.access_count,
            "expiresAt": memory.expires_at.isoformat() if memory.expires_at else None,
        }

        async with aiofiles.open(filepath, "w") as f:
            await f.write(json.dumps(data, indent=2))

    async def _save_team(self, team: Team) -> None:
        """Save team to file."""
        import aiofiles

        teams_dir = self.storage_path / "teams"
        teams_dir.mkdir(exist_ok=True)

        filepath = teams_dir / f"{team.id}.json"
        data = {
            "id": team.id,
            "name": team.name,
            "members": [
                {
                    "id": m.id,
                    "name": m.name,
                    "email": m.email,
                    "role": m.role,
                }
                for m in team.members
            ],
            "sharedMemories": team.shared_memories,
            "settings": team.settings,
        }

        async with aiofiles.open(filepath, "w") as f:
            await f.write(json.dumps(data, indent=2))


# Global service
_service: Optional[MemDirService] = None


def get_memdir_service() -> MemDirService:
    """Get global service."""
    if _service is None:
        _service = MemDirService()
    return _service


async def create_memory(content: str, type: str = "learning", project: str = "") -> MemoryEntry:
    """Create memory."""
    service = get_memdir_service()
    return await service.create_memory(
        type=MemoryType(type),
        content=content,
        author="system",
        project=project,
    )


__all__ = [
    "MemoryType",
    "MemoryEntry",
    "TeamMember",
    "Team",
    "MemDirService",
    "get_memdir_service",
    "create_memory",
]