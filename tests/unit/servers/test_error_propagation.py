"""Triage tests confirming ToolError is not yet used in Jira/Confluence servers.

Each test asserts that ToolError IS present in the server source. The tests
currently FAIL because the feature is not implemented — that failure is the
proof. Once ToolError is introduced (issue resolved), the tests turn GREEN.

Regression for https://github.com/sooperset/mcp-atlassian/issues/486
"""

import inspect


class TestToolErrorPropagation:
    """Errors are not propagated to MCP client as informative ToolError messages.

    Regression for https://github.com/sooperset/mcp-atlassian/issues/486
    Feature requested: use fastmcp.exceptions.ToolError so errors reach the MCP
    client as structured tool errors instead of being swallowed by FastMCP.
    Currently ValueError/TypeError raised in tools are not surfaced via ToolError.

    Each test FAILS until the feature is implemented, then turns GREEN.
    """

    def test_tool_error_used_in_jira_server(self):
        """ToolError must be imported and used in jira server for client-visible errors.

        FAILS while issue #486 is unresolved. Passes once ToolError is introduced.
        """
        from mcp_atlassian.servers import jira as jira_server

        source = inspect.getsource(jira_server)
        assert "ToolError" in source, (
            "ToolError is NOT used in jira server — "
            "issue #486 is unresolved: errors swallowed, never reach MCP client"
        )

    def test_tool_error_used_in_confluence_server(self):
        """ToolError must be imported and used in confluence server.

        FAILS while issue #486 is unresolved. Passes once ToolError is introduced.
        """
        from mcp_atlassian.servers import confluence as conf_server

        source = inspect.getsource(conf_server)
        assert "ToolError" in source, (
            "ToolError is NOT used in confluence server — "
            "issue #486 is unresolved: errors swallowed, never reach MCP client"
        )

    def test_fastmcp_exceptions_imported_in_jira_server(self):
        """fastmcp.exceptions must be imported in jira server.

        FAILS while issue #486 is unresolved.
        """
        from mcp_atlassian.servers import jira as jira_server

        source = inspect.getsource(jira_server)
        assert "from fastmcp" in source and "ToolError" in source, (
            "fastmcp ToolError not imported in jira server — issue #486 is unresolved"
        )
