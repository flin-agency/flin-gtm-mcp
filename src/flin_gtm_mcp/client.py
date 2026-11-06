"""Fixed read-only API surface, process-wide throttling and bounded pagination."""

import random
import re
import threading
import time

import requests
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import AuthorizedSession

from .auth import GoogleTokenRequest, credentials

ACCOUNT = r"accounts/[0-9]+"
CONTAINER = ACCOUNT + r"/containers/[0-9]+"
WORKSPACE = CONTAINER + r"/workspaces/[0-9]+"
VERSION = CONTAINER + r"/versions/(?:[0-9]+|published)"
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
    "templates": (WORKSPACE, "template"),
    "gtag_config": (WORKSPACE, "gtagConfig"),
    "clients": (WORKSPACE, "client"),
    "transformations": (WORKSPACE, "transformation"),
}
GET_PATTERNS = [
    ACCOUNT, CONTAINER, WORKSPACE, VERSION,
    *(WORKSPACE + "/" + kind + r"/[0-9]+" for kind in (
        "tags", "triggers", "variables", "folders", "templates", "gtag_config",
        "clients", "transformations",
    )),
    CONTAINER + r"/versions:live", WORKSPACE + r"/status", "accounts/containers:lookup",
]
LIST_PATTERNS = [
    parent + "/" + kind if parent else kind for kind, (parent, _) in COLLECTIONS.items()
]
FOLDER_ENTITIES = WORKSPACE + r"/folders/[0-9]+:entities"


class GTMError(RuntimeError):
    pass


def validate(value: str, pattern: str) -> None:
    if not re.fullmatch(pattern, value):
        raise GTMError("Invalid GTM resource path. Use numeric IDs and documented relative paths.")


class RateLimiter:
    """Space starts by >4 seconds: at most 25 starts in any 100 seconds per process."""

    def __init__(self, clock=time.monotonic, sleep=time.sleep):
        self.clock, self.sleep = clock, sleep
        self.lock = threading.Lock()
        self.next_start = 0.0

    def wait(self):
        with self.lock:
            delay = self.next_start - self.clock()
            if delay > 0:
                self.sleep(delay)
            self.next_start = self.clock() + 4.05


LIMITER = RateLimiter()


def retryable(response):
    if response.status_code in (429, 500, 502, 503, 504):
        return True
    if response.status_code == 403:
        try:
            errors = response.json().get("error", {}).get("errors", [])
            return any(e.get("reason") in ("rateLimitExceeded", "userRateLimitExceeded")
                       for e in errors)
        except (ValueError, AttributeError, TypeError):
            pass
    return False


class GTMClient:
    def __init__(self, session=None, limiter=None, sleep=None):
        self._session = session
        self.limiter = LIMITER if limiter is None else limiter
        self.sleep = sleep or time.sleep

    def _request(self, method: str, path: str, params=None) -> dict:
        patterns = GET_PATTERNS + LIST_PATTERNS if method == "GET" else (
            [FOLDER_ENTITIES] if method == "POST" else []
        )
        if not any(re.fullmatch(pattern, path) for pattern in patterns):
            raise GTMError("GTM operation is not on the read-only allowlist.")
        token_request = None
        session = self._session
        try:
            if session is None:
                creds = credentials()
                token_request = GoogleTokenRequest()
                session = AuthorizedSession(creds, auth_request=token_request,
                                            refresh_timeout=30, max_refresh_attempts=0)
            for attempt in range(3):
                self.limiter.wait()
                request = session.get if method == "GET" else session.post
                response = request(
                    "https://tagmanager.googleapis.com/tagmanager/v2/" + path,
                    params=params or {}, timeout=30, allow_redirects=False,
                )
                if response.status_code == 200:
                    result = response.json()
                    if not isinstance(result, dict):
                        raise GTMError("Unexpected Google API response.")
                    return result
                if attempt < 2 and retryable(response):
                    # Jitter only; no security-sensitive randomness.
                    delay = 2 ** (attempt + 1) + random.uniform(0, 1)  # nosec B311
                    header = response.headers.get("Retry-After")
                    if isinstance(header, str) and header.isdigit():
                        # Do not retry earlier than requested; stop if outside our bounded wait.
                        if int(header) > 30:
                            break
                        delay = max(delay, int(header))
                    self.sleep(delay)
                    continue
                break
            errors = {
                401: "Google login expired. Run login again.",
                403: "Access denied or quota exceeded. Check GTM access, API enablement and quota.",
                404: "GTM resource not found or unavailable to this account.",
                429: "Google API quota exceeded. Retry later.",
            }
            raise GTMError(errors.get(response.status_code,
                                     f"Google API request failed (HTTP {response.status_code})."))
        except requests.RequestException:
            raise GTMError("Google API connection failed or timed out.") from None
        except GoogleAuthError:
            raise GTMError("Google authentication failed. Check credentials or log in again.") from None
        except ValueError:
            raise GTMError("Invalid JSON response from Google API.") from None
        finally:
            if self._session is None and session is not None:
                session.close()
            if token_request is not None:
                token_request.session.close()

    def _get(self, path: str, params=None) -> dict:
        return self._request("GET", path, params)

    def list(self, kind: str, parent: str = "", page_token: str | None = None,
             max_pages: int = 1) -> dict:
        if kind not in COLLECTIONS:
            raise GTMError("Unsupported collection.")
        pattern, key = COLLECTIONS[kind]
        validate(parent, pattern)
        path = parent + "/" + kind if parent else kind
        data = self.pages("GET", path, [key], page_token, max_pages)
        return {"items": data[key], "next_page_token": data.get("nextPageToken"),
                "parent": parent, "collection": kind, "pages_read": data["pages_read"],
                "complete": not bool(data.get("nextPageToken"))}

    def pages(self, method, path, keys, page_token=None, max_pages=1):
        if not 1 <= max_pages <= 5:
            raise GTMError("max_pages must be between 1 and 5. Continue with next_page_token.")
        result = {key: [] for key in keys}
        seen = {page_token} if page_token else set()
        for index in range(max_pages):
            data = self._request(method, path, {"pageToken": page_token} if page_token else {})
            for key in keys:
                result[key].extend(data.get(key, []))
            page_token = data.get("nextPageToken")
            if not page_token:
                break
            if page_token in seen:
                raise GTMError("Google returned a repeated pagination token; stopped safely.")
            seen.add(page_token)
        return {**result, "nextPageToken": page_token, "pages_read": index + 1}

    def get(self, path: str, pattern: str) -> dict:
        validate(path, pattern)
        return self._get(path)

    def lookup(self, tag_id=None, destination_id=None):
        if bool(tag_id) == bool(destination_id):
            raise GTMError("Provide exactly one of tag_id or destination_id; never guess IDs.")
        value = tag_id or destination_id
        if not re.fullmatch(r"[A-Za-z0-9-]{1,100}", value):
            raise GTMError("Invalid public tag or destination ID.")
        return self._get("accounts/containers:lookup",
                         {"tagId" if tag_id else "destinationId": value})

    def folder_entities(self, path, page_token=None, max_pages=1):
        validate(path, WORKSPACE + r"/folders/[0-9]+")
        return self.pages("POST", path + ":entities", ["tag", "trigger", "variable"],
                          page_token, max_pages)
