"""Tests for missing get_current_user MCP tool (upstream #459)."""

from __future__ import annotations

from mcp_atlassian.jira import JiraFetcher


class TestGetCurrentUserTool:
    """No dedicated get_me or get_current_user MCP tool exists.

    Regression for https://github.com/sooperset/mcp-atlassian/issues/459
    Feature requested: MCP tool to retrieve the currently authenticated user.
    Test FAILS until a dedicated get_current_user/get_me tool is added.
    """

    def test_get_current_user_tool_importable(self) -> None:
        """get_current_user or get_me should be importable from jira server."""
        try:
            from mcp_atlassian.servers.jira import get_current_user  # noqa: F401
        except ImportError:
            from mcp_atlassian.servers.jira import get_me  # noqa: F401

    def test_get_current_user_via_tool(self, jira_fetcher: JiraFetcher) -> None:
        """Calling get_me/get_current_user should return current user info.

        This fails because the feature is not yet implemented.
        """
        import inspect

        from mcp_atlassian.servers import jira as jira_server

        source = inspect.getsource(jira_server)
        has_tool = (
            "async def get_current_user(" in source or "async def get_me(" in source
        )
        assert has_tool, "No get_current_user/get_me tool — issue #459 not implemented"
