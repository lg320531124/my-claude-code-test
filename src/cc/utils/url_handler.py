"""URL Handler - URL parsing, validation, and manipulation utilities."""

from __future__ import annotations
import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode, quote, unquote


class URLScheme(Enum):
    """URL schemes."""
    HTTP = "http"
    HTTPS = "https"
    FTP = "ftp"
    FILE = "file"
    MAILTO = "mailto"
    WS = "ws"
    WSS = "wss"


class URLStatus(Enum):
    """URL validation status."""
    VALID = "valid"
    INVALID = "invalid"
    UNKNOWN_SCHEME = "unknown_scheme"
    MISSING_HOST = "missing_host"
    MALFORMED = "malformed"


@dataclass
class URLInfo:
    """Parsed URL information."""
    scheme: str
    host: str
    port: Optional[int] = None
    path: str = ""
    query: Dict[str, List[str]] = field(default_factory=dict)
    fragment: str = ""
    username: Optional[str] = None
    password: Optional[str] = None
    original: str = ""
    status: URLStatus = URLStatus.VALID
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_secure(self) -> bool:
        """Check if URL uses secure scheme."""
        return self.scheme in ("https", "wss")

    @property
    def default_port(self) -> Optional[int]:
        """Get default port for scheme."""
        defaults = {
            "http": 80,
            "https": 443,
            "ftp": 21,
            "ws": 80,
            "wss": 443,
        }
        return defaults.get(self.scheme)

    @property
    def effective_port(self) -> int:
        """Get effective port (explicit or default)."""
        if self.port is not None:
            return self.port
        return self.default_port or 0

    def rebuild(self) -> str:
        """Rebuild URL from components."""
        netloc = self.host
        if self.port and self.port != self.default_port:
            netloc = f"{netloc}:{self.port}"
        if self.username:
            if self.password:
                netloc = f"{quote(self.username)}:{quote(self.password)}@{netloc}"
            else:
                netloc = f"{quote(self.username)}@{netloc}"

        query_str = ""
        if self.query:
            query_str = urlencode(self.query, doseq=True)

        return urlunparse((
            self.scheme,
            netloc,
            self.path,
            "",  # params (deprecated)
            query_str,
            self.fragment,
        ))


@dataclass
class URLConfig:
    """URL handler configuration."""
    allowed_schemes: List[str] = field(default_factory=lambda: ["http", "https", "ftp", "file"])
    max_length: int = 2048
    allow_credentials: bool = True
    allow_private_hosts: bool = True
    validate_dns: bool = False


class URLHandler:
    """Handle URL parsing and validation."""

    # URL pattern
    URL_PATTERN = re.compile(
        r"^(?P<scheme>[a-zA-Z][a-zA-Z0-9+.-]*):"
        r"(?P<authority>//[^/?#]*)?"
        r"(?P<path>[^?#]*)?"
        r"(?:\?(?P<query>[^#]*))?"
        r"(?:#(?P<fragment>.*))?$"
    )

    # Private host patterns
    PRIVATE_HOSTS = [
        r"^localhost$",
        r"^127\.",
        r"^10\.",
        r"^172\.1[6-9]\.",
        r"^172\.2[0-9]\.",
        r"^172\.3[0-1]\.",
        r"^192\.168\.",
        r"^::1$",
        r"^fc00:",
        r"^fe80:",
    ]

    def __init__(self, config: Optional[URLConfig] = None):
        self.config = config or URLConfig()

    def parse(self, url: str) -> URLInfo:
        """Parse URL into components."""
        self.original = url

        # Check max length
        if len(url) > self.config.max_length:
            return URLInfo(
                scheme="",
                host="",
                original=url,
                status=URLStatus.MALFORMED,
                metadata={"error": "URL exceeds max length"},
            )

        try:
            parsed = urlparse(url)

            # Extract components
            scheme = parsed.scheme.lower()
            host = parsed.hostname or ""
            port = parsed.port

            # Parse query
            query = parse_qs(parsed.query)

            # Check scheme
            if not scheme:
                return URLInfo(
                    scheme="",
                    host=host,
                    original=url,
                    status=URLStatus.MALFORMED,
                    metadata={"error": "Missing scheme"},
                )

            if scheme not in self.config.allowed_schemes:
                return URLInfo(
                    scheme=scheme,
                    host=host,
                    original=url,
                    status=URLStatus.UNKNOWN_SCHEME,
                    metadata={"error": f"Scheme '{scheme}' not allowed"},
                )

            # Check host
            if not host and scheme not in ("file", "mailto"):
                return URLInfo(
                    scheme=scheme,
                    host="",
                    original=url,
                    status=URLStatus.MISSING_HOST,
                    metadata={"error": "Missing host"},
                )

            # Check private hosts
            if not self.config.allow_private_hosts and self._is_private_host(host):
                return URLInfo(
                    scheme=scheme,
                    host=host,
                    original=url,
                    status=URLStatus.INVALID,
                    metadata={"error": "Private host not allowed"},
                )

            return URLInfo(
                scheme=scheme,
                host=host,
                port=port,
                path=parsed.path,
                query=query,
                fragment=parsed.fragment,
                username=parsed.username,
                password=parsed.password,
                original=url,
                status=URLStatus.VALID,
            )

        except Exception as e:
            return URLInfo(
                scheme="",
                host="",
                original=url,
                status=URLStatus.MALFORMED,
                metadata={"error": str(e)},
            )

    def validate(self, url: str) -> bool:
        """Validate URL."""
        info = self.parse(url)
        return info.status == URLStatus.VALID

    def _is_private_host(self, host: str) -> bool:
        """Check if host is private."""
        for pattern in self.PRIVATE_HOSTS:
            if re.match(pattern, host, re.IGNORECASE):
                return True
        return False

    def normalize(self, url: str) -> str:
        """Normalize URL."""
        info = self.parse(url)
        if info.status != URLStatus.VALID:
            return url

        # Normalize path
        path = info.path
        if not path:
            path = "/"

        # Remove default port
        port = info.port
        if port == info.default_port:
            port = None

        # Sort query params
        query = dict(sorted(info.query.items()))

        return URLInfo(
            scheme=info.scheme,
            host=info.host.lower(),
            port=port,
            path=path,
            query=query,
            fragment=info.fragment,
            username=info.username,
            password=info.password,
        ).rebuild()

    def resolve(self, base_url: str, relative_url: str) -> str:
        """Resolve relative URL against base."""
        from urllib.parse import urljoin
        return urljoin(base_url, relative_url)

    def extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text."""
        # Common URL regex
        pattern = r"https?://[^\s<>\"']+"
        return re.findall(pattern, text)

    def build(
        self,
        scheme: str,
        host: str,
        path: str = "",
        query: Optional[Dict[str, str]] = None,
        fragment: str = "",
        port: Optional[int] = None,
    ) -> str:
        """Build URL from components."""
        query_dict = {}
        if query:
            for k, v in query.items():
                query_dict[k] = [v]

        info = URLInfo(
            scheme=scheme,
            host=host,
            port=port,
            path=path,
            query=query_dict,
            fragment=fragment,
        )
        return info.rebuild()

    def add_query(self, url: str, params: Dict[str, str]) -> str:
        """Add query parameters to URL."""
        info = self.parse(url)
        if info.status != URLStatus.VALID:
            return url

        for key, value in params.items():
            if key in info.query:
                info.query[key].append(value)
            else:
                info.query[key] = [value]

        return info.rebuild()

    def remove_query(self, url: str, keys: List[str]) -> str:
        """Remove query parameters from URL."""
        info = self.parse(url)
        if info.status != URLStatus.VALID:
            return url

        for key in keys:
            info.query.pop(key, None)

        return info.rebuild()

    def get_query_value(self, url: str, key: str) -> Optional[str]:
        """Get query parameter value."""
        info = self.parse(url)
        if info.status != URLStatus.VALID:
            return None

        values = info.query.get(key, [])
        return values[0] if values else None

    def encode(self, url: str) -> str:
        """Encode URL."""
        return quote(url, safe=":/?#[]@!$&'()*+,;=")

    def decode(self, url: str) -> str:
        """Decode URL."""
        return unquote(url)

    def get_domain(self, url: str) -> str:
        """Get domain from URL."""
        info = self.parse(url)
        return info.host

    def get_path_segments(self, url: str) -> List[str]:
        """Get path segments."""
        info = self.parse(url)
        segments = info.path.split("/")
        return [s for s in segments if s]

    def is_same_origin(self, url1: str, url2: str) -> bool:
        """Check if two URLs have same origin."""
        info1 = self.parse(url1)
        info2 = self.parse(url2)

        return (
            info1.scheme == info2.scheme
            and info1.host == info2.host
            and info1.effective_port == info2.effective_port
        )


def parse_url(url: str) -> URLInfo:
    """Parse URL with default configuration."""
    handler = URLHandler()
    return handler.parse(url)


def validate_url(url: str) -> bool:
    """Validate URL with default configuration."""
    handler = URLHandler()
    return handler.validate(url)


def normalize_url(url: str) -> str:
    """Normalize URL with default configuration."""
    handler = URLHandler()
    return handler.normalize(url)


def build_url(
    scheme: str,
    host: str,
    path: str = "",
    query: Optional[Dict[str, str]] = None,
) -> str:
    """Build URL from components."""
    handler = URLHandler()
    return handler.build(scheme, host, path, query)


__all__ = [
    "URLScheme",
    "URLStatus",
    "URLInfo",
    "URLConfig",
    "URLHandler",
    "parse_url",
    "validate_url",
    "normalize_url",
    "build_url",
]