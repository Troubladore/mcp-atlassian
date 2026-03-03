"""Reproduction test for upstream issue #743.

Bug: 'str' object has no attribute 'get' when calling confluence_get_page.
https://github.com/sooperset/mcp-atlassian/issues/743

Reported on v0.11.9. Fixed by commit 071c522 which added isinstance(page, str)
guard before calling page.get() in get_page_content().
"""

from __future__ import annotations

import pytest

from mcp_atlassian.confluence import ConfluenceFetcher

from .conftest import TriageInstanceInfo

pytestmark = pytest.mark.upstream_triage


class TestIssue743:
    """Upstream #743: 'str' object has no attribute 'get' on get_page_content."""

    def test_nonexistent_page_raises_clean_error(
        self,
        triage_confluence: ConfluenceFetcher,
    ) -> None:
        """get_page_content with a bad page ID should raise a clean error,
        not AttributeError: 'str' object has no attribute 'get'."""
        with pytest.raises(Exception) as exc_info:
            triage_confluence.get_page_content("000000000")

        # Should be a clean error message, not an AttributeError about 'str'
        assert "str" not in str(exc_info.value) or "has no attribute" not in str(
            exc_info.value
        ), f"Got raw AttributeError: {exc_info.value}"

    def test_existing_page_returns_content(
        self,
        triage_confluence: ConfluenceFetcher,
        triage_instance: TriageInstanceInfo,
    ) -> None:
        """get_page_content on a valid page should return a ConfluencePage."""
        from mcp_atlassian.models import ConfluencePage

        # Use the known MCPTEST homepage
        result = triage_confluence.get_page_content("2570551630")
        assert isinstance(result, ConfluencePage)
        assert result.id == "2570551630"
