# Error Recovery Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add intelligent error recovery with fuzzy matching so MCP tools auto-correct when confident and suggest alternatives when ambiguous, instead of failing with generic errors.

**Architecture:** Recovery logic lives in server tool functions. A new `utils/suggestions.py` module provides reusable fuzzy matching helpers. Client mixins remain unchanged.

**Tech Stack:** Python 3.10+, `difflib.get_close_matches`, existing Confluence/Jira APIs

---

### Task 1: Create `utils/suggestions.py` with fuzzy matching helpers

**Files:**
- Create: `src/mcp_atlassian/utils/suggestions.py`
- Test: `tests/unit/utils/test_suggestions.py`

**Step 1: Write failing tests for `fuzzy_match`**

```python
# tests/unit/utils/test_suggestions.py
"""Tests for suggestion/fuzzy matching utilities."""

import pytest

from mcp_atlassian.utils.suggestions import fuzzy_match


class TestFuzzyMatch:
    """Tests for fuzzy_match()."""

    def test_exact_case_insensitive_match(self):
        """Exact match differing only in case returns single result."""
        result = fuzzy_match("acme", ["ACME", "OTHER"])
        assert result == ["ACME"]

    def test_no_match_returns_empty(self):
        """Completely unrelated input returns no suggestions."""
        result = fuzzy_match("zzzzz", ["ALPHA", "BETA"])
        assert result == []

    def test_multiple_close_matches(self):
        """Multiple similar candidates all returned."""
        result = fuzzy_match("erud", ["ACME", "ACMEARCHIVE", "OTHER"])
        assert "ACME" in result
        assert "ACMEARCHIVE" in result
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
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/utils/test_suggestions.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mcp_atlassian.utils.suggestions'`

**Step 3: Implement `fuzzy_match`**

```python
# src/mcp_atlassian/utils/suggestions.py
"""Fuzzy matching and suggestion utilities for error recovery."""

from difflib import get_close_matches


def fuzzy_match(
    user_input: str,
    candidates: list[str],
    max_results: int = 3,
    cutoff: float = 0.4,
) -> list[str]:
    """Find candidates that fuzzy-match the user input.

    Uses case-insensitive difflib matching plus substring matching.

    Args:
        user_input: The string the user provided.
        candidates: Available valid strings to match against.
        max_results: Maximum number of suggestions to return.
        cutoff: Minimum similarity ratio (0.0-1.0) for difflib.

    Returns:
        List of matching candidates (original case), best matches first.
    """
    if not user_input or not candidates:
        return []

    input_lower = user_input.lower()

    # 1. Exact case-insensitive match (highest priority)
    exact = [c for c in candidates if c.lower() == input_lower]
    if exact:
        return exact[:max_results]

    # 2. difflib fuzzy matching (case-insensitive comparison)
    lower_to_original: dict[str, str] = {}
    for c in candidates:
        lower_to_original.setdefault(c.lower(), c)

    difflib_matches = get_close_matches(
        input_lower, list(lower_to_original.keys()), n=max_results, cutoff=cutoff
    )
    results = [lower_to_original[m] for m in difflib_matches]

    # 3. Substring matching (append any not already found)
    if len(results) < max_results:
        for c in candidates:
            if input_lower in c.lower() and c not in results:
                results.append(c)
                if len(results) >= max_results:
                    break

    return results[:max_results]
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/utils/test_suggestions.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/mcp_atlassian/utils/suggestions.py tests/unit/utils/test_suggestions.py
git commit -m "feat: add fuzzy matching helpers in utils/suggestions.py"
```

---

### Task 2: Add `format_suggestions` helper

**Files:**
- Modify: `src/mcp_atlassian/utils/suggestions.py`
- Modify: `tests/unit/utils/test_suggestions.py`

**Step 1: Write failing tests for `format_suggestions`**

Append to `tests/unit/utils/test_suggestions.py`:

```python
from mcp_atlassian.utils.suggestions import format_suggestions


class TestFormatSuggestions:
    """Tests for format_suggestions()."""

    def test_with_suggestions_and_hint(self):
        result = format_suggestions(
            "Space 'erud' not found",
            ["ACME", "ACMEARCHIVE"],
            hint="Space keys are case-sensitive uppercase",
        )
        assert result["error"] == "Space 'erud' not found"
        assert result["suggestions"] == ["ACME", "ACMEARCHIVE"]
        assert result["hint"] == "Space keys are case-sensitive uppercase"

    def test_without_hint(self):
        result = format_suggestions("Not found", ["A", "B"])
        assert "hint" not in result
        assert result["suggestions"] == ["A", "B"]

    def test_empty_suggestions(self):
        result = format_suggestions("Not found", [])
        assert result["suggestions"] == []
        assert "hint" not in result
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/utils/test_suggestions.py::TestFormatSuggestions -v`
Expected: FAIL — `ImportError`

**Step 3: Implement `format_suggestions`**

Add to `src/mcp_atlassian/utils/suggestions.py`:

```python
def format_suggestions(
    error_msg: str,
    suggestions: list[str],
    hint: str | None = None,
) -> dict[str, object]:
    """Build a structured error response with suggestions.

    Args:
        error_msg: The primary error message.
        suggestions: List of suggested corrections.
        hint: Optional hint for the user.

    Returns:
        Dict with 'error', 'suggestions', and optionally 'hint'.
    """
    result: dict[str, object] = {
        "error": error_msg,
        "suggestions": suggestions,
    }
    if hint:
        result["hint"] = hint
    return result
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/utils/test_suggestions.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/mcp_atlassian/utils/suggestions.py tests/unit/utils/test_suggestions.py
git commit -m "feat: add format_suggestions helper"
```

---

### Task 3: Add `suggest_spaces` helper (Phase 1 core)

This is the Confluence-specific helper that fetches available spaces and fuzzy-matches.

**Files:**
- Modify: `src/mcp_atlassian/utils/suggestions.py`
- Modify: `tests/unit/utils/test_suggestions.py`

**Step 1: Write failing tests**

```python
from unittest.mock import MagicMock

from mcp_atlassian.utils.suggestions import suggest_spaces


class TestSuggestSpaces:
    """Tests for suggest_spaces()."""

    def _make_fetcher(self, space_keys: list[str]) -> MagicMock:
        """Create a mock fetcher returning given space keys."""
        fetcher = MagicMock()
        results = [{"key": k, "name": f"Space {k}"} for k in space_keys]
        fetcher.get_spaces.return_value = {"results": results}
        return fetcher

    def test_exact_case_insensitive(self):
        fetcher = self._make_fetcher(["ACME", "OTHER"])
        result = suggest_spaces("acme", fetcher)
        assert result == ["ACME"]

    def test_no_match(self):
        fetcher = self._make_fetcher(["ALPHA", "BETA"])
        result = suggest_spaces("zzzzz", fetcher)
        assert result == []

    def test_multiple_matches(self):
        fetcher = self._make_fetcher(["ACME", "ACMEARCHIVE", "OTHER"])
        result = suggest_spaces("erud", fetcher)
        assert "ACME" in result
        assert "ACMEARCHIVE" in result

    def test_fetcher_error_returns_empty(self):
        fetcher = MagicMock()
        fetcher.get_spaces.side_effect = Exception("API error")
        result = suggest_spaces("test", fetcher)
        assert result == []
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/utils/test_suggestions.py::TestSuggestSpaces -v`
Expected: FAIL — `ImportError`

**Step 3: Implement `suggest_spaces`**

Add to `src/mcp_atlassian/utils/suggestions.py`:

```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_atlassian.confluence import ConfluenceFetcher

logger = logging.getLogger(__name__)


def suggest_spaces(
    space_key_input: str,
    fetcher: ConfluenceFetcher,
) -> list[str]:
    """Suggest similar space keys when the given key is invalid.

    Fetches available spaces from Confluence and fuzzy-matches against them.
    Designed to be lightweight — single API call, no caching.

    Args:
        space_key_input: The invalid space key the user provided.
        fetcher: A ConfluenceFetcher instance.

    Returns:
        List of similar space keys, best matches first.
    """
    try:
        spaces_response = fetcher.get_spaces(limit=100)
        results = spaces_response.get("results", [])
        space_keys = [s["key"] for s in results if "key" in s]
    except Exception:
        logger.debug("Failed to fetch spaces for suggestions", exc_info=True)
        return []

    return fuzzy_match(space_key_input, space_keys)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/utils/test_suggestions.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/mcp_atlassian/utils/suggestions.py tests/unit/utils/test_suggestions.py
git commit -m "feat(confluence): add suggest_spaces helper for space key recovery"
```

---

### Task 4: Wire space key recovery into `get_page` tool

**Files:**
- Modify: `src/mcp_atlassian/servers/confluence.py` (lines 263-274)
- Modify: `tests/unit/servers/test_confluence_server.py`

**Context:** Currently at line 263-274 of `servers/confluence.py`, when `get_page_by_title` returns `None`, the tool returns `{"error": "Page with title '...' not found in space '...'"}`. We need to:
1. First validate the space_key itself
2. If space_key is invalid and a single match exists → auto-correct and retry
3. If space_key is valid but page not found → that's Phase 2 (next task)

**Step 1: Write failing test for space key auto-correction in get_page**

Add a new test class in `tests/unit/servers/test_confluence_server.py`. Follow the existing mock patterns (see `mock_confluence_fetcher` fixture at top of file). The test should verify that when `get_page_by_title` returns `None` due to a bad space key, and `suggest_spaces` finds a match, the tool auto-corrects.

The exact test structure depends on the existing test harness — use the `mock_confluence_fetcher` fixture and the FastMCP `Client` pattern already in the file. The test should:
- Mock `get_page_by_title` to return `None` on first call (bad key), return a page on second call (corrected key)
- Mock `get_spaces` to return a space list containing the corrected key
- Assert the response contains the page data AND a correction note

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/servers/test_confluence_server.py::TestGetPageSpaceKeyRecovery -v`
Expected: FAIL

**Step 3: Implement space key recovery in `get_page`**

In `src/mcp_atlassian/servers/confluence.py`, modify the `elif title and space_key:` block (lines 263-274). After `get_page_by_title` returns `None`:

```python
elif title and space_key:
    page_object = confluence_fetcher.get_page_by_title(
        space_key, title, convert_to_markdown=convert_to_markdown
    )
    if not page_object:
        # Attempt space key recovery
        from mcp_atlassian.utils.suggestions import suggest_spaces, format_suggestions

        suggestions = suggest_spaces(space_key, confluence_fetcher)
        if len(suggestions) == 1 and suggestions[0].lower() == space_key.lower():
            # High-confidence match (case mismatch) — auto-correct
            corrected_key = suggestions[0]
            page_object = confluence_fetcher.get_page_by_title(
                corrected_key, title, convert_to_markdown=convert_to_markdown
            )
            if page_object:
                # Build response with correction note
                if include_metadata:
                    result = {"metadata": page_object.to_simplified_dict()}
                else:
                    result = {"content": {"value": page_object.content}}
                result["note"] = (
                    f"Corrected space_key '{space_key}' to '{corrected_key}'"
                )
                return json.dumps(result, indent=2, ensure_ascii=False)

        # Could not auto-correct — return suggestions
        if suggestions:
            return json.dumps(
                format_suggestions(
                    f"Page with title '{title}' not found in space '{space_key}'.",
                    suggestions,
                    hint="Space keys are case-sensitive uppercase. Try one of the suggestions.",
                ),
                indent=2,
                ensure_ascii=False,
            )

        return json.dumps(
            {
                "error": f"Page with title '{title}' not found in space '{space_key}'.",
                "hint": "Use the list_spaces tool to discover available space keys.",
            },
            indent=2,
            ensure_ascii=False,
        )
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/servers/test_confluence_server.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add src/mcp_atlassian/servers/confluence.py tests/unit/servers/test_confluence_server.py
git commit -m "feat(confluence): add space key recovery to get_page tool"
```

---

### Task 5: Wire space key recovery into remaining Confluence tools

**Files:**
- Modify: `src/mcp_atlassian/servers/confluence.py`
- Modify: `tests/unit/servers/test_confluence_server.py`

Apply the same pattern from Task 4 to:
- `create_page` (line ~784) — validate space_key before calling `confluence_fetcher.create_page`
- `get_space_page_tree` (line ~466) — validate space_key before calling `get_space_page_tree`
- `search` (line ~142) — validate `spaces_filter` if provided

**Extract a shared helper** to avoid duplication. Add to `servers/confluence.py`:

```python
def _validate_or_correct_space_key(
    space_key: str, fetcher: ConfluenceFetcher
) -> tuple[str, str | None]:
    """Validate a space key, attempting auto-correction if invalid.

    Returns:
        Tuple of (corrected_key, correction_note). If no correction needed,
        correction_note is None. If space_key is invalid and cannot be
        corrected, raises ValueError with suggestions.
    """
```

Write tests for each tool's space key recovery, then implement. Follow the same Red/Green pattern: failing test → minimal implementation → passing test → commit.

One commit per tool is fine, or batch them if the pattern is identical.

---

### Task 6: Page title recovery (Phase 2)

**Files:**
- Modify: `src/mcp_atlassian/servers/confluence.py` (lines 263-274, inside get_page)
- Modify: `tests/unit/servers/test_confluence_server.py`

**Context:** After space_key is validated (Phase 1), if `get_page_by_title` still returns `None`, search for similar titles using CQL.

**Step 1: Write failing test**

Test that when title doesn't match exactly, the tool searches for similar titles and either auto-corrects (single confident match) or suggests alternatives.

**Step 2: Run test to verify it fails**

**Step 3: Implement title recovery**

After the Phase 1 space key recovery block in `get_page`, add title recovery:

```python
# Space key is valid but page not found — try title recovery
from mcp_atlassian.utils.suggestions import fuzzy_match, format_suggestions

try:
    search_results = confluence_fetcher.search(
        f'title ~ "{title}" AND space = "{space_key}"', limit=5
    )
    similar_titles = [p.title for p in search_results if p.title]
except Exception:
    similar_titles = []

if similar_titles:
    matches = fuzzy_match(title, similar_titles)
    if len(matches) == 1:
        # Auto-correct: fetch the matched page
        page_object = confluence_fetcher.get_page_by_title(
            space_key, matches[0], convert_to_markdown=convert_to_markdown
        )
        if page_object:
            if include_metadata:
                result = {"metadata": page_object.to_simplified_dict()}
            else:
                result = {"content": {"value": page_object.content}}
            result["note"] = f"Corrected title '{title}' to '{matches[0]}'"
            return json.dumps(result, indent=2, ensure_ascii=False)

    if matches:
        return json.dumps(
            format_suggestions(
                f"Page with title '{title}' not found in space '{space_key}'.",
                matches,
                hint="Similar page titles found. Try one of the suggestions.",
            ),
            indent=2,
            ensure_ascii=False,
        )
```

**Step 4: Run tests to verify they pass**

**Step 5: Commit**

```bash
git add src/mcp_atlassian/servers/confluence.py tests/unit/servers/test_confluence_server.py
git commit -m "feat(confluence): add page title recovery with fuzzy matching"
```

---

### Task 7: Partial results metadata (Phase 3)

**Files:**
- Modify: `src/mcp_atlassian/servers/confluence.py` (get_space_page_tree tool, line ~466-468)
- Modify: `tests/unit/servers/test_confluence_server.py`

**Step 1: Write failing test**

Test that when the page tree returns exactly `limit` results, the response includes `has_more: true` and `next_start`.

**Step 2: Run test to verify it fails**

**Step 3: Implement**

In the `get_space_page_tree` server tool (line ~466-468):

```python
confluence_fetcher = await get_confluence_fetcher(ctx)
tree_data = confluence_fetcher.get_space_page_tree(space_key=space_key, limit=limit)

# Add pagination metadata
total_pages = tree_data.get("total_pages", 0)
if total_pages >= limit:
    tree_data["has_more"] = True
    tree_data["next_start"] = limit
    tree_data["hint"] = f"Results may be truncated at {limit}. Increase limit or paginate."
else:
    tree_data["has_more"] = False

return json.dumps(tree_data, indent=2, ensure_ascii=False)
```

**Step 4: Run tests to verify they pass**

**Step 5: Commit**

```bash
git add src/mcp_atlassian/servers/confluence.py tests/unit/servers/test_confluence_server.py
git commit -m "feat(confluence): add partial results metadata to page tree"
```

---

### Task 8: Toolset-aware error messages (Phase 4)

**Files:**
- Modify: `src/mcp_atlassian/servers/main.py`
- Modify: `src/mcp_atlassian/utils/toolsets.py`
- Create: `tests/unit/servers/test_tool_error_recovery.py`

**Context:** There is no `call_tool` override in `AtlassianMCP`. We need to add one that catches unknown-tool errors and provides helpful messages about which toolset the tool belongs to.

**Step 1: Write failing test for toolset lookup helper**

In `tests/unit/utils/test_toolsets.py`, add:

```python
from mcp_atlassian.utils.toolsets import find_tool_toolset


class TestFindToolToolset:
    """Tests for find_tool_toolset()."""

    def test_finds_known_tool(self):
        result = find_tool_toolset("jira_get_sprints_from_board")
        assert result is not None
        # Result should contain toolset name

    def test_unknown_tool_returns_none(self):
        result = find_tool_toolset("completely_fake_tool")
        assert result is None
```

**Step 2: Run test to verify it fails**

**Step 3: Add `find_tool_toolset` to `toolsets.py`**

This function needs to know which tools belong to which toolsets. The toolset tags are on the tool objects themselves (set at registration time), not in `toolsets.py`. So we need to scan all registered tools.

Add a helper that accepts the `all_tools` dict (from `AtlassianMCP.get_tools()`) and a tool name, and returns the toolset name if found:

```python
def find_tool_toolset_from_registry(
    tool_name: str, all_tools: dict[str, object]
) -> str | None:
    """Find which toolset a tool belongs to by checking its tags.

    Args:
        tool_name: The tool name to look up.
        all_tools: Dict of all registered tools (from get_tools()).

    Returns:
        Toolset name if found, None otherwise.
    """
    tool = all_tools.get(tool_name)
    if tool is None:
        return None
    tags = getattr(tool, "tags", set())
    return get_toolset_tag(tags)
```

**Step 4: Write failing test for `_call_tool_mcp` override**

In `tests/unit/servers/test_tool_error_recovery.py`:

```python
"""Tests for toolset-aware error messages in call_tool."""

# Test that calling a filtered-out tool returns a helpful error
# explaining which toolset it belongs to and how to enable it.
```

**Step 5: Implement `_call_tool_mcp` override in `AtlassianMCP`**

In `src/mcp_atlassian/servers/main.py`, add a `_call_tool_mcp` method override. When the base class raises a "tool not found" error, catch it, look up the tool in the full registry, and return a helpful message.

**Step 6: Run all tests**

Run: `uv run pytest tests/unit/ -v`
Expected: All PASS

**Step 7: Commit**

```bash
git add src/mcp_atlassian/servers/main.py src/mcp_atlassian/utils/toolsets.py tests/
git commit -m "feat(server): add toolset-aware error messages for filtered tools"
```

---

### Task 9: Final integration test and cleanup

**Files:**
- Modify: `src/mcp_atlassian/utils/__init__.py` — export new functions if needed
- Review all changes for lint/type compliance

**Step 1: Run full test suite**

Run: `uv run pytest tests/ -x -v`
Expected: All PASS

**Step 2: Run linting and type checking**

Run: `uv run pre-commit run --all-files`
Expected: All PASS

**Step 3: Final commit if any cleanup needed**

**Step 4: Push and create PR**

```bash
git push -u origin feat/error-recovery-24
gh pr create \
  --repo Troubladore/mcp-atlassian \
  --base team/main \
  --head feat/error-recovery-24 \
  --title "feat: intelligent error recovery with fuzzy matching (#24)" \
  --body "..."
```
