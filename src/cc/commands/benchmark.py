"""Benchmark Command - Performance benchmarking."""

from __future__ import annotations
import asyncio
import time
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table



def run_benchmark(console: Console, target: Optional[str] = None, iterations: int = 10) -> None:
    """Run benchmark command."""
    console.print("[bold]Performance Benchmarks[/bold]\n")

    if target == "tools":
        benchmark_tools(console, iterations)
    elif target == "api":
        benchmark_api(console, iterations)
    elif target == "memory":
        benchmark_memory(console)
    elif target == "startup":
        benchmark_startup(console)
    else:
        run_all_benchmarks(console, iterations)


def benchmark_tools(console: Console, iterations: int) -> None:
    """Benchmark tool execution."""
    console.print("[cyan]Tool Execution Benchmarks[/cyan]")

    from ..types.tool import ToolUseContext
    from ..tools.bash import BashTool
    from ..tools.read import ReadTool

    ctx = ToolUseContext(cwd="/tmp", session_id="bench")

    results = []

    # Bash benchmark
    bash = BashTool()
    times = []
    for _ in range(iterations):
        start = time.time()
        asyncio.run(bash.execute({"command": "echo test"}, ctx))
        times.append(time.time() - start)

    avg_time = sum(times) / len(times)
    results.append(("Bash (echo)", avg_time * 1000))

    # Read benchmark (existing file)
    read = ReadTool()
    test_file = Path("/tmp/bench_test.txt")
    test_file.write_text("test content\n" * 100)

    times = []
    for _ in range(iterations):
        start = time.time()
        asyncio.run(read.execute({"file_path": str(test_file)}, ctx))
        times.append(time.time() - start)

    avg_time = sum(times) / len(times)
    results.append(("Read (100 lines)", avg_time * 1000))

    # Display results
    table = Table(title="Tool Benchmarks")
    table.add_column("Tool", style="cyan")
    table.add_column("Avg Time (ms)")

    for tool, time_ms in results:
        table.add_row(tool, f"{time_ms:.2f}")

    console.print(table)

    test_file.unlink(missing_ok=True)


def benchmark_api(console: Console, iterations: int) -> None:
    """Benchmark API calls."""
    console.print("[cyan]API Benchmarks[/cyan]")
    console.print("[dim]API benchmark requires actual API connection[/dim]")

    # Simulated results
    table = Table(title="API Benchmarks (Simulated)")
    table.add_column("Operation", style="cyan")
    table.add_column("Avg Time (ms)")

    table.add_row("Single request", "~500")
    table.add_row("Streaming response", "~100/s")
    table.add_row("Tool call round", "~300")

    console.print(table)


def benchmark_memory(console: Console) -> None:
    """Benchmark memory usage."""
    console.print("[cyan]Memory Benchmarks[/cyan]")

    import sys

    # Check memory of common objects
    from ..types.message import UserMessage, TextBlock
    from ..types.tool import ToolResult

    results = []

    # Message memory
    msg = UserMessage(role="user", content=[TextBlock(text="test")])
    results.append(("UserMessage", sys.getsizeof(msg)))

    # Tool result memory
    result = ToolResult(content="test output")
    results.append(("ToolResult", sys.getsizeof(result)))

    # Display results
    table = Table(title="Memory Benchmarks")
    table.add_column("Object", style="cyan")
    table.add_column("Size (bytes)")

    for obj, size in results:
        table.add_row(obj, str(size))

    console.print(table)


def benchmark_startup(console: Console) -> None:
    """Benchmark startup time."""
    console.print("[cyan]Startup Benchmarks[/cyan]")

    # Measure import times
    import_times = []

    modules = [
        "cc.types",
        "cc.tools",
        "cc.services",
        "cc.core",
    ]

    for module in modules:
        start = time.time()
        __import__(module)
        elapsed = time.time() - start
        import_times.append((module, elapsed * 1000))

    table = Table(title="Import Benchmarks")
    table.add_column("Module", style="cyan")
    table.add_column("Import Time (ms)")

    for module, time_ms in import_times:
        table.add_row(module, f"{time_ms:.2f}")

    console.print(table)


def run_all_benchmarks(console: Console, iterations: int) -> None:
    """Run all benchmarks."""
    benchmark_tools(console, iterations)
    console.print()
    benchmark_api(console, iterations)
    console.print()
    benchmark_memory(console)
    console.print()
    benchmark_startup(console)


__all__ = ["run_benchmark"]