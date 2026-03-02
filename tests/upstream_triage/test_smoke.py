"""Smoke test: verify triage test infrastructure works."""

from __future__ import annotations

import pytest

from mcp_atlassian.confluence import ConfluenceFetcher

from .conftest import TriageInstanceInfo, TriageResourceTracker

pytestmark = pytest.mark.upstream_triage


class TestTriageSmoke:
    """Verify the triage test harness connects and operates correctly."""

    def test_can_connect(self, triage_confluence: ConfluenceFetcher) -> None:
        """Verify we can connect to Confluence Cloud."""
        assert triage_confluence.config.is_cloud is True

    def test_can_create_and_read_page(
        self,
        triage_confluence: ConfluenceFetcher,
        triage_instance: TriageInstanceInfo,
        triage_tracker: TriageResourceTracker,
        unique_id: str,
    ) -> None:
        """Verify we can create a page in MCPTEST and read it back."""
        page = triage_confluence.create_page(
            space_key=triage_instance.space_key,
            title=f"Triage Smoke Test {unique_id}",
            body="<p>This page verifies the triage harness works.</p>",
            is_markdown=False,
        )
        triage_tracker.add_page(page.id)
        assert page.id is not None

        fetched = triage_confluence.get_page_content(page.id)
        assert "Smoke" in fetched.title

    def test_space_exists(
        self,
        triage_confluence: ConfluenceFetcher,
        triage_instance: TriageInstanceInfo,
    ) -> None:
        """Verify the MCPTEST space exists."""
        spaces_data = triage_confluence.get_spaces(limit=100)
        results = spaces_data.get("results", [])
        space_keys = [s["key"] for s in results if isinstance(s, dict)]
        assert triage_instance.space_key in space_keys, (
            f"Space {triage_instance.space_key} not found. Available: {space_keys[:10]}"
        )
