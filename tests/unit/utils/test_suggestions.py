"""Tests for suggestion/fuzzy matching utilities."""

from mcp_atlassian.utils.suggestions import format_suggestions, fuzzy_match


class TestFuzzyMatch:
    """Tests for fuzzy_match()."""

    def test_exact_case_insensitive_match(self):
        """Exact match differing only in case returns single result."""
        result = fuzzy_match("eruditis", ["ERUDITIS", "OTHER"])
        assert result == ["ERUDITIS"]

    def test_no_match_returns_empty(self):
        """Completely unrelated input returns no suggestions."""
        result = fuzzy_match("zzzzz", ["ALPHA", "BETA"])
        assert result == []

    def test_multiple_close_matches(self):
        """Multiple similar candidates all returned."""
        result = fuzzy_match("erud", ["ERUDITIS", "ERUDITISARCHIVE", "OTHER"])
        assert "ERUDITIS" in result
        assert "ERUDITISARCHIVE" in result
        assert "OTHER" not in result

    def test_empty_candidates(self):
        """Empty candidate list returns empty."""
        result = fuzzy_match("test", [])
        assert result == []

    def test_empty_input(self):
        """Empty input returns empty."""
        result = fuzzy_match("", ["ALPHA"])
        assert result == []

    def test_max_results_default(self):
        """Returns at most 3 suggestions by default."""
        candidates = [f"TEST{i}" for i in range(10)]
        result = fuzzy_match("TEST", candidates)
        assert len(result) <= 3

    def test_substring_match(self):
        """Substring of a candidate is found."""
        result = fuzzy_match("pages", ["confluence_pages", "jira_issues"])
        assert "confluence_pages" in result


class TestFormatSuggestions:
    """Tests for format_suggestions()."""

    def test_with_suggestions_and_hint(self):
        result = format_suggestions(
            "Space 'erud' not found",
            ["ERUDITIS", "ERUDITISARCHIVE"],
            hint="Space keys are case-sensitive uppercase",
        )
        assert result["error"] == "Space 'erud' not found"
        assert result["suggestions"] == ["ERUDITIS", "ERUDITISARCHIVE"]
        assert result["hint"] == "Space keys are case-sensitive uppercase"

    def test_without_hint(self):
        result = format_suggestions("Not found", ["A", "B"])
        assert "hint" not in result
        assert result["suggestions"] == ["A", "B"]

    def test_empty_suggestions(self):
        result = format_suggestions("Not found", [])
        assert result["suggestions"] == []
        assert "hint" not in result
