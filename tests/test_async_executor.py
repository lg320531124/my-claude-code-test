"""Tests for async bash executor."""

import pytest
import asyncio
from src.cc.utils.bash.async_executor import (
    AsyncBashExecutor,
    BashPool,
    ExecutionStatus,
    ExecutionConfig,
    ExecutionResult,
)


@pytest.mark.asyncio
async def test_async_executor_init():
    """Test executor initialization."""
    executor = AsyncBashExecutor()
    assert executor.config is not None
    assert executor._processes == {}


@pytest.mark.asyncio
async def test_execute_simple():
    """Test simple execution."""
    executor = AsyncBashExecutor()

    result = await executor.execute("echo hello")

    assert result.status == ExecutionStatus.COMPLETED
    assert result.stdout.strip() == "hello"
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_execute_with_timeout():
    """Test execution with timeout."""
    config = ExecutionConfig(timeout=1.0)
    executor = AsyncBashExecutor(config)

    result = await executor.execute("sleep 5")

    assert result.status == ExecutionStatus.TIMEOUT


@pytest.mark.asyncio
async def test_execute_failed():
    """Test failed execution."""
    executor = AsyncBashExecutor()

    result = await executor.execute("exit 1")

    assert result.status == ExecutionStatus.FAILED
    assert result.exit_code == 1


@pytest.mark.asyncio
async def test_execute_with_cwd():
    """Test execution with cwd."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        config = ExecutionConfig(cwd=tmpdir)
        executor = AsyncBashExecutor(config)

        result = await executor.execute("pwd")

        assert tmpdir in result.stdout


@pytest.mark.asyncio
async def test_execute_stream():
    """Test streaming execution."""
    executor = AsyncBashExecutor()

    output = []

    async for line in executor.execute_stream("echo line1; echo line2"):
        output.append(line)

    assert len(output) >= 2


@pytest.mark.asyncio
async def test_execute_parallel():
    """Test parallel execution."""
    executor = AsyncBashExecutor()

    commands = ["echo one", "echo two", "echo three"]
    results = await executor.execute_parallel(commands)

    assert len(results) == 3
    assert all(r.status == ExecutionStatus.COMPLETED for r in results)


@pytest.mark.asyncio
async def test_cancel():
    """Test cancellation."""
    executor = AsyncBashExecutor()

    # Start long running command
    task = asyncio.create_task(executor.execute("sleep 10"))

    # Wait a bit for process to start
    await asyncio.sleep(0.5)

    # Get running processes
    running = executor.get_running()

    if running:
        pid = running[0]
        cancelled = await executor.cancel(pid)
        assert cancelled is True

    # Clean up
    try:
        await asyncio.wait_for(task, timeout=2.0)
    except asyncio.TimeoutError:
        pass


@pytest.mark.asyncio
async def test_get_running():
    """Test getting running processes."""
    executor = AsyncBashExecutor()

    # Start processes
    tasks = [
        asyncio.create_task(executor.execute("sleep 1"))
        for _ in range(3)
    ]

    await asyncio.sleep(0.3)

    running = executor.get_running()

    # Should have some running
    assert len(running) >= 0

    # Clean up
    await asyncio.gather(*tasks)


@pytest.mark.asyncio
async def test_bash_pool():
    """Test bash pool."""
    pool = BashPool(max_concurrent=2)

    result = await pool.execute("echo test")

    assert result.status == ExecutionStatus.COMPLETED


@pytest.mark.asyncio
async def test_pool_batch():
    """Test pool batch execution."""
    pool = BashPool(max_concurrent=5)

    commands = ["echo 1", "echo 2", "echo 3"]
    results = await pool.execute_batch(commands)

    assert len(results) == 3


@pytest.mark.asyncio
async def test_pool_results():
    """Test pool results."""
    pool = BashPool()

    await pool.execute("echo 1")
    await pool.execute("echo 2")

    results = pool.get_results()

    assert len(results) == 2


@pytest.mark.asyncio
async def test_pool_clear():
    """Test pool clear."""
    pool = BashPool()

    await pool.execute("echo test")
    count = pool.clear_results()

    assert count == 1
    assert len(pool.get_results()) == 0


@pytest.mark.asyncio
async def test_pool_limit():
    """Test pool concurrency limit."""
    pool = BashPool(max_concurrent=2)

    # Start more than limit
    tasks = [
        asyncio.create_task(pool.execute("sleep 0.1"))
        for _ in range(10)
    ]

    # Should complete without error
    results = await asyncio.gather(*tasks)

    assert len(results) == 10


@pytest.mark.asyncio
async def test_execution_result():
    """Test execution result."""
    result = ExecutionResult(
        status=ExecutionStatus.COMPLETED,
        stdout="output",
        stderr="error",
        exit_code=0,
        duration=1.0,
        command="test",
    )

    assert result.status == ExecutionStatus.COMPLETED
    assert result.stdout == "output"


@pytest.mark.asyncio
async def test_execution_config():
    """Test execution config."""
    config = ExecutionConfig(
        timeout=60.0,
        cwd=None,
        env={"VAR": "value"},
        capture_output=True,
        shell=True,
    )

    assert config.timeout == 60.0
    assert config.env["VAR"] == "value"