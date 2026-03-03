"""Triage tests confirming batch/bulk update of Jira issues is not implemented.

Each test asserts that the batch update capability IS present. The tests
currently FAIL because the feature does not exist — that failure is the proof.
Once batch update is implemented (issue resolved), the tests turn GREEN.

Regression for https://github.com/sooperset/mcp-atlassian/issues/510
"""

import inspect

import pytest


class TestJiraBatchUpdate:
    """Batch/bulk update of multiple Jira issues not implemented.

    Regression for https://github.com/sooperset/mcp-atlassian/issues/510
    Feature requested: expose batch update endpoint for updating multiple
    issues. batch_create_issues exists but batch update (Bulk Edit API)
    does not.

    Each test FAILS until the feature is implemented, then turns GREEN.
    """

    def test_batch_update_issues_method_exists(self, jira_fetcher):
        """JiraFetcher must have a batch_update_issues method.

        FAILS while issue #510 is unresolved.
        """
        assert hasattr(jira_fetcher, "batch_update_issues"), (
            "batch_update_issues does not exist on JiraFetcher — "
            "issue #510 is unresolved: bulk update API not implemented"
        )

    def test_batch_update_mcp_tool_exists(self):
        """A batch_update_issues MCP tool must exist in the jira server.

        FAILS while issue #510 is unresolved.
        """
        from mcp_atlassian.servers import jira as jira_server

        source = inspect.getsource(jira_server)
        has_batch_update = (
            "async def batch_update_issues" in source
            or "async def bulk_update_issues" in source
        )
        assert has_batch_update, (
            "No batch_update_issues or bulk_update_issues MCP tool found — "
            "issue #510 is unresolved: bulk update API not implemented"
        )

    def test_batch_update_issues_callable(self, jira_fetcher):
        """batch_update_issues must be callable with issue keys and field data.

        FAILS while issue #510 is unresolved.
        """
        assert callable(getattr(jira_fetcher, "batch_update_issues", None)), (
            "batch_update_issues is not callable — "
            "issue #510 is unresolved: bulk update API not implemented"
        )

    @pytest.mark.parametrize(
        "method_name", ["batch_update_issues", "bulk_update_issues"]
    )
    def test_bulk_update_variant_exists(self, jira_fetcher, method_name):
        """At least one bulk/batch update variant must exist on JiraFetcher.

        FAILS while issue #510 is unresolved.
        """
        assert hasattr(jira_fetcher, method_name), (
            f"{method_name} does not exist on JiraFetcher — "
            "issue #510 is unresolved: bulk update API not implemented"
        )
