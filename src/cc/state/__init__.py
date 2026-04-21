"""State Module - Centralized state management.

Provides Redux-like state management with:
- AppState: Central state container
- Actions: State mutations
- Reducers: Pure functions for state changes
- Selectors: Derived state queries
- Async state operations
"""

from __future__ import annotations
import asyncio
from typing import Dict, Any, Optional, Callable, List, Tuple, TypeVar
from dataclasses import dataclass, field
from enum import Enum
from copy import deepcopy


T = TypeVar('T')


class ActionType(Enum):
    """Standard action types."""
    # Session
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    SESSION_RESET = "session_reset"

    # Messages
    MESSAGE_ADD = "message_add"
    MESSAGE_UPDATE = "message_update"
    MESSAGE_DELETE = "message_delete"
    MESSAGE_CLEAR = "message_clear"

    # Tools
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_PROGRESS = "tool_call_progress"
    TOOL_CALL_END = "tool_call_end"
    TOOL_PERMISSION_REQUEST = "tool_permission_request"
    TOOL_PERMISSION_GRANT = "tool_permission_grant"
    TOOL_PERMISSION_DENY = "tool_permission_deny"

    # UI
    UI_MODE_CHANGE = "ui_mode_change"
    UI_THEME_CHANGE = "ui_theme_change"
    UI_FOCUS_CHANGE = "ui_focus_change"
    UI_SCROLL = "ui_scroll"
    UI_RESIZE = "ui_resize"
    UI_DIALOG_OPEN = "ui_dialog_open"
    UI_DIALOG_CLOSE = "ui_dialog_close"

    # Input
    INPUT_SET = "input_set"
    INPUT_APPEND = "input_append"
    INPUT_CLEAR = "input_clear"
    INPUT_HISTORY_ADD = "input_history_add"

    # Context
    CONTEXT_UPDATE = "context_update"
    CONTEXT_FILE_ADD = "context_file_add"
    CONTEXT_FILE_REMOVE = "context_file_remove"
    CONTEXT_GIT_UPDATE = "context_git_update"

    # MCP
    MCP_SERVER_ADD = "mcp_server_add"
    MCP_SERVER_REMOVE = "mcp_server_remove"
    MCP_SERVER_CONNECT = "mcp_server_connect"
    MCP_SERVER_DISCONNECT = "mcp_server_disconnect"
    MCP_TOOL_ENABLE = "mcp_tool_enable"
    MCP_TOOL_DISABLE = "mcp_tool_disable"

    # Config
    CONFIG_UPDATE = "config_update"
    CONFIG_RESET = "config_reset"

    # Tasks
    TASK_CREATE = "task_create"
    TASK_UPDATE = "task_update"
    TASK_DELETE = "task_delete"
    TASK_START = "task_start"
    TASK_COMPLETE = "task_complete"
    TASK_FAIL = "task_fail"

    # Tokens
    TOKEN_UPDATE = "token_update"
    TOKEN_WARNING = "token_warning"
    TOKEN_LIMIT_REACHED = "token_limit_reached"

    # Error
    ERROR_SET = "error_set"
    ERROR_CLEAR = "error_clear"

    # Loading
    LOADING_START = "loading_start"
    LOADING_END = "loading_end"

    # Custom
    CUSTOM = "custom"


@dataclass
class Action:
    """State action."""
    type: ActionType
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    source: str = "system"

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = asyncio.get_event_loop().time()


@dataclass
class SessionState:
    """Session state slice."""
    id: str = ""
    cwd: str = ""
    started_at: float = 0.0
    messages: List[Dict[str, Any]] = field(default_factory=list)
    input_history: List[str] = field(default_factory=list)
    active: bool = True


@dataclass
class UIState:
    """UI state slice."""
    mode: str = "normal"
    theme: str = "dark"
    focus: str = "input"
    scroll_position: int = 0
    viewport_size: Tuple[int, int] = (0, 0)
    dialog: Optional[str] = None
    dialog_data: Dict[str, Any] = field(default_factory=dict)
    vim_mode: str = "normal"
    show_token_bar: bool = False
    show_help: bool = False


@dataclass
class ToolState:
    """Tool state slice."""
    active_tools: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    pending_permissions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    tool_history: List[Dict[str, Any]] = field(default_factory=list)
    last_tool_result: Optional[Dict[str, Any]] = None


@dataclass
class ContextState:
    """Context state slice."""
    files: List[str] = field(default_factory=list)
    git_branch: str = ""
    git_status: str = ""
    git_recent_commits: List[str] = field(default_factory=list)
    project_type: str = ""
    system_prompt: str = ""


@dataclass
class MCPState:
    """MCP state slice."""
    servers: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    connected_servers: List[str] = field(default_factory=list)
    available_tools: Dict[str, bool] = field(default_factory=dict)


@dataclass
class ConfigState:
    """Config state slice."""
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 8192
    temperature: float = 1.0
    permissions: Dict[str, List[str]] = field(default_factory=dict)
    hooks: Dict[str, Any] = field(default_factory=dict)
    custom: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskStateSlice:
    """Task state slice."""
    tasks: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    active_task: Optional[int] = None


@dataclass
class TokenState:
    """Token state slice."""
    input_tokens: int = 0
    output_tokens: int = 0
    max_input_tokens: int = 100000
    max_output_tokens: int = 8192
    last_estimate: float = 0.0
    warning_threshold: float = 0.8


@dataclass
class ErrorState:
    """Error state slice."""
    current_error: Optional[str] = None
    error_history: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class LoadingState:
    """Loading state slice."""
    is_loading: bool = False
    loading_message: str = ""
    loading_progress: float = 0.0
    loading_operations: List[str] = field(default_factory=list)


@dataclass
class AppState:
    """Central application state."""
    session: SessionState = field(default_factory=SessionState)
    ui: UIState = field(default_factory=UIState)
    tools: ToolState = field(default_factory=ToolState)
    context: ContextState = field(default_factory=ContextState)
    mcp: MCPState = field(default_factory=MCPState)
    config: ConfigState = field(default_factory=ConfigState)
    tasks: TaskStateSlice = field(default_factory=TaskStateSlice)
    tokens: TokenState = field(default_factory=TokenState)
    errors: ErrorState = field(default_factory=ErrorState)
    loading: LoadingState = field(default_factory=LoadingState)

    # Custom state
    custom: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "session": {
                "id": self.session.id,
                "cwd": self.session.cwd,
                "started_at": self.session.started_at,
                "messages": self.session.messages,
                "input_history": self.session.input_history,
                "active": self.session.active,
            },
            "ui": {
                "mode": self.ui.mode,
                "theme": self.ui.theme,
                "focus": self.ui.focus,
                "scroll_position": self.ui.scroll_position,
                "viewport_size": self.ui.viewport_size,
                "dialog": self.ui.dialog,
                "vim_mode": self.ui.vim_mode,
            },
            "tools": {
                "active_tools": self.tools.active_tools,
                "pending_permissions": self.tools.pending_permissions,
            },
            "context": {
                "files": self.context.files,
                "git_branch": self.context.git_branch,
                "git_status": self.context.git_status,
            },
            "mcp": {
                "servers": self.mcp.servers,
                "connected_servers": self.mcp.connected_servers,
            },
            "config": {
                "model": self.config.model,
                "max_tokens": self.config.max_tokens,
            },
            "tokens": {
                "input_tokens": self.tokens.input_tokens,
                "output_tokens": self.tokens.output_tokens,
                "usage_percent": self.tokens.input_tokens / self.tokens.max_input_tokens,
            },
            "errors": {
                "current_error": self.errors.current_error,
            },
            "loading": {
                "is_loading": self.loading.is_loading,
                "loading_message": self.loading.loading_message,
            },
        }


class Store:
    """Redux-like store for state management."""

    def __init__(self, initial_state: AppState = None):
        self._state = initial_state or AppState()
        self._reducers: Dict[ActionType, Callable] = {}
        self._listeners: List[Callable] = []
        self._middleware: List[Callable] = []
        self._action_history: List[Action] = []
        self._lock = asyncio.Lock()

        # Register default reducers
        self._register_default_reducers()

    def _register_default_reducers(self) -> None:
        """Register built-in reducers."""
        self.register_reducer(ActionType.SESSION_START, self._session_start_reducer)
        self.register_reducer(ActionType.SESSION_END, self._session_end_reducer)
        self.register_reducer(ActionType.SESSION_RESET, self._session_reset_reducer)
        self.register_reducer(ActionType.MESSAGE_ADD, self._message_add_reducer)
        self.register_reducer(ActionType.MESSAGE_CLEAR, self._message_clear_reducer)
        self.register_reducer(ActionType.UI_MODE_CHANGE, self._ui_mode_change_reducer)
        self.register_reducer(ActionType.UI_THEME_CHANGE, self._ui_theme_change_reducer)
        self.register_reducer(ActionType.INPUT_SET, self._input_set_reducer)
        self.register_reducer(ActionType.INPUT_CLEAR, self._input_clear_reducer)
        self.register_reducer(ActionType.TOOL_CALL_START, self._tool_call_start_reducer)
        self.register_reducer(ActionType.TOOL_CALL_END, self._tool_call_end_reducer)
        self.register_reducer(ActionType.TOKEN_UPDATE, self._token_update_reducer)
        self.register_reducer(ActionType.ERROR_SET, self._error_set_reducer)
        self.register_reducer(ActionType.ERROR_CLEAR, self._error_clear_reducer)
        self.register_reducer(ActionType.LOADING_START, self._loading_start_reducer)
        self.register_reducer(ActionType.LOADING_END, self._loading_end_reducer)
        self.register_reducer(ActionType.CONFIG_UPDATE, self._config_update_reducer)
        self.register_reducer(ActionType.TASK_CREATE, self._task_create_reducer)
        self.register_reducer(ActionType.TASK_UPDATE, self._task_update_reducer)
        self.register_reducer(ActionType.TASK_DELETE, self._task_delete_reducer)

    def register_reducer(self, action_type: ActionType, reducer: Callable) -> None:
        """Register reducer for action type."""
        self._reducers[action_type] = reducer

    def subscribe(self, listener: Callable) -> Callable:
        """Subscribe to state changes. Returns unsubscribe function."""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware for action processing."""
        self._middleware.append(middleware)

    def get_state(self) -> AppState:
        """Get current state."""
        return self._state

    async def dispatch(self, action: Action) -> AppState:
        """Dispatch action to state."""
        # Run middleware
        for middleware in self._middleware:
            action = await middleware(action, self._state)
            if action is None:
                return self._state

        # Apply reducer
        async with self._lock:
            reducer = self._reducers.get(action.type)
            if reducer:
                self._state = await reducer(self._state, action)

            # Record action
            self._action_history.append(action)

            # Notify listeners
            for listener in self._listeners:
                if asyncio.iscoroutinefunction(listener):
                    await listener(self._state, action)
                else:
                    listener(self._state, action)

        return self._state

    def dispatch_sync(self, action: Action) -> AppState:
        """Synchronous dispatch (for non-async contexts)."""
        reducer = self._reducers.get(action.type)
        if reducer:
            # Call sync version
            try:
                result = reducer(self._state, action)
                if asyncio.iscoroutine(result):
                    # Can't run async in sync context
                    return self._state
                self._state = result
            except:
                pass

        self._action_history.append(action)
        return self._state

    # Default reducers
    async def _session_start_reducer(self, state: AppState, action: Action) -> AppState:
        """Handle session start."""
        new_state = deepcopy(state)
        new_state.session.id = action.payload.get("id", "")
        new_state.session.cwd = action.payload.get("cwd", "")
        new_state.session.started_at = action.timestamp
        new_state.session.active = True
        return new_state

    async def _session_end_reducer(self, state: AppState, action: Action) -> AppState:
        """Handle session end."""
        new_state = deepcopy(state)
        new_state.session.active = False
        return new_state

    async def _session_reset_reducer(self, state: AppState, action: Action) -> AppState:
        """Handle session reset."""
        new_state = deepcopy(state)
        new_state.session.messages = []
        new_state.session.input_history = []
        new_state.tokens.input_tokens = 0
        new_state.tokens.output_tokens = 0
        new_state.errors.current_error = None
        return new_state

    async def _message_add_reducer(self, state: AppState, action: Action) -> AppState:
        """Handle message add."""
        new_state = deepcopy(state)
        message = action.payload.get("message", {})
        new_state.session.messages.append(message)
        return new_state

    async def _message_clear_reducer(self, state: AppState, action: Action) -> AppState:
        """Handle message clear."""
        new_state = deepcopy(state)
        new_state.session.messages = []
        return new_state

    async def _ui_mode_change_reducer(self, state: AppState, action: Action) -> AppState:
        """Handle UI mode change."""
        new_state = deepcopy(state)
        new_state.ui.mode = action.payload.get("mode", "normal")
        new_state.ui.vim_mode = action.payload.get("vim_mode", "normal")
        return new_state

    async def _ui_theme_change_reducer(self, state: AppState, action: Action) -> AppState:
        """Handle theme change."""
        new_state = deepcopy(state)
        new_state.ui.theme = action.payload.get("theme", "dark")
        return new_state

    async def _input_set_reducer(self, state: AppState, action: Action) -> AppState:
        """Handle input set."""
        new_state = deepcopy(state)
        new_state.custom["input"] = action.payload.get("input", "")
        return new_state

    async def _input_clear_reducer(self, state: AppState, action: Action) -> AppState:
        """Handle input clear."""
        new_state = deepcopy(state)
        new_state.custom["input"] = ""
        return new_state

    async def _tool_call_start_reducer(self, state: AppState, action: Action) -> AppState:
        """Handle tool call start."""
        new_state = deepcopy(state)
        tool_id = action.payload.get("tool_id", "")
        tool_name = action.payload.get("tool_name", "")
        new_state.tools.active_tools[tool_id] = {
            "name": tool_name,
            "start_time": action.timestamp,
            "status": "running",
        }
        return new_state

    async def _tool_call_end_reducer(self, state: AppState, action: Action) -> AppState:
        """Handle tool call end."""
        new_state = deepcopy(state)
        tool_id = action.payload.get("tool_id", "")
        if tool_id in new_state.tools.active_tools:
            tool_info = new_state.tools.active_tools.pop(tool_id)
            tool_info["end_time"] = action.timestamp
            tool_info["status"] = "completed"
            tool_info["result"] = action.payload.get("result", "")
            new_state.tools.tool_history.append(tool_info)
            new_state.tools.last_tool_result = tool_info
        return new_state

    async def _token_update_reducer(self, state: AppState, action: Action) -> AppState:
        """Handle token update."""
        new_state = deepcopy(state)
        new_state.tokens.input_tokens = action.payload.get("input_tokens", 0)
        new_state.tokens.output_tokens = action.payload.get("output_tokens", 0)
        new_state.tokens.last_estimate = action.timestamp
        return new_state

    async def _error_set_reducer(self, state: AppState, action: Action) -> AppState:
        """Handle error set."""
        new_state = deepcopy(state)
        error = action.payload.get("error", "")
        new_state.errors.current_error = error
        new_state.errors.error_history.append({
            "error": error,
            "timestamp": action.timestamp,
            "source": action.source,
        })
        return new_state

    async def _error_clear_reducer(self, state: AppState, action: Action) -> AppState:
        """Handle error clear."""
        new_state = deepcopy(state)
        new_state.errors.current_error = None
        return new_state

    async def _loading_start_reducer(self, state: AppState, action: Action) -> AppState:
        """Handle loading start."""
        new_state = deepcopy(state)
        new_state.loading.is_loading = True
        new_state.loading.loading_message = action.payload.get("message", "")
        new_state.loading.loading_operations.append(action.payload.get("operation", ""))
        return new_state

    async def _loading_end_reducer(self, state: AppState, action: Action) -> AppState:
        """Handle loading end."""
        new_state = deepcopy(state)
        operation = action.payload.get("operation", "")
        if operation in new_state.loading.loading_operations:
            new_state.loading.loading_operations.remove(operation)
        if not new_state.loading.loading_operations:
            new_state.loading.is_loading = False
            new_state.loading.loading_message = ""
        return new_state

    async def _config_update_reducer(self, state: AppState, action: Action) -> AppState:
        """Handle config update."""
        new_state = deepcopy(state)
        for key, value in action.payload.items():
            if hasattr(new_state.config, key):
                setattr(new_state.config, key, value)
            else:
                new_state.config.custom[key] = value
        return new_state

    async def _task_create_reducer(self, state: AppState, action: Action) -> AppState:
        """Handle task create."""
        new_state = deepcopy(state)
        task_id = action.payload.get("task_id", 0)
        new_state.tasks.tasks[task_id] = {
            "subject": action.payload.get("subject", ""),
            "description": action.payload.get("description", ""),
            "status": "pending",
            "created_at": action.timestamp,
        }
        return new_state

    async def _task_update_reducer(self, state: AppState, action: Action) -> AppState:
        """Handle task update."""
        new_state = deepcopy(state)
        task_id = action.payload.get("task_id", 0)
        if task_id in new_state.tasks.tasks:
            for key, value in action.payload.items():
                if key != "task_id":
                    new_state.tasks.tasks[task_id][key] = value
        return new_state

    async def _task_delete_reducer(self, state: AppState, action: Action) -> AppState:
        """Handle task delete."""
        new_state = deepcopy(state)
        task_id = action.payload.get("task_id", 0)
        new_state.tasks.tasks.pop(task_id, None)
        return new_state


# Selectors - Derived state queries
class Selectors:
    """Selectors for derived state."""

    @staticmethod
    def get_messages(state: AppState) -> List[Dict[str, Any]]:
        """Get all messages."""
        return state.session.messages

    @staticmethod
    def get_last_message(state: AppState) -> Optional[Dict[str, Any]]:
        """Get last message."""
        if state.session.messages:
            return state.session.messages[-1]
        return None

    @staticmethod
    def get_token_usage_percent(state: AppState) -> float:
        """Get token usage percentage."""
        if state.tokens.max_input_tokens == 0:
            return 0.0
        return state.tokens.input_tokens / state.tokens.max_input_tokens

    @staticmethod
    def is_token_warning(state: AppState) -> bool:
        """Check if token usage exceeds warning threshold."""
        return Selectors.get_token_usage_percent(state) > state.tokens.warning_threshold

    @staticmethod
    def get_active_tools(state: AppState) -> Dict[str, Dict[str, Any]]:
        """Get active tools."""
        return state.tools.active_tools

    @staticmethod
    def get_pending_permissions(state: AppState) -> Dict[str, Dict[str, Any]]:
        """Get pending permissions."""
        return state.tools.pending_permissions

    @staticmethod
    def get_connected_mcp_servers(state: AppState) -> List[str]:
        """Get connected MCP servers."""
        return state.mcp.connected_servers

    @staticmethod
    def get_current_error(state: AppState) -> Optional[str]:
        """Get current error."""
        return state.errors.current_error

    @staticmethod
    def is_loading(state: AppState) -> bool:
        """Check if loading."""
        return state.loading.is_loading

    @staticmethod
    def get_vim_mode(state: AppState) -> str:
        """Get vim mode."""
        return state.ui.vim_mode

    @staticmethod
    def get_config(state: AppState) -> Dict[str, Any]:
        """Get config."""
        return {
            "model": state.config.model,
            "max_tokens": state.config.max_tokens,
            "temperature": state.config.temperature,
        }

    @staticmethod
    def get_pending_tasks(state: AppState) -> Dict[int, Dict[str, Any]]:
        """Get pending tasks."""
        return {
            k: v for k, v in state.tasks.tasks.items()
            if v.get("status") == "pending"
        }

    @staticmethod
    def get_active_task(state: AppState) -> Optional[int]:
        """Get active task ID."""
        return state.tasks.active_task


# Global store
_store: Optional[Store] = None


def get_store() -> Store:
    """Get global store."""
    global _store
    if _store is None:
        _store = Store()
    return _store


def create_store(initial_state: AppState = None) -> Store:
    """Create new store."""
    return Store(initial_state)


# Action creators
def create_action(action_type: ActionType, payload: Dict[str, Any] = None, source: str = "system") -> Action:
    """Create action."""
    return Action(
        type=action_type,
        payload=payload or {},
        source=source,
    )


async def dispatch_action(action_type: ActionType, payload: Dict[str, Any] = None) -> AppState:
    """Dispatch action to global store."""
    store = get_store()
    action = create_action(action_type, payload)
    return await store.dispatch(action)


# Import submodules
from .hooks import (
    StateHook,
    use_state,
    use_selector,
    use_dispatch,
    use_effect,
    use_store,
    use_messages,
    use_last_message,
    use_token_usage,
    use_loading,
    use_error,
    use_vim_mode,
    use_ui_state,
    use_config,
    use_active_tools,
    use_pending_permissions,
    use_mcp_servers,
    use_tasks,
    use_pending_tasks,
    set_ui_mode,
    set_ui_theme,
    set_input,
    clear_input,
    set_error,
    clear_error,
    start_loading,
    end_loading,
    update_tokens,
    add_message,
    clear_messages,
)

from .persistence import (
    StatePersistence,
    get_persistence,
    save_current_state,
    load_saved_state,
    save_current_session,
    load_session_state,
    list_saved_sessions,
    restore_session,
)


__all__ = [
    # Core
    "ActionType",
    "Action",
    "AppState",
    "SessionState",
    "UIState",
    "ToolState",
    "ContextState",
    "MCPState",
    "ConfigState",
    "TaskStateSlice",
    "TokenState",
    "ErrorState",
    "LoadingState",
    "Store",
    "Selectors",
    "get_store",
    "create_store",
    "create_action",
    "dispatch_action",
    # Hooks
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
    # Persistence
    "StatePersistence",
    "get_persistence",
    "save_current_state",
    "load_saved_state",
    "save_current_session",
    "load_session_state",
    "list_saved_sessions",
    "restore_session",
]