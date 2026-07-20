from __future__ import annotations

import io
import json
import tarfile

import pytest

from app import _check_online_update_available, _csv_safe_cell, _safe_extract_full_backup, _sign_user_security_state
from app.extensions import db
from app.models import Device, Group, User
from tests.conftest import set_csrf


def test_health_and_security_headers(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]


def test_setup_requires_the_server_token(client, clean_app):
    csrf = set_csrf(client)
    response = client.post(
        "/setup",
        data={
            "csrf_token": csrf,
            "setup_token": "wrong-token",
            "username": "admin",
            "password": "correct-horse-battery-staple",
            "password2": "correct-horse-battery-staple",
        },
    )
    assert response.status_code == 200
    with clean_app.app_context():
        assert User.query.count() == 0

    csrf = set_csrf(client, "valid-setup-csrf")
    response = client.post(
        "/setup",
        data={
            "csrf_token": csrf,
            "setup_token": clean_app.config["SETUP_TOKEN"],
            "username": "admin",
            "password": "correct-horse-battery-staple",
            "password2": "correct-horse-battery-staple",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    with clean_app.app_context():
        admin = User.query.filter_by(username="admin").one()
        assert admin.is_admin
        assert admin.check_password("correct-horse-battery-staple")


def test_regular_user_group_visibility_and_admin_denial(client, clean_app):
    with clean_app.app_context():
        visible_group = Group(name="Visible", color="primary", icon="collection")
        hidden_group = Group(name="Hidden", color="secondary", icon="collection")
        db.session.add_all([visible_group, hidden_group])
        db.session.flush()
        db.session.add_all(
            [
                Device(name="Visible device", rustdesk_id="100", group=visible_group),
                Device(name="Hidden device", rustdesk_id="200", group=hidden_group),
                Device(name="Ungrouped device", rustdesk_id="300", group=None),
            ]
        )
        user = User(username="reader", role="user", active=True, auth_provider="local")
        user.set_password("reader-password-123")
        user.groups.append(visible_group)
        db.session.add(user)
        db.session.flush()
        _sign_user_security_state(user)
        db.session.commit()

    csrf = set_csrf(client)
    response = client.post(
        "/login",
        data={"csrf_token": csrf, "username": "reader", "password": "reader-password-123"},
        follow_redirects=False,
    )
    assert response.status_code == 302

    devices = client.get("/devices")
    assert devices.status_code == 200
    assert b"Visible device" in devices.data
    assert b"Hidden device" not in devices.data
    assert b"Ungrouped device" not in devices.data
    assert client.get("/groups").status_code == 403


def test_restore_rejects_symbolic_links(clean_app, tmp_path):
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:gz") as tar:
        manifest = json.dumps({"format": "rustdesk-addressbook-full-backup", "version": 1}).encode()
        manifest_info = tarfile.TarInfo("manifest.json")
        manifest_info.size = len(manifest)
        tar.addfile(manifest_info, io.BytesIO(manifest))

        for name in ("data/addressbook.db", "data/config.json"):
            payload = b"placeholder"
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))

        link = tarfile.TarInfo("data/logs/escape")
        link.type = tarfile.SYMTYPE
        link.linkname = "/tmp"
        tar.addfile(link)

    with clean_app.app_context(), pytest.raises(ValueError, match="Nicht unterstützter Dateityp"):
        _safe_extract_full_backup(archive.getvalue(), tmp_path)


def test_csv_formula_protection_and_disabled_online_updates(clean_app):
    assert _csv_safe_cell("=2+2").startswith("'")
    assert _csv_safe_cell("normal") == "normal"
    with clean_app.app_context():
        result = _check_online_update_available()
    assert result["disabled"] is True
    assert result["update_available"] is False


def test_administrator_pages_render(client, clean_app):
    with clean_app.app_context():
        admin = User(username="admin-pages", role="admin", active=True, auth_provider="local")
        admin.set_password("admin-pages-password-123")
        db.session.add(admin)
        db.session.flush()
        _sign_user_security_state(admin)
        db.session.commit()

    csrf = set_csrf(client)
    response = client.post(
        "/login",
        data={"csrf_token": csrf, "username": "admin-pages", "password": "admin-pages-password-123"},
        follow_redirects=False,
    )
    assert response.status_code == 302

    for path in (
        "/",
        "/devices",
        "/groups",
        "/import",
        "/import/rustdesk-server",
        "/backup",
        "/security",
        "/settings",
        "/settings/oidc",
        "/users",
        "/account",
        "/help",
        "/release-notes",
    ):
        page = client.get(path)
        assert page.status_code == 200, path
