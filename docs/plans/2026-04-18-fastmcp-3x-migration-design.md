# FastMCP 2.x → 3.x Security Migration Design

**Date:** 2026-04-18
**Branch:** `fix/fastmcp-3x-cve` (off `community/main`)
**Tracking:** [#320 local](https://github.com/Troubladore/mcp-atlassian/issues/320) · [sooperset/mcp-atlassian#1234 upstream](https://github.com/sooperset/mcp-atlassian/issues/1234)
**Deferred work:** [#326 Post-3.x convergence](https://github.com/Troubladore/mcp-atlassian/issues/326)

## Guiding principle

> We will take a compatibility-first FastMCP 3.x port to remediate the security issue with minimal behavior drift, and defer any adoption of new 3.x extension surfaces to a separate post-migration refactor once production behavior is validated.

## Motivation

Three open Dependabot alerts against `fastmcp>=2.13.0,<2.15.0` (currently 2.14.5), all requiring `fastmcp>=3.2.0`:

| CVE | Severity | Exposure |
|-----|----------|----------|
| CVE-2026-32871 | Critical | SSRF & path traversal in OpenAPI Provider — **not applicable** (we don't use OpenAPIProvider) |
| CVE-2026-27124 | High | Missing consent verification in OAuth Proxy Callback (confused deputy) — **applicable** to HTTP+OAuth deployments |
| CVE-2025-64340 | Medium | Command injection in Gemini CLI — **not applicable** |

Practical driver: CVE-2026-27124. The fix is in the upstream callback path; our `HardenedOAuthProxy` hardens a different layer (DCR policy) and does not by itself patch the CVE.

## Scope

**In scope:** thin mechanical port of all FastMCP imports, API signatures, and subclass overrides to 3.x.

**Out of scope** (deferred to [#326](https://github.com/Troubladore/mcp-atlassian/issues/326)):
- Replacing `_list_tools_mcp()` override with native 3.x tool-catalog hook (if one exists)
- Replacing `http_app()` override with native 3.x middleware injection
- Removing or simplifying the `AtlassianMCP` subclass
- Writing an OAuth storage migration shim (DiskStore → FileTreeStore) — accept forced re-auth

## Non-negotiables for this PR

1. No behavior change in tool visibility rules — toolset filtering, `enabled_tools` allowlist, read-only `write` tool suppression, per-service availability gating, schema sanitization all preserved bit-for-bit.
2. No behavior change in HTTP middleware semantics — `UserTokenMiddleware` continues to perform auth header extraction, SSRF validation, `request.state` population, 401 rejection, and disconnect-safe response handling at the same point in the request lifecycle.
3. No behavior change in auth policy — `HardenedOAuthProxy` DCR constraints (response_types, grant_types allowlist, forced scopes) remain active with identical semantics; `require_authorization_consent=True` remains set.
4. No silent config-autoload regression — every FastMCP-consumed config value continues to be explicitly passed.

## Architectural analysis (from code review)

### `AtlassianMCP(FastMCP[MainAppContext])` overrides

**`_list_tools_mcp()`** — real product behavior. Reads `MainAppContext` from lifespan state, reads per-request `request.state.atlassian_service_headers`, filters by toolset membership, `enabled_tools` allowlist, read-only mode, and service availability, then rewrites each emitted schema via `_sanitize_schema_for_compatibility()`. Must survive the migration.

**`http_app()`** — mostly wiring. Installs `UserTokenMiddleware`, normalizes the streamable HTTP path so the middleware knows which POST endpoint to process, forwards the rest to `super().http_app(...)`. The intrinsic HTTP-layer logic lives in the middleware, not in this override.

### `HardenedOAuthProxy(OAuthProxy)`

Override is only `register_client()`. Forces `response_types=["code"]`, filters requested grant_types against an allowlist, forces scope to a configured value, delegates to super. **Orthogonal to CVE-2026-27124** (which is about callback consent verification, not DCR input policy). Ports mechanically; no redesign required.

### `AtlassianOpaqueTokenVerifier(TokenVerifier)`

Override is only `verify_token()`. Uses named public fields on `AccessToken(token, client_id, scopes, expires_at)`, no private method calls, no FastMCP-internal exception types. **Mechanical port** pending verification of 3.x `AccessToken` constructor signature.

### `_build_auth_provider()` and `build_oauth_client_storage_from_env()`

`_build_auth_provider()` reads every config value from our own env vars and passes all of them explicitly to `HardenedOAuthProxy(...)`. **No silent env-autoload trap** — upgrading to 3.x (which removes auth-provider env auto-loading) does not break this code.

`build_oauth_client_storage_from_env()` returns `None` when `ATLASSIAN_OAUTH_CLIENT_STORAGE_MODE` is unset/default. `_build_auth_provider()` then passes `client_storage=None`, deferring to FastMCP's default backend. **This is the real user-impact surface:** default-mode OAuth deployments will inherit the 3.x DiskStore → FileTreeStore change and may need to re-authenticate once.

## User-impact model

Breakage taxonomy:
- **Type A — boot-time/framework:** subclass overrides stop matching FastMCP internals. Loud failures, caught by CI.
- **Type B — behavior drift:** server starts fine but semantics shift (tool visibility, auth flow, storage location). Quiet failures, require behavioral testing.

| Segment | Type A risk | Type B risk |
|---------|-------------|-------------|
| Stdio + Docker (most common) | Moderate — subclass overrides must match new internals; tool enumeration is startup-critical | Low |
| HTTP + PAT (multi-tenant) | Moderate | High — correctness depends on `request.state.atlassian_service_headers` being populated identically by 3.x's middleware pipeline |
| HTTP + OAuth, default storage mode | Moderate | **High** — inherits DiskStore → FileTreeStore change; re-auth likely required |
| HTTP + OAuth, factory storage mode | Moderate | Low — our custom storage is isolated from the default change |

## Migration tactics

### 1. Version constraint bump

`pyproject.toml`: `fastmcp>=2.13.0,<2.15.0` → `fastmcp>=3.2.0,<4.0.0`.
Verify Python minimum version required by FastMCP 3.x against our `requires-python = ">=3.10"` — bump if needed.

### 2. Import path updates

Search and replace across `src/mcp_atlassian/` and `tests/`:
- `fastmcp.server.auth.oauth_proxy` → new 3.x path (to be determined by spike)
- `fastmcp.server.auth.auth` → new 3.x path
- `fastmcp.server.dependencies.get_access_token, get_http_request` → confirm still present / relocated
- `fastmcp.server.http.StarletteWithLifespan` → confirm still present / relocated
- `fastmcp.server.event_store.EventStore` → confirm still present / relocated
- `fastmcp.tools.Tool` → confirm still present / relocated
- `fastmcp.exceptions.ToolError` → confirm still present / relocated

### 3. `AtlassianMCP._list_tools_mcp()`

Replace `await self.get_tools()` (returns `dict[str, FastMCPTool]`) with `await self.list_tools()` (returns `list[FastMCPTool]`). Adjust iteration — we previously iterated `items()`, now iterate the list directly. `tool.name` is already on the tool object. All filtering, `tags` access, `to_mcp_tool()` calls, and `_sanitize_schema_for_compatibility()` logic remains identical.

### 4. `AtlassianMCP.http_app()`

Verify 3.x `http_app()` parameter list. Some constructor kwargs (`host`, `port`, `log_level`, etc.) moved to `run_http_async()`. Audit the 5 kwargs we currently pass (`transport`, `middleware`, `event_store`, `stateless_http`, `json_response`, `retry_interval`) against the new signature and relocate any that moved.

### 5. `main_mcp.mount(jira_mcp, "jira")` signature change

Update to `main_mcp.mount(jira_mcp, namespace="jira")` at the two call sites in `servers/main.py`.

### 6. `HardenedOAuthProxy`

Import path update. Verify `OAuthProxy.register_client()` signature and `OAuthClientInformationFull` shape against 3.x. Keep semantics identical.

### 7. `AtlassianOpaqueTokenVerifier`

Import path update. Verify `AccessToken(token, client_id, scopes, expires_at)` constructor against 3.x. Verify `TokenVerifier.required_scopes` attribute still present.

### 8. `fastmcp.settings` access

Three sites in `servers/main.py` reference `fastmcp_settings.streamable_http_path`. Verify the settings structure and migrate access if the attribute moved.

### 9. Env var rename

If any user-facing docs reference `FASTMCP_SHOW_CLI_BANNER`, update to `FASTMCP_SHOW_SERVER_BANNER`.

## Testing strategy

### Existing safety net

Unit and integration tests under `tests/`. Behavioral tests around tool listing, auth, and HTTP middleware are the load-bearing coverage for this migration.

### Required regression tests (if not already covered)

- `_list_tools_mcp()` filters by read-only mode, toolset allowlist, `enabled_tools` allowlist, per-service availability — each condition has an explicit test
- `HardenedOAuthProxy.register_client()` rejects/rewrites bad inputs (forced response_types, grant_type filtering, forced scopes)
- `AtlassianOpaqueTokenVerifier.verify_token()` returns `None` for empty token, correctly-shaped `AccessToken` otherwise
- `UserTokenMiddleware` populates `request.state.atlassian_service_headers` correctly from auth headers
- Schema sanitization via `_sanitize_schema_for_compatibility()` produces identical output before and after migration

Add coverage for any gap before porting code.

### Validation plan

1. Full test suite: `uv run pytest -xvs -W error`
2. Type check: `uv run mypy src/`
3. Lint: `pre-commit run --all-files`
4. Manual stdio smoke test against a sandbox Atlassian instance
5. Manual HTTP transport smoke test if any HTTP code path changes

## Rollback path

The change is a single PR with a dependency bump and mechanical code updates. Rollback is `git revert` on the merge commit plus reverting the `pyproject.toml` constraint. No data migration is introduced by this PR itself — the DiskStore → FileTreeStore change is an upstream FastMCP decision, not ours. Users who roll back can return to `fastmcp>=2.13.0,<2.15.0` with no further action.

## Release notes outline

For the release cutting this PR:

- **Security:** Upgraded to FastMCP 3.2.0 to remediate CVE-2026-32871, CVE-2026-27124, CVE-2025-64340.
- **User-visible migration (OAuth only):** FastMCP 3.x changed its default OAuth storage backend. Deployments using the default storage mode (`ATLASSIAN_OAUTH_CLIENT_STORAGE_MODE` unset) may need to re-authenticate once after upgrade. Deployments using `ATLASSIAN_OAUTH_CLIENT_STORAGE_MODE=factory` with a custom backend are unaffected. This change is itself a security fix for CVE-2025-69872.
- **No user-facing tool changes.**
- **Deferred architectural cleanup** tracked at #326 — no action required.

## Open spikes (to answer before/during implementation)

1. **FastMCP 3.2.0 auth module layout** — new paths for `OAuthProxy`, `TokenVerifier`, `AccessToken`; stability of `OAuthClientInformationFull`, `TokenVerifier.required_scopes`, and `AccessToken` constructor fields.
2. **FastMCP 3.x storage behavior under `client_storage=None`** — when existing DiskStore data is present, is it migrated, ignored, or does it cause errors?
3. **FastMCP 3.x HTTP middleware pipeline** — does the `request.state` object remain the same, or do we need to update how `UserTokenMiddleware` populates it?
4. **`http_app()` constructor parameter list in 3.x** — which of our 5 kwargs are still accepted on `http_app()`, and which moved to `run_http_async()` or elsewhere?
5. **Python minimum version on FastMCP 3.x** — does `pyproject.toml` need a `requires-python` bump?

Each spike is bounded: answerable by reading FastMCP 3.2.0 source or running a small standalone test. No spike should block scope decisions — if an answer forces a material behavior change we're unwilling to accept, we fall back to Approach B (adopt 3.x extension surface) rather than ship a compromised port.

## Spike findings

*Recorded 2026-04-18 against fastmcp==3.2.4 installed at `/tmp/fastmcp3-spike/.venv`.*

### Kill-criteria verdict

**No blockers.** `OAuthProxy` and `TokenVerifier` remain subclassable with signatures preserved. Starlette-middleware pipeline is unchanged. We can proceed with the thin mechanical port as planned.

### Symbol mapping table

| Symbol | 2.x path | 3.x path | Notes |
|---|---|---|---|
| `OAuthProxy` | `fastmcp.server.auth.oauth_proxy.OAuthProxy` | `fastmcp.server.auth.oauth_proxy.OAuthProxy` | unchanged; also accessible via subpackage `oauth_proxy/proxy.py` |
| `OAuthClientInformationFull` | `fastmcp.server.auth.oauth_proxy.OAuthClientInformationFull` | `mcp.shared.auth.OAuthClientInformationFull` | **moved to MCP SDK** — update import |
| `TokenVerifier` | `fastmcp.server.auth.auth.TokenVerifier` | `fastmcp.server.auth.auth.TokenVerifier` | unchanged; now inherits from new `AuthProvider` base |
| `AccessToken` | `fastmcp.server.auth.auth.AccessToken` | `fastmcp.server.auth.auth.AccessToken` | unchanged; added optional `claims: dict[str, Any]` field |
| `get_access_token` | `fastmcp.server.dependencies.get_access_token` | `fastmcp.server.dependencies.get_access_token` | unchanged |
| `get_http_request` | `fastmcp.server.dependencies.get_http_request` | `fastmcp.server.dependencies.get_http_request` | unchanged |
| `StarletteWithLifespan` | `fastmcp.server.http.StarletteWithLifespan` | `fastmcp.server.http.StarletteWithLifespan` | unchanged |
| `EventStore` | `fastmcp.server.event_store.EventStore` | `fastmcp.server.event_store.EventStore` | unchanged for application code; in 3.x it is a subclass of `mcp.server.streamable_http.EventStore` (the SDK type), but the `fastmcp.server.event_store` re-export still exists and is what `http_app(event_store=...)` is typed against in `server/mixins/transport.py` |
| `Tool` | `fastmcp.tools.Tool` | `fastmcp.tools.Tool` | unchanged (re-exported from `fastmcp.tools.base`) |
| `ToolError` | `fastmcp.exceptions.ToolError` | `fastmcp.exceptions.ToolError` | unchanged |
| `FastMCP`, `Context` | `fastmcp.FastMCP`, `fastmcp.Context` | same | unchanged |
| `Client`, `FastMCPTransport` | `fastmcp.Client`, `fastmcp.client.transports.FastMCPTransport` | same | unchanged |
| `fastmcp.settings.streamable_http_path` | attribute on top-level singleton | same | unchanged |

### A. `AccessToken` constructor

Fields: `token: str`, `client_id: str`, `scopes: list[str]`, `expires_at: int | None = None`, `resource: str | None = None`, plus new optional `claims: dict[str, Any]`. Existing kwargs unchanged; our `AtlassianOpaqueTokenVerifier` port needs no signature change.

### B. `TokenVerifier` base class

```python
class TokenVerifier(AuthProvider):
    def __init__(self, base_url=None, required_scopes=None, resource_base_url=None): ...
    @property
    def scopes_supported(self) -> list[str]:
        return self.required_scopes or []
    async def verify_token(self, token: str) -> AccessToken | None:
        raise NotImplementedError
```

`required_scopes` still present; `verify_token` signature unchanged; now inherits from `AuthProvider` but init still accepts the scope kwarg we use.

### C. `OAuthProxy.register_client()` signature

```python
async def register_client(self, client_info: OAuthClientInformationFull) -> None: ...
```

Unchanged. `HardenedOAuthProxy` override pattern remains valid — we can still force `response_types`, filter `grant_types`, and force scope by overriding.

### D. `OAuthProxy.__init__()` — client storage kwarg

```python
def __init__(
    self, *,
    upstream_authorization_endpoint, upstream_token_endpoint, upstream_client_id,
    upstream_client_secret=None, upstream_revocation_endpoint=None,
    token_verifier, base_url, resource_base_url=None, redirect_path=None,
    issuer_url=None, service_documentation_url=None,
    allowed_client_redirect_uris=None, valid_scopes=None,
    forward_pkce=True, forward_resource=True,
    token_endpoint_auth_method=None,
    extra_authorize_params=None, extra_token_params=None,
    client_storage: AsyncKeyValue | None = None,
    jwt_signing_key=None,
    require_authorization_consent: bool | Literal["external"] = True,
    consent_csp_policy=None, fallback_access_token_expiry_seconds=None,
    enable_cimd=True,
): ...
```

- Kwarg name unchanged (`client_storage`).
- Type changed from `ClientStorage | None` (2.x) to `AsyncKeyValue | None` (3.x) — a protocol from the `key_value.aio` package. Our current default path returns `None`, so types do not bite us there; factory-mode users supply their own backend implementing the protocol.
- `require_authorization_consent=True` still the default — matches our policy.

### E. `http_app()` vs `run_http_async()` kwarg locations

**`http_app()`** kwargs in 3.x:
`path`, `middleware`, `json_response`, `stateless_http`, `transport`, `event_store`, `retry_interval`.

**`run_http_async()`** kwargs in 3.x:
`show_banner`, `transport`, `host`, `port`, `log_level`, `path`, `uvicorn_config`, `middleware`, `json_response`, `stateless_http`, `stateless`.

Kwarg movement vs. 2.x:
- `event_store`, `retry_interval`: **on `http_app()`** in 3.x (still). No move.
- `transport`: now accepted on both as a param (was settings-only in 2.x).
- All others present on `http_app()` unchanged.

Our `AtlassianMCP.http_app()` override should pass `middleware`, `json_response`, `stateless_http`, `event_store`, `retry_interval`, `transport` to `super().http_app(...)` — same set as today. No relocation required.

### F. `mount()` namespace kwarg

```python
def mount(self, server, namespace=None, as_proxy=None, tool_names=None, prefix=None) -> None: ...
```

`namespace=` is the canonical kwarg; `prefix=` is deprecated but accepted. Our calls `main_mcp.mount(jira_mcp, "jira")` work as positional today; to avoid the deprecation path, switch to `namespace="jira"`.

### G. `list_tools()` return shape

```python
async def list_tools(self, *, run_middleware: bool = True) -> Sequence[Tool]: ...
```

Returns `Sequence[Tool]`, **not** `dict[str, Tool]`. Iteration switches from `for k, v in tools.items()` to `for tool in tools`. `tool.name` is the authoritative name.

No top-level `get_tools()` on the server; if our override called `self.get_tools()` we need to switch to `self.list_tools()`. **Confirm at Task 16** which method our override uses.

### H. `fastmcp.settings`

Still a top-level singleton (`settings = Settings()` in `fastmcp/__init__.py`). `streamable_http_path: str = "/mcp"` is a `Settings` field. Access pattern `fastmcp.settings.streamable_http_path` works unchanged.

### I. Subclass-compatibility summary

- `HardenedOAuthProxy` → **port mechanically, import update only for `OAuthClientInformationFull`** (now from `mcp.shared.auth`).
- `AtlassianOpaqueTokenVerifier` → **no signature changes needed**; `required_scopes` still accepted via `__init__`.
- `AtlassianMCP._list_tools_mcp` → **must change iteration** from `dict.items()` to list comprehension over `Sequence[Tool]`, and call `list_tools()` instead of `get_tools()` if our code uses the latter.
- `AtlassianMCP.http_app` → **no kwarg relocation**; only possibly update `Middleware` import (still `starlette.middleware.Middleware`, unchanged).

### OAuth storage behavior under `client_storage=None` (Spike 2)

**What the source shows:** FastMCP 3.x removes internal use of `DiskStore` (the class still exists in the third-party `key_value` package but is not imported anywhere in `fastmcp/`). When `client_storage=None`, `OAuthProxy.__init__` constructs an **encrypted `FileTreeStore`** (per-key JSON, Fernet-wrapped) at `${FASTMCP_HOME:-~/.local/share/fastmcp}/oauth-proxy/<12-char sha256 fingerprint of derived storage key>/`. The on-disk format (per-key JSON) is not structurally compatible with what 2.x's `DiskStore` (diskcache/SQLite) wrote, and no migration path was found in the FastMCP source.

**Operational impact (not yet exercised):** Source evidence is consistent with default-mode deployments needing to re-authenticate once after upgrade, but this spike did not actually attempt to read pre-existing 2.x storage under the 3.x code path. Until that is demonstrated, default-mode deployments **should be treated as requiring re-auth** for release-note and rollout planning purposes.

**Release note wording:** *"OAuth client storage (default mode): FastMCP 3.x replaces the previous `DiskStore` with an encrypted `FileTreeStore` at a new path under `$FASTMCP_HOME` (default `~/.local/share/fastmcp/oauth-proxy/<key-fingerprint>/`). Treat default-mode deployments as requiring a one-time re-authentication after upgrade unless migration compatibility is explicitly demonstrated. Operators who need zero-downtime cutover should migrate to `ATLASSIAN_OAUTH_CLIENT_STORAGE_MODE=factory` with an external backend before the upgrade."*

### HTTP middleware pipeline (Spike 3)

**Verdict:** No upstream structural change found that would force middleware rewiring. In 3.x, Starlette middleware still attaches via the `middleware=list[starlette.middleware.Middleware]` kwarg on `FastMCP.http_app()` (forwarded from `run_http_async`), and FastMCP's outermost layer `RequestContextMiddleware` constructs a stock `starlette.requests.Request(scope)` — the shared `scope["state"]` is what Starlette uses for `request.state`, and nothing in the traced call path rewraps or relocates it. Order is preserved: our `UserTokenMiddleware` would run after `RequestContextMiddleware` (so `get_http_request()` works inside tools) and before any auth-provider route wrappers (so SSRF check + 401 short-circuit still win before MCP handling).

**How we'll verify:** Keep current middleware insertion pattern unchanged and rely on regression tests around `request.state.atlassian_service_headers` population and early-401 behavior (Task 9) to catch any behavior drift the source read missed.

FastMCP 3.x also ships a new *MCP-level* middleware abstraction at `fastmcp.server.middleware`, registered via `FastMCP.add_middleware()`. It operates on `MiddlewareContext[T]` with MCP message types, **not** ASGI scope/receive/send — not a suitable home for `UserTokenMiddleware`. Orthogonal and additive to Starlette middleware.

### Python minimum version (Spike 4)

FastMCP 3.2.4 declares `Requires-Python: >=3.10`. Our project **can keep `requires-python = ">=3.10"`**. No Python 3.11+ syntax found in FastMCP 3.x source (`Self` uses `typing_extensions` backport; no `match` statements; no hard `ExceptionGroup` usage). Task 12 step 2 becomes a no-op.

### Concrete changes implied for the port

1. **Import updates** (Tasks 13–15):
   - `fastmcp.server.auth.oauth_proxy.OAuthClientInformationFull` → `mcp.shared.auth.OAuthClientInformationFull` (only confirmed application-level import move).
   - `fastmcp.server.event_store.EventStore` is **unchanged** for application code — the re-export still exists in 3.x, so `src/mcp_atlassian/servers/main.py` does not need to move this import.
   - All other `fastmcp.*` imports remain unchanged.

2. **API-shape updates** (Tasks 16–22):
   - **Task 16:** `_list_tools_mcp` iteration switches from dict to sequence; verify `get_tools()` vs. `list_tools()` usage at the call site.
   - **Task 17:** `mount(sub, "jira")` → `mount(sub, namespace="jira")` to avoid deprecation warning.
   - **Task 18:** No kwarg relocation on `http_app()`. Plan task becomes an audit only.
   - **Task 19:** `fastmcp.settings.streamable_http_path` unchanged — plan task likely no-op.
   - **Task 20:** `HardenedOAuthProxy.register_client` signature unchanged — no-op beyond the `OAuthClientInformationFull` import update.
   - **Task 21:** `AtlassianOpaqueTokenVerifier.verify_token` / `AccessToken` constructor unchanged — no-op.
   - **Task 22:** `UserTokenMiddleware` wiring unchanged — no-op.

3. **No Python bump** (Task 12 step 2 drops).

4. **Known FastMCP 3.x env var rename** to verify at Task 23: `FASTMCP_SHOW_CLI_BANNER` → `FASTMCP_SHOW_SERVER_BANNER`. Other `FASTMCP_*` vars to audit via grep.

## Success criteria

- All three CVEs resolved in Dependabot
- Full test suite passes on 3.x with no warnings
- All non-negotiables met (tool visibility, middleware semantics, auth policy, no silent autoload regression)
- PR diff readable as "mechanical port" — no architectural refactoring mixed in
- Release notes cover the OAuth re-auth scenario for default-mode users
