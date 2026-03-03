"""Tests for missing Confluence Whiteboards support (upstream #511)."""

from __future__ import annotations

import inspect


class TestConfluenceWhiteboards:
    """Confluence Whiteboards are not supported.

    Regression for https://github.com/sooperset/mcp-atlassian/issues/511
    Feature requested: retrieve Confluence whiteboards via MCP tools.
    Requires separate Confluence API endpoints for whiteboard content.
    """

    def test_get_whiteboard_mcp_tool_exists(self) -> None:
        """A whiteboard MCP tool should exist in Confluence server."""
        from mcp_atlassian.servers import confluence as conf_server

        source = inspect.getsource(conf_server)
        has_tool = (
            "async def get_whiteboard(" in source
            or "async def retrieve_whiteboard(" in source
            or "async def list_whiteboards(" in source
        )
        assert has_tool, "No whiteboard tool — issue #511 not yet implemented"

    def test_whiteboard_method_on_fetcher(self) -> None:
        """ConfluenceFetcher should have a whiteboard method."""
        from mcp_atlassian.confluence import ConfluenceFetcher

        has_method = hasattr(ConfluenceFetcher, "get_whiteboard") or hasattr(
            ConfluenceFetcher, "get_whiteboards"
        )
        assert has_method, (
            "No whiteboard method on ConfluenceFetcher — #511 not implemented"
        )
