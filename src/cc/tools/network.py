"""Network Tool - Network operations."""

from __future__ import annotations
import socket
import asyncio
import httpx
from typing import ClassVar, Optional, List
from pydantic import BaseModel, Field

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class NetworkInput(ToolInput):
    """Input for NetworkTool."""
    action: str = Field(description="Action: ping, resolve, port, check, info")
    host: Optional[str] = Field(default=None, description="Host address")
    port: Optional[int] = Field(default=None, description="Port number")
    timeout: int = Field(default=5000, description="Timeout in milliseconds")


class NetworkTool(ToolDef):
    """Network operations."""

    name: ClassVar[str] = "Network"
    description: ClassVar[str] = "Network diagnostics and operations"
    input_schema: ClassVar[type] = NetworkInput

    async def execute(self, input: NetworkInput, ctx: ToolUseContext) -> ToolResult:
        """Execute network operation."""
        action = input.action

        try:
            if action == "ping":
                return await self._ping(input.host, input.timeout)
            elif action == "resolve":
                return self._resolve(input.host)
            elif action == "port":
                return await self._check_port(input.host, input.port, input.timeout)
            elif action == "check":
                return await self._check_url(input.host, input.timeout)
            elif action == "info":
                return self._network_info()
            else:
                return ToolResult(
                    content=f"Unknown action: {action}",
                    is_error=True,
                )
        except Exception as e:
            return ToolResult(
                content=f"Network error: {e}",
                is_error=True,
            )

    async def _ping(self, host: Optional[str], timeout: int) -> ToolResult:
        """Ping host (TCP ping)."""
        if not host:
            return ToolResult(content="Host required", is_error=True)

        # Resolve first
        try:
            ip = socket.gethostbyname(host)
        except socket.gaierror:
            return ToolResult(content=f"Cannot resolve host: {host}", is_error=True)

        # TCP ping to port 80
        start = asyncio.get_event_loop().time()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, 80),
                timeout=timeout / 1000,
            )
            duration = (asyncio.get_event_loop().time() - start) * 1000
            writer.close()
            await writer.wait_closed()

            return ToolResult(
                content=f"Ping to {host} ({ip}): {duration:.1f}ms",
                metadata={"host": host, "ip": ip, "duration_ms": duration},
            )
        except asyncio.TimeoutError:
            return ToolResult(
                content=f"Ping to {host}: timeout after {timeout}ms",
                is_error=True,
            )

    def _resolve(self, host: Optional[str]) -> ToolResult:
        """Resolve hostname."""
        if not host:
            return ToolResult(content="Host required", is_error=True)

        try:
            # Get all addresses
            info = socket.getaddrinfo(host, None)
            addresses = [addr[4][0] for addr in info]
            unique_addresses = list(set(addresses))

            # Get canonical name
            try:
                cname = socket.getfqdn(host)
            except Exception:
                cname = host

            result = f"Host: {host}\n"
            result += f"Canonical: {cname}\n"
            result += f"Addresses:\n"
            for addr in unique_addresses:
                result += f"  {addr}\n"

            return ToolResult(
                content=result,
                metadata={"host": host, "cname": cname, "addresses": unique_addresses},
            )
        except socket.gaierror:
            return ToolResult(
                content=f"Cannot resolve: {host}",
                is_error=True,
            )

    async def _check_port(self, host: Optional[str], port: Optional[int], timeout: int) -> ToolResult:
        """Check if port is open."""
        if not host or not port:
            return ToolResult(content="Host and port required", is_error=True)

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout / 1000,
            )
            writer.close()
            await writer.wait_closed()

            return ToolResult(
                content=f"Port {port} on {host}: OPEN",
                metadata={"host": host, "port": port, "status": "open"},
            )
        except asyncio.TimeoutError:
            return ToolResult(
                content=f"Port {port} on {host}: TIMEOUT",
                metadata={"host": host, "port": port, "status": "timeout"},
            )
        except Exception:
            return ToolResult(
                content=f"Port {port} on {host}: CLOSED",
                metadata={"host": host, "port": port, "status": "closed"},
            )

    async def _check_url(self, url: Optional[str], timeout: int) -> ToolResult:
        """Check URL accessibility."""
        if not url:
            return ToolResult(content="URL required", is_error=True)

        # Add scheme if missing
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            async with httpx.AsyncClient(timeout=timeout / 1000) as client:
                response = await client.get(url, follow_redirects=True)

            return ToolResult(
                content=f"URL: {url}\nStatus: {response.status_code}\nContent-Type: {response.headers.get('content-type', 'unknown')}",
                metadata={
                    "url": url,
                    "status": response.status_code,
                    "content_type": response.headers.get("content-type"),
                    "size": len(response.content),
                },
            )
        except httpx.TimeoutException:
            return ToolResult(content=f"URL check timeout: {url}", is_error=True)
        except Exception as e:
            return ToolResult(content=f"URL check failed: {e}", is_error=True)

    def _network_info(self) -> ToolResult:
        """Get local network info."""
        info = {
            "hostname": socket.gethostname(),
            "fqdn": socket.getfqdn(),
        }

        # Get local addresses
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
            info["local_ip"] = local_ip
        except Exception:
            info["local_ip"] = "unknown"

        # Try to get all interfaces (limited info without extra libs)
        info["interfaces"] = []

        result = f"Network Info:\n"
        result += f"  Hostname: {info['hostname']}\n"
        result += f"  FQDN: {info['fqdn']}\n"
        result += f"  Local IP: {info['local_ip']}\n"

        return ToolResult(content=result, metadata=info)


__all__ = ["NetworkTool", "NetworkInput"]