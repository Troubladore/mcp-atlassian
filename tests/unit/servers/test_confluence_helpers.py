"""Unit tests for Confluence server helper functions."""

import pytest

from mcp_atlassian.servers.confluence import parse_page_id_from_url


class TestURLParsing:
    """Tests for URL parsing helper."""

    def test_parse_modern_url(self):
        """Test parsing modern Confluence Cloud URL format."""
        url = "https://eruditis.atlassian.net/wiki/spaces/TEAM/pages/123456789/Page+Title"
        result = parse_page_id_from_url(url)
        assert result == "123456789"

    def test_parse_legacy_url(self):
        """Test parsing legacy viewpage.action URL format."""
        url = "https://site.atlassian.net/wiki/pages/viewpage.action?pageId=987654"
        result = parse_page_id_from_url(url)
        assert result == "987654"

    def test_parse_already_id(self):
        """Test that plain ID strings are returned unchanged."""
        result = parse_page_id_from_url("123456")
        assert result == "123456"

    def test_parse_int_id(self):
        """Test that integer IDs are converted to strings."""
        result = parse_page_id_from_url(123456)
        assert result == "123456"

    def test_parse_none(self):
        """Test that None returns None."""
        result = parse_page_id_from_url(None)
        assert result is None

    def test_parse_invalid_url(self):
        """Test that invalid URLs are returned as-is with warning."""
        url = "https://example.com/not-a-confluence-url"
        result = parse_page_id_from_url(url)
        assert result == url  # Returns unchanged

    def test_parse_http_url(self):
        """Test that http:// URLs also work (not just https://)."""
        url = "http://site.atlassian.net/wiki/spaces/DEV/pages/99999/Test"
        result = parse_page_id_from_url(url)
        assert result == "99999"
