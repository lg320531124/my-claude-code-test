"""Process Tool - Process management."""

from __future__ import annotations
import asyncio
import signal
from typing import ClassVar, Optional, List, Dict, Any
from pydantic import BaseModel, Field

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class ProcessInfo(BaseModel):
    """Process information."""
    pid: int
    name: str
    status: str
    cpu_percent: Optional[float] = None
    memory_percent: Optional[float] = None
    command: Optional[str] = None


class ProcessInput(ToolInput):
    """Input for ProcessTool."""
    action: str = Field(description="Action: list, info, kill, monitor")
    pid: Optional[int] = Field(default=None, description="Process ID")
    signal: str = Field(default="TERM", description="Signal to send: TERM, KILL, INT")
    filter: Optional[str] = Field(default=None, description="Filter by name")


class ProcessTool(ToolDef):
    """Manage system processes."""

    name: ClassVar[str] = "Process"
    description: ClassVar[str] = "List and manage system processes"
    input_schema: ClassVar[type] = ProcessInput

    # Running background processes
    _background_processes: Dict[int, asyncio.subprocess.Process] = {}

    async def execute(self, input: ProcessInput, ctx: ToolUseContext) -> ToolResult:
        """Execute process operation."""
        action = input.action

        if action == "list":
            return self._list_processes(input.filter)
        elif action == "info":
            return self._process_info(input.pid)
        elif action == "kill":
            return self._kill_process(input.pid, input.signal)
        elif action == "monitor":
            return self._monitor_processes()
        else:
            return ToolResult(
                content=f"Unknown action: {action}",
                is_error=True,
            )

    def _list_processes(self, filter: Optional[str]) -> ToolResult:
        """List processes."""
        # Simulated process list (in production, use psutil)
        processes = [
            ProcessInfo(pid=1, name="init", status="running"),
            ProcessInfo(pid=100, name="python", status="running", command="cc"),
            ProcessInfo(pid=200, name="node", status="sleeping"),
        ]

        if filter:
            processes = [p for p in processes if filter.lower() in p.name.lower()]

        lines = ["PID    NAME       STATUS"]
        lines.append("-" * 30)
        for p in processes:
            lines.append(f"{p.pid:<6} {p.name:<10} {p.status}")

        return ToolResult(
            content="\n".join(lines),
            metadata={"count": len(processes)},
        )

    def _process_info(self, pid: Optional[int]) -> ToolResult:
        """Get process info."""
        if pid is None:
            return ToolResult(
                content="PID required for info action",
                is_error=True,
            )

        # Simulated info
        info = ProcessInfo(
            pid=pid,
            name=f"process_{pid}",
            status="running",
            cpu_percent=1.5,
            memory_percent=0.3,
            command="/usr/bin/example",
        )

        return ToolResult(
            content=f"Process {pid}:\n"
            f"  Name: {info.name}\n"
            f"  Status: {info.status}\n"
            f"  CPU: {info.cpu_percent}%\n"
            f"  Memory: {info.memory_percent}%\n"
            f"  Command: {info.command}",
            metadata=info.model_dump(),
        )

    async def _kill_process(self, pid: Optional[int], signal_name: str) -> ToolResult:
        """Kill a process."""
        if pid is None:
            return ToolResult(
                content="PID required for kill action",
                is_error=True,
            )

        # Map signal names
        signals = {
            "TERM": signal.SIGTERM,
            "KILL": signal.SIGKILL,
            "INT": signal.SIGINT,
        }

        sig = signals.get(signal_name.upper(), signal.SIGTERM)

        try:
            # Check if it's a background process we manage
            if pid in self._background_processes:
                proc = self._background_processes[pid]
                proc.terminate()
                del self._background_processes[pid]
                return ToolResult(
                    content=f"Terminated background process {pid}",
                    metadata={"pid": pid, "signal": signal_name},
                )

            # Otherwise, try system kill (requires permission)
            return ToolResult(
                content=f"Signal {signal_name} sent to process {pid} (simulated)",
                metadata={"pid": pid, "signal": signal_name},
            )

        except Exception as e:
            return ToolResult(
                content=f"Error killing process: {e}",
                is_error=True,
            )

    def _monitor_processes(self) -> ToolResult:
        """Monitor background processes."""
        lines = ["Background Processes:"]
        lines.append("-" * 30)

        for pid, proc in self._background_processes.items():
            status = "running" if proc.returncode is None else f"exit({proc.returncode})"
            lines.append(f"{pid}: {status}")

        if not self._background_processes:
            lines.append("No background processes")

        return ToolResult(
            content="\n".join(lines),
            metadata={"count": len(self._background_processes)},
        )

    @classmethod
    def register_background(cls, pid: int, proc: asyncio.subprocess.Process) -> None:
        """Register a background process."""
        cls._background_processes[pid] = proc


__all__ = ["ProcessTool", "ProcessInput", "ProcessInfo"]