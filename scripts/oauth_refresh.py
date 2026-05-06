#!/usr/bin/env python
"""OAuth 2.0 refresh helper for BYO OAuth Cloud E2E tests.

Reads OAuth credentials from a configured *secret store* (``env`` or
``1password``), refreshes the access token, persists the rotated refresh
token back to the store, and either prints a JSON token block to stdout
or execs a child command (typically ``pytest``) with the fresh access
token in its environment.

Cloud refresh tokens are **single-use** — Atlassian rotates the
``refresh_token`` on every refresh, invalidating the old one. Storing
the rotated token back is therefore mandatory for repeatable workflows;
this script does it transparently when configured against a writable
store.

Two stores ship today:

- **env** (default): reads literal env vars, no write-back. Suitable for
  CI runs where the CI system injects credentials, or for one-off use
  where the rotated token can be captured from the JSON stdout.

- **1password**: reads + writes via the ``op`` CLI as a child subprocess.
  Owns ``op`` invocations directly with a list argv (no ``shell=True``),
  so the rotated refresh token never passes through a shell string.

Output modes:

- **Default (stdout JSON)**: prints
  ``{access_token, refresh_token, cloud_id, expires_at}`` to stdout.
- **--exec CMD ARG...**: sets ``CLOUD_E2E_OAUTH_ACCESS_TOKEN`` and
  ``CLOUD_E2E_OAUTH_CLOUD_ID`` in the child environment, then execs the
  given command. Designed to wrap pytest invocations of the
  byo_oauth-parametrized tests.

If the refresh request fails (e.g. the stored refresh token is stale)
**and** the configured store is writable, the script falls back to the
interactive browser authorize flow and persists the new tokens before
proceeding. This is the only path that requires a human in the loop —
the browser consent step.

Bootstrap (first-time setup) still uses ``scripts/oauth_authorize.py
--no-persist`` for the initial token mint.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import logging
import os
import sys
from collections.abc import Iterator

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPTS_DIR)
sys.path.append(os.path.dirname(_SCRIPTS_DIR))

from _oauth_stores import SecretStoreError, build_store  # noqa: E402

from src.mcp_atlassian.utils.oauth import OAuthConfig  # noqa: E402
from src.mcp_atlassian.utils.oauth_setup import (  # noqa: E402
    OAuthSetupArgs,
    run_oauth_flow_returning_config,
)

logger = logging.getLogger("oauth-refresh")


@contextlib.contextmanager
def _store_lock(lock_path: str | None) -> Iterator[None]:
    """Hold an exclusive lock for the duration of the critical section.

    Two processes targeting the same secret store would otherwise consume
    the same refresh_token, the second one's refresh would fail (Atlassian
    invalidated the token when the first refresh succeeded), and one of
    them would burn a rotation that never gets persisted. The lock
    serializes read → refresh → write per-store.
    """
    if lock_path is None:
        yield
        return
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def _reauthorize(client_id: str, client_secret: str) -> OAuthConfig | None:
    """Run the interactive browser authorize flow as a stale-token fallback.

    Returns the new OAuthConfig on success, None on failure.
    """
    redirect_uri = os.environ.get(
        "ATLASSIAN_OAUTH_REDIRECT_URI", "http://localhost:8080/callback"
    )
    scope = os.environ.get("ATLASSIAN_OAUTH_SCOPE")
    if not scope:
        logger.error(
            "Cannot re-authorize: ATLASSIAN_OAUTH_SCOPE is not set. "
            "Set it to the same scope string used at initial registration."
        )
        return None

    setup_args = OAuthSetupArgs(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope,
        persist=False,
    )
    return run_oauth_flow_returning_config(setup_args)


def main() -> int:
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(
        description=(
            "Refresh an Atlassian Cloud OAuth access token via a configured "
            "secret store, persist the rotated refresh token, and optionally "
            "exec a child command with the fresh credentials in its environment."
        )
    )
    parser.add_argument(
        "--store",
        choices=["env", "1password"],
        default=os.environ.get("CLOUD_E2E_OAUTH_BACKEND", "env"),
        help=(
            "Secret-store backend (default: %(default)s, also configurable via "
            "CLOUD_E2E_OAUTH_BACKEND). 'env' reads literal env vars (read-only); "
            "'1password' reads + writes via the op CLI."
        ),
    )
    parser.add_argument(
        "--op-vault",
        default=os.environ.get("ATLASSIAN_OAUTH_OP_VAULT"),
        help="1Password vault UUID (also: ATLASSIAN_OAUTH_OP_VAULT env var).",
    )
    parser.add_argument(
        "--op-item-id",
        default=os.environ.get("ATLASSIAN_OAUTH_OP_ITEM"),
        help="1Password item UUID (also: ATLASSIAN_OAUTH_OP_ITEM env var).",
    )
    parser.add_argument(
        "--reauthorize",
        action="store_true",
        help=(
            "Skip refresh and go straight to the interactive authorize flow. "
            "Use this when scopes have been added to the Atlassian app's "
            "Permissions page — a refresh would only mint a new access_token "
            "under the old scopes, while the user-clicked authorize flow "
            "issues a token reflecting the latest registration. Requires a "
            "writable store."
        ),
    )
    parser.add_argument(
        "--allow-rotation-loss",
        action="store_true",
        help=(
            "Permit --exec on a read-only store (e.g. 'env') even though the "
            "rotated refresh_token cannot be persisted. The next run will see "
            "a stale refresh_token and require re-authorization. Only use this "
            "in CI runners where credentials are injected per-job."
        ),
    )
    parser.add_argument(
        "--exec",
        nargs=argparse.REMAINDER,
        metavar="CMD",
        help=(
            "After refresh, exec CMD with CLOUD_E2E_OAUTH_ACCESS_TOKEN and "
            "CLOUD_E2E_OAUTH_CLOUD_ID set in the child environment."
        ),
    )
    args = parser.parse_args()

    # argparse.REMAINDER makes `--exec` with no command produce []. Reject
    # that before we burn a one-shot refresh token on a malformed call.
    if args.exec is not None and not args.exec:
        logger.error("--exec requires a command")
        return 1

    try:
        store = build_store(args.store, op_vault=args.op_vault, op_item=args.op_item_id)
    except SecretStoreError as exc:
        logger.error("%s", exc)
        return 1

    if args.exec and not store.writable() and not args.allow_rotation_loss:
        logger.error(
            "Refusing --exec with the read-only %s store: pytest would "
            "consume the refresh_token, Atlassian would rotate it, but the "
            "rotated value cannot be persisted back to the store — the next "
            "run would fail. Either switch to --store 1password, or pass "
            "--allow-rotation-loss to opt into the rotation-drop (CI only).",
            store.name,
        )
        return 1

    if args.reauthorize and not store.writable():
        logger.error(
            "--reauthorize requires a writable store; the %s store is read-only "
            "so the freshly-minted tokens would have nowhere to land.",
            store.name,
        )
        return 1

    with _store_lock(store.lock_path):
        try:
            creds = store.read()
        except SecretStoreError as exc:
            logger.error("%s", exc)
            return 1

        config = OAuthConfig(
            client_id=creds.client_id,
            client_secret=creds.client_secret,
            redirect_uri="",
            scope="",
            cloud_id=creds.cloud_id,
            refresh_token=creds.refresh_token,
            persist=False,
        )

        # Force re-authorization when --reauthorize is set: a refresh would
        # only mint a new access_token under the old scopes.
        refresh_succeeded = False if args.reauthorize else config.refresh_access_token()

        if not refresh_succeeded:
            if not store.writable():
                logger.error(
                    "Refresh failed and the %s store is read-only — re-run "
                    "scripts/oauth_authorize.py --no-persist to mint new tokens, "
                    "or switch to a writable store (--store 1password) for "
                    "automatic re-authorization.",
                    store.name,
                )
                return 1

            if args.reauthorize:
                logger.info(
                    "--reauthorize: launching interactive authorize flow. "
                    "A browser window will open; complete consent to mint "
                    "tokens reflecting the latest scope registration."
                )
            else:
                logger.warning(
                    "Refresh failed — falling back to interactive authorize "
                    "flow. A browser window will open; complete consent to "
                    "mint new tokens."
                )
            new_config = _reauthorize(creds.client_id, creds.client_secret)
            if new_config is None:
                logger.error("Authorize flow failed; new tokens NOT minted")
                return 1
            config = new_config

        if store.writable():
            try:
                store.write(
                    access_token=config.access_token or "",
                    refresh_token=config.refresh_token or "",
                    cloud_id=config.cloud_id or "",
                    expires_at=config.expires_at,
                )
                store.verify_refresh_token(config.refresh_token or "")
            except SecretStoreError as exc:
                logger.error("%s", exc)
                return 1

    if args.exec:
        cmd, *cmd_args = args.exec
        child_env = os.environ.copy()
        child_env["CLOUD_E2E_OAUTH_ACCESS_TOKEN"] = config.access_token or ""
        child_env["CLOUD_E2E_OAUTH_CLOUD_ID"] = config.cloud_id or ""
        os.execvpe(cmd, [cmd, *cmd_args], child_env)
        # execvpe replaces the process; this line only reached if exec fails.
        return 1

    payload = {
        "access_token": config.access_token,
        "refresh_token": config.refresh_token,
        "cloud_id": config.cloud_id,
        "expires_at": config.expires_at,
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
