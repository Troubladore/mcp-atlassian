@AGENTS.md

# Claude Code Project Notes

## Repository Structure

This is a fork of `sooperset/mcp-atlassian`. Remotes:
- `origin` = `Troubladore/mcp-atlassian` (our fork)
- `upstream` = `sooperset/mcp-atlassian` (upstream)

Our development branch is `eruditis/main`. The `main` branch is a clean mirror of upstream.

**NEVER commit directly to `eruditis/main` or `main`.** Always create a feature branch and merge via PR — no exceptions, even for "quick" changes like version bumps or doc fixes.

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

**Use `gh pr create` with REST API (the default).** Do NOT use GraphQL API calls — they fail with personal tokens on this repo.

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

## Creating GitHub Issues

```bash
gh issue create \
  --repo Troubladore/mcp-atlassian \
  --label enhancement \
  --title "Issue title" \
  --body "Issue body here"
```

## Upstream Alignment

Our fork is rebased on upstream `main`, keeping fork-specific commits as a clean stack on top. See `docs/UPSTREAM_CONTRIBUTIONS.md` for the full workflow.

**Quick reference:**
```bash
# Sync main with upstream
git checkout main && git pull upstream main && git push origin main

# Rebase fork onto latest upstream
git checkout eruditis/main && git rebase main

# Check status of our upstream PRs
for pr in 1087 1088 1090 1091 1092; do
  echo -n "PR #$pr: "; gh pr view $pr --repo sooperset/mcp-atlassian --json state -q '.state'
done
```

**Auth context for upstream PRs:** The fine-grained PAT (`github_pat_`) cannot create cross-repo PRs. Switch to the classic PAT first:
```bash
gh auth login    # Select github.com, paste the classic token (ghp_...)
```

## Docker

Images are pushed to GHCR under `ghcr.io/troubladore/mcp-atlassian`.

## MCPB Extension

The MCPB extension file lives at `docs/mcpb-extension/eruditis-atlassian.mcpb`. Upload this file to Claude Desktop to install/update the extension.
