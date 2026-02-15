# Token Efficiency Audit

Based on "MCPs are not like other APIs" (https://blog.fsck.com/2025/10/19/mcps-are-not-like-other-apis/)

## Current State

**Estimated token count at startup:** ~37,000 tokens (148KB server code)
**Target (per article):** <1,000 tokens
**Gap:** 36x too large

## Key Principles We're Violating

### 1. Verbose Parameter Descriptions

**Current (confluence_get_page):**
```python
page_id: "Confluence page ID (numeric ID, can be found in the page URL). "
         "For example, in the URL 'https://example.atlassian.net/wiki/spaces/TEAM/pages/123456789/Page+Title', "
         "the page ID is '123456789'. "
         "Provide this OR both 'title' and 'space_key'. If page_id is provided, title and space_key will be ignored."
```
**Tokens:** ~50

**Should be:**
```python
page_id: "Page ID from URL or use title+space_key"
```
**Tokens:** ~5

**Savings:** 90% reduction per parameter × 3-5 parameters per tool × 32 tools = **massive**

### 2. No Automatic Recovery

**Current:** If page_id invalid → error
**Should be:** If page_id invalid → try searching by partial title, suggest matches

**Current:** Require exact space_key
**Should be:** If space_key wrong, search for similar spaces and auto-correct

### 3. Rigid Parameter Requirements

**Current:** `confluence_get_page` requires page_id OR (title AND space_key)
**Should be:** Accept a URL and extract everything automatically

Example:
```python
# Current: User must parse URL themselves
get_page(page_id="123456789")

# Better: Tool parses URL automatically
get_page(url="https://eruditis.atlassian.net/wiki/spaces/TEAM/pages/123456789/Page+Title")
# Auto-extracts: space_key="TEAM", page_id="123456789"
```

### 4. Multiple Tools for Similar Operations

**Current:**
- `confluence_get_page` (by ID or title)
- `confluence_search` (search by query)
- Could add: `confluence_get_page_by_url`

**Should be:** ONE tool that handles all cases:
```python
get_content(identifier="123456789")  # page ID
get_content(identifier="Page Title", space="TEAM")  # title lookup
get_content(identifier="https://...pages/123/Title")  # URL parsing
get_content(identifier="search term")  # Falls back to search
```

### 5. Failing Fast Instead of Partial Results

**Current:** `get_space_page_tree` with limit=500 loads all 500 or fails
**Better:** Return first 100 with `has_more: true`, let AI request more if needed

**Current:** Page not found → error
**Better:** Page not found → return similar pages with message

## Recommended Refactoring (Priority Order)

### Phase 1: Description Cleanup (Immediate, No Breaking Changes)

**Impact:** ~60% token reduction
**Effort:** Low (find/replace)

- Reduce all parameter descriptions to 1 sentence max
- Remove examples from descriptions (put in docstring if needed)
- Remove implementation details ("If X is provided, Y is ignored")
- Remove teaching content ("can be found in the page URL")

### Phase 2: Auto-Recovery (Medium Effort, High Value)

**Impact:** Better UX, fewer retries
**Effort:** Medium

- Add URL parsing to `get_page` (auto-extract page_id/space_key)
- Auto-suggest similar spaces if space_key typo
- Auto-search if page_id not found
- Return partial results instead of errors

### Phase 3: Consolidate Tools (Breaking Change, Defer)

**Impact:** Fewer tools = smaller context
**Effort:** High (breaking change)

- Merge get_page + search into smart `get_content(identifier)`
- Merge create + update into `save_page` (auto-detect if exists)
- Merge move_page_position + update_page parent_id into `move_page`

## Specific Tool Audit

### confluence_get_page
- **Current tokens:** ~150 (parameter descriptions alone)
- **Target:** ~30
- **Actions:**
  - Reduce descriptions by 80%
  - Add URL auto-parsing
  - Auto-search fallback if not found

### confluence_create_page
- **Current:** Requires space_key, title, body
- **Better:** Auto-detect space from context, suggest parent based on current page
- **Auto-recover:** If space_key invalid, search for similar spaces

### confluence_get_space_page_tree
- **Current:** Returns all pages up to limit
- **Better:** ✅ Already improved (JSON format, reduced default limit)
- **Could improve:** Add depth_limit parameter (only return pages up to depth N)

### confluence_move_page_position
- **Current:** Requires page_id, position, target_id (rigid)
- **Better:** Could accept "move page X after page Y" and parse
- **Auto-recover:** If target_id not found, suggest similar pages

## Anti-Patterns Found

❌ **Teaching in descriptions** - "For example, in the URL..."
❌ **Implementation details** - "If page_id is provided, X is ignored"
❌ **Redundant explanations** - Both Field description AND docstring say same thing
❌ **No graceful degradation** - Errors instead of partial results
❌ **No auto-correction** - Exact matches required
❌ **Verbose field names** - `spaces_filter` could be `spaces`

## Division of Responsibility

**MCP Layer (mcp-atlassian):**
- Thin, helpful data access
- Auto-parse URLs to extract page_id/space_key
- Auto-suggest fixes for typos (fuzzy match space_keys)
- Return partial results when possible
- Clear error messages with suggestions
- Minimal token footprint (<10 words per parameter)

**Skill Layer (.claude/skills/confluence-navigation):**
- Eruditis-specific conventions ("Eruditis" is default space)
- Progressive disclosure (start with 50 pages, drill down)
- Workflow intelligence (discover → create → position)
- Company naming patterns

## Immediate Actions (This Session)

1. ✅ Create PARAMETER_DESCRIPTION_STYLE_GUIDE.md
2. ✅ Create confluence-navigation skill
3. TODO: Reduce all Confluence parameter descriptions to <10 words
4. TODO: Add URL auto-parsing to confluence_get_page
5. TODO: Add fuzzy space_key matching with suggestions
6. TODO: Return partial results instead of hard errors

## Long-Term Refactoring (Future PR)

1. Consolidate similar tools (breaking change)
2. Add smart fallbacks to all tools
3. Make all parameters as flexible as possible
4. Add progressive disclosure (depth limits, pagination hints)

## Quote to Remember

> "Build your tools like they're a set of scripts you're handing to that
> undertrained kid who just got hired in the NOC. They are going to page you
> at 2AM when they can't figure out what's going on."

Our tools currently assume Claude is an expert who knows:
- Exact parameter formats
- Confluence URL structure
- When to use page_id vs title+space_key
- How to recover from errors

We should assume Claude is that NOC kid who needs:
- Tools that "just work" with whatever input they get
- Helpful suggestions when things go wrong
- Automatic fallbacks
- Plain English errors
