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

Update assertion: 24 → 25
