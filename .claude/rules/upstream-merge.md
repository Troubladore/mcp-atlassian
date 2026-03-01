---
paths:
  - "uv.lock"
  - ".github/workflows/**"
  - "pyproject.toml"
---

# Upstream Merge Workflow

This is a fork of `sooperset/mcp-atlassian`. Remotes:
- `origin` = `Troubladore/mcp-atlassian` (our fork)
- `upstream` = `sooperset/mcp-atlassian` (upstream)

## Sync process (rebase, not merge)

We rebase `eruditis/main` onto `main` to keep a clean stack of fork-specific commits.

```bash
git checkout main && git pull upstream main && git push origin main
git checkout eruditis/main && git rebase main
# Resolve conflicts, then:
uv run ruff format . && uv run ruff check --fix .
uv run pytest tests/ -x
git push --force-with-lease origin eruditis/main
```

## Fork-specific features to preserve during rebases

- Error recovery / fuzzy matching (utils/suggestions.py, servers/confluence.py, servers/main.py)
- Page hierarchy (get_space_page_tree in pages.py and servers/confluence.py)
- Page width support (page_width on ConfluencePage model, create/update)
- Delete safety filter (ALLOW_DELETE_TOOLS, "delete" tag filtering)
- URL security fix (endswith() in urls.py)
- MCPB extension (docs/mcpb-extension/)
- Security docs (security/)
- Fork CI config, Claude rules, plans docs

**Note:** Some of these have been proposed upstream (see docs/UPSTREAM_CONTRIBUTIONS.md). As upstream merges them, they leave our fork diff and no longer need preserving.

## Where conflicts typically occur

- `src/mcp_atlassian/servers/confluence.py` — tool definitions, descriptions, tags
- `src/mcp_atlassian/confluence/pages.py` — page methods
- `src/mcp_atlassian/utils/urls.py` — URL validation
- `docs/tools-reference.mdx` — tool documentation
- `tests/unit/confluence/test_pages.py` — test additions from both sides
