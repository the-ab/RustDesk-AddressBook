from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

TEST_ROOT = Path(tempfile.mkdtemp(prefix="rab-tests-"))
os.environ.setdefault("APP_DATA_DIR", str(TEST_ROOT / "data"))
os.environ.setdefault("BACKUP_DIR", str(TEST_ROOT / "backups"))
os.environ.setdefault("SESSION_COOKIE_SECURE", "false")
os.environ.setdefault("RAB_UPDATE_BASE_URL", "disabled")
os.environ.setdefault("AUTH_LOG_FILE", str(TEST_ROOT / "data" / "logs" / "auth.log"))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402


@pytest.fixture(scope="session")
def app():
    application = create_app()
    application.config.update(TESTING=True, SESSION_COOKIE_SECURE=False, SERVER_NAME="localhost")
    return application


@pytest.fixture()
def clean_app(app):
    with app.app_context():
        db.drop_all()
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(clean_app):
    return clean_app.test_client()


def set_csrf(client, token: str = "test-csrf-token") -> str:
    with client.session_transaction() as session:
        session["csrf_token"] = token
    return token
