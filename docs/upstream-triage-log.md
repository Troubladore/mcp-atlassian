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
| 332 | get jira issue links | OUT_OF_SCOPE | — | 2026-03-02 | Jira only, mislabeled as bug | #37 |
| 420 | Can't connect to mcp container, random port | OUT_OF_SCOPE | — | 2026-03-02 | Docker/infra, Server/DC | |
| 435 | Jira tool not registered on 2nd invocation | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud | #37 |
| 475 | Unable to get space when get page by title | OUT_OF_SCOPE | — | 2026-03-02 | Server/DC only, reporter has >500 spaces | |
| 502 | 307 redirect on curl to mcp server | OUT_OF_SCOPE | — | 2026-03-02 | HTTP transport/infra | |
| 507 | Streamable-HTTP Transport ISSUE | OUT_OF_SCOPE | — | 2026-03-02 | Transport, 16 comments back-and-forth | |
| 539 | MCP Connection Timed out | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud/n8n, timeout | #37 |
| 541 | GitHub Copilot retrieves 0 tools | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud, client compat | #37 |
| 543 | Can't assign task (assignee ignored) | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud | #37 |
| 554 | Custom fields wiki renderer bad formatting | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud | #37 |
| 571 | Intermittent jira_create_issue failures | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud | #37 |
| 584 | SIGTERM not handled gracefully in Docker | OUT_OF_SCOPE | — | 2026-03-02 | Docker/infra | |
| 590 | PAT from headers not working | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC | #37 |
| 593 | Bulk issue creation wrong top-level key | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud | #37 |
| 596 | jira_get_user_profile crashes on `me` | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud | #37 |
| 601 | max_results ignored in jira_search | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud | #37 |
| 607 | Can't find author_name, created_on, last_modified | CONFIRMED | Easy | 2026-03-02 | Missing `history` in expand params | #34 |
| 608 | Can't add image/media to Jira ticket | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud, attachment | #37 |
| 613 | Tool names stripped of jira_ prefix | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud | #37 |
| 618 | Attachment upload needs server-side path | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC, architectural | #37 |
| 620 | issue_createmeta unsupported in Jira 9+ | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC | #37 |
| 626 | additionalProperties breaks Gemini | OUT_OF_SCOPE | — | 2026-03-02 | Schema/LLM compat, not Confluence | |
| 630 | `\n` corrupted to `n` in jira_update_issue | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud | #37 |
| 632 | Update assignee fails on Jira DC | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC | #37 |
| 652 | Multi-Cloud OAuth 403 on Confluence | CANNOT_REPRODUCE | — | 2026-03-02 | Confluence Cloud, OAuth-specific, no OAuth setup | |
| 653 | Latest comment returns oldest | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud | #37 |
| 657 | Request before initialization complete | OUT_OF_SCOPE | — | 2026-03-02 | Transport/init, Jira DC | |
| 668 | Error editing Confluence page (version/status) | OUT_OF_SCOPE | — | 2026-03-02 | Server/DC only, upstream atlassian-python-api bug | |
| 670 | jira_create_issue fails due to issueType | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud | #37 |
| 677 | Proxy env vars not respected | OUT_OF_SCOPE | — | 2026-03-02 | Infra/proxy, Jira Cloud | |
| 692 | Update page error message problem | CONFIRMED | Medium | 2026-03-02 | Confluence API returns misleading error on duplicate title | #35 |
| 693 | Can't access via Docker MCP Toolkit | OUT_OF_SCOPE | — | 2026-03-02 | Docker toolkit/infra | |
| 709 | jira_create_issue fails for datetime fields | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC | #37 |
| 711 | Jira DC no actions after connect | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC | #37 |
| 714 | All tool invocations fail | OUT_OF_SCOPE | — | 2026-03-02 | Credential/setup issue, Jira Cloud | |
| 719 | jira_get_sprint_issues ignores fields param | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC | #37 |
| 722 | Custom checklist field update fails | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC, third-party plugin | #37 |
| 735 | jira_transition_issue resolution not set | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC, str vs dict | #37 |
| 743 | 'str' object has no attribute 'get' | RESOLVED | — | 2026-03-02 | Fixed in commit 071c522 (isinstance guard). Regression test added | [PR #1106](https://github.com/sooperset/mcp-atlassian/pull/1106) |
| 748 | Cursor IDE all tools fail | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud, 7 comments, likely env issue | |
| 756 | confluence_search_user fails on Server | OUT_OF_SCOPE | — | 2026-03-02 | Server/DC only | |
| 765 | Tools not working on Confluence/Jira Cloud | CANNOT_REPRODUCE | — | 2026-03-02 | Maintainer confirmed works, credential misconfiguration | |
| 777 | Unclear reason of failed connection | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC, infra/debug | |
| 842 | Person tags/mentions lost on get/update | COMPLEX_DEFER | Hard | 2026-03-02 | Maintainer has 3-option analysis. Architectural. | |
| 858 | OAuth fails — missing refresh token | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC, OAuth | |
| 868 | 100% CPU fakeredis busy-loop | OUT_OF_SCOPE | — | 2026-03-02 | Upstream FastMCP bug, not mcp-atlassian | |
| 884 | 403 from DDoS protection (User-Agent) | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC | #37 |
| 889 | Wiki page link wrong format | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC | #37 |
| 897 | Date object not returned in page data | RESOLVED | — | 2026-03-02 | Date macro content IS preserved. Regression test added | [PR #1107](https://github.com/sooperset/mcp-atlassian/pull/1107) |
| 907 | confluence_search empty for space queries | CONFIRMED | Easy | 2026-03-02 | CQL `type=space` returns 0 results. `content` key vs `space` key | #36 |
| 909 | Orphaned processes after close | OUT_OF_SCOPE | — | 2026-03-02 | Infra/process management | |
| 1082 | Cloud-only tools exposed to DC agents | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC, toolset filtering. Also affects Confluence. | #37 |
| 1096 | per-request cloud_id overridden | OUT_OF_SCOPE | — | 2026-03-02 | Mixed DC+Cloud OAuth, auth only | |
| 1097 | DCR redirect_uri loop | OUT_OF_SCOPE | — | 2026-03-02 | OAuth, not Confluence content | |

## Deferred Issues (Our Repo)

| Our Issue # | Upstream # | Difficulty | Title |
|-------------|-----------|------------|-------|
| [#34](https://github.com/Troubladore/mcp-atlassian/issues/34) | 607 | Easy | Missing page metadata (created, updated, author) |
| [#35](https://github.com/Troubladore/mcp-atlassian/issues/35) | 692 | Medium | Misleading error message on duplicate title update |
| [#36](https://github.com/Troubladore/mcp-atlassian/issues/36) | 907 | Easy | CQL type=space search returns empty results |
| [#37](https://github.com/Troubladore/mcp-atlassian/issues/37) | multiple | — | Jira bugs backlog (full list) |

## Session Log

| Date | Session | Issues Examined | Outcomes |
|------|---------|-----------------|----------|
| 2026-03-02 | 1 | #475, #607, #668, #692, #765, #842, #897, #907 | 2 OUT_OF_SCOPE, 3 CONFIRMED, 1 RESOLVED, 1 CANNOT_REPRODUCE, 1 COMPLEX_DEFER |
| 2026-03-02 | 2 | All 107 open issues (complete pass) | 3 CONFIRMED, 2 RESOLVED, 2 CANNOT_REPRODUCE, 1 COMPLEX_DEFER, rest OUT_OF_SCOPE or Jira |
