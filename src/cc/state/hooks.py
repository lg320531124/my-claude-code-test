"""State Hooks - React-like hooks for state management.

Provides async hooks for state access in async contexts:
- use_state: Get/set state slice
- use_selector: Select derived state
- use_dispatch: Dispatch actions
- use_effect: Side effects on state changes
"""

from __future__ import annotations
import asyncio
from typing import Callable, Optional, Any, Dict, List, TypeVar, Generic
from dataclasses import dataclass

from . import AppState, Store, Action, ActionType, get_store, Selectors


T = TypeVar('T')


@dataclass
class StateHook(Generic[T]):
    """State hook result."""
    value: T
    setter: Callable[[T], None]


async def use_state(
    path: str,
    default: T = None,
) -> StateHook[T]:
    """Get state value at path with setter.

    Usage:
        input_state = await use_state("custom.input", "")
        input_state.setter("new value")
    """
    store = get_store()
    state = store.get_state()

    # Get value at path
    parts = path.split(".")
    value = state

    for part in parts:
        if hasattr(value, part):
            value = getattr(value, part)
        elif isinstance(value, dict) and part in value:
            value = value[part]
        else:
            value = default
            break

    # Create setter
    def setter(new_value: T) -> None:
        async def async_set():
            await store.dispatch(Action(
                type=ActionType.CUSTOM,
                payload={"path": path, "value": new_value},
            ))

        # Try async dispatch
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(async_set())
            else:
                loop.run_until_complete(async_set())
        except:
            # Sync fallback
            store.dispatch_sync(Action(
                type=ActionType.CUSTOM,
                payload={"path": path, "value": new_value},
            ))

    return StateHook(value=value, setter=setter)


async def use_selector(
    selector: Callable[[AppState], T],
) -> T:
    """Select derived state.

    Usage:
        messages = await use_selector(Selectors.get_messages)
        token_percent = await use_selector(lambda s: s.tokens.input_tokens / s.tokens.max_input_tokens)
    """
    store = get_store()
    state = store.get_state()
    return selector(state)


async def use_dispatch() -> Callable[[Action], None]:
    """Get dispatch function.

    Usage:
        dispatch = await use_dispatch()
        await dispatch(Action(type=ActionType.MESSAGE_ADD, payload={"message": {...}}))
    """
    store = get_store()

    async def dispatch(action: Action) -> None:
        await store.dispatch(action)

    return dispatch


async def use_effect(
    effect: Callable[[AppState], None],
    deps: List[str] = None,
) -> Callable[[], None]:
    """Subscribe to state changes with effect.

    Usage:
        cleanup = await use_effect(
            lambda state: print(f"Token: {state.tokens.input_tokens}"),
            deps=["tokens"]
        )
        cleanup()  # Unsubscribe
    """
    store = get_store()

    # Filter by deps
    if deps:
        def listener(state: AppState, action: Action) -> None:
            # Check if action affects any dep
            dep_paths = {
                "session": ["session"],
                "messages": ["session", "messages"],
                "ui": ["ui"],
                "tokens": ["tokens"],
                "tools": ["tools"],
                "config": ["config"],
            }

            affected = False
            for dep in deps:
                paths = dep_paths.get(dep, [dep])
                for path in paths:
                    if action.type.name.lower().startswith(path.lower()):
                        affected = True
                        break

            if affected:
                effect(state)

    else:
        def listener(state: AppState, action: Action) -> None:
            effect(state)

    # Subscribe
    unsubscribe = store.subscribe(listener)

    # Run effect immediately
    effect(store.get_state())

    return unsubscribe


async def use_store() -> Store:
    """Get store directly.

    Usage:
        store = await use_store()
        state = store.get_state()
    """
    return get_store()


# Convenience hooks
async def use_messages() -> List[Dict[str, Any]]:
    """Get messages."""
    return await use_selector(Selectors.get_messages)


async def use_last_message() -> Optional[Dict[str, Any]]:
    """Get last message."""
    return await use_selector(Selectors.get_last_message)


async def use_token_usage() -> Dict[str, Any]:
    """Get token usage."""
    state = await use_store().get_state()
    return {
        "input": state.tokens.input_tokens,
        "output": state.tokens.output_tokens,
        "max_input": state.tokens.max_input_tokens,
        "percent": Selectors.get_token_usage_percent(state),
        "warning": Selectors.is_token_warning(state),
    }


async def use_loading() -> Dict[str, Any]:
    """Get loading state."""
    state = await use_store().get_state()
    return {
        "is_loading": state.loading.is_loading,
        "message": state.loading.loading_message,
        "operations": state.loading.loading_operations,
    }


async def use_error() -> Optional[str]:
    """Get current error."""
    return await use_selector(Selectors.get_current_error)


async def use_vim_mode() -> str:
    """Get vim mode."""
    return await use_selector(Selectors.get_vim_mode)


async def use_ui_state() -> Dict[str, Any]:
    """Get UI state."""
    state = await use_store().get_state()
    return {
        "mode": state.ui.mode,
        "theme": state.ui.theme,
        "vim_mode": state.ui.vim_mode,
        "focus": state.ui.focus,
        "dialog": state.ui.dialog,
    }


async def use_config() -> Dict[str, Any]:
    """Get config."""
    return await use_selector(Selectors.get_config)


async def use_active_tools() -> Dict[str, Dict[str, Any]]:
    """Get active tools."""
    return await use_selector(Selectors.get_active_tools)


async def use_pending_permissions() -> Dict[str, Dict[str, Any]]:
    """Get pending permissions."""
    return await use_selector(Selectors.get_pending_permissions)


async def use_mcp_servers() -> Dict[str, Any]:
    """Get MCP servers."""
    state = await use_store().get_state()
    return {
        "servers": state.mcp.servers,
        "connected": state.mcp.connected_servers,
        "tools": state.mcp.available_tools,
    }


async def use_tasks() -> Dict[int, Dict[str, Any]]:
    """Get all tasks."""
    state = await use_store().get_state()
    return state.tasks.tasks


async def use_pending_tasks() -> Dict[int, Dict[str, Any]]:
    """Get pending tasks."""
    return await use_selector(Selectors.get_pending_tasks)


# State change actions
async def set_ui_mode(mode: str, vim_mode: str = None) -> None:
    """Set UI mode."""
    dispatch = await use_dispatch()
    await dispatch(Action(
        type=ActionType.UI_MODE_CHANGE,
        payload={"mode": mode, "vim_mode": vim_mode or mode},
    ))


async def set_ui_theme(theme: str) -> None:
    """Set UI theme."""
    dispatch = await use_dispatch()
    await dispatch(Action(
        type=ActionType.UI_THEME_CHANGE,
        payload={"theme": theme},
    ))


async def set_input(text: str) -> None:
    """Set input text."""
    dispatch = await use_dispatch()
    await dispatch(Action(
        type=ActionType.INPUT_SET,
        payload={"input": text},
    ))


async def clear_input() -> None:
    """Clear input."""
    dispatch = await use_dispatch()
    await dispatch(Action(type=ActionType.INPUT_CLEAR))


async def set_error(error: str) -> None:
    """Set error."""
    dispatch = await use_dispatch()
    await dispatch(Action(
        type=ActionType.ERROR_SET,
        payload={"error": error},
    ))


async def clear_error() -> None:
    """Clear error."""
    dispatch = await use_dispatch()
    await dispatch(Action(type=ActionType.ERROR_CLEAR))


async def start_loading(message: str, operation: str) -> None:
    """Start loading."""
    dispatch = await use_dispatch()
    await dispatch(Action(
        type=ActionType.LOADING_START,
        payload={"message": message, "operation": operation},
    ))


async def end_loading(operation: str) -> None:
    """End loading."""
    dispatch = await use_dispatch()
    await dispatch(Action(
        type=ActionType.LOADING_END,
        payload={"operation": operation},
    ))


async def update_tokens(input_tokens: int, output_tokens: int) -> None:
    """Update tokens."""
    dispatch = await use_dispatch()
    await dispatch(Action(
        type=ActionType.TOKEN_UPDATE,
        payload={"input_tokens": input_tokens, "output_tokens": output_tokens},
    ))


async def add_message(message: Dict[str, Any]) -> None:
    """Add message."""
    dispatch = await use_dispatch()
    await dispatch(Action(
        type=ActionType.MESSAGE_ADD,
        payload={"message": message},
    ))


async def clear_messages() -> None:
    """Clear messages."""
    dispatch = await use_dispatch()
    await dispatch(Action(type=ActionType.MESSAGE_CLEAR))


__all__ = [
    "StateHook",
    "use_state",
    "use_selector",
    "use_dispatch",
    "use_effect",
    "use_store",
    "use_messages",
    "use_last_message",
    "use_token_usage",
    "use_loading",
    "use_error",
    "use_vim_mode",
    "use_ui_state",
    "use_config",
    "use_active_tools",
    "use_pending_permissions",
    "use_mcp_servers",
    "use_tasks",
    "use_pending_tasks",
    "set_ui_mode",
    "set_ui_theme",
    "set_input",
    "clear_input",
    "set_error",
    "clear_error",
    "start_loading",
    "end_loading",
    "update_tokens",
    "add_message",
    "clear_messages",
]