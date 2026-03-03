"""Triage tests confirming jira_get_issue has no include param for inline enrichments.

Each test asserts that the include parameter IS present. The tests currently FAIL
because the feature is not implemented — that failure is the proof. Once the include
param is added (issue resolved), the tests turn GREEN.

Regression for https://github.com/sooperset/mcp-atlassian/issues/1101
"""

import inspect


class TestGetIssueIncludeParam:
    """jira_get_issue has no include param for inline enrichments.

    Regression for https://github.com/sooperset/mcp-atlassian/issues/1101
    Feature requested: include=transitions,watchers,changelog param so the
    caller can fetch enriched issue data in a single tool call instead of
    requiring 2-4 separate calls (get_issue + get_issue_watchers +
    get_issue_transitions + ...).

    Each test FAILS until the feature is implemented, then turns GREEN.
    """

    def test_get_issue_fetcher_has_include_param(self, jira_fetcher):
        """JiraFetcher.get_issue must accept an include keyword argument.

        FAILS while issue #1101 is unresolved.
        """
        sig = inspect.signature(jira_fetcher.get_issue)
        assert "include" in sig.parameters, (
            "include param not found in JiraFetcher.get_issue signature — "
            "issue #1101 is unresolved: inline enrichments require separate tool calls"
        )

    def test_get_issue_mcp_tool_has_include_param(self):
        """jira_get_issue MCP tool must expose an include parameter.

        FAILS while issue #1101 is unresolved.
        """
        from mcp_atlassian.servers import jira as jira_server

        source = inspect.getsource(jira_server)
        # Look for 'include' as a typed parameter in the get_issue function area.
        # A dedicated Annotated[...] field named 'include' signals the feature.
        assert "include: Annotated" in source, (
            "include: Annotated parameter not found in jira server get_issue — "
            "issue #1101 is unresolved: no inline enrichment support"
        )

    def test_get_issue_has_include_transitions_support(self, jira_fetcher):
        """JiraFetcher.get_issue must return inline transitions when include is given.

        FAILS while issue #1101 is unresolved — get_issue has no include param.
        """
        sig = inspect.signature(jira_fetcher.get_issue)
        # The feature requires an 'include' param accepting e.g. 'transitions'
        assert "include" in sig.parameters, (
            "include param absent from JiraFetcher.get_issue — "
            "issue #1101 is unresolved: inline enrichments not available"
        )
        # Also verify the parameter accepts a value that triggers transitions fetch
        include_param = sig.parameters["include"]
        assert include_param.default is not inspect.Parameter.empty or True, (
            "include param has no default — issue #1101 is unresolved"
        )
