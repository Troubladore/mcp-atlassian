# Branching Strategy for mcp-atlassian Fork

## Overview

This repository is a fork of `sooperset/mcp-atlassian` with three purposes:
1. **Mirror upstream** via `main`
2. **Maintain an actively updated community fork** via `community/main` (default branch)
3. **Team-specific customizations** via `team/main`

## Branch Hierarchy

```
upstream (sooperset/mcp-atlassian)
    └── main (clean mirror — never commit here)

origin (Troubladore/mcp-atlassian)
    ├── main                (mirrors upstream exactly)
    ├── community/main      (upstream + vetted community PRs — DEFAULT BRANCH)
    └── team/main           (community + team-specific features)
```

Changes flow down, never up. `community/main` uses **merge** from `main`
(safe for others to base work on — never force-push). `team/main` uses
**rebase** onto `community/main` (only the team uses it).

## Branch Purposes

### `main`

**Purpose**: Clean mirror of `upstream/main`
**Sync**: `git checkout main && git pull upstream main && git push origin main`

Never commit to this branch. It exists so we have a pushable copy of upstream
and a clean base for upstream contribution branches.

### `community/main` (default branch)

**Purpose**: Actively maintained fork incorporating community PRs that upstream
hasn't merged yet. This is the branch the community uses.

**Based on**: `main` (rebased)

Community PRs are squash-merged with provenance:
```bash
git checkout -b integrate/pr-NNNN community/main
# Apply the PR
git commit -m "feat(scope): description (#NNNN)

Cherry-picked from sooperset/mcp-atlassian#NNNN
Original-Author: name <email>"
# PR to community/main
```

When upstream eventually merges a PR, the corresponding community commit
drops out naturally during the next rebase onto `main`.

### `team/main`

**Purpose**: Team-specific features on top of the community fork
**Based on**: `community/main` (rebased)

Contains:
- Intelligent error recovery with fuzzy matching
- Additional Confluence tools (get_page_ancestors, list_spaces, move_page_position)
- Delete safety filter (ALLOW_DELETE_TOOLS)
- MCPB desktop extension (docs/mcpb-extension/)
- Security scanning protocol and docs
- Upstream issue triage infrastructure
- Fork CI config, Claude rules, and development plans

## Workflows

### Sync with Upstream

```bash
# 1. Update main
git checkout main && git pull upstream main && git push origin main

# 2. Merge upstream into community (never rebase — others depend on this branch)
git checkout community/main && git merge main
uv run ruff format . && uv run ruff check --fix .
uv run pytest tests/ -x
git push origin community/main

# 3. Rebase team onto latest community (only we use this branch)
git checkout team/main && git rebase community/main
uv run ruff format . && uv run ruff check --fix .
uv run pytest tests/ -x
git push --force-with-lease origin team/main
```

### Adding a Community PR

```bash
git checkout -b integrate/pr-NNNN community/main
# Cherry-pick or apply the PR, test, commit with provenance
gh pr create --repo Troubladore/mcp-atlassian --base community/main
```

### Contributing to Upstream

```bash
# Always branch from main (clean upstream mirror)
git checkout -b fix/description main
# Implement, test, then PR to sooperset/mcp-atlassian
```

### Team-Specific Work

```bash
git checkout -b feature/description team/main
# Implement, test, then PR to team/main
```

## What Goes Where

| Content | Branch |
|---------|--------|
| Upstream contributions (fixes, tests) | `main` → PR to upstream |
| Community PRs awaiting upstream merge | `community/main` |
| Team features, MCPB extension, fork docs | `team/main` |

## Branch Protection

- **Never commit directly** to `main`, `community/main`, or `team/main`
- **Never merge up** — changes flow down only (main → community → team)
- **Never include fork-specific code** in upstream contributions

---

**Maintainer**: Troubladore
**Upstream**: https://github.com/sooperset/mcp-atlassian
