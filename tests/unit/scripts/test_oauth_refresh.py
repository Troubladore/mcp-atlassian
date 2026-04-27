"""Tests for the scripts/oauth_refresh.py CLI script.

The refresh helper takes a long-lived refresh_token and mints a fresh
access_token without persisting anything to disk or the OS keyring.
Two output modes:

- Default: JSON token block to stdout (callers pipe into ``op item edit``
  or similar to update external storage).
- ``--exec CMD ARG...``: sets ``CLOUD_E2E_OAUTH_ACCESS_TOKEN`` and
  ``CLOUD_E2E_OAUTH_CLOUD_ID`` in the child environment and execs the
  command. Used to wrap pytest invocations for the BYO OAuth E2E suite.
"""

import importlib.util
import json
import os
import sys
from unittest.mock import MagicMock, patch


def _load_script_module():
    script_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "scripts", "oauth_refresh.py"
    )
    script_path = os.path.abspath(script_path)
    spec = importlib.util.spec_from_file_location("oauth_refresh", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


REQUIRED_ENV = {
    "ATLASSIAN_OAUTH_CLIENT_ID": "test-client-id",
    "ATLASSIAN_OAUTH_CLIENT_SECRET": "test-client-secret",
    "CLOUD_E2E_OAUTH_REFRESH_TOKEN": "test-refresh-token",
    "CLOUD_E2E_OAUTH_CLOUD_ID": "test-cloud-id",
}


class TestOAuthRefreshScript:
    def test_errors_when_required_env_var_missing(self):
        """Missing env vars produce a clear error and non-zero exit."""
        mod = _load_script_module()
        argv = ["prog"]
        env = {
            k: v
            for k, v in REQUIRED_ENV.items()
            if k != "ATLASSIAN_OAUTH_CLIENT_SECRET"
        }
        with patch.object(sys, "argv", argv):
            with patch.dict(os.environ, env, clear=True):
                with patch.object(mod.logger, "error") as mock_error:
                    rc = mod.main()
        assert rc != 0
        # Logger called with format-string + args, not pre-formatted.
        all_messages = " ".join(
            (call.args[0] % call.args[1:]) if len(call.args) > 1 else str(call.args[0])
            for call in mock_error.call_args_list
        )
        assert "ATLASSIAN_OAUTH_CLIENT_SECRET" in all_messages

    def test_emits_refreshed_token_as_json(self, capsys):
        """Default mode prints a JSON token block to stdout."""
        mod = _load_script_module()
        argv = ["prog"]

        def fake_refresh(self):
            self.access_token = "fresh-access"
            self.refresh_token = "rotated-refresh"
            self.expires_at = 9999.0
            return True

        with patch.object(sys, "argv", argv):
            with patch.dict(os.environ, REQUIRED_ENV, clear=True):
                with patch(
                    "src.mcp_atlassian.utils.oauth.OAuthConfig.refresh_access_token",
                    fake_refresh,
                ):
                    rc = mod.main()

        assert rc == 0
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert payload["access_token"] == "fresh-access"
        assert payload["refresh_token"] == "rotated-refresh"
        assert payload["cloud_id"] == "test-cloud-id"

    def test_refresh_failure_returns_nonzero(self):
        """When refresh_access_token returns False, exit non-zero."""
        mod = _load_script_module()
        argv = ["prog"]

        def fake_refresh(self):
            return False

        with patch.object(sys, "argv", argv):
            with patch.dict(os.environ, REQUIRED_ENV, clear=True):
                with patch(
                    "src.mcp_atlassian.utils.oauth.OAuthConfig.refresh_access_token",
                    fake_refresh,
                ):
                    rc = mod.main()
        assert rc != 0

    def test_exec_with_no_command_errors_before_refresh(self, caplog):
        """--exec with no command must reject early, before consuming refresh token.

        argparse.REMAINDER produces args.exec == [] when --exec is passed
        with nothing after it. Falling through to default JSON mode would
        consume (and rotate) the refresh token while silently printing it
        to a terminal the caller didn't intend to capture.
        """
        import logging

        mod = _load_script_module()
        argv = ["prog", "--exec"]

        refresh_calls = []

        def fake_refresh(self):
            refresh_calls.append(1)
            return True

        with caplog.at_level(logging.ERROR):
            with patch.object(sys, "argv", argv):
                with patch.dict(os.environ, REQUIRED_ENV, clear=True):
                    with patch(
                        "src.mcp_atlassian.utils.oauth.OAuthConfig.refresh_access_token",
                        fake_refresh,
                    ):
                        rc = mod.main()

        assert rc != 0
        assert refresh_calls == []
        assert "--exec requires a command" in caplog.text

    def test_store_1password_full_flow_refresh_persist_exec(self):
        """--store 1password reads via op, refreshes, writes rotated tokens, execs."""
        import subprocess

        mod = _load_script_module()
        argv = [
            "prog",
            "--store",
            "1password",
            "--op-vault",
            "VAULT-UUID",
            "--op-item-id",
            "ITEM-UUID",
            "--exec",
            "pytest",
            "-k",
            "byo_oauth",
        ]

        op_calls: list[tuple[list[str], dict[str, object]]] = []
        refresh_read_count = [0]

        def fake_run(cmd, **kwargs):
            op_calls.append((list(cmd), dict(kwargs)))
            result = MagicMock()
            if list(cmd[:2]) == ["op", "read"]:
                ref = cmd[2]
                if ref.endswith("/refresh_token"):
                    refresh_read_count[0] += 1
                    # First read: stored value. Second read: verify-after-write.
                    result.stdout = (
                        "ROTATED-refresh\n"
                        if refresh_read_count[0] >= 2
                        else "stored-refresh_token\n"
                    )
                else:
                    result.stdout = f"stored-{ref.split('/')[-1]}\n"
            result.returncode = 0
            return result

        def fake_refresh(self):
            self.access_token = "fresh-access"
            self.refresh_token = "ROTATED-refresh"
            self.expires_at = 1234.5
            return True

        execvpe_calls: list[tuple] = []

        with patch.object(sys, "argv", argv):
            with patch.dict(os.environ, {}, clear=True):
                with patch("subprocess.run", side_effect=fake_run):
                    with patch(
                        "src.mcp_atlassian.utils.oauth.OAuthConfig.refresh_access_token",
                        fake_refresh,
                    ):
                        with patch(
                            "os.execvpe",
                            side_effect=lambda *a, **k: execvpe_calls.append(a),
                        ):
                            mod.main()

        # Five `op read` calls (4 initial fields + 1 verify-after-write) and
        # one `op item edit`.
        read_cmds = [cmd for cmd, _ in op_calls if cmd[:2] == ["op", "read"]]
        edit_cmds = [cmd for cmd, _ in op_calls if cmd[:3] == ["op", "item", "edit"]]
        assert len(read_cmds) == 5
        assert len(edit_cmds) == 1
        edit_cmd = edit_cmds[0]
        # Rotated refresh_token must appear as discrete arg-list element.
        assert any("refresh_token=ROTATED-refresh" in arg for arg in edit_cmd)
        assert any("access_token=fresh-access" in arg for arg in edit_cmd)
        # No invocation may use shell=True.
        assert all(kw.get("shell", False) is False for _, kw in op_calls)
        # `op item edit` must use stdin=DEVNULL.
        edit_kwargs = next(
            kw for cmd, kw in op_calls if cmd[:3] == ["op", "item", "edit"]
        )
        assert edit_kwargs["stdin"] == subprocess.DEVNULL
        # Then exec'd pytest with the fresh access token.
        assert execvpe_calls
        execvpe_args = execvpe_calls[0]
        assert execvpe_args[0] == "pytest"
        assert execvpe_args[2]["CLOUD_E2E_OAUTH_ACCESS_TOKEN"] == "fresh-access"

    def test_store_1password_missing_uuids_errors(self):
        """--store 1password without --op-vault/--op-item-id errors clearly."""
        mod = _load_script_module()
        argv = ["prog", "--store", "1password"]

        with patch.object(sys, "argv", argv):
            with patch.dict(os.environ, {}, clear=True):
                with patch.object(mod.logger, "error") as mock_error:
                    rc = mod.main()
        assert rc != 0
        all_messages = " ".join(
            str(call.args[0]) % call.args[1:]
            if len(call.args) > 1
            else str(call.args[0])
            for call in mock_error.call_args_list
        )
        assert "1password" in all_messages.lower()

    def test_stale_refresh_token_with_readonly_store_returns_error(self):
        """With env store (read-only), refresh failure returns nonzero with guidance."""
        mod = _load_script_module()
        argv = ["prog", "--store", "env"]

        def fake_refresh(self):
            return False

        with patch.object(sys, "argv", argv):
            with patch.dict(os.environ, REQUIRED_ENV, clear=True):
                with patch(
                    "src.mcp_atlassian.utils.oauth.OAuthConfig.refresh_access_token",
                    fake_refresh,
                ):
                    with patch.object(mod.logger, "error") as mock_error:
                        rc = mod.main()
        assert rc != 0
        all_messages = " ".join(
            str(call.args[0]) % call.args[1:]
            if len(call.args) > 1
            else str(call.args[0])
            for call in mock_error.call_args_list
        )
        assert "oauth_authorize.py" in all_messages

    def test_env_store_with_exec_refuses_without_allow_rotation_loss(self):
        """--store env --exec refuses by default — rotation would be lost."""
        mod = _load_script_module()
        argv = ["prog", "--store", "env", "--exec", "pytest"]

        refresh_calls = []

        def fake_refresh(self):
            refresh_calls.append(1)
            return True

        with patch.object(sys, "argv", argv):
            with patch.dict(os.environ, REQUIRED_ENV, clear=True):
                with patch(
                    "src.mcp_atlassian.utils.oauth.OAuthConfig.refresh_access_token",
                    fake_refresh,
                ):
                    with patch.object(mod.logger, "error") as mock_error:
                        rc = mod.main()
        assert rc != 0
        assert refresh_calls == []
        all_messages = " ".join(str(call.args[0]) for call in mock_error.call_args_list)
        assert "rotation" in all_messages.lower()

    def test_env_store_with_exec_and_allow_flag_proceeds(self):
        """--allow-rotation-loss escape hatch lets --exec run on env store."""
        mod = _load_script_module()
        argv = [
            "prog",
            "--store",
            "env",
            "--exec",
            "pytest",
            "--allow-rotation-loss",
        ]

        def fake_refresh(self):
            self.access_token = "fresh"
            self.refresh_token = "rotated"
            self.expires_at = 1.0
            return True

        execvpe_calls: list = []
        # --exec eats the rest of argv via REMAINDER, so --allow-rotation-loss
        # must be placed BEFORE --exec to be parsed as a flag.
        argv = [
            "prog",
            "--store",
            "env",
            "--allow-rotation-loss",
            "--exec",
            "pytest",
        ]

        with patch.object(sys, "argv", argv):
            with patch.dict(os.environ, REQUIRED_ENV, clear=True):
                with patch(
                    "src.mcp_atlassian.utils.oauth.OAuthConfig.refresh_access_token",
                    fake_refresh,
                ):
                    with patch(
                        "os.execvpe",
                        side_effect=lambda *a, **k: execvpe_calls.append(a),
                    ):
                        mod.main()
        assert execvpe_calls

    def test_1password_store_calls_verify_after_write(self):
        """After op item edit, OnePasswordStore.verify_refresh_token must run."""
        mod = _load_script_module()
        argv = [
            "prog",
            "--store",
            "1password",
            "--op-vault",
            "V",
            "--op-item-id",
            "I",
        ]

        def fake_run(cmd, **_kwargs):
            result = MagicMock()
            if list(cmd[:2]) == ["op", "read"]:
                # Returns the rotated value on the verify-after-write call
                # so verify passes; for initial reads, return placeholders.
                field = cmd[2].split("/")[-1]
                if field == "refresh_token":
                    # First read → original; second read (verify) → rotated.
                    result.stdout = (
                        "ROTATED-rt\n"
                        if "verify-marker" in str(_kwargs.get("_marker", ""))
                        else f"original-{field}\n"
                    )
                else:
                    result.stdout = f"value-of-{field}\n"
            result.returncode = 0
            return result

        # Simpler approach: track call order and serve the right value per call.
        read_calls: list[str] = []

        def fake_run_v2(cmd, **_kwargs):
            result = MagicMock()
            result.returncode = 0
            if list(cmd[:2]) == ["op", "read"]:
                ref = cmd[2]
                read_calls.append(ref)
                if ref.endswith("/refresh_token"):
                    # First refresh_token read → stored; second (verify) → rotated.
                    refresh_reads = [
                        r for r in read_calls if r.endswith("/refresh_token")
                    ]
                    result.stdout = (
                        "ROTATED-rt\n" if len(refresh_reads) > 1 else "stored-rt\n"
                    )
                else:
                    result.stdout = f"value-of-{ref.split('/')[-1]}\n"
            return result

        def fake_refresh(self):
            self.access_token = "ATOK"
            self.refresh_token = "ROTATED-rt"
            self.expires_at = 9999.0
            return True

        with patch.object(sys, "argv", argv):
            with patch.dict(os.environ, {}, clear=True):
                with patch("subprocess.run", side_effect=fake_run_v2):
                    with patch(
                        "src.mcp_atlassian.utils.oauth.OAuthConfig.refresh_access_token",
                        fake_refresh,
                    ):
                        rc = mod.main()
        assert rc == 0
        # Two refresh_token reads: initial credentials read + verify-after-write.
        refresh_reads = [r for r in read_calls if r.endswith("/refresh_token")]
        assert len(refresh_reads) == 2

    def test_1password_store_aborts_when_verify_after_write_mismatches(self):
        """If verify reads a different value than we wrote, abort with non-zero exit."""
        mod = _load_script_module()
        argv = [
            "prog",
            "--store",
            "1password",
            "--op-vault",
            "V",
            "--op-item-id",
            "I",
            "--exec",
            "pytest",
        ]

        read_call_count: list[int] = [0]

        def fake_run(cmd, **_kwargs):
            result = MagicMock()
            result.returncode = 0
            if list(cmd[:2]) == ["op", "read"]:
                ref = cmd[2]
                if ref.endswith("/refresh_token"):
                    read_call_count[0] += 1
                    # Verify (second refresh_token read) returns a DIFFERENT value.
                    if read_call_count[0] >= 2:
                        result.stdout = "WRONG-VALUE\n"
                    else:
                        result.stdout = "stored-rt\n"
                else:
                    result.stdout = f"value-of-{ref.split('/')[-1]}\n"
            return result

        def fake_refresh(self):
            self.access_token = "ATOK"
            self.refresh_token = "ROTATED-rt"
            self.expires_at = 9999.0
            return True

        execvpe_calls: list = []

        with patch.object(sys, "argv", argv):
            with patch.dict(os.environ, {}, clear=True):
                with patch("subprocess.run", side_effect=fake_run):
                    with patch(
                        "src.mcp_atlassian.utils.oauth.OAuthConfig.refresh_access_token",
                        fake_refresh,
                    ):
                        with patch(
                            "os.execvpe",
                            side_effect=lambda *a, **k: execvpe_calls.append(a),
                        ):
                            rc = mod.main()
        assert rc != 0
        assert execvpe_calls == []

    def test_lock_acquired_around_critical_section(self):
        """When the store has a lock_path, fcntl.flock(LOCK_EX) is called.

        Defends against two local processes consuming the same refresh_token
        concurrently and racing the write-back.
        """
        import fcntl

        mod = _load_script_module()
        argv = [
            "prog",
            "--store",
            "1password",
            "--op-vault",
            "V",
            "--op-item-id",
            "I",
        ]

        flock_calls: list[int] = []

        def fake_flock(_fd, op):
            flock_calls.append(op)

        def fake_run(cmd, **_kwargs):
            result = MagicMock()
            result.returncode = 0
            if list(cmd[:2]) == ["op", "read"]:
                result.stdout = f"value-of-{cmd[2].split('/')[-1]}\n"
            return result

        def fake_refresh(self):
            self.access_token = "a"
            self.refresh_token = "r"
            self.expires_at = 1.0
            return True

        with patch.object(sys, "argv", argv):
            with patch.dict(os.environ, {}, clear=True):
                with patch("subprocess.run", side_effect=fake_run):
                    with patch(
                        "src.mcp_atlassian.utils.oauth.OAuthConfig.refresh_access_token",
                        fake_refresh,
                    ):
                        with patch("fcntl.flock", side_effect=fake_flock):
                            mod.main()
        assert fcntl.LOCK_EX in flock_calls

    def test_stale_refresh_token_with_writable_store_invokes_authorize(self):
        """1P store + refresh failure → authorize flow runs and persists new tokens."""
        mod = _load_script_module()
        argv = [
            "prog",
            "--store",
            "1password",
            "--op-vault",
            "V",
            "--op-item-id",
            "I",
        ]

        verify_marker = ["pre"]

        def fake_run(cmd, **kwargs):
            result = MagicMock()
            if list(cmd[:2]) == ["op", "read"]:
                ref = cmd[2]
                if ref.endswith("/refresh_token") and verify_marker[0] == "post":
                    # Verify-after-write call returns the rotated token.
                    result.stdout = "post-authorize-refresh\n"
                else:
                    field = ref.split("/")[-1]
                    result.stdout = f"stored-{field}\n"
            result.returncode = 0
            return result

        def fake_refresh(self):
            return False

        new_config = MagicMock()
        new_config.access_token = "post-authorize-access"
        new_config.refresh_token = "post-authorize-refresh"
        new_config.cloud_id = "post-authorize-cloud"
        new_config.expires_at = 9999.0

        # Authorize flow returning new_config flips the marker so subsequent
        # refresh_token reads (verify-after-write) return the rotated value.
        def fake_authorize(*_a, **_k):
            verify_marker[0] = "post"
            return new_config

        with patch.object(sys, "argv", argv):
            with patch.dict(
                os.environ,
                {"ATLASSIAN_OAUTH_SCOPE": "read:jira-work offline_access"},
                clear=True,
            ):
                with patch("subprocess.run", side_effect=fake_run):
                    with patch(
                        "src.mcp_atlassian.utils.oauth.OAuthConfig.refresh_access_token",
                        fake_refresh,
                    ):
                        with patch.object(
                            mod,
                            "run_oauth_flow_returning_config",
                            side_effect=fake_authorize,
                        ) as mock_authorize:
                            rc = mod.main()

        assert rc == 0
        mock_authorize.assert_called_once()

    def test_exec_mode_sets_env_and_execs(self):
        """--exec passes refreshed access_token + cloud_id into child env."""
        mod = _load_script_module()
        # env store + --exec requires --allow-rotation-loss (the rotated
        # refresh_token cannot be persisted by the env store).
        argv = [
            "prog",
            "--allow-rotation-loss",
            "--exec",
            "pytest",
            "-k",
            "byo_oauth",
        ]

        def fake_refresh(self):
            self.access_token = "fresh-access"
            self.refresh_token = "rotated-refresh"
            self.expires_at = 9999.0
            return True

        recorded: dict[str, object] = {}

        def fake_execvpe(file: str, argv_: list[str], env: dict[str, str]) -> None:
            recorded["file"] = file
            recorded["argv"] = argv_
            recorded["env"] = env

        with patch.object(sys, "argv", argv):
            with patch.dict(os.environ, REQUIRED_ENV, clear=True):
                with patch(
                    "src.mcp_atlassian.utils.oauth.OAuthConfig.refresh_access_token",
                    fake_refresh,
                ):
                    with patch("os.execvpe", side_effect=fake_execvpe):
                        mod.main()

        assert recorded["file"] == "pytest"
        assert recorded["argv"] == ["pytest", "-k", "byo_oauth"]
        env = recorded["env"]
        assert env["CLOUD_E2E_OAUTH_ACCESS_TOKEN"] == "fresh-access"
        assert env["CLOUD_E2E_OAUTH_CLOUD_ID"] == "test-cloud-id"
