from copy import deepcopy
from unittest.mock import Mock

import pytest

from flin_gtm_mcp.analysis import dependencies, diff_versions
from flin_gtm_mcp.client import GTMClient, GTMError, RateLimiter
from flin_gtm_mcp.snapshots import SnapshotStore, summary


class Clock:
    def __init__(self):
        self.now = 1000

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def response(status=200, data=None):
    result = Mock(status_code=status, headers={})
    result.json.return_value = data or {}
    return result


def client_with(responses):
    session = Mock()
    session.get.side_effect = responses
    return GTMClient(session, limiter=Mock(), sleep=Mock()), session


def test_limiter_rolling_window():
    clock = Clock()
    limiter = RateLimiter(clock, clock.sleep)
    starts = []
    for _ in range(60):
        limiter.wait()
        starts.append(clock())
    assert all(sum(t <= s < t + 100 for s in starts) <= 25 for t in starts)


def test_retries_quota_but_not_permissions_or_daily_limit():
    for reason, count in [("rateLimitExceeded", 2), ("forbidden", 1), ("dailyLimitExceeded", 1)]:
        client, fake = client_with([
            response(403, {"error": {"errors": [{"reason": reason}]}}), response(),
        ])
        if count == 1:
            with pytest.raises(GTMError):
                client.list("accounts")
        else:
            client.list("accounts")
        assert fake.get.call_count == count
        assert client.limiter.wait.call_count == count


def test_retry_bounded_and_retry_after():
    fail = response(429)
    fail.headers = {"Retry-After": "12"}
    client, fake = client_with([fail, fail, fail])
    with pytest.raises(GTMError):
        client.list("accounts")
    assert fake.get.call_count == 3
    assert [c.args[0] for c in client.sleep.call_args_list] == [12, 12]
    fail.headers = {"Retry-After": "120"}
    client, fake = client_with([fail])
    with pytest.raises(GTMError):
        client.list("accounts")
    client.sleep.assert_not_called()


def test_pagination_bounds_and_loops():
    client, fake = client_with([
        response(data={"tag": [{"tagId": "1"}], "nextPageToken": "a"}),
        response(data={"tag": [{"tagId": "2"}], "nextPageToken": "b"}),
    ])
    data = client.list("tags", "accounts/1/containers/2/workspaces/3", max_pages=2)
    assert len(data["items"]) == 2
    assert data["next_page_token"] == "b" and not data["complete"]
    assert fake.get.call_args.kwargs["params"] == {"pageToken": "a"}
    client, fake = client_with([response(data={"nextPageToken": "a"})] * 2)
    with pytest.raises(GTMError, match="repeated"):
        client.list("accounts", max_pages=2)
    client, fake = client_with([])
    with pytest.raises(GTMError):
        client.list("accounts", max_pages=6)
    fake.get.assert_not_called()


def test_only_readonly_post_endpoint_and_empty_body():
    client, fake = client_with([])
    fake.post.return_value = response(data={"tag": [{"tagId": "1"}]})
    data = client.folder_entities("accounts/1/containers/2/workspaces/3/folders/4")
    assert data["tag"][0]["tagId"] == "1"
    assert set(fake.post.call_args.kwargs) == {"params", "timeout", "allow_redirects"}
    for method, path in [("POST", "accounts/1/containers/2/versions/3:publish"),
                         ("DELETE", "accounts/1"), ("POST", "accounts/1")]:
        with pytest.raises(GTMError):
            client._request(method, path)
    assert fake.post.call_count == 1


def test_new_collection_mapping_and_lookup():
    client, fake = client_with([response(data={"template": [{"templateId": "7"}]}), response()])
    assert client.list("templates", "accounts/1/containers/2/workspaces/3")["items"]
    client.lookup(tag_id="GTM-ABC")
    assert fake.get.call_args.kwargs["params"] == {"tagId": "GTM-ABC"}
    assert fake.get.call_args.args[0].endswith("accounts/containers:lookup")


def test_summary_preserves_consent_and_dependencies():
    tag = {"consentSettings": {"consentStatus": "needed"}, "blockingTriggerId": ["2"],
           "setupTag": [{"tagName": "setup"}], "parameter": [{"value": "secret code"}]}
    compact = summary(tag)
    assert compact["consentSettings"] == tag["consentSettings"]
    assert compact["blockingTriggerId"] == ["2"] and compact["setupTag"] == tag["setupTag"]
    assert compact["_omitted_fields"] == ["parameter"]
    assert "parameter" in tag


def test_snapshot_cache_expiry_refresh_and_identity():
    clock = Clock()
    owner = ["alice"]
    client = Mock()
    client._get.return_value = {"fingerprint": "abc", "tag": [{"tagId": "1"}]}
    store = SnapshotStore(clock, lambda: owner[0], lambda: client)
    path = "accounts/1/containers/2/versions:live"
    first = store.fetch(path)
    assert store.fetch(path)["snapshot_id"] == first["snapshot_id"]
    assert client._get.call_count == 1
    assert store.fetch(path, True)["snapshot_id"] != first["snapshot_id"]
    assert store.entities(first["snapshot_id"], "tag")["items"] == [{"tagId": "1"}]
    changed = store.read(first["snapshot_id"])
    changed["tag"].clear()
    assert store.read(first["snapshot_id"])["tag"]
    owner[0] = "bob"
    with pytest.raises(GTMError):
        store.read(first["snapshot_id"])
    owner[0] = "alice"
    clock.sleep(61)
    assert store.fetch(path)["snapshot_id"] != first["snapshot_id"]
    clock.sleep(240)
    with pytest.raises(GTMError):
        store.read(first["snapshot_id"])


def test_snapshot_capacity_and_paging():
    client = Mock()
    client._get.return_value = {"tag": [{"tagId": str(i)} for i in range(3)]}
    store = SnapshotStore(owner=lambda: "alice", client_factory=lambda: client)
    keys = [store.fetch(f"accounts/1/containers/2/versions/{i}")["snapshot_id"] for i in range(9)]
    assert len(store.entries) == 8
    with pytest.raises(GTMError):
        store.read(keys[0])
    page = store.entities(keys[-1], "tag", limit=2)
    assert page["next_offset"] == 2 and len(page["items"]) == 2
    assert store.entities(keys[-1], "tag", entity_id="2")["items"] == [{"tagId": "2"}]
    store.max_bytes = 1
    with pytest.raises(GTMError, match="budget"):
        store.fetch("accounts/1/containers/2/versions/50")


def test_dependencies_sequence_blockers_groups_and_variables():
    data = {
        "tag": [{"tagId": "1", "name": "main", "firingTriggerId": ["2147479553"],
                 "blockingTriggerId": ["2", "missing"], "setupTag": [{"tagName": "setup"}],
                 "parameter": [{"value": "{{Used}}"}]},
                {"tagId": "2", "name": "setup"}, {"tagId": "3", "name": "orphan"}],
        "trigger": [{"triggerId": "2"}, {"triggerId": "3"}, {"triggerId": "4"},
                    {"triggerId": "5", "type": "triggerGroup", "parameter": [{"value": "3"}]}],
        "variable": [{"variableId": "1", "name": "Used"}, {"variableId": "2", "name": "Unused"}],
    }
    result = dependencies(data)
    assert result["tags_without_firing_or_sequence_reference"] == ["3"]
    assert result["unreferenced_trigger_candidates"] == ["4", "5"]
    assert result["unreferenced_variable_candidates"] == ["2"]
    assert len(result["missing_references"]) == 1


def test_diff_detects_actual_fields_not_just_fingerprint():
    left = {"accountId": "1", "containerId": "2", "tag": [
        {"tagId": "1", "fingerprint": "a", "consentSettings": {"consentStatus": "needed"}},
        {"tagId": "2"}], "customTemplate": [{"templateId": "1", "templateData": "old"}]}
    right = deepcopy(left)
    right["tag"][0]["consentSettings"]["consentStatus"] = "notSet"
    right["tag"][1]["tagId"] = "3"
    right["customTemplate"][0]["templateData"] = "new"
    changes = diff_versions(left, right)
    assert changes[0]["fields"] == ["consentSettings.consentStatus"]
    assert [c["change"] for c in changes] == ["modified", "removed", "added", "modified"]
    right = deepcopy(left)
    right["tag"][0]["fingerprint"] = "b"
    assert diff_versions(left, right) == []
    right["containerId"] = "3"
    with pytest.raises(GTMError):
        diff_versions(left, right)


@pytest.mark.parametrize("collection,key", [
    ("templates", "template"), ("gtag_config", "gtagConfig"),
    ("clients", "client"), ("transformations", "transformation"),
])
def test_expanded_read_surface(collection, key):
    client, fake = client_with([response(data={key: [{"name": "sample"}]}), response()])
    parent = "accounts/1/containers/2/workspaces/3"
    result = client.list(collection, parent)
    assert result["items"] == [{"name": "sample"}]
    assert fake.get.call_args.args[0].endswith(f"/{collection}")
    client._get(f"{parent}/{collection}/4")
    fake.post.assert_not_called()


def test_snapshot_fetch_validates_before_auth_or_network():
    owner, client = Mock(), Mock()
    store = SnapshotStore(owner=owner, client_factory=lambda: client)
    with pytest.raises(GTMError):
        store.fetch("accounts/1/containers/2/versions/3:publish")
    owner.assert_not_called()
    client._get.assert_not_called()
