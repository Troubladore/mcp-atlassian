# Content Properties Integration — Design

**Date:** 2026-03-25
**Source:** Upstream PR #1174 (kbichave) — content properties tools
**Approach:** Integrate capability, refactor tool exposure per Phase C (#1201)

## Context

PR #1174 adds a `PropertiesMixin` with `get_content_properties` / `set_content_property`
and two standalone tools. Phase C says these should fold into existing tools.

Discovery: `PagesMixin` already has `_set_single_property`, `_get_page_width`, and
`_set_page_width` — private helpers that use the atlassian-python-api library methods
(`get_page_property`, `set_page_property`, `update_page_property`). PR #1174 duplicates
this with raw `_session` calls.

## Decision

- **Skip `PropertiesMixin`** — no new file, no new mixin
- **Add public methods to `PagesMixin`** that generalize existing private helpers
- **Read:** `get_page(include="properties")` — same enrichment pattern as comments/labels/views
- **Write:** One new tool `confluence_set_content_property` — because property-only writes can't be expressed as a param on `update_page` (which requires title+content)
- **Net tool count:** +1 (not +2)

## Mixin Layer (PagesMixin)

### `get_content_properties(page_id, key=None) -> dict[str, Any]`

- `key=None`: `self.confluence.get_page_properties(page_id)` → `{k: v for each result}`
- `key` provided: `self.confluence.get_page_property(page_id, key)` → `{key: value}`
- Exceptions propagate — no broad `except Exception` wrapping

### `set_content_property(page_id, key, value) -> dict[str, Any]`

- Generalizes `_set_single_property` to accept `Any` values (dict, list, string)
- Same create-or-update-with-version-increment logic
- Returns `{key: value}`
- Existing `_set_page_width` / `_set_page_emoji` continue using `_set_single_property`

## Tool Layer

### `get_page` — add `"properties"` to `include` param

```python
if "properties" in sections:
    try:
        props = confluence_fetcher.get_content_properties(resolved_page_id)
        result["properties"] = props
    except Exception:
        logger.warning("Failed to inline properties for page %s", resolved_page_id)
        result["properties"] = {}
```

### `confluence_set_content_property` — new tool

- Params: `page_id: str`, `key: str`, `value: str` (JSON string, parsed server-side)
- Tags: `{"confluence", "write", "toolset:confluence_pages"}`
- Annotations: `{"title": "Set Content Property", "destructiveHint": True}`
- `@check_write_access`
- Returns JSON `{key: value}`

## Tests (13 total)

### Mixin tests (test_pages.py)

1. `get_content_properties` — all properties returned
2. `get_content_properties` — empty results
3. `get_content_properties` — single key
4. `get_content_properties` — API error propagates
5. `set_content_property` — creates when not exists
6. `set_content_property` — updates existing with version increment
7. `set_content_property` — missing version defaults to 1
8. `set_content_property` — API error on update propagates
9. `set_content_property` — API error on create propagates
10. `set_content_property` — dict/list values (JSON objects)

### Tool-level tests

11. `get_page` with `include="properties"` inlines properties
12. `set_content_property` tool — valid JSON value
13. `set_content_property` tool — invalid JSON value raises ValueError

### Tool count

Update assertion: 28 → 29

---

# Content Properties — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expose arbitrary Confluence content properties via `get_page(include="properties")` for reads and a single `confluence_set_content_property` tool for writes, integrating PR #1174's capability without adding standalone getter tools.

**Architecture:** Two new public methods on `PagesMixin` wrapping existing atlassian-python-api library calls. Read-side wired into the existing `include` enrichment pattern on `get_page`. Write-side as one new FastMCP tool. TDD throughout — all tests written before implementation.

**Tech Stack:** Python 3.10+, FastMCP, atlassian-python-api, pytest, Pydantic v2

---

### Task 1: Mixin — `get_content_properties` (tests)

**Files:**
- Modify: `tests/unit/confluence/test_pages.py` (append after `TestPageWidth` class, ~line 2600)

**Step 1: Write the failing tests**

Add a new test class after `TestPageWidth`. Uses the same fixture pattern as `TestPageWidth`.

```python
class TestContentProperties:
    """Tests for arbitrary content property get/set."""

    @pytest.fixture
    def pages_mixin(self, confluence_client):
        """Create a PagesMixin instance for testing."""
        with patch(
            "mcp_atlassian.confluence.pages.ConfluenceClient.__init__"
        ) as mock_init:
            mock_init.return_value = None
            mixin = PagesMixin()
            mixin.confluence = confluence_client.confluence
            mixin.config = confluence_client.config
            mixin.preprocessor = confluence_client.preprocessor
            return mixin

    def test_get_content_properties_all(self, pages_mixin):
        """Get all properties returns {key: value} dict."""
        pages_mixin.confluence.get_page_properties.return_value = {
            "results": [
                {"key": "content-appearance-published", "value": "full-width"},
                {"key": "content-appearance-draft", "value": "fixed-width"},
            ]
        }

        result = pages_mixin.get_content_properties("123456789")

        pages_mixin.confluence.get_page_properties.assert_called_once_with("123456789")
        assert result == {
            "content-appearance-published": "full-width",
            "content-appearance-draft": "fixed-width",
        }

    def test_get_content_properties_empty(self, pages_mixin):
        """Empty results return empty dict."""
        pages_mixin.confluence.get_page_properties.return_value = {"results": []}

        result = pages_mixin.get_content_properties("123456789")

        assert result == {}

    def test_get_content_properties_single_key(self, pages_mixin):
        """Single key returns only that property."""
        pages_mixin.confluence.get_page_property.return_value = {
            "key": "content-appearance-published",
            "value": "full-width",
            "version": {"number": 2},
        }

        result = pages_mixin.get_content_properties(
            "123456789", key="content-appearance-published"
        )

        pages_mixin.confluence.get_page_property.assert_called_once_with(
            "123456789", "content-appearance-published"
        )
        assert result == {"content-appearance-published": "full-width"}

    def test_get_content_properties_api_error(self, pages_mixin):
        """API errors propagate without wrapping."""
        pages_mixin.confluence.get_page_properties.side_effect = Exception("API error")

        with pytest.raises(Exception, match="API error"):
            pages_mixin.get_content_properties("123456789")
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/confluence/test_pages.py::TestContentProperties -xvs -W error`
Expected: FAIL — `AttributeError: 'PagesMixin' object has no attribute 'get_content_properties'`

**Step 3: Commit**

```bash
git add tests/unit/confluence/test_pages.py
git commit -m "test(confluence): add get_content_properties tests (red)"
```

---

### Task 2: Mixin — `get_content_properties` (implementation)

**Files:**
- Modify: `src/mcp_atlassian/confluence/pages.py` (add method after `_get_page_width`, ~line 337)

**Step 1: Write minimal implementation**

Add after `_get_page_width` method (before `_set_page_width`):

```python
def get_content_properties(
    self, page_id: str, key: str | None = None
) -> dict[str, Any]:
    """Get content properties for a Confluence page.

    Args:
        page_id: The ID of the page.
        key: Optional property key. If provided, returns only that property.
            If omitted, returns all properties as a ``{key: value}`` dict.

    Returns:
        Dict mapping property key(s) to their values.
    """
    if key:
        prop = self.confluence.get_page_property(page_id, key)
        return {prop["key"]: prop["value"]}

    properties = self.confluence.get_page_properties(page_id)
    return {
        item["key"]: item["value"]
        for item in properties.get("results", [])
    }
```

Ensure `from typing import Any` is already imported at top of file (it is — used by existing methods).

**Step 2: Run tests to verify they pass**

Run: `uv run pytest tests/unit/confluence/test_pages.py::TestContentProperties -xvs -W error`
Expected: 4 PASSED

**Step 3: Commit**

```bash
git add src/mcp_atlassian/confluence/pages.py
git commit -m "feat(confluence): add get_content_properties to PagesMixin"
```

---

### Task 3: Mixin — `set_content_property` (tests)

**Files:**
- Modify: `tests/unit/confluence/test_pages.py` (append to `TestContentProperties` class)

**Step 1: Write the failing tests**

Append these methods to the `TestContentProperties` class:

```python
    def test_set_content_property_creates_when_not_exists(self, pages_mixin):
        """Property that doesn't exist is created via set_page_property."""
        pages_mixin.confluence.get_page_property.side_effect = Exception("Not found")
        pages_mixin.confluence.set_page_property.return_value = {
            "key": "custom-key",
            "value": "custom-value",
        }

        result = pages_mixin.set_content_property(
            "123456789", "custom-key", "custom-value"
        )

        pages_mixin.confluence.set_page_property.assert_called_once_with(
            "123456789", {"key": "custom-key", "value": "custom-value"}
        )
        assert result == {"custom-key": "custom-value"}

    def test_set_content_property_updates_existing(self, pages_mixin):
        """Existing property is updated with version increment."""
        pages_mixin.confluence.get_page_property.return_value = {
            "key": "content-appearance-published",
            "value": "fixed-width",
            "version": {"number": 2},
        }
        pages_mixin.confluence.update_page_property.return_value = None

        result = pages_mixin.set_content_property(
            "123456789", "content-appearance-published", "full-width"
        )

        pages_mixin.confluence.update_page_property.assert_called_once_with(
            "123456789",
            {
                "key": "content-appearance-published",
                "value": "full-width",
                "version": {"number": 3},
            },
        )
        assert result == {"content-appearance-published": "full-width"}

    def test_set_content_property_version_defaults_to_1(self, pages_mixin):
        """Missing version info defaults to version 1."""
        pages_mixin.confluence.get_page_property.return_value = {
            "key": "custom-key",
            "value": "old",
        }
        pages_mixin.confluence.update_page_property.return_value = None

        result = pages_mixin.set_content_property("123456789", "custom-key", "new")

        call_data = pages_mixin.confluence.update_page_property.call_args[0][1]
        assert call_data["version"]["number"] == 1

    def test_set_content_property_dict_value(self, pages_mixin):
        """Dict values (JSON objects) are supported."""
        pages_mixin.confluence.get_page_property.side_effect = Exception("Not found")
        pages_mixin.confluence.set_page_property.return_value = {
            "key": "editor",
            "value": {"version": 2},
        }

        result = pages_mixin.set_content_property(
            "123456789", "editor", {"version": 2}
        )

        pages_mixin.confluence.set_page_property.assert_called_once_with(
            "123456789", {"key": "editor", "value": {"version": 2}}
        )
        assert result == {"editor": {"version": 2}}

    def test_set_content_property_api_error_on_update(self, pages_mixin):
        """API error during update propagates."""
        pages_mixin.confluence.get_page_property.return_value = {
            "key": "k",
            "value": "v",
            "version": {"number": 1},
        }
        pages_mixin.confluence.update_page_property.side_effect = Exception(
            "Version conflict"
        )

        with pytest.raises(Exception, match="Version conflict"):
            pages_mixin.set_content_property("123456789", "k", "new")

    def test_set_content_property_api_error_on_create(self, pages_mixin):
        """API error during create propagates."""
        pages_mixin.confluence.get_page_property.side_effect = Exception("Not found")
        pages_mixin.confluence.set_page_property.side_effect = Exception("Bad request")

        with pytest.raises(Exception, match="Bad request"):
            pages_mixin.set_content_property("123456789", "k", "v")
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/confluence/test_pages.py::TestContentProperties -xvs -W error`
Expected: First 4 pass, new 6 FAIL — `AttributeError: 'PagesMixin' object has no attribute 'set_content_property'`

**Step 3: Commit**

```bash
git add tests/unit/confluence/test_pages.py
git commit -m "test(confluence): add set_content_property tests (red)"
```

---

### Task 4: Mixin — `set_content_property` (implementation)

**Files:**
- Modify: `src/mcp_atlassian/confluence/pages.py` (add method after `get_content_properties`)

**Step 1: Write minimal implementation**

Add after `get_content_properties`:

```python
def set_content_property(
    self, page_id: str, key: str, value: Any
) -> dict[str, Any]:
    """Create or update a content property on a Confluence page.

    Handles version increment automatically. Reads the current version
    before writing, so callers do not need to manage version numbers.

    Args:
        page_id: The ID of the page.
        key: Property key (e.g. ``content-appearance-published``).
        value: Property value. Strings, dicts, and lists are all supported.

    Returns:
        Dict with ``{key: value}`` of the created or updated property.
    """
    property_data: dict[str, Any] = {"key": key, "value": value}

    # Check if property exists (need version for update)
    existing_version = None
    try:
        existing = self.confluence.get_page_property(page_id, key)
        if existing and isinstance(existing, dict):
            existing_version = existing.get("version", {}).get("number")
    except Exception:  # noqa: BLE001
        # Property doesn't exist — will create it
        pass

    if existing_version is not None:
        property_data["version"] = {"number": existing_version + 1}
        self.confluence.update_page_property(page_id, property_data)
    else:
        self.confluence.set_page_property(page_id, property_data)

    return {key: value}
```

**Step 2: Run tests to verify they pass**

Run: `uv run pytest tests/unit/confluence/test_pages.py::TestContentProperties -xvs -W error`
Expected: 10 PASSED

**Step 3: Commit**

```bash
git add src/mcp_atlassian/confluence/pages.py
git commit -m "feat(confluence): add set_content_property to PagesMixin"
```

---

### Task 5: Tool — `get_page` include="properties" (tests)

**Files:**
- Modify: `tests/unit/servers/test_confluence_server.py` (add after `test_get_page_include_views_graceful_degradation`, ~line 870)

**Step 1: Write the failing test**

Add after the existing include tests:

```python
@pytest.mark.anyio
async def test_get_page_include_properties(client, mock_confluence_fetcher):
    """Test get_page with include='properties' inlines content properties."""
    mock_confluence_fetcher.get_content_properties.return_value = {
        "content-appearance-published": "full-width",
        "editor": {"version": 2},
    }

    response = await client.call_tool(
        "confluence_get_page", {"page_id": "123456", "include": "properties"}
    )

    mock_confluence_fetcher.get_content_properties.assert_called_once_with("123456")

    result_data = json.loads(response.content[0].text)
    assert "metadata" in result_data
    assert "properties" in result_data
    assert result_data["properties"]["content-appearance-published"] == "full-width"
    assert result_data["properties"]["editor"] == {"version": 2}
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/servers/test_confluence_server.py::test_get_page_include_properties -xvs -W error`
Expected: FAIL — `get_content_properties` not called (no `"properties"` handler in `get_page` yet)

**Step 3: Commit**

```bash
git add tests/unit/servers/test_confluence_server.py
git commit -m "test(confluence): add get_page include=properties test (red)"
```

---

### Task 6: Tool — `get_page` include="properties" (implementation)

**Files:**
- Modify: `src/mcp_atlassian/servers/confluence.py` (two changes)

**Step 1: Update include param description**

At line 188, change the description string from:
```
"comments, labels, views"
```
to:
```
"comments, labels, views, properties"
```

**Step 2: Add properties enrichment block**

After the `"views"` enrichment block (~line 302), add:

```python
        if "properties" in sections:
            try:
                props = confluence_fetcher.get_content_properties(resolved_page_id)
                result["properties"] = props
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Failed to inline properties for page %s",
                    resolved_page_id,
                )
                result["properties"] = {}
```

**Step 3: Run test to verify it passes**

Run: `uv run pytest tests/unit/servers/test_confluence_server.py::test_get_page_include_properties -xvs -W error`
Expected: PASS

**Step 4: Commit**

```bash
git add src/mcp_atlassian/servers/confluence.py
git commit -m "feat(confluence): add properties to get_page include param"
```

---

### Task 7: Tool — `confluence_set_content_property` (tests)

**Files:**
- Modify: `tests/unit/servers/test_confluence_server.py` (append near end of file)

**Step 1: Write the failing tests**

```python
@pytest.mark.anyio
async def test_set_content_property_valid_json(client, mock_confluence_fetcher):
    """Test set_content_property with valid JSON string value."""
    mock_confluence_fetcher.set_content_property.return_value = {
        "content-appearance-published": "full-width"
    }

    response = await client.call_tool(
        "confluence_set_content_property",
        {
            "page_id": "123456",
            "key": "content-appearance-published",
            "value": '"full-width"',
        },
    )

    mock_confluence_fetcher.set_content_property.assert_called_once_with(
        "123456", "content-appearance-published", "full-width"
    )

    result_data = json.loads(response.content[0].text)
    assert result_data["content-appearance-published"] == "full-width"


@pytest.mark.anyio
async def test_set_content_property_json_object(client, mock_confluence_fetcher):
    """Test set_content_property with JSON object value."""
    mock_confluence_fetcher.set_content_property.return_value = {
        "editor": {"version": 2}
    }

    response = await client.call_tool(
        "confluence_set_content_property",
        {
            "page_id": "123456",
            "key": "editor",
            "value": '{"version": 2}',
        },
    )

    mock_confluence_fetcher.set_content_property.assert_called_once_with(
        "123456", "editor", {"version": 2}
    )

    result_data = json.loads(response.content[0].text)
    assert result_data["editor"] == {"version": 2}


@pytest.mark.anyio
async def test_set_content_property_invalid_json(client, mock_confluence_fetcher):
    """Test set_content_property rejects invalid JSON value."""
    response = await client.call_tool(
        "confluence_set_content_property",
        {
            "page_id": "123456",
            "key": "some-key",
            "value": "not valid json",
        },
    )

    result_text = response.content[0].text
    assert "valid JSON" in result_text or "error" in result_text.lower()
    mock_confluence_fetcher.set_content_property.assert_not_called()
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/servers/test_confluence_server.py::test_set_content_property_valid_json -xvs -W error`
Expected: FAIL — tool `confluence_set_content_property` does not exist

**Step 3: Commit**

```bash
git add tests/unit/servers/test_confluence_server.py
git commit -m "test(confluence): add set_content_property tool tests (red)"
```

---

### Task 8: Tool — `confluence_set_content_property` (implementation)

**Files:**
- Modify: `src/mcp_atlassian/servers/confluence.py` (append at end of file)

**Step 1: Add the tool function**

Append at end of file:

```python
@confluence_mcp.tool(
    tags={"confluence", "write", "toolset:confluence_pages"},
    annotations={"title": "Set Content Property", "destructiveHint": True},
)
@check_write_access
async def set_content_property(
    ctx: Context,
    page_id: Annotated[
        str,
        Field(
            description=(
                "Confluence page ID (numeric string from the page URL, "
                "e.g. '123456789')."
            )
        ),
    ],
    key: Annotated[
        str,
        Field(
            description=(
                "Property key to create or update. "
                "Well-known keys: 'content-appearance-published', "
                "'content-appearance-draft' (values: 'full-width' or 'fixed-width'), "
                "'editor' (value: '{\"version\": 2}'). "
                "Custom keys are also supported for app metadata."
            )
        ),
    ],
    value: Annotated[
        str,
        Field(
            description=(
                "Property value as a JSON string. "
                "Examples: '\"full-width\"' for a string value, "
                "'{\"version\": 2}' for an object value. "
                "The version number is managed automatically."
            )
        ),
    ],
) -> str:
    """Create or update a content property on a Confluence page.

    Performs an upsert: creates the property if it does not exist, or updates
    it if it does. The Confluence API version number is incremented automatically
    so callers never need to manage it.

    Common use cases:
    - Switch page to full-width layout: key='content-appearance-published',
      value='"full-width"'
    - Switch page to fixed-width layout: key='content-appearance-published',
      value='"fixed-width"'
    - Set editor version: key='editor', value='{"version": 2}'

    Args:
        ctx: The FastMCP context.
        page_id: Confluence page ID.
        key: Property key to create or update.
        value: Property value as a JSON string.

    Returns:
        JSON object with the resulting ``{key: value}`` pair.

    Raises:
        ValueError: If the value is not valid JSON or in read-only mode.
    """
    try:
        parsed_value = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"'value' must be a valid JSON string (e.g. '\"full-width\"' or "
            f"'{{\"version\": 2}}'). Got: {value!r}"
        ) from exc

    confluence_fetcher = await get_confluence_fetcher(ctx)
    result = confluence_fetcher.set_content_property(page_id, key, parsed_value)
    return json.dumps(result, indent=2, ensure_ascii=False)
```

**Step 2: Run tool tests to verify they pass**

Run: `uv run pytest tests/unit/servers/test_confluence_server.py::test_set_content_property_valid_json tests/unit/servers/test_confluence_server.py::test_set_content_property_json_object tests/unit/servers/test_confluence_server.py::test_set_content_property_invalid_json -xvs -W error`
Expected: 3 PASSED

**Step 3: Commit**

```bash
git add src/mcp_atlassian/servers/confluence.py
git commit -m "feat(confluence): add confluence_set_content_property tool"
```

---

### Task 9: Tool count + full suite

**Files:**
- Modify: `tests/unit/utils/test_toolsets.py:254-258`

**Step 1: Update tool count assertion**

Change line 256-257 from:
```python
        assert len(confluence_tools) == 28, (
            f"Expected 28 Confluence tools, got {len(confluence_tools)}"
```
to:
```python
        assert len(confluence_tools) == 29, (
            f"Expected 29 Confluence tools, got {len(confluence_tools)}"
```

**Step 2: Run full test suite**

Run: `uv run pytest tests/unit/ -x -W error`
Expected: ALL PASSED

**Step 3: Run pre-commit**

Run: `uv run pre-commit run --all-files`
Expected: ALL PASSED

**Step 4: Commit**

```bash
git add tests/unit/utils/test_toolsets.py
git commit -m "test(confluence): update tool count for content properties (+1)"
```
