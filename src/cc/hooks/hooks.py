"""Hooks package - Async hook implementations."""

from __future__ import annotations
from .tool_permission import (
    PermissionState,
    ToolPermissionHook,
    use_tool_permission,
    use_bash_permission,
    register_permission_hook,
)
from .keybindings import (
    KeyMode,
    KeyBinding,
    KeybindingsHook,
    use_keybindings,
    register_default_keybindings,
)

# Import all from main hooks
from . import (
    HookState,
    use_state,
    use_effect,
    use_async_effect,
    use_can_use_tool,
    use_global_keybindings,
    use_text_input,
    use_virtual_scroll,
    use_repl_bridge,
    use_ide_integration,
    use_mcp_connection,
    use_voice_integration,
    use_history_search,
    use_typeahead,
    use_background_task,
    use_scheduled_tasks,
    use_session_storage,
    use_clipboard,
    use_notifications,
)

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
    "PermissionState",
    "ToolPermissionHook",
    "use_tool_permission",
    "use_bash_permission",
    "register_permission_hook",
    # Keybinding hooks
    "KeyMode",
    "KeyBinding",
    "KeybindingsHook",
    "use_keybindings",
    "register_default_keybindings",
]