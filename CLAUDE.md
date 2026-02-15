# Claude Code Project Notes

## Repository Structure

This is a fork of `sooperset/mcp-atlassian`. Remotes:
- `origin` = `Troubladore/mcp-atlassian` (our fork)
- `upstream` = `sooperset/mcp-atlassian` (upstream)

Our development branch is `eruditis/main`.

## Creating Pull Requests

**Use `gh pr create` with REST API (the default).** Do NOT use GraphQL API calls — they fail with personal tokens on this repo.

### Standard PR command

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

### Key points
- Always specify `--repo Troubladore/mcp-atlassian` explicitly
- Base branch is `eruditis/main` (not `main`)
- Push your branch to `origin` before creating the PR
- Use heredoc for the body to handle multiline markdown

## Creating GitHub Issues

```bash
gh issue create \
  --repo Troubladore/mcp-atlassian \
  --label enhancement \
  --title "Issue title" \
  --body "$(cat <<'EOF'
Issue body here
EOF
)"
```

## Running Tests

```bash
uv run pytest tests/ -x
```

## Docker

Images are pushed to GHCR under `ghcr.io/troubladore/mcp-atlassian`.

## MCPB Extension

The MCPB extension file lives at `docs/mcpb-extension/eruditis-atlassian.mcpb`. Upload this file to Claude Desktop to install/update the extension.
