# Upstream Issue Triage Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the infrastructure (Confluence test space, triage test harness, tracking log, skill, and session workflow) for systematically triaging upstream Confluence Cloud bugs.

**Architecture:** A new `tests/upstream_triage/` directory with its own conftest reusing the existing Cloud E2E fixture patterns. A tracking log in `docs/` and a Claude skill in `.claude/skills/` enable session resumption. The MCPTEST Confluence space provides a safe sandbox for destructive testing.

**Tech Stack:** Python 3.10+, pytest, existing ConfluenceFetcher/ConfluenceConfig classes, `gh` CLI for upstream issue interaction.

---

### Task 1: Register the `upstream_triage` pytest marker

**Files:**
- Modify: `pyproject.toml:62-67`
- Modify: `tests/e2e/conftest.py:55-82`

**Step 1: Add marker to pyproject.toml**

In `pyproject.toml`, add the new marker to the existing markers list:

```toml
[tool.pytest.ini_options]
markers = [
    "integration: mark test as requiring integration with real services",
    "dc_e2e: mark test as requiring DC instances (Jira DC + Confluence DC)",
    "cloud_e2e: mark test as requiring Cloud instances (Jira Cloud + Confluence Cloud)",
    "upstream_triage: mark test as upstream issue reproduction (requires --upstream-triage flag)",
]
```

**Step 2: Add CLI flag and auto-skip in tests/e2e/conftest.py**

In `tests/e2e/conftest.py`, add the `--upstream-triage` option and auto-skip logic alongside the existing `--dc-e2e` and `--cloud-e2e` handling:

In `pytest_addoption`:
```python
parser.addoption(
    "--upstream-triage",
    action="store_true",
    default=False,
    help="Run upstream issue triage tests",
)
```

In `pytest_configure`:
```python
config.addinivalue_line(
    "markers",
    "upstream_triage: mark test as upstream issue reproduction (requires --upstream-triage flag)",
)
```

In `pytest_collection_modifyitems`, add handling for `upstream_triage` marker with the same skip-unless-flag pattern used by `cloud_e2e`.

**Step 3: Run tests to verify marker is registered**

Run: `uv run pytest --markers 2>&1 | grep upstream_triage`
Expected: `@pytest.mark.upstream_triage: mark test as upstream issue reproduction`

**Step 4: Commit**

```bash
git add pyproject.toml tests/e2e/conftest.py
git commit -m "test: register upstream_triage pytest marker and CLI flag"
```

---

### Task 2: Create the triage test directory and conftest

**Files:**
- Create: `tests/upstream_triage/__init__.py`
- Create: `tests/upstream_triage/conftest.py`

**Step 1: Create the directory structure**

```bash
mkdir -p tests/upstream_triage
touch tests/upstream_triage/__init__.py
```

**Step 2: Write the conftest.py**

This conftest maps the standard MCP env vars (`CONFLUENCE_URL`, `CONFLUENCE_USERNAME`,
`CONFLUENCE_API_TOKEN`) to the fixtures needed for triage tests. It does NOT require
the `CLOUD_E2E_*` vars — it works with the same credentials the MCP server uses.

```python
"""Upstream issue triage test configuration.

Provides fixtures for reproducing upstream bug reports against a real
Confluence Cloud instance. Uses the same credentials as the MCP server
(CONFLUENCE_URL, CONFLUENCE_USERNAME, CONFLUENCE_API_TOKEN).

Run with: uv run pytest tests/upstream_triage/ --upstream-triage -xvs
"""

from __future__ import annotations

import logging
import os
import uuid
from collections.abc import Generator
from dataclasses import dataclass

import pytest

from mcp_atlassian.confluence import ConfluenceFetcher
from mcp_atlassian.confluence.config import ConfluenceConfig

logger = logging.getLogger(__name__)

TRIAGE_SPACE_KEY = os.environ.get("TRIAGE_SPACE_KEY", "MCPTEST")


@dataclass
class TriageInstanceInfo:
    """Connection info for triage tests, loaded from MCP server env vars."""

    confluence_url: str = ""
    username: str = ""
    api_token: str = ""
    space_key: str = TRIAGE_SPACE_KEY

    @classmethod
    def from_env(cls) -> TriageInstanceInfo:
        return cls(
            confluence_url=os.environ.get("CONFLUENCE_URL", ""),
            username=os.environ.get("CONFLUENCE_USERNAME", ""),
            api_token=os.environ.get("CONFLUENCE_API_TOKEN", ""),
            space_key=os.environ.get("TRIAGE_SPACE_KEY", TRIAGE_SPACE_KEY),
        )

    def has_credentials(self) -> bool:
        return bool(self.confluence_url and self.username and self.api_token)


class TriageResourceTracker:
    """Tracks resources created during triage tests for cleanup."""

    def __init__(self) -> None:
        self.confluence_pages: list[str] = []

    def add_page(self, page_id: str) -> None:
        self.confluence_pages.append(page_id)

    def cleanup(self, confluence_client: ConfluenceFetcher | None = None) -> None:
        if not confluence_client:
            return
        for page_id in reversed(self.confluence_pages):
            try:
                confluence_client.delete_page(page_id)
                logger.info("Cleaned up triage page %s", page_id)
            except Exception:
                logger.warning("Failed to clean up triage page %s", page_id)


@pytest.fixture(scope="session")
def triage_instance() -> TriageInstanceInfo:
    """Load triage connection info from environment."""
    info = TriageInstanceInfo.from_env()
    if not info.has_credentials():
        pytest.skip(
            "Triage tests require CONFLUENCE_URL, CONFLUENCE_USERNAME, "
            "CONFLUENCE_API_TOKEN environment variables"
        )
    return info


@pytest.fixture(scope="session")
def triage_confluence(triage_instance: TriageInstanceInfo) -> ConfluenceFetcher:
    """Session-scoped Confluence client for triage tests."""
    config = ConfluenceConfig(
        url=triage_instance.confluence_url,
        username=triage_instance.username,
        api_token=triage_instance.api_token,
    )
    return ConfluenceFetcher(config=config)


@pytest.fixture
def triage_tracker(
    triage_confluence: ConfluenceFetcher,
) -> Generator[TriageResourceTracker]:
    """Function-scoped resource tracker with auto-cleanup."""
    tracker = TriageResourceTracker()
    yield tracker
    tracker.cleanup(triage_confluence)


@pytest.fixture
def unique_id() -> str:
    """Short unique ID for test page titles."""
    return uuid.uuid4().hex[:8]
```

**Step 3: Verify conftest loads correctly**

Run: `uv run pytest tests/upstream_triage/ --collect-only 2>&1 | head -5`
Expected: "no tests ran" or empty collection (no errors)

**Step 4: Commit**

```bash
git add tests/upstream_triage/
git commit -m "test: add upstream triage test directory with conftest"
```

---

### Task 3: Create the MCPTEST Confluence space

**This is a manual + verification step, not a code change.**

**Step 1: Check if MCPTEST space already exists**

Run the existing E2E or integration test infrastructure, or use a quick script:

```bash
uv run python -c "
import os
from mcp_atlassian.confluence import ConfluenceFetcher
from mcp_atlassian.confluence.config import ConfluenceConfig
config = ConfluenceConfig(
    url=os.environ['CONFLUENCE_URL'],
    username=os.environ['CONFLUENCE_USERNAME'],
    api_token=os.environ['CONFLUENCE_API_TOKEN'],
)
client = ConfluenceFetcher(config=config)
spaces = client.get_spaces()
for s in spaces:
    print(f'{s.key}: {s.name}')
"
```

**Step 2: Create MCPTEST space if it doesn't exist**

Go to your Confluence Cloud instance → Spaces → Create space → Blank space:
- **Name:** MCP Atlassian Test Lab
- **Key:** MCPTEST

Alternatively, use the Confluence REST API:
```bash
uv run python -c "
import os, requests
url = os.environ['CONFLUENCE_URL']
auth = (os.environ['CONFLUENCE_USERNAME'], os.environ['CONFLUENCE_API_TOKEN'])
resp = requests.post(
    f'{url}/rest/api/space',
    json={'key': 'MCPTEST', 'name': 'MCP Atlassian Test Lab', 'description': {'plain': {'value': 'Sandbox for MCP Atlassian upstream issue triage. Safe to destroy.', 'representation': 'plain'}}},
    auth=auth,
    headers={'Content-Type': 'application/json'},
)
print(resp.status_code, resp.json().get('key', resp.text[:200]))
"
```

**Step 3: Verify the space is accessible**

Run: The same list-spaces script from Step 1, confirm `MCPTEST` appears.

**Step 4: No commit needed** (this is infrastructure, not code)

---

### Task 4: Write a smoke test to verify the triage harness works

**Files:**
- Create: `tests/upstream_triage/test_smoke.py`

**Step 1: Write a smoke test that creates and deletes a page in MCPTEST**

```python
"""Smoke test: verify triage test infrastructure works."""

from __future__ import annotations

import pytest

from mcp_atlassian.confluence import ConfluenceFetcher

from .conftest import TriageInstanceInfo, TriageResourceTracker

pytestmark = pytest.mark.upstream_triage


class TestTriageSmoke:
    """Verify the triage test harness connects and operates correctly."""

    def test_can_connect(self, triage_confluence: ConfluenceFetcher) -> None:
        """Verify we can connect to Confluence Cloud."""
        assert triage_confluence.config.is_cloud is True

    def test_can_create_and_read_page(
        self,
        triage_confluence: ConfluenceFetcher,
        triage_instance: TriageInstanceInfo,
        triage_tracker: TriageResourceTracker,
        unique_id: str,
    ) -> None:
        """Verify we can create a page in MCPTEST and read it back."""
        page = triage_confluence.create_page(
            space_key=triage_instance.space_key,
            title=f"Triage Smoke Test {unique_id}",
            body="<p>This page verifies the triage harness works.</p>",
            is_markdown=False,
        )
        triage_tracker.add_page(page.id)
        assert page.id is not None

        # Read it back
        fetched = triage_confluence.get_page_content(page.id)
        assert "smoke" in fetched.title.lower() or "Smoke" in fetched.title

    def test_space_exists(
        self,
        triage_confluence: ConfluenceFetcher,
        triage_instance: TriageInstanceInfo,
    ) -> None:
        """Verify the MCPTEST space exists."""
        spaces = triage_confluence.get_spaces()
        space_keys = [s.key for s in spaces]
        assert triage_instance.space_key in space_keys, (
            f"Space {triage_instance.space_key} not found. "
            f"Available: {space_keys[:10]}"
        )
```

**Step 2: Run the smoke test (will skip without credentials)**

Run: `uv run pytest tests/upstream_triage/test_smoke.py --upstream-triage -xvs`
Expected: 3 tests pass (or skip if credentials not set)

**Step 3: Commit**

```bash
git add tests/upstream_triage/test_smoke.py
git commit -m "test: add triage harness smoke test"
```

---

### Task 5: Create the upstream triage tracking log

**Files:**
- Create: `docs/upstream-triage-log.md`

**Step 1: Create the tracking log with initial candidate issues**

```markdown
# Upstream Issue Triage Log

Tracking document for systematic triage of upstream `sooperset/mcp-atlassian` issues.
Focus: Confluence Cloud bugs. Working oldest to newest.

**Test space:** MCPTEST (Confluence Cloud)
**Test directory:** `tests/upstream_triage/`
**Skill:** `.claude/skills/upstream-triage/`

## Status Key

| Status | Meaning |
|--------|---------|
| PENDING | Not yet examined |
| RESOLVED | Bug no longer reproduces — suggest closure |
| CONFIRMED | Bug still reproduces — offer PR |
| CANNOT_REPRODUCE | Insufficient info to reproduce |
| COMPLEX_DEFER | Too entangled, deferred to our issue tracker |
| OUT_OF_SCOPE | Not Confluence Cloud, or feature request |

## Triage Log

| Issue # | Title | Status | Date | Notes | Comment Link |
|---------|-------|--------|------|-------|--------------|
| 475 | Unable to get space when get page by title | PENDING | | Space limit >500 | |
| 607 | Can't find author_name, created_on, last_modified | PENDING | | Metadata fields missing | |
| 668 | Error editing Confluence page (version/status) | PENDING | | Update page error | |
| 692 | Update page error message problem | PENDING | | Error messaging | |
| 765 | Tools not working on Confluence Cloud and Jira Cloud | PENDING | | Broad — needs assessment | |
| 842 | Person tags/mentions lost on get/update page | PENDING | | ADF conversion issue | |
| 897 | Date object not returned in page data | PENDING | | Date macro handling | |
| 907 | confluence_search empty for space queries | PENDING | | CQL type=space | |

## Deferred Issues (Our Repo)

Issues filed in `Troubladore/mcp-atlassian` for future work:

| Our Issue # | Upstream # | Reason | Notes |
|-------------|-----------|--------|-------|
| | | | |

## Session Log

| Date | Session | Issues Examined | Outcomes |
|------|---------|-----------------|----------|
| | | | |
```

**Step 2: Commit**

```bash
git add docs/upstream-triage-log.md
git commit -m "docs: add upstream issue triage tracking log"
```

---

### Task 6: Create the upstream-triage skill

**Files:**
- Create: `.claude/skills/upstream-triage/skill.md`

**Step 1: Create the skill directory**

```bash
mkdir -p .claude/skills/upstream-triage
```

**Step 2: Write the skill**

```markdown
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

```
<paste test output>
```

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

```
<paste test output>
```

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
```

**Step 3: Commit**

```bash
git add .claude/skills/upstream-triage/
git commit -m "chore: add upstream-triage skill for session resumption"
```

---

### Task 7: Update project memory

**Files:**
- Modify: `/home/emaynard/.claude/projects/-home-emaynard-repos-mcp-atlassian/memory/MEMORY.md`

**Step 1: Add entry to Memory Organization section**

Add under "Memory Organization":
```markdown
- See `.claude/skills/upstream-triage/skill.md` for upstream issue triage workflow
- See `docs/upstream-triage-log.md` for triage progress tracking
```

**Step 2: Add entry to Key Patterns section**

Add under "Key Patterns":
```markdown
- Upstream triage tests: `tests/upstream_triage/`, run with `--upstream-triage` flag
- MCPTEST Confluence space is the sandbox for destructive testing
```

**Step 3: No commit needed** (memory is not in git)

---

### Task 8: Enable the skipped Confluence unit test

**Files:**
- Modify: `tests/upstream_triage/conftest.py` (add a fixture that sets CONFLUENCE_TEST_PAGE_ID)

**Step 1: Write a session-scoped fixture that creates a persistent test page**

In `tests/upstream_triage/conftest.py`, add a fixture that creates a page in MCPTEST
and sets `CONFLUENCE_TEST_PAGE_ID` in the environment:

```python
@pytest.fixture(scope="session", autouse=True)
def set_confluence_test_page_id(
    triage_confluence: ConfluenceFetcher,
    triage_instance: TriageInstanceInfo,
) -> Generator[str]:
    """Create a test page and set CONFLUENCE_TEST_PAGE_ID for the skipped unit test."""
    uid = uuid.uuid4().hex[:8]
    page = triage_confluence.create_page(
        space_key=triage_instance.space_key,
        title=f"Triage Reference Page {uid}",
        body="<p>Reference page for CONFLUENCE_TEST_PAGE_ID.</p>",
        is_markdown=False,
    )
    os.environ["CONFLUENCE_TEST_PAGE_ID"] = page.id
    yield page.id
    # Cleanup
    try:
        triage_confluence.delete_page(page.id)
    except Exception:
        logger.warning("Failed to clean up reference page %s", page.id)
    os.environ.pop("CONFLUENCE_TEST_PAGE_ID", None)
```

**Note:** This only helps when running triage tests. The unit test still skips
during normal `pytest tests/unit/` runs. A separate task should be filed in our
repo to make that test always runnable (either by creating the page in CI or by
converting it to a mock-based test).

**Step 2: Verify the fixture loads**

Run: `uv run pytest tests/upstream_triage/ --upstream-triage --collect-only 2>&1 | head -10`
Expected: Tests collected without error

**Step 3: Commit**

```bash
git add tests/upstream_triage/conftest.py
git commit -m "test: add session fixture to set CONFLUENCE_TEST_PAGE_ID for triage runs"
```

---

### Task 9: Create the first batch of reproduction test stubs

**Files:**
- Create: `tests/upstream_triage/test_issue_475.py`
- Create: `tests/upstream_triage/test_issue_607.py`
- Create: `tests/upstream_triage/test_issue_907.py`
- Create: `tests/upstream_triage/test_issue_897.py`

**Step 1: Write test stubs for the first 4 candidate issues**

Each file follows the template from the skill. The tests should target the
specific behavior reported in each issue. Read each issue fully before writing
the test.

**Issue #475:** Unable to get space when get page by title (space limit >500)
- Test: call `get_page_by_title()` with the MCPTEST space key and a known page title
- The bug was about `get_all_spaces()` hitting a 500-space limit
- Check if the space lookup works correctly

**Issue #607:** Can't find author_name, created_on, last_modified
- Test: create a page, then search for it, check metadata fields
- The bug was about missing metadata in search results

**Issue #907:** confluence_search empty for space queries
- Test: search with CQL `type=space`, verify results aren't empty
- The bug was about excerpt being empty for space results

**Issue #897:** Date object not returned in page data
- Test: create a page with a Date macro in the body, get the page, check date is present
- The bug was about date macros being stripped

**Step 2: Run the stubs to verify they fail (RED)**

Run: `uv run pytest tests/upstream_triage/ --upstream-triage -xvs`
Expected: Tests either fail (confirming bug) or pass (bug resolved)

**Step 3: Record results in tracking log**

Update `docs/upstream-triage-log.md` with the results of each test.

**Step 4: Commit**

```bash
git add tests/upstream_triage/test_issue_*.py docs/upstream-triage-log.md
git commit -m "test: add reproduction tests for upstream issues #475, #607, #897, #907"
```

---

### Task 10: Comment on upstream issues and promote tests

**Step 1: For each RESOLVED issue, comment using the template from the skill**

**Step 2: For each CONFIRMED issue, comment with reproduction evidence and offer PR**

**Step 3: For each test worth keeping, promote to the main test suite**

Move to `tests/e2e/cloud/` if it needs real API, or convert to mock-based and
move to `tests/unit/confluence/`.

**Step 4: Update tracking log with comment links**

**Step 5: Commit all changes**

```bash
git add tests/ docs/upstream-triage-log.md
git commit -m "test: record triage results and promote regression tests"
```

---

### Task 11: File deferred issues in our repo

**Step 1: For any COMPLEX_DEFER items, create issues in Troubladore/mcp-atlassian**

```bash
gh issue create \
  --repo Troubladore/mcp-atlassian \
  --label "upstream-triage" \
  --title "Upstream #NNN: <title> (deferred)" \
  --body "$(cat <<'EOF'
## Upstream Issue
sooperset/mcp-atlassian#NNN

## Why Deferred
<reason — too complex, derailed thread, needs deeper investigation>

## Notes
<any observations from initial assessment>
EOF
)"
```

**Step 2: Record our issue numbers in the tracking log**

**Step 3: File an issue for enabling the Jira skipped tests (separate effort)**

**Step 4: File an issue for platform-specific testing (Mac/Linux defer)**

**Step 5: Commit tracking log updates**

```bash
git add docs/upstream-triage-log.md
git commit -m "docs: record deferred items in triage log"
```
