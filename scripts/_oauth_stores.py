"""Pluggable secret-store backends for the BYO OAuth E2E workflow.

Two backends ship today:

- ``EnvStore`` (default): reads literal environment variables, no write-back.
  Suitable for contributors without a secret manager and for CI runs where
  credentials are injected as env vars by the CI system.

- ``OnePasswordStore``: reads + writes via the ``op`` CLI as a child
  subprocess. Owns ``op`` invocations directly with a list argv (no
  ``shell=True``), so secret values never pass through a shell string and
  the rotated refresh token is never visible as a ``$VAR`` expansion in any
  parent shell history. ``op item edit`` is invoked with
  ``stdin=subprocess.DEVNULL`` so op does not try to parse the parent's
  stdin as a JSON template (the documented op-subprocess gotcha from #328).

Adding a new backend (Vault, AWS Secrets Manager, GCP Secret Manager,
etc.) is a matter of implementing the same ``read()`` / ``write()`` /
``writable()`` surface; ``oauth_refresh.py`` will pick it up via the
``--store`` CLI flag.

Argv exposure note: ``op item edit`` accepts field updates as positional
``"section.field=value"`` arguments. The secret values are briefly visible
in ``/proc/<pid>/cmdline`` for the lifetime of the ``op`` subprocess (which
is hundreds of milliseconds at most). On a single-user dev machine this is
considered acceptable per #328's threat-model discussion. If a stricter
profile is needed later, switch the write path to ``op item edit``'s
template-via-stdin mode.
"""

from __future__ import annotations

import hashlib
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger("oauth-store")


class SecretStoreError(RuntimeError):
    """Raised when a secret store cannot satisfy a read or write."""


@dataclass
class Creds:
    client_id: str
    client_secret: str
    refresh_token: str
    cloud_id: str


class SecretStore(Protocol):
    name: str
    lock_path: str | None

    def read(self) -> Creds: ...
    def write(
        self,
        *,
        access_token: str,
        refresh_token: str,
        cloud_id: str,
        expires_at: float | None,
    ) -> None: ...
    def writable(self) -> bool: ...
    def verify_refresh_token(self, expected: str) -> None: ...


_ENV_FIELDS = {
    "client_id": "ATLASSIAN_OAUTH_CLIENT_ID",
    "client_secret": "ATLASSIAN_OAUTH_CLIENT_SECRET",
    "refresh_token": "CLOUD_E2E_OAUTH_REFRESH_TOKEN",
    "cloud_id": "CLOUD_E2E_OAUTH_CLOUD_ID",
}


class EnvStore:
    name = "env"
    lock_path: str | None = None

    def read(self) -> Creds:
        missing = [
            env_name
            for env_name in _ENV_FIELDS.values()
            if not os.environ.get(env_name)
        ]
        if missing:
            raise SecretStoreError(
                "env store missing required variables: " + ", ".join(missing)
            )
        return Creds(
            client_id=os.environ[_ENV_FIELDS["client_id"]],
            client_secret=os.environ[_ENV_FIELDS["client_secret"]],
            refresh_token=os.environ[_ENV_FIELDS["refresh_token"]],
            cloud_id=os.environ[_ENV_FIELDS["cloud_id"]],
        )

    def write(
        self,
        *,
        access_token: str,
        refresh_token: str,
        cloud_id: str,
        expires_at: float | None,
    ) -> None:
        logger.warning(
            "env store cannot persist rotated tokens — set CLOUD_E2E_OAUTH_BACKEND "
            "or rerun with --store 1password to enable write-back"
        )

    def writable(self) -> bool:
        return False

    def verify_refresh_token(self, expected: str) -> None:  # noqa: ARG002
        # Read-only store; nothing to verify.
        return


class OnePasswordStore:
    name = "1password"

    def __init__(
        self,
        *,
        vault: str,
        item: str,
        section_creds: str = "Atlassian Credentials",
        section_oauth: str = "OAuth Credentials",
    ) -> None:
        self.vault = vault
        self.item = item
        self.section_creds = section_creds
        self.section_oauth = section_oauth
        # Same-machine lock keyed by item UUID. Two processes targeting the
        # same 1Password item will serialize the read-refresh-write critical
        # section, so neither consumes the other's rotated refresh_token.
        # Cross-machine concurrency is out of scope (would require a
        # distributed lock or separate per-runner credentials).
        digest = hashlib.sha256(item.encode("utf-8")).hexdigest()[:16]
        self.lock_path = os.path.join(
            tempfile.gettempdir(), f"mcp_atlassian_oauth_{digest}.lock"
        )

    def _op_read(self, ref: str) -> str:
        # `op` is invoked by name (resolved via PATH); list argv prevents
        # any shell handling of the secret reference. Both behaviors are
        # required for the helper to be usable from any maintainer's
        # workstation regardless of where 1Password CLI lives.
        try:
            result = subprocess.run(
                ["op", "read", ref],
                capture_output=True,
                text=True,
                check=True,
                stdin=subprocess.DEVNULL,
                shell=False,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            msg = f"op read {ref} failed (1Password CLI unavailable or item missing)"
            raise SecretStoreError(msg) from exc
        return result.stdout.strip()

    def read(self) -> Creds:
        base = f"op://{self.vault}/{self.item}"
        return Creds(
            client_id=self._op_read(f"{base}/client_id"),
            client_secret=self._op_read(f"{base}/client_secret"),
            refresh_token=self._op_read(f"{base}/refresh_token"),
            cloud_id=self._op_read(f"{base}/cloud_id"),
        )

    def write(
        self,
        *,
        access_token: str,
        refresh_token: str,
        cloud_id: str,
        expires_at: float | None,
    ) -> None:
        # `op item edit` accepts `section.field=value` assignments. Each
        # assignment is its own argv element — no shell expansion, no
        # shell-string handling of the rotated refresh_token. stdin is
        # tied to /dev/null so op doesn't try to read a JSON template
        # from the parent's stdin.
        cmd = [
            "op",
            "item",
            "edit",
            self.item,
            "--vault",
            self.vault,
            f"{self.section_oauth}.access_token={access_token}",
            f"{self.section_oauth}.refresh_token={refresh_token}",
            f"{self.section_oauth}.cloud_id={cloud_id}",
        ]
        try:
            subprocess.run(
                cmd,
                check=True,
                stdin=subprocess.DEVNULL,
                shell=False,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            msg = "op item edit failed; rotated refresh token NOT persisted"
            raise SecretStoreError(msg) from exc

    def writable(self) -> bool:
        return True

    def verify_refresh_token(self, expected: str) -> None:
        """Re-read refresh_token from 1Password and assert it matches.

        Closes the gap where ``op item edit`` exits 0 but the value didn't
        actually persist (e.g. a concurrent writer overwrote it, or the
        item shape changed). Without this, the next run might fall back
        to the consent flow even though we thought we were done.
        """
        actual = self._op_read(f"op://{self.vault}/{self.item}/refresh_token")
        if actual != expected:
            msg = (
                "Persisted refresh_token does not match what was just written. "
                "Either a concurrent process overwrote the field, or the "
                "OnePasswordStore section/field labels diverged from the "
                "1Password item shape. Aborting before pytest so the next "
                "run does not fall back to consent."
            )
            raise SecretStoreError(msg)


def build_store(
    name: str,
    *,
    op_vault: str | None = None,
    op_item: str | None = None,
) -> SecretStore:
    """Construct a secret store by name.

    Names recognized: ``env``, ``1password``.
    """
    if name == "env":
        return EnvStore()
    if name == "1password":
        if not op_vault or not op_item:
            raise SecretStoreError(
                "1password store requires --op-vault and --op-item-id (or "
                "ATLASSIAN_OAUTH_OP_VAULT / ATLASSIAN_OAUTH_OP_ITEM env vars)"
            )
        return OnePasswordStore(vault=op_vault, item=op_item)
    raise SecretStoreError(f"unknown secret store: {name!r}")
