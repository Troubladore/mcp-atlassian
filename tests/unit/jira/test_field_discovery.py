"""Tests for Jira multi-field discovery (upstream #336)."""

from __future__ import annotations

import inspect

from mcp_atlassian.jira import JiraFetcher


class TestJiraFieldDiscovery:
    """No reliable way to discover project-specific custom fields.

    Regression for https://github.com/sooperset/mcp-atlassian/issues/336
    Feature requested: LLMs should be able to discover available fields
    (e.g. 'Actual Result', 'Expected Result') for a given project/issue type.
    additional_fields exists for passing custom fields but discovery is incomplete.
    """

    def test_get_project_fields_method_exists(self, jira_fetcher: JiraFetcher) -> None:
        """JiraFetcher should expose a method to list fields for a project."""
        has_method = (
            hasattr(jira_fetcher, "get_project_fields")
            or hasattr(jira_fetcher, "get_issue_type_fields")
            or hasattr(jira_fetcher, "get_fields_for_issue_type")
        )
        assert has_method, (
            "No project field discovery method — issue #336 not fully addressed"
        )

    def test_field_discovery_mcp_tool_exists(self) -> None:
        """A field discovery MCP tool should exist in jira server."""
        from mcp_atlassian.servers import jira as jira_server

        source = inspect.getsource(jira_server)
        has_tool = (
            "async def get_project_fields(" in source
            or "async def get_issue_type_fields(" in source
            or "async def get_fields_for_issue_type(" in source
        )
        assert has_tool, "No field discovery MCP tool — issue #336 not fully addressed"
