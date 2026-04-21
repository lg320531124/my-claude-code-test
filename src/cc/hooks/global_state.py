"""Global Hook - Global state management."""

from __future__ import annotations
import asyncio
from typing import Any, Dict, Optional, Callable, List, TypeVar
from dataclasses import dataclass, field
from weakref import WeakKeyDictionary


T = TypeVar("T")


@dataclass
class GlobalState:
    """Global state container."""
    values: Dict[str, Any] = field(default_factory=dict)
    subscribers: Dict[str, List[Callable]] = field(default_factory=dict)


class GlobalHook:
    """Global state management hook."""

    def __init__(self):
        self._state = GlobalState()
        self._component_states: WeakKeyDictionary = WeakKeyDictionary()

    def get(self, key: str, default: Any = None) -> Any:
        """Get global state value.

        Args:
            key: State key
            default: Default value

        Returns:
            State value
        """
        return self._state.values.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set global state value.

        Args:
            key: State key
            value: Value to set
        """
        old_value = self._state.values.get(key)
        self._state.values[key] = value

        # Notify subscribers
        if key in self._state.subscribers:
            for subscriber in self._state.subscribers[key]:
                try:
                    if asyncio.iscoroutinefunction(subscriber):
                        asyncio.create_task(
                            subscriber(key, old_value, value)
                        )
                    else:
                        subscriber(key, old_value, value)
                except Exception:
                    pass

    def delete(self, key: str) -> bool:
        """Delete global state value.

        Args:
            key: State key

        Returns:
            True if deleted
        """
        if key in self._state.values:
            old_value = self._state.values.pop(key)
            self._state.subscribers.pop(key, None)

            # Notify subscribers of deletion
            for subscriber in self._state.subscribers.get(key, []):
                try:
                    if asyncio.iscoroutinefunction(subscriber):
                        asyncio.create_task(subscriber(key, old_value, None))
                    else:
                        subscriber(key, old_value, None)
                except Exception:
                    pass

            return True
        return False

    def subscribe(
        self,
        key: str,
        callback: Callable[[str, Any, Any], None],
    ) -> None:
        """Subscribe to state changes.

        Args:
            key: State key
            callback: Callback function (key, old_value, new_value)
        """
        if key not in self._state.subscribers:
            self._state.subscribers[key] = []
        self._state.subscribers[key].append(callback)

    def unsubscribe(
        self,
        key: str,
        callback: Callable,
    ) -> bool:
        """Unsubscribe from state changes.

        Args:
            key: State key
            callback: Callback to remove

        Returns:
            True if removed
        """
        if key in self._state.subscribers:
            if callback in self._state.subscribers[key]:
                self._state.subscribers[key].remove(callback)
                return True
        return False

    def get_all(self) -> Dict[str, Any]:
        """Get all state values.

        Returns:
            Copy of all state
        """
        return dict(self._state.values)

    def clear(self) -> None:
        """Clear all state."""
        for key in list(self._state.values.keys()):
            self.delete(key)

    def has(self, key: str) -> bool:
        """Check if key exists.

        Args:
            key: State key

        Returns:
            True if exists
        """
        return key in self._state.values

    # Component-specific state

    def get_component_state(
        self,
        component: Any,
        key: str,
        default: T = None,
    ) -> T:
        """Get component-specific state.

        Args:
            component: Component instance
            key: State key
            default: Default value

        Returns:
            State value
        """
        if component not in self._component_states:
            return default

        return self._component_states[component].get(key, default)

    def set_component_state(
        self,
        component: Any,
        key: str,
        value: Any,
    ) -> None:
        """Set component-specific state.

        Args:
            component: Component instance
            key: State key
            value: Value to set
        """
        if component not in self._component_states:
            self._component_states[component] = {}

        self._component_states[component][key] = value

    def clear_component_state(self, component: Any) -> None:
        """Clear component state.

        Args:
            component: Component instance
        """
        if component in self._component_states:
            del self._component_states[component]

    # Persistent state (saved across sessions)

    def save_state(self, path: str) -> None:
        """Save state to file.

        Args:
            path: File path
        """
        import json

        try:
            with open(path, "w") as f:
                json.dump(self._state.values, f, indent=2)
        except Exception:
            pass

    def load_state(self, path: str) -> bool:
        """Load state from file.

        Args:
            path: File path

        Returns:
            True if loaded
        """
        import json

        try:
            with open(path, "r") as f:
                values = json.load(f)
            for key, value in values.items():
                self.set(key, value)
            return True
        except Exception:
            return False

    # Batch operations

    def batch_set(self, values: Dict[str, Any]) -> None:
        """Set multiple values at once.

        Args:
            values: Dictionary of key-value pairs
        """
        for key, value in values.items():
            self.set(key, value)

    def batch_delete(self, keys: List[str]) -> int:
        """Delete multiple keys.

        Args:
            keys: Keys to delete

        Returns:
            Number of deleted keys
        """
        count = 0
        for key in keys:
            if self.delete(key):
                count += 1
        return count


# Global instance
_global_hook: Optional[GlobalHook] = None


def get_global_hook() -> GlobalHook:
    """Get global hook instance."""
    global _global_hook
    if _global_hook is None:
        _global_hook = GlobalHook()
    return _global_hook


def use_global(key: str, default: Any = None) -> Any:
    """Use global state.

    Args:
        key: State key
        default: Default value

    Returns:
        State value
    """
    return get_global_hook().get(key, default)


def set_global(key: str, value: Any) -> None:
    """Set global state.

    Args:
        key: State key
        value: Value to set
    """
    get_global_hook().set(key, value)


async def use_global_state() -> Dict[str, Any]:
    """Global state hook for hooks module.

    Returns global state functions.
    """
    hook = get_global_hook()

    return {
        "get": hook.get,
        "set": hook.set,
        "delete": hook.delete,
        "subscribe": hook.subscribe,
        "unsubscribe": hook.unsubscribe,
        "get_all": hook.get_all,
        "clear": hook.clear,
        "has": hook.has,
        "batch_set": hook.batch_set,
        "batch_delete": hook.batch_delete,
        "save_state": hook.save_state,
        "load_state": hook.load_state,
    }


__all__ = [
    "GlobalState",
    "GlobalHook",
    "get_global_hook",
    "use_global",
    "set_global",
    "use_global_state",
]