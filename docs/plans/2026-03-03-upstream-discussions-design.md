# Upstream Discussions Engagement — Design

**Date:** 2026-03-03
**Status:** Approved

## Goal

Build a skill for engaging with GitHub Discussions on `sooperset/mcp-atlassian`.
The skill cross-references resolved issues/PRs from our triage work and provides
targeted, thoughtful responses to community questions — one discussion at a time,
with human approval before posting.

## Scope

- **In scope:** Q&A discussions where we can link resolved issues/PRs, and
  general guidance questions answerable from codebase knowledge.
- **Out of scope:** Opinionated feature debates, announcements, polls.
- **Response style:** Short + links (2-4 sentences, link to PR/issue, let the
  PR do the heavy lifting).

## Skill Location

`.claude/skills/upstream-discussions/skill.md`

## Core Principle: TDD for Discussions

**Evidence first, response second.** Before drafting any response, find or write
a test that proves the behavior we'd be advising. This is Red/Green TDD applied
to community engagement — we never guess, we prove.

Evidence hierarchy:
1. Existing test proves it (strongest — cite test file + function)
2. Merged PR proves it (cite PR, its tests back the claim)
3. Write a new test (run it, commit it, cite the output)
4. Codebase reading confirms it (config/setup only — cite file:line)
5. Cannot prove it — skip or defer, never draft

## Workflow

### 1. Fetch

Pull all open discussions via GraphQL:

```bash
gh api graphql -f query='{ repository(owner: "sooperset", name: "mcp-atlassian") {
  discussions(first: 50, orderBy: {field: CREATED_AT, direction: DESC}) {
    nodes { number title body category { name } comments { totalCount }
      createdAt answer { id } labels(first:5) { nodes { name } } }
  }
} }'
```

### 2. Cross-Reference

Match discussions against:
1. `docs/upstream-triage-log.md` — RESOLVED issues with PR links
2. `docs/upstream-discussions-log.md` — already-handled discussions (skip)
3. Closed issues via `gh issue list --state closed`
4. Codebase search for guidance questions

### 3. Present (One at a Time)

For each unhandled discussion, present:
- Discussion title, category, body excerpt, comment count
- Cross-reference matches (triage issues, PRs, codebase hits)
- Draft response using the appropriate template

### 4. User Review

Actions per discussion:
- **Approve** — post draft as-is
- **Edit** — user provides revised text
- **Skip** — mark as skipped with reason
- **Defer** — needs more research

### 5. Post

```bash
gh api graphql -f query='mutation {
  addDiscussionComment(input: {discussionId: "ID", body: "response"}) {
    comment { id }
  }
}'
```

### 6. Log

Track in `docs/upstream-discussions-log.md`:

| Discussion # | Title | Category | Status | Date | Action | Linked To |
|---|---|---|---|---|---|---|
| 274 | Debugging guidance | Q&A | RESPONDED | 2026-03-03 | Linked PR | PR #1120 |

Status values: RESPONDED, SKIPPED, DEFERRED, PENDING

## Response Templates

**Pattern A — Resolved by PR:**
> This was addressed in PR #NNNN. [Brief explanation]. If you're on the latest
> version, [tool/feature] should work as expected.

**Pattern B — Existing functionality:**
> The `tool_name` tool handles this. [1-2 sentences on usage].

**Pattern C — Redirect:**
> This would be best tracked as a feature request. Would you mind opening an
> issue so it can be triaged?

## Tone

- Factual, concise, helpful
- No performative enthusiasm
- Link rather than duplicate
- Represent the community, not ourselves
