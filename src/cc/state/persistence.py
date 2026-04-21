"""State Persistence - Save and load state to/from files.

Provides async state persistence for session recovery.
"""

from __future__ import annotations
import asyncio
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

import aiofiles

from . import AppState, Action, ActionType, get_store


class StatePersistence:
    """State persistence manager."""

    def __init__(self, storage_dir: Path = None):
        self.storage_dir = storage_dir or Path.home() / ".claude" / "state"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def save_state(self, state: AppState, filename: str = None) -> Path:
        """Save state to file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"state_{timestamp}.json"

        filepath = self.storage_dir / filename

        # Convert to serializable dict
        state_dict = self._serialize_state(state)

        async with aiofiles.open(filepath, "w") as f:
            await f.write(json.dumps(state_dict, indent=2))

        return filepath

    async def load_state(self, filename: str = None) -> Optional[AppState]:
        """Load state from file."""
        if filename is None:
            # Find most recent state file
            state_files = sorted(
                self.storage_dir.glob("state_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if not state_files:
                return None
            filepath = state_files[0]
        else:
            filepath = self.storage_dir / filename

        if not filepath.exists():
            return None

        async with aiofiles.open(filepath, "r") as f:
            content = await f.read()

        state_dict = json.loads(content)
        return self._deserialize_state(state_dict)

    async def save_session(self, session_id: str, state: AppState) -> Path:
        """Save session state."""
        filename = f"session_{session_id}.json"
        filepath = self.storage_dir / "sessions" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        state_dict = self._serialize_state(state)

        async with aiofiles.open(filepath, "w") as f:
            await f.write(json.dumps(state_dict, indent=2))

        return filepath

    async def load_session(self, session_id: str) -> Optional[AppState]:
        """Load session state."""
        filepath = self.storage_dir / "sessions" / f"session_{session_id}.json"

        if not filepath.exists():
            return None

        async with aiofiles.open(filepath, "r") as f:
            content = await f.read()

        state_dict = json.loads(content)
        return self._deserialize_state(state_dict)

    async def list_sessions(self) -> Dict[str, Dict[str, Any]]:
        """List saved sessions."""
        sessions_dir = self.storage_dir / "sessions"

        if not sessions_dir.exists():
            return {}

        sessions = {}
        for filepath in sessions_dir.glob("session_*.json"):
            try:
                async with aiofiles.open(filepath, "r") as f:
                    content = await f.read()
                state_dict = json.loads(content)

                session_id = filepath.stem.replace("session_", "")
                sessions[session_id] = {
                    "id": session_id,
                    "cwd": state_dict.get("session", {}).get("cwd", ""),
                    "started_at": state_dict.get("session", {}).get("started_at", 0),
                    "message_count": len(state_dict.get("session", {}).get("messages", [])),
                    "filepath": str(filepath),
                }
            except Exception:
                pass

        return sessions

    async def delete_session(self, session_id: str) -> bool:
        """Delete session."""
        filepath = self.storage_dir / "sessions" / f"session_{session_id}.json"

        if filepath.exists():
            filepath.unlink()
            return True

        return False

    async def auto_save(self, interval_seconds: int = 60) -> None:
        """Auto-save state periodically."""
        while True:
            await asyncio.sleep(interval_seconds)

            store = get_store()
            state = store.get_state()

            if state.session.active:
                await self.save_session(state.session.id, state)

    def _serialize_state(self, state: AppState) -> Dict[str, Any]:
        """Serialize state to dict."""
        return {
            "session": {
                "id": state.session.id,
                "cwd": state.session.cwd,
                "started_at": state.session.started_at,
                "messages": state.session.messages,
                "input_history": state.session.input_history,
                "active": state.session.active,
            },
            "ui": {
                "mode": state.ui.mode,
                "theme": state.ui.theme,
                "focus": state.ui.focus,
                "vim_mode": state.ui.vim_mode,
            },
            "tokens": {
                "input_tokens": state.tokens.input_tokens,
                "output_tokens": state.tokens.output_tokens,
            },
            "config": {
                "model": state.config.model,
                "max_tokens": state.config.max_tokens,
                "custom": state.config.custom,
            },
            "context": {
                "files": state.context.files,
                "git_branch": state.context.git_branch,
            },
            "custom": state.custom,
            "saved_at": datetime.now().isoformat(),
        }

    def _deserialize_state(self, data: Dict[str, Any]) -> AppState:
        """Deserialize dict to state."""
        state = AppState()

        session_data = data.get("session", {})
        state.session.id = session_data.get("id", "")
        state.session.cwd = session_data.get("cwd", "")
        state.session.started_at = session_data.get("started_at", 0.0)
        state.session.messages = session_data.get("messages", [])
        state.session.input_history = session_data.get("input_history", [])

        ui_data = data.get("ui", {})
        state.ui.mode = ui_data.get("mode", "normal")
        state.ui.theme = ui_data.get("theme", "dark")
        state.ui.vim_mode = ui_data.get("vim_mode", "normal")

        tokens_data = data.get("tokens", {})
        state.tokens.input_tokens = tokens_data.get("input_tokens", 0)
        state.tokens.output_tokens = tokens_data.get("output_tokens", 0)

        config_data = data.get("config", {})
        state.config.model = config_data.get("model", "claude-sonnet-4-6")
        state.config.max_tokens = config_data.get("max_tokens", 8192)
        state.config.custom = config_data.get("custom", {})

        context_data = data.get("context", {})
        state.context.files = context_data.get("files", [])
        state.context.git_branch = context_data.get("git_branch", "")

        state.custom = data.get("custom", {})

        return state


# Convenience functions
_persistence: Optional[StatePersistence] = None


def get_persistence() -> StatePersistence:
    """Get global persistence manager."""
    global _persistence
    if _persistence is None:
        _persistence = StatePersistence()
    return _persistence


async def save_current_state(filename: str = None) -> Path:
    """Save current state."""
    persistence = get_persistence()
    store = get_store()
    return await persistence.save_state(store.get_state(), filename)


async def load_saved_state(filename: str = None) -> Optional[AppState]:
    """Load saved state."""
    persistence = get_persistence()
    return await persistence.load_state(filename)


async def save_current_session() -> Path:
    """Save current session."""
    persistence = get_persistence()
    store = get_store()
    state = store.get_state()
    return await persistence.save_session(state.session.id, state)


async def load_session_state(session_id: str) -> Optional[AppState]:
    """Load session state."""
    persistence = get_persistence()
    return await persistence.load_session(session_id)


async def list_saved_sessions() -> Dict[str, Dict[str, Any]]:
    """List saved sessions."""
    persistence = get_persistence()
    return await persistence.list_sessions()


async def restore_session(session_id: str) -> bool:
    """Restore session into store."""
    persistence = get_persistence()
    state = await persistence.load_session(session_id)

    if state is None:
        return False

    store = get_store()

    # Restore state by dispatching actions
    await store.dispatch(Action(
        type=ActionType.SESSION_START,
        payload={
            "id": state.session.id,
            "cwd": state.session.cwd,
        },
    ))

    for message in state.session.messages:
        await store.dispatch(Action(
            type=ActionType.MESSAGE_ADD,
            payload={"message": message},
        ))

    return True


__all__ = [
    "StatePersistence",
    "get_persistence",
    "save_current_state",
    "load_saved_state",
    "save_current_session",
    "load_session_state",
    "list_saved_sessions",
    "restore_session",
]