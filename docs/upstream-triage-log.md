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
| 475 | Unable to get space when get page by title | OUT_OF_SCOPE | 2026-03-02 | Server/DC only, reporter has >500 spaces | |
| 607 | Can't find author_name, created_on, last_modified | CONFIRMED | 2026-03-02 | `get_page_content()` missing `history` in expand params — created/updated/author all empty. Fix: add `history` to expand. PR-able. | |
| 668 | Error editing Confluence page (version/status) | OUT_OF_SCOPE | 2026-03-02 | Server/DC only, confirmed as upstream `atlassian-python-api` bug | |
| 692 | Update page error message problem | CONFIRMED | 2026-03-02 | Confluence API returns misleading "No space or no content type..." instead of "title already exists". mcp-atlassian passes it through. Could improve error parsing. | |
| 765 | Tools not working on Confluence Cloud and Jira Cloud | CANNOT_REPRODUCE | 2026-03-02 | Maintainer confirmed works on their end, likely user credential misconfiguration | |
| 842 | Person tags/mentions lost on get/update page | COMPLEX_DEFER | 2026-03-02 | Maintainer has detailed analysis with 3 solution approaches. Not low-hanging fruit. | |
| 897 | Date object not returned in page data | RESOLVED | 2026-03-02 | Date macro content IS preserved in current code. Test passes on Cloud. | |
| 907 | confluence_search empty for space queries | CONFIRMED | 2026-03-02 | CQL `type=space` returns 0 results on Cloud. Search processing expects `content` key but spaces use `space` key. PR-able. | |

## Deferred Issues (Our Repo)

Issues filed in `Troubladore/mcp-atlassian` for future work:

| Our Issue # | Upstream # | Reason | Notes |
|-------------|-----------|--------|-------|
| | | | |

## Session Log

| Date | Session | Issues Examined | Outcomes |
|------|---------|-----------------|----------|
| 2026-03-02 | 1 | #475, #607, #668, #692, #765, #842, #897, #907 | 2 OUT_OF_SCOPE, 3 CONFIRMED, 1 RESOLVED, 1 CANNOT_REPRODUCE, 1 COMPLEX_DEFER |
