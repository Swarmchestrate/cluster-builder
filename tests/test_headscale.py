
from unittest.mock import Mock

import pytest
import requests

from cluster_builder.infrastructure.headscale import (
    HeadscaleAPIError,
    HeadscaleAuthenticationError,
    HeadscaleClient,
    HeadscaleConfig,
    HeadscaleConnectionError,
    HeadscaleResponseError,
)

BASE_URL = "http://headscale.test"


@pytest.fixture
def client():
    return HeadscaleClient(
        HeadscaleConfig(
            base_url=BASE_URL,
            api_key="test-api-key",
        )
    )


def test_create_user(client, monkeypatch):
    response = Mock()
    response.status_code = 200
    response.ok = True
    response.json.return_value = {
        "user": {"id": "123", "name": "alice"}
    }

    request = Mock(return_value=response)
    monkeypatch.setattr(client.session, "request", request)

    result = client.create_user("alice")

    assert result == {"user": {"id": "123", "name": "alice"}}

    args, kwargs = request.call_args
    assert args == ("POST", f"{BASE_URL}/api/v1/user")
    assert kwargs["json"] == {"name": "alice"}
    assert kwargs["timeout"] == 10


def test_list_users(client, monkeypatch):
    response = Mock()
    response.status_code = 200
    response.ok = True
    response.json.return_value = {
        "users": [{"id": "123", "name": "alice"}]
    }

    request = Mock(return_value=response)
    monkeypatch.setattr(client.session, "request", request)

    result = client.list_users()

    assert result == [{"id": "123", "name": "alice"}]

    args, kwargs = request.call_args
    assert args == ("GET", f"{BASE_URL}/api/v1/user")
    assert kwargs["timeout"] == 10


def test_create_preauth_key(client, monkeypatch):
    response = Mock()
    response.status_code = 200
    response.ok = True
    response.json.return_value = {
        "preAuthKey": {"key": "example-key"}
    }

    request = Mock(return_value=response)
    monkeypatch.setattr(client.session, "request", request)

    result = client.create_preauth_key(
        "alice", reusable=True, ephemeral=True
    )

    assert result == {"preAuthKey": {"key": "example-key"}}

    args, kwargs = request.call_args
    assert args == ("POST", f"{BASE_URL}/api/v1/preauthkey")
    assert kwargs["json"] == {
        "user": "alice",
        "reusable": True,
        "ephemeral": True,
    }
    assert kwargs["timeout"] == 10


def test_list_nodes(client, monkeypatch):
    response = Mock()
    response.status_code = 200
    response.ok = True
    response.json.return_value = {
        "nodes": [{"id": "node-1"}]
    }

    request = Mock(return_value=response)
    monkeypatch.setattr(client.session, "request", request)

    result = client.list_nodes()

    assert result == [{"id": "node-1"}]

    args, kwargs = request.call_args
    assert args == ("GET", f"{BASE_URL}/api/v1/node")
    assert kwargs["timeout"] == 10


@pytest.mark.parametrize(
    ("method", "resource_id", "expected_url"),
    [
        (
            "delete_user",
            "user/123",
            f"{BASE_URL}/api/v1/user/user%2F123",
        ),
        (
            "delete_node",
            "node/123",
            f"{BASE_URL}/api/v1/node/node%2F123",
        ),
    ],
)
def test_delete_operations(
    client, monkeypatch, method, resource_id, expected_url
):
    response = Mock()
    response.status_code = 200
    response.ok = True

    request = Mock(return_value=response)
    monkeypatch.setattr(client.session, "request", request)

    assert getattr(client, method)(resource_id) is None

    args, kwargs = request.call_args
    assert args == ("DELETE", expected_url)
    assert kwargs["timeout"] == 10


def test_authentication_error(client, monkeypatch):
    response = Mock()
    response.status_code = 401
    response.ok = False

    request = Mock(return_value=response)
    monkeypatch.setattr(client.session, "request", request)

    with pytest.raises(HeadscaleAuthenticationError):
        client.list_users()

    args, _ = request.call_args
    assert args == ("GET", f"{BASE_URL}/api/v1/user")


def test_http_error(client, monkeypatch):
    response = Mock()
    response.status_code = 500
    response.ok = False

    request = Mock(return_value=response)
    monkeypatch.setattr(client.session, "request", request)

    with pytest.raises(HeadscaleAPIError):
        client.list_users()

    args, _ = request.call_args
    assert args == ("GET", f"{BASE_URL}/api/v1/user")


def test_connection_timeout(client, monkeypatch):
    request = Mock(side_effect=requests.exceptions.Timeout)
    monkeypatch.setattr(client.session, "request", request)

    with pytest.raises(HeadscaleConnectionError):
        client.list_users()

    args, kwargs = request.call_args
    assert args == ("GET", f"{BASE_URL}/api/v1/user")
    assert kwargs["timeout"] == 10


def test_invalid_json(client, monkeypatch):
    response = Mock()
    response.status_code = 200
    response.ok = True
    response.json.side_effect = ValueError("invalid JSON")

    request = Mock(return_value=response)
    monkeypatch.setattr(client.session, "request", request)

    with pytest.raises(HeadscaleResponseError):
        client.create_user("alice")

    args, kwargs = request.call_args
    assert args == ("POST", f"{BASE_URL}/api/v1/user")
    assert kwargs["json"] == {"name": "alice"}
    assert kwargs["timeout"] == 10