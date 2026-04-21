"""async_http - 异步HTTP客户端封装

使用 httpx 实现异步HTTP请求和流式响应。
"""

from __future__ import annotations
import json
import time
from typing import Optional, Union, AsyncIterator, Callable, Any

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


class HTTPResponse:
    """HTTP响应封装。"""

    status_code: int
    headers: dict[str, str]
    content: bytes
    text: str
    duration_ms: float
    url: str

    def __init__(
        self,
        status_code: int = 0,
        headers: dict[str, str] = None,
        content: bytes = b"",
        text: str = "",
        duration_ms: float = 0,
        url: str = "",
    ):
        self.status_code = status_code
        self.headers = headers or {}
        self.content = content
        self.text = text
        self.duration_ms = duration_ms
        self.url = url

    def is_success(self) -> bool:
        """检查是否成功（2xx状态码）。"""
        return 200 <= self.status_code < 300

    def json(self) -> Any:
        """解析JSON响应。"""
        return json.loads(self.text)

    def __repr__(self) -> str:
        return f"HTTPResponse(status_code={self.status_code}, content={len(self.content)}b)"


class AsyncHTTPClient:
    """异步HTTP客户端。"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        headers: Optional[dict[str, str]] = None,
        follow_redirects: bool = True,
        max_redirects: int = 10,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.headers = headers or {}
        self.follow_redirects = follow_redirects
        self.max_redirects = max_redirects
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "AsyncHTTPClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def connect(self) -> None:
        """建立连接。"""
        if HTTPX_AVAILABLE:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self.headers,
                follow_redirects=self.follow_redirects,
                max_redirects=self.max_redirects,
            )

    async def close(self) -> None:
        """关闭连接。"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        method: str,
        url: str,
        params: Optional[dict[str, Any]] = None,
        json_data: Optional[Any] = None,
        data: Optional[Union[bytes, str, dict]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> HTTPResponse:
        """发送HTTP请求。

        Args:
            method: HTTP方法
            url: URL
            params: 查询参数
            json_data: JSON体
            data: 请求体
            headers: 请求头
            timeout: 超时时间

        Returns:
            HTTPResponse
        """
        start_time = time.time()

        if not self._client:
            await self.connect()

        merged_headers = {**self.headers, **(headers or {})}

        try:
            if HTTPX_AVAILABLE and self._client:
                response = await self._client.request(
                    method,
                    url,
                    params=params,
                    json=json_data,
                    data=data,
                    headers=merged_headers,
                    timeout=timeout or self.timeout,
                )

                duration_ms = (time.time() - start_time) * 1000

                return HTTPResponse(
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    content=response.content,
                    text=response.text,
                    duration_ms=duration_ms,
                    url=str(response.url),
                )
            else:
                # 同步fallback (不推荐，仅作为后备)
                import urllib.request
                import urllib.parse

                full_url = url
                if self.base_url:
                    full_url = self.base_url + url

                if params:
                    full_url += "?" + urllib.parse.urlencode(params)

                req = urllib.request.Request(
                    full_url,
                    method=method,
                    headers=merged_headers,
                )

                if json_data:
                    req.data = json.dumps(json_data).encode("utf-8")
                elif data:
                    req.data = data.encode("utf-8") if isinstance(data, str) else data

                with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                    content = resp.read()
                    duration_ms = (time.time() - start_time) * 1000

                    return HTTPResponse(
                        status_code=resp.status,
                        headers=dict(resp.headers),
                        content=content,
                        text=content.decode("utf-8"),
                        duration_ms=duration_ms,
                        url=full_url,
                    )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HTTPResponse(
                status_code=0,
                text=str(e),
                duration_ms=duration_ms,
                url=url,
            )

    async def get(
        self,
        url: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> HTTPResponse:
        """GET请求。"""
        return await self.request("GET", url, params=params, headers=headers, timeout=timeout)

    async def post(
        self,
        url: str,
        json_data: Optional[Any] = None,
        data: Optional[Union[bytes, str, dict]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> HTTPResponse:
        """POST请求。"""
        return await self.request("POST", url, json_data=json_data, data=data, headers=headers, timeout=timeout)

    async def put(
        self,
        url: str,
        json_data: Optional[Any] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> HTTPResponse:
        """PUT请求。"""
        return await self.request("PUT", url, json_data=json_data, headers=headers, timeout=timeout)

    async def delete(
        self,
        url: str,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> HTTPResponse:
        """DELETE请求。"""
        return await self.request("DELETE", url, headers=headers, timeout=timeout)

    async def stream(
        self,
        method: str,
        url: str,
        json_data: Optional[Any] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> AsyncIterator[bytes]:
        """流式请求。

        Args:
            method: HTTP方法
            url: URL
            json_data: JSON体
            headers: 请求头
            timeout: 超时时间

        Yields:
            响应字节块
        """
        if not self._client:
            await self.connect()

        merged_headers = {**self.headers, **(headers or {})}

        if HTTPX_AVAILABLE and self._client:
            async with self._client.stream(
                method,
                url,
                json=json_data,
                headers=merged_headers,
                timeout=timeout or self.timeout,
            ) as response:
                async for chunk in response.aiter_bytes():
                    yield chunk

    async def stream_text(
        self,
        method: str,
        url: str,
        json_data: Optional[Any] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> AsyncIterator[str]:
        """流式文本请求。

        Yields:
            响应文本行
        """
        async for chunk in self.stream(method, url, json_data, headers, timeout):
            yield chunk.decode("utf-8", errors="replace")


async def fetch_url(
    url: str,
    method: str = "GET",
    json_data: Optional[Any] = None,
    headers: Optional[dict[str, str]] = None,
    timeout: float = 30.0,
) -> HTTPResponse:
    """快速HTTP请求。

    Args:
        url: URL
        method: HTTP方法
        json_data: JSON体
        headers: 请求头
        timeout: 超时时间

    Returns:
        HTTPResponse
    """
    client = AsyncHTTPClient(timeout=timeout)
    async with client:
        return await client.request(method, url, json_data=json_data, headers=headers)


async def fetch_json(
    url: str,
    method: str = "GET",
    json_data: Optional[Any] = None,
    headers: Optional[dict[str, str]] = None,
    timeout: float = 30.0,
) -> Any:
    """获取JSON响应。

    Args:
        url: URL
        method: HTTP方法
        json_data: JSON体
        headers: 请求头
        timeout: 超时时间

    Returns:
        JSON解析结果
    """
    response = await fetch_url(url, method, json_data, headers, timeout)
    if response.is_success():
        return response.json()
    raise Exception(f"HTTP error: {response.status_code}")


async def fetch_stream(
    url: str,
    method: str = "POST",
    json_data: Optional[Any] = None,
    headers: Optional[dict[str, str]] = None,
    timeout: float = 60.0,
    on_chunk: Optional[Callable[[bytes], None]] = None,
) -> AsyncIterator[bytes]:
    """流式HTTP请求。

    Args:
        url: URL
        method: HTTP方法
        json_data: JSON体
        headers: 请求头
        timeout: 超时时间
        on_chunk: 响应块回调

    Yields:
        响应字节块
    """
    client = AsyncHTTPClient(timeout=timeout)
    async with client:
        async for chunk in client.stream(method, url, json_data, headers):
            if on_chunk:
                on_chunk(chunk)
            yield chunk


async def fetch_sse_stream(
    url: str,
    method: str = "POST",
    json_data: Optional[Any] = None,
    headers: Optional[dict[str, str]] = None,
    timeout: float = 60.0,
) -> AsyncIterator[dict[str, Any]]:
    """SSE (Server-Sent Events) 流解析。

    Args:
        url: URL
        method: HTTP方法
        json_data: JSON体
        headers: 请求头
        timeout: 超时时间

    Yields:
        SSE事件字典 {"event": str, "data": str, "id": str}
    """
    client = AsyncHTTPClient(timeout=timeout)
    # SSE需要特定headers
    sse_headers = {"Accept": "text/event-stream", "Cache-Control": "no-cache"}
    merged_headers = {**sse_headers, **(headers or {})}

    async with client:
        buffer = ""
        async for chunk in client.stream(method, url, json_data, merged_headers):
            buffer += chunk.decode("utf-8", errors="replace")

            # 解析SSE事件
            while "\n\n" in buffer:
                event_text, buffer = buffer.split("\n\n", 1)
                event = _parse_sse_event(event_text)
                if event:
                    yield event


def _parse_sse_event(text: str) -> Optional[dict[str, Any]]:
    """解析单个SSE事件。"""
    event = {"event": "message", "data": "", "id": ""}

    for line in text.split("\n"):
        if not line or line.startswith(":"):
            continue

        if ":" in line:
            field, value = line.split(":", 1)
            field = field.strip()
            value = value.strip()

            if field == "event":
                event["event"] = value
            elif field == "data":
                event["data"] += value
            elif field == "id":
                event["id"] = value
            elif field == "retry":
                event["retry"] = int(value)

    if event["data"]:
        return event
    return None


async def download_file(
    url: str,
    path: Union[str, "Path"],
    chunk_size: int = 8192,
    on_progress: Optional[Callable[[int, int], None]] = None,
    timeout: float = 300.0,
) -> int:
    """下载文件。

    Args:
        url: URL
        path: 保存路径
        chunk_size: 响应块大小
        on_progress: 进度回调 (bytes_downloaded, total_bytes)
        timeout: 超时时间

    Returns:
        下载字节数
    """
    from .async_io import write_file_async, mkdir_async
    from pathlib import Path

    save_path = Path(path)
    await mkdir_async(save_path.parent)

    client = AsyncHTTPClient(timeout=timeout)
    async with client:
        response = await client.get(url)

        if not response.is_success():
            raise Exception(f"HTTP error: {response.status_code}")

        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0

        # 写入文件
        async with client.stream("GET", url) as stream:
            content = b""
            async for chunk in stream:
                content += chunk
                downloaded += len(chunk)
                if on_progress:
                    on_progress(downloaded, total_size)

            await write_file_async(save_path, content)

        return downloaded


async def upload_file(
    url: str,
    path: Union[str, "Path"],
    field_name: str = "file",
    headers: Optional[dict[str, str]] = None,
    timeout: float = 300.0,
) -> HTTPResponse:
    """上传文件。

    Args:
        url: URL
        path: 文件路径
        field_name: 表单字段名
        headers: 请求头
        timeout: 超时时间

    Returns:
        HTTPResponse
    """
    from .async_io import read_file_binary_async
    from pathlib import Path

    file_path = Path(path)
    content = await read_file_binary_async(file_path)

    client = AsyncHTTPClient(timeout=timeout)
    async with client:
        # multipart/form-data上传
        files = {field_name: (file_path.name, content)}
        return await client.post(url, data=files, headers=headers)


async def check_url_reachable(url: str, timeout: float = 5.0) -> bool:
    """检查URL是否可达。

    Args:
        url: URL
        timeout: 超时时间

    Returns:
        是否可达
    """
    try:
        response = await fetch_url(url, timeout=timeout)
        return response.is_success()
    except Exception:
        return False


async def get_headers(url: str, timeout: float = 10.0) -> dict[str, str]:
    """获取URL响应头（HEAD请求）。

    Args:
        url: URL
        timeout: 超时时间

    Returns:
        响应头字典
    """
    client = AsyncHTTPClient(timeout=timeout)
    async with client:
        response = await client.request("HEAD", url)
        return response.headers


__all__ = [
    "HTTPResponse",
    "AsyncHTTPClient",
    "fetch_url",
    "fetch_json",
    "fetch_stream",
    "fetch_sse_stream",
    "download_file",
    "upload_file",
    "check_url_reachable",
    "get_headers",
    "HTTPX_AVAILABLE",
]