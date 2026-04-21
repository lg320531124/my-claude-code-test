"""Workspace Manager - Manage workspace/projects."""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime

from ...utils.log import get_logger

logger = get_logger(__name__)


class WorkspaceType(Enum):
    """Workspace types."""
    PROJECT = "project"
    SESSION = "session"
    TEMP = "temp"
    CLONE = "clone"


@dataclass
class WorkspaceInfo:
    """Workspace information."""
    id: str
    name: str
    path: Path
    type: WorkspaceType
    created: datetime
    last_accessed: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkspaceConfig:
    """Workspace configuration."""
    root_path: Path = Path(".")
    max_workspaces: int = 10
    auto_cleanup: bool = True
    cleanup_age_days: int = 7
    persist_info: bool = True


class WorkspaceManager:
    """Manage workspaces."""

    def __init__(self, config: Optional[WorkspaceConfig] = None):
        self.config = config or WorkspaceConfig()
        self._workspaces: Dict[str, WorkspaceInfo] = {}
        self._current: Optional[str] = None

    async def create(
        self,
        name: str,
        type: WorkspaceType = WorkspaceType.PROJECT,
        path: Optional[Path] = None
    ) -> WorkspaceInfo:
        """Create workspace."""
        import uuid

        # Generate ID
        workspace_id = str(uuid.uuid4())[:8]

        # Determine path
        use_path = path or self.config.root_path / name

        # Create workspace info
        workspace = WorkspaceInfo(
            id=workspace_id,
            name=name,
            path=use_path,
            type=type,
            created=datetime.now(),
            last_accessed=datetime.now(),
        )

        self._workspaces[workspace_id] = workspace

        # Create directory
        try:
            use_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created workspace: {name}")
        except Exception as e:
            logger.error(f"Failed to create workspace: {e}")

        return workspace

    async def get(
        self,
        workspace_id: str
    ) -> Optional[WorkspaceInfo]:
        """Get workspace."""
        return self._workspaces.get(workspace_id)

    async def get_by_name(
        self,
        name: str
    ) -> Optional[WorkspaceInfo]:
        """Get workspace by name."""
        for workspace in self._workspaces.values():
            if workspace.name == name:
                return workspace

        return None

    async def set_current(
        self,
        workspace_id: str
    ) -> bool:
        """Set current workspace."""
        if workspace_id not in self._workspaces:
            return False

        self._current = workspace_id
        self._workspaces[workspace_id].last_accessed = datetime.now()

        return True

    async def get_current(self) -> Optional[WorkspaceInfo]:
        """Get current workspace."""
        if not self._current:
            return None

        return self._workspaces.get(self._current)

    async def list_workspaces(
        self,
        type: Optional[WorkspaceType] = None
    ) -> List[WorkspaceInfo]:
        """List workspaces."""
        if type:
            return [
                w for w in self._workspaces.values()
                if w.type == type
            ]

        return list(self._workspaces.values())

    async def delete(
        self,
        workspace_id: str
    ) -> bool:
        """Delete workspace."""
        if workspace_id not in self._workspaces:
            return False

        workspace = self._workspaces[workspace_id]

        # Remove directory for temp workspaces
        if workspace.type == WorkspaceType.TEMP:
            try:
                import shutil
                shutil.rmtree(workspace.path)
            except Exception as e:
                logger.error(f"Failed to remove workspace: {e}")

        del self._workspaces[workspace_id]

        if self._current == workspace_id:
            self._current = None

        return True

    async def cleanup(self) -> int:
        """Cleanup old workspaces."""
        if not self.config.auto_cleanup:
            return 0

        cutoff = datetime.now() - datetime.timedelta(days=self.config.cleanup_age_days)

        old_workspaces = [
            w.id for w in self._workspaces.values()
            if w.last_accessed < cutoff and w.type == WorkspaceType.TEMP
        ]

        count = 0

        for workspace_id in old_workspaces:
            if await self.delete(workspace_id):
                count += 1

        return count

    async def exists(
        self,
        path: Path
    ) -> bool:
        """Check if workspace exists at path."""
        for workspace in self._workspaces.values():
            if workspace.path == path:
                return True

        return False

    async def save_file(
        self,
        workspace_id: str,
        file_path: str,
        content: str
    ) -> bool:
        """Save file in workspace."""
        workspace = await self.get(workspace_id)

        if not workspace:
            return False

        full_path = workspace.path / file_path

        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
            return True
        except Exception as e:
            logger.error(f"Failed to save file: {e}")
            return False

    async def read_file(
        self,
        workspace_id: str,
        file_path: str
    ) -> Optional[str]:
        """Read file from workspace."""
        workspace = await self.get(workspace_id)

        if not workspace:
            return None

        full_path = workspace.path / file_path

        if not full_path.exists():
            return None

        try:
            return full_path.read_text()
        except Exception as e:
            logger.error(f"Failed to read file: {e}")
            return None

    async def list_files(
        self,
        workspace_id: str,
        pattern: str = "*"
    ) -> List[str]:
        """List files in workspace."""
        workspace = await self.get(workspace_id)

        if not workspace:
            return []

        try:
            files = list(workspace.path.glob(pattern))
            return [str(f.relative_to(workspace.path)) for f in files]
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return []

    async def get_stats(self) -> Dict[str, Any]:
        """Get workspace statistics."""
        by_type: Dict[str, int] = {}

        for workspace in self._workspaces.values():
            key = workspace.type.value
            by_type[key] = by_type.get(key, 0) + 1

        return {
            "total_workspaces": len(self._workspaces),
            "by_type": by_type,
            "current": self._current,
        }


__all__ = [
    "WorkspaceType",
    "WorkspaceInfo",
    "WorkspaceConfig",
    "WorkspaceManager",
]