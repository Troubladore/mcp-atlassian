"""Tests for missing Confluence inline comments tool (upstream #715)."""

from __future__ import annotations

import inspect


class TestConfluenceInlineComments:
    """No tool to retrieve inline (anchored) comments from Confluence pages.

    Regression for https://github.com/sooperset/mcp-atlassian/issues/715
    Feature requested: get_inline_comments to retrieve text-anchored comments.
    """

    def test_get_inline_comments_mcp_tool_exists(self) -> None:
        """get_inline_comments MCP tool should be in Confluence server."""
        from mcp_atlassian.servers import confluence as conf_server

        source = inspect.getsource(conf_server)
        assert "async def get_inline_comments(" in source, (
            "get_inline_comments not found — issue #715 not yet implemented"
        )

    def test_get_inline_comments_method_on_fetcher(self) -> None:
        """ConfluenceFetcher should have a get_inline_comments method."""
        from mcp_atlassian.confluence import ConfluenceFetcher

        assert hasattr(ConfluenceFetcher, "get_inline_comments"), (
            "No get_inline_comments on ConfluenceFetcher — issue #715 not implemented"
        )
