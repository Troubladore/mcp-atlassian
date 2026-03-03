"""Tests for missing include param on get_page (upstream #1103)."""

from __future__ import annotations

import inspect

from mcp_atlassian.confluence import ConfluenceFetcher


class TestGetPageIncludeParam:
    """confluence_get_page has no include param for inline enrichments.

    Regression for https://github.com/sooperset/mcp-atlassian/issues/1103
    Feature requested: include=comments,labels,views in get_page to avoid
    2-4 separate tool calls for common enrichments.
    """

    def test_get_page_content_has_include_param(self) -> None:
        """get_page_content should accept an include parameter."""
        sig = inspect.signature(ConfluenceFetcher.get_page_content)
        assert "include" in sig.parameters, (
            "include param missing from get_page_content — issue #1103 not implemented"
        )
