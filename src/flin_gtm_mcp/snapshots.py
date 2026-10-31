"""Bounded, authenticated in-memory version snapshots. Never persist GTM contents."""

import copy
import hashlib
import json
import threading
import time
import uuid
from collections import OrderedDict

from . import auth
from .client import CONTAINER, VERSION, GTMClient, GTMError, validate

ENTITY_IDS = {
    "tag": "tagId", "trigger": "triggerId", "variable": "variableId", "folder": "folderId",
    "builtInVariable": "type", "zone": "zoneId", "customTemplate": "templateId",
    "client": "clientId", "gtagConfig": "gtagConfigId", "transformation": "transformationId",
}


def summary(value):
    """Preserve structural/consent fields, explicitly mark omitted executable payloads."""
    if isinstance(value, list):
        return [summary(item) for item in value]
    if isinstance(value, dict):
        omitted = [key for key in ("parameter", "templateData") if key in value]
        result = {key: summary(item) for key, item in value.items() if key not in omitted}
        if omitted:
            result["_omitted_fields"] = omitted
        return result
    return value


def identity():
    creds = auth.credentials()  # Revalidate local auth even for cached data.
    principal = (str(auth.credentials_file().resolve()), creds.token,
                 getattr(creds, "service_account_email", None),
                 getattr(creds, "signer_email", None))
    return hashlib.sha256(repr(principal).encode()).hexdigest()


class SnapshotStore:
    def __init__(self, clock=time.monotonic, owner=identity, client_factory=GTMClient):
        self.clock, self.owner, self.client_factory = clock, owner, client_factory
        self.entries = OrderedDict()
        self.lock = threading.RLock()
        self.max_bytes = 32 * 1024 * 1024

    def _prune(self):
        for key, entry in list(self.entries.items()):
            if self.clock() - entry["created"] >= 300:
                del self.entries[key]

    def fetch(self, path, refresh=False):
        validate(path, rf"(?:{VERSION}|{CONTAINER}/versions:live)")
        owner = self.owner()
        with self.lock:
            self._prune()
            if not refresh:
                for key, entry in self.entries.items():
                    if (entry["owner"] == owner and entry["source"] == path
                            and self.clock() - entry["created"] < 60):
                        return self._view(key, entry)
            data = self.client_factory()._get(path)
            size = len(json.dumps(data).encode())
            if size > self.max_bytes:
                raise GTMError("Version exceeds the 32 MiB snapshot budget; use individual reads.")
            while self.entries and (len(self.entries) >= 8 or
                    sum(e["size"] for e in self.entries.values()) + size > self.max_bytes):
                self.entries.popitem(last=False)
            key = uuid.uuid4().hex
            entry = {"data": copy.deepcopy(data), "owner": owner, "source": path,
                     "created": self.clock(), "size": size}
            self.entries[key] = entry
            return self._view(key, entry)

    def _view(self, key, entry):
        data = entry["data"]
        return {"snapshot_id": key, "source": entry["source"],
                "containerVersionId": data.get("containerVersionId"),
                "fingerprint": data.get("fingerprint"),
                "age_seconds": round(self.clock() - entry["created"], 1),
                "expires_in_seconds": max(0, int(300 - (self.clock() - entry["created"]))),
                "counts": {kind: len(data.get(kind, [])) for kind in ENTITY_IDS},
                "detail_tool": "gtm_read_snapshot",
                "state": "published_at_fetch" if entry["source"].endswith((":live", "/published"))
                else "saved_version"}

    def read(self, key):
        owner = self.owner()
        with self.lock:
            self._prune()
            entry = self.entries.get(key)
            if entry is None or entry["owner"] != owner:
                raise GTMError("Snapshot unavailable, expired or login changed. Fetch it again.")
            return copy.deepcopy(entry["data"])

    def entities(self, key, kind, entity_id=None, offset=0, limit=50, full=False):
        if kind not in ENTITY_IDS or offset < 0 or not 1 <= limit <= 100:
            raise GTMError("Use a supported entity kind, offset >= 0 and limit 1..100.")
        data = self.read(key)
        items = data.get(kind, [])
        if entity_id is not None:
            items = [item for item in items if str(item.get(ENTITY_IDS[kind])) == entity_id]
            if not items:
                raise GTMError("Entity not found in this snapshot.")
        page = items[offset:offset + limit]
        return {"snapshot_id": key, "kind": kind, "items": page if full else summary(page),
                "total": len(items), "next_offset": offset + limit
                if offset + limit < len(items) else None, "full": full}


STORE = SnapshotStore()
