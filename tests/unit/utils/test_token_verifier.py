"""Unit tests for Atlassian opaque token verifier."""

from __future__ import annotations

import time

import pytest
from fastmcp.server.auth.auth import AccessToken

from mcp_atlassian.utils.token_verifier import AtlassianOpaqueTokenVerifier


@pytest.mark.anyio
async def test_verify_token_returns_fastmcp_access_token() -> None:
    verifier = AtlassianOpaqueTokenVerifier(required_scopes=["read:jira-work"])

    token = await verifier.verify_token("opaque-token")

    assert isinstance(token, AccessToken)
    assert token is not None
    assert token.token == "opaque-token"
    assert token.scopes == ["read:jira-work"]
    assert token.client_id == "atlassian"


@pytest.mark.anyio
async def test_verify_token_returns_none_for_empty_token() -> None:
    verifier = AtlassianOpaqueTokenVerifier(required_scopes=[])

    token = await verifier.verify_token("")

    assert token is None


@pytest.mark.anyio
async def test_verify_token_expires_at_30_days_future() -> None:
    """verify_token attaches a ~30-day expiry (86400 * 30 seconds from now)."""
    verifier = AtlassianOpaqueTokenVerifier(required_scopes=["read:jira-work"])

    before = int(time.time())
    token = await verifier.verify_token("opaque-token")
    after = int(time.time())

    assert token is not None
    assert token.expires_at is not None

    thirty_days = 86400 * 30
    assert before + thirty_days <= token.expires_at <= after + thirty_days
