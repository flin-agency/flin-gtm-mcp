"""Explicit local OAuth login; credentials never enter tool responses."""

import hashlib
import json
import logging
import os
import stat
import sys
import tempfile
import threading
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPE = "https://www.googleapis.com/auth/tagmanager.readonly"
SCOPES = [SCOPE]
# Public endpoint, not a password.
TOKEN_URI = "https://oauth2.googleapis.com/token"  # nosec B105
# The OAuth callback handler logs URLs with authorization codes at INFO.
logging.getLogger("google_auth_oauthlib.flow").setLevel(logging.WARNING)
_LOCK = threading.RLock()


class AuthError(RuntimeError):
    pass


class GoogleTokenRequest(Request):
    """Never forward credential-bearing refresh requests to another destination."""

    def __call__(self, url, method="GET", body=None, headers=None, **kwargs):
        if url != TOKEN_URI or method != "POST":
            raise AuthError("Unsupported Google token request.")
        kwargs.update(timeout=30, allow_redirects=False)
        return super().__call__(url, method=method, body=body, headers=headers, **kwargs)


class DesktopFlow(InstalledAppFlow):
    def fetch_token(self, **kwargs):
        kwargs.update(timeout=30, allow_redirects=False)
        return super().fetch_token(**kwargs)


def credentials_file() -> Path:
    value = os.environ.get("FLIN_GTM_CREDENTIALS_FILE", "")
    if not value:
        raise AuthError(
            "Enter your OAuth client ID and client secret in the extension settings, "
            "or configure FLIN_GTM_CREDENTIALS_FILE with your Google Desktop OAuth JSON."
        )
    return Path(value).expanduser()


def config() -> dict:
    client_id = os.environ.get("FLIN_GTM_CLIENT_ID", "").strip()
    client_secret = os.environ.get("FLIN_GTM_CLIENT_SECRET", "").strip()
    if client_id or client_secret:
        if not client_id or not client_secret:
            raise AuthError("Enter both OAuth client ID and client secret in the extension settings.")
        data = {"installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": TOKEN_URI,
        }}
    else:
        try:
            data = json.loads(credentials_file().read_text())
        except (OSError, ValueError):
            raise AuthError("Cannot read Google credentials JSON. Check the configured file.") from None
    if not isinstance(data, dict):
        raise AuthError("Google credentials must be a JSON object.")
    if data.get("type") == "service_account":
        # Restrict token destinations even for locally supplied credential files.
        if (data.get("token_uri") != TOKEN_URI
                or data.get("universe_domain", "googleapis.com") != "googleapis.com"):
            raise AuthError("Unsupported service account token endpoint.")
    else:
        installed = data.get("installed", {})
        if (not isinstance(installed, dict)
                or not isinstance(installed.get("client_id"), str)
                or not installed["client_id"]
                or not isinstance(installed.get("client_secret"), str)
                or not installed["client_secret"]):
            raise AuthError(
                "Use a Google OAuth client of type Desktop app (installed), not Web app."
            )
        if (
            installed.get("auth_uri") != "https://accounts.google.com/o/oauth2/auth"
            or installed.get("token_uri") != TOKEN_URI
        ):
            raise AuthError("Unsupported Google OAuth endpoints.")
    return data


def token_file(data: dict) -> Path:
    identity = data["installed"]["client_id"]
    key = hashlib.sha256(identity.encode()).hexdigest()[:20]
    root = Path.home() / "Library/Application Support/flin-gtm-mcp"
    if os.name != "posix" or not sys.platform.startswith("darwin"):
        root = Path.home() / ".config/flin-gtm-mcp"
    return root / f"token-{key}.json"


def private_token_directory(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = path.parent.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise AuthError("Token directory must be a real directory owned by the current user.")
    path.parent.chmod(0o700)


def read_token(path: Path) -> dict:
    private_token_directory(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd) as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
            raise AuthError("Token cache must be a private, regular file owned by the current user.")
        os.fchmod(source.fileno(), 0o600)
        return json.load(source)


def save_token(path: Path, creds: Credentials) -> None:
    private_token_directory(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".token-")
    try:
        with os.fdopen(fd, "w") as output:
            output.write(creds.to_json())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def login() -> dict:
    """Open Google's consent screen only on an explicit login request."""
    with _LOCK:
        data = config()
        if data.get("type") == "service_account":
            credentials()  # Validate before reporting success.
            return {"authenticated": True, "method": "service_account", "scope": SCOPE}
        try:
            flow = DesktopFlow.from_client_config(
                data, scopes=SCOPES, autogenerate_code_verifier=True,
            )
            creds = flow.run_local_server(
                host="127.0.0.1",
                port=0,
                open_browser=True,
                timeout_seconds=120,
                authorization_prompt_message="",
                success_message="flin GTM connected. Close this tab.",
                access_type="offline",
                prompt="consent",
                include_granted_scopes="false",
            )
            if not creds or not creds.has_scopes(SCOPES):
                raise AuthError("Read-only Google access was not granted.")
            if set(creds.granted_scopes or creds.scopes or []) != set(SCOPES):
                raise AuthError("Unexpected OAuth scopes. Revoke this app and reconnect read-only.")
            save_token(token_file(data), creds)
        except AuthError:
            raise
        except Exception:  # noqa: BLE001 -- auth boundary must never expose credential-bearing exceptions
            raise AuthError(
                "Google login failed or timed out. Retry login and complete browser consent."
            ) from None
        return {"authenticated": True, "method": "oauth", "scope": SCOPE}


def credentials():
    with _LOCK:
        data = config()
        if data.get("type") == "service_account":
            try:
                return service_account.Credentials.from_service_account_info(data, scopes=SCOPES)
            except Exception:  # noqa: BLE001 -- auth boundary must never expose credential-bearing exceptions
                raise AuthError("Invalid service account credentials.") from None
        path = token_file(data)
        try:
            stored = read_token(path)
            if set(stored.get("scopes", [])) != set(SCOPES):
                raise AuthError("Stored scopes are not read-only. Run login again.")
            if stored.get("client_id") != data["installed"]["client_id"]:
                raise AuthError("OAuth client mismatch. Run login again.")
            # Never trust token endpoint or client secret from the token cache.
            stored.update(
                token_uri=TOKEN_URI,
                client_secret=data["installed"].get("client_secret"),
                universe_domain="googleapis.com",
            )
            creds = Credentials.from_authorized_user_info(stored, scopes=SCOPES)
            if not creds.valid:
                if not creds.refresh_token:
                    raise AuthError("Google login required. Run flin-gtm-mcp login.")
                request = GoogleTokenRequest()
                try:
                    creds.refresh(request)
                finally:
                    request.session.close()
                if set(creds.granted_scopes or creds.scopes or []) != set(SCOPES):
                    raise AuthError("Unexpected OAuth scopes. Revoke this app and reconnect read-only.")
                save_token(path, creds)
            return creds
        except AuthError:
            raise
        except Exception:  # noqa: BLE001 -- auth boundary must never expose credential-bearing exceptions
            raise AuthError(
                "Google login missing or expired. Run flin-gtm-mcp login again."
            ) from None


def status() -> dict:
    try:
        credentials()
        return {"authenticated": True, "scope": SCOPE}
    except AuthError as exc:
        return {"authenticated": False, "message": str(exc), "scope": SCOPE}


def connection_status() -> dict:
    """Local inspection only: no token refresh, browser, API call or filesystem writes."""
    from . import __version__

    result = {
        "server_version": __version__,
        "configuration_status": "incomplete",
        "auth_status": "unauthenticated",
        "live_access": "not_checked",
        "next_step": "Enter both OAuth client ID and client secret in the extension settings; "
                     "for legacy configuration, check the credentials JSON file.",
    }
    try:
        data = config()
        if data.get("type") == "service_account":
            # Parse the key locally; constructing credentials does not obtain an access token.
            service_account.Credentials.from_service_account_info(data, scopes=SCOPES)
            result.update(configuration_status="configured", auth_status="unknown",
                          next_step="Call gtm_list_accounts to check live Google access.")
            return result
    except Exception:  # noqa: BLE001 -- never expose credential-bearing parser errors
        return result
    result["configuration_status"] = "configured"
    try:
        # Merely inspect presence: read_token/credentials would chmod, create dirs or refresh.
        token_file(data).lstat()
    except FileNotFoundError:
        result["next_step"] = "Request gtm_authenticate, complete Google consent, then " \
                              "call gtm_list_accounts to check live access."
        return result
    except OSError:
        result.update(auth_status="unknown",
                      next_step="Check local token cache access, then request gtm_authenticate.")
        return result
    result.update(auth_status="unknown",
                  next_step="Local login data is present but unverified. Call gtm_list_accounts "
                            "to check live access; reconnect with gtm_authenticate if required.")
    return result
