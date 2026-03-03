"""Triage tests: HTTP errors not propagated as ToolError to MCP client.

Each test asserts HTTP 400/500 errors are raised as ToolError so the MCP
client receives a structured, informative error. Tests currently FAIL because
the feature is not implemented. Once errors are wrapped in ToolError (issue
resolved), the tests turn GREEN.

Regression for https://github.com/sooperset/mcp-atlassian/issues/649
"""

from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import HTTPError


def _make_http_error(status_code: int) -> HTTPError:
    """Create an HTTPError with a mock response for the given status code."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.text = f'{{"errorMessages": ["HTTP {status_code} error"]}}'
    err = HTTPError(response=mock_response)
    err.response = mock_response
    return err


class TestHttpErrorPropagation:
    """HTTP errors from Atlassian API not propagated to MCP client as ToolError.

    Regression for https://github.com/sooperset/mcp-atlassian/issues/649
    Feature requested: HTTP 400/500 errors should reach the MCP client as
    structured ToolError messages. Currently they are re-raised as raw
    HTTPError or ValueError without ToolError wrapping.
    Related to #486.

    Each test FAILS until the feature is implemented, then turns GREEN.
    """

    def test_http_400_raises_tool_error(self, jira_fetcher):
        """HTTP 400 from Jira API must become a ToolError for the MCP client.

        FAILS while issue #649 is unresolved: currently raises raw HTTPError.
        """
        from fastmcp.exceptions import ToolError

        with patch.object(
            jira_fetcher.jira,
            "get_issue",
            side_effect=_make_http_error(400),
        ):
            with pytest.raises(ToolError):
                jira_fetcher.get_issue("TEST-400")

    def test_http_500_raises_tool_error(self, jira_fetcher):
        """HTTP 500 from Jira API must become a ToolError for the MCP client.

        FAILS while issue #649 is unresolved: currently raises raw HTTPError.
        """
        from fastmcp.exceptions import ToolError

        with patch.object(
            jira_fetcher.jira,
            "get_issue",
            side_effect=_make_http_error(500),
        ):
            with pytest.raises(ToolError):
                jira_fetcher.get_issue("TEST-500")

    def test_http_422_raises_tool_error(self, jira_fetcher):
        """HTTP 422 (Unprocessable Entity) must become a ToolError.

        FAILS while issue #649 is unresolved.
        """
        from fastmcp.exceptions import ToolError

        with patch.object(
            jira_fetcher.jira,
            "get_issue",
            side_effect=_make_http_error(422),
        ):
            with pytest.raises(ToolError):
                jira_fetcher.get_issue("TEST-422")
