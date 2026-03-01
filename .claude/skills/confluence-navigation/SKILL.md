---
name: confluence-navigation
description: Use when working with Eruditis Confluence - provides progressive discovery workflow, space structure understanding, and intelligent page placement
---

# Confluence Navigation for Eruditis

Use this skill when the user asks to work with Confluence pages, create documentation, or organize content in the Eruditis Confluence space.

## Core Philosophy

**Progressive Disclosure:** Start broad, drill down as needed. Don't fetch 500 pages when 20 will do.

**Context-Aware:** The Eruditis space has a standard structure. Use it.

**Intelligent Defaults:** Assume "Eruditis" space unless specified otherwise.

## Standard Workflow

### 1. Discover Before Creating

**When user asks to create a page**, ALWAYS follow this sequence:

```
1. List spaces (if space unclear)
   → Use confluence_list_spaces
   → Default to "Eruditis" for Eruditis work

2. Get high-level structure
   → Use confluence_get_space_page_tree with limit=50
   → This shows top 2-3 levels
   → Enough to understand organization

3. Find the right parent
   → User says "add to MacOS docs"
   → Filter pages by depth and title to find "on MacOS"
   → Use get_page_ancestors to verify it's in the right place

4. Create with proper parent
   → Use confluence_create_page with parent_id

5. Position precisely (if needed)
   → Use confluence_move_page_position to place after/before siblings
```

**Why:** Prevents pages from being created in wrong locations or at the bottom of long lists.

### 2. Handle "Page Not Found" Gracefully

**When a tool returns page not found:**

DO NOT just report the error. Instead:

```
1. Search for similar titles
   → Use confluence_search with the page title
   → Show user top 3 matches

2. Suggest what might be wrong
   → "I couldn't find page 'MacOS Guide'. Did you mean:"
   → "  - MacOS: Claude Code (ID: 2565144621)"
   → "  - MacOS: Claude Desktop (ID: 2465792001)"

3. Ask user to clarify or pick
```

### 3. Use Depth Filtering for Large Spaces

**When tree has >50 pages:**

```
1. Start with depth=0-2 (top levels only)
   → Filter: pages where depth <= 2
   → This shows the major sections

2. User clarifies section
   → "I want to add to MacOS docs"

3. Fetch that subtree
   → Find the "on MacOS" page ID from initial tree
   → Use get_page_children to get full list under that parent
```

**Why:** Loading 500 pages wastes tokens. Most tasks only need one section.

## Eruditis-Specific Conventions

### Default Space
- Assume "Eruditis" space for all work unless specified
- Don't ask "which space?" - just use Eruditis

### Common Structure
Based on actual hierarchy:
```
Eruditis (root)
├── Resources
│   └── How-to articles
│       └── Getting Started
│           └── on MacOS...
│               ├── MacOS: Claude Code
│               └── MacOS: Claude Desktop
└── [other sections]
```

### Naming Patterns
- Platform guides: "on {Platform}..." (e.g., "on MacOS...", "on Windows...")
- Tool docs: "{Platform}: {Tool}" (e.g., "MacOS: Claude Code")
- How-to articles go under Resources > How-to articles

## Error Recovery Patterns

### Space Not Found
```python
# Instead of error, search for similar spaces
spaces = confluence_list_spaces()
similar = [s for s in spaces if space_key.lower() in s['key'].lower()]
if similar:
    return f"Space '{space_key}' not found. Did you mean: {similar[0]['key']}?"
```

### Page Not Found
```python
# Search for similar titles
results = confluence_search(f'title~"{page_title}" AND space={space_key}')
if results:
    return f"Page not found. Similar pages: {[r['title'] for r in results[:3]]}"
```

### Unclear Parent
```python
# If user says "add to MacOS section" but unclear which
# Show the tree filtered to "MacOS" in titles
tree = confluence_get_space_page_tree(space_key="Eruditis", limit=100)
macos_pages = [p for p in tree['pages'] if 'macos' in p['title'].lower()]
# Ask user to pick from the list
```

## Tool Usage Guidelines

### confluence_list_spaces
**When:** User asks about "what spaces exist" or unclear which space to use
**Default:** Skip this for Eruditis work - we know the space

### confluence_get_space_page_tree
**When:** User wants to "see the structure" or before creating pages
**Limit:**
- Start with 50 for quick overview
- Increase to 200 if user needs more detail
- Never use 500 unless explicitly requested

**Post-processing:**
- Filter by depth to show relevant levels
- Filter by title substring to find sections
- Sort by position is already done

### confluence_get_page_ancestors
**When:** User asks "where is this page?" or verifying page location
**Use:** Shows breadcrumb from page to root

### confluence_move_page_position
**When:** User wants page in specific position (not just "under parent")
**Positions:**
- `after`: Most common - "add after the existing page"
- `before`: Less common - "insert before"
- `append`: Make it a child of target

## Anti-Patterns to Avoid

❌ **Fetching full tree every time**
- Only fetch tree when user explicitly wants to "see the structure"
- Otherwise, use search or get_page_children

❌ **Asking for information we can infer**
- Don't ask "which space?" for Eruditis work
- Don't ask for page_id if user gives you a URL
- Don't ask for parent_id if you can search for it

❌ **Reporting errors without suggestions**
- Never say "Page not found" without searching for alternatives
- Never say "Invalid space" without listing valid spaces

❌ **Over-fetching data**
- Don't get 500 pages to find 1 page
- Use search instead of tree when looking for specific content

## Example Session

**User:** "Add a page about installing Cursor to the MacOS docs"

**Bad approach:**
```
1. Ask: "Which space?"
2. Fetch 500 pages
3. Ask: "Which parent page?"
4. Create page
5. Page ends up at bottom of list
```

**Good approach (using this skill):**
```
1. Infer: Eruditis space (our default)
2. Get tree (limit=50) to find "on MacOS" section
3. Filter tree: pages with 'macos' in title
4. Find: "on MacOS..." (ID: 2176385025)
5. Create page with parent_id=2176385025
6. Find similar page: "MacOS: Claude Code"
7. Position after it: move_page_position(new_page, "after", claude_code_id)
8. Confirm placement with get_page_ancestors
```

**Result:** Page appears exactly where user expects, no questions asked.

## Summary

**MCP provides:** Raw data access
**This skill provides:** Eruditis workflow intelligence

Use progressive disclosure, intelligent defaults, and automatic recovery to make the experience feel natural instead of mechanical.
