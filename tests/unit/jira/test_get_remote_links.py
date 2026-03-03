"""Tests for missing get_remote_links feature (upstream #857)."""

from __future__ import annotations

from mcp_atlassian.jira import JiraFetcher


class TestGetRemoteIssueLinks:
    """No method to GET remote links from a Jira issue.

    Regression for https://github.com/sooperset/mcp-atlassian/issues/857
    Feature requested: retrieve remote links from a Jira issue.
    create_remote_issue_link exists but GET is not implemented.
    """

    def test_create_remote_link_exists(self, jira_fetcher: JiraFetcher) -> None:
        """create_remote_issue_link exists (baseline check)."""
        assert hasattr(jira_fetcher, "create_remote_issue_link")

    def test_get_remote_links_method_exists(self, jira_fetcher: JiraFetcher) -> None:
        """get_remote_links or get_remote_issue_links method should exist."""
        has_method = hasattr(jira_fetcher, "get_remote_links") or hasattr(
            jira_fetcher, "get_remote_issue_links"
        )
        assert has_method, "No get_remote_links method — issue #857 not yet implemented"
