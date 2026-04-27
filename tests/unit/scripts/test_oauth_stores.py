"""Tests for scripts/_oauth_stores.py — pluggable secret-store backends.

Two backends:
- EnvStore: reads literal env vars, no write-back.
- OnePasswordStore: reads + writes via `op` CLI subprocess, no shell.

The OnePasswordStore must:
- Use subprocess.run with a list (shell=False) so secrets never pass through
  a shell string — neither in expansion nor in argv-of-a-shell.
- Pass stdin=subprocess.DEVNULL on `op item edit` so op doesn't try to
  parse the parent's stdin as a JSON template (the documented op gotcha).
- Read each field via `op read op://<vault>/<item>/<field>`.
- Write all rotated fields in a single `op item edit` invocation.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from unittest.mock import MagicMock, patch


def _load_module():
    path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "scripts", "_oauth_stores.py"
        )
    )
    spec = importlib.util.spec_from_file_location("_oauth_stores", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_oauth_stores"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestEnvStore:
    def test_read_returns_credentials_from_env(self):
        mod = _load_module()
        env = {
            "ATLASSIAN_OAUTH_CLIENT_ID": "cid",
            "ATLASSIAN_OAUTH_CLIENT_SECRET": "csec",
            "CLOUD_E2E_OAUTH_REFRESH_TOKEN": "rtok",
            "CLOUD_E2E_OAUTH_CLOUD_ID": "cloud",
        }
        with patch.dict(os.environ, env, clear=True):
            creds = mod.EnvStore().read()
        assert creds.client_id == "cid"
        assert creds.client_secret == "csec"
        assert creds.refresh_token == "rtok"
        assert creds.cloud_id == "cloud"

    def test_read_raises_clear_error_when_missing(self):
        mod = _load_module()
        with patch.dict(os.environ, {}, clear=True):
            try:
                mod.EnvStore().read()
            except mod.SecretStoreError as exc:
                assert "ATLASSIAN_OAUTH_CLIENT_ID" in str(exc)
            else:
                raise AssertionError("expected SecretStoreError")

    def test_writable_is_false(self):
        mod = _load_module()
        assert mod.EnvStore().writable() is False

    def test_write_is_noop_with_warning(self, caplog):
        import logging

        mod = _load_module()
        with caplog.at_level(logging.WARNING):
            mod.EnvStore().write(
                access_token="a", refresh_token="r", cloud_id="c", expires_at=1.0
            )
        assert "env store cannot persist" in caplog.text.lower()


class TestOnePasswordStore:
    def test_read_uses_op_read_per_field_no_shell(self):
        mod = _load_module()

        captured: list[tuple[list[str], dict[str, object]]] = []

        def fake_run(cmd, **kwargs):
            captured.append((list(cmd), kwargs))
            field = cmd[-1].split("/")[-1]
            result = MagicMock()
            result.stdout = f"value-of-{field}\n"
            result.returncode = 0
            return result

        with patch("subprocess.run", side_effect=fake_run):
            creds = mod.OnePasswordStore(vault="VAULT", item="ITEM").read()

        assert creds.client_id == "value-of-client_id"
        assert creds.refresh_token == "value-of-refresh_token"
        # All four reads must be op subprocess invocations, list form (no shell).
        assert len(captured) == 4
        for cmd, kwargs in captured:
            assert cmd[0] == "op"
            assert cmd[1] == "read"
            assert cmd[2].startswith("op://VAULT/ITEM/")
            assert kwargs.get("shell", False) is False
            assert kwargs.get("stdin") == subprocess.DEVNULL

    def test_write_invokes_op_item_edit_no_shell_devnull_stdin(self):
        mod = _load_module()

        captured: dict[str, object] = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = list(cmd)
            captured["kwargs"] = kwargs
            result = MagicMock()
            result.returncode = 0
            return result

        with patch("subprocess.run", side_effect=fake_run):
            mod.OnePasswordStore(vault="V", item="ITEM").write(
                access_token="ATOK",
                refresh_token="RTOK-ROTATED",
                cloud_id="C",
                expires_at=1234.5,
            )

        cmd = captured["cmd"]
        kwargs = captured["kwargs"]
        # First three positional args: op item edit ITEM
        assert cmd[:3] == ["op", "item", "edit"]
        assert "ITEM" in cmd
        # Each rotated field appears as a discrete arg-list element so the
        # secret never passes through a shell string.
        assigns = [arg for arg in cmd if "=" in arg]
        assert any("access_token=ATOK" in a for a in assigns)
        assert any("refresh_token=RTOK-ROTATED" in a for a in assigns)
        assert kwargs.get("shell", False) is False
        assert kwargs.get("stdin") == subprocess.DEVNULL
        assert kwargs.get("check", False) is True

    def test_writable_is_true(self):
        mod = _load_module()
        assert mod.OnePasswordStore(vault="v", item="i").writable() is True

    def test_read_raises_secretstoreerror_on_op_failure(self):
        mod = _load_module()

        def fake_run(*_a, **_k):
            raise subprocess.CalledProcessError(returncode=1, cmd=["op"])

        with patch("subprocess.run", side_effect=fake_run):
            try:
                mod.OnePasswordStore(vault="v", item="i").read()
            except mod.SecretStoreError as exc:
                assert "op read" in str(exc).lower() or "1password" in str(exc).lower()
            else:
                raise AssertionError("expected SecretStoreError")

    def test_write_includes_vault_flag(self):
        """`op item edit` invocation must scope to the vault, not just the item.

        Read uses op://VAULT/ITEM/field — write should be symmetric.
        """
        mod = _load_module()
        captured: list[list[str]] = []

        def fake_run(cmd, **_kwargs):
            captured.append(list(cmd))
            result = MagicMock()
            result.returncode = 0
            return result

        with patch("subprocess.run", side_effect=fake_run):
            mod.OnePasswordStore(vault="VAULT-UUID", item="ITEM-UUID").write(
                access_token="a",
                refresh_token="r",
                cloud_id="c",
                expires_at=1.0,
            )

        cmd = captured[0]
        assert "--vault" in cmd
        assert "VAULT-UUID" in cmd
        # --vault must appear immediately before the value.
        idx = cmd.index("--vault")
        assert cmd[idx + 1] == "VAULT-UUID"

    def test_verify_refresh_token_round_trips_via_op_read(self):
        """verify_refresh_token re-reads the refresh_token field and asserts match."""
        mod = _load_module()

        captured: list[list[str]] = []

        def fake_run(cmd, **_kwargs):
            captured.append(list(cmd))
            result = MagicMock()
            result.stdout = "PERSISTED-TOKEN\n"
            result.returncode = 0
            return result

        with patch("subprocess.run", side_effect=fake_run):
            mod.OnePasswordStore(vault="V", item="I").verify_refresh_token(
                "PERSISTED-TOKEN"
            )

        # Must invoke `op read` against the refresh_token field.
        assert captured[0][:2] == ["op", "read"]
        assert "refresh_token" in captured[0][2]

    def test_verify_refresh_token_raises_on_mismatch(self):
        """If 1Password returns a different value than we wrote, abort loudly."""
        mod = _load_module()

        def fake_run(*_a, **_k):
            result = MagicMock()
            result.stdout = "DIFFERENT-VALUE\n"
            result.returncode = 0
            return result

        with patch("subprocess.run", side_effect=fake_run):
            try:
                mod.OnePasswordStore(vault="V", item="I").verify_refresh_token(
                    "EXPECTED-TOKEN"
                )
            except mod.SecretStoreError as exc:
                assert (
                    "refresh_token" in str(exc).lower()
                    or "mismatch" in str(exc).lower()
                )
            else:
                raise AssertionError("expected SecretStoreError on round-trip mismatch")

    def test_lock_path_is_unique_per_item(self):
        """Same item UUID → same lock path; different items → different paths."""
        mod = _load_module()
        s1 = mod.OnePasswordStore(vault="A", item="ITEM-1")
        s2 = mod.OnePasswordStore(vault="B", item="ITEM-1")
        s3 = mod.OnePasswordStore(vault="A", item="ITEM-2")
        assert s1.lock_path == s2.lock_path
        assert s1.lock_path != s3.lock_path

    def test_env_store_has_no_lock_path(self):
        mod = _load_module()
        assert mod.EnvStore().lock_path is None

    def test_env_store_verify_is_noop(self):
        """EnvStore.verify_refresh_token does nothing (read-only store)."""
        mod = _load_module()
        # Should not raise, should not call subprocess.
        mod.EnvStore().verify_refresh_token("anything")
