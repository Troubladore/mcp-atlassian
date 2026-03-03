"""Tests for missing SimpleFields utility class (upstream #287)."""

from __future__ import annotations


class TestSimpleFieldsClass:
    """No SimpleFields utility class for consistent field type handling.

    Regression for https://github.com/sooperset/mcp-atlassian/issues/287
    Feature requested: SimpleFields class to handle str/list/*all/None
    field values uniformly, replacing ad-hoc type checks in issues.py.
    """

    def test_simple_fields_in_utils(self) -> None:
        """SimpleFields class should exist in utils module."""
        from mcp_atlassian.utils import SimpleFields  # noqa: F401

    def test_simple_fields_handles_str(self) -> None:
        """SimpleFields should accept a comma-separated string."""
        from mcp_atlassian.utils import SimpleFields

        sf = SimpleFields("field1,field2")
        assert "field1" in sf
        assert sf.as_param() in ("field1,field2", "field2,field1")
