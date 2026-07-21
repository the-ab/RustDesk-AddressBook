import json
import os
import secrets
from pathlib import Path

from cryptography.fernet import Fernet


def _read_or_create_runtime_config(data_dir: Path) -> dict:
    data_dir.mkdir(parents=True, exist_ok=True)
    config_file = data_dir / "config.json"

    if config_file.exists():
        with config_file.open("r", encoding="utf-8") as fh:
            cfg = json.load(fh)
    else:
        cfg = {}

    changed = False
    if not cfg.get("SECRET_KEY"):
        cfg["SECRET_KEY"] = secrets.token_hex(48)
        changed = True
    if not cfg.get("FERNET_KEY"):
        cfg["FERNET_KEY"] = Fernet.generate_key().decode("utf-8")
        changed = True
    if not cfg.get("SECURITY_SIGNING_KEY"):
        cfg["SECURITY_SIGNING_KEY"] = secrets.token_hex(64)
        changed = True
    if not cfg.get("SETUP_TOKEN"):
        cfg["SETUP_TOKEN"] = secrets.token_urlsafe(32)
        changed = True

    if changed:
        tmp = config_file.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2)
        tmp.replace(config_file)
    try:
        config_file.chmod(0o600)
    except PermissionError:
        pass

    return cfg


class Config:
    APP_VERSION = "0.5.32-github-release-update-default"
    DATA_DIR = Path(os.environ.get("APP_DATA_DIR", "/data"))
    BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", "/backups"))
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    runtime_config = _read_or_create_runtime_config(DATA_DIR)

    SECRET_KEY = runtime_config["SECRET_KEY"]
    FERNET_KEY = runtime_config["FERNET_KEY"]
    SECURITY_SIGNING_KEY = runtime_config["SECURITY_SIGNING_KEY"]
    SETUP_TOKEN = os.environ.get("RAB_SETUP_TOKEN", runtime_config["SETUP_TOKEN"])

    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DATA_DIR / 'addressbook.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Erlaubt auch größere SQLite-Backups und RustDesk-Serverdatenbanken als Upload.
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", str(100 * 1024 * 1024)))
    RUSTDESK_SERVER_DB = os.environ.get("RUSTDESK_SERVER_DB", "").strip()
    LOG_DIR = Path(os.environ.get("LOG_DIR", str(DATA_DIR / "logs")))
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    AUTH_LOG_FILE = Path(os.environ.get("AUTH_LOG_FILE", str(LOG_DIR / "auth.log")))

    AUTH_LOG_ROTATE_DAYS = int(os.environ.get("AUTH_LOG_ROTATE_DAYS", "7"))
    AUTH_LOG_ROTATE_KEEP = int(os.environ.get("AUTH_LOG_ROTATE_KEEP", "8"))
    TRUST_PROXY_HEADERS = os.environ.get("TRUST_PROXY_HEADERS", "false").lower() in {"1", "true", "yes", "on"}
    LOGIN_FAIL_LIMIT = int(os.environ.get("LOGIN_FAIL_LIMIT", "5"))
    LOGIN_FAIL_WINDOW_SECONDS = int(os.environ.get("LOGIN_FAIL_WINDOW_SECONDS", "900"))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() in {"1", "true", "yes", "on"}
    APP_HSTS = os.environ.get("APP_HSTS", "false").lower() in {"1", "true", "yes", "on"}
    # Sicherheitsrelevante Benutzerzustände werden ausschließlich strikt geprüft.
    USER_SIGNATURE_POLICY = "strict"
    SECURITY_SIGNATURE_VERSION = 2
    AUTH_EVENT_RETENTION_DAYS = int(os.environ.get("AUTH_EVENT_RETENTION_DAYS", "90"))
    AUTH_EVENT_MAX_ROWS = int(os.environ.get("AUTH_EVENT_MAX_ROWS", "50000"))
    SENSITIVE_ACTION_REAUTH_SECONDS = int(os.environ.get("SENSITIVE_ACTION_REAUTH_SECONDS", "1800"))
    FULL_BACKUP_MAX_MEMBERS = int(os.environ.get("FULL_BACKUP_MAX_MEMBERS", "5000"))
    FULL_BACKUP_MAX_TOTAL_BYTES = int(os.environ.get("FULL_BACKUP_MAX_TOTAL_BYTES", str(512 * 1024 * 1024)))
    FULL_BACKUP_MAX_FILE_BYTES = int(os.environ.get("FULL_BACKUP_MAX_FILE_BYTES", str(128 * 1024 * 1024)))
    OIDC_ALLOW_PRIVATE_ISSUER = os.environ.get("OIDC_ALLOW_PRIVATE_ISSUER", "false").lower() in {"1", "true", "yes", "on"}
    DEFAULT_UPDATE_BASE_URL = "https://github.com/the-ab/RustDesk-AddressBook/releases/latest/download"
    RAB_UPDATE_BASE_URL = os.environ.get("RAB_UPDATE_BASE_URL", DEFAULT_UPDATE_BASE_URL).strip() or DEFAULT_UPDATE_BASE_URL
