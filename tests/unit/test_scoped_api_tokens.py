"""Tests for missing scoped API token support (upstream #968)."""

from __future__ import annotations

import inspect


class TestScopedApiTokens:
    """Scoped Atlassian Cloud API tokens not supported.

    Regression for https://github.com/sooperset/mcp-atlassian/issues/968
    Feature requested: scoped tokens require api.atlassian.com/ex/... routing.
    Currently mcp-atlassian always uses the direct site URL.
    """

    def test_jira_config_supports_scoped_token_routing(self) -> None:
        """JiraConfig should support api.atlassian.com gateway routing."""
        from mcp_atlassian.jira.config import JiraConfig

        source = inspect.getsource(JiraConfig)
        has_support = (
            "scoped_token" in source
            or "api.atlassian.com/ex" in source
            or "granular_token" in source
        )
        assert has_support, (
            "No scoped token support in JiraConfig — issue #968 not implemented"
        )
