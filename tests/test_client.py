from unittest.mock import Mock

import pytest
import requests

from flin_gtm_mcp.client import CONTAINER, GTMClient, GTMError


def session(status=200, data=None):
    response = Mock(status_code=status)
    response.json.return_value = data if data is not None else {}
    fake = Mock()
    fake.get.return_value = response
    return fake


def test_pagination_and_empty_response():
    fake = session(data={"tag": [{"tagId": "1"}], "nextPageToken": "next"})
    result = GTMClient(fake).list("tags", "accounts/1/containers/2/workspaces/3", "previous")
    assert result["items"] == [{"tagId": "1"}]
    assert result["next_page_token"] == "next"
    assert fake.get.call_args.kwargs == {
        "params": {"pageToken": "previous"},
        "timeout": 30,
        "allow_redirects": False,
    }
    assert GTMClient(session()).list("accounts")["items"] == []


@pytest.mark.parametrize(
    "path",
    [
        "https://evil.example",
        "accounts/1/../2",
        "accounts/1?x=y",
        "accounts/1/containers/2:publish",
        "accounts/1/containers/2/workspaces/3:create_version",
        "accounts/1%2fcontainers/2",
        "accounts/1/containers/2/versions/3:publish",
        "accounts/1\n",
        "accounts/1/user_permissions",
    ],
)
def test_non_allowlisted_paths_never_reach_network(path):
    fake = session()
    with pytest.raises(GTMError):
        GTMClient(fake)._get(path)
    fake.get.assert_not_called()


def test_wrong_parent_never_reaches_network():
    fake = session()
    with pytest.raises(GTMError):
        GTMClient(fake).list("tags", "accounts/1")
    fake.get.assert_not_called()


@pytest.mark.parametrize("status", [301, 401, 403, 404, 429, 500])
def test_api_errors_are_not_empty_successes_or_raw_bodies(status):
    fake = session(status, {"error": "sensitive body"})
    with pytest.raises(GTMError) as error:
        GTMClient(fake).list("accounts")
    assert "sensitive" not in str(error.value)


def test_connection_error_redacted():
    fake = session()
    fake.get.side_effect = requests.ConnectionError("secret token")
    with pytest.raises(GTMError, match="connection failed"):
        GTMClient(fake).list("accounts")


def test_live_version_is_get():
    fake = session(data={"containerVersionId": "42"})
    assert (
        GTMClient(fake).get("accounts/1/containers/2/versions:live", CONTAINER + "/versions:live")[
            "containerVersionId"
        ]
        == "42"
    )
    assert fake.get.call_args.args[0].endswith("/versions:live")
    fake.post.assert_not_called()
