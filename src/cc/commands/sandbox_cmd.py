"""Sandbox Command - Manage sandbox environments."""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ..utils.bash.sandbox import BashSandbox, SandboxConfig
from ..utils.log import get_logger

logger = get_logger(__name__)


class SandboxStatus(Enum):
    """Sandbox status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    RESTARTING = "restarting"


@dataclass
class SandboxInfo:
    """Sandbox information."""
    id: str
    status: SandboxStatus
    path: Path
    config: SandboxConfig
    created_at: float
    last_used: float
    usage_count: int = 0


class SandboxCommand:
    """Command to manage sandboxes."""

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or Path.home() / ".claude" / "sandboxes"
        self._sandboxes: Dict[str, SandboxInfo] = {}
        self._executors: Dict[str, BashSandbox] = {}
        self._current: Optional[str] = None

    async def create(
        self,
        name: str,
        config: Optional[SandboxConfig] = None
    ) -> SandboxInfo:
        """Create a new sandbox."""
        import time

        sandbox_id = f"sb_{name}_{int(time.time())}"
        sandbox_path = self.base_path / sandbox_id

        # Create directory
        sandbox_path.mkdir(parents=True, exist_ok=True)

        # Create executor
        use_config = config or SandboxConfig()
        executor = BashSandbox(use_config)
        self._executors[sandbox_id] = executor

        # Track info
        info = SandboxInfo(
            id=sandbox_id,
            status=SandboxStatus.ACTIVE,
            path=sandbox_path,
            config=use_config,
            created_at=time.time(),
            last_used=time.time(),
        )
        self._sandboxes[sandbox_id] = info

        logger.info(f"Created sandbox: {sandbox_id}")
        return info

    async def list(self) -> List[SandboxInfo]:
        """List all sandboxes."""
        return list(self._sandboxes.values())

    async def get(self, sandbox_id: str) -> Optional[SandboxInfo]:
        """Get sandbox by ID."""
        return self._sandboxes.get(sandbox_id)

    async def activate(self, sandbox_id: str) -> bool:
        """Activate sandbox."""
        info = self._sandboxes.get(sandbox_id)
        if not info:
            return False

        self._current = sandbox_id
        info.status = SandboxStatus.ACTIVE
        logger.info(f"Activated sandbox: {sandbox_id}")
        return True

    async def deactivate(self, sandbox_id: str) -> bool:
        """Deactivate sandbox."""
        info = self._sandboxes.get(sandbox_id)
        if not info:
            return False

        info.status = SandboxStatus.INACTIVE
        if self._current == sandbox_id:
            self._current = None

        logger.info(f"Deactivated sandbox: {sandbox_id}")
        return True

    async def run(
        self,
        sandbox_id: str,
        command: str
    ) -> Dict[str, Any]:
        """Run command in sandbox."""
        import time

        executor = self._executors.get(sandbox_id)
        if not executor:
            return {"error": "Sandbox not found"}

        info = self._sandboxes[sandbox_id]
        info.last_used = time.time()
        info.usage_count += 1

        try:
            result = await executor.execute(command)
            return result
        except Exception as e:
            logger.error(f"Sandbox execution error: {e}")
            return {"error": str(e)}

    async def destroy(self, sandbox_id: str) -> bool:
        """Destroy sandbox."""
        info = self._sandboxes.get(sandbox_id)
        if not info:
            return False

        # Remove directory
        if info.path.exists():
            import shutil
            shutil.rmtree(info.path)

        # Clean up tracking
        del self._sandboxes[sandbox_id]
        if sandbox_id in self._executors:
            del self._executors[sandbox_id]

        if self._current == sandbox_id:
            self._current = None

        logger.info(f"Destroyed sandbox: {sandbox_id}")
        return True

    async def clean_all(self) -> int:
        """Clean all inactive sandboxes."""
        to_remove = [
            id for id, info in self._sandboxes.items()
            if info.status == SandboxStatus.INACTIVE
        ]

        for id in to_remove:
            await self.destroy(id)

        return len(to_remove)

    def get_current(self) -> Optional[str]:
        """Get current active sandbox ID."""
        return self._current

    async def restart(self, sandbox_id: str) -> bool:
        """Restart sandbox."""
        info = self._sandboxes.get(sandbox_id)
        if not info:
            return False

        info.status = SandboxStatus.RESTARTING

        # Recreate executor
        config = info.config
        executor = SandboxExecutor(config)
        self._executors[sandbox_id] = executor

        info.status = SandboxStatus.ACTIVE
        logger.info(f"Restarted sandbox: {sandbox_id}")
        return True


__all__ = [
    "SandboxStatus",
    "SandboxInfo",
    "SandboxCommand",
]