"""Triage tests confirming update_issue does not support orchestration.

Each test asserts that orchestration IS supported (transition + comment + worklog
in a single call). The tests currently FAIL because the feature is not implemented
— that failure is the proof. Once orchestration is added (issue resolved), the
tests turn GREEN.

Regression for https://github.com/sooperset/mcp-atlassian/issues/1102
"""

import inspect


class TestUpdateIssueOrchestration:
    """update_issue does not support transition/comment/worklog in one call.

    Regression for https://github.com/sooperset/mcp-atlassian/issues/1102
    Feature requested: consolidated update — apply a transition, add a comment,
    and log work all in a single jira_update_issue call to reduce tool call
    round-trips for common "close with comment" and "log and resolve" workflows.

    Each test FAILS until the feature is implemented, then turns GREEN.
    """

    def test_update_issue_fetcher_has_transition_param(self, jira_fetcher):
        """JiraFetcher.update_issue must accept a transition parameter.

        FAILS while issue #1102 is unresolved.
        """
        sig = inspect.signature(jira_fetcher.update_issue)
        assert "transition" in sig.parameters, (
            "transition param not found in JiraFetcher.update_issue — "
            "issue #1102 is unresolved: cannot transition+update in one call"
        )

    def test_update_issue_fetcher_has_comment_param(self, jira_fetcher):
        """JiraFetcher.update_issue must accept a comment parameter.

        FAILS while issue #1102 is unresolved.
        """
        sig = inspect.signature(jira_fetcher.update_issue)
        assert "comment" in sig.parameters, (
            "comment param not found in JiraFetcher.update_issue — "
            "issue #1102 is unresolved: cannot update+comment in one call"
        )

    def test_update_issue_fetcher_has_worklog_param(self, jira_fetcher):
        """JiraFetcher.update_issue must accept a worklog/log_work parameter.

        FAILS while issue #1102 is unresolved.
        """
        sig = inspect.signature(jira_fetcher.update_issue)
        has_worklog = "worklog" in sig.parameters or "log_work" in sig.parameters
        assert has_worklog, (
            "worklog/log_work param not found in JiraFetcher.update_issue — "
            "issue #1102 is unresolved: cannot update+log work in one call"
        )

    def test_update_issue_mcp_tool_has_transition_param(self):
        """jira_update_issue MCP tool must support inline transition.

        FAILS while issue #1102 is unresolved.
        """
        from mcp_atlassian.servers import jira as jira_server

        source = inspect.getsource(jira_server)
        # Look for transition as a typed Annotated parameter inside update_issue
        # The current update_issue passes 'status' via the fields JSON string,
        # not as a dedicated first-class param — the feature adds a dedicated param.
        assert "transition_to" in source or ("transition: Annotated" in source), (
            "No dedicated transition param in jira server update_issue — "
            "issue #1102 is unresolved: orchestration not supported"
        )
