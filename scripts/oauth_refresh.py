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
import subprocess
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mcp_atlassian.utils.oauth import OAuthConfig

logger = logging.getLogger("oauth-refresh")


REQUIRED_ENV_VARS = (
    "ATLASSIAN_OAUTH_CLIENT_ID",
    "ATLASSIAN_OAUTH_CLIENT_SECRET",
    "CLOUD_E2E_OAUTH_REFRESH_TOKEN",
    "CLOUD_E2E_OAUTH_CLOUD_ID",
)


def main() -> int:
    # basicConfig only fires when invoked as a CLI; importing the script
    # for tests does NOT add a StreamHandler to the root logger, which
    # would otherwise interfere with pytest's caplog fixture.
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

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
    parser.add_argument(
        "--write-cmd",
        metavar="SHELL_CMD",
        help=(
            "Shell command to run after a successful refresh and before --exec. "
            "Intended for persisting the rotated refresh_token (Atlassian "
            "rotates it on every refresh — Cloud refresh tokens are one-shot). "
            "The command runs with ATLASSIAN_OAUTH_ACCESS_TOKEN, "
            "ATLASSIAN_OAUTH_REFRESH_TOKEN, ATLASSIAN_OAUTH_CLOUD_ID, and "
            "ATLASSIAN_OAUTH_EXPIRES_AT in the environment, and stdin tied "
            "to /dev/null (so `op item edit` doesn't try to parse the "
            "parent's stdin as a JSON template). If the command exits "
            "non-zero, oauth_refresh.py exits non-zero without running --exec."
        ),
    )
    args = parser.parse_args()

    # argparse.REMAINDER makes `--exec` with no command produce []. Catch
    # that before we burn a one-shot refresh token on a malformed call
    # whose JSON output would just go to an uncaptured terminal.
    if args.exec is not None and not args.exec:
        logger.error("--exec requires a command")
        return 1

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

    if args.write_cmd:
        write_env = os.environ.copy()
        write_env["ATLASSIAN_OAUTH_ACCESS_TOKEN"] = config.access_token or ""
        write_env["ATLASSIAN_OAUTH_REFRESH_TOKEN"] = config.refresh_token or ""
        write_env["ATLASSIAN_OAUTH_CLOUD_ID"] = config.cloud_id or ""
        write_env["ATLASSIAN_OAUTH_EXPIRES_AT"] = (
            str(config.expires_at) if config.expires_at is not None else ""
        )
        result = subprocess.run(  # noqa: S602
            args.write_cmd,
            shell=True,
            env=write_env,
            stdin=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode != 0:
            logger.error(
                "--write-cmd exited %d; aborting before --exec", result.returncode
            )
            return result.returncode

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
