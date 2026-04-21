"""Runtime Types - SDK runtime interfaces and callbacks.

Types that cannot be serialized and include callbacks or methods.
"""

from __future__ import annotations
from typing import Any, Optional, Dict, List, Callable, AsyncGenerator, Union
from dataclasses import dataclass
from pathlib import Path


class AbortError(Exception):
    """Error raised when operation is aborted."""
    pass


@dataclass
class Options:
    """SDK query options."""
    model: Optional[str] = None
    system_prompt: Optional[List[str]] = None
    cwd: Optional[Path] = None
    tools: Optional[List[Any]] = None
    mcp_servers: Optional[Dict[str, Any]] = None
    permission_mode: Optional[str] = None
    max_tokens: Optional[int] = None
    timeout_ms: Optional[int] = None
    stop_sequences: Optional[List[str]] = None
    on_message: Optional[Callable[[Any], None]] = None
    on_tool_use: Optional[Callable[[str, Dict], None]] = None
    on_error: Optional[Callable[[Exception], None]] = None


@dataclass
class InternalOptions(Options):
    """Internal SDK options with additional fields."""
    internal: bool = True
    enable_remote_control: Optional[Dict[str, Any]] = None


@dataclass
class ListSessionsOptions:
    """Options for list_sessions."""
    dir: Optional[str] = None
    limit: int = 50
    offset: int = 0


@dataclass
class GetSessionInfoOptions:
    """Options for get_session_info."""
    dir: Optional[str] = None


@dataclass
class SessionMutationOptions:
    """Options for session mutation operations."""
    dir: Optional[str] = None


@dataclass
class ForkSessionOptions:
    """Options for fork_session."""
    dir: Optional[str] = None
    up_to_message_id: Optional[str] = None
    title: Optional[str] = None


@dataclass
class ForkSessionResult:
    """Result from fork_session."""
    session_id: str


@dataclass
class GetSessionMessagesOptions:
    """Options for get_session_messages."""
    dir: Optional[str] = None
    limit: Optional[int] = None
    offset: int = 0
    include_system_messages: bool = False


@dataclass
class SessionMessage:
    """A single message in a session."""
    role: str
    content: Any
    uuid: Optional[str] = None
    timestamp: Optional[float] = None


@dataclass
class SDKSessionOptions:
    """Options for creating/resuming SDK sessions."""
    model: Optional[str] = None
    cwd: Optional[str] = None
    system_prompt: Optional[List[str]] = None
    tools: Optional[List[Any]] = None
    mcp_servers: Optional[Dict[str, Any]] = None


class Query:
    """SDK Query interface.

    AsyncGenerator that yields SDK messages.
    """

    def __init__(self) -> None:
        self._generator: Optional[AsyncGenerator] = None

    async def __aiter__(self) -> AsyncGenerator[Any, None]:
        """Iterate over query results."""
        if self._generator:
            return self._generator
        raise NotImplementedError("Query not implemented")

    async def __anext__(self) -> Any:
        """Get next result."""
        if self._generator:
            return await self._generator.__anext__()
        raise StopAsyncIteration


class InternalQuery(Query):
    """Internal query with additional methods."""

    def __init__(self) -> None:
        super().__init__()
        self._messages: List[Any] = []

    def messages(self) -> List[Any]:
        """Get accumulated messages."""
        return self._messages


class SDKSession:
    """SDK Session interface for multi-turn conversations."""

    def __init__(self, options: SDKSessionOptions) -> None:
        self.options = options
        self._session_id: Optional[str] = None

    def session_id(self) -> Optional[str]:
        """Get session ID."""
        return self._session_id

    async def prompt(
        self,
        message: str,
        options: Optional[SDKSessionOptions] = None
    ) -> Any:
        """Send a prompt to the session."""
        raise NotImplementedError("SDKSession.prompt not implemented")

    async def close(self) -> None:
        """Close the session."""
        raise NotImplementedError("SDKSession.close not implemented")


@dataclass
class CronTask:
    """A scheduled task from scheduled_tasks.json."""
    id: str
    cron: str
    prompt: str
    created_at: float
    recurring: bool = False


@dataclass
class CronJitterConfig:
    """Cron scheduler tuning knobs."""
    recurring_frac: float = 0.1
    recurring_cap_ms: float = 15000.0
    one_shot_max_ms: float = 90000.0
    one_shot_floor_ms: float = 1000.0
    one_shot_minute_mod: float = 30.0
    recurring_max_age_ms: float = 604800000.0  # 7 days


@dataclass
class ScheduledTaskEvent:
    """Event from scheduled task watcher."""
    type: str  # 'fire' or 'missed'
    task: Optional[CronTask] = None
    tasks: Optional[List[CronTask]] = None


class ScheduledTasksHandle:
    """Handle returned by watch_scheduled_tasks."""

    async def events(self) -> AsyncGenerator[ScheduledTaskEvent, None]:
        """Get event stream."""
        raise NotImplementedError("events not implemented")

    def get_next_fire_time(self) -> Optional[float]:
        """Get next scheduled fire time."""
        raise NotImplementedError("get_next_fire_time not implemented")


# Inbound prompt types for remote control
@dataclass
class InboundPrompt:
    """User message typed on claude.ai."""
    content: Union[str, List[Any]]
    uuid: Optional[str] = None


@dataclass
class ConnectRemoteControlOptions:
    """Options for connect_remote_control."""
    dir: str
    name: Optional[str] = None
    worker_type: Optional[str] = None
    branch: Optional[str] = None
    git_repo_url: Optional[str] = None
    get_access_token: Optional[Callable[[], Optional[str]]] = None
    base_url: str = "https://api.anthropic.com"
    org_uuid: str = ""
    model: str = ""


class RemoteControlHandle:
    """Handle returned by connect_remote_control."""

    session_url: str = ""
    environment_id: str = ""
    bridge_session_id: str = ""

    def write(self, msg: Any) -> None:
        """Write SDK message."""
        raise NotImplementedError("write not implemented")

    def send_result(self) -> None:
        """Send result signal."""
        raise NotImplementedError("send_result not implemented")

    def send_control_request(self, req: Any) -> None:
        """Send control request."""
        raise NotImplementedError("send_control_request not implemented")

    def send_control_response(self, res: Any) -> None:
        """Send control response."""
        raise NotImplementedError("send_control_response not implemented")

    def send_control_cancel_request(self, request_id: str) -> None:
        """Send control cancel request."""
        raise NotImplementedError("send_control_cancel_request not implemented")

    async def inbound_prompts(self) -> AsyncGenerator[InboundPrompt, None]:
        """Get inbound prompt stream."""
        raise NotImplementedError("inbound_prompts not implemented")

    async def control_requests(self) -> AsyncGenerator[Any, None]:
        """Get control request stream."""
        raise NotImplementedError("control_requests not implemented")

    async def permission_responses(self) -> AsyncGenerator[Any, None]:
        """Get permission response stream."""
        raise NotImplementedError("permission_responses not implemented")

    def on_state_change(
        self,
        cb: Callable[[str, Optional[str]], None]
    ) -> None:
        """Register state change callback."""
        raise NotImplementedError("on_state_change not implemented")

    async def teardown(self) -> None:
        """Teardown connection."""
        raise NotImplementedError("teardown not implemented")