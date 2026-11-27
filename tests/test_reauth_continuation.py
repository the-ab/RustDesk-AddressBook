from __future__ import annotations

import os
import subprocess
import time
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pyotp
import pytest
from flask import redirect
from werkzeug.middleware.proxy_fix import ProxyFix

import app as application
from app.crypto import encrypt_value
from app.extensions import db
from app.models import AuthEvent, Device, User
from tests.conftest import set_csrf


class Elements(HTMLParser):
    def __init__(self, content):
        super().__init__()
        self.by_id = {}
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.by_id[attrs["id"]] = (tag, attrs)


@pytest.fixture
def signed_in(client, clean_app):
    with clean_app.app_context():
        user = User(username="continuation-admin", role="admin", active=True, auth_provider="local")
        user.set_password("continuation-test-password")
        db.session.add(user)
        db.session.flush()
        application._sign_user_security_state(user)
        db.session.add(Device(
            id=12, name="Selected client", rustdesk_id="987654321",
            encrypted_password=encrypt_value("synthetic & device?password"),
        ))
        db.session.commit()
        user_id = user.id
    csrf = set_csrf(client)
    response = client.post("/login", data={
        "csrf_token": csrf, "username": "continuation-admin", "password": "continuation-test-password",
    })
    assert response.status_code == 302
    return SimpleNamespace(client=client, app=clean_app, user_id=user_id, csrf=csrf)


def expire(state):
    with state.client.session_transaction() as session:
        session["auth_time"] = int(time.time()) - 1801


def confirm(state, target, **values):
    return state.client.post("/reauth", data={
        "csrf_token": state.csrf, "current_password": "continuation-test-password", "next": target, **values,
    })


@pytest.mark.parametrize("language", ["de", "en"])
def test_connect_resumes_requested_client_on_internal_page(signed_in, language):
    state = signed_in
    with state.app.app_context():
        user = db.session.get(User, state.user_id)
        user.preferred_language = language
        application._sign_user_security_state(user)
        db.session.commit()
    expire(state)
    response = state.client.get("/devices/12/connect")
    assert response.status_code == 302
    assert parse_qs(urlsplit(response.location).query)["next"] == ["/devices/12/connect"]
    assert state.client.get(response.location).status_code == 200

    response = confirm(state, "/devices/12/connect")
    assert response.status_code == 302
    assert response.location == "/devices/12/connect"
    page = state.client.get(response.location)
    assert page.status_code == 200
    assert "Location" not in page.headers
    assert page.headers["Cache-Control"] == "no-store"
    assert page.headers["Referrer-Policy"] == "no-referrer"
    assert "form-action 'self'" in page.headers["Content-Security-Policy"]
    link = Elements(page.get_data(as_text=True)).by_id["rustdeskConnectLink"]
    assert link[0] == "a"
    target = urlsplit(link[1]["href"])
    assert target.scheme == "rustdesk"
    assert target.netloc == "987654321"
    assert parse_qs(target.query)["password"] == ["synthetic & device?password"]
    assert "Selected client" in page.get_data(as_text=True)
    assert ("Open RustDesk" if language == "en" else "RustDesk öffnen") in page.get_data(as_text=True)

    # Execute the production browser code with a harmless navigation recorder:
    # no external protocol handler or real client is contacted by the test.
    env = dict(os.environ, RAB_TEST_CONNECT_URL=link[1]["href"])
    result = subprocess.run(
        ["node", str(Path(__file__).parent / "js" / "test_device_continuation.cjs")],
        env=env, text=True, capture_output=True, timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_reauth_failure_and_csrf_do_not_release_connection(signed_in):
    state = signed_in
    expire(state)
    response = confirm(state, "/devices/12/connect", current_password="wrong")
    assert response.status_code == 200
    assert "rustdeskConnectLink" not in response.get_data(as_text=True)
    assert state.client.get("/devices/12/connect").status_code == 302
    assert state.client.post("/reauth", data={
        "next": "/devices/12/connect", "current_password": "continuation-test-password",
    }).status_code == 400
    assert state.client.get("/devices/12/connect").status_code == 302


def test_totp_is_required_before_connection_continues(signed_in):
    state = signed_in
    secret = pyotp.random_base32()
    with state.app.app_context():
        user = db.session.get(User, state.user_id)
        user.totp_enabled = True
        user.totp_secret_encrypted = encrypt_value(secret)
        application._sign_user_security_state(user)
        db.session.commit()
    expire(state)
    assert confirm(state, "/devices/12/connect", totp_code="").status_code == 200
    assert state.client.get("/devices/12/connect").status_code == 302
    response = confirm(state, "/devices/12/connect", totp_code=pyotp.TOTP(secret).now())
    assert response.location == "/devices/12/connect"
    assert state.client.get(response.location).status_code == 200


def test_reauth_respects_attempt_limit_without_using_initial_login_budget(signed_in, monkeypatch):
    state = signed_in
    monkeypatch.setattr(application, "_get_bruteforce_settings", lambda: {"limit": 1, "window_seconds": 900})
    expire(state)
    target = "/devices/12/connect"
    assert state.client.post("/reauth", data={
        "csrf_token": state.csrf, "current_password": "incorrect", "next": target,
    }).status_code == 200
    response = confirm(state, target)
    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0
    assert response.headers["Cache-Control"] == "no-store"
    assert state.client.get(target).status_code == 302
    other = state.app.test_client()
    login = other.post("/login", data={
        "csrf_token": set_csrf(other), "username": "continuation-admin", "password": "continuation-test-password",
    })
    assert login.status_code == 302


@pytest.mark.parametrize("path", ["/account", "/settings"])
def test_security_forms_share_the_reauthentication_attempt_limit(signed_in, monkeypatch, path):
    state = signed_in
    monkeypatch.setattr(application, "_get_bruteforce_settings", lambda: {"limit": 1, "window_seconds": 900})
    form = {"csrf_token": state.csrf, "action": "password", "new_password": "replacement-password",
            "new_password2": "replacement-password"}
    assert state.client.post(path, data={**form, "current_password": "incorrect"}).status_code == 302
    assert confirm(state, "/devices/12/connect").status_code == 429
    assert state.client.post(path, data={**form, "current_password": "continuation-test-password"}).status_code == 302
    with state.app.app_context():
        user = db.session.get(User, state.user_id)
        assert user.check_password("continuation-test-password")


@pytest.mark.parametrize("path", ["/account", "/settings"])
def test_enrolled_second_factor_requires_verification_before_removal(signed_in, path):
    state = signed_in
    secret = pyotp.random_base32()
    with state.app.app_context():
        user = db.session.get(User, state.user_id)
        user.totp_enabled = True
        user.totp_secret_encrypted = encrypt_value(secret)
        application._sign_user_security_state(user)
        db.session.commit()
    form = {"csrf_token": state.csrf, "current_password": "continuation-test-password"}
    assert state.client.post(path, data={**form, "action": "totp_prepare"}).status_code == 302
    with state.app.app_context():
        assert db.session.get(User, state.user_id).totp_enabled
    assert state.client.post(path, data={
        **form, "action": "totp_disable", "totp_code": pyotp.TOTP(secret).now(),
    }).status_code == 302
    with state.app.app_context():
        assert not db.session.get(User, state.user_id).totp_enabled


def test_auth_audit_uses_the_address_selected_by_the_trusted_proxy(signed_in, monkeypatch):
    state = signed_in
    monkeypatch.setattr(state.app, "wsgi_app", ProxyFix(state.app.wsgi_app, x_for=1))
    assert state.client.post(
        "/logout", data={"csrf_token": state.csrf}, headers={"X-Forwarded-For": "192.0.2.100, 192.0.2.20"},
    ).status_code == 302
    with state.app.app_context():
        event = AuthEvent.query.filter_by(event_type="logout").one()
        assert event.ip_address == "192.0.2.20"


@pytest.mark.parametrize("change", ["none", "expired", "revoked"])
def test_second_factor_requires_current_password_confirmation(signed_in, change):
    state = signed_in
    secret = pyotp.random_base32()
    with state.app.app_context():
        user = db.session.get(User, state.user_id)
        user.totp_enabled = True
        user.totp_secret_encrypted = encrypt_value(secret)
        application._sign_user_security_state(user)
        db.session.commit()
    client = state.app.test_client()
    csrf = set_csrf(client)
    assert client.post("/login", data={
        "csrf_token": csrf, "username": "continuation-admin", "password": "continuation-test-password",
    }).location == "/login/2fa"
    if change == "expired":
        with client.session_transaction() as session:
            session["pending_2fa"] = dict(session["pending_2fa"], issued_at=int(time.time()) - 301)
    elif change == "revoked":
        with state.app.app_context():
            user = db.session.get(User, state.user_id)
            user.session_version += 1
            application._sign_user_security_state(user)
            db.session.commit()
    response = client.post("/login/2fa", data={"csrf_token": csrf, "totp_code": pyotp.TOTP(secret).now()})
    assert response.location == ("/" if change == "none" else "/login")


@pytest.mark.parametrize("subject,expected", [("existing-subject", "/devices/12/connect"), ("other-subject", "/login")])
def test_oidc_continuation_preserves_target_and_identity(signed_in, monkeypatch, subject, expected):
    state = signed_in
    issuer = "https://issuer.example"
    with state.app.app_context():
        user = db.session.get(User, state.user_id)
        user.auth_provider = "oidc"
        user.oidc_issuer = issuer
        user.oidc_subject = "existing-subject"
        application._sign_user_security_state(user)
        db.session.commit()
    settings = {
        "enabled": True, "configured": True, "issuer_url": issuer, "allow_insecure": False,
        "allowed_domains": [], "auto_provision": False, "username_claim": "preferred_username",
        "provider_name": "Test provider",
    }
    requested = []
    provider = SimpleNamespace(
        authorize_redirect=lambda uri, **kwargs: requested.append(kwargs) or redirect("/test-provider"),
        authorize_access_token=lambda: {"userinfo": {
            "sub": subject, "preferred_username": "continuation-admin", "email": "test@example.org",
        }},
    )
    monkeypatch.setattr(application, "_get_oidc_settings", lambda: settings)
    monkeypatch.setattr(application, "_configure_oidc_client", lambda: provider)
    monkeypatch.setattr(application, "_validate_oidc_issuer_url", lambda value, **kwargs: value)
    expire(state)
    response = confirm(state, "/devices/12/connect")
    assert response.status_code == 302
    assert urlsplit(response.location).path == "/login/oidc"
    assert state.client.get(response.location).location == "/test-provider"
    assert requested == [{"prompt": "login", "max_age": 0}]
    response = state.client.get("/login/oidc/callback")
    assert response.location == expected
    if subject == "existing-subject":
        page = state.client.get(response.location)
        assert page.status_code == 200
        assert "rustdeskConnectLink" in page.get_data(as_text=True)
    else:
        assert state.client.get("/devices/12/connect").status_code == 302


def test_password_request_is_resumed_without_secret_in_get(signed_in):
    state = signed_in
    expire(state)
    response = state.client.post("/devices/12/password", headers={"X-CSRF-Token": state.csrf})
    assert response.status_code == 401
    target = parse_qs(urlsplit(response.json["reauth_url"]).query)["next"][0]
    assert target == "/devices/12/password/view"
    response = confirm(state, target)
    assert response.location == target
    page = state.client.get(target)
    assert page.status_code == 200
    assert page.headers["Cache-Control"] == "no-store"
    assert "synthetic &amp; device?password" not in page.get_data(as_text=True)
    button = Elements(page.get_data(as_text=True)).by_id["resumeDevicePassword"]
    assert button[1]["data-password-url"] == "/devices/12/password"
    assert state.client.post("/devices/12/password").status_code == 400
    response = state.client.post("/devices/12/password", headers={"X-CSRF-Token": state.csrf})
    assert response.json == {"password": "synthetic & device?password"}


@pytest.mark.parametrize("target", ["/devices/12/connect", "/devices/12/password/view", "/devices/12/password"])
def test_device_access_is_rechecked_after_reauthentication(signed_in, target):
    state = signed_in
    expire(state)
    assert confirm(state, "/devices/12/connect").status_code == 302
    with state.app.app_context():
        user = db.session.get(User, state.user_id)
        user.role = "user"
        application._sign_user_security_state(user)
        db.session.commit()
    response = (state.client.post(target, headers={"X-CSRF-Token": state.csrf})
                if target.endswith("/password") else state.client.get(target))
    assert response.status_code == 404
    assert b"synthetic" not in response.data


@pytest.mark.parametrize("target", ["https://example.org/", "//example.org/", "javascript:alert(1)"])
def test_reauth_rejects_external_continuations(signed_in, target):
    assert confirm(signed_in, target).location == "/"


def test_recent_auth_does_not_show_reauth_form_again(signed_in):
    response = signed_in.client.get("/reauth?next=/devices/12/connect")
    assert response.status_code == 302
    assert response.location == "/devices/12/connect"


def test_revoked_session_cannot_complete_connection(signed_in):
    state = signed_in
    with state.app.app_context():
        user = db.session.get(User, state.user_id)
        user.session_version += 1
        application._sign_user_security_state(user)
        db.session.commit()
    response = state.client.get("/devices/12/connect")
    assert response.status_code == 302
    assert urlsplit(response.location).path == "/login"
    assert b"synthetic" not in response.data


def test_password_export_still_continues_after_reauth(signed_in):
    state = signed_in
    expire(state)
    response = state.client.get("/export?include_passwords=1")
    assert response.status_code == 302
    target = parse_qs(urlsplit(response.location).query)["next"][0]
    response = confirm(state, target)
    assert response.location == "/export?include_passwords=1"
    assert state.client.get(response.location).status_code == 200
