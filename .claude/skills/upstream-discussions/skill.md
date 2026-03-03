---
name: upstream-discussions
description: Use when responding to upstream sooperset/mcp-atlassian GitHub Discussions. Provides the workflow for cross-referencing resolved issues/PRs, drafting targeted responses, and tracking engagement.
---

# Upstream Discussions Engagement

## Quick Start

1. Read the tracking log: `docs/upstream-discussions-log.md`
2. Fetch open discussions (see Fetch step below)
3. For each discussion (oldest first):
   a. Cross-reference against triage log, closed issues, and codebase
   b. **Find or write evidence** (test, PR, codebase citation) — BEFORE drafting
   c. If evidence exists: run/verify it, then draft response citing it
   d. If no evidence: skip or defer — never draft without proof
   e. Present to user for review
   f. Post if approved, log either way
4. Commit log updates

**This is TDD for Discussions.** Evidence first, response second. Always.

## Scope

**Respond to (concrete resolutions + light guidance):**
- Q&A where a resolved triage issue or merged PR answers the question
- Questions answerable from codebase knowledge (existing tools, configuration)
- General questions where we can point to specific functionality

**Skip:**
- Discussions already answered satisfactorily
- Feature debates or opinion-based discussions
- Announcements, polls, show-and-tell
- Discussions where we'd just be guessing
- Anything we cannot back with evidence (test, PR, or codebase citation)

## Fetch Discussions

```bash
gh api graphql -f query='{ repository(owner: "sooperset", name: "mcp-atlassian") {
  discussions(first: 50, orderBy: {field: CREATED_AT, direction: DESC}) {
    nodes { number title body category { name } comments { totalCount }
      createdAt answer { id } labels(first:5) { nodes { name } } }
  }
} }'
```

To read a specific discussion's full body and comments:
```bash
gh api graphql -f query='{ repository(owner: "sooperset", name: "mcp-atlassian") {
  discussion(number: NNN) {
    id number title body category { name }
    comments(first: 20) { nodes { body author { login } createdAt } }
  }
} }'
```

## Cross-Reference Sources

Check these in order to find matches:

1. **Triage log** — `docs/upstream-triage-log.md` for RESOLVED issues with PR links
2. **Discussions log** — `docs/upstream-discussions-log.md` for already-handled (skip)
3. **Closed issues** — `gh issue list --repo sooperset/mcp-atlassian --state closed --limit 100`
4. **Codebase search** — grep `src/mcp_atlassian/` for relevant tools, methods, config
5. **Test search** — grep `tests/` for existing tests that prove the behavior


## Per-Discussion Workflow (TDD for Discussions)

### Step 1: Read & Cross-Reference

Read the full discussion + comments. Cross-reference against triage log, closed
issues, and codebase. Identify what the user is asking about.

### Step 2: Find or Build Evidence (BEFORE drafting)

This is the RED/GREEN step. Before writing a single word of response:

1. **Search for existing tests** that prove the behavior:
   ```bash
   grep -r "relevant_keyword" tests/
   ```
2. **If test exists** — run it. Confirm it passes (GREEN). This is your evidence.
3. **If no test exists but one is warranted** — write a unit test that demonstrates
   the correct behavior. Run it. Watch it pass. Commit it to the branch.
4. **If a merged PR covers it** — the PR's test evidence is sufficient. Cite it.
5. **If only codebase reading confirms it** (config/setup questions) — cite file:line.
6. **If you cannot establish evidence** — SKIP or DEFER. Do not draft.

**The evidence step is not optional.** A response without evidence is a guess.
Guesses posted to a community forum damage trust.

### Step 3: Present to User (evidence + draft)

Only after evidence is established, present:

```
─── Discussion #NNN: "Title" (Category) ───
Created: YYYY-MM-DD | Comments: N | Answered: yes/no
URL: https://github.com/sooperset/mcp-atlassian/discussions/NNN

Body (first 500 chars):
> [excerpt]

Existing comments summary:
> [key points from thread]

Cross-reference:
> Matches triage issue #NNN (RESOLVED, PR #NNNN)
> — or —
> Codebase: `tool_name` in src/mcp_atlassian/servers/jira.py handles this

Evidence (REQUIRED):
> GREEN: tests/unit/.../test_file.py::test_name passes — proves correct usage
> — or —
> GREEN: PR #NNNN merged with test coverage
> — or —
> NEW TEST: wrote tests/unit/.../test_file.py::test_name — passes, committed
> — or —
> CITE: src/mcp_atlassian/config.py:42 shows the configuration option

Draft response:
> [generated using appropriate template, citing the evidence]

Action: [Approve] [Edit] [Skip] [Defer]
```

Always use AskUserQuestion for the action — never post without explicit approval.

## Response Templates

### Pattern A — Resolved by PR

Use when a triage issue maps directly to the discussion topic.

```
This was addressed in PR #NNNN ([brief title]). [One sentence on what changed].

If you're on the latest version, [tool/feature] should work as expected. See
the PR for details: https://github.com/sooperset/mcp-atlassian/pull/NNNN
```

### Pattern B — Existing Functionality (Guidance)

Use when the answer is already in the codebase but the user may not know.

```
The `tool_name` tool handles this. [1-2 sentences explaining usage or config].

For reference, [link to relevant file or docs section if available].
```

### Pattern C — Redirect to Issue

Use when the discussion describes a real bug or feature request that should be tracked.

```
This sounds like it would be best tracked as [a bug report / feature request].
Would you mind opening an issue? That way it can be prioritized and tracked
properly.
```

### Pattern D — Already Resolved in Thread

Use when the discussion already has a correct answer but isn't marked resolved.

```
[Skip — no response needed, but log as SKIPPED with reason "already answered"]
```

## Post Response

Get the discussion's GraphQL node ID first (from the fetch query), then post:

```bash
gh api graphql -f query='mutation {
  addDiscussionComment(input: {
    discussionId: "DISCUSSION_NODE_ID",
    body: "RESPONSE_TEXT"
  }) {
    comment { id url }
  }
}'
```

**Important:** Escape the response body properly for JSON. Use a variable:

```bash
BODY='The response text here'
gh api graphql -f query="mutation { addDiscussionComment(input: { discussionId: \"NODE_ID\", body: \"$BODY\" }) { comment { id url } } }"
```

Or better, use the `-f` flag for variables:

```bash
gh api graphql \
  -f query='mutation($discussionId: ID!, $body: String!) {
    addDiscussionComment(input: {discussionId: $discussionId, body: $body}) {
      comment { id url }
    }
  }' \
  -f discussionId="NODE_ID" \
  -f body="Response text here"
```

## Log Updates

After each discussion is handled, update `docs/upstream-discussions-log.md`:

```markdown
| Discussion # | Title | Category | Status | Date | Action | Linked To |
|---|---|---|---|---|---|---|
| NNN | Title | Q&A | RESPONDED | 2026-03-03 | Linked PR | PR #NNNN |
| NNN | Title | General | SKIPPED | 2026-03-03 | Already answered | — |
| NNN | Title | Q&A | DEFERRED | 2026-03-03 | Needs research | — |
```

**Status values:**
- RESPONDED — we posted a reply
- SKIPPED — no action needed (already answered, off-topic, etc.)
- DEFERRED — needs more research before responding
- PENDING — not yet examined

Commit log updates to the feature branch periodically.

## Tone Guidelines

- **Factual and concise** — no filler, no "Happy to help!"
- **Link rather than duplicate** — point to PRs, issues, docs
- **Represent the project** — we're community members helping, not authorities
- **No performative enthusiasm** — state facts, provide links
- **Respect existing answers** — if someone already answered well, skip or upvote
- **One discussion at a time** — never batch-post responses

## Comment Etiquette

- Read the full thread before drafting — don't repeat what others said
- If the discussion author already found a workaround, acknowledge it
- Never promise features or timelines
- If unsure, skip — a wrong answer is worse than no answer
- Always defer to the maintainer's existing responses — if they already answered well, skip
- For Q&A category: only the discussion author or repo maintainers can mark a comment
  as "the answer." We cannot do this ourselves (requires write permissions). If a
  maintainer has already given a correct response that isn't marked as answered, that's
  their call to make — do not nag about it

## Session Flow

A typical session looks like:

1. Invoke this skill
2. Fetch discussions + read logs
3. Filter to unhandled discussions
4. For each (oldest first):
   a. Read full discussion + comments
   b. Cross-reference against triage log and codebase
   c. Present to user with draft
   d. User approves/edits/skips/defers
   e. Post if approved, log either way
5. Commit log updates
6. Report summary (responded: N, skipped: N, deferred: N)
