import json
from unittest.mock import Mock

import pytest

from flin_gtm_mcp import __version__, auth


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    for key in ('FLIN_GTM_CLIENT_ID', 'FLIN_GTM_CLIENT_SECRET', 'FLIN_GTM_CREDENTIALS_FILE'):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(auth.Path, 'home', lambda: tmp_path)

    def forbidden(*args, **kwargs):
        pytest.fail('Local connection_status must not refresh, log in, write or call Google')

    for name in ('credentials', 'login', 'read_token', 'save_token', 'private_token_directory',
                 'GoogleTokenRequest'):
        monkeypatch.setattr(auth, name, forbidden)
    monkeypatch.setattr(auth.DesktopFlow, 'from_client_config', forbidden)


def configure(monkeypatch):
    monkeypatch.setenv('FLIN_GTM_CLIENT_ID', 'synthetic.apps.googleusercontent.com')
    monkeypatch.setenv('FLIN_GTM_CLIENT_SECRET', 'never-output-this-secret')


def test_missing_and_partial_configuration(monkeypatch, tmp_path):
    assert auth.connection_status()['configuration_status'] == 'incomplete'
    monkeypatch.setenv('FLIN_GTM_CLIENT_SECRET', 'never-output-this-secret')
    result = auth.connection_status()
    assert result['server_version'] == __version__
    assert result['auth_status'] == 'unauthenticated'
    assert result['live_access'] == 'not_checked'
    assert 'never-output' not in json.dumps(result)
    assert list(tmp_path.iterdir()) == []


def test_configured_without_login_makes_no_files(monkeypatch, tmp_path):
    configure(monkeypatch)
    result = auth.connection_status()
    assert result['configuration_status'] == 'configured'
    assert result['auth_status'] == 'unauthenticated'
    assert 'gtm_authenticate' in result['next_step']
    assert list(tmp_path.iterdir()) == []


def test_existing_token_is_unverified_and_untouched(monkeypatch):
    configure(monkeypatch)
    token = auth.token_file(auth.config())
    token.parent.mkdir(parents=True)
    token.write_text('unverified-sensitive-token-even-if-invalid')
    token.chmod(0o640)
    before = token.stat()
    result = auth.connection_status()
    assert result['auth_status'] == 'unknown'
    assert result['live_access'] == 'not_checked'
    assert result['configuration_status'] == 'configured'
    assert 'gtm_list_accounts' in result['next_step']
    assert 'sensitive-token' not in json.dumps(result)
    assert token.stat().st_mode == before.st_mode
    assert token.stat().st_mtime_ns == before.st_mtime_ns
    assert token.read_text() == 'unverified-sensitive-token-even-if-invalid'


def test_legacy_json_still_configured_and_bad_json_is_redacted(monkeypatch, tmp_path):
    configure(monkeypatch)
    data = auth.config()
    for key in ('FLIN_GTM_CLIENT_ID', 'FLIN_GTM_CLIENT_SECRET'):
        monkeypatch.delenv(key)
    path = tmp_path / 'legacy.json'
    path.write_text(json.dumps(data))
    monkeypatch.setenv('FLIN_GTM_CREDENTIALS_FILE', str(path))
    assert auth.connection_status()['configuration_status'] == 'configured'
    path.write_text('never-output-this-secret')
    result = auth.connection_status()
    assert result['configuration_status'] == 'incomplete'
    assert 'never-output' not in json.dumps(result)


def test_service_account_is_local_only_and_parser_errors_redacted(monkeypatch):
    data = {'type': 'service_account', 'token_uri': auth.TOKEN_URI}
    monkeypatch.setattr(auth, 'config', lambda: data)
    parser = Mock(return_value=object())
    monkeypatch.setattr(auth.service_account.Credentials, 'from_service_account_info', parser)
    result = auth.connection_status()
    assert result['configuration_status'] == 'configured'
    assert result['auth_status'] == 'unknown' and result['live_access'] == 'not_checked'
    parser.assert_called_once_with(data, scopes=auth.SCOPES)
    parser.side_effect = ValueError('never-output-private-key')
    result = auth.connection_status()
    assert result['configuration_status'] == 'incomplete'
    assert 'private-key' not in json.dumps(result)
