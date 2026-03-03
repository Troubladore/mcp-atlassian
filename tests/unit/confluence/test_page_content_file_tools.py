"""Tests for missing page content file tools (upstream #996)."""

from __future__ import annotations

import inspect


class TestPageContentFileTools:
    """No tools to download/upload Confluence page content to/from files.

    Regression for https://github.com/sooperset/mcp-atlassian/issues/996
    Feature requested: download_page_to_file / upload_page_from_file tools
    to avoid passing large page bodies through the LLM context window.
    """

    def test_download_page_to_file_tool_exists(self) -> None:
        """download_page_to_file MCP tool should exist in Confluence server."""
        from mcp_atlassian.servers import confluence as conf_server

        source = inspect.getsource(conf_server)
        assert "async def download_page_to_file(" in source, (
            "download_page_to_file not found — issue #996 not yet implemented"
        )

    def test_upload_page_from_file_tool_exists(self) -> None:
        """upload_page_from_file MCP tool should exist in Confluence server."""
        from mcp_atlassian.servers import confluence as conf_server

        source = inspect.getsource(conf_server)
        assert "async def upload_page_from_file(" in source, (
            "upload_page_from_file not found — issue #996 not yet implemented"
        )
