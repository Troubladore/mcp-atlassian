# Upstream Issue Triage Log

Tracking document for systematic triage of upstream `sooperset/mcp-atlassian` issues.
Focus: All open issues (bugs and features, any service).

**Test spaces:** MCPTEST (Confluence Cloud), JTEST (Jira Cloud — general), JSMTEST (JSM — requires separate license)
**Skill:** `.claude/skills/upstream-triage/`

## Status Key

| Status | Meaning |
|--------|---------|
| PENDING | Not yet examined |
| RESOLVED | Feature exists / bug no longer reproduces — upstream PR with regression test |
| CONFIRMED | Feature missing or bug still reproduces — branch with failing test, fix in Phase 2 |
| CANNOT_REPRODUCE | Insufficient info to reproduce |
| COMPLEX_DEFER | Too entangled or architectural, deferred to our issue tracker |
| OUT_OF_SCOPE | Pure infrastructure, third-party plugins, documentation, or client-side |

## Difficulty Key

| Rating | Meaning | Examples |
|--------|---------|----------|
| Easy | 1-2 file change, <20 lines | Add expand param, fix filter logic, expose existing method |
| Medium | 3-5 files, needs tests, <100 lines | New error handling, model changes, new tool |
| Hard | Architectural change, >100 lines | New preprocessing pipeline, multi-instance support |

## Triage Log

| Issue # | Title | Status | Difficulty | Date | Notes | Our Issue | Fix Branch |
|---------|-------|--------|------------|------|-------|-----------|------------|
| 126 | Streamline env vars / CLI args config | OUT_OF_SCOPE | — | 2026-03-02 | Internal refactor; no behavioral test possible | | |
| 231 | Multiple Atlassian instances per server | CONFIRMED | Hard | 2026-03-02 | Server config supports only one Jira + one Confluence | | `triage/upstream-231-multiple-instances` |
| 240 | Add web links and Confluence links to Jira | RESOLVED | Easy | 2026-03-02 | `create_remote_issue_link` already implemented in links.py | | `triage/upstream-240-remote-issue-links` |
| 287 | SimpleFields utility class for Jira | CONFIRMED | Medium | 2026-03-02 | Class doesn't exist; field handling is ad-hoc in issues.py | | `triage/upstream-287-simple-fields` |
| 289 | Bitbucket support | OUT_OF_SCOPE | — | 2026-03-02 | Entirely new product, outside project scope | | |
| 332 | get jira issue links | OUT_OF_SCOPE | — | 2026-03-02 | Jira only, mislabeled as bug | #37 | |
| 336 | Multiple fields for Jira tickets (actual/expected result) | CONFIRMED | Medium | 2026-03-02 | `additional_fields` exists but project-specific field discovery incomplete | | `triage/upstream-336-jira-field-discovery` |
| 338 | Support Jira REST API v3 | RESOLVED | — | 2026-03-02 | v3 already used on Cloud for ADF payloads in client.py | | `triage/upstream-338-jira-v3` |
| 353 | Confluence GraphQL Search | CONFIRMED | Hard | 2026-03-02 | No GraphQL client; atlassian-python-api doesn't support GraphQL | | `triage/upstream-353-confluence-graphql` |
| 420 | Can't connect to mcp container, random port | OUT_OF_SCOPE | — | 2026-03-02 | Docker/infra, Server/DC | | |
| 423 | Integration Testing infrastructure | OUT_OF_SCOPE | — | 2026-03-02 | Meta-issue about testing — we're building this now | | |
| 433 | Seamless OAuth flow for MCP clients | COMPLEX_DEFER | Hard | 2026-03-02 | 3LO flow requiring server-side callback; complex auth architecture | | |
| 435 | Jira tool not registered on 2nd invocation | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud | #37 | |
| 447 | Jira Service Management support | RESOLVED | Medium | 2026-03-02 | Service desk tools exist: get_service_desk_for_project, get_service_desk_queues, get_queue_issues | | `triage/upstream-447-jsm-tools` |
| 454 | Use /customFields to detect Epic Link field dynamically | RESOLVED | Medium | 2026-03-02 | Already dynamic via `_get_epic_field_ids()` — no hardcoded customfield_10008 | | `triage/upstream-454-epic-link-dynamic` |
| 459 | Retrieve my username using token | CONFIRMED | Easy | 2026-03-02 | No dedicated `get_me` tool; `get_user_profile` requires explicit identifier | | `triage/upstream-459-get-current-user` |
| 460 | Get project issue types and fields per project | CONFIRMED | Easy | 2026-03-02 | `get_project_issue_types()` exists in projects.py but not exposed as MCP tool | | `triage/upstream-460-project-issue-types` |
| 475 | Unable to get space when get page by title | OUT_OF_SCOPE | — | 2026-03-02 | Server/DC only, reporter has >500 spaces | | |
| 483 | Add/remove watchers on Jira | RESOLVED | — | 2026-03-02 | add_watcher, remove_watcher, get_issue_watchers all implemented | | `triage/upstream-483-jira-watchers` |
| 484 | MCP Server not compatible with ChatGPT | OUT_OF_SCOPE | — | 2026-03-02 | Client-side compatibility, not server code | | |
| 486 | Informative error messages via ToolError | CONFIRMED | Medium | 2026-03-02 | FastMCP swallows exceptions; ToolError not used; errors lost to client | | `triage/upstream-486-toolerrror-propagation` |
| 499 | Zephyr plugin integration | OUT_OF_SCOPE | — | 2026-03-02 | Third-party plugin, not core Atlassian | | |
| 502 | 307 redirect on curl to mcp server | OUT_OF_SCOPE | — | 2026-03-02 | HTTP transport/infra | | |
| 507 | Streamable-HTTP Transport ISSUE | OUT_OF_SCOPE | — | 2026-03-02 | Transport, 16 comments back-and-forth | | |
| 510 | Batch / bulk update API for Jira | CONFIRMED | Medium | 2026-03-02 | batch_create_issues exists; batch update (bulk edit/move) not implemented | | `triage/upstream-510-jira-batch-update` |
| 511 | Confluence Whiteboards | CONFIRMED | Hard | 2026-03-02 | Whiteboard API not implemented; separate Confluence API endpoints required | | `triage/upstream-511-confluence-whiteboards` |
| 525 | FastMCP mount_path configuration | OUT_OF_SCOPE | — | 2026-03-02 | Infrastructure/server config, not Atlassian API | | |
| 534 | Multiple Jira DC instances | COMPLEX_DEFER | Hard | 2026-03-02 | Architectural (same root as #231); DC-specific multi-instance | | |
| 539 | MCP Connection Timed out | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud/n8n, timeout | #37 | |
| 541 | GitHub Copilot retrieves 0 tools | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud, client compat | #37 | |
| 543 | Can't assign task (assignee ignored) | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud | #37 | |
| 554 | Custom fields wiki renderer bad formatting | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud | #37 | |
| 556 | OAuth with MCP Spec / Dynamic Registration | OUT_OF_SCOPE | — | 2026-03-02 | OAuth infrastructure; complex multi-user auth | | |
| 571 | Intermittent jira_create_issue failures | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud | #37 | |
| 584 | SIGTERM not handled gracefully in Docker | OUT_OF_SCOPE | — | 2026-03-02 | Docker/infra | | |
| 590 | PAT from headers not working | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC | #37 | |
| 593 | Bulk issue creation wrong top-level key | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud | #37 | |
| 594 | HTTPS support for Docker | OUT_OF_SCOPE | — | 2026-03-02 | Infrastructure/Docker | | |
| 596 | jira_get_user_profile crashes on `me` identifier | CONFIRMED | Easy | 2026-03-02 | `me` not handled in get_user_profile; related to #459 | | `triage/upstream-596-user-profile-me` |
| 601 | max_results ignored in jira_search | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud | #37 | |
| 607 | Can't find author_name, created_on, last_modified | CONFIRMED | Easy | 2026-03-02 | Missing `history` in expand params | #34 | `fix/upstream-607-page-metadata` |
| 608 | Can't add image/media to Jira ticket | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud, attachment | #37 | |
| 613 | Tool names stripped of jira_ prefix | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud | #37 | |
| 618 | Attachment upload needs server-side path | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC, architectural | #37 | |
| 620 | issue_createmeta unsupported in Jira 9+ | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC | #37 | |
| 622 | Write API documentation | OUT_OF_SCOPE | — | 2026-03-02 | Documentation only | | |
| 626 | additionalProperties breaks Gemini | OUT_OF_SCOPE | — | 2026-03-02 | Schema/LLM compat, not Atlassian behavior | | |
| 627 | GPT Agent support | OUT_OF_SCOPE | — | 2026-03-02 | Client-side compatibility | | |
| 630 | `\n` corrupted to `n` in jira_update_issue | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud | #37 | |
| 632 | Update assignee fails on Jira DC | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC | #37 | |
| 649 | Propagate errors to MCP client | CONFIRMED | Medium | 2026-03-02 | HTTP 400/500 errors swallowed; not forwarded to client (related to #486) | | `triage/upstream-649-error-propagation` |
| 652 | Multi-Cloud OAuth 403 on Confluence | CANNOT_REPRODUCE | — | 2026-03-02 | OAuth-specific; no OAuth setup available | | |
| 653 | Latest comment returns oldest | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud | #37 | |
| 654 | Get user details in Confluence tools | CONFIRMED | Easy | 2026-03-02 | search_user exists but no get_user_by_id; only searches, doesn't fetch by accountId | | `triage/upstream-654-confluence-user-details` |
| 657 | Request before initialization complete | OUT_OF_SCOPE | — | 2026-03-02 | Transport/init, Jira DC | | |
| 667 | Attachment content parsing in Confluence | CONFIRMED | Hard | 2026-03-02 | Only metadata returned; no PDF/Word/Excel content extraction | | `triage/upstream-667-attachment-parsing` |
| 668 | Error editing Confluence page (version/status) | OUT_OF_SCOPE | — | 2026-03-02 | Server/DC only, upstream atlassian-python-api bug | | |
| 670 | jira_create_issue fails due to issueType | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud | #37 | |
| 671 | Access token forwarding | OUT_OF_SCOPE | — | 2026-03-02 | Infrastructure: central server forwarding user tokens | | |
| 673 | Get Jira custom field available values | RESOLVED | Easy | 2026-03-02 | `get_field_options` MCP tool already exists in jira server | | `triage/upstream-673-field-options` |
| 677 | Proxy env vars not respected | OUT_OF_SCOPE | — | 2026-03-02 | Infra/proxy, Jira Cloud | | |
| 684 | Raw HTML content in Jira issue description | CONFIRMED | Medium | 2026-03-02 | Only Markdown→ADF conversion supported; direct HTML not accepted | | `triage/upstream-684-jira-html-content` |
| 692 | Update page error message problem | CONFIRMED | Medium | 2026-03-02 | Confluence API returns misleading error on duplicate title | #35 | `fix/upstream-692-duplicate-title-error` |
| 693 | Can't access via Docker MCP Toolkit | OUT_OF_SCOPE | — | 2026-03-02 | Docker toolkit/infra | | |
| 708 | HTTP access with PATs for Jira and Confluence | OUT_OF_SCOPE | — | 2026-03-02 | Infrastructure: per-user PATs in centrally hosted server | | |
| 709 | jira_create_issue fails for datetime fields | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC | #37 | |
| 711 | Jira DC no actions after connect | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC | #37 | |
| 713 | Help tools / documentation | OUT_OF_SCOPE | — | 2026-03-02 | Documentation request | | |
| 714 | All tool invocations fail | OUT_OF_SCOPE | — | 2026-03-02 | Credential/setup issue, Jira Cloud | | |
| 715 | Confluence inline comments tool | CONFIRMED | Medium | 2026-03-02 | No get_inline_comments tool; get_comments only returns page-level comments | | `triage/upstream-715-confluence-inline-comments` |
| 716 | Internal Jira comments (public: false) | RESOLVED | Easy | 2026-03-02 | `add_comment(public=False)` via ServiceDesk API already implemented | | `triage/upstream-716-internal-comments` |
| 719 | jira_get_sprint_issues ignores fields param | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC | #37 | |
| 722 | Custom checklist field update fails | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC, third-party plugin | #37 | |
| 725 | Comment with security/visibility level | RESOLVED | Easy | 2026-03-02 | `comment_visibility` param in add_comment already implemented | | `triage/upstream-725-comment-visibility` |
| 735 | jira_transition_issue resolution not set | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC, str vs dict | #37 | |
| 743 | 'str' object has no attribute 'get' | RESOLVED | — | 2026-03-02 | Fixed in commit 071c522 (isinstance guard). Regression test added | [PR #1106](https://github.com/sooperset/mcp-atlassian/pull/1106) | |
| 748 | Cursor IDE all tools fail | OUT_OF_SCOPE | — | 2026-03-02 | Jira Cloud, 7 comments, likely env issue | | |
| 751 | Xray plugin integration | OUT_OF_SCOPE | — | 2026-03-02 | Third-party plugin | | |
| 756 | confluence_search_user fails on Server | OUT_OF_SCOPE | — | 2026-03-02 | Server/DC only | | |
| 765 | Tools not working on Confluence/Jira Cloud | CANNOT_REPRODUCE | — | 2026-03-02 | Maintainer confirmed works, credential misconfiguration | | |
| 777 | Unclear reason of failed connection | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC, infra/debug | | |
| 781 | Service Accounts | COMPLEX_DEFER | Hard | 2026-03-02 | Different API endpoint (api.atlassian.com/ex/...); OAuth-style auth pattern | | |
| 832 | Add DeepWiki badge to README | OUT_OF_SCOPE | — | 2026-03-02 | README/documentation only | | |
| 833 | Add docs URL to GitHub About section | OUT_OF_SCOPE | — | 2026-03-02 | GitHub settings, not code | | |
| 842 | Person tags/mentions lost on get/update | COMPLEX_DEFER | Hard | 2026-03-02 | Maintainer has 3-option analysis. Architectural. | | |
| 847 | JSM internal comments (public: false) | RESOLVED | Easy | 2026-03-02 | Same as #716 — `add_comment(public=False)` already works via ServiceDesk API | | `triage/upstream-847-jsm-internal-comments` |
| 850 | Per-request config headers (multi-user) | COMPLEX_DEFER | Hard | 2026-03-02 | Multi-tenant server architecture; requires session isolation | | |
| 857 | Get remote links from Jira issue | CONFIRMED | Easy | 2026-03-02 | `create_remote_issue_link` exists but GET not implemented | | `triage/upstream-857-get-remote-links` |
| 858 | OAuth fails — missing refresh token | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC, OAuth | | |
| 866 | ProForma forms field update limitations | OUT_OF_SCOPE | — | 2026-03-02 | Stale; ProForma forms API already implemented | | |
| 868 | 100% CPU fakeredis busy-loop | OUT_OF_SCOPE | — | 2026-03-02 | Upstream FastMCP bug, not mcp-atlassian | | |
| 884 | 403 from DDoS protection (User-Agent) | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC | #37 | |
| 889 | Wiki page link wrong format | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC | #37 | |
| 897 | Date object not returned in page data | RESOLVED | — | 2026-03-02 | Date macro content IS preserved. Regression test added | [PR #1107](https://github.com/sooperset/mcp-atlassian/pull/1107) | |
| 907 | confluence_search empty for space queries | CONFIRMED | Easy | 2026-03-02 | CQL `type=space` returns 0 results. `content` key vs `space` key | #36 | `fix/upstream-907-cql-space-search` |
| 909 | Orphaned processes after close | OUT_OF_SCOPE | — | 2026-03-02 | Infra/process management | | |
| 965 | Confluence create/update date fields empty | CONFIRMED | Easy | 2026-03-02 | Same root cause as #607 — `history` not in expand params | | `triage/upstream-965-confluence-dates` |
| 968 | Scoped (granular) Atlassian Cloud API tokens | CONFIRMED | Medium | 2026-03-02 | Scoped tokens need api.atlassian.com/ex/... routing, not direct site URL | | `triage/upstream-968-scoped-tokens` |
| 996 | Download/upload page content to file | CONFIRMED | Easy | 2026-03-02 | No confluence_download_page_to_file tool; large page bodies bloat LLM context | | `triage/upstream-996-page-content-file` |
| 1082 | Cloud-only tools exposed to DC agents | OUT_OF_SCOPE | — | 2026-03-02 | Jira DC, toolset filtering. Also affects Confluence. | #37 | |
| 1096 | per-request cloud_id overridden | OUT_OF_SCOPE | — | 2026-03-02 | Mixed DC+Cloud OAuth, auth only | | |
| 1097 | DCR redirect_uri loop | OUT_OF_SCOPE | — | 2026-03-02 | OAuth, not Atlassian content | | |
| 1100 | Shared helpers for outcome-oriented tools | OUT_OF_SCOPE | — | 2026-03-02 | Prerequisite utility; not a standalone feature | | |
| 1101 | add include param to jira_get_issue | CONFIRMED | Medium | 2026-03-02 | No inline enrichment; 2-4 separate calls needed for transitions/watchers/changelog | | `triage/upstream-1101-get-issue-include` |
| 1102 | update_issue orchestration (transition/comment/worklog) | CONFIRMED | Medium | 2026-03-02 | Each action requires separate tool call; no consolidated update | | `triage/upstream-1102-update-issue-orchestration` |
| 1103 | add include param to confluence_get_page | CONFIRMED | Medium | 2026-03-02 | No inline enrichment; 2-4 separate calls needed for comments/labels/views | | `triage/upstream-1103-get-page-include` |
| 1104 | Roadmap: outcome-oriented tool restructuring | OUT_OF_SCOPE | — | 2026-03-02 | Roadmap/tracking issue, not a code change | | |

## Summary

| Status | Count |
|--------|-------|
| RESOLVED | 12 |
| CONFIRMED | 26 |
| CANNOT_REPRODUCE | 3 |
| COMPLEX_DEFER | 6 |
| OUT_OF_SCOPE | 60 |
| **Total** | **107** |

## Phase 2: Test Branches

All 107 issues assessed. Next: create one branch per testable issue (RESOLVED + CONFIRMED), write E2E or unit test, submit upstream PR for RESOLVED items.

### Priority Queue (oldest first, by status)

**RESOLVED — branch + upstream PR:**

| Issue | Title | Difficulty | Branch | Test type |
|-------|-------|------------|--------|-----------|
| 240 | Web/Confluence links to Jira | Easy | `triage/upstream-240-remote-issue-links` | E2E Jira (JTEST) |
| 338 | Jira REST API v3 | — | `triage/upstream-338-jira-v3` | Unit |
| 447 | JSM tools | Medium | `triage/upstream-447-jsm-tools` | Unit (no JSM project) |
| 454 | Epic link dynamic field detection | Medium | `triage/upstream-454-epic-link-dynamic` | Unit |
| 483 | Jira watchers | — | `triage/upstream-483-jira-watchers` | E2E Jira (JTEST) |
| 673 | Get field options | Easy | `triage/upstream-673-field-options` | E2E Jira (JTEST) |
| 716 | Internal Jira comments | Easy | `triage/upstream-716-internal-comments` | Unit (no JSM) |
| 725 | Comment visibility/security | Easy | `triage/upstream-725-comment-visibility` | E2E Jira (JTEST) |
| 743 | 'str' no attribute 'get' | — | already in [PR #1106](https://github.com/sooperset/mcp-atlassian/pull/1106) | Unit ✓ |
| 847 | JSM internal comments | Easy | `triage/upstream-847-jsm-internal-comments` | Unit (no JSM, same as #716) |
| 897 | Date macro content | — | already in [PR #1107](https://github.com/sooperset/mcp-atlassian/pull/1107) | E2E ✓ |

**CONFIRMED — branch with failing test:**

| Issue | Title | Difficulty | Branch | Test type |
|-------|-------|------------|--------|-----------|
| 231 | Multiple instances | Hard | `triage/upstream-231-multiple-instances` | Unit |
| 287 | SimpleFields class | Medium | `triage/upstream-287-simple-fields` | Unit |
| 336 | Multi-field Jira ticket creation | Medium | `triage/upstream-336-jira-field-discovery` | E2E Jira |
| 353 | Confluence GraphQL search | Hard | `triage/upstream-353-confluence-graphql` | Unit |
| 459 | Get current user (get_me) | Easy | `triage/upstream-459-get-current-user` | E2E Jira |
| 460 | Project issue types MCP tool | Easy | `triage/upstream-460-project-issue-types` | E2E Jira |
| 486 | ToolError propagation | Medium | `triage/upstream-486-toolerrror-propagation` | Unit |
| 510 | Jira batch update | Medium | `triage/upstream-510-jira-batch-update` | E2E Jira |
| 511 | Confluence Whiteboards | Hard | `triage/upstream-511-confluence-whiteboards` | Unit |
| 596 | user_profile crashes on 'me' | Easy | `triage/upstream-596-user-profile-me` | Unit |
| 607 | Confluence page metadata | Easy | `fix/upstream-607-page-metadata` | E2E Confluence ✓ |
| 649 | Error propagation to client | Medium | `triage/upstream-649-error-propagation` | Unit |
| 654 | Confluence user details | Easy | `triage/upstream-654-confluence-user-details` | E2E Confluence |
| 667 | Attachment content parsing | Hard | `triage/upstream-667-attachment-parsing` | E2E Confluence |
| 684 | Raw HTML in Jira description | Medium | `triage/upstream-684-jira-html-content` | Unit |
| 692 | Duplicate title error message | Medium | `fix/upstream-692-duplicate-title-error` | E2E Confluence ✓ |
| 715 | Confluence inline comments | Medium | `triage/upstream-715-confluence-inline-comments` | E2E Confluence |
| 857 | Get Jira remote links | Easy | `triage/upstream-857-get-remote-links` | E2E Jira |
| 907 | CQL space search | Easy | `fix/upstream-907-cql-space-search` | E2E Confluence ✓ |
| 965 | Confluence dates (same root as #607) | Easy | `triage/upstream-965-confluence-dates` | E2E Confluence |
| 968 | Scoped API tokens | Medium | `triage/upstream-968-scoped-tokens` | Unit |
| 996 | Page content to file | Easy | `triage/upstream-996-page-content-file` | Unit |
| 1101 | get_issue include param | Medium | `triage/upstream-1101-get-issue-include` | E2E Jira |
| 1102 | update_issue orchestration | Medium | `triage/upstream-1102-update-issue-orchestration` | E2E Jira |
| 1103 | get_page include param | Medium | `triage/upstream-1103-get-page-include` | E2E Confluence |

**Already branched (from previous sessions):**
- `fix/upstream-607-page-metadata` — failing E2E test exists ✓
- `fix/upstream-692-duplicate-title-error` — failing E2E test exists ✓
- `fix/upstream-907-cql-space-search` — failing E2E test exists ✓
- `fix/upstream-743-str-get-regression` — passing, upstream PR #1106 open ✓
- `fix/upstream-897-date-macro-regression` — passing, upstream PR #1107 open ✓

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
| 2026-03-02 | 3 | All 107 re-examined including features | Expanded to 12 RESOLVED, 26 CONFIRMED; added JTEST Jira project; full branch plan |
