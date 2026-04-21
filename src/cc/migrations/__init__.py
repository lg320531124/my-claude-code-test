"""Migrations Module - Database and schema migrations.

Provides migration management for:
- Schema versioning
- Migration execution
- Rollback support
- Migration tracking
"""

from __future__ import annotations
import asyncio
import json
from pathlib import Path
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class MigrationStatus(Enum):
    """Migration status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class Migration:
    """Migration definition."""
    id: str
    name: str
    version: str
    description: str
    up_script: str  # Migration script
    down_script: str  # Rollback script
    dependencies: List[str] = field(default_factory=list)
    status: MigrationStatus = MigrationStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    executed_at: Optional[datetime] = None
    error: Optional[str] = None


@dataclass
class MigrationRecord:
    """Migration execution record."""
    migration_id: str
    status: MigrationStatus
    executed_at: datetime
    duration_ms: int
    error: Optional[str] = None


class MigrationManager:
    """Migration manager."""

    def __init__(self, migrations_dir: Path = None, db_path: Path = None):
        self.migrations_dir = migrations_dir or Path("migrations")
        self.db_path = db_path or Path.home() / ".claude" / "migrations.json"
        self._migrations: Dict[str, Migration] = {}
        self._records: List[MigrationRecord] = []
        self._current_version: str = "0.0.0"
        self._lock = asyncio.Lock()

        # Ensure directories exist
        self.migrations_dir.mkdir(parents=True, exist_ok=True)

    async def load_migrations(self) -> None:
        """Load migrations from directory."""
        import aiofiles

        # Load existing records
        if self.db_path.exists():
            async with aiofiles.open(self.db_path, "r") as f:
                content = await f.read()
            data = json.loads(content)
            self._current_version = data.get("current_version", "0.0.0")
            self._records = [
                MigrationRecord(
                    migration_id=r["migration_id"],
                    status=MigrationStatus(r["status"]),
                    executed_at=datetime.fromisoformat(r["executed_at"]),
                    duration_ms=r["duration_ms"],
                    error=r.get("error"),
                )
                for r in data.get("records", [])
            ]

        # Load migration files
        for filepath in self.migrations_dir.glob("*.json"):
            async with aiofiles.open(filepath, "r") as f:
                content = await f.read()
            data = json.loads(content)

            migration = Migration(
                id=data["id"],
                name=data["name"],
                version=data["version"],
                description=data.get("description", ""),
                up_script=data.get("up", ""),
                down_script=data.get("down", ""),
                dependencies=data.get("dependencies", []),
            )
            self._migrations[migration.id] = migration

    async def create_migration(
        self,
        name: str,
        description: str,
        up_script: str,
        down_script: str,
        dependencies: List[str] = None,
    ) -> Migration:
        """Create new migration."""
        import aiofiles

        # Generate ID and version
        version_parts = self._current_version.split(".")
        new_version = f"{version_parts[0]}.{version_parts[1]}.{int(version_parts[2]) + 1}"

        migration_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{name}"

        migration = Migration(
            id=migration_id,
            name=name,
            version=new_version,
            description=description,
            up_script=up_script,
            down_script=down_script,
            dependencies=dependencies or [],
        )

        self._migrations[migration_id] = migration

        # Save to file
        filepath = self.migrations_dir / f"{migration_id}.json"
        data = {
            "id": migration_id,
            "name": name,
            "version": new_version,
            "description": description,
            "up": up_script,
            "down": down_script,
            "dependencies": dependencies or [],
            "created_at": migration.created_at.isoformat(),
        }

        async with aiofiles.open(filepath, "w") as f:
            await f.write(json.dumps(data, indent=2))

        return migration

    async def run_migration(self, migration_id: str, executor: Callable = None) -> bool:
        """Run single migration."""
        async with self._lock:
            migration = self._migrations.get(migration_id)
            if not migration:
                return False

            # Check dependencies
            for dep_id in migration.dependencies:
                dep_record = self._get_record(dep_id)
                if not dep_record or dep_record.status != MigrationStatus.COMPLETED:
                    raise ValueError(f"Dependency not completed: {dep_id}")

            start_time = datetime.now()
            migration.status = MigrationStatus.RUNNING

            try:
                # Execute up script
                if executor:
                    if asyncio.iscoroutinefunction(executor):
                        await executor(migration.up_script)
                    else:
                        executor(migration.up_script)

                migration.status = MigrationStatus.COMPLETED
                migration.executed_at = datetime.now()
                self._current_version = migration.version

                # Record execution
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                record = MigrationRecord(
                    migration_id=migration_id,
                    status=MigrationStatus.COMPLETED,
                    executed_at=datetime.now(),
                    duration_ms=duration_ms,
                )
                self._records.append(record)

                await self._save_records()
                return True

            except Exception as e:
                migration.status = MigrationStatus.FAILED
                migration.error = str(e)

                record = MigrationRecord(
                    migration_id=migration_id,
                    status=MigrationStatus.FAILED,
                    executed_at=datetime.now(),
                    duration_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                    error=str(e),
                )
                self._records.append(record)

                await self._save_records()
                return False

    async def rollback_migration(self, migration_id: str, executor: Callable = None) -> bool:
        """Rollback migration."""
        async with self._lock:
            migration = self._migrations.get(migration_id)
            if not migration:
                return False

            record = self._get_record(migration_id)
            if not record or record.status != MigrationStatus.COMPLETED:
                return False

            start_time = datetime.now()

            try:
                # Execute down script
                if executor:
                    if asyncio.iscoroutinefunction(executor):
                        await executor(migration.down_script)
                    else:
                        executor(migration.down_script)

                migration.status = MigrationStatus.ROLLED_BACK

                # Update record
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                rollback_record = MigrationRecord(
                    migration_id=migration_id,
                    status=MigrationStatus.ROLLED_BACK,
                    executed_at=datetime.now(),
                    duration_ms=duration_ms,
                )
                self._records.append(rollback_record)

                await self._save_records()
                return True

            except Exception as e:
                migration.error = str(e)
                return False

    async def run_all_pending(self, executor: Callable = None) -> Dict[str, bool]:
        """Run all pending migrations."""
        results = {}
        pending = self.get_pending_migrations()

        for migration in pending:
            success = await self.run_migration(migration.id, executor)
            results[migration.id] = success

        return results

    def get_pending_migrations(self) -> List[Migration]:
        """Get pending migrations."""
        pending = []
        for migration in self._migrations.values():
            if migration.status == MigrationStatus.PENDING:
                # Check if already executed
                record = self._get_record(migration.id)
                if not record or record.status not in (MigrationStatus.COMPLETED, MigrationStatus.ROLLED_BACK):
                    pending.append(migration)
        return sorted(pending, key=lambda m: m.version)

    def get_completed_migrations(self) -> List[Migration]:
        """Get completed migrations."""
        completed = []
        for migration in self._migrations.values():
            record = self._get_record(migration.id)
            if record and record.status == MigrationStatus.COMPLETED:
                completed.append(migration)
        return completed

    def get_current_version(self) -> str:
        """Get current schema version."""
        return self._current_version

    def _get_record(self, migration_id: str) -> Optional[MigrationRecord]:
        """Get latest record for migration."""
        for record in reversed(self._records):
            if record.migration_id == migration_id:
                return record
        return None

    async def _save_records(self) -> None:
        """Save records to file."""
        import aiofiles

        data = {
            "current_version": self._current_version,
            "records": [
                {
                    "migration_id": r.migration_id,
                    "status": r.status.value,
                    "executed_at": r.executed_at.isoformat(),
                    "duration_ms": r.duration_ms,
                    "error": r.error,
                }
                for r in self._records
            ],
        }

        async with aiofiles.open(self.db_path, "w") as f:
            await f.write(json.dumps(data, indent=2))


# Global manager
_manager: Optional[MigrationManager] = None


def get_migration_manager() -> MigrationManager:
    """Get global migration manager."""
    if _manager is None:
        _manager = MigrationManager()
    return _manager


async def run_migrations() -> Dict[str, bool]:
    """Run pending migrations."""
    manager = get_migration_manager()
    await manager.load_migrations()
    return await manager.run_all_pending()


__all__ = [
    "MigrationStatus",
    "Migration",
    "MigrationRecord",
    "MigrationManager",
    "get_migration_manager",
    "run_migrations",
]