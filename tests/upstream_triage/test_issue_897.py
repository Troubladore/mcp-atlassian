"""Reproduction test for upstream issue #897.

Bug: Date macro content is lost when getting a Confluence page via MCP.
https://github.com/sooperset/mcp-atlassian/issues/897
"""

from __future__ import annotations

import pytest

from mcp_atlassian.confluence import ConfluenceFetcher

from .conftest import TriageInstanceInfo, TriageResourceTracker

pytestmark = pytest.mark.upstream_triage


class TestIssue897:
    """Upstream #897: Date macro content missing from page data."""

    def test_date_macro_preserved_in_page_content(
        self,
        triage_confluence: ConfluenceFetcher,
        triage_instance: TriageInstanceInfo,
        triage_tracker: TriageResourceTracker,
        unique_id: str,
    ) -> None:
        """A page with a date macro should include the date value in content."""
        # Create a page with a Confluence date macro in storage format
        storage_body = (
            "<p>Meeting date: "
            '<ac:structured-macro ac:name="date">'
            '<ac:parameter ac:name="date">2026-02-04</ac:parameter>'
            "</ac:structured-macro>"
            "</p>"
        )
        page = triage_confluence.create_page(
            space_key=triage_instance.space_key,
            title=f"Issue 897 Date Test {unique_id}",
            body=storage_body,
            is_markdown=False,
            content_representation="storage",
        )
        triage_tracker.add_page(page.id)

        # Fetch the page — content should contain the date value
        fetched = triage_confluence.get_page_content(page.id)
        content = fetched.content or ""
        assert "2026-02-04" in content or "Feb" in content or "February" in content, (
            f"Date macro value not found in page content. Content was: {content[:500]}"
        )
