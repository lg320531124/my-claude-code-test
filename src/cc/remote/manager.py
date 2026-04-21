"""Remote Session Manager - Manages remote CCR sessions.

Coordinates WebSocket subscription for receiving messages from CCR,
HTTP POST for sending user messages to CCR, and permission request/response flow.
"""

from __future__ import annotations
import logging
from typing import Any, Callable, Optional, Dict
from dataclasses import dataclass

from .websocket import SessionsWebSocket, SessionsWebSocketCallbacks

logger = logging.getLogger(__name__)


def is_sdk_message(message: Dict[str, Any]) -> bool:
    """Type guard to check if a message is an SDKMessage (not a control message)."""
    return (
        message.get("type") != "control_request"
        and message.get("type") != "control_response"
        and message.get("type") != "control_cancel_request"
    )


@dataclass
class RemotePermissionResponse:
    """Permission response for remote sessions.

    Simplified version of PermissionResult for CCR communication.
    """
    behavior: str  # 'allow' or 'deny'
    updated_input: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

    @classmethod
    def allow(cls, updated_input: Dict[str, Any]) -> "RemotePermissionResponse":
        """Create an allow response."""
        return cls(behavior="allow", updated_input=updated_input)

    @classmethod
    def deny(cls, message: str) -> "RemotePermissionResponse":
        """Create a deny response."""
        return cls(behavior="deny", message=message)


@dataclass
class RemoteSessionConfig:
    """Configuration for a remote session."""
    session_id: str
    get_access_token: Callable[[], str]
    org_uuid: str
    has_initial_prompt: bool = False
    viewer_only: bool = False


@dataclass
class RemoteSessionCallbacks:
    """Callbacks for remote session events."""
    on_message: Callable[[Dict[str, Any]], None]
    on_permission_request: Callable[[Dict[str, Any], str], None]
    on_permission_cancelled: Optional[Callable[[str, Optional[str]], None]] = None
    on_connected: Optional[Callable[[], None]] = None
    on_disconnected: Optional[Callable[[], None]] = None
    on_reconnecting: Optional[Callable[[], None]] = None
    on_error: Optional[Callable[[Exception], None]] = None


class RemoteSessionManager:
    """Manages a remote CCR session.

    Coordinates:
    - WebSocket subscription for receiving messages from CCR
    - HTTP POST for sending user messages to CCR
    - Permission request/response flow
    """

    def __init__(
        self,
        config: RemoteSessionConfig,
        callbacks: RemoteSessionCallbacks,
    ) -> None:
        self.config = config
        self.callbacks = callbacks

        self._websocket: Optional[SessionsWebSocket] = None
        self._pending_permission_requests: Dict[str, Dict[str, Any]] = {}

    def connect(self) -> None:
        """Connect to the remote session via WebSocket."""
        logger.debug(f"[RemoteSessionManager] Connecting to session {self.config.session_id}")

        def on_connected():
            logger.debug("[RemoteSessionManager] Connected")
            if self.callbacks.on_connected:
                self.callbacks.on_connected()

        def on_close():
            logger.debug("[RemoteSessionManager] Disconnected")
            if self.callbacks.on_disconnected:
                self.callbacks.on_disconnected()

        def on_reconnecting():
            logger.debug("[RemoteSessionManager] Reconnecting")
            if self.callbacks.on_reconnecting:
                self.callbacks.on_reconnecting()

        def on_error(e: Exception):
            logger.error(f"[RemoteSessionManager] Error: {e}")
            if self.callbacks.on_error:
                self.callbacks.on_error(e)

        ws_callbacks = SessionsWebSocketCallbacks(
            on_message=self._handle_message,
            on_connected=on_connected,
            on_close=on_close,
            on_reconnecting=on_reconnecting,
            on_error=on_error,
        )

        self._websocket = SessionsWebSocket(
            self.config.session_id,
            self.config.org_uuid,
            self.config.get_access_token,
            ws_callbacks,
        )

        import asyncio
        asyncio.create_task(self._websocket.connect())

    def _handle_message(self, message: Dict[str, Any]) -> None:
        """Handle messages from WebSocket."""
        msg_type = message.get("type")

        # Handle control requests (permission prompts from CCR)
        if msg_type == "control_request":
            self._handle_control_request(message)
            return

        # Handle control cancel requests
        if msg_type == "control_cancel_request":
            request_id = message.get("request_id")
            pending_request = self._pending_permission_requests.get(request_id)
            logger.debug(f"[RemoteSessionManager] Permission request cancelled: {request_id}")
            self._pending_permission_requests.pop(request_id, None)
            if self.callbacks.on_permission_cancelled:
                self.callbacks.on_permission_cancelled(
                    request_id,
                    pending_request.get("tool_use_id") if pending_request else None,
                )
            return

        # Handle control responses (acknowledgments)
        if msg_type == "control_response":
            logger.debug("[RemoteSessionManager] Received control response")
            return

        # Forward SDK messages to callback
        if is_sdk_message(message):
            self.callbacks.on_message(message)

    def _handle_control_request(self, request: Dict[str, Any]) -> None:
        """Handle control requests from CCR (e.g., permission requests)."""
        request_id = request.get("request_id")
        inner = request.get("request", {})
        subtype = inner.get("subtype")

        if subtype == "can_use_tool":
            logger.debug(f"[RemoteSessionManager] Permission request for tool: {inner.get('tool_name')}")
            self._pending_permission_requests[request_id] = inner
            self.callbacks.on_permission_request(inner, request_id)
        else:
            # Send an error response for unrecognized subtypes
            logger.debug(f"[RemoteSessionManager] Unsupported control request subtype: {subtype}")
            response = {
                "type": "control_response",
                "response": {
                    "subtype": "error",
                    "request_id": request_id,
                    "error": f"Unsupported control request subtype: {subtype}",
                },
            }
            self._websocket.send_control_response(response) if self._websocket else None

    async def send_message(
        self,
        content: Dict[str, Any],
        opts: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send a user message to the remote session via HTTP POST."""
        logger.debug(f"[RemoteSessionManager] Sending message to session {self.config.session_id}")

        # This would use send_event_to_remote_session in TS
        # For Python, implement HTTP POST to CCR API
        import aiohttp

        access_token = self.config.get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        url = f"https://api.anthropic.com/v1/sessions/{self.config.session_id}/events"

        payload = {"content": content}
        if opts and "uuid" in opts:
            payload["uuid"] = opts["uuid"]

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        return True
                    logger.error(f"[RemoteSessionManager] Failed to send: {resp.status}")
                    return False
        except Exception as e:
            logger.error(f"[RemoteSessionManager] Failed to send message: {e}")
            return False

    def respond_to_permission_request(
        self,
        request_id: str,
        result: RemotePermissionResponse,
    ) -> None:
        """Respond to a permission request from CCR."""
        pending_request = self._pending_permission_requests.get(request_id)
        if not pending_request:
            logger.error(f"[RemoteSessionManager] No pending permission request with ID: {request_id}")
            return

        self._pending_permission_requests.pop(request_id, None)

        response = {
            "type": "control_response",
            "response": {
                "subtype": "success",
                "request_id": request_id,
                "response": {
                    "behavior": result.behavior,
                    **(
                        {"updated_input": result.updated_input}
                        if result.behavior == "allow"
                        else {"message": result.message}
                    ),
                },
            },
        }

        logger.debug(f"[RemoteSessionManager] Sending permission response: {result.behavior}")
        self._websocket.send_control_response(response) if self._websocket else None

    def is_connected(self) -> bool:
        """Check if connected to the remote session."""
        return self._websocket.is_connected() if self._websocket else False

    def cancel_session(self) -> None:
        """Send an interrupt signal to cancel the current request."""
        logger.debug("[RemoteSessionManager] Sending interrupt signal")
        self._websocket.send_control_request({"subtype": "interrupt"}) if self._websocket else None

    def get_session_id(self) -> str:
        """Get the session ID."""
        return self.config.session_id

    async def disconnect(self) -> None:
        """Disconnect from the remote session."""
        logger.debug("[RemoteSessionManager] Disconnecting")
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
        self._pending_permission_requests.clear()

    async def reconnect(self) -> None:
        """Force reconnect the WebSocket."""
        logger.debug("[RemoteSessionManager] Reconnecting WebSocket")
        if self._websocket:
            await self._websocket.reconnect()


def create_remote_session_config(
    session_id: str,
    get_access_token: Callable[[], str],
    org_uuid: str,
    has_initial_prompt: bool = False,
    viewer_only: bool = False,
) -> RemoteSessionConfig:
    """Create a remote session config."""
    return RemoteSessionConfig(
        session_id=session_id,
        get_access_token=get_access_token,
        org_uuid=org_uuid,
        has_initial_prompt=has_initial_prompt,
        viewer_only=viewer_only,
    )