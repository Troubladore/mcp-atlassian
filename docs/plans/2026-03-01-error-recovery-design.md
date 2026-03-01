# Intelligent Error Recovery with Fuzzy Matching and Suggestions

**Issue:** [#24](https://github.com/Troubladore/mcp-atlassian/issues/24)
**Date:** 2026-03-01

## Guiding Principle

MCP tools should behave like a helpful colleague, not a rigid API. When the LLM
provides something slightly wrong, the tool auto-corrects when confident and
suggests alternatives when ambiguous — rather than failing and forcing a retry
loop. (See: [MCPs Are Not Like Other APIs](https://blog.fsck.com/2025/10/19/mcps-are-not-like-other-apis/))

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Recovery behavior | Auto-correct + inform | Single high-confidence match: use it and note the correction. Multiple matches: return suggestions. Minimizes token-expensive retry loops. |
| Architecture | Server layer + thin helpers | Server tools own recovery logic. Client mixins stay unchanged (return None/[]). New `utils/suggestions.py` for reusable fuzzy matching. |
| Partial results | Respect limit + signal | Return requested amount plus `has_more`/`next_start` metadata. LLM decides whether to paginate. |
| Scope | All 4 phases | Space key, page title, partial results, toolset-aware errors. |
| TDD | Red/Green | Write failing tests first, then implement. |

## Architecture

```
LLM client
  │
  ▼
Server tool (servers/confluence.py, servers/jira.py)
  │  ← Recovery logic lives here
  │  ← Calls suggestions.py helpers
  ▼
Client mixin (confluence/pages.py, etc.)
  │  ← Returns None/[] on failure (unchanged)
  ▼
Atlassian API
```

**New module:** `src/mcp_atlassian/utils/suggestions.py`

Pure-function helpers:
- `fuzzy_match(input, candidates, threshold) -> list[Match]` — wraps
  `difflib.get_close_matches` with case-insensitive preprocessing
- `format_suggestions(error_msg, matches, hint?) -> dict` — builds structured
  error response with `error`, `suggestions`, and optional `hint` fields

No new exceptions. No changes to client mixin contracts.

## Phase 1: Space Key Recovery

When a Confluence tool receives an invalid `space_key`:

1. Call `get_spaces()` to fetch available spaces
2. Run `fuzzy_match(input_key, space_keys)`
3. **Single high-confidence match** → auto-correct: use the matched key, prepend
   a note like `"Note: corrected space_key 'eruditis' → 'ERUDITIS'"` to the
   response
4. **Multiple matches** → return suggestions:
   ```json
   {
     "error": "Space 'erud' not found",
     "suggestions": ["ERUDITIS", "ERUDITISARCHIVE"],
     "hint": "Space keys are case-sensitive uppercase"
   }
   ```
5. **No matches** → return plain error with hint to use `list_spaces`

**Applies to:** `get_page`, `create_page`, `get_space_page_tree`,
`search_confluence` (when space_key provided)

## Phase 2: Page Title Recovery

When `get_page_by_title` returns `None`:

1. Use Confluence search API (`cql: title ~ "fuzzy title" AND space = KEY`) to
   find similar titles
2. **Single high-confidence match** → auto-correct and fetch that page, noting
   the correction
3. **Multiple matches** → return error with title suggestions
4. No fuzzy matching for page IDs (numeric, not typo-prone)

**Applies to:** `get_page` (title+space_key path), `create_page` (parent title
validation)

## Phase 3: Partial Results

When paginated tools hit limits:

- Include `has_more: true` and `next_start` in the response when results are
  truncated
- Include `total_available` count if the API provides it
- Additive metadata on successful responses, not error recovery

**Applies to:** `get_space_page_tree` and other paginated endpoints

## Phase 4: Toolset-Aware Error Messages

When a `call_tool` request references a tool not in the filtered list:

1. Look up the tool name across all toolset definitions
2. **Found in disabled toolset** →
   ```json
   {
     "error": "Tool 'jira_get_sprints_from_board' not available",
     "reason": "Part of 'jira_agile' toolset (not enabled)",
     "suggestion": "Set TOOLSETS=default,jira_agile"
   }
   ```
3. **Blocked by read-only/delete filter** → explain which setting to change
4. **Not found anywhere** → standard "unknown tool" error

**Hooks into:** `_list_tools_mcp()` or complementary method in `servers/main.py`
