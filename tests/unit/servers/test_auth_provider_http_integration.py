"""HTTP-level integration tests for the FastMCP 3.x auth provider.

These tests mount `HardenedOAuthProxy` on a Starlette app via FastMCP 3.x's
`http_app()` and exercise the OAuth Proxy surface through ASGI, not by
calling provider methods directly. They prove that the provider boots, its
routes are wired, and the DCR hardening in `HardenedOAuthProxy` still
applies when driven over HTTP — which is the code path an actual OAuth
client (IDE, browser) would take.

Distinct from `test_oauth_proxy_build.py`, which unit-tests the Python
`register_client` method in isolation.
"""

from __future__ import annotations

import httpx
import pytest
from fastmcp import FastMCP

from mcp_atlassian.servers.main import _build_auth_provider


def _set_oauth_env(
    monkeypatch, *, allowed_grant_types: str = "authorization_code"
) -> None:
    monkeypatch.setenv("ATLASSIAN_OAUTH_PROXY_ENABLE", "true")
    monkeypatch.setenv("ATLASSIAN_OAUTH_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("ATLASSIAN_OAUTH_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv(
        "ATLASSIAN_OAUTH_REDIRECT_URI",
        "https://mcp.example.com/mcp-atlassian/callback",
    )
    monkeypatch.setenv("JIRA_URL", "https://jira.example.com")
    monkeypatch.delenv("CONFLUENCE_URL", raising=False)
    monkeypatch.setenv("ATLASSIAN_OAUTH_SCOPE", "read:jira-work")
    monkeypatch.setenv("ATLASSIAN_OAUTH_ALLOWED_GRANT_TYPES", allowed_grant_types)
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    monkeypatch.delenv("ATLASSIAN_OAUTH_INSTANCE_URL", raising=False)


def _build_asgi_app(provider):
    mcp = FastMCP(name="test-auth-app", auth=provider)
    return mcp.http_app(transport="streamable-http")


def test_auth_provider_boots_with_consent_required(monkeypatch):
    """CVE-2026-27124: the port must keep authorization consent required."""
    _set_oauth_env(monkeypatch)

    provider = _build_auth_provider()

    assert provider is not None
    assert provider._require_authorization_consent is True
    assert provider._allowed_grant_types == ["authorization_code"]
    assert provider._forced_scopes == ["read:jira-work"]


def test_auth_provider_exposes_expected_oauth_routes(monkeypatch):
    """All OAuth-spec endpoints the 3.x provider needs must be registered,
    including /callback and /consent which are the CVE-2026-27124 surfaces."""
    _set_oauth_env(monkeypatch)

    provider = _build_auth_provider()
    assert provider is not None

    route_paths = {r.path for r in provider.get_routes()}

    # Discovery surfaces
    assert "/.well-known/oauth-authorization-server" in route_paths
    assert any(
        path.startswith("/.well-known/oauth-protected-resource") for path in route_paths
    )
    # OAuth endpoints (DCR + authorization code flow)
    assert "/authorize" in route_paths
    assert "/token" in route_paths
    assert "/register" in route_paths
    # Callback / consent — the CVE-2026-27124 code paths
    assert "/callback" in route_paths
    assert "/consent" in route_paths


@pytest.mark.anyio
async def test_discovery_endpoint_serves_over_http(monkeypatch):
    """Mount the provider on a Starlette app and hit discovery over HTTP."""
    _set_oauth_env(monkeypatch)
    provider = _build_auth_provider()
    assert provider is not None

    app = _build_asgi_app(provider)

    transport = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        resp = await client.get("/.well-known/oauth-authorization-server")

    assert resp.status_code == 200
    payload = resp.json()
    assert "issuer" in payload
    assert "authorization_endpoint" in payload
    assert "token_endpoint" in payload
    assert "registration_endpoint" in payload


@pytest.mark.anyio
async def test_dcr_rejects_out_of_scope_request(monkeypatch):
    """Defense-in-depth: FastMCP 3.x's DCR endpoint rejects clients requesting
    scopes outside the provider's valid_scopes set (configured via
    ATLASSIAN_OAUTH_SCOPE). This check runs before HardenedOAuthProxy's
    hardening — losing it would expand the attack surface."""
    _set_oauth_env(monkeypatch)
    provider = _build_auth_provider()
    assert provider is not None

    app = _build_asgi_app(provider)

    payload = {
        "redirect_uris": ["http://localhost:1234/callback"],
        "grant_types": ["authorization_code"],
        "scope": "read:jira-work write:jira-work",
        "token_endpoint_auth_method": "none",
    }

    transport = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        resp = await client.post("/register", json=payload)

    assert resp.status_code == 400
    body = resp.json()
    assert body.get("error") == "invalid_client_metadata"


@pytest.mark.anyio
async def test_dcr_over_http_applies_hardened_grant_types(monkeypatch):
    """POST /register over HTTP must apply HardenedOAuthProxy's grant_types
    filtering end-to-end: a client requesting mixed grant_types gets only
    the allowlisted ones stored, response_types is forced to ['code'], and
    the scope is forced to the configured value. Proves the subclass
    override runs in the 3.x DCR pipeline, not just as a Python method."""
    _set_oauth_env(monkeypatch, allowed_grant_types="authorization_code")
    provider = _build_auth_provider()
    assert provider is not None

    app = _build_asgi_app(provider)

    payload = {
        "redirect_uris": ["http://localhost:1234/callback"],
        "grant_types": [
            "refresh_token",
            "authorization_code",
            "urn:ietf:params:oauth:grant-type:jwt-bearer",
        ],
        "response_types": ["code", "token"],
        "scope": "read:jira-work",
        "token_endpoint_auth_method": "none",
    }

    transport = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        resp = await client.post("/register", json=payload)

    assert resp.status_code == 201, resp.text
    body = resp.json()
    client_id = body["client_id"]
    assert client_id

    stored = await provider._client_store.get(key=client_id)
    assert stored is not None
    assert stored.response_types == ["code"]
    assert stored.grant_types == ["authorization_code"]
    assert stored.scope == "read:jira-work"


@pytest.mark.anyio
async def test_callback_route_rejects_missing_code(monkeypatch):
    """The /callback route must exist and return an error (not 500) when
    called without the required OAuth parameters. Proves the route is
    wired through the 3.x ASGI pipeline, not just present in get_routes()."""
    _set_oauth_env(monkeypatch)
    provider = _build_auth_provider()
    assert provider is not None

    app = _build_asgi_app(provider)

    transport = httpx.ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as client,
    ):
        resp = await client.get("/callback")

    # Should return 4xx (not 500) — bad request, not server crash
    assert 400 <= resp.status_code < 500, (
        f"callback returned {resp.status_code}: {resp.text}"
    )
