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
| RESOLVED | Bug no longer reproduces — comment on upstream suggesting closure |
| CONFIRMED | Bug still reproduces — file issue in our repo, fix in Phase 2 |
| CANNOT_REPRODUCE | Insufficient info to reproduce |
| COMPLEX_DEFER | Too entangled, deferred to our issue tracker |
| OUT_OF_SCOPE | Not Confluence Cloud, or feature request |

## Difficulty Key

| Rating | Meaning | Examples |
|--------|---------|----------|
| Easy | 1-2 file change, <20 lines | Add expand param, fix filter logic |
| Medium | 3-5 files, needs tests, <100 lines | New error handling, model changes |
| Hard | Architectural change, >100 lines | New preprocessing pipeline, round-trip fidelity |

## Triage Log

| Issue # | Title | Status | Difficulty | Date | Notes | Our Issue |
|---------|-------|--------|------------|------|-------|-----------|
| 475 | Unable to get space when get page by title | OUT_OF_SCOPE | — | 2026-03-02 | Server/DC only, reporter has >500 spaces | |
| 607 | Can't find author_name, created_on, last_modified | CONFIRMED | Easy | 2026-03-02 | Missing `history` in expand params. Fix: add `history` to expand string in `pages.py` | #34 |
| 668 | Error editing Confluence page (version/status) | OUT_OF_SCOPE | — | 2026-03-02 | Server/DC only, upstream `atlassian-python-api` bug | |
| 692 | Update page error message problem | CONFIRMED | Medium | 2026-03-02 | Confluence API returns misleading error on duplicate title. Needs error parsing/detection layer | #35 |
| 765 | Tools not working on Confluence Cloud and Jira Cloud | CANNOT_REPRODUCE | — | 2026-03-02 | Maintainer confirmed works, likely user credential misconfiguration | |
| 842 | Person tags/mentions lost on get/update page | COMPLEX_DEFER | Hard | 2026-03-02 | Maintainer has detailed analysis with 3 solution approaches. Architectural change needed | |
| 897 | Date object not returned in page data | RESOLVED | — | 2026-03-02 | Date macro content IS preserved in current code. Commented on upstream | |
| 907 | confluence_search empty for space queries | CONFIRMED | Easy | 2026-03-02 | CQL `type=space` returns 0 results. Search processing expects `content` key but spaces use `space` key | #36 |

## Deferred Issues (Our Repo)

Issues filed in `Troubladore/mcp-atlassian` for CONFIRMED items (Phase 2 fix work):

| Our Issue # | Upstream # | Difficulty | Title |
|-------------|-----------|------------|-------|
| [#34](https://github.com/Troubladore/mcp-atlassian/issues/34) | 607 | Easy | Missing page metadata (created, updated, author) |
| [#35](https://github.com/Troubladore/mcp-atlassian/issues/35) | 692 | Medium | Misleading error message on duplicate title update |
| [#36](https://github.com/Troubladore/mcp-atlassian/issues/36) | 907 | Easy | CQL type=space search returns empty results |

## Session Log

| Date | Session | Issues Examined | Outcomes |
|------|---------|-----------------|----------|
| 2026-03-02 | 1 | #475, #607, #668, #692, #765, #842, #897, #907 | 2 OUT_OF_SCOPE, 3 CONFIRMED, 1 RESOLVED, 1 CANNOT_REPRODUCE, 1 COMPLEX_DEFER |
