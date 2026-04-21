"""Hooks System - Async hook implementations.

Python hooks equivalent to React hooks for managing state, effects,
and async operations in the REPL context.
"""

from __future__ import annotations
import asyncio
from typing import Any, Callable, Optional, Dict, List, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum

# Import hook types from services
from ..services.hooks.hooks_system import HookType, HookContext, HookResult, get_hook_manager
from .advanced import HookResult as AdvancedHookResult

# Import new hook modules
from .permissions import (
    PermissionAction,
    PermissionChecker,
    PermissionHooks,
    get_permission_checker,
)
from .input import (
    InputEvent,
    InputHandler,
    TextInputHooks,
    get_input_handler,
)
from .scroll import (
    VirtualScroller,
    ScrollHooks,
    get_virtual_scroller,
)
from .history import (
    HistoryManager,
    HistoryHooks,
    get_history_manager,
)
from .ide import (
    IDEIntegration,
    IDEHooks,
    get_ide_integration,
)
from .mcp import (
    MCPHooks,
    get_mcp_hooks,
)
from .clipboard import (
    ClipboardContent,
    ClipboardHook,
    get_clipboard_hook,
    use_clipboard,
)
from .notifications import (
    NotificationLevel,
    NotificationMessage,
    NotificationHook,
    get_notification_hook,
    use_notifications,
)
from .diff import (
    DiffType,
    DiffOperation,
    DiffLine,
    DiffResult,
    DiffHook,
    get_diff_hook,
    use_diff,
)
from .search import (
    SearchType,
    SearchMatch,
    SearchResult,
    SearchHook,
    get_search_hook,
    use_search,
)
from .global_state import (
    GlobalState,
    GlobalHook,
    get_global_hook,
    use_global,
    set_global,
    use_global_state,
)
from .background import (
    TaskState,
    BackgroundTask,
    BackgroundHook,
    get_background_hook,
    use_background,
)
from .schedule import (
    ScheduleType,
    ScheduledJob,
    ScheduleHook,
    get_schedule_hook,
    use_schedule,
)
from .session import (
    SessionState,
    SessionData,
    SessionHook,
    get_session_hook,
    use_session,
)


class HookState:
    """Base class for hook state management."""

    def __init__(self):
        self._state: Dict[str, Any] = {}
        self._effects: List[Callable] = []
        self._cleanup: List[Callable] = []


def use_state(initial_value: Any = None) -> tuple[Any, Callable]:
    """React-like useState hook for Python.

    Returns (value, setter) tuple.
    """
    state_manager = HookState()

    key = f"state_{len(state_manager._state)}"
    state_manager._state[key] = initial_value

    def setter(new_value: Any) -> None:
        state_manager._state[key] = new_value
        # Trigger effects
        for effect in state_manager._effects:
            if asyncio.iscoroutinefunction(effect):
                asyncio.create_task(effect())
            else:
                effect()

    return state_manager._state[key], setter


def use_effect(effect: Callable, deps: List[Any] = None) -> None:
    """React-like useEffect hook for Python.

    Registers an effect to run when dependencies change.
    """
    state_manager = HookState()

    # Check if deps changed
    key = f"effect_{len(state_manager._effects)}"
    prev_deps = state_manager._state.get(key)

    if deps is None or prev_deps != deps:
        state_manager._state[key] = deps

        # Run cleanup if exists
        if state_manager._cleanup:
            for cleanup in state_manager._cleanup:
                cleanup()

        # Run effect
        state_manager._effects.append(effect)

        if asyncio.iscoroutinefunction(effect):
            asyncio.create_task(effect())
        else:
            effect()


def use_async_effect(effect: Callable[[], AsyncIterator[Any]]) -> None:
    """Async effect hook that returns cleanup function.

    Usage:
        async def my_effect():
            async for item in stream:
                process(item)
            return cleanup

        use_async_effect(my_effect)
    """
    async def run_effect():
        cleanup = await effect()
        if cleanup:
            HookState()._cleanup.append(cleanup)

    asyncio.create_task(run_effect())


# Specific hooks for Claude Code

async def use_can_use_tool(tool_name: str) -> bool:
    """Check if tool can be used based on permissions.

    Async hook for permission checking.
    """
    from ..tools.shared.permissions import check_tool_permission

    return await check_tool_permission(tool_name)


async def use_global_keybindings(bindings: Dict[str, Callable]) -> None:
    """Register global keybindings.

    Args:
        bindings: Dict mapping key to handler function
    """
    manager = get_hook_manager()

    async def keybinding_handler(context: HookContext):
        key = context.data.get("key")
        if key in bindings:
            handler = bindings[key]
            if asyncio.iscoroutinefunction(handler):
                await handler(context.data)
            else:
                handler(context.data)
            return HookResult(success=True)

    manager.register(
        hook_type=HookType.PRE_TOOL_USE,
        name="global_keybindings",
        handler=keybinding_handler,
    )


async def use_text_input(
    placeholder: str = "",
    default: str = "",
    multiline: bool = False
) -> tuple[str, Callable]:
    """Async input hook.

    Returns (value, submit_function).
    """
    value = default

    async def submit(new_value: str = None) -> str:
        if new_value:
            value = new_value
        return value

    return value, submit


async def use_virtual_scroll(
    items: List[Any],
    item_height: int = 1,
    visible_count: int = 20
) -> Dict[str, Any]:
    """Virtual scroll hook for large lists.

    Returns scroll state: {start, end, visible_items}
    """
    scroll_state = {
        "start": 0,
        "end": visible_count,
        "visible_items": items[:visible_count],
        "total": len(items),
    }

    def scroll_up(count: int = 1):
        scroll_state["start"] = max(0, scroll_state["start"] - count)
        scroll_state["end"] = scroll_state["start"] + visible_count
        scroll_state["visible_items"] = items[scroll_state["start"]:scroll_state["end"]]

    def scroll_down(count: int = 1):
        max_start = len(items) - visible_count
        scroll_state["start"] = min(max_start, scroll_state["start"] + count)
        scroll_state["end"] = scroll_state["start"] + visible_count
        scroll_state["visible_items"] = items[scroll_state["start"]:scroll_state["end"]]

    scroll_state["scroll_up"] = scroll_up
    scroll_state["scroll_down"] = scroll_down

    return scroll_state


async def use_repl_bridge() -> Dict[str, Callable]:
    """REPL bridge hook for communicating with REPL.

    Returns bridge functions: {send, receive, subscribe}
    """
    _subscribers: List[Callable] = []
    _messages: List[Any] = []

    async def send(message: Any) -> None:
        _messages.append(message)
        for subscriber in _subscribers:
            if asyncio.iscoroutinefunction(subscriber):
                await subscriber(message)
            else:
                subscriber(message)

    async def receive() -> Optional[Any]:
        if _messages:
            return _messages.pop(0)
        return None

    def subscribe(handler: Callable) -> None:
        _subscribers.append(handler)

    return {
        "send": send,
        "receive": receive,
        "subscribe": subscribe,
    }


async def use_ide_integration() -> Dict[str, Any]:
    """IDE integration hook.

    Returns IDE state and functions.
    """
    ide_state = {
        "connected": False,
        "ide_type": None,  # vscode, jetbrains, neovim
        "features": [],
    }

    async def connect(ide_type: str) -> bool:
        # Would actually connect to IDE
        ide_state["connected"] = True
        ide_state["ide_type"] = ide_type
        ide_state["features"] = ["completion", "diagnostics", "hover"]
        return True

    async def open_file(path: str) -> None:
        if ide_state["connected"]:
            # Would send to IDE
            pass

    async def show_diagnostic(diagnostic: Any) -> None:
        if ide_state["connected"]:
            # Would send to IDE
            pass

    ide_state["connect"] = connect
    ide_state["open_file"] = open_file
    ide_state["show_diagnostic"] = show_diagnostic

    return ide_state


async def use_mcp_connection(server_name: str) -> Dict[str, Any]:
    """MCP connection hook.

    Returns connection state and functions.
    """
    connection_state = {
        "connected": False,
        "tools": [],
        "resources": [],
    }

    async def connect() -> bool:
        from ..services.mcp import MCPManager

        manager = MCPManager()
        client = manager.get_client(server_name)

        if client:
            connection_state["connected"] = True
            connection_state["tools"] = client.get_tools()
            connection_state["resources"] = client.get_resources()
            return True
        return False

    async def call_tool(tool_name: str, args: Dict) -> Any:
        if connection_state["connected"]:
            from ..services.mcp import MCPManager

            manager = MCPManager()
            return await manager.call_tool(server_name, tool_name, args)
        return None

    connection_state["connect"] = connect
    connection_state["call_tool"] = call_tool

    return connection_state


async def use_voice_integration() -> Dict[str, Any]:
    """Voice integration hook.

    Returns voice state and functions.
    """
    voice_state = {
        "listening": False,
        "speaking": False,
        "transcript": "",
    }

    async def start_listening() -> None:
        from ..services.voice import VoiceService

        service = VoiceService()
        voice_state["listening"] = True
        # Would start actual listening

    async def stop_listening() -> str:
        voice_state["listening"] = False
        # Would return transcript
        return voice_state["transcript"]

    async def speak(text: str) -> None:
        voice_state["speaking"] = True
        from ..services.voice import VoiceService

        service = VoiceService()
        await service.synthesize(text)
        voice_state["speaking"] = False

    voice_state["start_listening"] = start_listening
    voice_state["stop_listening"] = stop_listening
    voice_state["speak"] = speak

    return voice_state


async def use_history_search(query: str) -> List[Dict]:
    """History search hook.

    Returns matching history entries.
    """
    from ..core.session import SessionManager

    manager = SessionManager()
    sessions = manager.list_sessions()

    results = []
    for session in sessions:
        for msg in session.get("messages", []):
            content = msg.get("content", "")
            if isinstance(content, str) and query.lower() in content.lower():
                results.append({
                    "session_id": session.get("id"),
                    "message": msg,
                })

    return results


async def use_typeahead(items: List[str], query: str) -> List[str]:
    """Typeahead/autocomplete hook.

    Returns matching items.
    """
    if not query:
        return items[:10]

    matching = []
    for item in items:
        if item.lower().startswith(query.lower()):
            matching.append(item)

    return matching[:10]


async def use_background_task(
    task: Callable,
    on_complete: Callable = None,
    on_error: Callable = None
) -> Dict[str, Any]:
    """Background task hook.

    Returns task state.
    """
    task_state = {
        "running": False,
        "result": None,
        "error": None,
    }

    async def run_task():
        task_state["running"] = True
        try:
            result = await task()
            task_state["result"] = result
            task_state["running"] = False

            if on_complete:
                await on_complete(result)

        except Exception as e:
            task_state["error"] = e
            task_state["running"] = False

            if on_error:
                await on_error(e)

    asyncio.create_task(run_task())

    return task_state


async def use_scheduled_tasks(
    tasks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Scheduled tasks hook.

    Args:
        tasks: List of {name, schedule, handler}

    Returns scheduler state.
    """
    from ..tools.schedule import get_scheduler

    scheduler = get_scheduler()

    for task in tasks:
        scheduler.add_job(
            name=task["name"],
            cron=task["schedule"],
            handler=task["handler"],
        )

    return {
        "scheduler": scheduler,
        "jobs": scheduler.list_jobs(),
    }


async def use_session_storage() -> Dict[str, Any]:
    """Session storage hook.

    Returns storage functions.
    """
    from ..core.session import SessionManager

    manager = SessionManager()

    async def save(key: str, value: Any) -> None:
        # Would save to session
        pass

    async def load(key: str) -> Optional[Any]:
        # Would load from session
        return None

    async def clear() -> None:
        # Would clear session
        pass

    return {
        "save": save,
        "load": load,
        "clear": clear,
        "manager": manager,
    }


async def use_clipboard() -> Dict[str, Any]:
    """Clipboard hook.

    Returns clipboard functions.
    """
    async def copy(text: str) -> None:
        # Would copy to clipboard
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: __import__("subprocess").run(["pbcopy"], input=text.encode())
        )

    async def paste() -> str:
        # Would paste from clipboard
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: __import__("subprocess").run(["pbpaste"], capture_output=True, text=True)
        )
        return result.stdout

    return {
        "copy": copy,
        "paste": paste,
    }


async def use_notifications() -> Dict[str, Any]:
    """Notifications hook.

    Returns notification functions.
    """
    async def notify(message: str, level: str = "info") -> None:
        from ..services.notifier import get_notifier

        notifier = get_notifier()
        await notifier.notify(message, level)

    async def subscribe(handler: Callable) -> None:
        # Would subscribe to notifications
        pass

    return {
        "notify": notify,
        "subscribe": subscribe,
    }


__all__ = [
    # Base hooks
    "HookState",
    "use_state",
    "use_effect",
    "use_async_effect",
    # Claude Code hooks
    "use_can_use_tool",
    "use_global_keybindings",
    "use_text_input",
    "use_virtual_scroll",
    "use_repl_bridge",
    "use_ide_integration",
    "use_mcp_connection",
    "use_voice_integration",
    "use_history_search",
    "use_typeahead",
    "use_background_task",
    "use_scheduled_tasks",
    "use_session_storage",
    "use_clipboard",
    "use_notifications",
    # Permission hooks
    "PermissionAction",
    "PermissionChecker",
    "PermissionHooks",
    "get_permission_checker",
    # Input hooks
    "InputEvent",
    "InputHandler",
    "TextInputHooks",
    "get_input_handler",
    # Scroll hooks
    "VirtualScroller",
    "ScrollHooks",
    "get_virtual_scroller",
    # History hooks
    "HistoryManager",
    "HistoryHooks",
    "get_history_manager",
    # IDE hooks
    "IDEIntegration",
    "IDEHooks",
    "get_ide_integration",
    # MCP hooks
    "MCPHooks",
    "get_mcp_hooks",
    # Clipboard hooks
    "ClipboardContent",
    "ClipboardHook",
    "get_clipboard_hook",
    # Notification hooks
    "NotificationLevel",
    "NotificationMessage",
    "NotificationHook",
    "get_notification_hook",
    # Diff hooks
    "DiffType",
    "DiffOperation",
    "DiffLine",
    "DiffResult",
    "DiffHook",
    "get_diff_hook",
    # Search hooks
    "SearchType",
    "SearchMatch",
    "SearchResult",
    "SearchHook",
    "get_search_hook",
    # Global state hooks
    "GlobalState",
    "GlobalHook",
    "get_global_hook",
    "use_global",
    "set_global",
    "use_global_state",
    # Background hooks
    "TaskState",
    "BackgroundTask",
    "BackgroundHook",
    "get_background_hook",
    # Schedule hooks
    "ScheduleType",
    "ScheduledJob",
    "ScheduleHook",
    "get_schedule_hook",
    # Session hooks
    "SessionState",
    "SessionData",
    "SessionHook",
    "get_session_hook",
]