# FastMCP 3.x Security Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Port `mcp-atlassian` from FastMCP 2.14.5 to FastMCP ≥ 3.2.0 to remediate three Dependabot CVEs, with minimal behavior drift.

**Architecture:** Thin mechanical port. Preserve all subclass overrides (`AtlassianMCP`, `HardenedOAuthProxy`, `AtlassianOpaqueTokenVerifier`). Update import paths, method signatures, and iteration patterns for 3.x API. Refactor to native 3.x extension surfaces is explicitly deferred to Troubladore/mcp-atlassian#326.

**Tech Stack:** Python ≥ 3.10, FastMCP, pytest, mypy (strict), Ruff, uv.

**Design doc:** `docs/plans/2026-04-18-fastmcp-3x-migration-design.md`
**Tracking:** #320 (local), sooperset/mcp-atlassian#1234 (upstream)
**Branch:** `fix/fastmcp-3x-cve` off `community/main`

---

## Non-negotiables (preserve bit-for-bit)

1. Tool visibility rules: toolset filter, `enabled_tools` allowlist, read-only `write` suppression, per-service availability gating, schema sanitization
2. HTTP middleware semantics: `UserTokenMiddleware` auth extraction, SSRF validation, `request.state` population, 401 rejection, disconnect tolerance
3. Auth policy: `HardenedOAuthProxy` DCR constraints, `require_authorization_consent=True`
4. No silent env-autoload regression

## Phase ordering rationale

Spikes first so the subsequent port has concrete answers, not guesses. Safety-net tests next so we can detect behavior drift. Dependency bump is the trigger that breaks the build in a known way. Mechanical port fixes each failure. Validation confirms no drift. Release prep closes the loop.

---

### Task 1: Spike — FastMCP 3.2.0 auth module layout

**Goal:** Answer open spike #1 from design doc. We need concrete new import paths and API shapes before porting.

**Step 1: Install FastMCP 3.2.0 into an isolated throwaway env to inspect**

Run:
```bash
mkdir -p /tmp/fastmcp3-spike && cd /tmp/fastmcp3-spike
uv venv .venv
uv pip install --python .venv/bin/python 'fastmcp>=3.2.0,<4.0.0'
```

Expected: `fastmcp==3.2.x` installed.

**Step 2: Read source to answer specific questions**

Use a research agent (Explore/general-purpose) to read the installed FastMCP 3.x source at `/tmp/fastmcp3-spike/.venv/lib/python*/site-packages/fastmcp/` and report:

- New import path for `OAuthProxy` (2.x: `fastmcp.server.auth.oauth_proxy.OAuthProxy`)
- New import path for `TokenVerifier`, `AccessToken` (2.x: `fastmcp.server.auth.auth`)
- New import path for `get_access_token`, `get_http_request` (2.x: `fastmcp.server.dependencies`)
- New import path for `StarletteWithLifespan` (2.x: `fastmcp.server.http`)
- New import path for `EventStore` (2.x: `fastmcp.server.event_store`)
- New import path for `Tool` (2.x: `fastmcp.tools`)
- New import path for `ToolError` (2.x: `fastmcp.exceptions`)
- `AccessToken` constructor signature — does it still accept `token=`, `client_id=`, `scopes=`, `expires_at=`?
- `TokenVerifier.required_scopes` — still present as attribute?
- `OAuthProxy.register_client()` signature — same or different?
- `OAuthClientInformationFull` — still importable and same field names?
- `http_app()` parameter list — which of `transport`, `middleware`, `event_store`, `stateless_http`, `json_response`, `retry_interval` remain vs. moved to `run_http_async()`?
- `mount()` signature — does it accept `namespace=` kwarg or is the argument named differently?
- `list_tools()` return type — `list[Tool]` or something else?
- `fastmcp.settings` structure — does `streamable_http_path` exist, and where?
- Python version requirement (`python_requires` in `pyproject.toml` / `setup.py`)

**Step 3: Record findings**

Append findings to `docs/plans/2026-04-18-fastmcp-3x-migration-design.md` under a new "## Spike findings" section. Use a table: `Symbol | 2.x path | 3.x path | Notes`. This doc is gitignored so findings stay local.

**Step 4: Decide on kill-criteria triggers**

If any of these are true, stop and escalate — the plan needs revision:
- `OAuthProxy` no longer subclassable in a form that preserves `register_client()` hardening
- `TokenVerifier` abstract contract incompatible with our override
- No way to inject `UserTokenMiddleware` that preserves request lifecycle semantics

**Step 5: Commit nothing (spike produces knowledge, not code)**

No git commit for this task.

---

### Task 2: Spike — FastMCP 3.x OAuth storage behavior

**Goal:** Answer open spike #2. Determine what happens to existing DiskStore data under 3.x defaults.

**Step 1: Dispatch research agent**

Use a general-purpose agent to investigate what FastMCP 3.2.0 does when `client_storage=None` is passed to `OAuthProxy`:
- Does it instantiate `FileTreeStore` by default? (per changelog)
- What filesystem path does `FileTreeStore` use?
- Does FastMCP 3.x read old `DiskStore` data for backward compatibility, or is it a clean break?
- What error (if any) occurs when old DiskStore files are present?

Approach: read FastMCP 3.x source at `/tmp/fastmcp3-spike/.venv/lib/python*/site-packages/fastmcp/server/auth/` for storage backends. Trace `OAuthProxy.__init__` when `client_storage` is None.

**Step 2: Record findings**

Append to design doc's "Spike findings" section with a clear statement: *"Under 3.x defaults, existing DiskStore data is [ignored/migrated/causes error X]. Users in default storage mode [must re-authenticate / continue transparently / see error Y]."*

**Step 3: Update release notes outline in design doc**

If findings confirm re-auth is required, sharpen the release note wording from "may need to re-authenticate" to concrete language.

**Step 4: Commit nothing**

---

### Task 3: Spike — HTTP middleware pipeline and `request.state`

**Goal:** Answer open spike #3. Verify `UserTokenMiddleware` can populate `request.state.atlassian_service_headers` the same way in 3.x.

**Step 1: Dispatch research agent**

Read FastMCP 3.2.0 source for:
- How middleware is registered on the HTTP app in 3.x (constructor kwarg, method call, config object?)
- Whether middleware runs inside the same Starlette/ASGI scope as 2.x (same `request.state` object)
- Whether 3.x introduced a new "middleware" abstraction that wraps Starlette middleware differently
- Any documented order of middleware execution that would change our positioning

**Step 2: Record findings**

Append to design doc. Concrete statement: *"In 3.x, Starlette middleware attaches via [method]. `request.state` semantics are [identical/different]. UserTokenMiddleware [requires no changes / requires change X] to preserve behavior."*

**Step 3: Commit nothing**

---

### Task 4: Spike — Python minimum version

**Goal:** Answer open spike #5.

**Step 1: Read FastMCP 3.2.0's declared Python requirement**

Run:
```bash
grep -E "requires-python|python_requires" /tmp/fastmcp3-spike/.venv/lib/python*/site-packages/fastmcp*/METADATA 2>&1 | head -5
```

Or read `/tmp/fastmcp3-spike/.venv/lib/python*/site-packages/fastmcp-*.dist-info/METADATA`.

**Step 2: Record finding**

Append to design doc. If FastMCP 3.x requires Python ≥ 3.11, our `pyproject.toml` `requires-python = ">=3.10"` must bump.

**Step 3: Commit nothing**

---

### Task 5: Verify existing test coverage for `_list_tools_mcp()` filter behaviors

**Files:**
- Read: `tests/unit/servers/test_mcp_protocol.py`
- Read: `src/mcp_atlassian/servers/main.py` (the `_list_tools_mcp()` method)

**Goal:** Confirm behavioral tests exist (or identify gaps to fill) for each filter condition: read-only mode, `enabled_tools` allowlist, toolset allowlist, per-service availability (from startup config and from per-request headers), schema sanitization.

**Step 1: Read `_list_tools_mcp()` source**

Run: `grep -n "_list_tools_mcp\|_sanitize_schema_for_compatibility" src/mcp_atlassian/servers/main.py` — note method line numbers.

**Step 2: Read the test file**

Run: `cat tests/unit/servers/test_mcp_protocol.py | wc -l` and open it. Catalog which test functions cover which filter conditions.

**Step 3: Produce coverage matrix**

Write down (in your head or scratch) a matrix like:
```
Condition                           | Test function(s) covering it
----------------------------------- | ---------------------------
Read-only mode suppresses write     | test_...
enabled_tools allowlist             | test_... or MISSING
toolset allowlist                   | test_...
Startup-time service unavailability | test_... or MISSING
Per-request service unavailability  | test_... or MISSING
Schema sanitization                 | test_... in test_schema_compatibility.py
```

**Step 4: For each MISSING row, open a micro-task**

If any row is MISSING, the next task (Task 6) will add that specific test first. If all rows are covered, skip Task 6 and proceed.

**Step 5: Commit nothing (this is audit, not code)**

---

### Task 6: Fill any test gaps identified in Task 5

**Scope:** Only execute this task if Task 5 found MISSING coverage. One sub-task per missing behavioral test.

For each missing behavior:

**Step A: Write failing test that asserts the current behavior**

Write the test that exercises the filter condition end-to-end (construct context, call `_list_tools_mcp()`, assert filtered result). The test should PASS on current FastMCP 2.14.5 code. If it fails, we have already identified a bug — stop and fix.

**Step B: Run the test, confirm it passes**

Run: `uv run pytest tests/unit/servers/test_mcp_protocol.py::<new_test_name> -xvs -W error`
Expected: PASS.

**Step C: Commit**

```bash
git add tests/unit/servers/test_mcp_protocol.py
git commit -m "test(server): add regression test for <specific filter behavior>"
```

---

### Task 7: Verify existing test coverage for `HardenedOAuthProxy.register_client()`

**Files:**
- Read: `src/mcp_atlassian/servers/oauth_proxy.py`
- Find: tests covering `HardenedOAuthProxy`

**Step 1: Locate tests**

Run: `grep -rln "HardenedOAuthProxy\|register_client" tests/ src/mcp_atlassian/servers/oauth_proxy.py`

**Step 2: Confirm coverage for three behaviors**

- Forces `response_types=["code"]` regardless of input
- Filters requested `grant_types` against configured allowlist
- Forces scope to configured `forced_scopes` value

If any gap, write a failing test that asserts the behavior on current 2.x code (should PASS on 2.x — we are capturing the behavior, not fixing a bug).

**Step 3: Run and commit any new test**

```bash
uv run pytest tests/path -xvs -W error
git add tests/path
git commit -m "test(auth): add regression test for HardenedOAuthProxy <behavior>"
```

---

### Task 8: Verify existing test coverage for `AtlassianOpaqueTokenVerifier`

**Files:**
- Read: `tests/unit/utils/test_token_verifier.py`
- Read: `src/mcp_atlassian/utils/token_verifier.py`

**Step 1: Open both files and confirm coverage**

Confirm tests exist for:
- Empty token returns `None`
- Non-empty token returns `AccessToken` with `client_id="atlassian"`, `scopes=required_scopes`, 30-day expiry

**Step 2: Add any missing test, run, commit**

Follow the red/green/commit pattern from Task 6.

---

### Task 9: Verify existing test coverage for `UserTokenMiddleware` request.state population

**Files:**
- Search: `grep -rln "UserTokenMiddleware\|atlassian_service_headers" tests/`
- Read: `src/mcp_atlassian/servers/main.py` (UserTokenMiddleware class)

**Step 1: Confirm coverage for:**

- Auth header extraction populates `request.state.atlassian_service_headers` with expected shape
- SSRF validation rejects disallowed Jira/Confluence URL overrides
- Missing/invalid auth returns 401 with JSON body before app runs
- Client disconnect during response streaming is tolerated

**Step 2: Add any missing test, run, commit**

---

### Task 10: Verify existing test coverage for `build_oauth_client_storage_from_env()`

**Files:**
- Read: `tests/unit/servers/test_client_storage.py`
- Read: `src/mcp_atlassian/servers/client_storage.py`

**Step 1: Confirm coverage for three modes**

- Default/unset mode returns `None`
- Factory mode constructs custom backend
- Invalid config raises or logs

**Step 2: Add any missing test, run, commit**

---

### Task 11: Run full test suite on 2.x baseline

**Goal:** Establish a green baseline before any code change. Any failures here are pre-existing and must be resolved before proceeding.

**Step 1: Run tests**

```bash
uv run pytest -x -W error
```

Expected: all pass, no warnings.

**Step 2: Run lint and type check**

```bash
pre-commit run --all-files
uv run mypy src/
```

Expected: all pass.

**Step 3: If anything fails, STOP**

Do not proceed to the dependency bump. Fix pre-existing issues in separate commits on this branch (per project rule: "Fix pre-existing issues when touching a file").

---

### Task 12: Bump FastMCP constraint in `pyproject.toml`

**Files:**
- Modify: `pyproject.toml` (the `fastmcp` constraint line under `[project].dependencies`)

**Step 1: Edit the constraint**

Change:
```
"fastmcp>=2.13.0,<2.15.0",
```
to:
```
"fastmcp>=3.2.0,<4.0.0",
```

**Step 2: If Task 4 spike found Python ≥ 3.11 required, also bump `requires-python`**

Change `requires-python = ">=3.10"` to `requires-python = ">=3.11"`. Note: this is a user-facing compatibility break — add to release notes.

**Step 3: Re-lock dependencies**

```bash
uv sync --frozen=false --all-extras --dev
```

Expected: `uv.lock` updates; FastMCP resolves to 3.2.x.

**Step 4: Run tests to observe expected failures**

```bash
uv run pytest -x -W error 2>&1 | head -80
```

Expected: FAIL with `ImportError` or similar on the first file that imports from a moved `fastmcp.*` submodule. This is the baseline we will fix in subsequent tasks.

**Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore(deps): bump fastmcp to >=3.2.0,<4.0.0 (CVE remediation)"
```

---

### Task 13: Update import paths for auth subsystem

**Files:**
- Modify: `src/mcp_atlassian/servers/oauth_proxy.py`
- Modify: `src/mcp_atlassian/utils/token_verifier.py`
- Modify: `src/mcp_atlassian/servers/dependencies.py`
- Use: spike findings from Task 1 (new paths)

**Step 1: Update `oauth_proxy.py`**

Replace the `from fastmcp.server.auth.oauth_proxy import OAuthProxy` import with the 3.x path from Task 1. If 3.x also moved `OAuthClientInformationFull`, update that import too (it may now come from `fastmcp.mcp` or a new location).

**Step 2: Update `token_verifier.py`**

Replace `from fastmcp.server.auth.auth import AccessToken, TokenVerifier` with the 3.x paths.

**Step 3: Update `dependencies.py`**

Replace `from fastmcp.server.dependencies import get_access_token, get_http_request` with the 3.x paths (may be unchanged).

**Step 4: Run targeted tests**

```bash
uv run pytest tests/unit/utils/test_token_verifier.py tests/unit/servers/test_auto_oauth.py tests/unit/servers/test_dependencies.py -x -W error
```

Expected: PASS (or, if signatures changed, FAIL on a signature issue — that's the next task).

**Step 5: Commit**

```bash
git add src/mcp_atlassian/servers/oauth_proxy.py src/mcp_atlassian/utils/token_verifier.py src/mcp_atlassian/servers/dependencies.py
git commit -m "fix(auth): update fastmcp 3.x import paths for auth subsystem"
```

---

### Task 14: Update import paths in `servers/main.py`

**Files:**
- Modify: `src/mcp_atlassian/servers/main.py`

**Step 1: Update imports**

Replace the following imports with their 3.x equivalents (from Task 1 spike):
- `from fastmcp import FastMCP, Context`
- `from fastmcp import settings as fastmcp_settings`
- `from fastmcp.tools import Tool as FastMCPTool`
- `from fastmcp.server.event_store import EventStore`
- `from fastmcp.server.http import StarletteWithLifespan`

Most of these are likely unchanged, but the spike findings table is authoritative.

**Step 2: Run module import check**

```bash
uv run python -c "from mcp_atlassian.servers.main import AtlassianMCP, main_mcp; print('ok')"
```

Expected: `ok` printed.

**Step 3: Commit**

```bash
git add src/mcp_atlassian/servers/main.py
git commit -m "fix(server): update fastmcp 3.x import paths in servers/main.py"
```

---

### Task 15: Update remaining FastMCP imports across codebase

**Files:**
- Search: `grep -rln "from fastmcp" src/ tests/`
- Modify: all hits not covered by Tasks 13-14

**Step 1: Locate remaining imports**

Run: `grep -rn "from fastmcp" src/ tests/ | grep -v __pycache__`

**Step 2: Update each file using spike findings**

Common imports likely present:
- `from fastmcp import Client` (in tests)
- `from fastmcp.client import FastMCPTransport` (in tests)
- `from fastmcp.exceptions import ToolError` (in tests and `utils/decorators.py`)
- `from fastmcp.server.auth.auth import AccessToken` (in tests)

**Step 3: Run full test suite (import-only phase)**

```bash
uv run pytest -x --collect-only 2>&1 | tail -40
```

Expected: collection succeeds with no ImportError. Any remaining import error means a path was missed.

**Step 4: Commit**

```bash
git add -p  # stage only import changes
git commit -m "fix(deps): update remaining fastmcp 3.x import paths"
```

---

### Task 16: Update `_list_tools_mcp()` for `list_tools()` signature change

**Files:**
- Modify: `src/mcp_atlassian/servers/main.py` — `AtlassianMCP._list_tools_mcp()` method

**Step 1: Locate the override**

Run: `grep -n "_list_tools_mcp\|async def.*list_tools\|get_tools" src/mcp_atlassian/servers/main.py`

**Step 2: Change `get_tools()` call to `list_tools()`, adapt iteration**

Before (2.x pattern):
```python
all_tools: dict[str, FastMCPTool] = await self.get_tools()
for registered_name, tool_obj in all_tools.items():
    # tool_obj is FastMCPTool
    ...
```

After (3.x pattern — exact shape depends on Task 1 findings):
```python
all_tools: list[FastMCPTool] = await self.list_tools()
for tool_obj in all_tools:
    registered_name = tool_obj.name
    ...
```

**Important:** the `registered_name` value was a key in 2.x's dict. In 3.x list form, `tool_obj.name` is the authoritative name. If 2.x's dict key ever differed from `tool_obj.name` (e.g., namespace prefix), Task 1 spike must have surfaced that and this code block must handle it.

**Step 3: Run targeted tests**

```bash
uv run pytest tests/unit/servers/test_mcp_protocol.py -xvs -W error
```

Expected: PASS. If any of the Task 5 filter-behavior tests fail, the port is not behavior-preserving — fix before committing.

**Step 4: Commit**

```bash
git add src/mcp_atlassian/servers/main.py
git commit -m "fix(server): adapt _list_tools_mcp for fastmcp 3.x list_tools signature"
```

---

### Task 17: Update `mount()` call signatures

**Files:**
- Modify: `src/mcp_atlassian/servers/main.py`

**Step 1: Locate `mount()` calls**

Run: `grep -n "main_mcp.mount\|\.mount(" src/mcp_atlassian/servers/main.py`

**Step 2: Update call signature**

Before:
```python
main_mcp.mount(jira_mcp, "jira")
main_mcp.mount(confluence_mcp, "confluence")
```

After (per Task 1 spike — likely):
```python
main_mcp.mount(jira_mcp, namespace="jira")
main_mcp.mount(confluence_mcp, namespace="confluence")
```

Use the exact kwarg name from the spike, not a guess.

**Step 3: Smoke test server startup**

```bash
uv run python -c "from mcp_atlassian.servers.main import main_mcp; print([name for name in main_mcp._sub_servers] if hasattr(main_mcp, '_sub_servers') else 'check tools'); "
```

Or better: run the integration test that exercises mounted namespaces.

```bash
uv run pytest tests/unit/servers/test_mcp_protocol.py tests/unit/servers/test_cross_service.py -xvs -W error
```

Expected: PASS.

**Step 4: Commit**

```bash
git add src/mcp_atlassian/servers/main.py
git commit -m "fix(server): update mount() to fastmcp 3.x namespace kwarg"
```

---

### Task 18: Audit and update `AtlassianMCP.http_app()` kwargs

**Files:**
- Modify: `src/mcp_atlassian/servers/main.py` — `AtlassianMCP.http_app()` method

**Step 1: Locate `http_app()` override**

Run: `grep -n "def http_app\|super().http_app" src/mcp_atlassian/servers/main.py`

**Step 2: Cross-reference each kwarg against Task 1 spike**

For each of: `transport`, `middleware`, `event_store`, `stateless_http`, `json_response`, `retry_interval`:
- If still accepted by `http_app()` in 3.x → no change
- If moved to `run_http_async()` → remove from `http_app()` call, relocate to wherever `run_http_async()` is invoked (check `src/mcp_atlassian/__init__.py`)
- If renamed → rename

**Step 3: Check `run_http_async()` call site for relocations**

Run: `grep -n "run_async\|run_http_async" src/mcp_atlassian/__init__.py`

If any kwarg moved, update that call site too.

**Step 4: Run tests**

```bash
uv run pytest tests/unit/servers/ -xvs -W error
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/mcp_atlassian/servers/main.py src/mcp_atlassian/__init__.py
git commit -m "fix(server): relocate fastmcp 3.x http_app kwargs to correct call sites"
```

---

### Task 19: Update `fastmcp.settings` access patterns

**Files:**
- Modify: `src/mcp_atlassian/servers/main.py` — the three sites accessing `fastmcp_settings.streamable_http_path`

**Step 1: Locate each access**

Run: `grep -n "fastmcp_settings\." src/mcp_atlassian/servers/main.py`

Expected: 3 hits (per earlier analysis).

**Step 2: Update each access if the attribute moved**

Task 1 spike will tell you whether `streamable_http_path` is still on `fastmcp.settings` or elsewhere (e.g., `FASTMCP_MESSAGE_PATH` env, a different settings object, etc.).

**Step 3: Run tests that exercise HTTP path resolution**

If a test hits this code path, run it. Otherwise smoke-test by instantiating the server and inspecting the resolved path attribute set by `AtlassianMCP.__init__` or `http_app()`.

**Step 4: Commit**

```bash
git add src/mcp_atlassian/servers/main.py
git commit -m "fix(server): update fastmcp 3.x settings access for streamable_http_path"
```

---

### Task 20: Update `HardenedOAuthProxy.register_client()` if signature changed

**Files:**
- Modify: `src/mcp_atlassian/servers/oauth_proxy.py`

**Step 1: Cross-reference against Task 1 spike**

If `OAuthProxy.register_client()` signature or `OAuthClientInformationFull` shape changed in 3.x, update the override. Otherwise this task is a no-op.

**Step 2: Verify semantics preserved**

Re-read the override. Confirm the three hardening behaviors (forced `response_types`, `grant_types` filter, forced scope) still apply.

**Step 3: Run auth tests**

```bash
uv run pytest tests/unit/servers/test_auto_oauth.py tests/unit/auth/ -xvs -W error
```

Expected: PASS. If any Task 7 regression tests fail, fix before committing.

**Step 4: Commit (if changes)**

```bash
git add src/mcp_atlassian/servers/oauth_proxy.py
git commit -m "fix(auth): port HardenedOAuthProxy.register_client to fastmcp 3.x signature"
```

---

### Task 21: Update `AtlassianOpaqueTokenVerifier.verify_token()` if signature changed

**Files:**
- Modify: `src/mcp_atlassian/utils/token_verifier.py`

**Step 1: Cross-reference against Task 1 spike**

If `TokenVerifier.verify_token()` signature, `AccessToken` constructor, or `required_scopes` attribute changed, update.

**Step 2: Verify return shape**

`AccessToken(token=..., client_id="atlassian", scopes=..., expires_at=...)` must produce a valid 3.x AccessToken. If constructor fields renamed (e.g., `expires_at` → `expiration`), rename.

**Step 3: Run tests**

```bash
uv run pytest tests/unit/utils/test_token_verifier.py -xvs -W error
```

Expected: PASS.

**Step 4: Commit (if changes)**

```bash
git add src/mcp_atlassian/utils/token_verifier.py
git commit -m "fix(auth): port AtlassianOpaqueTokenVerifier to fastmcp 3.x AccessToken signature"
```

---

### Task 22: Update `UserTokenMiddleware` wiring if 3.x middleware pipeline changed

**Files:**
- Modify: `src/mcp_atlassian/servers/main.py` — `UserTokenMiddleware` installation in `http_app()`
- Consult: Task 3 spike findings

**Step 1: Apply findings from Task 3**

If Task 3 found that middleware attaches differently in 3.x (e.g., via a new method, or `request.state` semantics changed), update the installation point.

If Task 3 confirmed identical semantics, this task is a no-op.

**Step 2: Smoke-test middleware behavior**

Run HTTP middleware tests:
```bash
uv run pytest tests/unit/servers/ -k "middleware or header or token" -xvs -W error
```

Expected: PASS.

**Step 3: Commit (if changes)**

```bash
git add src/mcp_atlassian/servers/main.py
git commit -m "fix(server): adapt UserTokenMiddleware wiring to fastmcp 3.x pipeline"
```

---

### Task 23: Handle any env var renames

**Files:**
- Search: `grep -rln "FASTMCP_" src/ tests/ .env.example docs/ scripts/`

**Step 1: Enumerate FastMCP-prefixed env vars in use**

**Step 2: For each, confirm 3.x still recognizes it**

Known rename: `FASTMCP_SHOW_CLI_BANNER` → `FASTMCP_SHOW_SERVER_BANNER`. Task 1 spike may have surfaced others.

**Step 3: Update `.env.example` and docs to reflect renames**

**Step 4: Commit**

```bash
git add .env.example docs/
git commit -m "docs: update fastmcp 3.x env var names"
```

---

### Task 24: Full test suite — green or identify residual failures

**Step 1: Run full suite with warnings as errors**

```bash
uv run pytest -x -W error 2>&1 | tee /tmp/fastmcp3-test-run.log
```

**Step 2: If anything fails**

Triage each failure: is it (a) behavior-preservation test from Tasks 5-10 failing = **real drift, must fix before proceeding**; or (b) a test coupled to 2.x internal details that need a mechanical test update = fix the test to use 3.x API, not skip it.

**Step 3: If all pass**

Proceed to Task 25.

**Step 4: Commit any test updates**

```bash
git add tests/
git commit -m "test: update tests coupled to fastmcp 2.x internals"
```

---

### Task 25: mypy strict pass

**Step 1: Run mypy**

```bash
uv run mypy src/
```

Expected: no errors.

**Step 2: Fix any type errors introduced by 3.x type changes**

Common: if `list_tools()` return type shifted from `dict[str, Tool]` to `list[Tool]`, any type annotations on call sites need updating.

**Step 3: Commit**

```bash
git add src/
git commit -m "chore: fix mypy strict errors from fastmcp 3.x type changes"
```

---

### Task 26: Pre-commit pass

**Step 1: Run pre-commit on all files**

```bash
pre-commit run --all-files
```

Expected: all hooks pass.

**Step 2: Fix any Ruff formatting/lint issues**

**Step 3: Commit**

```bash
git add -A
git commit -m "chore: ruff formatting/lint after fastmcp 3.x migration"
```

---

### Task 27: Add code-comment breadcrumbs to override sites

**Files:**
- Modify: `src/mcp_atlassian/servers/main.py` — at `AtlassianMCP._list_tools_mcp()` and `AtlassianMCP.http_app()`

**Step 1: Add a single-line comment pointing to the deferred-refactor issue**

At the top of each override:
```python
# Deferred: evaluate replacing this override with a native FastMCP 3.x
# extension surface. See Troubladore/mcp-atlassian#326.
```

Keep it to two lines max. No multi-paragraph docstring.

**Step 2: Commit**

```bash
git add src/mcp_atlassian/servers/main.py
git commit -m "docs(server): breadcrumb deferred refactor to #326 at override sites"
```

---

### Task 28: Manual stdio smoke test

**Step 1: Start the server in stdio mode against a sandbox**

Use the MCPTEST (Confluence) and JTEST (Jira Cloud) sandboxes. Point the server at one of them via env vars.

```bash
uv run mcp-atlassian
```

**Step 2: Verify tool enumeration**

Via an MCP client (or curl-equivalent for stdio), request `tools/list` and confirm:
- Tool count matches what `tests/unit/utils/test_toolsets.py` asserts
- A Jira read tool appears when only Jira is configured
- A Confluence read tool does not appear when Confluence is not configured
- In `READ_ONLY_MODE=true`, no `write`-tagged tool appears

**Step 3: Record test evidence**

Capture output (screenshot or log) of the tool list. This is the "fresh verification" required by verification-before-completion skill for claiming stdio transport works.

**Step 4: Commit nothing (smoke test)**

---

### Task 29: Manual HTTP transport smoke test (if any HTTP code changed)

**Applies only if Tasks 18, 19, or 22 produced changes.**

**Step 1: Start the server in HTTP mode with OAuth**

Use a throwaway OAuth configuration or the existing Atlassian sandbox.

**Step 2: Exercise the callback path**

Initiate an OAuth flow, complete consent, and confirm:
- Token is stored (wherever 3.x puts it)
- `UserTokenMiddleware` populates `request.state.atlassian_service_headers` for subsequent requests
- Tool list respects per-request service availability
- SSRF validation still rejects invalid URL overrides

**Step 3: Record evidence**

Capture the OAuth round-trip log and a tool-list response. If the DiskStore → FileTreeStore change required re-auth, confirm it happened once and then worked.

**Step 4: Commit nothing**

---

### Task 30: Verify all three CVEs resolved in Dependabot

**Step 1: Push the branch (already done at start)**

If new commits exist, push:
```bash
git push
```

**Step 2: Check Dependabot alerts against the branch**

```bash
gh api repos/Troubladore/mcp-atlassian/dependabot/alerts --jq '.[] | select(.security_advisory.summary | contains("FastMCP")) | {number, state, summary: .security_advisory.summary}'
```

Dependabot alerts on the default branch do not automatically reflect non-default branches. This is a sanity check that our constraint is now `>=3.2.0`, which will clear the alerts once merged.

**Step 3: Commit nothing**

---

### Task 31: Release notes

**Files:**
- Modify: `CHANGELOG.md` or equivalent (check what the project uses)

**Step 1: Locate the changelog**

Run: `ls CHANGELOG* HISTORY* 2>&1; grep -l "## " docs/*.md 2>&1 | head -3`

**Step 2: Add an entry under the next release**

Outline (sharpen using Task 2 spike findings):
```markdown
## Security

- Upgraded to FastMCP 3.2.0 to remediate CVE-2026-32871 (critical, SSRF in OpenAPI Provider; not applicable to this project), CVE-2026-27124 (high, OAuth Proxy callback consent verification), and CVE-2025-64340 (medium, Gemini CLI; not applicable).

## User-visible migration notes

- **OAuth default-storage deployments:** FastMCP 3.x changed its default OAuth client storage backend (DiskStore → FileTreeStore, itself a security fix for CVE-2025-69872). Deployments using the default storage mode (`ATLASSIAN_OAUTH_CLIENT_STORAGE_MODE` unset) will need to re-authenticate once after upgrade. Deployments using `ATLASSIAN_OAUTH_CLIENT_STORAGE_MODE=factory` with a custom backend are unaffected.
- **Python minimum:** [only if Task 4 found a bump]

## Deferred

- Architectural refactor to adopt FastMCP 3.x native extension surfaces (replacing subclass overrides for tool catalog filtering and HTTP middleware injection) is tracked as #326 and will ship in a follow-up release.
```

**Step 3: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: add fastmcp 3.x migration release notes"
```

---

### Task 32: Open the PR

**Goal:** Rollup PR into `community/main` per the branch plan.

**Step 1: Push all commits**

```bash
git push
```

**Step 2: Create PR**

```bash
gh pr create --base community/main --title "fix(deps): migrate to fastmcp 3.x for CVE remediation" --body "$(cat <<'EOF'
## Summary

Upgrades FastMCP from 2.14.5 to >=3.2.0 to remediate three Dependabot CVEs:
- CVE-2026-32871 (critical, SSRF in OpenAPI Provider)
- CVE-2026-27124 (high, OAuth Proxy callback consent verification)
- CVE-2025-64340 (medium, Gemini CLI)

This is a **compatibility-first port** with minimal behavior drift. Architectural refactor to adopt FastMCP 3.x native extension surfaces is deliberately deferred to #326.

## Non-negotiables preserved

- Tool visibility rules (toolset filter, enabled_tools allowlist, read-only suppression, per-service availability, schema sanitization)
- HTTP middleware semantics (auth extraction, SSRF validation, request.state population, 401 handling, disconnect tolerance)
- Auth policy (HardenedOAuthProxy DCR constraints, require_authorization_consent=True)

## User-visible migration

OAuth default-storage deployments will need to re-authenticate once due to upstream FastMCP 3.x storage backend change. See release notes.

## Test plan

- [ ] Full unit suite passes under `-W error`
- [ ] mypy strict passes
- [ ] pre-commit passes
- [ ] Manual stdio smoke test against sandbox
- [ ] Manual HTTP+OAuth smoke test (if HTTP paths changed)
- [ ] All three Dependabot alerts clear after merge

Closes #320
EOF
)"
```

**Step 3: Verify PR appears**

```bash
gh pr view --web
```

**Step 4: Commit nothing (PR is external)**

---

## Reference: skills to invoke during execution

- `superpowers:test-driven-development` — every task that adds code must write the failing test first
- `superpowers:verification-before-completion` — before claiming "Task N complete", run the proving command in the current message
- `superpowers:systematic-debugging` — if any task triggers unexpected failures, use this before proposing fixes
- `superpowers:receiving-code-review` — when review comments arrive on the PR

## What to skip

- **Do NOT** add 3.x extension-surface refactoring in this PR. That is #326.
- **Do NOT** write a DiskStore → FileTreeStore migration shim. That is #326 if we decide to do it.
- **Do NOT** add "while we're here" cleanups unrelated to the migration.
- **Do NOT** use `--no-verify` or bypass signing to work around pre-commit failures — fix root causes.
