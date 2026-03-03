"""Triage tests confirming raw HTML content is not supported in Jira issue descriptions.

Each test asserts that HTML mode support IS present in the Jira server. The tests
currently FAIL because the feature is not implemented — that failure is the proof.
Once HTML content is supported (issue resolved), the tests turn GREEN.

Regression for https://github.com/sooperset/mcp-atlassian/issues/684
"""

import inspect


class TestJiraHtmlContent:
    """Raw HTML content not supported in Jira issue description or body fields.

    Regression for https://github.com/sooperset/mcp-atlassian/issues/684
    Feature requested: pass HTML directly to jira_create_issue/update_issue
    without Markdown-to-ADF conversion. Currently only Markdown input is
    supported; HTML is not accepted as a content format for Jira issues.

    Each test FAILS until the feature is implemented, then turns GREEN.
    """

    def test_create_issue_has_html_mode_param(self):
        """create_issue MCP tool must have an html_mode or content_format parameter.

        FAILS while issue #684 is unresolved.
        """
        from mcp_atlassian.servers import jira as jira_server

        source = inspect.getsource(jira_server)
        assert "html_mode" in source, (
            "html_mode parameter not found in jira server — "
            "issue #684 is unresolved: raw HTML input not supported for Jira issues"
        )

    def test_update_issue_has_html_mode_param(self):
        """update_issue MCP tool must support HTML content format.

        FAILS while issue #684 is unresolved.
        """
        from mcp_atlassian.servers import jira as jira_server

        source = inspect.getsource(jira_server)
        # Either html_mode or a jira-specific content_format param signals the feature
        has_html_support = "html_mode" in source or "content_format.*jira" in source
        assert has_html_support, (
            "No HTML mode support found in jira server update_issue — "
            "issue #684 is unresolved: raw HTML input not supported for Jira issues"
        )

    def test_issues_mixin_accepts_html_format(self):
        """IssuesMixin.create_issue must accept html as a content_format value.

        FAILS while issue #684 is unresolved.
        """
        from mcp_atlassian.jira.issues import IssuesMixin

        source = inspect.getsource(IssuesMixin)
        assert "html" in source and (
            "content_format" in source or "html_mode" in source
        ), (
            "IssuesMixin does not reference HTML as a content format — "
            "issue #684 is unresolved: raw HTML input not supported for Jira issues"
        )
