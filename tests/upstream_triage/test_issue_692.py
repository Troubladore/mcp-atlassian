"""Reproduction test for upstream issue #692.

Bug: Update page error message is not descriptive — just shows "Error calling tool"
when trying to update with a duplicate title.
https://github.com/sooperset/mcp-atlassian/issues/692
"""

from __future__ import annotations

import pytest

from mcp_atlassian.confluence import ConfluenceFetcher

from .conftest import TriageInstanceInfo, TriageResourceTracker

pytestmark = pytest.mark.upstream_triage


class TestIssue692:
    """Upstream #692: Error message not descriptive on duplicate title update."""

    def test_duplicate_title_error_is_descriptive(
        self,
        triage_confluence: ConfluenceFetcher,
        triage_instance: TriageInstanceInfo,
        triage_tracker: TriageResourceTracker,
        unique_id: str,
    ) -> None:
        """Updating a page to a title that already exists should raise
        an error with a descriptive message mentioning the title conflict."""
        # Create two pages in the same space
        page_a = triage_confluence.create_page(
            space_key=triage_instance.space_key,
            title=f"Issue 692 Page A {unique_id}",
            body="<p>First page.</p>",
            is_markdown=False,
        )
        triage_tracker.add_page(page_a.id)

        page_b = triage_confluence.create_page(
            space_key=triage_instance.space_key,
            title=f"Issue 692 Page B {unique_id}",
            body="<p>Second page.</p>",
            is_markdown=False,
        )
        triage_tracker.add_page(page_b.id)

        # Try to update page_b's title to match page_a's title.
        # The error message should mention the title conflict, not just
        # a generic "Error calling tool" or "Failed to update page".
        with pytest.raises(Exception, match="(?i)(already exists|title|duplicate)"):
            triage_confluence.update_page(
                page_id=page_b.id,
                title=f"Issue 692 Page A {unique_id}",
                body="<p>Updated body.</p>",
                is_markdown=False,
            )
