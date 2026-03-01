# TOOLSETS Passthrough Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace MCPB hardcoded tool lists with upstream TOOLSETS passthrough and add ALLOW_DELETE_TOOLS safety mechanism.

**Architecture:** All tool filtering moves into the Python server. The MCPB wrapper becomes a thin Docker launcher that relays env vars. Three knobs: TOOLSETS, READ_ONLY_MODE, ALLOW_DELETE_TOOLS.

**Tech Stack:** Python 3.10+ (server), Node.js (MCPB wrapper), pytest, node:test

---

### Task 1: Add "delete" tag to destructive tools

**Files:**
- Modify: `src/mcp_atlassian/servers/jira.py:1569`
- Modify: `src/mcp_atlassian/servers/confluence.py:920`
- Modify: `src/mcp_atlassian/servers/confluence.py:1816`

**Step 1: Add "delete" tag to jira_delete_issue**

In `src/mcp_atlassian/servers/jira.py:1569`, change:
```python
tags={"jira", "write", "toolset:jira_issues"},
```
to:
```python
tags={"jira", "write", "delete", "toolset:jira_issues"},
```

**Step 2: Add "delete" tag to confluence delete_page**

In `src/mcp_atlassian/servers/confluence.py:920`, change:
```python
tags={"confluence", "write", "toolset:confluence_pages"},
```
to:
```python
tags={"confluence", "write", "delete", "toolset:confluence_pages"},
```

**Step 3: Add "delete" tag to confluence delete_attachment**

In `src/mcp_atlassian/servers/confluence.py:1816`, change:
```python
tags={"confluence", "write", "attachments", "toolset:confluence_attachments"},
```
to:
```python
tags={"confluence", "write", "delete", "attachments", "toolset:confluence_attachments"},
```

**Step 4: Run existing tests to verify no regressions**

Run: `uv run pytest tests/unit/utils/test_toolsets.py -xvs`
Expected: All pass (tag additions don't break existing toolset filtering)

**Step 5: Commit**

```bash
git add src/mcp_atlassian/servers/jira.py src/mcp_atlassian/servers/confluence.py
git commit -m "feat(server): add 'delete' tag to destructive tools

Tag jira_delete_issue, confluence_delete_page, and
confluence_delete_attachment with 'delete' for filtering.

Github-Issue:#25"
```

---

### Task 2: Add is_delete_tools_allowed() helper

**Files:**
- Modify: `src/mcp_atlassian/utils/io.py`
- Test: `tests/unit/utils/test_io.py` (or create if needed)

**Step 1: Write the failing test**

Find or create `tests/unit/utils/test_io.py`. Add:

```python
"""Tests for I/O utility functions."""

import pytest

from mcp_atlassian.utils.io import is_delete_tools_allowed


class TestIsDeleteToolsAllowed:
    """Tests for is_delete_tools_allowed() env var."""

    def test_default_is_false(self, monkeypatch):
        monkeypatch.delenv("ALLOW_DELETE_TOOLS", raising=False)
        assert is_delete_tools_allowed() is False

    def test_explicit_false(self, monkeypatch):
        monkeypatch.setenv("ALLOW_DELETE_TOOLS", "false")
        assert is_delete_tools_allowed() is False

    def test_explicit_true(self, monkeypatch):
        monkeypatch.setenv("ALLOW_DELETE_TOOLS", "true")
        assert is_delete_tools_allowed() is True

    def test_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("ALLOW_DELETE_TOOLS", "TRUE")
        assert is_delete_tools_allowed() is True

    def test_yes_is_truthy(self, monkeypatch):
        monkeypatch.setenv("ALLOW_DELETE_TOOLS", "yes")
        assert is_delete_tools_allowed() is True
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/utils/test_io.py::TestIsDeleteToolsAllowed -xvs`
Expected: ImportError — `is_delete_tools_allowed` doesn't exist yet

**Step 3: Implement is_delete_tools_allowed()**

Add to `src/mcp_atlassian/utils/io.py` after `is_read_only_mode()`:

```python
def is_delete_tools_allowed() -> bool:
    """Check if delete tools are allowed.

    When disabled (default), tools tagged with 'delete' are filtered out
    even when read-only mode is off. This provides defense-in-depth
    against accidental destructive operations.

    Returns:
        True if delete tools are allowed, False otherwise
    """
    return is_env_extended_truthy("ALLOW_DELETE_TOOLS", "false")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/utils/test_io.py::TestIsDeleteToolsAllowed -xvs`
Expected: All 5 pass

**Step 5: Commit**

```bash
git add src/mcp_atlassian/utils/io.py tests/unit/utils/test_io.py
git commit -m "feat(server): add ALLOW_DELETE_TOOLS env var support

New is_delete_tools_allowed() helper defaults to false,
blocking delete-tagged tools unless explicitly enabled.

Github-Issue:#25"
```

---

### Task 3: Wire ALLOW_DELETE_TOOLS into server filtering

**Files:**
- Modify: `src/mcp_atlassian/servers/context.py:11-23`
- Modify: `src/mcp_atlassian/servers/main.py:120-170` (lifespan)
- Modify: `src/mcp_atlassian/servers/main.py:275-280` (filtering loop)

**Step 1: Add allow_delete to MainAppContext**

In `src/mcp_atlassian/servers/context.py`, add field after `read_only`:

```python
@dataclass(frozen=True)
class MainAppContext:
    """..."""
    full_jira_config: JiraConfig | None = None
    full_confluence_config: ConfluenceConfig | None = None
    read_only: bool = False
    allow_delete: bool = False
    enabled_tools: list[str] | None = None
    enabled_toolsets: set[str] | None = None
```

**Step 2: Import and call in lifespan**

In `src/mcp_atlassian/servers/main.py`, add import:
```python
from mcp_atlassian.utils.io import is_delete_tools_allowed, is_read_only_mode
```
(Update the existing `from mcp_atlassian.utils.io import is_read_only_mode` line)

In `main_lifespan()`, after `read_only = is_read_only_mode()` (line 124), add:
```python
allow_delete = is_delete_tools_allowed()
```

In the `MainAppContext(...)` constructor (line 161), add:
```python
allow_delete=allow_delete,
```

After the read-only log line (line 168), add:
```python
logger.info(f"Delete tools: {'ALLOWED' if allow_delete else 'BLOCKED'}")
```

**Step 3: Add filtering in _list_tools_mcp()**

In `_list_tools_mcp()`, after reading `read_only` from context (~line 226-230), add:
```python
allow_delete = (
    getattr(app_lifespan_state, "allow_delete", False)
    if app_lifespan_state
    else False
)
```

After the read-only filter block (after line 279), add:
```python
if not allow_delete and "delete" in tool_tags:
    logger.debug(
        f"Excluding tool '{registered_name}' due to delete tools being blocked"
    )
    continue
```

**Step 4: Run full test suite**

Run: `uv run pytest tests/unit/ -x`
Expected: All pass

**Step 5: Commit**

```bash
git add src/mcp_atlassian/servers/context.py src/mcp_atlassian/servers/main.py
git commit -m "feat(server): wire ALLOW_DELETE_TOOLS into filtering pipeline

Delete-tagged tools are now filtered in _list_tools_mcp() when
ALLOW_DELETE_TOOLS is not set to true (default: blocked).

Github-Issue:#25"
```

---

### Task 4: Add delete filtering tests

**Files:**
- Modify: `tests/unit/utils/test_toolsets.py`

**Step 1: Add test for delete tag presence**

Add to `TestToolsetTagCompleteness` class:

```python
def test_delete_tools_have_delete_tag(self, jira_tools, confluence_tools):
    """Verify delete tools are tagged with 'delete'."""
    all_tools = {**jira_tools, **confluence_tools}
    expected_delete_tools = {
        "delete_issue",
        "delete_page",
        "delete_attachment",
    }
    for name, tool in all_tools.items():
        tags = tool.tags if hasattr(tool, "tags") else set()
        if name in expected_delete_tools:
            assert "delete" in tags, (
                f"Tool '{name}' must have 'delete' tag for safety filtering"
            )
        else:
            assert "delete" not in tags, (
                f"Tool '{name}' has 'delete' tag but is not a delete operation"
            )
```

**Step 2: Run test**

Run: `uv run pytest tests/unit/utils/test_toolsets.py::TestToolsetTagCompleteness::test_delete_tools_have_delete_tag -xvs`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/unit/utils/test_toolsets.py
git commit -m "test(server): add delete tag verification tests

Ensures exactly the 3 delete tools have the 'delete' tag.

Github-Issue:#25"
```

---

### Task 5: Update MCPB server/index.js

**Files:**
- Modify: `docs/mcpb-extension/server/index.js`

**Step 1: Replace env var reading (lines 83-89)**

Replace:
```javascript
const ATLASSIAN_URL = process.env.ATLASSIAN_URL || "";
const ATLASSIAN_EMAIL = process.env.ATLASSIAN_EMAIL || "";
const ATLASSIAN_API_TOKEN = process.env.ATLASSIAN_API_TOKEN || "";
const ENABLE_WRITE = (process.env.ENABLE_WRITE_TOOLS || "false").toLowerCase() === "true";
const CONFLUENCE_SPACES_FILTER = process.env.CONFLUENCE_SPACES_FILTER || "";
const JIRA_PROJECTS_FILTER = process.env.JIRA_PROJECTS_FILTER || "";
```

With:
```javascript
const ATLASSIAN_URL = process.env.ATLASSIAN_URL || "";
const ATLASSIAN_EMAIL = process.env.ATLASSIAN_EMAIL || "";
const ATLASSIAN_API_TOKEN = process.env.ATLASSIAN_API_TOKEN || "";
const TOOLSETS = process.env.TOOLSETS || "default";
const READ_ONLY_MODE = process.env.READ_ONLY_MODE || "true";
const ALLOW_DELETE_TOOLS = process.env.ALLOW_DELETE_TOOLS || "false";
const CONFLUENCE_SPACES_FILTER = process.env.CONFLUENCE_SPACES_FILTER || "";
const JIRA_PROJECTS_FILTER = process.env.JIRA_PROJECTS_FILTER || "";
```

**Step 2: Remove tool arrays and enabledTools (lines 324-370)**

Delete from `// --- Build the tool allowlist ---` through the `enabledTools` construction:
```javascript
// --- Build the tool allowlist ---
// Read-only tools (always enabled)
const READ_TOOLS = [
  ...all 21 entries...
];

// Write tools (only if explicitly enabled — never includes delete operations)
const WRITE_TOOLS = [
  ...all 11 entries...
];

// NEVER exposed, regardless of config:
// jira_delete_issue, confluence_delete_page, jira_batch_create_issues

const enabledTools = ENABLE_WRITE
  ? [...READ_TOOLS, ...WRITE_TOOLS]
  : READ_TOOLS;
```

**Step 3: Replace ENABLED_TOOLS env var in Docker args (line 434)**

Replace:
```javascript
"-e", `ENABLED_TOOLS=${enabledTools.join(",")}`,
```

With:
```javascript
// Tool filtering (Python server handles all logic)
"-e", `TOOLSETS=${TOOLSETS}`,
"-e", `READ_ONLY_MODE=${READ_ONLY_MODE}`,
"-e", `ALLOW_DELETE_TOOLS=${ALLOW_DELETE_TOOLS}`,
```

**Step 4: Add startup log for new config**

After the config validation block (~line 98), add:
```javascript
log(`Config: TOOLSETS=${TOOLSETS}, READ_ONLY_MODE=${READ_ONLY_MODE}, ALLOW_DELETE_TOOLS=${ALLOW_DELETE_TOOLS}`);
```

**Step 5: Commit**

```bash
git add docs/mcpb-extension/server/index.js
git commit -m "refactor(mcpb): replace tool lists with TOOLSETS passthrough

Remove READ_TOOLS/WRITE_TOOLS arrays and ENABLED_TOOLS env var.
Pass TOOLSETS, READ_ONLY_MODE, ALLOW_DELETE_TOOLS to Docker instead.
Python server handles all tool filtering logic.

Github-Issue:#25"
```

---

### Task 6: Update manifest.json

**Files:**
- Modify: `docs/mcpb-extension/manifest.json`

**Step 1: Remove static tools array (lines 29-52)**

Delete the entire `"tools": [...]` array.

**Step 2: Replace user_config**

Replace `enable_write_tools` field with three new fields. Keep existing fields. Full user_config:

```json
"user_config": {
    "atlassian_url": {
      "type": "string",
      "title": "Atlassian Site URL",
      "description": "Your Atlassian Cloud URL, e.g. https://eruditis.atlassian.net (no trailing slash)",
      "required": true,
      "default": "https://eruditis.atlassian.net"
    },
    "atlassian_email": {
      "type": "string",
      "title": "Atlassian Email",
      "description": "The email address you use to log into Atlassian (your Gmail)",
      "required": true
    },
    "atlassian_api_token": {
      "type": "string",
      "title": "Atlassian API Token",
      "description": "Generate at https://id.atlassian.com/manage-profile/security/api-tokens",
      "sensitive": true,
      "required": true
    },
    "toolsets": {
      "type": "string",
      "title": "Enabled Toolsets",
      "description": "Comma-separated toolset names. Use 'default' for core tools, 'all' for everything. Available: confluence_pages, confluence_comments, confluence_labels, confluence_users, confluence_analytics, confluence_attachments, jira_issues, jira_fields, jira_comments, jira_transitions, jira_projects, jira_agile, jira_links, jira_worklog, jira_attachments, jira_users, jira_watchers, jira_service_desk, jira_forms, jira_metrics, jira_development",
      "required": false,
      "default": "default"
    },
    "read_only_mode": {
      "type": "string",
      "title": "Read-Only Mode",
      "description": "Set to 'false' to enable write operations (create, update). Default is read-only.",
      "required": false,
      "default": "true"
    },
    "allow_delete_tools": {
      "type": "string",
      "title": "Allow Delete Operations",
      "description": "Set to 'true' to allow delete operations. Requires read_only_mode=false. Default blocks all deletes.",
      "required": false,
      "default": "false"
    },
    "confluence_spaces_filter": {
      "type": "string",
      "title": "Confluence Spaces Filter",
      "description": "Comma-separated space keys to restrict access (e.g. 'DEV,TEAM,DOC'). Leave empty for all spaces.",
      "required": false,
      "default": ""
    },
    "jira_projects_filter": {
      "type": "string",
      "title": "Jira Projects Filter",
      "description": "Comma-separated project keys to restrict access (e.g. 'PROJ,DEV'). Leave empty for all projects.",
      "required": false,
      "default": ""
    }
  }
```

**Step 3: Update mcp_config.env**

Replace the env block:
```json
"env": {
    "ATLASSIAN_URL": "${user_config.atlassian_url}",
    "ATLASSIAN_EMAIL": "${user_config.atlassian_email}",
    "ATLASSIAN_API_TOKEN": "${user_config.atlassian_api_token}",
    "TOOLSETS": "${user_config.toolsets}",
    "READ_ONLY_MODE": "${user_config.read_only_mode}",
    "ALLOW_DELETE_TOOLS": "${user_config.allow_delete_tools}",
    "CONFLUENCE_SPACES_FILTER": "${user_config.confluence_spaces_filter}",
    "JIRA_PROJECTS_FILTER": "${user_config.jira_projects_filter}"
}
```

**Step 4: Bump version**

Change `"version": "1.0.18"` to `"version": "1.1.0"` (minor bump for new config schema).

**Step 5: Update long_description**

Replace:
```
"By default, only read operations and page create/update are enabled. Destructive operations (delete) are never exposed."
```
With:
```
"Read-only by default. Tool availability controlled via TOOLSETS. Delete operations blocked unless explicitly allowed."
```

**Step 6: Commit**

```bash
git add docs/mcpb-extension/manifest.json
git commit -m "refactor(mcpb): update manifest with TOOLSETS config schema

Replace enable_write_tools with toolsets, read_only_mode, and
allow_delete_tools. Remove static tools array. Bump to v1.1.0.

Github-Issue:#25"
```

---

### Task 7: Update MCPB static tests

**Files:**
- Modify: `docs/mcpb-extension/tests/static.test.js`

**Step 1: Remove tests that reference READ_TOOLS/WRITE_TOOLS**

Delete these tests from the `server/index.js` describe block:
- `"never exposes delete operations in tool arrays"` (lines 246-262)
- `"defaults write tools to disabled"` (lines 264-270)
- `"never exposes delete operations in ENABLED_TOOLS whitelist"` (lines 415-480)
- `"ENABLED_TOOLS whitelist includes all manifest.json tools"` (lines 482-513)

Delete these tests from the `manifest.json` describe block:
- `"defaults write tools to false"` (lines 530-535)
- `"all manifest tools appear in server/index.js ENABLED_TOOLS whitelist"` (lines 553-583)

**Step 2: Add new tests for env var passthrough**

Add to the `server/index.js` describe block:

```javascript
it("passes TOOLSETS env var to Docker (not ENABLED_TOOLS)", () => {
    assert.match(
      serverJs,
      /TOOLSETS/,
      "Must pass TOOLSETS env var to Docker"
    );
    assert.doesNotMatch(
      serverJs,
      /ENABLED_TOOLS/,
      "Must NOT use legacy ENABLED_TOOLS env var"
    );
  });

  it("passes READ_ONLY_MODE env var to Docker", () => {
    assert.match(
      serverJs,
      /READ_ONLY_MODE/,
      "Must pass READ_ONLY_MODE env var to Docker"
    );
  });

  it("passes ALLOW_DELETE_TOOLS env var to Docker", () => {
    assert.match(
      serverJs,
      /ALLOW_DELETE_TOOLS/,
      "Must pass ALLOW_DELETE_TOOLS env var to Docker"
    );
  });

  it("defaults READ_ONLY_MODE to true", () => {
    assert.match(
      serverJs,
      /READ_ONLY_MODE.*\|\|.*["']true["']/,
      "READ_ONLY_MODE must default to 'true'"
    );
  });

  it("defaults ALLOW_DELETE_TOOLS to false", () => {
    assert.match(
      serverJs,
      /ALLOW_DELETE_TOOLS.*\|\|.*["']false["']/,
      "ALLOW_DELETE_TOOLS must default to 'false'"
    );
  });

  it("does not have hardcoded tool arrays", () => {
    assert.doesNotMatch(
      serverJs,
      /const READ_TOOLS/,
      "Must NOT have hardcoded READ_TOOLS array"
    );
    assert.doesNotMatch(
      serverJs,
      /const WRITE_TOOLS/,
      "Must NOT have hardcoded WRITE_TOOLS array"
    );
  });
```

Add to the `manifest.json` describe block:

```javascript
it("has toolsets config with default value", () => {
    assert.equal(
      manifest.user_config?.toolsets?.default,
      "default",
      "toolsets must default to 'default'"
    );
  });

  it("has read_only_mode config defaulting to true", () => {
    assert.equal(
      manifest.user_config?.read_only_mode?.default,
      "true",
      "read_only_mode must default to 'true'"
    );
  });

  it("has allow_delete_tools config defaulting to false", () => {
    assert.equal(
      manifest.user_config?.allow_delete_tools?.default,
      "false",
      "allow_delete_tools must default to 'false'"
    );
  });

  it("does not have static tools array", () => {
    assert.ok(
      !manifest.tools,
      "manifest.json must not have static tools array (tools discovered dynamically)"
    );
  });
```

**Step 3: Run tests**

Run: `node --test docs/mcpb-extension/tests/static.test.js`
Expected: All pass

**Step 4: Commit**

```bash
git add docs/mcpb-extension/tests/static.test.js
git commit -m "test(mcpb): update tests for TOOLSETS passthrough

Replace READ_TOOLS/WRITE_TOOLS validation with TOOLSETS,
READ_ONLY_MODE, and ALLOW_DELETE_TOOLS passthrough tests.

Github-Issue:#25"
```

---

### Task 8: Update MCPB documentation

**Files:**
- Modify: `docs/mcpb-extension/BUILD_NOTES.md`
- Modify: `docs/mcpb-extension/README.md`

**Step 1: Update BUILD_NOTES.md**

Remove the entire "Adding New MCP Tools - Critical Checklist" section (lines 413-501). Replace with:

```markdown
## Tool Management

Tools are managed entirely by the upstream Python server's toolset system. The MCPB extension passes `TOOLSETS`, `READ_ONLY_MODE`, and `ALLOW_DELETE_TOOLS` env vars to Docker. No tool lists to maintain.

See `src/mcp_atlassian/utils/toolsets.py` for toolset definitions.
```

Update "Access Control" in Security Posture (line 337-341). Replace:
```markdown
- **Read-only by default**: Write tools require explicit opt-in
- **Tool allowlist**: Only curated operations are exposed
- **Delete operations never exposed**: `jira_delete_issue`, `confluence_delete_page` are hardcoded to be disabled
```
With:
```markdown
- **Read-only by default**: `READ_ONLY_MODE=true` blocks all writes
- **Delete blocked by default**: `ALLOW_DELETE_TOOLS=false` blocks deletes even when writes enabled
- **Toolset filtering**: `TOOLSETS=default` exposes only 6 core toolsets (of 21 available)
```

Update Security Checklist items (lines 367-370). Replace:
```markdown
- [ ] Delete operations not in tool arrays
- [ ] `atlassian_api_token` has `"sensitive": true` in manifest
- [ ] `enable_write_tools` defaults to `"false"`
```
With:
```markdown
- [ ] `atlassian_api_token` has `"sensitive": true` in manifest
- [ ] `READ_ONLY_MODE` defaults to `"true"`
- [ ] `ALLOW_DELETE_TOOLS` defaults to `"false"`
- [ ] No hardcoded tool arrays in server/index.js
```

**Step 2: Update README.md**

Replace "Configuration Options > Enable Write Operations" section (lines 72-80) with:

```markdown
### Toolsets

Control which categories of tools are available:

- **Default** (`default`): Core tools — issues, fields, comments, transitions, pages, page comments
- **All** (`all`): All 72 tools across 21 toolsets
- **Custom**: Comma-separated list, e.g. `default,jira_agile,jira_projects`

### Enable Write Operations

By default, the extension is read-only. To enable create/update operations:

1. Go to extension settings in Claude Desktop
2. Set "Read-Only Mode" to `false`
3. Restart Claude Desktop

### Allow Delete Operations

Delete operations are blocked by default, even when writes are enabled. To allow deletes:

1. Set "Read-Only Mode" to `false`
2. Set "Allow Delete Operations" to `true`
3. Restart Claude Desktop
```

Update "Curated tool list" in Features (line 10). Replace:
```markdown
- **Curated tool list**: Only safe operations are exposed (no delete operations)
```
With:
```markdown
- **Configurable toolsets**: Control which tool categories are available via TOOLSETS
- **Delete protection**: Delete operations blocked by default, even when writes are enabled
```

**Step 3: Commit**

```bash
git add docs/mcpb-extension/BUILD_NOTES.md docs/mcpb-extension/README.md
git commit -m "docs(mcpb): update docs for TOOLSETS passthrough

Remove 'Adding New Tools' checklist (no longer needed).
Document TOOLSETS, READ_ONLY_MODE, and ALLOW_DELETE_TOOLS config.

Github-Issue:#25"
```

---

### Task 9: Final verification and lint

**Step 1: Run Python linting**

```bash
uv run ruff format .
uv run ruff check --fix .
```

**Step 2: Run Python tests**

```bash
uv run pytest tests/unit/ -x
```

**Step 3: Run MCPB static tests**

```bash
node --test docs/mcpb-extension/tests/static.test.js
```

**Step 4: Run pre-commit**

```bash
uv run pre-commit run --all-files
```

**Step 5: Fix any issues, then final commit if needed**

---

### Task 10: Create feature branch and PR

**Step 1: Ensure all changes are on feature branch**

If not already on a feature branch:
```bash
git checkout -b feature/toolsets-passthrough eruditis/main
```

**Step 2: Push and create PR**

```bash
git push -u origin feature/toolsets-passthrough
gh pr create \
  --repo Troubladore/mcp-atlassian \
  --base eruditis/main \
  --head feature/toolsets-passthrough \
  --title "refactor: replace MCPB tool lists with TOOLSETS passthrough" \
  --body "$(cat <<'EOF'
## Summary
- Remove hardcoded READ_TOOLS/WRITE_TOOLS from MCPB server/index.js
- Pass TOOLSETS, READ_ONLY_MODE, ALLOW_DELETE_TOOLS env vars to Docker
- Add ALLOW_DELETE_TOOLS support to Python server (delete tag + filter)
- Update manifest.json with new user_config schema
- Update tests and documentation

Closes #25

## Test plan
- [x] Python unit tests pass (pytest tests/unit/ -x)
- [x] MCPB static tests pass (node --test tests/static.test.js)
- [x] Pre-commit hooks pass (ruff, mypy)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
