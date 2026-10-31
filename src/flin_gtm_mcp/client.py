"""Fixed, validated GET-only surface for Google Tag Manager API v2."""

import re

import requests
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import AuthorizedSession

from .auth import credentials

ACCOUNT = r"accounts/[0-9]+"
CONTAINER = ACCOUNT + r"/containers/[0-9]+"
WORKSPACE = CONTAINER + r"/workspaces/[0-9]+"
COLLECTIONS = {
    "accounts": ("", "account"),
    "containers": (ACCOUNT, "container"),
    "workspaces": (CONTAINER, "workspace"),
    "tags": (WORKSPACE, "tag"),
    "triggers": (WORKSPACE, "trigger"),
    "variables": (WORKSPACE, "variable"),
    "folders": (WORKSPACE, "folder"),
    "built_in_variables": (WORKSPACE, "builtInVariable"),
    "version_headers": (CONTAINER, "containerVersionHeader"),
}
GET_PATTERNS = [
    ACCOUNT,
    CONTAINER,
    WORKSPACE,
    *(WORKSPACE + "/" + kind + r"/[0-9]+" for kind in ("tags", "triggers", "variables", "folders")),
    CONTAINER + r"/versions/[0-9]+",
    CONTAINER + r"/versions:live",
]
LIST_PATTERNS = [
    parent + "/" + kind if parent else kind for kind, (parent, _) in COLLECTIONS.items()
]


class GTMError(RuntimeError):
    pass


def validate(value: str, pattern: str) -> None:
    if not re.fullmatch(pattern, value):
        raise GTMError(
            "Invalid GTM resource path. Use numeric IDs and the documented relative path."
        )


class GTMClient:
    def __init__(self, session=None):
        self._session = session

    def _get(self, path: str, params=None) -> dict:
        if not any(re.fullmatch(pattern, path) for pattern in GET_PATTERNS + LIST_PATTERNS):
            raise GTMError("GTM operation is not on the read-only allowlist.")
        session = self._session or AuthorizedSession(credentials())
        try:
            response = session.get(
                "https://tagmanager.googleapis.com/tagmanager/v2/" + path,
                params=params or {},
                timeout=30,
                allow_redirects=False,
            )
            errors = {
                401: "Google login expired. Run login again.",
                403: "Access denied or quota exceeded. Check GTM access, API enablement and quota.",
                404: "GTM resource not found or unavailable to this account.",
                429: "Google API quota exceeded. Retry later.",
            }
            if response.status_code != 200:
                raise GTMError(
                    errors.get(
                        response.status_code,
                        f"Google API request failed (HTTP {response.status_code}).",
                    )
                )
            result = response.json()
            if not isinstance(result, dict):
                raise GTMError("Unexpected Google API response.")
            return result
        except requests.RequestException:
            raise GTMError("Google API connection failed or timed out.") from None
        except GoogleAuthError:
            raise GTMError(
                "Google authentication failed. Check credentials or log in again."
            ) from None
        except ValueError:
            raise GTMError("Invalid JSON response from Google API.") from None
        finally:
            if self._session is None:
                session.close()

    def list(self, kind: str, parent: str = "", page_token: str | None = None) -> dict:
        if kind not in COLLECTIONS:
            raise GTMError("Unsupported collection.")
        pattern, key = COLLECTIONS[kind]
        validate(parent, pattern)
        path = parent + "/" + kind if parent else kind
        data = self._get(path, {"pageToken": page_token} if page_token else {})
        return {
            "items": data.get(key, []),
            "next_page_token": data.get("nextPageToken"),
            "parent": parent,
            "collection": kind,
        }

    def get(self, path: str, pattern: str) -> dict:
        validate(path, pattern)
        return self._get(path)
