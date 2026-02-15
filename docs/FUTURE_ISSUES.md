# Future GitHub Issues

Copy these into GitHub manually (gh GraphQL API doesn't work with personal tokens).

---

## Issue 1: Split into separate Confluence/Jira MCPB extensions

**Title:** Token efficiency: Split into separate Confluence/Jira MCPB extensions

**Labels:** enhancement

**Body:**

### Problem

Current `eruditis-atlassian.mcpb` bundles both Confluence and Jira tools (~37k tokens at startup). Users working only with Confluence load unnecessary Jira tools, wasting tokens.

### Proposed Solution

Create three separate MCPB extensions:
- `eruditis-confluence.mcpb` - Confluence-only (~15k tokens)
- `eruditis-jira.mcpb` - Jira-only (~15k tokens)
- `eruditis-atlassian.mcpb` - Both (current, for users needing both)

### Benefits

- **50% token reduction** for single-product users
- Faster startup (fewer tools to register)
- Better security (only expose what's needed)
- Clearer mental model

### Implementation

Upstream already has separate FastMCP instances (`confluence_mcp`, `jira_mcp`). Just need to:

1. Create separate MCPB manifests in `docs/mcpb-confluence/` and `docs/mcpb-jira/`
2. Each with different ENABLED_TOOLS filters (Confluence-only or Jira-only)
3. Same Docker image, different tool filtering
4. No code changes to mcp-atlassian itself

### Related

Based on token efficiency audit in TOKEN_EFFICIENCY_AUDIT.md

---

## Issue 2: Add fuzzy space key matching with suggestions

**Title:** MCP improvement: Add fuzzy space_key matching and auto-suggestions

**Labels:** enhancement

**Body:**

### Problem

When user provides incorrect space_key (typo, wrong case, etc.), tools fail with generic errors instead of helping.

Current behavior:
```
Error: Space 'eruditis' not found
```

### Proposed Solution

Add fuzzy matching and auto-suggestion when space_key invalid:

```
Error: Space 'eruditis' not found. Did you mean:
  - ERUDITIS (Eruditis)
  - ERUDITISARCHIVE (Eruditis Archive)
```

### Implementation

1. Add helper function to confluence server:
```python
def suggest_spaces(space_key_input, all_spaces):
    """Fuzzy match and suggest similar space keys."""
    # Case-insensitive match
    # Edit distance < 3
    # Substring match
    return top_3_matches
```

2. Update all tools that accept space_key to call this on error
3. Return suggestions in error message instead of just failing

### Benefits

- "Build for the NOC kid" principle - help users fix their mistakes
- Reduces retry loops (user sees suggestion, corrects immediately)
- Better UX (auto-recovery instead of fail-fast)

### Related

Part of MCP token efficiency improvements (TOKEN_EFFICIENCY_AUDIT.md)

---

## Issue 3: Return partial results instead of hard errors

**Title:** MCP improvement: Graceful degradation with partial results

**Labels:** enhancement

**Body:**

### Problem

Tools currently fail hard when something goes wrong instead of returning what they can.

Examples:
- `get_space_page_tree` with 600 pages and limit=500 → could return first 500 + warning
- Page not found → could search for similar titles and suggest
- Invalid parameter → could guess what user meant and ask for confirmation

### Proposed Solution

Apply "automatic recovery" principle from MCP best practices:

**Instead of:**
```json
{"error": "Page not found"}
```

**Return:**
```json
{
  "error": "Page 'MacOS Guide' not found",
  "suggestions": [
    {"id": "2565144621", "title": "MacOS: Claude Code"},
    {"id": "2465792001", "title": "MacOS: Claude Desktop"}
  ]
}
```

### Implementation Areas

1. `get_space_page_tree` - Return partial results + `has_more: true` if limit exceeded
2. `get_page` - If page not found, search for similar titles
3. `create_page` - If parent_id invalid, suggest similar page titles
4. All tools - Better error messages explaining how to fix

### Benefits

- Fewer retry loops
- Better UX (LLM can auto-recover)
- Follows "give partial answer if possible" principle

### Related

Based on https://blog.fsck.com/2025/10/19/mcps-are-not-like-other-apis/

---

## Issue 4: Reduce Jira tool parameter descriptions

**Title:** Token efficiency: Reduce Jira parameter descriptions by 80%

**Labels:** enhancement

**Body:**

### Problem

Jira tools still have verbose parameter descriptions (not yet optimized like Confluence tools in PR #XX).

### Solution

Apply same parameter description reductions done for Confluence tools:
- Before: "The ID of the issue to link (e.g., 'PROJ-123')"
- After: "Issue key"

Target: <10 words per parameter description

### Implementation

Follow PARAMETER_DESCRIPTION_STYLE_GUIDE.md and apply to all Jira tools in `src/mcp_atlassian/servers/jira.py`

### Expected Savings

~60% reduction in Jira tool definition overhead (similar to Confluence improvements)
