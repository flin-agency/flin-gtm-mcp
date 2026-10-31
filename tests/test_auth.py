import json
import os
from unittest.mock import Mock

import pytest

from flin_gtm_mcp import auth


@pytest.fixture
def oauth(tmp_path, monkeypatch):
    data = {
        "installed": {
            "client_id": "test.apps.googleusercontent.com",
            "client_secret": "test-secret",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    file = tmp_path / "client.json"
    file.write_text(json.dumps(data))
    monkeypatch.setenv("FLIN_GTM_CREDENTIALS_FILE", str(file))
    monkeypatch.setattr(auth, "token_file", lambda _: tmp_path / "token.json")
    return data, file, tmp_path / "token.json"


def test_missing_config_is_actionable(monkeypatch):
    monkeypatch.delenv("FLIN_GTM_CREDENTIALS_FILE", raising=False)
    assert auth.status()["authenticated"] is False


def test_scope_escalation_rejected(oauth):
    _, _, token = oauth
    token.write_text(json.dumps({"scopes": [auth.SCOPE, "write-scope"]}))
    with pytest.raises(auth.AuthError, match="not read-only"):
        auth.credentials()


def test_untrusted_oauth_endpoint_rejected(oauth):
    data, file, _ = oauth
    data["installed"]["token_uri"] = "https://evil.example"
    file.write_text(json.dumps(data))
    with pytest.raises(auth.AuthError, match="endpoints"):
        auth.config()


def test_atomic_private_token_file(tmp_path):
    creds = Mock()
    creds.to_json.return_value = '{"token":"example"}'
    path = tmp_path / "private" / "token.json"
    auth.save_token(path, creds)
    assert json.loads(path.read_text())["token"] == "example"
    if os.name == "posix":
        assert path.stat().st_mode & 0o777 == 0o600
    assert list(path.parent.iterdir()) == [path]


def test_login_only_requests_readonly(oauth, monkeypatch):
    creds = Mock(scopes=auth.SCOPES, granted_scopes=auth.SCOPES)
    creds.to_json.return_value = "{}"
    flow = Mock()
    flow.run_local_server.return_value = creds
    factory = Mock(return_value=flow)
    monkeypatch.setattr(auth.InstalledAppFlow, "from_client_config", factory)
    assert auth.login()["authenticated"]
    assert factory.call_args.kwargs["scopes"] == [auth.SCOPE]
    assert flow.run_local_server.call_args.kwargs["include_granted_scopes"] == "false"


def test_login_error_does_not_expose_secret(oauth, monkeypatch):
    monkeypatch.setattr(
        auth.InstalledAppFlow, "from_client_config", Mock(side_effect=ValueError("secret"))
    )
    with pytest.raises(auth.AuthError) as error:
        auth.login()
    assert "secret" not in str(error.value)
