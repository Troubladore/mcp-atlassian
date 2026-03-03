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

**Phase 1 (Triage):** Reproduce, classify, record. Comment on upstream only for
RESOLVED issues. For CONFIRMED bugs, file an issue in our repo with difficulty
rating and root cause. Do NOT offer PRs or ask the maintainer if they want help.

**Phase 2 (Fix):** Sweep back through CONFIRMED items grouped by difficulty.
Build PRs in batches of 5-10 and submit them together. This avoids PR-bombing
the maintainer and lets us do quality work.

## Per-Issue Workflow

For each issue:

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
Write a test in `tests/upstream_triage/test_issue_NNN.py`:

```python
"""Reproduction test for upstream issue #NNN: <title>."""

from __future__ import annotations

import pytest
from mcp_atlassian.confluence import ConfluenceFetcher
from .conftest import TriageInstanceInfo, TriageResourceTracker

pytestmark = pytest.mark.upstream_triage


class TestIssueNNN:
    """Upstream #NNN: <title>."""

    def test_reported_behavior(
        self,
        triage_confluence: ConfluenceFetcher,
        triage_instance: TriageInstanceInfo,
        triage_tracker: TriageResourceTracker,
        unique_id: str,
    ) -> None:
        """<Description of what the issue reports>."""
        # Setup: create test data
        # Action: perform the operation that reportedly fails
        # Assert: check for the reported bug behavior
```

### 4. RUN
```bash
set -a && source .env && set +a && uv run pytest tests/upstream_triage/test_issue_NNN.py --upstream-triage -xvs
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
| Hard | Architectural change, >100 lines | New preprocessing pipeline, round-trip fidelity |

### 7. RECORD
Update `docs/upstream-triage-log.md` with status, date, difficulty, and notes.

### 8. ACT

**RESOLVED:** Comment on the upstream issue with reproduction evidence and
suggest closure. This is the ONLY status that gets an upstream comment during
triage phase.

```bash
gh issue comment <NUMBER> --repo sooperset/mcp-atlassian --body "$(cat <<'EOF'
I attempted to reproduce this issue on Confluence Cloud using the latest code
(commit `<SHA>`).

**Test:** Created a reproduction test targeting the reported behavior.
**Result:** The issue no longer reproduces — the expected behavior works correctly.

<details>
<summary>Test output</summary>

\`\`\`
<paste test output>
\`\`\`

</details>

This may have been resolved by a subsequent commit. If the reporter can confirm
the fix, this issue could be closed.
EOF
)"
```

**CONFIRMED:** File an issue in our repo. Do NOT comment on upstream yet — that
happens in Phase 2 when we submit the actual PR.

```bash
gh issue create \
  --repo Troubladore/mcp-atlassian \
  --label "upstream-triage" \
  --label "<difficulty>" \
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

## Reproduction Test
`tests/upstream_triage/test_issue_NNN.py`
EOF
)"
```

**CANNOT_REPRODUCE / COMPLEX_DEFER / OUT_OF_SCOPE:** Log only, no upstream
comment, no issue filed.

### 9. PROMOTE (always do this)

Every triage test that confirms or resolves a real behavior should become a
permanent test. Do not leave useful coverage only in `tests/upstream_triage/`.

**RESOLVED tests:** Convert to a unit test with mocked responses so it runs
in CI without live credentials. Add to `tests/unit/confluence/` alongside
existing tests for the same module.

**CONFIRMED tests (after Phase 2 fix):** The test that proved the bug exists
becomes the regression guard. Convert to unit test if mockable, otherwise move
to `tests/e2e/cloud/` with `cloud_e2e` marker.

Ask: "Would this test catch a regression if someone broke this behavior?"
If yes → promote. If it's testing a one-off reporter scenario → discard.

## Environment Setup

Tests use the same credentials as the MCP server, loaded from `.env`:
- `CONFLUENCE_URL` — your Confluence Cloud URL (with /wiki)
- `CONFLUENCE_USERNAME` — your Atlassian email
- `CONFLUENCE_API_TOKEN` — your API token
- `TRIAGE_SPACE_KEY` — defaults to `MCPTEST`

Run tests with:
```bash
set -a && source .env && set +a && uv run pytest tests/upstream_triage/ --upstream-triage -xvs
```

## Comment Etiquette

- Only comment on RESOLVED issues during triage phase
- For CONFIRMED issues, comment when submitting the PR (Phase 2)
- Polite, factual, includes test evidence
- Always mention commit SHA tested against
- Never mark review conversations as resolved
- "Read the room" — if the issue thread is contentious, tread carefully
- Never say "I can fix this if you want" — just do the work and submit it
