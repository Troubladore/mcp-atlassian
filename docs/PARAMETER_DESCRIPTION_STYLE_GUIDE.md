# Parameter Description Style Guide for MCP Tools

## The Rule: Maximum 10 Words Per Parameter Description

LLMs consume tokens for every character in your tool definitions. Verbose descriptions waste context that could be used for actual work.

## Good vs Bad Examples

### ❌ BAD (Teaching/Verbose)
```python
page_id: Annotated[str, Field(
    description=(
        "Confluence page ID (numeric ID, can be found in the page URL). "
        "For example, in the URL 'https://example.atlassian.net/wiki/spaces/TEAM/pages/123456789/Page+Title', "
        "the page ID is '123456789'. "
        "Provide this OR both 'title' and 'space_key'. If page_id is provided, title and space_key will be ignored."
    )
)]
```
**Token cost:** ~50 tokens

### ✅ GOOD (Concise)
```python
page_id: Annotated[str, Field(
    description="Page ID or URL"
)]
```
**Token cost:** ~3 tokens

**Savings:** 94% reduction

## Rules for Writing Descriptions

### 1. State What, Not How
- ❌ "Comma-separated list of space keys to filter results by. Overrides the environment variable if provided."
- ✅ "Space keys to filter (comma-separated)"

### 2. No Examples in Descriptions
- ❌ "Space key (e.g., 'TEAM', 'DEV', 'DOCS')"
- ✅ "Space key"
- **Why:** Examples belong in documentation, not tool definitions

### 3. No Implementation Details
- ❌ "If page_id is provided, title and space_key will be ignored"
- ✅ "Page ID" (just describe the parameter, not the logic)

### 4. No Teaching Content
- ❌ "can be found in the page URL"
- ✅ "Page identifier"

### 5. Omit Obvious Information
- ❌ "The ID of the page to retrieve"
- ✅ "Page ID" (the word "page_id" already says it's an ID)

### 6. Use Abbreviations When Clear
- ❌ "Maximum number of results to return"
- ✅ "Max results"

### 7. Trust Type Hints
- ❌ "Boolean value indicating whether to include content"
- ✅ "Include content" (bool type is already visible)

### 8. One Sentence Maximum
- ❌ "Search query string. Can be simple text or CQL. Simple queries use siteSearch by default."
- ✅ "Search query (text or CQL)"

## Template

```python
parameter_name: Annotated[
    type,
    Field(
        description="<What it is in ≤10 words>",
        default=value  # Let defaults speak for themselves
    )
]
```

## Special Cases

### Optional Parameters
- ❌ "(Optional) Space key for filtering results"
- ✅ "Space key (optional)" OR just "Space key" (default=None says it's optional)

### Enum/Choice Parameters
- ❌ "Position relative to target: 'before', 'after', or 'append'"
- ✅ "Position: before/after/append"

### Complex Types
- If the parameter is complex enough to need examples, the tool is probably too rigid
- Consider making it accept flexible input and parse internally

## Measuring Success

**Before applying guide:**
```bash
grep -r "description=" src/mcp_atlassian/servers/ | wc -c
# Result: ~50,000 characters = ~12,500 tokens
```

**After applying guide:**
```bash
# Target: <5,000 characters = ~1,250 tokens
# Reduction: 75%
```

## How to Apply This Guide

### For New Tools
1. Write the parameter name
2. Write the type
3. Write a 5-word description
4. Stop

### For Existing Tools
1. Find all Field(description=...) in servers/*.py
2. Reduce each to ≤10 words
3. Remove examples, implementation details, teaching content
4. Test that tool still works

### Validation Script

```bash
# Check if any descriptions are too long
grep -rn "Field(description" src/mcp_atlassian/servers/ | \
while read line; do
    # Extract description content
    desc=$(echo "$line" | sed -n 's/.*description="\([^"]*\)".*/\1/p')
    word_count=$(echo "$desc" | wc -w)
    if [ "$word_count" -gt 10 ]; then
        echo "❌ $line"
        echo "   Words: $word_count (max 10)"
    fi
done
```

## Remember

**The LLM doesn't need to be taught how Confluence works.**
**The LLM just needs to know what data to provide.**

If you find yourself writing more than 10 words, you're probably:
1. Teaching instead of documenting
2. Explaining implementation instead of interface
3. Providing examples that belong in docs
4. Being redundant with information already in the parameter name/type
