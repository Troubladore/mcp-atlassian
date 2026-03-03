"""Tests for missing project issue types MCP tool (upstream #460)."""

from __future__ import annotations

import inspect

from mcp_atlassian.jira import JiraFetcher


class TestProjectIssueTypesMCPTool:
    """get_project_issue_types not exposed as an MCP tool.

    Regression for https://github.com/sooperset/mcp-atlassian/issues/460
    Feature requested: MCP tool to list available issue types per project.
    The underlying JiraFetcher method exists but is not a registered tool.
    """

    def test_underlying_method_exists(self, jira_fetcher: JiraFetcher) -> None:
        """Underlying get_project_issue_types method exists on JiraFetcher."""
        assert hasattr(jira_fetcher, "get_project_issue_types")

    def test_get_project_issue_types_is_mcp_tool(self) -> None:
        """get_project_issue_types should be a registered MCP tool."""
        from mcp_atlassian.servers import jira as jira_server

        source = inspect.getsource(jira_server)
        assert "async def get_project_issue_types(" in source, (
            "get_project_issue_types not an MCP tool — issue #460 not yet implemented"
        )
