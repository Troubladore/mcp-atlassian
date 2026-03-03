@AGENTS.md

# Claude Code Project Notes

## Repository Structure

This is a fork of `sooperset/mcp-atlassian`. Remotes:
- `origin` = `Troubladore/mcp-atlassian` (our fork)
- `upstream` = `sooperset/mcp-atlassian` (upstream)

Our development branch is `eruditis/main`. The `main` branch is a clean mirror
of upstream.

## Branch Rules

| Work type | Branch from | PR target |
|-----------|-------------|-----------|
| Fork features / experiments | `eruditis/main` | `eruditis/main` |
| Upstream contributions (fixes, tests) | `main` | `sooperset/mcp-atlassian` main |

**NEVER commit directly to `eruditis/main` or `main`.**

Upstream PR branches must be cut from `main` (the clean upstream mirror), not
from `eruditis/main`. This keeps the diff clean — no fork-specific commits bleed
into upstream PRs.

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

### To our fork (eruditis/main)

```bash
gh pr create \
  --repo Troubladore/mcp-atlassian \
  --base eruditis/main \
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
- Base branch is `eruditis/main` (not `main`)
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

Our fork is rebased on upstream `main`, keeping fork-specific commits as a clean
stack on top. See `docs/UPSTREAM_CONTRIBUTIONS.md` for the full workflow.

```bash
# Sync main with upstream
git checkout main && git pull upstream main && git push origin main

# Rebase fork onto latest upstream
git checkout eruditis/main && git rebase main
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

The MCPB extension file lives at `docs/mcpb-extension/eruditis-atlassian.mcpb`.
Upload this file to Claude Desktop to install/update the extension.
