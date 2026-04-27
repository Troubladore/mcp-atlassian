"""Tests for the scripts/oauth_authorize.py CLI script."""

import importlib.util
import json
import os
import sys
from unittest.mock import MagicMock, patch


def _load_script_module():
    """Load the oauth_authorize script as a module."""
    script_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "scripts", "oauth_authorize.py"
    )
    script_path = os.path.abspath(script_path)
    spec = importlib.util.spec_from_file_location("oauth_authorize", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestOAuthAuthorizeScript:
    """Tests for the oauth_authorize CLI script."""

    def test_dc_argument_parsing(self):
        """DC base_url is passed through to OAuthSetupArgs."""
        mod = _load_script_module()
        argv = [
            "prog",
            "--base-url",
            "https://jira.corp.example.com",
            "--client-id",
            "X",
            "--client-secret",
            "Y",
            "--redirect-uri",
            "http://localhost:8080/callback",
            "--scope",
            "WRITE",
        ]
        with patch.object(sys, "argv", argv):
            with patch.object(mod, "run_oauth_flow") as mock_flow:
                mock_flow.return_value = True
                result = mod.main()
        assert result == 0
        mock_flow.assert_called_once()
        args = mock_flow.call_args[0][0]
        assert args.base_url == "https://jira.corp.example.com"

    def test_cloud_base_url_clearing(self):
        """Cloud URL clears base_url so OAuthSetupArgs has base_url=None."""
        mod = _load_script_module()
        argv = [
            "prog",
            "--base-url",
            "https://company.atlassian.net",
            "--client-id",
            "X",
            "--client-secret",
            "Y",
            "--redirect-uri",
            "http://localhost:8080/callback",
            "--scope",
            "read:jira-work offline_access",
        ]
        with patch.object(sys, "argv", argv):
            with patch.object(mod, "run_oauth_flow") as mock_flow:
                mock_flow.return_value = True
                result = mod.main()
        assert result == 0
        mock_flow.assert_called_once()
        args = mock_flow.call_args[0][0]
        assert args.base_url is None

    def test_env_var_fallback_chain(self):
        """JIRA_OAUTH_CLIENT_ID takes priority over ATLASSIAN_OAUTH_CLIENT_ID."""
        mod = _load_script_module()
        argv = [
            "prog",
            "--client-secret",
            "Y",
            "--redirect-uri",
            "http://localhost:8080/callback",
            "--scope",
            "WRITE",
        ]
        env = {
            "JIRA_OAUTH_CLIENT_ID": "jira-id",
            "ATLASSIAN_OAUTH_CLIENT_ID": "atlassian-id",
        }
        with patch.object(sys, "argv", argv):
            with patch.dict(os.environ, env, clear=False):
                with patch.object(mod, "run_oauth_flow") as mock_flow:
                    mock_flow.return_value = True
                    result = mod.main()
        assert result == 0
        mock_flow.assert_called_once()
        args = mock_flow.call_args[0][0]
        assert args.client_id == "jira-id"

    def test_offline_access_warning_skipped_for_dc(self, caplog):
        """DC scope without offline_access does not log a warning."""
        mod = _load_script_module()
        argv = [
            "prog",
            "--base-url",
            "https://jira.corp.example.com",
            "--client-id",
            "X",
            "--client-secret",
            "Y",
            "--redirect-uri",
            "http://localhost:8080/callback",
            "--scope",
            "WRITE",
        ]
        with patch.object(sys, "argv", argv):
            with patch.object(mod, "run_oauth_flow") as mock_flow:
                mock_flow.return_value = True
                mod.main()
        # No warning about offline_access for DC
        assert "offline_access" not in caplog.text

    def test_no_persist_flag_propagates(self):
        """--no-persist sets OAuthSetupArgs.persist=False."""
        mod = _load_script_module()
        argv = [
            "prog",
            "--client-id",
            "X",
            "--client-secret",
            "Y",
            "--redirect-uri",
            "http://localhost:8080/callback",
            "--scope",
            "read:jira-work offline_access",
            "--no-persist",
        ]
        with patch.object(sys, "argv", argv):
            with patch.object(mod, "run_oauth_flow_returning_config") as mock_flow:
                mock_flow.return_value = None  # exit non-zero, skip stdout assertions
                mod.main()
        mock_flow.assert_called_once()
        args = mock_flow.call_args[0][0]
        assert args.persist is False

    def test_default_omits_no_persist(self):
        """Without --no-persist, OAuthSetupArgs.persist=True (back-compat)."""
        mod = _load_script_module()
        argv = [
            "prog",
            "--client-id",
            "X",
            "--client-secret",
            "Y",
            "--redirect-uri",
            "http://localhost:8080/callback",
            "--scope",
            "read:jira-work offline_access",
        ]
        with patch.object(sys, "argv", argv):
            with patch.object(mod, "run_oauth_flow") as mock_flow:
                mock_flow.return_value = True
                mod.main()
        mock_flow.assert_called_once()
        args = mock_flow.call_args[0][0]
        assert args.persist is True

    def test_no_persist_emits_json_to_stdout(self, capsys):
        """--no-persist on success emits JSON token block to stdout."""
        mod = _load_script_module()
        argv = [
            "prog",
            "--client-id",
            "X",
            "--client-secret",
            "Y",
            "--redirect-uri",
            "http://localhost:8080/callback",
            "--scope",
            "read:jira-work offline_access",
            "--no-persist",
        ]

        fake_config = MagicMock()
        fake_config.access_token = "fake-access"
        fake_config.refresh_token = "fake-refresh"
        fake_config.cloud_id = "fake-cloud"
        fake_config.expires_at = 9999999999.0
        fake_config.is_data_center = False
        fake_config.base_url = None

        with patch.object(sys, "argv", argv):
            with patch.object(mod, "run_oauth_flow_returning_config") as mock_flow:
                mock_flow.return_value = fake_config
                result = mod.main()

        assert result == 0
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert payload["access_token"] == "fake-access"
        assert payload["refresh_token"] == "fake-refresh"
        assert payload["cloud_id"] == "fake-cloud"

    def test_no_persist_failure_returns_nonzero(self):
        """--no-persist when flow returns None exits with code 1."""
        mod = _load_script_module()
        argv = [
            "prog",
            "--client-id",
            "X",
            "--client-secret",
            "Y",
            "--redirect-uri",
            "http://localhost:8080/callback",
            "--scope",
            "read:jira-work offline_access",
            "--no-persist",
        ]
        with patch.object(sys, "argv", argv):
            with patch.object(mod, "run_oauth_flow_returning_config") as mock_flow:
                mock_flow.return_value = None
                result = mod.main()
        assert result == 1
