"""Tests for missing multi-instance support (upstream #231)."""

from __future__ import annotations

import inspect


class TestMultipleAtlassianInstances:
    """Single server process cannot connect to multiple Atlassian instances.

    Regression for https://github.com/sooperset/mcp-atlassian/issues/231
    Feature requested: configure multiple Jira/Confluence instances in one
    server process. Currently env vars define exactly one pair.
    """

    def test_jira_config_supports_multiple_instances(self) -> None:
        """JiraConfig or server should support multiple named instances."""
        from mcp_atlassian.jira.config import JiraConfig

        source = inspect.getsource(JiraConfig)
        has_multi = (
            "instances" in source
            or "multi_instance" in source
            or "JIRA_INSTANCES" in source
        )
        assert has_multi, (
            "No multi-instance support in JiraConfig — issue #231 not implemented"
        )

    def test_multiple_jira_fetchers_supported_by_server(self) -> None:
        """Server should support registering multiple JiraFetcher instances."""
        from mcp_atlassian.servers import jira as jira_server

        source = inspect.getsource(jira_server)
        has_multi = "instances" in source.lower() and (
            "fetchers" in source.lower() or "multi" in source.lower()
        )
        assert has_multi, (
            "Server does not support multiple JiraFetcher instances — #231 not implemented"
        )
