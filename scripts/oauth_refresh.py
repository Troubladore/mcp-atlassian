#!/usr/bin/env python
"""OAuth 2.0 refresh helper for BYO OAuth Cloud E2E tests.

Reads a long-lived refresh_token from the environment, mints a fresh
access_token via Atlassian's token endpoint, and emits the result without
persisting anything to ``~/.mcp-atlassian/`` or the OS keyring.

Two output modes:

- **Default (stdout JSON)**: prints a JSON block ``{access_token,
  refresh_token, cloud_id, expires_at}`` to stdout. The caller can pipe
  this into ``op item edit`` (or any other secrets-store update tool) to
  refresh storage.

- **``--exec CMD ARG...``**: sets ``CLOUD_E2E_OAUTH_ACCESS_TOKEN`` and
  ``CLOUD_E2E_OAUTH_CLOUD_ID`` in the child environment and execs the
  given command. Designed for wrapping pytest invocations of the BYO
  OAuth E2E suite so each run gets a fresh access token within
  Atlassian's ~1-hour expiry window.

Required environment variables:

- ``ATLASSIAN_OAUTH_CLIENT_ID``
- ``ATLASSIAN_OAUTH_CLIENT_SECRET``
- ``CLOUD_E2E_OAUTH_REFRESH_TOKEN``
- ``CLOUD_E2E_OAUTH_CLOUD_ID``

When invoking under ``op run --env-file=.env``, ``op://`` references in
the env file are substituted by the 1Password CLI before this script
runs, so this helper itself stays ignorant of any specific secrets store.
"""

import argparse
import json
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mcp_atlassian.utils.oauth import OAuthConfig

logger = logging.getLogger("oauth-refresh")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


REQUIRED_ENV_VARS = (
    "ATLASSIAN_OAUTH_CLIENT_ID",
    "ATLASSIAN_OAUTH_CLIENT_SECRET",
    "CLOUD_E2E_OAUTH_REFRESH_TOKEN",
    "CLOUD_E2E_OAUTH_CLOUD_ID",
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Refresh an Atlassian Cloud OAuth access token from a stored "
            "refresh_token without persisting tokens to disk or the OS keyring."
        )
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

    missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
    if missing:
        logger.error("Missing required environment variables: %s", ", ".join(missing))
        return 1

    config = OAuthConfig(
        client_id=os.environ["ATLASSIAN_OAUTH_CLIENT_ID"],
        client_secret=os.environ["ATLASSIAN_OAUTH_CLIENT_SECRET"],
        redirect_uri="",
        scope="",
        cloud_id=os.environ["CLOUD_E2E_OAUTH_CLOUD_ID"],
        refresh_token=os.environ["CLOUD_E2E_OAUTH_REFRESH_TOKEN"],
        persist=False,
    )

    if not config.refresh_access_token():
        logger.error("Failed to refresh access token")
        return 1

    if args.exec:
        cmd, *cmd_args = args.exec
        child_env = os.environ.copy()
        child_env["CLOUD_E2E_OAUTH_ACCESS_TOKEN"] = config.access_token or ""
        child_env["CLOUD_E2E_OAUTH_CLOUD_ID"] = config.cloud_id or ""
        # User-supplied command is the whole point of --exec. Caller has
        # explicit control over what is invoked.
        os.execvpe(cmd, [cmd, *cmd_args], child_env)  # noqa: S606
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
