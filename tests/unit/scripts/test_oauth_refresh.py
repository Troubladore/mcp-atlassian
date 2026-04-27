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

    def test_write_cmd_runs_with_rotated_refresh_token_in_env(self):
        """--write-cmd receives the rotated refresh token via env vars."""
        mod = _load_script_module()
        argv = [
            "prog",
            "--write-cmd",
            "true",
            "--exec",
            "pytest",
        ]

        def fake_refresh(self):
            self.access_token = "fresh-access"
            self.refresh_token = "ROTATED-refresh"
            self.expires_at = 9999.0
            return True

        captured: dict[str, object] = {}

        def fake_subprocess_run(*args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            result = MagicMock()
            result.returncode = 0
            return result

        with patch.object(sys, "argv", argv):
            with patch.dict(os.environ, REQUIRED_ENV, clear=True):
                with patch(
                    "src.mcp_atlassian.utils.oauth.OAuthConfig.refresh_access_token",
                    fake_refresh,
                ):
                    with patch("subprocess.run", side_effect=fake_subprocess_run):
                        with patch("os.execvpe"):
                            mod.main()

        assert captured["args"][0] == "true"
        kwargs = captured["kwargs"]
        env = kwargs["env"]
        assert env["ATLASSIAN_OAUTH_ACCESS_TOKEN"] == "fresh-access"
        assert env["ATLASSIAN_OAUTH_REFRESH_TOKEN"] == "ROTATED-refresh"
        assert env["ATLASSIAN_OAUTH_CLOUD_ID"] == "test-cloud-id"
        assert env["ATLASSIAN_OAUTH_EXPIRES_AT"] == "9999.0"
        # stdin must be DEVNULL so `op item edit` doesn't try to parse
        # the parent's stdin as a JSON template.
        import subprocess

        assert kwargs["stdin"] == subprocess.DEVNULL

    def test_write_cmd_failure_aborts_before_exec(self, caplog):
        """If --write-cmd exits nonzero, --exec must not run."""
        import logging

        mod = _load_script_module()
        argv = ["prog", "--write-cmd", "false", "--exec", "pytest"]

        def fake_refresh(self):
            self.access_token = "fresh"
            self.refresh_token = "rotated"
            self.expires_at = 1.0
            return True

        exec_calls = []

        def fake_subprocess_run(*_args, **_kwargs):
            result = MagicMock()
            result.returncode = 7
            return result

        with caplog.at_level(logging.ERROR):
            with patch.object(sys, "argv", argv):
                with patch.dict(os.environ, REQUIRED_ENV, clear=True):
                    with patch(
                        "src.mcp_atlassian.utils.oauth.OAuthConfig.refresh_access_token",
                        fake_refresh,
                    ):
                        with patch("subprocess.run", side_effect=fake_subprocess_run):
                            with patch(
                                "os.execvpe",
                                side_effect=lambda *a, **k: exec_calls.append(a),
                            ):
                                rc = mod.main()

        assert rc == 7
        assert exec_calls == []
        assert "--write-cmd exited" in caplog.text

    def test_exec_mode_sets_env_and_execs(self):
        """--exec passes refreshed access_token + cloud_id into child env."""
        mod = _load_script_module()
        argv = ["prog", "--exec", "pytest", "-k", "byo_oauth"]

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
