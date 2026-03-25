# Upstream Issue Triage — Confluence Cloud

**Date:** 2026-03-02
**Scope:** Bug triage for upstream `sooperset/mcp-atlassian` issues
**Focus:** Confluence Cloud only (no Jira, no Server/DC)

---

## Objective

Systematically work through the open upstream bug backlog for Confluence Cloud.
For each issue: attempt reproduction, classify the result, comment on the issue
with evidence, and promote useful tests to the main suite.

Goal is backlog reduction, not perfection. Low-hanging fruit first; complex or
entangled issues get deferred to our repo's issue tracker for future work.

---

## Scope Rules

**In scope:**
- Issues tagged `bug`
- Related to Confluence (not Jira-only)
- Reproducible on Cloud (not Server/DC-only)
- Not deeply entangled (no multi-month failed-fix threads)

**Out of scope:**
- Feature requests / enhancements
- Server/DC-only bugs
- Jira bugs (tracked separately via our repo issues)
- Issues with active PRs already addressing them

**"Read the room" heuristic:** If an issue has >5 comments with back-and-forth
debugging or failed PRs, flag as `COMPLEX_DEFER` and move on.

**Processing order:** Oldest creation date first, 4-5 issues in parallel per session.

---

## Infrastructure

### MCPTEST Confluence Space

- Created programmatically via MCP tools
- Ephemeral sandbox — create pages, break things, delete freely
- Clean up after each session (no persistent test artifacts)
- Space key: `MCPTEST`, name: "MCP Atlassian Test Lab"

### Test Harness

- **Location:** `tests/upstream_triage/`
- **Naming:** One test file per issue: `test_issue_NNN.py`
- **Marker:** `@pytest.mark.upstream_triage`
- **Fixtures:** Reuses existing Cloud E2E fixtures with MCP server credentials
- **Env var mapping:** `CONFLUENCE_URL` → `CLOUD_E2E_CONFLUENCE_URL`, etc.

### Skipped Unit Tests

- 1 Confluence test (`test_confluence_real_data.py`): Enable by setting
  `CONFLUENCE_TEST_PAGE_ID` to a page in MCPTEST
- 4 Jira tests: Deferred (tracked in our repo)

---

## Per-Issue Workflow

```
1. READ        → Read issue body, comments, linked PRs
2. ASSESS      → Cloud-applicable? Derailed? Active PR? → Skip or proceed
3. REPRODUCE   → Write a test targeting the reported behavior
4. RUN         → Execute against MCPTEST space on Cloud
5. CLASSIFY    → One of:
                  RESOLVED:           Bug no longer exists
                  CONFIRMED:          Bug still present
                  CANNOT_REPRODUCE:   Insufficient info
                  COMPLEX_DEFER:      Too entangled
6. RECORD      → Update tracking log with status + evidence
7. ACT         →
                  RESOLVED:           Comment with evidence, suggest closure
                  CONFIRMED:          Comment with repro steps, offer PR
                  CANNOT_REPRODUCE:   Comment asking for more info
                  COMPLEX_DEFER:      Log only, no upstream comment
8. PROMOTE     → Move valuable tests to main suite:
                  - Bug confirmed → regression test in tests/unit/ or tests/e2e/cloud/
                  - Bug resolved  → regression guard in main suite
                  - One-off       → discard or keep in triage dir
```

### Comment Etiquette

- Polite, factual, includes test output
- No promises — offer to submit PR if maintainer wants
- Always mention version/commit tested against
- Never mark conversations as resolved (maintainer's prerogative)

---

## Tracking & Persistence

### Tracking Log

**Location:** `docs/upstream-triage-log.md`

Table format:

| Issue # | Title | Status | Date | Notes | Comment Link |
|---------|-------|--------|------|-------|--------------|

Statuses: `PENDING`, `RESOLVED`, `CONFIRMED`, `CANNOT_REPRODUCE`,
`COMPLEX_DEFER`, `OUT_OF_SCOPE`

### Skill

**Location:** `.claude/skills/upstream-triage/`

Encodes the full workflow for session resumption:
- References tracking log, test location, MCPTEST space
- Includes "read the room" heuristic and scoping rules
- Comment templates
- Session resumption: read log → find PENDING → pick up 4-5

### Memory

Entry in `MEMORY.md` pointing to skill and tracking log.

### Deferred Work

- `COMPLEX_DEFER` items → create issue in `Troubladore/mcp-atlassian`
- Jira-related findings → create issue in our repo
- Platform-specific findings (Mac/Linux) → create issue in our repo

---

## Candidate Issues (Initial Batch)

Confluence Cloud bugs, oldest first:

| # | Created | Title | Notes |
|---|---------|-------|-------|
| 475 | 2025-06-01 | Unable to get space when get page by title | Space limit issue |
| 607 | 2025-07-10 | Can't find author_name, created_on, last_modified | Metadata fields |
| 668 | 2025-08-26 | Error editing Confluence page (version/status) | Update page error |
| 692 | 2025-09-12 | Update page error message problem | Error messaging |
| 765 | 2025-11-26 | Tools not working on Confluence Cloud and Jira Cloud | Broad — assess |
| 842 | 2026-01-08 | Person tags/mentions lost on get/update page | ADF conversion |
| 897 | 2026-02-04 | Date object not returned in page data | Date macro |
| 907 | 2026-02-10 | confluence_search empty for space queries | CQL search |

---

## Success Criteria

- Tracking log populated with status for each examined issue
- Upstream issues commented with reproduction evidence
- Valuable tests promoted to main suite
- Skill and tracking doc committed so work resumes seamlessly
- Skipped Confluence unit test enabled
