"""Additional Hooks - Background, schedule, session, clipboard, notifications."""

from __future__ import annotations
import asyncio
from typing import Dict, Any, Callable, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class HookResult:
    """Hook result."""
    success: bool = True
    data: Dict[str, Any] = None
    error: str = ""


async def use_background_task(
    task_func: Callable,
    on_complete: Callable = None,
    on_error: Callable = None,
) -> asyncio.Task:
    """Run task in background."""
    async def wrapped():
        try:
            result = await task_func()
            if on_complete:
                await on_complete(result)
            return result
        except Exception as e:
            if on_error:
                await on_error(str(e))
            raise

    return asyncio.create_task(wrapped())


async def use_scheduled_task(
    task_func: Callable,
    interval_seconds: int,
    run_immediately: bool = False,
) -> asyncio.Task:
    """Schedule recurring task."""
    async def scheduled():
        if run_immediately:
            await task_func()

        while True:
            await asyncio.sleep(interval_seconds)
            await task_func()

    return asyncio.create_task(scheduled())


@dataclass
class SessionState:
    """Session state."""
    id: str
    cwd: str
    messages: List[Dict[str, Any]]
    started_at: datetime


async def use_session_storage(
    key: str,
    default: Any = None,
) -> SessionState:
    """Get/set session storage."""
    from ..state import get_store

    store = get_store()
    state = store.get_state()

    return state.custom.get(key, default)


async def use_clipboard() -> Dict[str, Callable]:
    """Clipboard operations."""
    async def copy(text: str) -> bool:
        """Copy to clipboard."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "pbcopy" if __import__("platform").system() == "Darwin" else "xclip -selection clipboard",
                stdin=asyncio.subprocess.PIPE,
            )
            await proc.communicate(text.encode())
            return True
        except:
            return False

    async def paste() -> str:
        """Paste from clipboard."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "pbpaste" if __import__("platform").system() == "Darwin" else "xclip -selection clipboard -o",
                stdout=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            return stdout.decode()
        except:
            return ""

    return {"copy": copy, "paste": paste}


async def use_notifications() -> Dict[str, Callable]:
    """Notification operations."""
    async def notify(title: str, message: str) -> bool:
        """Send notification."""
        try:
            if __import__("platform").system() == "Darwin":
                proc = await asyncio.create_subprocess_exec(
                    "osascript", "-e",
                    f'display notification "{message}" with title "{title}"'
                )
                await proc.wait()
            return True
        except:
            return False

    async def notify_error(message: str) -> bool:
        """Send error notification."""
        return await notify("Error", message)

    async def notify_success(message: str) -> bool:
        """Send success notification."""
        return await notify("Success", message)

    return {
        "notify": notify,
        "error": notify_error,
        "success": notify_success,
    }


async def use_diff_viewer(
    before: str,
    after: str,
) -> List[Dict[str, Any]]:
    """View diff between two texts."""
    import difflib

    before_lines = before.splitlines()
    after_lines = after.splitlines()

    diff = difflib.unified_diff(before_lines, after_lines, lineterm="")

    result = []
    for line in diff:
        if line.startswith("---") or line.startswith("+++"):
            continue
        elif line.startswith("-"):
            result.append({"type": "removed", "content": line[1:]})
        elif line.startswith("+"):
            result.append({"type": "added", "content": line[1:]})
        elif line.startswith("@@"):
            result.append({"type": "header", "content": line})
        else:
            result.append({"type": "context", "content": line})

    return result


async def use_search(
    query: str,
    sources: List[str] = None,
) -> List[Dict[str, Any]]:
    """Search across sources."""
    results = []

    # Search in messages
    from ..state import get_store
    store = get_store()
    state = store.get_state()

    query_lower = query.lower()

    for msg in state.session.messages:
        content = str(msg.get("content", ""))
        if query_lower in content.lower():
            results.append({
                "source": "messages",
                "type": "message",
                "content": content[:100],
                "metadata": msg,
            })

    # Search in files
    if sources and "files" in sources:
        import glob
        for filepath in glob.glob("*.py"):
            try:
                with open(filepath, "r") as f:
                    content = f.read()
                if query_lower in content.lower():
                    results.append({
                        "source": "files",
                        "type": "file",
                        "path": filepath,
                        "content": content[:100],
                    })
            except:
                pass

    return results


async def use_global_state() -> Dict[str, Any]:
    """Get global state snapshot."""
    from ..state import get_store, Selectors

    store = get_store()
    state = store.get_state()

    return {
        "messages": state.session.messages,
        "tokens": {
            "input": state.tokens.input_tokens,
            "output": state.tokens.output_tokens,
            "usage": Selectors.get_token_usage_percent(state),
        },
        "ui": {
            "mode": state.ui.mode,
            "theme": state.ui.theme,
            "vim_mode": state.ui.vim_mode,
        },
        "tools": {
            "active": state.tools.active_tools,
            "pending_permissions": state.tools.pending_permissions,
        },
        "tasks": state.tasks.tasks,
        "errors": state.errors.current_error,
        "loading": state.loading.is_loading,
    }


__all__ = [
    "use_background_task",
    "use_scheduled_task",
    "use_session_storage",
    "use_clipboard",
    "use_notifications",
    "use_diff_viewer",
    "use_search",
    "use_global_state",
]