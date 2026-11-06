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


def test_token_symlink_and_hardlink_rejected(tmp_path):
    outside = tmp_path / 'outside.json'
    outside.write_text('{"token":"do-not-read"}')
    link = tmp_path / 'token.json'
    link.symlink_to(outside)
    with pytest.raises(OSError):
        auth.read_token(link)
    link.unlink()
    os.link(outside, link)
    with pytest.raises(auth.AuthError, match='private, regular'):
        auth.read_token(link)


def test_symlink_directory_rejected(tmp_path):
    real = tmp_path / 'real'
    real.mkdir()
    link = tmp_path / 'linked'
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(auth.AuthError, match='real directory'):
        auth.save_token(link / 'token.json', Mock())
    assert not list(real.iterdir())


def test_existing_token_permissions_repaired(tmp_path):
    root = tmp_path / 'cache'
    root.mkdir(mode=0o755)
    token = root / 'token.json'
    token.write_text('{}')
    token.chmod(0o644)
    assert auth.read_token(token) == {}
    assert root.stat().st_mode & 0o777 == 0o700
    assert token.stat().st_mode & 0o777 == 0o600


def test_token_transport_blocks_arbitrary_urls_and_redirects():
    session = Mock()
    request = auth.GoogleTokenRequest(session=session)
    for url in ('https://evil.example/token', auth.TOKEN_URI + '?redirect=1'):
        with pytest.raises(auth.AuthError):
            request(url, method='POST', body=b'secret')
    session.request.assert_not_called()
    request(auth.TOKEN_URI, method='POST', body=b'secret', timeout=None, allow_redirects=True)
    assert session.request.call_args.kwargs['timeout'] == 30
    assert session.request.call_args.kwargs['allow_redirects'] is False


def test_real_flow_uses_pkce_and_bounded_token_exchange(oauth, monkeypatch):
    from urllib.parse import parse_qs, urlparse

    data, _, _ = oauth
    flow = auth.DesktopFlow.from_client_config(data, scopes=auth.SCOPES,
                                              autogenerate_code_verifier=True)
    url, state = flow.authorization_url()
    params = parse_qs(urlparse(url).query)
    assert params['code_challenge_method'] == ['S256'] and state
    assert params['code_challenge'] and flow.code_verifier
    fetch = Mock()
    monkeypatch.setattr(flow.oauth2session, 'fetch_token', fetch)
    flow.fetch_token(code='example')
    assert fetch.call_args.kwargs['timeout'] == 30
    assert fetch.call_args.kwargs['allow_redirects'] is False
    assert fetch.call_args.kwargs['code_verifier'] == flow.code_verifier


def test_scope_escalation_on_refresh_never_saved(oauth, monkeypatch):
    data, _, token = oauth
    token.write_text(json.dumps({'scopes': auth.SCOPES,
                                'client_id': data['installed']['client_id']}))
    creds = Mock(valid=False, refresh_token='example', scopes=auth.SCOPES,
                 granted_scopes=auth.SCOPES + ['write-scope'])
    monkeypatch.setattr(auth.Credentials, 'from_authorized_user_info', Mock(return_value=creds))
    save = Mock()
    monkeypatch.setattr(auth, 'save_token', save)
    with pytest.raises(auth.AuthError, match='Unexpected OAuth scopes'):
        auth.credentials()
    save.assert_not_called()


@pytest.mark.parametrize('value', [None, [], {}, 42, ''])
def test_invalid_client_identity_is_safe(oauth, value):
    data, file, _ = oauth
    data['installed']['client_id'] = value
    file.write_text(json.dumps(data))
    assert auth.status()['authenticated'] is False
