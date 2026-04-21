"""Sessions WebSocket - WebSocket client for CCR sessions.

WebSocket client for connecting to CCR sessions via /v1/sessions/ws/{id}/subscribe
"""

from __future__ import annotations
import asyncio
import json
import uuid
from typing import Any, Callable, Optional, Dict, Set
from enum import Enum
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

RECONNECT_DELAY_MS = 2000
MAX_RECONNECT_ATTEMPTS = 5
PING_INTERVAL_MS = 30000
MAX_SESSION_NOT_FOUND_RETRIES = 3

PERMANENT_CLOSE_CODES: Set[int] = {4003}  # unauthorized


class WebSocketState(Enum):
    """WebSocket connection state."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    CLOSED = "closed"


@dataclass
class SessionsWebSocketCallbacks:
    """Callbacks for WebSocket events."""
    on_message: Callable[[Dict[str, Any]], None]
    on_close: Optional[Callable[[], None]] = None
    on_error: Optional[Callable[[Exception], None]] = None
    on_connected: Optional[Callable[[], None]] = None
    on_reconnecting: Optional[Callable[[], None]] = None


def is_sessions_message(value: Any) -> bool:
    """Check if value is a valid sessions message."""
    if not isinstance(value, dict) or "type" not in value:
        return False
    return isinstance(value["type"], str)


class SessionsWebSocket:
    """WebSocket client for connecting to CCR sessions.

    Protocol:
    1. Connect to wss://api.anthropic.com/v1/sessions/ws/{sessionId}/subscribe?organization_uuid=...
    2. Send auth message: { type: 'auth', credential: { type: 'oauth', token: '...' } }
    3. Receive SDKMessage stream from the session
    """

    def __init__(
        self,
        session_id: str,
        org_uuid: str,
        get_access_token: Callable[[], str],
        callbacks: SessionsWebSocketCallbacks,
    ) -> None:
        self.session_id = session_id
        self.org_uuid = org_uuid
        self.get_access_token = get_access_token
        self.callbacks = callbacks

        self._ws: Any = None
        self._state: WebSocketState = WebSocketState.CLOSED
        self._reconnect_attempts: int = 0
        self._session_not_found_retries: int = 0
        self._ping_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        self._base_url: str = "wss://api.anthropic.com"

    async def connect(self) -> None:
        """Connect to the sessions WebSocket endpoint."""
        if self._state == WebSocketState.CONNECTING:
            logger.debug("[SessionsWebSocket] Already connecting")
            return

        self._state = WebSocketState.CONNECTING

        url = f"{self._base_url}/v1/sessions/ws/{self.session_id}/subscribe?organization_uuid={self.org_uuid}"
        logger.debug(f"[SessionsWebSocket] Connecting to {url}")

        access_token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "anthropic-version": "2023-06-01",
        }

        try:
            import websockets
            self._ws = await websockets.connect(
                url,
                extra_headers=headers,
                ping_interval=PING_INTERVAL_MS / 1000,
                ping_timeout=10,
            )

            logger.debug("[SessionsWebSocket] Connection opened")
            self._state = WebSocketState.CONNECTED
            self._reconnect_attempts = 0
            self._session_not_found_retries = 0
            self._start_ping_interval()
            if self.callbacks.on_connected:
                self.callbacks.on_connected()

            # Start message listener
            asyncio.create_task(self._listen_messages())

        except ImportError:
            logger.warning("[SessionsWebSocket] websockets library not available")
            self._state = WebSocketState.CLOSED
            if self.callbacks.on_error:
                self.callbacks.on_error(Exception("websockets library not installed"))
        except Exception as e:
            logger.error(f"[SessionsWebSocket] Connection error: {e}")
            self._state = WebSocketState.CLOSED
            if self.callbacks.on_error:
                self.callbacks.on_error(e)
            self._handle_close(1006)  # Abnormal close

    async def _listen_messages(self) -> None:
        """Listen for incoming WebSocket messages."""
        if not self._ws:
            return

        try:
            async for data in self._ws:
                await self._handle_message(data)
        except Exception as e:
            if self._state != WebSocketState.CLOSED:
                logger.error(f"[SessionsWebSocket] Message error: {e}")
                if self.callbacks.on_error:
                    self.callbacks.on_error(e)
                self._handle_close(1006)

    async def _handle_message(self, data: str) -> None:
        """Handle incoming WebSocket message."""
        try:
            message = json.loads(data)

            if is_sessions_message(message):
                self.callbacks.on_message(message)
            else:
                msg_type = message.get("type", "unknown") if isinstance(message, dict) else "unknown"
                logger.debug(f"[SessionsWebSocket] Ignoring message type: {msg_type}")

        except json.JSONDecodeError as e:
            logger.error(f"[SessionsWebSocket] Failed to parse message: {e}")

    def _handle_close(self, close_code: int) -> None:
        """Handle WebSocket close."""
        self._stop_ping_interval()

        if self._state == WebSocketState.CLOSED:
            return

        self._ws = None
        previous_state = self._state
        self._state = WebSocketState.CLOSED

        # Permanent codes: stop reconnecting
        if close_code in PERMANENT_CLOSE_CODES:
            logger.debug(f"[SessionsWebSocket] Permanent close code {close_code}, not reconnecting")
            if self.callbacks.on_close:
                self.callbacks.on_close()
            return

        # 4001 (session not found) can be transient
        if close_code == 4001:
            self._session_not_found_retries += 1
            if self._session_not_found_retries > MAX_SESSION_NOT_FOUND_RETRIES:
                logger.debug("[SessionsWebSocket] 4001 retry budget exhausted")
                if self.callbacks.on_close:
                    self.callbacks.on_close()
                return
            self._schedule_reconnect(
                RECONNECT_DELAY_MS * self._session_not_found_retries / 1000,
                f"4001 attempt {self._session_not_found_retries}/{MAX_SESSION_NOT_FOUND_RETRIES}",
            )
            return

        # Attempt reconnection if we were connected
        if previous_state == WebSocketState.CONNECTED and self._reconnect_attempts < MAX_RECONNECT_ATTEMPTS:
            self._reconnect_attempts += 1
            self._schedule_reconnect(
                RECONNECT_DELAY_MS / 1000,
                f"attempt {self._reconnect_attempts}/{MAX_RECONNECT_ATTEMPTS}",
            )
        else:
            logger.debug("[SessionsWebSocket] Not reconnecting")
            if self.callbacks.on_close:
                self.callbacks.on_close()

    def _schedule_reconnect(self, delay: float, label: str) -> None:
        """Schedule a reconnect attempt."""
        if self.callbacks.on_reconnecting:
            self.callbacks.on_reconnecting()
        logger.debug(f"[SessionsWebSocket] Scheduling reconnect ({label}) in {delay}s")

        async def do_reconnect():
            await asyncio.sleep(delay)
            await self.connect()

        self._reconnect_task = asyncio.create_task(do_reconnect())

    def _start_ping_interval(self) -> None:
        """Start ping interval."""
        self._stop_ping_interval()

        async def ping_loop():
            while self._ws and self._state == WebSocketState.CONNECTED:
                try:
                    await asyncio.sleep(PING_INTERVAL_MS / 1000)
                    if self._ws:
                        await self._ws.ping()
                except Exception:
                    pass  # Ignore ping errors

        self._ping_task = asyncio.create_task(ping_loop())

    def _stop_ping_interval(self) -> None:
        """Stop ping interval."""
        if self._ping_task:
            self._ping_task.cancel()
            self._ping_task = None

    def send_control_response(self, response: Dict[str, Any]) -> None:
        """Send a control response back to the session."""
        if not self._ws or self._state != WebSocketState.CONNECTED:
            logger.error("[SessionsWebSocket] Cannot send: not connected")
            return

        logger.debug("[SessionsWebSocket] Sending control response")
        asyncio.create_task(self._ws.send(json.dumps(response)))

    def send_control_request(self, request: Dict[str, Any]) -> None:
        """Send a control request to the session (e.g., interrupt)."""
        if not self._ws or self._state != WebSocketState.CONNECTED:
            logger.error("[SessionsWebSocket] Cannot send: not connected")
            return

        control_request = {
            "type": "control_request",
            "request_id": str(uuid.uuid4()),
            "request": request,
        }

        logger.debug(f"[SessionsWebSocket] Sending control request: {request.get('subtype')}")
        asyncio.create_task(self._ws.send(json.dumps(control_request)))

    def is_connected(self) -> bool:
        """Check if connected."""
        return self._state == WebSocketState.CONNECTED

    async def close(self) -> None:
        """Close the WebSocket connection."""
        logger.debug("[SessionsWebSocket] Closing connection")
        self._state = WebSocketState.CLOSED
        self._stop_ping_interval()

        if self._reconnect_task:
            self._reconnect_task.cancel()
            self._reconnect_task = None

        if self._ws:
            await self._ws.close()
            self._ws = None

    async def reconnect(self) -> None:
        """Force reconnect."""
        logger.debug("[SessionsWebSocket] Force reconnecting")
        self._reconnect_attempts = 0
        self._session_not_found_retries = 0
        await self.close()

        await asyncio.sleep(0.5)
        await self.connect()