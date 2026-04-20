"""async_process - 异步子进程封装

使用 asyncio.subprocess 实现异步命令执行。
"""

from __future__ import annotations
import asyncio
import os
import sys
import signal
from pathlib import Path
from typing import Optional, Union, AsyncIterator, Callable, Any


class ProcessResult:
    """进程执行结果。"""

    stdout: str
    stderr: str
    returncode: int
    duration_ms: float

    def __init__(
        self,
        stdout: str = "",
        stderr: str = "",
        returncode: int = 0,
        duration_ms: float = 0,
    ):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.duration_ms = duration_ms

    def is_success(self) -> bool:
        """检查是否成功。"""
        return self.returncode == 0

    def __repr__(self) -> str:
        return f"ProcessResult(returncode={self.returncode}, stdout={len(self.stdout)}b, stderr={len(self.stderr)}b)"


class AsyncProcess:
    """异步进程管理器。"""

    def __init__(
        self,
        command: str,
        cwd: Optional[Union[str, Path]] = None,
        env: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
        shell: bool = True,
    ):
        self.command = command
        self.cwd = Path(cwd) if cwd else Path.cwd()
        self.env = env or os.environ.copy()
        self.timeout = timeout
        self.shell = shell
        self._process: Optional[asyncio.subprocess.Process] = None
        self._cancelled = False

    async def run(
        self,
        on_stdout: Optional[Callable[[str], None]] = None,
        on_stderr: Optional[Callable[[str], None]] = None,
    ) -> ProcessResult:
        """执行命令。

        Args:
            on_stdout: stdout回调
            on_stderr: stderr回调

        Returns:
            ProcessResult
        """
        import time
        start_time = time.time()

        try:
            # 创建子进程
            if self.shell:
                self._process = await asyncio.create_subprocess_shell(
                    self.command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(self.cwd),
                    env=self.env,
                )
            else:
                # 分割命令为列表
                args = self.command.split() if isinstance(self.command, str) else self.command
                self._process = await asyncio.create_subprocess_exec(
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(self.cwd),
                    env=self.env,
                )

            # 读取输出
            stdout_lines: list[str] = []
            stderr_lines: list[str] = []

            async def read_stream(
                stream: asyncio.StreamReader,
                lines: list[str],
                callback: Optional[Callable[[str], None]],
            ) -> None:
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    decoded = line.decode("utf-8", errors="replace")
                    lines.append(decoded)
                    if callback:
                        callback(decoded.rstrip("\n"))

            # 并行读取stdout和stderr
            tasks = []
            if self._process.stdout:
                tasks.append(read_stream(self._process.stdout, stdout_lines, on_stdout))
            if self._process.stderr:
                tasks.append(read_stream(self._process.stderr, stderr_lines, on_stderr))

            if tasks:
                await asyncio.gather(*tasks)

            # 等待进程结束（带超时）
            if self.timeout:
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=self.timeout)
                except asyncio.TimeoutError:
                    self._cancelled = True
                    await self.kill()
                    return ProcessResult(
                        stdout="".join(stdout_lines),
                        stderr="".join(stderr_lines) + "\nProcess timed out",
                        returncode=-1,
                        duration_ms=(time.time() - start_time) * 1000,
                    )
            else:
                await self._process.wait()

            duration_ms = (time.time() - start_time) * 1000

            return ProcessResult(
                stdout="".join(stdout_lines),
                stderr="".join(stderr_lines),
                returncode=self._process.returncode or 0,
                duration_ms=duration_ms,
            )

        except Exception as e:
            return ProcessResult(
                stdout="",
                stderr=str(e),
                returncode=-1,
                duration_ms=(time.time() - start_time) * 1000,
            )

    async def run_streaming(
        self,
        merge_stderr: bool = False,
    ) -> AsyncIterator[str]:
        """流式执行命令，逐行输出。

        Args:
            merge_stderr: 是否合并stderr到stdout

        Yields:
            输出行
        """
        if self.shell:
            self._process = await asyncio.create_subprocess_shell(
                self.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE if not merge_stderr else asyncio.subprocess.STDOUT,
                cwd=str(self.cwd),
                env=self.env,
            )
        else:
            args = self.command.split() if isinstance(self.command, str) else self.command
            self._process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE if not merge_stderr else asyncio.subprocess.STDOUT,
                cwd=str(self.cwd),
                env=self.env,
            )

        if self._process.stdout:
            while True:
                line = await self._process.stdout.readline()
                if not line:
                    break
                yield line.decode("utf-8", errors="replace")

        await self._process.wait()

    async def kill(self) -> None:
        """终止进程。"""
        if self._process and self._process.returncode is None:
            try:
                # 发送SIGTERM
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except asyncio.TimeoutError:
                # 强制SIGKILL
                self._process.kill()
                await self._process.wait()

    async def terminate(self) -> None:
        """优雅终止进程。"""
        if self._process and self._process.returncode is None:
            self._process.terminate()
            await self._process.wait()

    def is_running(self) -> bool:
        """检查进程是否运行中。"""
        return self._process is not None and self._process.returncode is None

    @property
    def pid(self) -> Optional[int]:
        """获取进程PID。"""
        return self._process.pid if self._process else None


async def run_command_async(
    command: str,
    cwd: Optional[Union[str, Path]] = None,
    env: Optional[dict[str, str]] = None,
    timeout: Optional[float] = None,
    shell: bool = True,
) -> ProcessResult:
    """快速执行命令。

    Args:
        command: 命令字符串
        cwd: 工作目录
        env: 环境变量
        timeout: 超时时间（秒）
        shell: 是否使用shell执行

    Returns:
        ProcessResult
    """
    proc = AsyncProcess(command, cwd, env, timeout, shell)
    return await proc.run()


async def run_command_streaming(
    command: str,
    cwd: Optional[Union[str, Path]] = None,
    env: Optional[dict[str, str]] = None,
    merge_stderr: bool = False,
) -> AsyncIterator[str]:
    """流式执行命令。

    Args:
        command: 命令字符串
        cwd: 工作目录
        env: 环境变量
        merge_stderr: 合并stderr

    Yields:
        输出行
    """
    proc = AsyncProcess(command, cwd, env)
    async for line in proc.run_streaming(merge_stderr):
        yield line


async def run_commands_parallel(
    commands: list[str],
    cwd: Optional[Union[str, Path]] = None,
    env: Optional[dict[str, str]] = None,
    timeout: Optional[float] = None,
) -> list[ProcessResult]:
    """并行执行多个命令。

    Args:
        commands: 命令列表
        cwd: 工作目录
        env: 环境变量
        timeout: 超时时间

    Returns:
        结果列表
    """
    tasks = [run_command_async(cmd, cwd, env, timeout) for cmd in commands]
    return await asyncio.gather(*tasks)


async def run_command_with_retry(
    command: str,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    cwd: Optional[Union[str, Path]] = None,
    env: Optional[dict[str, str]] = None,
    timeout: Optional[float] = None,
) -> ProcessResult:
    """带重试的命令执行。

    Args:
        command: 命令字符串
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）
        cwd: 工作目录
        env: 环境变量
        timeout: 超时时间

    Returns:
        ProcessResult
    """
    for attempt in range(max_retries + 1):
        result = await run_command_async(command, cwd, env, timeout)

        if result.is_success():
            return result

        if attempt < max_retries:
            await asyncio.sleep(retry_delay)

    return result


async def run_background(
    command: str,
    cwd: Optional[Union[str, Path]] = None,
    env: Optional[dict[str, str]] = None,
) -> AsyncProcess:
    """后台运行命令（不等待完成）。

    Args:
        command: 命令字符串
        cwd: 工作目录
        env: 环境变量

    Returns:
        AsyncProcess实例（可用于后续监控）
    """
    proc = AsyncProcess(command, cwd, env)

    # 创建进程但不等待
    proc._process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(proc.cwd),
        env=proc.env,
    )

    return proc


async def check_command_available(command: str) -> bool:
    """检查命令是否可用。

    Args:
        command: 命令名称

    Returns:
        是否可用
    """
    result = await run_command_async(f"which {command}" if sys.platform != "win32" else f"where {command}")
    return result.is_success()


async def get_pid_by_name(process_name: str) -> list[int]:
    """根据进程名获取PID列表。

    Args:
        process_name: 进程名

    Returns:
        PID列表
    """
    if sys.platform == "win32":
        result = await run_command_async(f'tasklist /FI "IMAGENAME eq {process_name}" /FO CSV')
        # 解析CSV输出获取PID
        pids = []
        for line in result.stdout.split("\n"):
            if process_name in line:
                parts = line.split(",")
                if len(parts) >= 2:
                    pid = parts[1].strip('"')
                    try:
                        pids.append(int(pid))
                    except ValueError:
                        pass
        return pids
    else:
        result = await run_command_async(f"pgrep {process_name}")
        pids = []
        for line in result.stdout.strip().split("\n"):
            if line:
                try:
                    pids.append(int(line))
                except ValueError:
                    pass
        return pids


__all__ = [
    "ProcessResult",
    "AsyncProcess",
    "run_command_async",
    "run_command_streaming",
    "run_commands_parallel",
    "run_command_with_retry",
    "run_background",
    "check_command_available",
    "get_pid_by_name",
]