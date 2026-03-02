"""Reproduction test for upstream issue #607.

Bug: Confluence can't find author_name, created_on, and last_modified for pages.
https://github.com/sooperset/mcp-atlassian/issues/607
"""

from __future__ import annotations

import pytest

from mcp_atlassian.confluence import ConfluenceFetcher

from .conftest import TriageInstanceInfo, TriageResourceTracker

pytestmark = pytest.mark.upstream_triage


class TestIssue607:
    """Upstream #607: Page metadata (author, created, modified) missing."""

    def test_page_has_created_date(
        self,
        triage_confluence: ConfluenceFetcher,
        triage_instance: TriageInstanceInfo,
        triage_tracker: TriageResourceTracker,
        unique_id: str,
    ) -> None:
        """get_page_content should return created_on timestamp."""
        page = triage_confluence.create_page(
            space_key=triage_instance.space_key,
            title=f"Issue 607 Test {unique_id}",
            body="<p>Testing metadata retrieval.</p>",
            is_markdown=False,
        )
        triage_tracker.add_page(page.id)

        fetched = triage_confluence.get_page_content(page.id)
        assert fetched.created, "created_on is empty — history not expanded in API call"

    def test_page_has_last_modified(
        self,
        triage_confluence: ConfluenceFetcher,
        triage_instance: TriageInstanceInfo,
        triage_tracker: TriageResourceTracker,
        unique_id: str,
    ) -> None:
        """get_page_content should return last_modified timestamp."""
        page = triage_confluence.create_page(
            space_key=triage_instance.space_key,
            title=f"Issue 607 Modified Test {unique_id}",
            body="<p>Testing metadata retrieval.</p>",
            is_markdown=False,
        )
        triage_tracker.add_page(page.id)

        fetched = triage_confluence.get_page_content(page.id)
        assert fetched.updated, (
            "last_modified is empty — history not expanded in API call"
        )

    def test_page_has_author(
        self,
        triage_confluence: ConfluenceFetcher,
        triage_instance: TriageInstanceInfo,
        triage_tracker: TriageResourceTracker,
        unique_id: str,
    ) -> None:
        """get_page_content should return author information."""
        page = triage_confluence.create_page(
            space_key=triage_instance.space_key,
            title=f"Issue 607 Author Test {unique_id}",
            body="<p>Testing author retrieval.</p>",
            is_markdown=False,
        )
        triage_tracker.add_page(page.id)

        fetched = triage_confluence.get_page_content(page.id)
        assert fetched.author is not None, "author is None — not returned by API"
