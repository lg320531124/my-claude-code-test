"""Storage Service - Persistent data storage."""

from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class StorageConfig(BaseModel):
    """Storage configuration."""
    storage_path: str = Field(default="~/.claude/storage", description="Storage directory")
    use_sqlite: bool = Field(default=True, description="Use SQLite for structured data")
    sqlite_db: str = Field(default="claude_data.db", description="SQLite database name")


class StorageService:
    """Unified storage service."""

    def __init__(self, config: Optional[StorageConfig] = None):
        self.config = config or StorageConfig()
        self._storage_dir = Path(self.config.storage_path).expanduser()
        self._storage_dir.mkdir(parents=True, exist_ok=True)

        self._db: Optional[sqlite3.Connection] = None
        if self.config.use_sqlite:
            self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database."""
        db_path = self._storage_dir / self.config.sqlite_db
        self._db = sqlite3.connect(str(db_path))
        self._db.row_factory = sqlite3.Row

        # Create tables
        self._db.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cwd TEXT,
                messages TEXT,
                metadata TEXT
            );

            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                type TEXT,
                description TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                description TEXT,
                content TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                scope TEXT DEFAULT 'user',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                event_data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self._db.commit()

    # Sessions
    def save_session(self, session_id: str, data: Dict[str, Any]) -> None:
        """Save session data."""
        if not self._db:
            # Fallback to file
            path = self._storage_dir / "sessions" / f"{session_id}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data))
            return

        self._db.execute(
            """INSERT OR REPLACE INTO sessions
               (id, cwd, messages, metadata, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                session_id,
                data.get("cwd", ""),
                json.dumps(data.get("messages", [])),
                json.dumps(data.get("metadata", {})),
                datetime.now().isoformat(),
            ),
        )
        self._db.commit()

    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session data."""
        if not self._db:
            path = self._storage_dir / "sessions" / f"{session_id}.json"
            if path.exists():
                return json.loads(path.read_text())
            return None

        row = self._db.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()

        if row:
            return {
                "id": row["id"],
                "cwd": row["cwd"],
                "messages": json.loads(row["messages"] or "[]"),
                "metadata": json.loads(row["metadata"] or "{}"),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        return None

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions."""
        if not self._db:
            sessions_dir = self._storage_dir / "sessions"
            if not sessions_dir.exists():
                return []
            return [
                {"id": f.stem, "path": str(f)}
                for f in sessions_dir.glob("*.json")
            ]

        rows = self._db.execute(
            "SELECT id, created_at, updated_at, cwd FROM sessions ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]

    # Settings
    def get_setting(self, key: str, scope: str = "user") -> Optional[Any]:
        """Get setting value."""
        if not self._db:
            path = self._storage_dir / "settings" / f"{scope}_{key}.json"
            if path.exists():
                return json.loads(path.read_text())
            return None

        row = self._db.execute(
            "SELECT value FROM settings WHERE key = ? AND scope = ?",
            (key, scope),
        ).fetchone()
        if row:
            return json.loads(row["value"])
        return None

    def set_setting(self, key: str, value: Any, scope: str = "user") -> None:
        """Set setting value."""
        if not self._db:
            path = self._storage_dir / "settings" / f"{scope}_{key}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value))
            return

        self._db.execute(
            """INSERT OR REPLACE INTO settings (key, value, scope, updated_at)
               VALUES (?, ?, ?, ?)""",
            (key, json.dumps(value), scope, datetime.now().isoformat()),
        )
        self._db.commit()

    # Memories
    def save_memory(self, name: str, type: str, content: str, description: Optional[str] = None) -> None:
        """Save memory."""
        if not self._db:
            path = self._storage_dir / "memories" / f"{name}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {"name": name, "type": type, "content": content, "description": description}
            path.write_text(json.dumps(data))
            return

        self._db.execute(
            """INSERT OR REPLACE INTO memories (name, type, description, content, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (name, type, description or "", content, datetime.now().isoformat()),
        )
        self._db.commit()

    def load_memory(self, name: str) -> Optional[Dict[str, Any]]:
        """Load memory."""
        if not self._db:
            path = self._storage_dir / "memories" / f"{name}.json"
            if path.exists():
                return json.loads(path.read_text())
            return None

        row = self._db.execute(
            "SELECT * FROM memories WHERE name = ?", (name,)
        ).fetchone()
        if row:
            return dict(row)
        return None

    # Analytics
    def save_analytics_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Save analytics event."""
        if not self._db:
            return  # Skip analytics if no DB

        self._db.execute(
            "INSERT INTO analytics (event_type, event_data, timestamp) VALUES (?, ?, ?)",
            (event_type, json.dumps(event_data), datetime.now().isoformat()),
        )
        self._db.commit()

    def get_analytics_events(self, event_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get analytics events."""
        if not self._db:
            return []

        if event_type:
            rows = self._db.execute(
                "SELECT * FROM analytics WHERE event_type = ? ORDER BY timestamp DESC LIMIT ?",
                (event_type, limit),
            ).fetchall()
        else:
            rows = self._db.execute(
                "SELECT * FROM analytics ORDER BY timestamp DESC LIMIT ?", (limit,)
            ).fetchall()

        return [dict(row) for row in rows]

    def close(self) -> None:
        """Close storage."""
        if self._db:
            self._db.close()
            self._db = None


# Singleton
_storage_service: Optional[StorageService] = None


def get_storage_service(config: Optional[StorageConfig] = None) -> StorageService:
    """Get storage service singleton."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService(config)
    return _storage_service


__all__ = [
    "StorageConfig",
    "StorageService",
    "get_storage_service",
]