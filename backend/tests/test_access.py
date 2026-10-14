"""Private deployment authorization, identity recording and configuration checks."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from supabase_auth.errors import AuthApiError

from app import access, main
from app.api import projects


@pytest.fixture
def private_app(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    monkeypatch.setenv("AUTH_ALLOWED_EMAILS", " Reviewer@example.com ")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "sb_secret_fake_for_tests")
    monkeypatch.setenv("CORS_ORIGINS", "https://rbdemo.example.com")
    user = SimpleNamespace(
        id="reviewer-id",
        email="reviewer@example.com",
        role="authenticated",
        email_confirmed_at=datetime.now(timezone.utc),
    )
    get_user = Mock(return_value=SimpleNamespace(user=user))
    store = SimpleNamespace(
        client=SimpleNamespace(auth=SimpleNamespace(get_user=get_user)),
        list=Mock(return_value=[{"id": "private-report"}]),
        approve=Mock(),
        advance=Mock(),
    )
    monkeypatch.setattr(main, "ReportStore", lambda: store)
    app = main.create_app()
    return TestClient(app), store, user


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/health"),
        ("GET", "/api/catalog"),
        ("GET", "/api/projects"),
        ("GET", "/api/projects/report"),
        ("GET", "/api/knowledge/portfolio"),
        ("POST", "/api/projects/analyze"),
        ("POST", "/api/materials"),
        ("POST", "/api/knowledge/entries"),
        ("POST", "/api/knowledge/ask"),
        ("POST", "/api/projects/report/approve"),
        ("POST", "/api/projects/report/execute"),
        ("POST", "/api/projects/report/work-order/actions"),
    ],
)
def test_every_api_requires_sign_in(private_app, method, path):
    client, store, _ = private_app
    response = client.request(method, path, json={} if method == "POST" else None)
    assert response.status_code == 401
    store.client.auth.get_user.assert_not_called()
    store.list.assert_not_called()


def test_verified_invited_user_can_read_and_docs_are_hidden(private_app):
    client, store, _ = private_app
    response = client.get("/api/projects", headers={"Authorization": "Bearer user-access-token"})
    assert response.json() == [{"id": "private-report"}]
    store.client.auth.get_user.assert_called_once_with("user-access-token")
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404


@pytest.mark.parametrize(
    "change,status",
    [
        ({"email": "outsider@example.com"}, 403),
        ({"email_confirmed_at": None}, 401),
        ({"role": "service_role"}, 401),
    ],
)
def test_rejected_accounts_cannot_read_reports(private_app, change, status):
    client, store, user = private_app
    for key, value in change.items():
        setattr(user, key, value)
    assert (
        client.get("/api/projects", headers={"Authorization": "Bearer token"}).status_code == status
    )
    store.list.assert_not_called()


@pytest.mark.parametrize(
    "failure,status",
    [
        (AuthApiError("Expired token", 401, None), 401),
        (AuthApiError("Unavailable", 503, None), 503),
        (RuntimeError("Network down"), 503),
    ],
)
def test_authentication_failures_do_not_grant_access(private_app, failure, status):
    client, store, _ = private_app
    store.client.auth.get_user.side_effect = failure
    response = client.get("/api/projects", headers={"Authorization": "Bearer private-token"})
    assert response.status_code == status
    assert "private-token" not in response.text
    store.list.assert_not_called()


def test_approval_and_progress_record_the_verified_identity(private_app, monkeypatch):
    client, store, _ = private_app
    store.approve.return_value = {"id": "report"}
    monkeypatch.setattr(projects, "run_post_approval", lambda *_: {"id": "report"})
    headers = {"Authorization": "Bearer token"}
    response = client.post(
        "/api/projects/report/approve",
        headers=headers,
        json={
            "reviewer": "Display name",
            "measurements_confirmed": True,
            "specification_confirmed": True,
            "commercial_terms_confirmed": True,
            "execution_confirmed": True,
        },
    )
    assert response.status_code == 200
    approval = store.approve.call_args.args[1]
    assert approval["approved_by_user_id"] == "reviewer-id"
    assert approval["approved_by_email"] == "reviewer@example.com"
    store.client.auth.get_user.assert_called_once()
    store.advance.return_value = {"id": "report"}
    response = client.post(
        "/api/projects/report/work-order/actions",
        headers=headers,
        json={
            "action": "start_production",
            "actor": "Someone else",
            "note": "Demo progress",
        },
    )
    assert response.status_code == 200
    assert store.advance.call_args.kwargs["actor"] == "reviewer@example.com"


def test_cross_origin_authorization_header_is_allowed(private_app):
    client, _, _ = private_app
    response = client.options(
        "/api/projects",
        headers={
            "Origin": "https://rbdemo.example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://rbdemo.example.com"
    assert "Authorization" in response.headers["access-control-allow-headers"]


@pytest.mark.parametrize(
    "variable,value",
    [
        ("AUTH_REQUIRED", "false"),
        ("AUTH_REQUIRED", "invalid"),
        ("AUTH_ALLOWED_EMAILS", ""),
        ("AUTH_ALLOWED_EMAILS", "*@example.com"),
        ("SUPABASE_SERVICE_ROLE_KEY", ""),
    ],
)
def test_insecure_private_configuration_fails_at_startup(private_app, monkeypatch, variable, value):
    monkeypatch.setenv(variable, value)
    with pytest.raises(RuntimeError):
        access.access_settings()
