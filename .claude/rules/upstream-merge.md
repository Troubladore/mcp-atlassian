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

## Branch hierarchy

```
main                 ← clean mirror of upstream
  └── community/main ← upstream + vetted community PRs
      └── team/main  ← community + team-specific features
```

## Sync process

`community/main` uses **merge** (others depend on it — never rebase or force-push).
`team/main` uses **rebase** (only we use it).

```bash
# 1. Sync main with upstream
git checkout main && git pull upstream main && git push origin main

# 2. Merge upstream into community (never rebase — others base work on this)
git checkout community/main && git merge main
# Resolve conflicts, then:
uv run ruff format . && uv run ruff check --fix .
uv run pytest tests/ -x
git push origin community/main

# 3. Rebase team onto latest community (only we use this branch)
git checkout team/main && git rebase community/main
# Resolve conflicts, then:
uv run ruff format . && uv run ruff check --fix .
uv run pytest tests/ -x
git push --force-with-lease origin team/main
```

## Adding community PRs to community/main

Squash-merge each vetted PR as a single commit with provenance:

```bash
git checkout -b integrate/pr-NNNN community/main
# Cherry-pick or apply the PR
git commit -m "feat(scope): description (#NNNN)

Cherry-picked from sooperset/mcp-atlassian#NNNN
Original-Author: name <email>"
# PR to community/main
```

## Fork-specific features (team/main only)

- Error recovery / fuzzy matching (utils/suggestions.py, servers/confluence.py, servers/main.py)
- Page hierarchy tools (get_page_ancestors, list_spaces, move_page_position)
- Delete safety filter (ALLOW_DELETE_TOOLS, "delete" tag filtering)
- MCPB extension (docs/mcpb-extension/)
- Security docs (security/)
- Fork CI config, Claude rules, plans docs

**Note:** As upstream merges community PRs, they move from `community/main` to `main` and the duplicate community commits merge as no-ops or can be reverted.

## Where conflicts typically occur

- `src/mcp_atlassian/servers/confluence.py` — tool definitions, descriptions, tags
- `src/mcp_atlassian/confluence/pages.py` — page methods
- `tests/unit/confluence/test_pages.py` — test additions from both sides
- `tests/unit/utils/test_toolsets.py` — tool count assertions
