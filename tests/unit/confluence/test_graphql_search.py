"""Tests for missing Confluence GraphQL search (upstream #353)."""

from __future__ import annotations

import inspect


class TestConfluenceGraphQLSearch:
    """Confluence GraphQL search is not implemented.

    Regression for https://github.com/sooperset/mcp-atlassian/issues/353
    Feature requested: use Confluence GraphQL API for better full-text search.
    Requires custom implementation — atlassian-python-api lacks GraphQL support.
    """

    def test_graphql_search_mcp_tool_exists(self) -> None:
        """A GraphQL search MCP tool should exist in Confluence server."""
        from mcp_atlassian.servers import confluence as conf_server

        source = inspect.getsource(conf_server)
        has_tool = (
            "async def graphql_search(" in source
            or "async def search_graphql(" in source
        )
        assert has_tool, "No GraphQL search tool — issue #353 not yet implemented"

    def test_graphql_search_method_on_fetcher(self) -> None:
        """ConfluenceFetcher should have a graphql_search method."""
        from mcp_atlassian.confluence import ConfluenceFetcher

        has_method = hasattr(ConfluenceFetcher, "graphql_search") or hasattr(
            ConfluenceFetcher, "search_graphql"
        )
        assert has_method, (
            "No graphql_search on ConfluenceFetcher — issue #353 not implemented"
        )
