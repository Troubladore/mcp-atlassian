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

## Merge process

1. `git fetch upstream && git merge upstream/main` into `eruditis/main`
2. Resolve conflicts — favor upstream's structure, preserve fork features
3. Run `uv run ruff format .` and `uv run ruff check --fix .` after resolution
4. Run `uv run pytest tests/ -x` to verify
5. Create feature branch and PR to `eruditis/main`

## Fork-specific features to preserve during merges

- Page hierarchy navigation (get_page_ancestors, get_space_page_tree, list_spaces, move_page_position)
- Page width support (page_width parameter on create/update)
- URL auto-parsing (parse_page_id_from_url helper)
- MCPB extension (docs/mcpb-extension/)
- Security docs (security/)

## Where conflicts typically occur

- `src/mcp_atlassian/servers/confluence.py` — tool definitions, descriptions, tags
- `src/mcp_atlassian/confluence/pages.py` — page methods
- `src/mcp_atlassian/utils/urls.py` — URL validation
- `docs/tools-reference.mdx` — tool documentation
- `tests/unit/confluence/test_pages.py` — test additions from both sides
