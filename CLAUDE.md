@AGENTS.md

# Claude Code Project Notes

## Repository Structure

This is a fork of `sooperset/mcp-atlassian`. Remotes:
- `origin` = `Troubladore/mcp-atlassian` (our fork)
- `upstream` = `sooperset/mcp-atlassian` (upstream)

## Branch Strategy

```
main                 ← clean mirror of upstream (never commit here)
  └── community/main ← upstream + vetted community PRs (rebased onto main)
      └── team/main  ← community + team-specific features (rebased onto community/main)
```

| Branch | Purpose | Rebases onto |
|--------|---------|-------------|
| `main` | Clean upstream mirror | `upstream/main` |
| `community/main` | Upstream + community PRs awaiting merge | `main` |
| `team/main` | Team-specific features and customizations | `community/main` |

**NEVER commit directly to `team/main`, `community/main`, or `main`.**

## Branch Rules

| Work type | Branch from | PR target |
|-----------|-------------|-----------|
| Team features / experiments | `team/main` | `team/main` |
| Community PR integration | `community/main` | `community/main` |
| Upstream contributions (fixes, tests) | `main` | `sooperset/mcp-atlassian` main |

Upstream PR branches must be cut from `main` (the clean upstream mirror), not
from `community/main` or `team/main`.

## Developer Setup

```bash
uv run pre-commit install   # Required: install git hooks for formatting/lint
```

## Key Commands

```bash
uv run pytest tests/ -x              # Run tests (stop on first failure)
uv run ruff format .                  # Format code
uv run ruff check --fix .            # Lint and auto-fix
```

## Creating Pull Requests

### To our fork (team/main)

```bash
gh pr create \
  --repo Troubladore/mcp-atlassian \
  --base team/main \
  --head <your-branch-name> \
  --title "feat: description" \
  --body "$(cat <<'EOF'
## Summary
- bullet points

## Test plan
- [x] tests pass

EOF
)"
```

- Always specify `--repo Troubladore/mcp-atlassian` explicitly
- Base branch is `team/main` (not `main`)
- Push your branch to `origin` before creating the PR

### To upstream (sooperset/mcp-atlassian)

Requires classic PAT (`ghp_`). Check with `gh auth status` — switch if needed.

```bash
gh pr create \
  --repo sooperset/mcp-atlassian \
  --base main \
  --head Troubladore:<your-branch-name> \
  --title "..." \
  --body "..."
```

## Creating GitHub Issues

```bash
gh issue create \
  --repo Troubladore/mcp-atlassian \
  --label enhancement \
  --title "Issue title" \
  --body "Issue body here"
```

## Upstream Alignment

`community/main` uses **merge** (safe for others to base work on).
`team/main` uses **rebase** (only we use it).

```bash
# Sync main with upstream
git checkout main && git pull upstream main && git push origin main

# Merge upstream into community (never rebase — others depend on this branch)
git checkout community/main && git merge main && git push origin community/main

# Rebase team onto latest community
git checkout team/main && git rebase community/main
git push --force-with-lease origin team/main
```

**Auth context for upstream PRs:** The fine-grained PAT (`github_pat_`) cannot
create cross-repo PRs. Use the classic PAT (`ghp_`):
```bash
gh auth login    # Select github.com, paste the classic token (ghp_...)
```

## Upstream Issue Triage

Active triage of `sooperset/mcp-atlassian` issues. See:
- `docs/upstream-triage-log.md` — status of all examined issues
- `.claude/skills/upstream-triage/skill.md` — per-session workflow

## Docker

Images are pushed to GHCR under `ghcr.io/troubladore/mcp-atlassian`.

## MCPB Extension

The MCPB extension file lives at `docs/mcpb-extension/team-mcp-atlassian.mcpb`.
Upload this file to Claude Desktop to install/update the extension.
