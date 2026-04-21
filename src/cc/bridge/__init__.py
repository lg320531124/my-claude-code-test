"""Bridge Module - REPL process communication bridge.

Async bridge for communication between REPL process and main process.
Provides messaging, permission callbacks, and status management.
"""

from __future__ import annotations
import asyncio
import json
from typing import Dict, Any, Optional, Callable, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class BridgeStatus(Enum):
    """Bridge connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class BridgeMessageType(Enum):
    """Bridge message types."""
    QUERY = "query"
    RESPONSE = "response"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    PERMISSION_REQUEST = "permission_request"
    PERMISSION_RESPONSE = "permission_response"
    STATUS_UPDATE = "status_update"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


@dataclass
class BridgeMessage:
    """Bridge message structure."""
    type: BridgeMessageType
    id: str
    data: Dict[str, Any]
    timestamp: float = 0.0
    source: str = "main"
    target: str = "repl"


@dataclass
class BridgeConfig:
    """Bridge configuration."""
    transport_type: str = "socket"  # socket, file, pipe
    socket_path: Optional[str] = None
    buffer_size: int = 65536
    timeout_ms: int = 30000
    retry_count: int = 3
    retry_delay_ms: int = 1000
    enable_debug: bool = False
    enable_permission_bridge: bool = True


class BridgeAPI:
    """Bridge API for sending/receiving messages."""

    def __init__(self, config: BridgeConfig = None):
        self.config = config or BridgeConfig()
        self._status = BridgeStatus.DISCONNECTED
        self._message_handlers: Dict[BridgeMessageType, Callable] = {}
        self._pending_responses: Dict[str, asyncio.Future] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None

    def get_status(self) -> BridgeStatus:
        """Get current bridge status."""
        return self._status

    async def connect(self) -> bool:
        """Connect to bridge."""
        self._status = BridgeStatus.CONNECTING

        try:
            if self.config.transport_type == "socket":
                await self._connect_socket()
            elif self.config.transport_type == "file":
                await self._connect_file()
            else:
                await self._connect_pipe()

            self._status = BridgeStatus.CONNECTED
            return True

        except Exception as e:
            self._status = BridgeStatus.ERROR
            return False

    async def _connect_socket(self) -> None:
        """Connect via Unix socket."""
        socket_path = self.config.socket_path or "/tmp/claude_bridge.sock"

        # Try to connect as client
        try:
            reader, writer = await asyncio.open_unix_connection(socket_path)
            self._reader = reader
            self._writer = writer
        except:
            # Start as server
            server = await asyncio.start_server(
                self._handle_connection,
                path=socket_path,
            )
            asyncio.create_task(server.serve_forever())

    async def _connect_file(self) -> None:
        """Connect via file-based messaging."""
        # Would implement file-based IPC
        pass

    async def _connect_pipe(self) -> None:
        """Connect via stdio pipe."""
        # Use stdin/stdout for messaging
        pass

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ) -> None:
        """Handle incoming connection."""
        self._reader = reader
        self._writer = writer

        # Start message loop
        asyncio.create_task(self._message_loop())

    async def _message_loop(self) -> None:
        """Process incoming messages."""
        while self._status == BridgeStatus.CONNECTED:
            try:
                # Read message
                data = await self._reader.read(65536)
                if not data:
                    break

                message = self._parse_message(data)

                # Handle message
                await self._handle_message(message)

            except Exception as e:
                if self.config.enable_debug:
                    print(f"Bridge error: {e}")
                break

        self._status = BridgeStatus.DISCONNECTED

    def _parse_message(self, data: bytes) -> BridgeMessage:
        """Parse incoming message."""
        try:
            obj = json.loads(data.decode())
            return BridgeMessage(
                type=BridgeMessageType(obj.get("type", "query")),
                id=obj.get("id", ""),
                data=obj.get("data", {}),
                timestamp=obj.get("timestamp", 0.0),
                source=obj.get("source", ""),
                target=obj.get("target", ""),
            )
        except json.JSONDecodeError:
            return BridgeMessage(
                type=BridgeMessageType.ERROR,
                id="",
                data={"error": "Invalid message format"},
            )

    async def _handle_message(self, message: BridgeMessage) -> None:
        """Handle incoming message."""
        # Check for pending response
        if message.id in self._pending_responses:
            future = self._pending_responses.pop(message.id)
            future.set_result(message)
            return

        # Call registered handler
        handler = self._message_handlers.get(message.type)
        if handler:
            if asyncio.iscoroutinefunction(handler):
                response = await handler(message)
            else:
                response = handler(message)

            # Send response if needed
            if response:
                await self.send(response)

    async def send(self, message: BridgeMessage) -> None:
        """Send message through bridge."""
        if self._status != BridgeStatus.CONNECTED:
            raise Exception("Bridge not connected")

        data = json.dumps({
            "type": message.type.value,
            "id": message.id,
            "data": message.data,
            "timestamp": message.timestamp,
            "source": message.source,
            "target": message.target,
        }).encode()

        self._writer.write(data)
        await self._writer.drain()

    async def send_and_wait(
        self,
        message: BridgeMessage,
        timeout: float = 30.0
    ) -> Optional[BridgeMessage]:
        """Send message and wait for response."""
        future = asyncio.get_event_loop().create_future()
        self._pending_responses[message.id] = future

        await self.send(message)

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending_responses.pop(message.id, None)
            return None

    def register_handler(
        self,
        message_type: BridgeMessageType,
        handler: Callable
    ) -> None:
        """Register message handler."""
        self._message_handlers[message_type] = handler

    def unregister_handler(self, message_type: BridgeMessageType) -> None:
        """Unregister message handler."""
        self._message_handlers.pop(message_type, None)

    async def disconnect(self) -> None:
        """Disconnect bridge."""
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()

        self._status = BridgeStatus.DISCONNECTED


class BridgeMessaging:
    """Bridge messaging utilities."""

    def __init__(self, api: BridgeAPI):
        self.api = api

    async def send_query(self, prompt: str, context: Dict = None) -> str:
        """Send query and get response."""
        message = BridgeMessage(
            type=BridgeMessageType.QUERY,
            id=self._generate_id(),
            data={"prompt": prompt, "context": context or {}},
        )

        response = await self.api.send_and_wait(message)

        if response:
            return response.data.get("response", "")
        return ""

    async def send_tool_call(
        self,
        tool_name: str,
        tool_input: Dict
    ) -> Dict:
        """Send tool call request."""
        message = BridgeMessage(
            type=BridgeMessageType.TOOL_CALL,
            id=self._generate_id(),
            data={"name": tool_name, "input": tool_input},
        )

        response = await self.api.send_and_wait(message)

        if response:
            return response.data.get("result", {})
        return {}

    async def request_permission(
        self,
        tool_name: str,
        tool_input: Dict,
        context: Dict = None
    ) -> bool:
        """Request permission through bridge."""
        message = BridgeMessage(
            type=BridgeMessageType.PERMISSION_REQUEST,
            id=self._generate_id(),
            data={
                "tool_name": tool_name,
                "tool_input": tool_input,
                "context": context or {},
            },
        )

        response = await self.api.send_and_wait(message)

        if response:
            return response.data.get("allowed", False)
        return False

    def _generate_id(self) -> str:
        """Generate unique message ID."""
        import uuid
        return str(uuid.uuid4())


class BridgePermissionCallbacks:
    """Bridge-based permission callbacks."""

    def __init__(self, messaging: BridgeMessaging):
        self.messaging = messaging
        self._pending_permissions: Dict[str, asyncio.Future] = {}

    async def check_permission(
        self,
        tool_name: str,
        tool_input: Dict,
        context: Dict = None
    ) -> Dict[str, Any]:
        """Check permission via bridge."""
        request_id = self._generate_request_id()

        # Create future for response
        future = asyncio.get_event_loop().create_future()
        self._pending_permissions[request_id] = future

        # Send request
        allowed = await self.messaging.request_permission(
            tool_name, tool_input, context
        )

        return {
            "allowed": allowed,
            "request_id": request_id,
        }

    async def wait_for_permission_response(
        self,
        request_id: str,
        timeout: float = 60.0
    ) -> bool:
        """Wait for permission response."""
        if request_id not in self._pending_permissions:
            return False

        future = self._pending_permissions[request_id]

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending_permissions.pop(request_id, None)
            return False

    def grant_permission(self, request_id: str) -> None:
        """Grant pending permission."""
        if request_id in self._pending_permissions:
            future = self._pending_permissions.pop(request_id)
            future.set_result(True)

    def deny_permission(self, request_id: str) -> None:
        """Deny pending permission."""
        if request_id in self._pending_permissions:
            future = self._pending_permissions.pop(request_id)
            future.set_result(False)

    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        import uuid
        return str(uuid.uuid4())


class BridgeStatusUtil:
    """Bridge status utilities."""

    def __init__(self, api: BridgeAPI):
        self.api = api

    def is_connected(self) -> bool:
        """Check if bridge is connected."""
        return self.api.get_status() == BridgeStatus.CONNECTED

    def get_status_text(self) -> str:
        """Get status as text."""
        status = self.api.get_status()
        texts = {
            BridgeStatus.DISCONNECTED: "Disconnected",
            BridgeStatus.CONNECTING: "Connecting...",
            BridgeStatus.CONNECTED: "Connected",
            BridgeStatus.ERROR: "Error",
        }
        return texts.get(status, "Unknown")

    async def ping(self) -> bool:
        """Ping bridge to check connectivity."""
        message = BridgeMessage(
            type=BridgeMessageType.PING,
            id="ping",
            data={},
        )

        try:
            response = await self.api.send_and_wait(message, timeout=5.0)
            return response and response.type == BridgeMessageType.PONG
        except:
            return False


class BridgeUI:
    """Bridge UI integration."""

    def __init__(self, api: BridgeAPI):
        self.api = api
        self._ui_callbacks: Dict[str, Callable] = {}

    def register_ui_callback(self, event: str, callback: Callable) -> None:
        """Register UI event callback."""
        self._ui_callbacks[event] = callback

    async def notify_ui(self, event: str, data: Dict) -> None:
        """Notify UI of event."""
        callback = self._ui_callbacks.get(event)
        if callback:
            if asyncio.iscoroutinefunction(callback):
                await callback(data)
            else:
                callback(data)

    async def send_status_update(self, status: Dict) -> None:
        """Send status update through bridge."""
        message = BridgeMessage(
            type=BridgeMessageType.STATUS_UPDATE,
            id="status",
            data=status,
        )
        await self.api.send(message)


class BridgeMain:
    """Main bridge coordinator."""

    def __init__(self, config: BridgeConfig = None):
        self.config = config or BridgeConfig()
        self.api = BridgeAPI(config)
        self.messaging = BridgeMessaging(self.api)
        self.permissions = BridgePermissionCallbacks(self.messaging)
        self.status_util = BridgeStatusUtil(self.api)
        self.ui = BridgeUI(self.api)

    async def start(self) -> bool:
        """Start bridge."""
        success = await self.api.connect()
        if success:
            # Register default handlers
            self._register_handlers()
        return success

    def _register_handlers(self) -> None:
        """Register default message handlers."""
        self.api.register_handler(
            BridgeMessageType.PERMISSION_RESPONSE,
            self._handle_permission_response
        )
        self.api.register_handler(
            BridgeMessageType.STATUS_UPDATE,
            self._handle_status_update
        )

    async def _handle_permission_response(self, message: BridgeMessage) -> None:
        """Handle permission response."""
        request_id = message.data.get("request_id")
        allowed = message.data.get("allowed", False)

        if request_id:
            if allowed:
                self.permissions.grant_permission(request_id)
            else:
                self.permissions.deny_permission(request_id)

    async def _handle_status_update(self, message: BridgeMessage) -> None:
        """Handle status update."""
        await self.ui.notify_ui("status", message.data)

    async def stop(self) -> None:
        """Stop bridge."""
        await self.api.disconnect()


__all__ = [
    "BridgeStatus",
    "BridgeMessageType",
    "BridgeMessage",
    "BridgeConfig",
    "BridgeAPI",
    "BridgeMessaging",
    "BridgePermissionCallbacks",
    "BridgeStatusUtil",
    "BridgeUI",
    "BridgeMain",
]