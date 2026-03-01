@AGENTS.md

# Claude Code Project Notes

## Repository Structure

This is a fork of `sooperset/mcp-atlassian`. Remotes:
- `origin` = `Troubladore/mcp-atlassian` (our fork)
- `upstream` = `sooperset/mcp-atlassian` (upstream)

Our development branch is `eruditis/main`. Feature branches merge into `eruditis/main` via PR. The `main` branch is a clean mirror of upstream.

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

## Docker

Images are pushed to GHCR under `ghcr.io/troubladore/mcp-atlassian`.

## MCPB Extension

The MCPB extension file lives at `docs/mcpb-extension/eruditis-atlassian.mcpb`. Upload this file to Claude Desktop to install/update the extension.
