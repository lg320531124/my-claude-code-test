"""Bash Execute - Async command execution."""

from __future__ import annotations
import asyncio
import os
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class ExecuteResult:
    """Execution result."""
    id: str
    command: str
    stdout: str = ""
    stderr: str = ""
    returncode: int = -1
    success: bool = False
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: float = 0.0
    cwd: str = ""
    env: Dict[str, str] = field(default_factory=dict)
    timeout: bool = False
    cancelled: bool = False

    @property
    def output(self) -> str:
        """Combined output."""
        return self.stdout + self.stderr


class BashExecutor:
    """Async bash command executor."""

    def __init__(self):
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._results: Dict[str, ExecuteResult] = {}
        self._default_timeout: float = 120.0

    async def execute(
        self,
        command: str,
        cwd: str = None,
        env: Dict[str, str] = None,
        timeout: float = None,
        capture_output: bool = True,
    ) -> ExecuteResult:
        """Execute command."""
        exec_id = str(uuid.uuid4())[:8]
        result = ExecuteResult(
            id=exec_id,
            command=command,
            cwd=cwd or os.getcwd(),
            env=env or {},
        )
        result.started_at = datetime.now()

        full_env = os.environ.copy()
        full_env.update(env or {})

        timeout_val = timeout or self._default_timeout

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE if capture_output else None,
                stderr=asyncio.subprocess.PIPE if capture_output else None,
                cwd=cwd,
                env=full_env,
            )

            self._processes[exec_id] = proc

            if capture_output:
                try:
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(),
                        timeout=timeout_val,
                    )
                    result.stdout = stdout.decode()
                    result.stderr = stderr.decode()
                except asyncio.TimeoutError:
                    result.timeout = True
                    proc.kill()
                    await proc.wait()
                    result.stderr = f"Timeout after {timeout_val}s"
            else:
                await asyncio.wait_for(proc.wait(), timeout=timeout_val)

            result.returncode = proc.returncode
            result.success = proc.returncode == 0

        except asyncio.CancelledError:
            result.cancelled = True
            if exec_id in self._processes:
                proc = self._processes[exec_id]
                proc.kill()
                await proc.wait()

        except Exception as e:
            result.stderr = str(e)
            result.returncode = -1

        finally:
            result.completed_at = datetime.now()
            result.duration = (result.completed_at - result.started_at).total_seconds()
            self._processes.pop(exec_id, None)
            self._results[exec_id] = result

        return result

    def cancel(self, exec_id: str) -> bool:
        """Cancel running process."""
        proc = self._processes.get(exec_id)
        if proc:
            proc.kill()
            return True
        return False

    def get_result(self, exec_id: str) -> Optional[ExecuteResult]:
        """Get result by ID."""
        return self._results.get(exec_id)

    def get_running(self) -> List[str]:
        """Get running execution IDs."""
        return list(self._processes.keys())

    def clear_results(self) -> None:
        """Clear stored results."""
        self._results.clear()


_executor: Optional[BashExecutor] = None

def get_executor() -> BashExecutor:
    """Get global executor."""
    global _executor
    if _executor is None:
        _executor = BashExecutor()
    return _executor

async def run_command(
    command: str,
    cwd: str = None,
    timeout: float = None,
) -> ExecuteResult:
    """Run single command."""
    return await get_executor().execute(command, cwd, timeout=timeout)


__all__ = [
    "ExecuteResult", "BashExecutor", "get_executor", "run_command",
]
