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
uv run pytest tests/upstream_triage/test_issue_NNN.py --upstream-triage -xvs
```

### 5. CLASSIFY
- Test passes (bug NOT present) → RESOLVED
- Test fails (bug IS present) → CONFIRMED
- Can't write a meaningful test → CANNOT_REPRODUCE
- Too complex → COMPLEX_DEFER

### 6. RECORD
Update `docs/upstream-triage-log.md` with status, date, and notes.

### 7. ACT

**RESOLVED:**
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

**CONFIRMED:**
```bash
gh issue comment <NUMBER> --repo sooperset/mcp-atlassian --body "$(cat <<'EOF'
I confirmed this issue reproduces on Confluence Cloud using the latest code
(commit `<SHA>`).

**Test:** Created a reproduction test targeting the reported behavior.
**Result:** The bug is still present.

<details>
<summary>Test output</summary>

\`\`\`
<paste test output>
\`\`\`

</details>

I can put together a PR to fix this if you'd like. [Brief description of
the fix approach.]
EOF
)"
```

**CANNOT_REPRODUCE:**
Comment asking the reporter for more details (version, exact steps, config).

### 8. PROMOTE
If the test is valuable as a regression guard, move it to:
- `tests/unit/confluence/` (if it can work with mocks)
- `tests/e2e/cloud/` (if it needs real API)

Update the test's marker from `upstream_triage` to `cloud_e2e` or remove it.

## Environment Setup

Tests use the same credentials as the MCP server:
- `CONFLUENCE_URL` — your Confluence Cloud URL (with /wiki)
- `CONFLUENCE_USERNAME` — your Atlassian email
- `CONFLUENCE_API_TOKEN` — your API token
- `TRIAGE_SPACE_KEY` — defaults to `MCPTEST`

## Comment Etiquette

- Polite, factual, includes test evidence
- No promises — offer to PR, let maintainer decide
- Always mention commit SHA tested against
- Never mark review conversations as resolved
- "Read the room" — if the issue thread is contentious, tread carefully
