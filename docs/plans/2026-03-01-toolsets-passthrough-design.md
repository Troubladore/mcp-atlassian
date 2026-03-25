# Design: Replace MCPB Manual Tool Lists with TOOLSETS Passthrough

**Issue**: #25
**Date**: 2026-03-01
**Approach**: Full Passthrough (Approach A)

## Problem

The MCPB extension maintains hardcoded `READ_TOOLS`/`WRITE_TOOLS` arrays in `server/index.js` that duplicate and diverge from the upstream toolset system. The MCPB lists cover 32 tools while the Python server has 72 tools across 21 toolsets. Every new upstream tool requires manual updates to two places.

## Design

### 1. Python Server: Add ALLOW_DELETE_TOOLS

Add a `"delete"` tag to 3 destructive tools:
- `jira_delete_issue` (in `jira_issues` toolset)
- `confluence_delete_page` (in `confluence_pages` toolset)
- `confluence_delete_attachment` (in `confluence_attachments` toolset)

Add `ALLOW_DELETE_TOOLS` env var (default `false`):
- New helper `is_delete_tools_allowed()` in `utils/env.py`
- Filter in `_list_tools_mcp()`: if `not allow_delete` and `"delete" in tool_tags` → skip
- Store in `MainAppContext` alongside `read_only`
- Log at startup

Filtering precedence (checked in order):
1. Toolset enabled? (`TOOLSETS`)
2. Read-only mode? (`READ_ONLY_MODE`) — blocks all `"write"` tagged tools
3. Delete allowed? (`ALLOW_DELETE_TOOLS`) — blocks `"delete"` tagged tools
4. Service configured? (Jira/Confluence credentials present)

### 2. MCPB server/index.js: Remove Tool Lists, Relay Env Vars

Remove:
- `READ_TOOLS` array (lines 326-348)
- `WRITE_TOOLS` array (lines 351-363)
- `enabledTools` construction logic
- `ENABLED_TOOLS` env var passed to Docker

Replace with env-var passthrough:
```javascript
const TOOLSETS = process.env.TOOLSETS || "default";
const READ_ONLY_MODE = process.env.READ_ONLY_MODE || "true";
const ALLOW_DELETE_TOOLS = process.env.ALLOW_DELETE_TOOLS || "false";
```

Passed to `docker run` as `-e TOOLSETS=...`, `-e READ_ONLY_MODE=...`, `-e ALLOW_DELETE_TOOLS=...`.

### 3. manifest.json: New user_config, Remove Static Tools

Replace `enable_write_tools` with:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `toolsets` | string | `"default"` | Comma-separated toolset names. Keywords: `default`, `all` |
| `read_only_mode` | string | `"true"` | Set to `false` to enable write operations |
| `allow_delete_tools` | string | `"false"` | Set to `true` to allow delete operations (requires read_only_mode=false) |

Remove static `tools` array (lines 29-52) — tools discovered dynamically via MCP.

Update `mcp_config.env` to map new fields to env vars.

### 4. Documentation

- **BUILD_NOTES.md**: Remove "Adding New Tools" checklist, update architecture
- **README.md**: Replace `enable_write_tools` refs with new config, add toolsets examples
- **MCPB tests**: Remove READ_TOOLS/WRITE_TOOLS validation, add env-var passthrough tests
- **Python tests**: Add ALLOW_DELETE_TOOLS unit tests in `test_toolsets.py`
- Bump manifest.json version (minor)

## Safety Model

Default configuration is maximally safe:
- `READ_ONLY_MODE=true` — all writes blocked
- `ALLOW_DELETE_TOOLS=false` — deletes blocked even if writes enabled
- `TOOLSETS=default` — only core toolsets (6 of 21)

To enable writes: set `read_only_mode=false`.
To enable deletes: set both `read_only_mode=false` AND `allow_delete_tools=true`.
