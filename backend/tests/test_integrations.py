"""Tests for third-party integration endpoints."""

from unittest.mock import MagicMock


def test_google_status_requires_auth(unauthenticated_client):
    response = unauthenticated_client.get("/api/v1/integrations/google/status")
    assert response.status_code == 401


def test_google_status_not_connected(client, monkeypatch):
    monkeypatch.setattr(
        "api.v1.integrations_api.google_workspace.get_connection",
        lambda _user_id: None,
    )

    response = client.get("/api/v1/integrations/google/status")

    assert response.status_code == 200
    assert response.json() == {"connected": False, "google_email": None}


def test_google_status_connected(client, monkeypatch):
    monkeypatch.setattr(
        "api.v1.integrations_api.google_workspace.get_connection",
        lambda _user_id: {
            "google_email": "user@gmail.com",
            "created_at": "2026-01-01T00:00:00Z",
        },
    )

    response = client.get("/api/v1/integrations/google/status")

    assert response.status_code == 200
    assert response.json() == {
        "connected": True,
        "google_email": "user@gmail.com",
        "connected_at": "2026-01-01T00:00:00Z",
    }


def test_google_authorize_returns_consent_url(client, monkeypatch):
    flow = MagicMock()
    flow.authorization_url.return_value = ("https://accounts.google.com/o/oauth2/auth", None)

    monkeypatch.setattr(
        "api.v1.integrations_api.google_workspace.build_flow",
        lambda **_: flow,
    )
    monkeypatch.setattr(
        "api.v1.integrations_api.google_workspace.sign_state",
        lambda *_args, **_kwargs: "signed-state",
    )

    response = client.get("/api/v1/integrations/google/authorize")

    assert response.status_code == 200
    assert response.json() == {"url": "https://accounts.google.com/o/oauth2/auth"}


def test_google_disconnect(client, monkeypatch):
    monkeypatch.setattr(
        "api.v1.integrations_api.google_workspace.get_google_credentials",
        lambda _user_id: None,
    )
    deleted = []

    monkeypatch.setattr(
        "api.v1.integrations_api.google_workspace.delete_connection",
        lambda user_id: deleted.append(user_id),
    )

    response = client.delete("/api/v1/integrations/google")

    assert response.status_code == 204
    assert deleted == ["test-user-id"]
