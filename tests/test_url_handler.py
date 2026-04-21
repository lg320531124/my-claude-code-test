"""Tests for URL Handler."""

import pytest

from cc.utils.url_handler import (
    URLScheme,
    URLStatus,
    URLInfo,
    URLConfig,
    URLHandler,
    parse_url,
    validate_url,
    normalize_url,
    build_url,
)


class TestURLScheme:
    """Test URLScheme enum."""

    def test_all_schemes(self):
        """Test all scheme types."""
        assert URLScheme.HTTP.value == "http"
        assert URLScheme.HTTPS.value == "https"
        assert URLScheme.FTP.value == "ftp"
        assert URLScheme.FILE.value == "file"


class TestURLStatus:
    """Test URLStatus enum."""

    def test_all_statuses(self):
        """Test all status types."""
        assert URLStatus.VALID.value == "valid"
        assert URLStatus.INVALID.value == "invalid"
        assert URLStatus.UNKNOWN_SCHEME.value == "unknown_scheme"
        assert URLStatus.MISSING_HOST.value == "missing_host"
        assert URLStatus.MALFORMED.value == "malformed"


class TestURLInfo:
    """Test URLInfo."""

    def test_create(self):
        """Test creating URL info."""
        info = URLInfo(
            scheme="https",
            host="example.com",
            path="/path",
        )
        assert info.scheme == "https"
        assert info.host == "example.com"

    def test_is_secure(self):
        """Test is_secure."""
        info = URLInfo(scheme="https", host="example.com")
        assert info.is_secure is True

        info = URLInfo(scheme="http", host="example.com")
        assert info.is_secure is False

    def test_default_port(self):
        """Test default port."""
        info = URLInfo(scheme="https", host="example.com")
        assert info.default_port == 443

        info = URLInfo(scheme="http", host="example.com")
        assert info.default_port == 80

    def test_effective_port(self):
        """Test effective port."""
        info = URLInfo(scheme="https", host="example.com", port=8080)
        assert info.effective_port == 8080

        info = URLInfo(scheme="https", host="example.com")
        assert info.effective_port == 443

    def test_rebuild(self):
        """Test rebuild."""
        info = URLInfo(
            scheme="https",
            host="example.com",
            path="/path",
            query={"key": ["value"]},
            fragment="frag",
        )
        url = info.rebuild()
        assert "https://" in url
        assert "example.com" in url
        assert "key=value" in url
        assert "#frag" in url


class TestURLConfig:
    """Test URLConfig."""

    def test_defaults(self):
        """Test default configuration."""
        config = URLConfig()
        assert "http" in config.allowed_schemes
        assert "https" in config.allowed_schemes
        assert config.max_length == 2048

    def test_custom(self):
        """Test custom configuration."""
        config = URLConfig(
            allowed_schemes=["https"],
            max_length=1000,
        )
        assert config.allowed_schemes == ["https"]
        assert config.max_length == 1000


class TestURLHandler:
    """Test URLHandler."""

    def test_init(self):
        """Test initialization."""
        handler = URLHandler()
        assert handler.config is not None

    def test_parse_http(self):
        """Test parsing HTTP URL."""
        handler = URLHandler()
        info = handler.parse("http://example.com/path?key=value#frag")
        assert info.status == URLStatus.VALID
        assert info.scheme == "http"
        assert info.host == "example.com"
        assert info.path == "/path"
        assert "key" in info.query
        assert info.fragment == "frag"

    def test_parse_https(self):
        """Test parsing HTTPS URL."""
        handler = URLHandler()
        info = handler.parse("https://example.com")
        assert info.status == URLStatus.VALID
        assert info.scheme == "https"

    def test_parse_with_port(self):
        """Test parsing URL with port."""
        handler = URLHandler()
        info = handler.parse("http://example.com:8080/path")
        assert info.port == 8080

    def test_parse_with_credentials(self):
        """Test parsing URL with credentials."""
        handler = URLHandler()
        info = handler.parse("http://user:pass@example.com")
        assert info.username == "user"
        assert info.password == "pass"

    def test_parse_invalid_scheme(self):
        """Test parsing URL with invalid scheme."""
        handler = URLHandler()
        info = handler.parse("unknown://example.com")
        assert info.status == URLStatus.UNKNOWN_SCHEME

    def test_parse_missing_host(self):
        """Test parsing URL missing host."""
        handler = URLHandler()
        info = handler.parse("http:///path")
        assert info.status == URLStatus.MISSING_HOST

    def test_parse_malformed(self):
        """Test parsing malformed URL."""
        handler = URLHandler()
        info = handler.parse("not a url")
        assert info.status == URLStatus.MALFORMED

    def test_validate(self):
        """Test validation."""
        handler = URLHandler()
        assert handler.validate("https://example.com") is True
        assert handler.validate("not a url") is False

    def test_normalize(self):
        """Test normalization."""
        handler = URLHandler()
        url = handler.normalize("https://EXAMPLE.COM:443/path/")
        assert "example.com" in url.lower()

    def test_resolve(self):
        """Test resolving relative URL."""
        handler = URLHandler()
        url = handler.resolve("https://example.com/page/", "/other")
        assert url == "https://example.com/other"

    def test_extract_urls(self):
        """Test extracting URLs."""
        handler = URLHandler()
        text = "Check https://example.com and http://test.com"
        urls = handler.extract_urls(text)
        assert len(urls) == 2

    def test_build(self):
        """Test building URL."""
        handler = URLHandler()
        url = handler.build(
            scheme="https",
            host="example.com",
            path="/path",
            query={"key": "value"},
        )
        assert "https://example.com/path" in url
        assert "key=value" in url

    def test_add_query(self):
        """Test adding query params."""
        handler = URLHandler()
        url = handler.add_query("https://example.com", {"key": "value"})
        assert "key=value" in url

    def test_remove_query(self):
        """Test removing query params."""
        handler = URLHandler()
        url = handler.remove_query("https://example.com?key=value&other=1", ["key"])
        assert "key" not in url
        assert "other=1" in url

    def test_get_query_value(self):
        """Test getting query value."""
        handler = URLHandler()
        value = handler.get_query_value("https://example.com?key=value", "key")
        assert value == "value"

    def test_encode_decode(self):
        """Test encoding and decoding."""
        handler = URLHandler()
        encoded = handler.encode("https://example.com/path with spaces")
        assert " " not in encoded

        decoded = handler.decode(encoded)
        assert "path with spaces" in decoded

    def test_get_domain(self):
        """Test getting domain."""
        handler = URLHandler()
        domain = handler.get_domain("https://sub.example.com/path")
        assert domain == "sub.example.com"

    def test_get_path_segments(self):
        """Test getting path segments."""
        handler = URLHandler()
        segments = handler.get_path_segments("https://example.com/a/b/c")
        assert segments == ["a", "b", "c"]

    def test_is_same_origin(self):
        """Test same origin check."""
        handler = URLHandler()
        assert handler.is_same_origin(
            "https://example.com/a",
            "https://example.com/b",
        ) is True

        assert handler.is_same_origin(
            "https://example.com/a",
            "http://example.com/b",
        ) is False


class TestHelperFunctions:
    """Test helper functions."""

    def test_parse_url(self):
        """Test parse_url function."""
        info = parse_url("https://example.com")
        assert info.status == URLStatus.VALID

    def test_validate_url(self):
        """Test validate_url function."""
        assert validate_url("https://example.com") is True

    def test_normalize_url(self):
        """Test normalize_url function."""
        url = normalize_url("HTTPS://EXAMPLE.COM")
        assert "https://example.com" in url.lower()

    def test_build_url(self):
        """Test build_url function."""
        url = build_url("https", "example.com", "/path", {"key": "value"})
        assert "https://example.com" in url