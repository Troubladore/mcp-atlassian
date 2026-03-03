---
name: upstream-triage
description: Use when triaging upstream sooperset/mcp-atlassian issues. Provides the workflow for reproducing, classifying, and commenting on Confluence Cloud bugs.
---

# Upstream Issue Triage

## Quick Start

1. Read the tracking log: `docs/upstream-triage-log.md`
2. Find the next PENDING issues (oldest first)
3. Pick 4-5 issues to work in parallel
4. Follow the per-issue workflow below
5. Update the tracking log and commit

## Two-Phase Strategy

**Phase 1 (Triage):** Reproduce, classify, record. For RESOLVED bugs, cut a PR
with a regression test to upstream. For CONFIRMED bugs, file an issue in our
repo with difficulty rating. Do NOT offer PRs for confirmed bugs yet.

**Phase 2 (Fix):** Sweep back through CONFIRMED items grouped by difficulty.
Build PRs in batches of 5-10 and submit together.

## Where Tests Live

Tests belong in the natural location for the code they test — not in any
special triage directory.

- **Mockable** (no live API needed) → `tests/unit/confluence/`
- **Needs live API** → `tests/e2e/cloud/` with `@pytest.mark.cloud_e2e`

## Per-Issue Workflow

### 1. READ
```bash
gh issue view <NUMBER> --repo sooperset/mcp-atlassian --json title,body,labels,comments,createdAt
```

### 2. ASSESS
- Is this a Confluence Cloud bug? If not → OUT_OF_SCOPE
- Does it have >5 comments with failed fix attempts? → COMPLEX_DEFER
- Is there an active PR? → OUT_OF_SCOPE (already being addressed)
- Can we reproduce it with our infrastructure? If not → CANNOT_REPRODUCE

### 3. REPRODUCE
Write a test where it naturally belongs:

**Unit test (mockable):**
```python
# tests/unit/confluence/test_pages.py (or appropriate module)
def test_reported_behavior(self, pages_mixin):
    """<What the issue reports. Link to upstream issue.>"""
    # Setup mocks to trigger the bug scenario
    # Assert expected behavior
```

**E2E test (needs live API):**
```python
# tests/e2e/cloud/test_confluence_cloud_operations.py
class TestConfluence<Feature>:
    """<What the issue reports. Link to upstream issue.>"""

    def test_reported_behavior(
        self,
        confluence_fetcher: ConfluenceFetcher,
        cloud_instance: CloudInstanceInfo,
        resource_tracker: CloudResourceTracker,
    ) -> None:
        uid = uuid.uuid4().hex[:8]
        # Setup, action, assert
```

### 4. RUN
```bash
# Unit tests:
uv run pytest tests/unit/confluence/test_pages.py::TestClassName::test_name -xvs

# E2E tests (needs credentials):
set -a && source .env && set +a && \
  uv run pytest tests/e2e/cloud/ --cloud-e2e -k "test_name" -xvs
```

### 5. CLASSIFY
- Test passes (bug NOT present) → RESOLVED
- Test fails (bug IS present) → CONFIRMED
- Can't write a meaningful test → CANNOT_REPRODUCE
- Too complex → COMPLEX_DEFER

### 6. RATE DIFFICULTY (CONFIRMED only)

| Rating | Meaning | Examples |
|--------|---------|----------|
| Easy | 1-2 file change, <20 lines | Add expand param, fix filter logic |
| Medium | 3-5 files, needs tests, <100 lines | New error handling, model changes |
| Hard | Architectural change, >100 lines | New preprocessing pipeline |

### 7. RECORD
Update `docs/upstream-triage-log.md` with status, date, difficulty, and notes.

### 8. ACT

**RESOLVED:** Cut a branch, open a PR to upstream, then comment on the issue.
Each RESOLVED issue gets its own PR so the maintainer can accept or reject
independently.

```bash
# 1. Cut branch from upstream/main
git checkout -b fix/upstream-NNN-short-description upstream/main

# 2. The test proving the fix is already in the right place in this repo.
#    Cherry-pick it or re-add it to the upstream branch.

# 3. Verify tests pass on that branch
uv run pytest <path/to/test> -xvs

# 4. Push and open PR to upstream
git push origin fix/upstream-NNN-short-description
gh pr create \
  --repo sooperset/mcp-atlassian \
  --base main \
  --title "test: add regression test for <issue title> (closes #NNN)" \
  --body "$(cat <<'EOF'
Adds a regression test proving that #NNN is resolved.

## What This Does
<one sentence>

## Test Evidence
<paste test output>

Closes #NNN
EOF
)"

# 5. Comment on the upstream issue
gh issue comment NNN --repo sooperset/mcp-atlassian --body "$(cat <<'EOF'
I verified this no longer reproduces on Confluence Cloud (commit `<SHA>`).

**Test:** <link to test in PR>
**Result:** Passes — the expected behavior works correctly.

PR #<PR_NUMBER> adds a regression test if you'd like the coverage.

<details>
<summary>Test output</summary>

\`\`\`
<paste output>
\`\`\`

</details>
EOF
)"
```

**CONFIRMED:** File an issue in our repo. Do NOT comment on upstream yet.

```bash
gh issue create \
  --repo Troubladore/mcp-atlassian \
  --label "upstream-triage" \
  --label "<difficulty:easy|medium|hard>" \
  --title "Upstream #NNN: <title>" \
  --body "$(cat <<'EOF'
## Upstream Issue
sooperset/mcp-atlassian#NNN

## Status
CONFIRMED — reproduces on Confluence Cloud

## Root Cause
<brief technical description>

## Fix Approach
<what needs to change and where>

## Difficulty
<Easy/Medium/Hard> — <why>

## Regression Test
<path to test file in this repo>
EOF
)"
```

**CANNOT_REPRODUCE / COMPLEX_DEFER / OUT_OF_SCOPE:** Log only. No upstream
comment, no issue filed.

## Environment Setup

Tests use credentials from `.env` in the project root (gitignored):
```
CONFLUENCE_URL=https://eruditis.atlassian.net/wiki
CONFLUENCE_USERNAME=eric@eruditis.com
CONFLUENCE_API_TOKEN=<token>
CONFLUENCE_TEST_PAGE_ID=2570944513  (page in MCPTEST space)
TRIAGE_SPACE_KEY=MCPTEST
```

Run E2E tests:
```bash
set -a && source .env && set +a && uv run pytest tests/e2e/cloud/ --cloud-e2e -xvs
```

## Comment Etiquette

- Only comment upstream when you have a PR to attach (RESOLVED) or a fix (Phase 2)
- Never say "I can fix this if you want" — just do the work
- Polite, factual, includes test output and commit SHA
- Each issue gets its own PR — never bundle multiple issues into one PR
- Never mark review conversations as resolved
