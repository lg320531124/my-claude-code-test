"""async_io - 异步文件IO封装

使用 aiofiles 实现异步文件读写操作。
"""

from __future__ import annotations
import asyncio
import os
from pathlib import Path
from typing import Optional, Union, AsyncIterator

try:
    import aiofiles
    import aiofiles.os
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False


async def read_file_async(
    path: Union[str, Path],
    encoding: str = "utf-8",
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> str:
    """异步读取文件内容。

    Args:
        path: 文件路径
        encoding: 编码格式
        limit: 读取行数限制
        offset: 起始行偏移

    Returns:
        文件内容字符串
    """
    path = str(path)

    if AIOFILES_AVAILABLE:
        async with aiofiles.open(path, "r", encoding=encoding) as f:
            if limit is None and offset is None:
                return await f.read()

            lines = []
            line_count = 0
            skip_count = offset or 0

            async for line in f:
                if skip_count > 0:
                    skip_count -= 1
                    continue

                lines.append(line)
                line_count += 1

                if limit and line_count >= limit:
                    break

            return "".join(lines)
    else:
        # 同步fallback
        with open(path, "r", encoding=encoding) as f:
            if limit is None and offset is None:
                return f.read()

            lines = f.readlines()
            if offset:
                lines = lines[offset:]
            if limit:
                lines = lines[:limit]
            return "".join(lines)


async def read_file_binary_async(path: Union[str, Path]) -> bytes:
    """异步读取二进制文件。

    Args:
        path: 文件路径

    Returns:
        二进制内容
    """
    path = str(path)

    if AIOFILES_AVAILABLE:
        async with aiofiles.open(path, "rb") as f:
            return await f.read()
    else:
        with open(path, "rb") as f:
            return f.read()


async def write_file_async(
    path: Union[str, Path],
    content: Union[str, bytes],
    encoding: str = "utf-8",
    mode: str = "w",
) -> None:
    """异步写入文件。

    Args:
        path: 文件路径
        content: 写入内容
        encoding: 编码格式（文本模式）
        mode: 写入模式 ('w' 或 'a')
    """
    path = str(path)

    # 确保父目录存在
    parent = Path(path).parent
    if not parent.exists():
        await mkdir_async(parent)

    if isinstance(content, bytes):
        mode = mode.replace("w", "wb").replace("a", "ab")
        if AIOFILES_AVAILABLE:
            async with aiofiles.open(path, mode) as f:
                await f.write(content)
        else:
            with open(path, mode) as f:
                f.write(content)
    else:
        if AIOFILES_AVAILABLE:
            async with aiofiles.open(path, mode, encoding=encoding) as f:
                await f.write(content)
        else:
            with open(path, mode, encoding=encoding) as f:
                f.write(content)


async def append_file_async(
    path: Union[str, Path],
    content: Union[str, bytes],
    encoding: str = "utf-8",
) -> None:
    """异步追加文件内容。

    Args:
        path: 文件路径
        content: 追加内容
        encoding: 编码格式
    """
    await write_file_async(path, content, encoding, mode="a")


async def mkdir_async(
    path: Union[str, Path],
    parents: bool = True,
    exist_ok: bool = True,
) -> None:
    """异步创建目录。

    Args:
        path: 目录路径
        parents: 是否创建父目录
        exist_ok: 是否允许已存在
    """
    path = Path(path)

    if AIOFILES_AVAILABLE:
        if parents:
            await aiofiles.os.makedirs(str(path), exist_ok=exist_ok)
        else:
            await aiofiles.os.mkdir(str(path))
    else:
        if parents:
            os.makedirs(path, exist_ok=exist_ok)
        else:
            path.mkdir(exist_ok=exist_ok)


async def exists_async(path: Union[str, Path]) -> bool:
    """异步检查路径是否存在。

    Args:
        path: 路径

    Returns:
        是否存在
    """
    path = str(path)

    if AIOFILES_AVAILABLE:
        return await aiofiles.os.path.exists(path)
    else:
        return os.path.exists(path)


async def is_file_async(path: Union[str, Path]) -> bool:
    """异步检查是否为文件。

    Args:
        path: 路径

    Returns:
        是否为文件
    """
    path = str(path)

    if AIOFILES_AVAILABLE:
        return await aiofiles.os.path.isfile(path)
    else:
        return os.path.isfile(path)


async def is_dir_async(path: Union[str, Path]) -> bool:
    """异步检查是否为目录。

    Args:
        path: 路径

    Returns:
        是否为目录
    """
    path = str(path)

    if AIOFILES_AVAILABLE:
        return await aiofiles.os.path.isdir(path)
    else:
        return os.path.isdir(path)


async def stat_async(path: Union[str, Path]) -> os.stat_result:
    """异步获取文件状态。

    Args:
        path: 文件路径

    Returns:
        stat结果
    """
    path = str(path)

    if AIOFILES_AVAILABLE:
        return await aiofiles.os.stat(path)
    else:
        return os.stat(path)


async def remove_async(path: Union[str, Path]) -> None:
    """异步删除文件。

    Args:
        path: 文件路径
    """
    path = str(path)

    if AIOFILES_AVAILABLE:
        await aiofiles.os.remove(path)
    else:
        os.remove(path)


async def rmtree_async(path: Union[str, Path]) -> None:
    """异步删除目录树。

    Args:
        path: 目录路径
    """
    import shutil

    path = str(path)

    # aiofiles 不支持 rmtree，使用同步方式
    await asyncio.get_event_loop().run_in_executor(None, shutil.rmtree, path)


async def list_dir_async(path: Union[str, Path]) -> list[str]:
    """异步列出目录内容。

    Args:
        path: 目录路径

    Returns:
        文件名列表
    """
    path = str(path)

    if AIOFILES_AVAILABLE:
        return await aiofiles.os.listdir(path)
    else:
        return os.listdir(path)


async def copy_file_async(
    src: Union[str, Path],
    dst: Union[str, Path],
) -> None:
    """异步复制文件。

    Args:
        src: 源文件路径
        dst: 目标文件路径
    """
    import shutil

    src = str(src)
    dst = str(dst)

    await asyncio.get_event_loop().run_in_executor(None, shutil.copy2, src, dst)


async def move_file_async(
    src: Union[str, Path],
    dst: Union[str, Path],
) -> None:
    """异步移动文件。

    Args:
        src: 源文件路径
        dst: 目标文件路径
    """
    import shutil

    src = str(src)
    dst = str(dst)

    await asyncio.get_event_loop().run_in_executor(None, shutil.move, src, dst)


async def glob_async(
    pattern: str,
    path: Optional[Union[str, Path]] = None,
) -> list[Path]:
    """异步glob搜索。

    Args:
        pattern: glob模式
        path: 搜索路径（默认当前目录）

    Returns:
        匹配的路径列表
    """
    from pathlib import Path

    base_path = Path(path) if path else Path.cwd()

    # glob是同步操作，使用线程池
    def _glob():
        return list(base_path.glob(pattern))

    return await asyncio.get_event_loop().run_in_executor(None, _glob)


async def read_lines_async(
    path: Union[str, Path],
    encoding: str = "utf-8",
) -> AsyncIterator[str]:
    """异步逐行读取文件。

    Args:
        path: 文件路径
        encoding: 编码格式

    Yields:
        每行内容
    """
    path = str(path)

    if AIOFILES_AVAILABLE:
        async with aiofiles.open(path, "r", encoding=encoding) as f:
            async for line in f:
                yield line
    else:
        with open(path, "r", encoding=encoding) as f:
            for line in f:
                yield line


async def write_lines_async(
    path: Union[str, Path],
    lines: list[str],
    encoding: str = "utf-8",
) -> None:
    """异步写入多行。

    Args:
        path: 文件路径
        lines: 行内容列表
        encoding: 编码格式
    """
    content = "\n".join(lines)
    await write_file_async(path, content, encoding)


async def get_file_size_async(path: Union[str, Path]) -> int:
    """异步获取文件大小。

    Args:
        path: 文件路径

    Returns:
        文件大小（字节）
    """
    stat = await stat_async(path)
    return stat.st_size


async def get_mtime_async(path: Union[str, Path]) -> float:
    """异步获取文件修改时间。

    Args:
        path: 文件路径

    Returns:
        修改时间戳
    """
    stat = await stat_async(path)
    return stat.st_mtime


__all__ = [
    "read_file_async",
    "read_file_binary_async",
    "write_file_async",
    "append_file_async",
    "mkdir_async",
    "exists_async",
    "is_file_async",
    "is_dir_async",
    "stat_async",
    "remove_async",
    "rmtree_async",
    "list_dir_async",
    "copy_file_async",
    "move_file_async",
    "glob_async",
    "read_lines_async",
    "write_lines_async",
    "get_file_size_async",
    "get_mtime_async",
    "AIOFILES_AVAILABLE",
]