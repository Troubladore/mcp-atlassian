# Contributing to Upstream

This fork (`Troubladore/mcp-atlassian`) maintains alignment with `sooperset/mcp-atlassian` and contributes features back when they're generally useful.

## Architecture: Three-Tier Rebase Chain

```
main                 ← clean mirror of upstream
  └── community/main ← upstream + vetted community PRs (default branch)
      └── team/main  ← community + team-specific features
```

`community/main` uses **merge** (not rebase) so others can safely base work on it.
`team/main` uses **rebase** onto `community/main` for a clean linear diff.

```bash
# Sync chain
git checkout main && git pull upstream main && git push origin main
git checkout community/main && git merge main        # merge — safe for others
git checkout team/main && git rebase community/main  # rebase — only we use this
```

`community/main` serves as an actively maintained alternative while upstream
is slow to merge PRs. Community PRs are squash-merged with provenance trailers.
When upstream eventually merges a PR, the duplicate community commit can be
reverted or will merge cleanly as a no-op.

## How to Propose Features Upstream

### 1. Create a focused branch from `main`

Each upstream PR should contain exactly one feature, branched from `main` (the upstream mirror), not from `team/main`.

```bash
git checkout main
git checkout -b feature/my-feature   # or fix/my-fix
```

### 2. Implement the feature cleanly

- No fork-specific code (no MCPB, no fork CI, no Claude rules)
- Follow upstream conventions: Google docstrings, ruff 88-char, mypy
- Run `uv run pytest tests/ -x` and `uv run pre-commit run --all-files`
- **Security fixes:** Do NOT submit as public PRs or issues. Use GitHub's private vulnerability reporting at https://github.com/sooperset/mcp-atlassian/security — see below

### 3. Switch to the classic PAT for cross-repo operations

The fine-grained PAT (`github_pat_...`) is scoped to our fork only. To create PRs or issues on `sooperset/mcp-atlassian`, switch to the classic token:

```bash
# Switch auth context
gh auth login
# Select: GitHub.com → Paste token → paste the classic token (ghp_...)

# Verify
gh auth status   # Should show ghp_... token
```

The classic PAT needs only the `public_repo` scope. Generate one at:
https://github.com/settings/tokens/new (select "Generate new token (classic)")

### 4. Create an issue first (for features)

Bug fixes can go straight to a PR. Features should have an issue first:

```bash
gh issue create \
  --repo sooperset/mcp-atlassian \
  --title "[Feature]: Description of the feature" \
  --body "..."
```

### 5. Push and create the PR

```bash
git push -u origin feature/my-feature

gh api repos/sooperset/mcp-atlassian/pulls \
  --method POST \
  -f title="feat(scope): description" \
  -f head="Troubladore:feature/my-feature" \
  -f base="main" \
  -f body="PR body here..."
```

### 6. Switch back to fine-grained PAT for fork work

```bash
gh auth login
# Paste the fine-grained token (github_pat_...)
```

## Active Upstream PRs

Tracked in [Issue #28](https://github.com/Troubladore/mcp-atlassian/issues/28).

| Upstream PR | Feature | Branch |
|-------------|---------|--------|
| [#1087](https://github.com/sooperset/mcp-atlassian/pull/1087) | Security: `endswith()` URL validation | `fix/url-validation-bypass` |
| [#1088](https://github.com/sooperset/mcp-atlassian/pull/1088) | `ALLOW_DELETE_TOOLS` safety filter | `feature/delete-tools-safety-filter` |
| [#1090](https://github.com/sooperset/mcp-atlassian/pull/1090) | `get_space_page_tree` hierarchy tool | `feature/space-page-tree` |
| [#1091](https://github.com/sooperset/mcp-atlassian/pull/1091) | Page width layout support | `feature/page-width-support` |
| [#1092](https://github.com/sooperset/mcp-atlassian/pull/1092) | Error recovery / fuzzy matching | `feature/intelligent-error-recovery` |

## When Upstream Merges a PR

1. Sync `main`: `git checkout main && git pull upstream main && git push origin main`
2. Merge into community: `git checkout community/main && git merge main` — if the upstream now includes the PR, the community commit is redundant and can be reverted or will merge cleanly
3. Rebase team: `git checkout team/main && git rebase community/main`
4. Delete the feature branch: `git branch -D feature/xxx && git push origin --delete feature/xxx`
5. Update issue #28 status
6. Push: `git push origin community/main && git push --force-with-lease origin team/main`

## Security Vulnerabilities

**NEVER report security issues as public PRs or issues on upstream.**

Upstream has a security policy at https://github.com/sooperset/mcp-atlassian/security that requires private disclosure. Their commitments:
- Acknowledge within 72 hours
- Initial assessment within 7 days
- Patch within 30 days

**Process for security fixes:**
1. Report via GitHub's "Report a vulnerability" button at the security link above
2. Wait for maintainer acknowledgment
3. Coordinate on timing for the fix and public disclosure
4. Only then submit a PR (or the maintainer may fix it themselves)

**Lesson learned:** PR #1087 (URL validation bypass) was submitted as a public PR, which disclosed the vulnerability before the maintainer could assess it. Follow the private reporting process going forward.

## Monitoring

```bash
# Check all upstream PR statuses
for pr in 1087 1088 1090 1091 1092; do
  echo -n "sooperset#$pr: "
  gh pr view $pr --repo sooperset/mcp-atlassian --json state,title -q '"\(.state) - \(.title)"'
done
```
