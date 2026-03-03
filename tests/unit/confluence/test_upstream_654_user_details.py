"""Failing triage test for upstream issue #654.

Issue: "Get user details in Confluence tools"
URL: https://github.com/sooperset/mcp-atlassian/issues/654

The UsersMixin has get_user_details_by_accountid and get_user_details_by_username
methods, but neither is exposed as an MCP tool in the Confluence server.  The
only user-related MCP tool is search_user, which searches by display-name/email
substring rather than fetching a specific user by identifier.

These tests FAIL until the feature is implemented.
"""

import inspect


class TestConfluenceUserDetails:
    """No get_user_by_account_id MCP tool exposed in Confluence server.

    Regression for https://github.com/sooperset/mcp-atlassian/issues/654
    Feature requested: MCP tools to fetch Confluence user details by
    accountId or username — not just substring search.
    """

    def test_get_user_by_account_id_mcp_tool_exists(self) -> None:
        """Confluence server must expose a get_user_by_account_id MCP tool.

        This test FAILS until the feature is implemented.
        """
        from mcp_atlassian.servers import confluence as conf_server

        source = inspect.getsource(conf_server)
        assert "async def get_user_by_account_id" in source, (
            "get_user_by_account_id MCP tool not found in Confluence server — "
            "issue #654 is not yet implemented"
        )

    def test_get_user_details_mcp_tool_exists(self) -> None:
        """Confluence server must expose a get_user_details MCP tool.

        This test FAILS until the feature is implemented.
        """
        from mcp_atlassian.servers import confluence as conf_server

        source = inspect.getsource(conf_server)
        assert "async def get_user_details" in source or (
            "async def get_user_by_account_id" in source
        ), (
            "No user-details MCP tool (get_user_details or get_user_by_account_id) "
            "found in Confluence server — issue #654 is not yet implemented"
        )

    def test_user_details_by_accountid_reachable_via_mcp_server(
        self, confluence_fetcher: object
    ) -> None:
        """MCP server must call through to get_user_details_by_accountid.

        The underlying mixin method already exists; this test verifies that
        the MCP server wires it up as a callable tool.

        This test FAILS until the feature is implemented.
        """
        from mcp_atlassian.servers import confluence as conf_server

        source = inspect.getsource(conf_server)

        # The underlying mixin method must still exist
        assert hasattr(confluence_fetcher, "get_user_details_by_accountid"), (
            "get_user_details_by_accountid disappeared from UsersMixin — unexpected"
        )

        # The MCP server must call through to it
        assert "get_user_details_by_accountid" in source, (
            "MCP server does not call get_user_details_by_accountid — "
            "issue #654 is not yet implemented"
        )
