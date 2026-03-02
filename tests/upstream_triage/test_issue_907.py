"""Reproduction test for upstream issue #907.

Bug: confluence_search returns empty results when querying with CQL type=space.

The search method in confluence/search.py processes results by matching on
``result_item.get("content", {}).get("id")``, but space search results have a
``space`` key instead of ``content``. This means the excerpt-matching loop never
finds a match for space results, so all returned ConfluencePage objects have
empty content.

https://github.com/sooperset/mcp-atlassian/issues/907
"""

from __future__ import annotations

import pytest

from mcp_atlassian.confluence import ConfluenceFetcher

from .conftest import TriageInstanceInfo

pytestmark = pytest.mark.upstream_triage


class TestIssue907:
    """Upstream #907: confluence_search empty for space queries."""

    def test_cql_type_space_returns_results(
        self,
        triage_confluence: ConfluenceFetcher,
        triage_instance: TriageInstanceInfo,
    ) -> None:
        """Searching with CQL type=space should return space results."""
        # We know MCPTEST space exists, so type=space should find at least one
        results = triage_confluence.search(cql="type=space", limit=10)
        assert len(results) > 0, (
            "CQL search for type=space returned no results, "
            "but spaces exist in the instance"
        )

    def test_cql_type_space_results_have_content(
        self,
        triage_confluence: ConfluenceFetcher,
        triage_instance: TriageInstanceInfo,
    ) -> None:
        """Space search results should have meaningful content, not empty strings."""
        results = triage_confluence.search(cql="type=space", limit=10)
        if not results:
            pytest.skip("No space results returned (may be issue #907 itself)")

        # At least one result should have non-empty content or title
        has_content = any(
            (getattr(r, "content", None) or getattr(r, "title", None)) for r in results
        )
        assert has_content, (
            "All space search results have empty content and title — "
            "space result processing is broken"
        )
