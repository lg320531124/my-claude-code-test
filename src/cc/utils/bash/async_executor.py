"""Async Bash Executor - Async subprocess execution."""

from __future__ import annotations
import asyncio
import os
import signal
from typing import Dict, Any, Optional, List, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ...utils.log import get_logger

logger = get_logger(__name__)


class ExecutionStatus(Enum):
    """Execution status."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class ExecutionConfig:
    """Execution configuration."""
    timeout: float = 30.0
    cwd: Optional[Path] = None
    env: Optional[Dict[str, str]] = None
    capture_output: bool = True
    shell: bool = True
    input: Optional[str] = None
    uid: Optional[int] = None
    gid: Optional[int] = None


@dataclass
class ExecutionResult:
    """Execution result."""
    status: ExecutionStatus
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration: float = 0.0
    pid: Optional[int] = None
    command: str = ""
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AsyncBashExecutor:
    """Execute bash commands asynchronously."""

    def __init__(self, config: Optional[ExecutionConfig] = None):
        self.config = config or ExecutionConfig()
        self._processes: Dict[int, asyncio.subprocess.Process] = {}
        self._cancelled: List[int] = []

    async def execute(
        self,
        command: str,
        config: Optional[ExecutionConfig] = None
    ) -> ExecutionResult:
        """Execute command."""
        use_config = config or self.config

        start_time = asyncio.get_event_loop().time()

        try:
            # Create subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE if use_config.capture_output else None,
                stderr=asyncio.subprocess.PIPE if use_config.capture_output else None,
                stdin=asyncio.subprocess.PIPE if use_config.input else None,
                cwd=str(use_config.cwd) if use_config.cwd else None,
                env=use_config.env or os.environ,
            )

            self._processes[process.pid] = process

            # Wait with timeout
            stdout = b""
            stderr = b""
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(use_config.input.encode() if use_config.input else None),
                    timeout=use_config.timeout
                )
            except asyncio.TimeoutError:
                # Kill process
                process.kill()
                await process.wait()

                return ExecutionResult(
                    status=ExecutionStatus.TIMEOUT,
                    stdout=stdout.decode() if stdout else "",
                    stderr=stderr.decode() if stderr else "",
                    exit_code=-1,
                    duration=use_config.timeout,
                    pid=process.pid,
                    command=command,
                    error="Timeout",
                )

            duration = asyncio.get_event_loop().time() - start_time

            # Clean up
            if process.pid in self._processes:
                del self._processes[process.pid]

            return ExecutionResult(
                status=ExecutionStatus.COMPLETED if process.returncode == 0 else ExecutionStatus.FAILED,
                stdout=stdout.decode() if stdout else "",
                stderr=stderr.decode() if stderr else "",
                exit_code=process.returncode or 0,
                duration=duration,
                pid=process.pid,
                command=command,
            )

        except Exception as e:
            duration = asyncio.get_event_loop().time() - start_time

            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                duration=duration,
                command=command,
                error=str(e),
            )

    async def execute_stream(
        self,
        command: str,
        config: Optional[ExecutionConfig] = None
    ) -> AsyncIterator[str]:
        """Execute with streaming output."""
        use_config = config or self.config

        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(use_config.cwd) if use_config.cwd else None,
            env=use_config.env or os.environ,
        )

        self._processes[process.pid] = process

        # Stream output
        async for line in process.stdout:
            yield line.decode()

        await process.wait()

        if process.pid in self._processes:
            del self._processes[process.pid]

    async def execute_parallel(
        self,
        commands: List[str],
        config: Optional[ExecutionConfig] = None
    ) -> List[ExecutionResult]:
        """Execute multiple commands in parallel."""
        tasks = [
            self.execute(cmd, config)
            for cmd in commands
        ]

        results = await asyncio.gather(*tasks)
        return results

    async def cancel(self, pid: int) -> bool:
        """Cancel running process."""
        process = self._processes.get(pid)

        if process:
            process.kill()
            self._cancelled.append(pid)
            logger.info(f"Cancelled process {pid}")
            return True

        return False

    async def cancel_all(self) -> int:
        """Cancel all running processes."""
        count = 0

        for pid, process in self._processes.items():
            process.kill()
            self._cancelled.append(pid)
            count += 1

        self._processes.clear()
        return count

    def get_running(self) -> List[int]:
        """Get running process IDs."""
        return list(self._processes.keys())

    async def wait_for(
        self,
        pid: int,
        timeout: Optional[float] = None
    ) -> Optional[int]:
        """Wait for process to complete."""
        process = self._processes.get(pid)

        if process:
            try:
                await asyncio.wait_for(process.wait(), timeout=timeout)
                return process.returncode
            except asyncio.TimeoutError:
                return None

        return None

    async def send_signal(
        self,
        pid: int,
        sig: signal.Signals = signal.SIGTERM
    ) -> bool:
        """Send signal to process."""
        process = self._processes.get(pid)

        if process:
            process.send_signal(sig)
            return True

        return False


class BashPool:
    """Pool for bash execution."""

    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self._executor = AsyncBashExecutor()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._results: List[ExecutionResult] = []

    async def execute(
        self,
        command: str,
        priority: int = 0
    ) -> ExecutionResult:
        """Execute with pool limit."""
        async with self._semaphore:
            result = await self._executor.execute(command)
            self._results.append(result)
            return result

    async def execute_batch(
        self,
        commands: List[str]
    ) -> List[ExecutionResult]:
        """Execute batch."""
        tasks = [
            self.execute(cmd)
            for cmd in commands
        ]

        return await asyncio.gather(*tasks)

    def get_results(self) -> List[ExecutionResult]:
        """Get all results."""
        return self._results

    def clear_results(self) -> int:
        """Clear results."""
        count = len(self._results)
        self._results.clear()
        return count


__all__ = [
    "ExecutionStatus",
    "ExecutionConfig",
    "ExecutionResult",
    "AsyncBashExecutor",
    "BashPool",
]