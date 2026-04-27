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
from unittest.mock import patch


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
    def test_errors_when_required_env_var_missing(self, caplog):
        """Missing env vars produce a clear error and non-zero exit."""
        import logging

        mod = _load_script_module()
        argv = ["prog"]
        # Missing ATLASSIAN_OAUTH_CLIENT_SECRET
        env = {
            k: v
            for k, v in REQUIRED_ENV.items()
            if k != "ATLASSIAN_OAUTH_CLIENT_SECRET"
        }
        with caplog.at_level(logging.ERROR):
            with patch.object(sys, "argv", argv):
                with patch.dict(os.environ, env, clear=True):
                    rc = mod.main()
        assert rc != 0
        assert "ATLASSIAN_OAUTH_CLIENT_SECRET" in caplog.text

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
