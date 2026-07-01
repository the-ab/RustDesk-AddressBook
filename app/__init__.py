from __future__ import annotations

import base64
import csv
import hashlib
import hmac
import json
import os
import re
import urllib.error
import urllib.request
import secrets
import shutil
import sqlite3
import subprocess
import tempfile
import time
import tarfile
import zipfile
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timedelta
from io import BytesIO, StringIO
from pathlib import Path

from flask import (
    Flask,
    Response,
    abort,
    jsonify,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
import pyotp
import qrcode
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from .config import Config
from .crypto import decrypt_value, encrypt_value
from .extensions import db, login_manager
from .helpers import csrf_token, normalize_bool, parse_csv_upload, rustdesk_link, validate_csrf
from .models import AuthEvent, Device, Group, Setting, User, utcnow
from .rustdesk_live import RustDeskLiveStatusError, query_hbbs_online_status


DEFAULT_OS_CHOICES = [
    "Windows",
    "Linux",
    "macOS",
    "Android",
    "iOS",
    "Proxmox",
    "QNAP",
    "Synology",
    "Sonstiges",
]

GROUP_COLOR_CHOICES = [
    ("primary", "Blau"),
    ("secondary", "Grau"),
    ("success", "Grün"),
    ("danger", "Rot"),
    ("warning", "Gelb"),
    ("info", "Cyan"),
    ("dark", "Dunkel"),
]

GROUP_ICON_CHOICES = [
    ("collection", "Sammlung"),
    ("hdd-network", "Server / Netzwerk"),
    ("server", "Server"),
    ("pc-display", "Client / PC"),
    ("pc-display-horizontal", "Desktop"),
    ("laptop", "Notebook"),
    ("windows", "Windows"),
    ("ubuntu", "Linux"),
    ("apple", "Apple / macOS"),
    ("android2", "Android"),
    ("phone", "Mobilgerät"),
    ("router", "Router"),
    ("ethernet", "Netzwerk"),
    ("globe2", "Internet / Remote"),
    ("house", "Privat / Zuhause"),
    ("building", "Firma / Gebäude"),
    ("person-workspace", "Arbeitsplatz"),
    ("people", "Kunden / Benutzer"),
    ("shield-lock", "Sicherheit"),
    ("cloud", "Cloud"),
    ("database", "Datenbank"),
    ("device-hdd", "Storage"),
    ("tools", "Wartung"),
    ("wrench-adjustable", "Service"),
    ("tag", "Tag / Kategorie"),
    ("star", "Favoriten"),
    ("folder", "Ordner"),
]

THEME_CHOICES = [
    ("light", "Heller Modus"),
    ("dark", "Darkmode"),
]

STATUS_SOURCE_CHOICES = [
    ("manual", "Nur manuell"),
    ("hbbs", "hbbs Live-Abfrage"),
]

LANGUAGE_CHOICES = [
    ("de", "Deutsch"),
    ("en", "English"),
]

TRANSLATIONS = {
    "en": {
        "nav.devices": "Devices",
        "nav.groups": "Groups",
        "nav.import_export": "Import / Export",
        "nav.backup": "Backup",
        "nav.security": "Security",
        "nav.help": "Help",
        "nav.settings": "Settings",
        "nav.update_available": "Update available",
        "nav.logout": "Logout",
        "common.save": "Save",
        "common.active": "Active",
        "common.inactive": "Inactive",
        "common.error": "Error",
        "common.ok": "OK",
        "common.search": "Search",
        "common.all": "All",
        "common.never_checked": "never checked",
        "common.no_online_check": "no online status check",
        "dashboard.title": "Dashboard",
        "dashboard.subtitle": "Central address book for your RustDesk devices.",
        "dashboard.add_device": "Add device",
        "dashboard.live_status": "Live status hbbs",
        "dashboard.devices": "Devices",
        "dashboard.favorites": "Favorites",
        "dashboard.online": "Online",
        "dashboard.show_all": "Show all",
        "dashboard.no_favorites": "No favorites yet.",
        "dashboard.quick_search": "Quick search",
        "dashboard.groups": "Groups",
        "dashboard.no_groups": "No groups yet.",
        "dashboard.recent": "Recently changed",
        "dashboard.no_devices": "No devices created yet.",
        "devices.title": "Devices",
        "devices.subtitle": "Search, filter, check online status and connect directly with RustDesk.",
        "devices.add_device": "Add device",
        "devices.live_status": "Live status hbbs",
        "devices.search": "Search",
        "devices.group": "Group",
        "devices.all_groups": "All groups",
        "devices.device_type": "Device type",
        "devices.favorites": "Favorites",
        "devices.only_favorites": "Only favorites",
        "devices.sort": "Sort",
        "devices.no_results": "No devices found.",
        "devices.first_device": "Create first device",
        "devices.hbbs_missing": "For automatic online status, enter your hbbs host under Settings → Online status and then use Live status hbbs. Server DB import and diagnostics are available under Import / Export.",
        "settings.title": "Settings",
        "settings.subtitle": "Manage appearance, language, admin security, imports, online status and update checks.",
        "settings.menu.display": "Display & language",
        "settings.menu.admin": "Admin account",
        "settings.menu.twofa": "2FA / Authenticator",
        "settings.menu.devices": "Device types",
        "settings.menu.online": "Online status",
        "settings.menu.bruteforce": "Brute-force protection",
        "settings.menu.updates": "Update check",
        "settings.menu.notes": "Security notes",
        "settings.display.title": "Display & language",
        "settings.display.theme": "Color scheme",
        "settings.display.language": "Language",
        "settings.display.language_help": "Currently available: German and English. The core user interface is translated; technical logs and some imported content remain unchanged.",
        "settings.display.save": "Save display settings",
        "settings.admin.username_title": "Change admin username",
        "settings.admin.current_username": "Current username",
        "settings.admin.new_username": "New username",
        "settings.admin.username_help": "Allowed: letters, digits, dot, underscore, hyphen and @.",
        "settings.admin.current_password_confirm": "Current password for confirmation",
        "settings.admin.save_username": "Save username",
        "settings.admin.password_title": "Change password",
        "settings.admin.current_password": "Current password",
        "settings.admin.new_password": "New password",
        "settings.admin.repeat_password": "Repeat new password",
        "settings.twofa.title": "2FA / Authenticator app",
        "settings.twofa.subtitle": "Additional one-time code for the admin login.",
        "settings.os.title": "Device type / operating system choices",
        "settings.os.values": "Choices",
        "settings.os.help": "One entry per line. This list appears in the device form. Existing devices keep their current value.",
        "settings.os.save": "Save choices",
        "settings.status.title": "Online status",
        "settings.status.source": "Status source",
        "settings.status.source_help": "Automatic online status is queried through hbbs live. If the query fails, existing states remain unchanged.",
        "settings.status.host": "hbbs host",
        "settings.status.port": "hbbs Online/NAT TCP port",
        "settings.status.timeout": "Timeout seconds",
        "settings.status.requester": "Requester ID",
        "settings.status.batch": "Batch size",
        "settings.status.auto": "Automatic query",
        "settings.status.auto_label": "Automatically query online status while the WebUI is open",
        "settings.status.interval": "Interval",
        "settings.status.unit": "Unit",
        "settings.status.minutes": "Minutes (1–10)",
        "settings.status.hours": "Hours (1–24)",
        "settings.status.warning": "This function uses RustDesk OnlineRequest/OnlineResponse against hbbs. It is useful in practice, but not an officially documented web API and may change with RustDesk versions.",
        "settings.status.save": "Save status source",
        "settings.status.last_check": "Last status check",
        "settings.status.no_check": "No hbbs live check has been performed yet.",
        "settings.bruteforce.title": "Brute-force protection",
        "settings.bruteforce.help": "Applies to failed password and 2FA attempts per IP address or username. The fail2ban/CrowdSec log remains active as an additional layer.",
        "settings.bruteforce.failures": "Failed attempts",
        "settings.bruteforce.window": "Window minutes",
        "settings.bruteforce.save": "Save lockout settings",
        "settings.update.title": "Update check",
        "settings.update.help": "Checks the configured download server through latest.txt and shows available changes.",
        "settings.update.now": "Check now",
        "settings.update.none": "No online update check has been performed yet.",
        "settings.update.available": "Update available",
        "settings.update.current": "Current",
        "settings.update.changes": "Changes in this version",
        "settings.update.auto": "Check automatically",
        "settings.update.interval": "Interval",
        "settings.update.save": "Save update check",
        "settings.update.install_hint": "Updates are installed with ./scripts/update.sh. The script checks local ZIP files in updates/ and then the download server automatically.",
        "settings.security.title": "Security notes",
        "settings.security.https": "Run the app through HTTPS when it is reachable outside your LAN.",
        "settings.security.fernet": "Device passwords in the database are encrypted with Fernet. The key is stored in ./data/config.json.",
        "settings.security.backups": "For portable backups, create encrypted backups with AES-256-GCM and PBKDF2-HMAC-SHA256.",
        "settings.security.data_backup": "Back up ./data and ./backups regularly. Without ./data/config.json, saved device passwords cannot be decrypted.",
        "theme.light": "Light mode",
        "theme.dark": "Dark mode",
        "status.manual": "Manual only",
        "status.hbbs": "hbbs live query",
        "sort.online": "Online first",
        "sort.name": "Name A-Z",
        "sort.favorites": "Favorites first",
        "sort.updated": "Recently changed",
    }
}


def _short_app_version(version: str) -> str:
    raw = str(version or "dev").strip()
    if "-" in raw:
        return raw.split("-", 1)[0]
    return raw


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        db.create_all()
        _migrate_schema()
        _ensure_user_security_signatures()
        _create_default_groups()

    register_template_helpers(app)
    register_hooks(app)
    register_routes(app)
    return app


@login_manager.user_loader
def load_user(user_id: str):
    if not user_id.isdigit():
        return None
    return db.session.get(User, int(user_id))



def _migrate_schema() -> None:
    """Small SQLite migrations for existing installations without Alembic."""
    with db.engine.begin() as conn:
        user_cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()}
        if "totp_secret_encrypted" not in user_cols:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN totp_secret_encrypted TEXT")
        if "totp_enabled" not in user_cols:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN totp_enabled BOOLEAN NOT NULL DEFAULT 0")
        if "totp_recovery_hashes" not in user_cols:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN totp_recovery_hashes TEXT")
        security_signature_created = False
        if "security_signature" not in user_cols:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN security_signature TEXT")
            security_signature_created = True
        current_app.config["_SECURITY_SIGNATURE_INITIALIZE_MISSING"] = security_signature_created


def _security_signature_payload(user: User) -> str:
    data = {
        "username": user.username or "",
        "password_hash": user.password_hash or "",
        "totp_secret_encrypted": user.totp_secret_encrypted or "",
        "totp_enabled": bool(user.totp_enabled),
        "totp_recovery_hashes": user.totp_recovery_hashes or "",
    }
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _security_hmac(payload: str) -> str:
    key = str(current_app.config.get("SECURITY_SIGNING_KEY", "")).encode("utf-8")
    return hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def _sign_user_security_state(user: User) -> None:
    user.security_signature = _security_hmac(_security_signature_payload(user))


def _verify_user_security_state(user: User) -> bool:
    expected = _security_hmac(_security_signature_payload(user))
    stored = getattr(user, "security_signature", None) or ""
    if not stored:
        return False
    return hmac.compare_digest(stored, expected)


def _user_signature_policy() -> str:
    policy = str(current_app.config.get("USER_SIGNATURE_POLICY", "repair_on_verified_login")).strip().lower()
    if policy not in {"strict", "repair_on_verified_login"}:
        policy = "strict"
    return policy


def _reseal_user_after_verified_auth(user: User, *, username: str, reason: str) -> None:
    _sign_user_security_state(user)
    db.session.commit()
    _record_auth_event("security_resealed", username=username, success=True, message=reason)


def _ensure_user_security_signatures() -> None:
    # Only initialize missing signatures during the one-time migration that creates
    # the column. If the column already existed and a signature is missing, treat
    # it as suspicious rather than silently resealing a possibly manipulated row.
    if not current_app.config.get("_SECURITY_SIGNATURE_INITIALIZE_MISSING"):
        return
    changed = False
    for user in User.query.all():
        if not getattr(user, "security_signature", None):
            _sign_user_security_state(user)
            changed = True
    if changed:
        db.session.commit()


def _client_ip() -> str:
    if current_app.config.get("TRUST_PROXY_HEADERS"):
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()[:64]
        real_ip = request.headers.get("X-Real-IP", "")
        if real_ip:
            return real_ip.strip()[:64]
    return (request.remote_addr or "unknown")[:64]


def _record_auth_event(event_type: str, *, username: str = "", success: bool = False, message: str = "") -> None:
    username = (username or "").strip()[:120]
    ip = _client_ip()
    user_agent = (request.headers.get("User-Agent", "") or "")[:255]
    message = (message or "")[:1000]
    try:
        db.session.add(AuthEvent(
            event_type=(event_type or "unknown")[:64],
            username=username or None,
            ip_address=ip,
            user_agent=user_agent or None,
            success=bool(success),
            message=message or None,
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()
    _write_auth_log_line(event_type, username=username, ip=ip, success=success, message=message, user_agent=user_agent)


def _write_auth_log_line(event_type: str, *, username: str, ip: str, success: bool, message: str, user_agent: str) -> None:
    auth_log = Path(current_app.config.get("AUTH_LOG_FILE"))
    auth_log.parent.mkdir(parents=True, exist_ok=True)
    stamp = utcnow().isoformat()
    result = "OK" if success else "FAIL"
    marker = "RAB_AUTH_OK" if success else "RAB_AUTH_FAIL"
    def clean(value: str) -> str:
        return str(value or "").replace("\n", " ").replace("\r", " ")[:500]
    line = (
        f"{stamp} {marker} result={result} event={clean(event_type)} "
        f"ip={clean(ip)} username={clean(username) or '-'} "
        f"message=\"{clean(message)}\" user_agent=\"{clean(user_agent)}\"\n"
    )
    try:
        with auth_log.open("a", encoding="utf-8") as fh:
            fh.write(line)
        try:
            auth_log.chmod(0o600)
        except PermissionError:
            pass
    except OSError:
        pass


def _is_login_blocked(username: str) -> tuple[bool, int]:
    brute = _get_bruteforce_settings()
    limit = brute["limit"]
    window = brute["window_seconds"]
    since = utcnow() - timedelta(seconds=window)
    ip = _client_ip()
    fail_types = ["password_fail", "2fa_fail"]
    base = AuthEvent.query.filter(AuthEvent.success.is_(False), AuthEvent.created_at >= since, AuthEvent.event_type.in_(fail_types))
    ip_count = base.filter(AuthEvent.ip_address == ip).count() if ip else 0
    user_count = base.filter(AuthEvent.username == (username or "").strip()[:120]).count() if username else 0
    if ip_count >= limit or user_count >= limit:
        oldest = base.filter((AuthEvent.ip_address == ip) | (AuthEvent.username == (username or "").strip()[:120])).order_by(AuthEvent.created_at.asc()).first()
        if oldest and oldest.created_at:
            try:
                elapsed = int((utcnow() - oldest.created_at).total_seconds())
            except TypeError:
                elapsed = int((datetime.utcnow() - oldest.created_at.replace(tzinfo=None)).total_seconds())
            return True, max(window - elapsed, 1)
        return True, window
    return False, 0


def _create_default_groups() -> None:
    if Group.query.count() > 0:
        return
    for name, color, icon in [
        ("Server", "primary", "hdd-network"),
        ("Clients", "success", "pc-display"),
        ("Privat", "info", "house"),
    ]:
        db.session.add(Group(name=name, color=color, icon=icon))
    db.session.commit()


def register_template_helpers(app: Flask) -> None:
    app.jinja_env.globals["csrf_token"] = csrf_token
    app.jinja_env.globals["rustdesk_link"] = rustdesk_link
    app.jinja_env.globals["now"] = lambda: datetime.now()
    app.jinja_env.globals["app_version"] = app.config.get("APP_VERSION", "dev")
    app.jinja_env.globals["app_version_short"] = _short_app_version(app.config.get("APP_VERSION", "dev"))
    app.jinja_env.filters["decrypt"] = decrypt_value
    app.jinja_env.globals["os_icon_class"] = _os_icon_class
    app.jinja_env.globals["get_os_choices"] = _get_os_choices
    app.jinja_env.globals["group_icon_choices"] = GROUP_ICON_CHOICES
    app.jinja_env.globals["group_color_choices"] = GROUP_COLOR_CHOICES
    app.jinja_env.globals["theme_choices"] = THEME_CHOICES
    app.jinja_env.globals["language_choices"] = LANGUAGE_CHOICES
    app.jinja_env.globals["get_language"] = _get_language
    app.jinja_env.globals["t"] = _t
    app.jinja_env.globals["get_theme_mode"] = _get_theme_mode
    app.jinja_env.globals["status_source_choices"] = STATUS_SOURCE_CHOICES
    app.jinja_env.globals["get_status_settings"] = _get_status_settings
    app.jinja_env.globals["get_status_check_info"] = _get_status_check_info
    app.jinja_env.globals["get_auto_status_settings"] = _get_auto_status_settings
    app.jinja_env.globals["rustdesk_server_db_configured"] = lambda: bool(current_app.config.get("RUSTDESK_SERVER_DB"))
    app.jinja_env.globals["rustdesk_server_db_exists"] = _rustdesk_server_db_exists
    app.jinja_env.globals["rustdesk_server_db_status"] = _rustdesk_server_db_status
    app.jinja_env.globals["get_ssh_import_settings"] = _get_ssh_import_settings
    app.jinja_env.globals["get_bruteforce_settings"] = _get_bruteforce_settings
    app.jinja_env.globals["get_update_check_info"] = _get_update_check_info
    app.jinja_env.globals["get_update_auto_check_settings"] = _get_update_auto_check_settings

    @app.context_processor
    def inject_dynamic_template_values():
        return {
            "os_choices": _get_os_choices(),
            "theme_mode": _get_theme_mode(),
            "app_language": _get_language(),
            "theme_choices": _translated_theme_choices(),
            "status_source_choices": _translated_status_source_choices(),
            "status_settings": _get_status_settings(),
            "status_check_info": _get_status_check_info(),
            "auto_status_settings": _get_auto_status_settings(),
            "bruteforce_settings": _get_bruteforce_settings(),
            "update_check_info": _get_update_check_info(),
            "update_auto_check_settings": _get_update_auto_check_settings(),
        }


    @app.template_filter("datetime_de")
    def datetime_de(value):
        if not value:
            return "-"
        try:
            return value.astimezone().strftime("%d.%m.%Y %H:%M")
        except Exception:
            return value.strftime("%d.%m.%Y %H:%M")

    @app.template_filter("timestamp_de")
    def timestamp_de(value):
        if not value:
            return "-"
        return datetime.fromtimestamp(value).strftime("%d.%m.%Y %H:%M")

    @app.template_filter("taglist")
    def taglist(value):
        if not value:
            return []
        return [x.strip() for x in value.split(",") if x.strip()]


def register_hooks(app: Flask) -> None:
    @app.before_request
    def app_before_request():
        validate_csrf()
        if request.endpoint in {"static", "setup"}:
            return None
        has_user = db.session.query(User.id).first() is not None
        if not has_user:
            return redirect(url_for("setup"))
        if current_user.is_authenticated and not _verify_user_security_state(current_user):
            username = getattr(current_user, "username", "")
            _record_auth_event("security_signature_invalid_session", username=username, success=False, message="Aktive Sitzung beendet: Benutzer-Sicherheitsdatenbank-Signatur ungültig")
            logout_user()
            session.clear()
            flash("Sitzung wurde aus Sicherheitsgründen beendet. Bitte melde dich erneut an.", "warning")
            return redirect(url_for("login"))
        return None

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Content-Security-Policy", "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; font-src 'self' https://cdn.jsdelivr.net data:; img-src 'self' data:; connect-src 'self'; frame-ancestors 'self'; base-uri 'self'; form-action 'self'")
        if current_app.config.get("APP_HSTS") and request.is_secure:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


def register_routes(app: Flask) -> None:
    @app.route("/setup", methods=["GET", "POST"])
    def setup():
        if db.session.query(User.id).first() is not None:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            password2 = request.form.get("password2", "")

            if not username:
                flash("Benutzername fehlt.", "danger")
            elif len(password) < 8:
                flash("Das Passwort muss mindestens 8 Zeichen haben.", "danger")
            elif password != password2:
                flash("Die Passwörter stimmen nicht überein.", "danger")
            else:
                user = User(username=username)
                user.set_password(password)
                _sign_user_security_state(user)
                db.session.add(user)
                db.session.commit()
                _record_auth_event("setup_login", username=username, success=True, message="Installation abgeschlossen und Admin angemeldet")
                login_user(user)
                flash("Installation abgeschlossen.", "success")
                return redirect(url_for("dashboard"))

        return render_template("setup.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            blocked, wait_seconds = _is_login_blocked(username)
            if blocked:
                _record_auth_event("rate_limited", username=username, success=False, message=f"Zu viele Fehlversuche; gesperrt für ca. {wait_seconds} Sekunden")
                flash("Zu viele fehlgeschlagene Anmeldeversuche. Bitte später erneut versuchen.", "danger")
                return render_template("login.html")

            user = User.query.filter_by(username=username).first()
            signature_ok = _verify_user_security_state(user) if user else True

            if user and user.check_password(password):
                next_url = request.args.get("next")
                signature_repair_needed = not signature_ok
                if signature_repair_needed and _user_signature_policy() == "strict":
                    _record_auth_event("security_signature_invalid", username=username, success=False, message="Benutzer-Sicherheitsdatenbank-Signatur ungültig; Login durch Strict-Policy blockiert")
                    flash("Anmeldung blockiert: Die Benutzer-Sicherheitsdaten haben keine gültige Signatur. Für Recovery USER_SIGNATURE_POLICY temporär auf repair_on_verified_login setzen oder neu installieren.", "danger")
                    return render_template("login.html")

                if getattr(user, "totp_enabled", False):
                    _record_auth_event("password_ok_2fa_required", username=username, success=True, message=("Passwort korrekt; 2FA erforderlich; Signatur-Reparatur nach 2FA" if signature_repair_needed else "Passwort korrekt; 2FA erforderlich"))
                    session["pending_2fa_user_id"] = user.id
                    session["pending_2fa_next"] = next_url or url_for("dashboard")
                    session["pending_2fa_signature_repair"] = bool(signature_repair_needed)
                    return redirect(url_for("login_2fa"))

                user.last_login_at = utcnow()
                if signature_repair_needed:
                    _reseal_user_after_verified_auth(user, username=username, reason="Benutzer-Sicherheitsdaten nach gültigem Passwort neu signiert")
                    flash("Angemeldet. Die Benutzer-Sicherheitsdaten wurden nach erfolgreicher Authentifizierung neu signiert.", "warning")
                else:
                    _sign_user_security_state(user)
                    db.session.commit()
                    flash("Angemeldet.", "success")
                _record_auth_event("login_success", username=username, success=True, message=("Login ohne 2FA erfolgreich; Signatur neu versiegelt" if signature_repair_needed else "Login ohne 2FA erfolgreich"))
                login_user(user)
                return redirect(next_url or url_for("dashboard"))
            _record_auth_event("password_fail", username=username, success=False, message="Ungültiger Benutzername oder Passwort")
            flash("Benutzername oder Passwort ist falsch.", "danger")

        return render_template("login.html")

    @app.route("/login/2fa", methods=["GET", "POST"])
    def login_2fa():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        user_id = session.get("pending_2fa_user_id")
        user = db.session.get(User, int(user_id)) if str(user_id).isdigit() else None
        if not user or not getattr(user, "totp_enabled", False):
            session.pop("pending_2fa_user_id", None)
            session.pop("pending_2fa_next", None)
            flash("Bitte erneut anmelden.", "warning")
            return redirect(url_for("login"))
        signature_ok = _verify_user_security_state(user)
        signature_repair_pending = bool(session.get("pending_2fa_signature_repair"))
        if not signature_ok and not signature_repair_pending:
            _record_auth_event("security_signature_invalid", username=getattr(user, "username", ""), success=False, message="2FA-Anmeldung blockiert: Benutzer-Sicherheitsdatenbank-Signatur ungültig")
            session.pop("pending_2fa_user_id", None)
            session.pop("pending_2fa_next", None)
            session.pop("pending_2fa_signature_repair", None)
            flash("Anmeldung aus Sicherheitsgründen blockiert. Bitte melde dich erneut an.", "danger")
            return redirect(url_for("login"))
        if request.method == "POST":
            blocked, wait_seconds = _is_login_blocked(user.username)
            if blocked:
                _record_auth_event("rate_limited", username=user.username, success=False, message=f"2FA blockiert nach Fehlversuchen; gesperrt für ca. {wait_seconds} Sekunden")
                flash("Zu viele fehlgeschlagene Anmeldeversuche. Bitte später erneut versuchen.", "danger")
                return redirect(url_for("login"))
            code = request.form.get("totp_code", "")
            ok, method = _verify_second_factor_for_user(user, code, consume_recovery=True)
            if ok:
                user.last_login_at = utcnow()
                repair_done = bool(session.pop("pending_2fa_signature_repair", None))
                _sign_user_security_state(user)
                db.session.commit()
                _record_auth_event("login_success_2fa", username=user.username, success=True, message=(("Login mit Wiederherstellungscode" if method == "recovery" else "Login mit TOTP") + ("; Signatur neu versiegelt" if repair_done else "")))
                if repair_done:
                    _record_auth_event("security_resealed", username=user.username, success=True, message="Benutzer-Sicherheitsdaten nach Passwort plus 2FA neu signiert")
                login_user(user)
                next_url = session.pop("pending_2fa_next", None) or url_for("dashboard")
                session.pop("pending_2fa_user_id", None)
                if repair_done:
                    flash("Die Benutzer-Sicherheitsdaten wurden nach erfolgreicher 2FA neu signiert.", "warning")
                if method == "recovery":
                    remaining = _recovery_code_count(user)
                    flash(f"Angemeldet. Ein Wiederherstellungscode wurde verbraucht. Verbleibend: {remaining}.", "warning")
                else:
                    flash("Angemeldet.", "success")
                return redirect(next_url)
            _record_auth_event("2fa_fail", username=user.username, success=False, message="Ungültiger 2FA- oder Wiederherstellungscode")
            flash("2FA-Code oder Wiederherstellungscode ist ungültig.", "danger")

        return render_template("login_2fa.html")

    @app.route("/logout", methods=["POST"])
    @login_required
    def logout():
        username = current_user.username if current_user.is_authenticated else ""
        _record_auth_event("logout", username=username, success=True, message="Benutzer abgemeldet")
        logout_user()
        flash("Abgemeldet.", "info")
        return redirect(url_for("login"))

    @app.route("/")
    @login_required
    def dashboard():
        total_devices = Device.query.count()
        favorite_devices = Device.query.filter_by(favorite=True).count()
        online_devices = Device.query.filter_by(online=True).count()
        groups = Group.query.order_by(Group.name.asc()).all()
        favorites = Device.query.filter_by(favorite=True).order_by(Device.name.asc()).limit(8).all()
        recent = Device.query.order_by(Device.updated_at.desc()).limit(8).all()
        return render_template(
            "dashboard.html",
            total_devices=total_devices,
            favorite_devices=favorite_devices,
            online_devices=online_devices,
            groups=groups,
            favorites=favorites,
            recent=recent,
        )

    @app.route("/devices")
    @login_required
    def devices():
        q = request.args.get("q", "").strip()
        group_id = request.args.get("group", "").strip()
        fav = request.args.get("fav", "").strip()
        os_filter = request.args.get("os", "").strip()
        sort = request.args.get("sort", "online").strip().lower()

        query = Device.query
        if q:
            like = f"%{q}%"
            query = query.filter(
                or_(
                    Device.name.ilike(like),
                    Device.rustdesk_id.ilike(like),
                    Device.customer.ilike(like),
                    Device.location.ilike(like),
                    Device.os.ilike(like),
                    Device.tags.ilike(like),
                    Device.notes.ilike(like),
                )
            )
        if group_id.isdigit():
            query = query.filter(Device.group_id == int(group_id))
        if fav == "1":
            query = query.filter(Device.favorite.is_(True))
        if os_filter:
            query = query.filter(Device.os == os_filter)

        sort_choices = {
            "online": _t("sort.online", "Online zuerst"),
            "name": _t("sort.name", "Name A-Z"),
            "favorites": _t("sort.favorites", "Favoriten zuerst"),
            "updated": _t("sort.updated", "Zuletzt geändert"),
        }
        if sort not in sort_choices:
            sort = "online"
        if sort == "name":
            query = query.order_by(Device.name.asc())
        elif sort == "favorites":
            query = query.order_by(Device.favorite.desc(), Device.online.desc(), Device.name.asc())
        elif sort == "updated":
            query = query.order_by(Device.updated_at.desc(), Device.online.desc(), Device.name.asc())
        else:
            query = query.order_by(Device.online.desc(), Device.favorite.desc(), Device.name.asc())

        all_devices = query.all()
        groups = Group.query.order_by(Group.name.asc()).all()
        available_os = sorted({row[0] for row in db.session.query(Device.os).filter(Device.os.isnot(None)).all() if row[0]})
        return render_template(
            "devices.html",
            devices=all_devices,
            groups=groups,
            q=q,
            selected_group=group_id,
            fav=fav,
            selected_os=os_filter,
            selected_sort=sort,
            sort_choices=sort_choices,
            available_os=available_os,
        )

    @app.route("/devices/new", methods=["GET", "POST"])
    @login_required
    def device_new():
        groups = Group.query.order_by(Group.name.asc()).all()
        if request.method == "POST":
            device = Device()
            _fill_device_from_form(device)
            db.session.add(device)
            db.session.commit()
            flash("Gerät wurde angelegt.", "success")
            return redirect(url_for("devices"))
        return render_template("device_form.html", device=None, groups=groups)

    @app.route("/devices/<int:device_id>/edit", methods=["GET", "POST"])
    @login_required
    def device_edit(device_id: int):
        device = db.session.get(Device, device_id) or abort(404)
        groups = Group.query.order_by(Group.name.asc()).all()
        if request.method == "POST":
            _fill_device_from_form(device)
            db.session.commit()
            flash("Gerät wurde gespeichert.", "success")
            return redirect(url_for("devices"))
        return render_template("device_form.html", device=device, groups=groups)

    @app.route("/devices/<int:device_id>/delete", methods=["POST"])
    @login_required
    def device_delete(device_id: int):
        device = db.session.get(Device, device_id) or abort(404)
        db.session.delete(device)
        db.session.commit()
        flash("Gerät wurde gelöscht.", "info")
        return redirect(url_for("devices"))

    @app.route("/devices/<int:device_id>/connect")
    @login_required
    def device_connect(device_id: int):
        device = db.session.get(Device, device_id) or abort(404)
        return redirect(rustdesk_link(device.rustdesk_id, decrypt_value(device.encrypted_password)))

    @app.route("/devices/<int:device_id>/password", methods=["POST"])
    @login_required
    def device_password(device_id: int):
        device = db.session.get(Device, device_id) or abort(404)
        return jsonify({"password": decrypt_value(device.encrypted_password)})


    @app.route("/devices/<int:device_id>/favorite", methods=["POST"])
    @login_required
    def device_toggle_favorite(device_id: int):
        device = db.session.get(Device, device_id) or abort(404)
        device.favorite = not device.favorite
        db.session.commit()
        return redirect(request.referrer or url_for("devices"))

    @app.route("/devices/<int:device_id>/online", methods=["POST"])
    @login_required
    def device_toggle_online(device_id: int):
        device = db.session.get(Device, device_id) or abort(404)
        device.online = not device.online
        db.session.commit()
        return redirect(request.referrer or url_for("devices"))

    @app.route("/groups", methods=["GET", "POST"])
    @login_required
    def groups():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            color = _normalize_group_color(request.form.get("color", "secondary"))
            icon = _normalize_group_icon(request.form.get("icon", "collection"))
            if not name:
                flash("Gruppenname fehlt.", "danger")
            elif Group.query.filter_by(name=name).first():
                flash("Diese Gruppe existiert bereits.", "warning")
            else:
                db.session.add(Group(name=name, color=color, icon=icon))
                db.session.commit()
                flash("Gruppe wurde angelegt.", "success")
            return redirect(url_for("groups"))
        return render_template("groups.html", groups=Group.query.order_by(Group.name.asc()).all())

    @app.route("/groups/<int:group_id>/edit", methods=["POST"])
    @login_required
    def group_edit(group_id: int):
        group = db.session.get(Group, group_id) or abort(404)
        name = request.form.get("name", "").strip()
        color = _normalize_group_color(request.form.get("color", "secondary"))
        icon = _normalize_group_icon(request.form.get("icon", "collection"))
        if not name:
            flash("Gruppenname fehlt.", "danger")
            return redirect(url_for("groups"))
        duplicate = Group.query.filter(Group.name == name, Group.id != group.id).first()
        if duplicate:
            flash("Eine andere Gruppe mit diesem Namen existiert bereits.", "warning")
            return redirect(url_for("groups"))
        group.name = name
        group.color = color
        group.icon = icon
        db.session.commit()
        flash("Gruppe wurde gespeichert.", "success")
        return redirect(url_for("groups"))

    @app.route("/groups/<int:group_id>/delete", methods=["POST"])
    @login_required
    def group_delete(group_id: int):
        group = db.session.get(Group, group_id) or abort(404)
        Device.query.filter_by(group_id=group.id).update({"group_id": None})
        db.session.delete(group)
        db.session.commit()
        flash("Gruppe wurde gelöscht. Zugeordnete Geräte bleiben erhalten.", "info")
        return redirect(url_for("groups"))

    @app.route("/import", methods=["GET", "POST"])
    @login_required
    def import_devices():
        if request.method == "POST":
            upload = request.files.get("csv_file")
            if not upload or not upload.filename:
                flash("Bitte eine CSV-Datei auswählen.", "danger")
                return redirect(url_for("import_devices"))
            rows = parse_csv_upload(upload)
            count = 0
            for row in rows:
                name = row.get("name") or row.get("gerät") or row.get("device")
                rustdesk_id = row.get("rustdesk_id") or row.get("rustdesk-id") or row.get("id")
                if not name or not rustdesk_id:
                    continue
                group_name = row.get("group") or row.get("gruppe")
                group = _get_or_create_group(group_name) if group_name else None
                device = Device(
                    name=name,
                    rustdesk_id=rustdesk_id,
                    customer=row.get("customer") or row.get("kunde"),
                    location=row.get("location") or row.get("standort"),
                    os=_normalize_os(row.get("os") or row.get("betriebssystem") or row.get("device_type") or row.get("gerätetyp") or row.get("platform")),
                    tags=row.get("tags"),
                    notes=row.get("notes") or row.get("notizen"),
                    favorite=normalize_bool(row.get("favorite") or row.get("favorit")),
                    online=normalize_bool(row.get("online")),
                    group=group,
                    encrypted_password=encrypt_value(row.get("password") or row.get("passwort")),
                )
                db.session.add(device)
                count += 1
            db.session.commit()
            flash(f"Import abgeschlossen: {count} Geräte angelegt.", "success")
            return redirect(url_for("devices"))
        return render_template("import.html", groups=Group.query.order_by(Group.name.asc()).all())

    @app.route("/import/rustdesk-server", methods=["GET", "POST"])
    @login_required
    def import_rustdesk_server():
        """Import devices from the RustDesk OSS server SQLite database.

        The free RustDesk server (hbbs) stores known peers in db_v2.sqlite3.
        This import intentionally reads a copy uploaded by the admin and never
        writes back to the RustDesk server database.
        """
        if request.method == "POST":
            uploads = [f for f in request.files.getlist("server_files") if f and f.filename]
            legacy_upload = request.files.get("sqlite_file")
            if legacy_upload and legacy_upload.filename:
                uploads.append(legacy_upload)

            update_existing = normalize_bool(request.form.get("update_existing"))
            default_group_name = _resolve_group_name_from_form(default="RustDesk Server")

            if not uploads:
                flash("Bitte db_v2.sqlite3 oder ein ZIP mit db_v2.sqlite3, db_v2.sqlite3-wal und optional db_v2.sqlite3-shm auswählen.", "danger")
                return redirect(url_for("import_rustdesk_server"))

            try:
                with _stage_rustdesk_sqlite_uploads(uploads) as staged_db:
                    result = _import_from_rustdesk_sqlite(staged_db, default_group_name, update_existing)
            except sqlite3.DatabaseError as exc:
                flash(f"Die Datei konnte nicht als RustDesk-SQLite-Datenbank gelesen werden: {exc}", "danger")
                return redirect(url_for("import_rustdesk_server"))
            except ValueError as exc:
                flash(str(exc), "danger")
                return redirect(url_for("import_rustdesk_server"))

            wal_note = " WAL wurde berücksichtigt." if result.get("wal_seen") else " Keine WAL-Datei im Upload gefunden."
            status_note = " Online-Status wird nicht aus der Server-DB übernommen; nutze dafür Live-Status hbbs."
            flash(
                f"RustDesk-Server-Import abgeschlossen: {result['created']} neu, "
                f"{result['updated']} aktualisiert, {result['skipped']} übersprungen."
                f"{wal_note}{status_note}",
                "success",
            )
            return redirect(url_for("devices"))

        return render_template("import_rustdesk_server.html", groups=Group.query.order_by(Group.name.asc()).all())

    @app.route("/sync/rustdesk-status", methods=["POST"])
    @login_required
    def sync_rustdesk_status():
        flash("Status aus Server-DB wurde entfernt. Der Online-Status wird jetzt über hbbs Live abgefragt; die Server-DB bleibt für Import und Diagnose erhalten.", "info")
        return redirect(request.referrer or url_for("devices"))

    @app.route("/sync/rustdesk-live-status", methods=["POST"])
    @login_required
    def sync_rustdesk_live_status():
        try:
            result = _sync_hbbs_live_status(trigger="Manuell")
        except RustDeskLiveStatusError as exc:
            db.session.rollback()
            _record_status_check(False, str(exc), trigger="Manuell")
            flash(f"hbbs Live-Abfrage fehlgeschlagen: {exc}", "danger")
            return redirect(request.referrer or url_for("devices"))

        flash(
            f"hbbs Live-Status aktualisiert: {result['updated']} geändert, "
            f"{result['online']} online, {result['offline']} offline. "
            f"Letzte Response states={result.get('states') or '-'}.",
            "success",
        )
        return redirect(request.referrer or url_for("devices"))

    @app.route("/api/status/auto-check", methods=["POST"])
    @login_required
    def api_status_auto_check():
        auto = _get_auto_status_settings()
        if not auto["enabled"]:
            return jsonify({"ok": True, "skipped": True, "reason": "auto_disabled"})
        if _get_status_settings()["source"] != "hbbs":
            return jsonify({"ok": True, "skipped": True, "reason": "status_source_not_hbbs"})
        last_epoch = _get_status_last_checked_epoch()
        now_epoch = int(time.time())
        if last_epoch and now_epoch - last_epoch < auto["interval_seconds"]:
            return jsonify({"ok": True, "skipped": True, "reason": "not_due", "next_in": auto["interval_seconds"] - (now_epoch - last_epoch)})
        try:
            result = _sync_hbbs_live_status(trigger="Automatik")
        except RustDeskLiveStatusError as exc:
            db.session.rollback()
            _record_status_check(False, str(exc), trigger="Automatik")
            return jsonify({"ok": False, "error": str(exc)}), 200
        return jsonify({"ok": True, "skipped": False, **result})

    @app.route("/sync/rustdesk-mounted-import", methods=["POST"])
    @login_required
    def sync_rustdesk_mounted_import():
        configured = current_app.config.get("RUSTDESK_SERVER_DB", "")
        if not configured:
            flash("Kein RUSTDESK_SERVER_DB gesetzt. Binde die RustDesk-Datei db_v2.sqlite3 read-only in den Container ein.", "warning")
            return redirect(request.referrer or url_for("import_rustdesk_server"))

        db_path = Path(configured)
        if not db_path.is_file():
            flash(f"RustDesk-Serverdatenbank nicht gefunden: {configured}", "danger")
            return redirect(request.referrer or url_for("import_rustdesk_server"))

        try:
            result = _import_from_rustdesk_sqlite(db_path, _resolve_group_name_from_form(default="RustDesk Server"), True)
        except sqlite3.DatabaseError as exc:
            flash(f"Echtzeit-Import aus der eingebundenen RustDesk-Datenbank fehlgeschlagen: {exc}", "danger")
            return redirect(request.referrer or url_for("import_rustdesk_server"))
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(request.referrer or url_for("import_rustdesk_server"))

        wal_note = " WAL sichtbar und per SQLite-Snapshot berücksichtigt." if _sqlite_family_info(db_path)["wal"] else " Keine WAL-Datei sichtbar."
        flash(
            f"Echtzeit-Import aus eingebundener Server-DB abgeschlossen: {result['created']} neu, "
            f"{result['updated']} aktualisiert, {result['skipped']} übersprungen.{wal_note}",
            "success",
        )
        return redirect(request.referrer or url_for("import_rustdesk_server"))

    @app.route("/import/rustdesk-ssh/test", methods=["POST"])
    @login_required
    def rustdesk_ssh_test():
        _save_ssh_import_settings_from_form()
        try:
            result = _ssh_fetch_and_inspect_rustdesk_db()
        except ValueError as exc:
            session["ssh_import_result"] = {"ok": False, "message": str(exc), "finished_at": _ui_timestamp()}
            flash(f"SSH-Test fehlgeschlagen: {exc}", "danger")
            return redirect(url_for("import_devices"))

        result["finished_at"] = _ui_timestamp()
        session["ssh_import_result"] = result
        if result.get("ok"):
            flash(
                f"SSH-Test erfolgreich: {result.get('bytes', 0)} Bytes übertragen, "
                f"peer-Tabelle vorhanden, {result.get('peer_count', 0)} Geräte gefunden, "
                f"Integrity-Check: {result.get('integrity', '-')}."
                f" Dauer: {result.get('elapsed_ms', 0)} ms.",
                "success",
            )
        else:
            flash(f"SSH-Test fehlgeschlagen: {result.get('message', 'Unbekannter Fehler')}", "danger")
        return redirect(url_for("import_devices"))

    @app.route("/import/rustdesk-ssh/import", methods=["POST"])
    @login_required
    def rustdesk_ssh_import():
        _save_ssh_import_settings_from_form()
        update_existing = normalize_bool(request.form.get("update_existing"))
        default_group_name = _resolve_group_name_from_form(default="RustDesk Server")
        try:
            with _ssh_fetch_rustdesk_db_snapshot() as snapshot:
                diagnostics = _inspect_rustdesk_sqlite(snapshot)
                result = _import_from_rustdesk_sqlite(snapshot, default_group_name, update_existing)
        except (ValueError, sqlite3.DatabaseError) as exc:
            session["ssh_import_result"] = {"ok": False, "message": str(exc), "finished_at": _ui_timestamp()}
            flash(f"SSH-Import fehlgeschlagen: {exc}", "danger")
            return redirect(url_for("import_devices"))

        ssh_result = {
            "ok": True,
            "message": "Import erfolgreich",
            "peer_count": diagnostics.get("row_count", 0),
            "created": result["created"],
            "updated": result["updated"],
            "skipped": result["skipped"],
            "wal_seen": result.get("wal_seen", False),
            "finished_at": _ui_timestamp(),
        }
        session["ssh_import_result"] = ssh_result
        flash(
            f"SSH-Import abgeschlossen: {result['created']} neu, "
            f"{result['updated']} aktualisiert, {result['skipped']} übersprungen. "
            f"Remote-Snapshot enthielt {diagnostics.get('row_count', 0)} Peers.",
            "success",
        )
        return redirect(url_for("devices"))

    @app.route("/import/rustdesk-server/diagnose")
    @login_required
    def rustdesk_server_diagnose():
        configured = current_app.config.get("RUSTDESK_SERVER_DB", "")
        diagnostics = None
        error = None
        if not configured:
            error = "Kein RUSTDESK_SERVER_DB gesetzt."
        else:
            db_path = Path(configured)
            if not db_path.is_file():
                error = f"RustDesk-Serverdatenbank nicht gefunden: {configured}"
            else:
                try:
                    diagnostics = _inspect_rustdesk_sqlite(db_path)
                except (sqlite3.DatabaseError, ValueError) as exc:
                    error = str(exc)
        return render_template("rustdesk_server_diagnose.html", configured=configured, diagnostics=diagnostics, error=error)


    @app.route("/export")
    @login_required
    def export_devices():
        include_passwords = request.args.get("include_passwords") == "1"
        output = StringIO()
        fieldnames = ["name", "rustdesk_id", "customer", "location", "os", "tags", "notes", "favorite", "online", "group"]
        if include_passwords:
            fieldnames.insert(2, "password")
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for d in Device.query.order_by(Device.name.asc()).all():
            row = {
                "name": d.name,
                "rustdesk_id": d.rustdesk_id,
                "customer": d.customer or "",
                "location": d.location or "",
                "os": d.os or "",
                "tags": d.tags or "",
                "notes": d.notes or "",
                "favorite": "1" if d.favorite else "0",
                "online": "1" if d.online else "0",
                "group": d.group.name if d.group else "",
            }
            if include_passwords:
                row["password"] = decrypt_value(d.encrypted_password)
            writer.writerow(row)

        suffix = "with-passwords" if include_passwords else "no-passwords"
        filename = f"rustdesk-addressbook-{suffix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"
        return Response(
            output.getvalue(),
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    @app.route("/backup", methods=["GET", "POST"])
    @login_required
    def backup():
        backup_dir = Path(current_app.config["BACKUP_DIR"])
        db_file = Path(current_app.config["DATA_DIR"]) / "addressbook.db"
        backup_dir.mkdir(parents=True, exist_ok=True)

        if request.method == "POST":
            action = request.form.get("action", "create")

            if action == "create":
                filename = _create_database_backup(db_file, backup_dir)
                flash(f"Backup erstellt: {filename}", "success")
                return redirect(url_for("backup"))

            if action == "create_encrypted":
                password = request.form.get("backup_password", "")
                password2 = request.form.get("backup_password2", "")
                if len(password) < 12:
                    flash("Das Backup-Passwort muss mindestens 12 Zeichen haben.", "danger")
                    return redirect(url_for("backup"))
                if password != password2:
                    flash("Die Backup-Passwörter stimmen nicht überein.", "danger")
                    return redirect(url_for("backup"))
                filename = _create_encrypted_database_backup(db_file, backup_dir, password)
                flash(f"Verschlüsseltes Datenbank-Backup erstellt: {filename}", "success")
                return redirect(url_for("backup"))

            if action == "create_full_encrypted":
                password = request.form.get("full_backup_password", "")
                password2 = request.form.get("full_backup_password2", "")
                if len(password) < 16:
                    flash("Das Vollbackup-Passwort muss mindestens 16 Zeichen haben.", "danger")
                    return redirect(url_for("backup"))
                if password != password2:
                    flash("Die Vollbackup-Passwörter stimmen nicht überein.", "danger")
                    return redirect(url_for("backup"))
                filename = _create_encrypted_full_backup(db_file, backup_dir, password)
                flash(f"Verschlüsseltes Vollbackup erstellt: {filename}", "success")
                return redirect(url_for("backup"))

            if action == "restore_existing":
                filename = secure_filename(request.form.get("filename", ""))
                source = backup_dir / filename
                if not filename or not source.is_file():
                    flash("Backup-Datei wurde nicht gefunden.", "danger")
                    return redirect(url_for("backup"))
                try:
                    restore_password = request.form.get("restore_password", "")
                    safety_backup = _restore_database_from_file(source, db_file, backup_dir, password=restore_password)
                except ValueError as exc:
                    flash(str(exc), "danger")
                    return redirect(url_for("backup"))
                flash(f"Backup wiederhergestellt. Vorheriger Stand wurde als {safety_backup} gesichert.", "success")
                return redirect(url_for("dashboard"))

            if action == "restore_upload":
                upload = request.files.get("backup_file")
                if not upload or not upload.filename:
                    flash("Bitte eine SQLite-Backup-Datei auswählen.", "danger")
                    return redirect(url_for("backup"))
                filename = secure_filename(upload.filename)
                if not filename.lower().endswith((".db", ".sqlite", ".sqlite3", ".rabenc", ".rabfull")):
                    flash("Bitte eine SQLite-Datei, ein .rabenc-Backup oder ein .rabfull-Vollbackup hochladen.", "danger")
                    return redirect(url_for("backup"))
                upload_dir = Path(current_app.config["DATA_DIR"]) / "tmp_uploads"
                upload_dir.mkdir(parents=True, exist_ok=True)
                tmp_file = upload_dir / f"restore-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{filename}"
                upload.save(tmp_file)
                try:
                    restore_password = request.form.get("restore_password", "")
                    safety_backup = _restore_database_from_file(tmp_file, db_file, backup_dir, password=restore_password)
                except ValueError as exc:
                    flash(str(exc), "danger")
                    return redirect(url_for("backup"))
                finally:
                    try:
                        tmp_file.unlink(missing_ok=True)
                    except OSError:
                        pass
                flash(f"Backup hochgeladen und wiederhergestellt. Vorheriger Stand wurde als {safety_backup} gesichert.", "success")
                return redirect(url_for("dashboard"))

            if action == "delete_existing":
                filename = secure_filename(request.form.get("filename", ""))
                source = backup_dir / filename
                if not filename or not source.is_file():
                    flash("Backup-Datei wurde nicht gefunden.", "danger")
                    return redirect(url_for("backup"))
                try:
                    source.unlink()
                except OSError as exc:
                    flash(f"Backup konnte nicht gelöscht werden: {exc}", "danger")
                    return redirect(url_for("backup"))
                flash(f"Backup gelöscht: {filename}", "info")
                return redirect(url_for("backup"))

            flash("Unbekannte Backup-Aktion.", "danger")
            return redirect(url_for("backup"))

        files = sorted(
            [p for p in backup_dir.iterdir() if p.is_file() and p.name.lower().endswith((".db", ".rabenc", ".rabfull"))],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return render_template("backup.html", backups=files)

    @app.route("/backup/<path:filename>")
    @login_required
    def backup_download(filename: str):
        safe = secure_filename(filename)
        if safe != filename:
            abort(404)
        return send_from_directory(current_app.config["BACKUP_DIR"], filename, as_attachment=True)

    @app.route("/security")
    @login_required
    def security():
        events = AuthEvent.query.order_by(AuthEvent.created_at.desc()).limit(250).all()
        return render_template(
            "security.html",
            auth_events=events,
            report=_security_audit_report(),
            auth_log_file=str(current_app.config.get("AUTH_LOG_FILE")),
            fail_limit=_get_bruteforce_settings()["limit"],
            fail_window=_get_bruteforce_settings()["window_seconds"],
        )

    @app.route("/security/auth-log/download")
    @login_required
    def security_auth_log_download():
        auth_log = Path(current_app.config.get("AUTH_LOG_FILE"))
        if not auth_log.is_file():
            abort(404)
        return send_from_directory(auth_log.parent, auth_log.name, as_attachment=True)

    @app.route("/help")
    @login_required
    def help_page():
        return render_template("help.html")

    @app.route("/release-notes")
    @login_required
    def release_notes():
        return render_template("release_notes.html")

    @app.route("/api/update-check")
    @login_required
    def api_update_check():
        result = _check_online_update_available()
        _record_update_check(result)
        return jsonify(result)


    @app.route("/settings", methods=["GET", "POST"])
    @login_required
    def settings():
        if request.method == "POST":
            action = request.form.get("action", "password")

            if action == "password":
                current_password = request.form.get("current_password", "")
                new_password = request.form.get("new_password", "")
                new_password2 = request.form.get("new_password2", "")
                if not current_user.check_password(current_password):
                    flash("Aktuelles Passwort ist falsch.", "danger")
                elif len(new_password) < 8:
                    flash("Das neue Passwort muss mindestens 8 Zeichen haben.", "danger")
                elif new_password != new_password2:
                    flash("Die neuen Passwörter stimmen nicht überein.", "danger")
                else:
                    current_user.set_password(new_password)
                    _sign_user_security_state(current_user)
                    db.session.commit()
                    _record_auth_event("password_changed", username=current_user.username, success=True, message="Admin-Passwort wurde geändert")
                    flash("Passwort wurde geändert.", "success")
                return redirect(url_for("settings"))

            if action == "username":
                current_password = request.form.get("current_password", "")
                new_username = request.form.get("new_username", "").strip()
                allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.@-")
                if not current_user.check_password(current_password):
                    flash("Aktuelles Passwort ist falsch.", "danger")
                elif not (3 <= len(new_username) <= 80):
                    flash("Der Benutzername muss zwischen 3 und 80 Zeichen lang sein.", "danger")
                elif any(ch not in allowed_chars for ch in new_username):
                    flash("Der Benutzername darf nur Buchstaben, Zahlen, Punkt, Unterstrich, Bindestrich und @ enthalten.", "danger")
                elif User.query.filter(User.id != current_user.id, User.username == new_username).first():
                    flash("Dieser Benutzername ist bereits vergeben.", "danger")
                else:
                    old_username = current_user.username
                    current_user.username = new_username
                    _sign_user_security_state(current_user)
                    db.session.commit()
                    _record_auth_event("username_changed", username=new_username, success=True, message=f"Admin-Benutzername wurde von {old_username} geändert")
                    flash("Admin-Benutzername wurde geändert.", "success")
                return redirect(url_for("settings"))

            if action == "theme":
                theme_mode = request.form.get("theme_mode", "light").strip().lower()
                language = request.form.get("language", _get_language()).strip().lower()
                if theme_mode not in {"light", "dark"}:
                    flash("Ungültiger Darstellungsmodus.", "danger")
                elif language not in {key for key, _label in LANGUAGE_CHOICES}:
                    flash("Ungültige Sprache.", "danger")
                else:
                    _set_setting("theme_mode", theme_mode)
                    _set_setting("language", language)
                    flash("Darstellung und Sprache wurden gespeichert.", "success")
                return redirect(url_for("settings") + "#display")

            if action == "os_choices":
                raw = request.form.get("os_choices", "")
                choices = _parse_os_choices(raw)
                if not choices:
                    flash("Die Betriebssystem-Auswahl darf nicht leer sein.", "danger")
                else:
                    _set_setting("os_choices", json.dumps(choices, ensure_ascii=False))
                    flash("Betriebssystem-Auswahl wurde gespeichert.", "success")
                return redirect(url_for("settings"))

            if action == "status_settings":
                source = request.form.get("status_source", "manual").strip().lower()
                allowed = {key for key, _label in STATUS_SOURCE_CHOICES}
                if source not in allowed:
                    source = "manual"
                hbbs_host = request.form.get("hbbs_host", "").strip()
                try:
                    hbbs_port = min(max(int(request.form.get("hbbs_port", "21115") or "21115"), 1), 65535)
                except ValueError:
                    hbbs_port = 21115
                try:
                    hbbs_timeout = min(max(float(request.form.get("hbbs_timeout", "3") or "3"), 1.0), 30.0)
                except ValueError:
                    hbbs_timeout = 3.0
                try:
                    hbbs_batch_size = min(max(int(request.form.get("hbbs_batch_size", "50") or "50"), 1), 500)
                except ValueError:
                    hbbs_batch_size = 50
                hbbs_requester_id = request.form.get("hbbs_requester_id", "rustdesk-addressbook").strip() or "rustdesk-addressbook"

                auto_enabled = normalize_bool(request.form.get("auto_status_enabled"))
                try:
                    auto_value = int(request.form.get("auto_status_value", "5") or "5")
                except ValueError:
                    auto_value = 5
                auto_unit = request.form.get("auto_status_unit", "minutes").strip().lower()
                if auto_unit == "hours":
                    auto_value = min(max(auto_value, 1), 24)
                else:
                    auto_unit = "minutes"
                    auto_value = min(max(auto_value, 1), 10)

                _set_setting("status_source", source)
                _set_setting("hbbs_host", hbbs_host)
                _set_setting("hbbs_port", str(hbbs_port))
                _set_setting("hbbs_timeout", str(hbbs_timeout))
                _set_setting("hbbs_batch_size", str(hbbs_batch_size))
                _set_setting("hbbs_requester_id", hbbs_requester_id[:80])
                _set_setting("auto_status_enabled", "1" if auto_enabled else "0")
                _set_setting("auto_status_value", str(auto_value))
                _set_setting("auto_status_unit", auto_unit)
                flash("Online-Status-Einstellungen wurden gespeichert.", "success")
                return redirect(url_for("settings"))

            if action == "update_check_settings":
                auto_enabled = normalize_bool(request.form.get("update_auto_check_enabled"))
                try:
                    interval_hours = int(request.form.get("update_auto_check_hours", "6") or "6")
                except ValueError:
                    interval_hours = 6
                interval_hours = min(max(interval_hours, 1), 168)
                _set_setting("update_auto_check_enabled", "1" if auto_enabled else "0")
                _set_setting("update_auto_check_interval_seconds", str(interval_hours * 3600))
                flash("Update-Check-Einstellungen wurden gespeichert.", "success")
                return redirect(url_for("settings") + "#update-check-card")

            if action == "bruteforce":
                current_password = request.form.get("current_password", "")
                try:
                    limit = int(request.form.get("login_fail_limit", "5") or "5")
                except ValueError:
                    limit = 5
                try:
                    window_minutes = int(request.form.get("login_fail_window_minutes", "15") or "15")
                except ValueError:
                    window_minutes = 15
                limit = min(max(limit, 2), 50)
                window_minutes = min(max(window_minutes, 1), 1440)
                if not current_user.check_password(current_password):
                    flash("Aktuelles Passwort ist falsch.", "danger")
                else:
                    _set_setting("login_fail_limit", str(limit))
                    _set_setting("login_fail_window_seconds", str(window_minutes * 60))
                    _record_auth_event("bruteforce_settings_changed", username=current_user.username, success=True, message=f"Brute-Force-Sperre: {limit} Fehlversuche / {window_minutes} Minuten")
                    flash("Brute-Force-Sperre wurde gespeichert.", "success")
                return redirect(url_for("settings"))

            if action == "totp_prepare":
                current_password = request.form.get("current_password", "")
                if not current_user.check_password(current_password):
                    flash("Aktuelles Passwort ist falsch.", "danger")
                else:
                    current_user.totp_secret_encrypted = encrypt_value(pyotp.random_base32())
                    current_user.totp_enabled = False
                    _sign_user_security_state(current_user)
                    db.session.commit()
                    _record_auth_event("2fa_prepare", username=current_user.username, success=True, message="2FA-Einrichtung vorbereitet")
                    flash("2FA vorbereitet. Scanne den QR-Code und bestätige danach einen Code aus deiner Authenticator-App.", "success")
                return redirect(url_for("settings"))

            if action == "totp_enable":
                current_password = request.form.get("current_password", "")
                code = request.form.get("totp_code", "")
                if not current_user.check_password(current_password):
                    flash("Aktuelles Passwort ist falsch.", "danger")
                elif not _verify_totp_for_user(current_user, code):
                    flash("2FA-Code ist ungültig oder abgelaufen.", "danger")
                else:
                    recovery_codes = _generate_recovery_codes()
                    _set_recovery_codes_for_user(current_user, recovery_codes)
                    current_user.totp_enabled = True
                    _sign_user_security_state(current_user)
                    db.session.commit()
                    _record_auth_event("2fa_enabled", username=current_user.username, success=True, message="2FA aktiviert und Recovery-Codes erstellt")
                    session["new_recovery_codes"] = recovery_codes
                    flash("2FA wurde aktiviert. Speichere die Wiederherstellungscodes jetzt sicher ab; sie werden nur einmal angezeigt.", "success")
                return redirect(url_for("settings"))

            if action == "totp_disable":
                current_password = request.form.get("current_password", "")
                code = request.form.get("totp_code", "")
                if not current_user.check_password(current_password):
                    flash("Aktuelles Passwort ist falsch.", "danger")
                else:
                    ok, method = _verify_second_factor_for_user(current_user, code, consume_recovery=True)
                    if not ok:
                        flash("2FA-Code oder Wiederherstellungscode ist ungültig.", "danger")
                    else:
                        current_user.totp_enabled = False
                        current_user.totp_secret_encrypted = None
                        current_user.totp_recovery_hashes = None
                        _sign_user_security_state(current_user)
                        db.session.commit()
                        _record_auth_event("2fa_disabled", username=current_user.username, success=True, message=("2FA mit Recovery-Code deaktiviert" if method == "recovery" else "2FA deaktiviert"))
                        if method == "recovery":
                            flash("2FA wurde mit einem Wiederherstellungscode deaktiviert.", "warning")
                        else:
                            flash("2FA wurde deaktiviert.", "info")
                return redirect(url_for("settings"))

            if action == "totp_recovery_regenerate":
                current_password = request.form.get("current_password", "")
                code = request.form.get("totp_code", "")
                if not getattr(current_user, "totp_enabled", False):
                    flash("2FA ist nicht aktiviert.", "danger")
                elif not current_user.check_password(current_password):
                    flash("Aktuelles Passwort ist falsch.", "danger")
                else:
                    ok, method = _verify_second_factor_for_user(current_user, code, consume_recovery=True)
                    if not ok:
                        flash("2FA-Code oder Wiederherstellungscode ist ungültig.", "danger")
                    else:
                        recovery_codes = _generate_recovery_codes()
                        _set_recovery_codes_for_user(current_user, recovery_codes)
                        _sign_user_security_state(current_user)
                        db.session.commit()
                        _record_auth_event("2fa_recovery_regenerated", username=current_user.username, success=True, message="2FA-Recovery-Codes neu erstellt")
                        session["new_recovery_codes"] = recovery_codes
                        if method == "recovery":
                            flash("Neue Wiederherstellungscodes wurden erstellt. Der eingegebene alte Wiederherstellungscode wurde ersetzt.", "warning")
                        else:
                            flash("Neue Wiederherstellungscodes wurden erstellt. Speichere sie jetzt sicher ab; sie werden nur einmal angezeigt.", "success")
                return redirect(url_for("settings"))

            if action == "totp_cancel":
                if not getattr(current_user, "totp_enabled", False):
                    current_user.totp_secret_encrypted = None
                    _sign_user_security_state(current_user)
                    db.session.commit()
                    _record_auth_event("2fa_cancel", username=current_user.username, success=True, message="2FA-Einrichtung verworfen")
                    flash("2FA-Einrichtung wurde verworfen.", "info")
                return redirect(url_for("settings"))

            flash("Unbekannte Einstellungs-Aktion.", "danger")
            return redirect(url_for("settings"))
        return render_template(
            "settings.html",
            current_os_choices=_get_os_choices(),
            current_theme_mode=_get_theme_mode(),
            current_language=_get_language(),
            totp_secret=_get_user_totp_secret(current_user),
            totp_qr_data_uri=_totp_qr_data_uri(current_user),
            recovery_code_count=_recovery_code_count(current_user),
            new_recovery_codes=session.pop("new_recovery_codes", None),
        )



def _import_from_rustdesk_sqlite(db_path: Path, default_group_name: str, update_existing: bool) -> dict[str, int]:
    group = _get_or_create_group(default_group_name)
    created = updated = skipped = status_values_seen = 0

    for row in _read_rustdesk_peer_rows(db_path):
        rustdesk_id = str(row["id"] or "").strip()
        if not rustdesk_id:
            skipped += 1
            continue

        existing = Device.query.filter_by(rustdesk_id=rustdesk_id).first()
        if existing and not update_existing:
            skipped += 1
            continue

        note = _safe_text(row["note"] if "note" in row.keys() else "")
        raw_info = _safe_text(row["info"] if "info" in row.keys() else "")
        info = _parse_rustdesk_info(raw_info)
        name = _guess_rustdesk_device_name(rustdesk_id, note, info)
        os_name = _guess_rustdesk_os(info)
        status = _safe_text(row["status"] if "status" in row.keys() else "")
        if status:
            status_values_seen += 1
        created_at = _safe_text(row["created_at"] if "created_at" in row.keys() else "")
        notes = _build_rustdesk_import_notes(note, raw_info, status, created_at)

        if existing:
            existing.name = existing.name or name
            existing.customer = existing.customer or ""
            existing.location = existing.location or ""
            existing.os = existing.os or os_name
            existing.notes = existing.notes or notes
            existing.group = existing.group or group
            # Online wird bewusst nicht aus peer.status übernommen. Der Live-Status kommt über hbbs.
            updated += 1
        else:
            device = Device(
                name=name,
                rustdesk_id=rustdesk_id,
                customer="",
                location="",
                os=os_name,
                tags="rustdesk-server-import",
                notes=notes,
                favorite=False,
                online=False,
                group=group,
                encrypted_password=encrypt_value(""),
            )
            db.session.add(device)
            created += 1

    db.session.commit()
    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "wal_seen": _sqlite_family_info(db_path)["wal"],
        "status_values_seen": status_values_seen,
    }


@contextmanager
def _stage_rustdesk_sqlite_uploads(uploads):
    """Stage an uploaded RustDesk SQLite database family.

    Accepts either:
    - db_v2.sqlite3 alone,
    - db_v2.sqlite3 plus db_v2.sqlite3-wal/db_v2.sqlite3-shm as multiple files,
    - a ZIP containing that file family.

    The files are written to a temporary directory so SQLite can see the WAL
    file beside the main database under the original base name.
    """
    upload_root = Path(current_app.config["DATA_DIR"]) / "tmp_uploads"
    upload_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rustdesk-server-import-", dir=upload_root) as tmp_name:
        tmp_dir = Path(tmp_name)
        saved_files: list[Path] = []

        for upload in uploads:
            filename = secure_filename(upload.filename or "")
            if not filename:
                continue
            lower = filename.lower()
            if lower.endswith(".zip"):
                zip_path = tmp_dir / filename
                upload.save(zip_path)
                saved_files.extend(_extract_safe_zip_members(zip_path, tmp_dir))
            elif _is_rustdesk_sqlite_family_file(filename):
                target = tmp_dir / filename
                upload.save(target)
                saved_files.append(target)
            else:
                raise ValueError(f"Nicht unterstützte RustDesk-Importdatei: {filename}")

        db_path = _find_rustdesk_main_db(saved_files or list(tmp_dir.iterdir()))
        if not db_path:
            raise ValueError("Keine passende Hauptdatenbank gefunden. Erwartet wird z.B. db_v2.sqlite3 zusammen mit optional db_v2.sqlite3-wal und db_v2.sqlite3-shm.")
        yield db_path


def _is_rustdesk_sqlite_family_file(filename: str) -> bool:
    lower = filename.lower()
    return lower.endswith((".sqlite", ".sqlite3", ".db", ".sqlite-wal", ".sqlite3-wal", ".db-wal", ".sqlite-shm", ".sqlite3-shm", ".db-shm"))


def _extract_safe_zip_members(zip_path: Path, target_dir: Path) -> list[Path]:
    extracted: list[Path] = []
    try:
        with zipfile.ZipFile(zip_path) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                filename = secure_filename(Path(info.filename).name)
                if not filename:
                    continue
                if not _is_rustdesk_sqlite_family_file(filename):
                    continue
                target = target_dir / filename
                with zf.open(info) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                extracted.append(target)
    except zipfile.BadZipFile as exc:
        raise ValueError("Die ZIP-Datei konnte nicht gelesen werden.") from exc
    finally:
        try:
            zip_path.unlink(missing_ok=True)
        except OSError:
            pass
    return extracted


def _find_rustdesk_main_db(paths: list[Path]) -> Path | None:
    candidates = []
    for path in paths:
        if not path.is_file():
            continue
        lower = path.name.lower()
        if lower.endswith(("-wal", "-shm")):
            continue
        if lower.endswith((".sqlite", ".sqlite3", ".db")):
            candidates.append(path)
    if not candidates:
        return None
    for preferred in candidates:
        if preferred.name.lower() == "db_v2.sqlite3":
            return preferred
    return candidates[0]


def _sqlite_family_info(db_path: Path) -> dict[str, bool]:
    return {
        "wal": Path(str(db_path) + "-wal").is_file(),
        "shm": Path(str(db_path) + "-shm").is_file(),
    }


@contextmanager
def _sqlite_snapshot(db_path: Path):
    """Create a consistent, temporary SQLite snapshot and include WAL changes.

    First try SQLite's backup API against the source DB. That path includes
    committed frames from the WAL when SQLite can open the database family.
    If that fails, copy the DB/WAL/SHM family to a writable temp directory and
    open that copy, which is useful for read-only Docker mounts or uploaded
    file families.
    """
    upload_root = Path(current_app.config["DATA_DIR"]) / "tmp_uploads"
    upload_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="sqlite-snapshot-", dir=upload_root) as tmp_name:
        tmp_dir = Path(tmp_name)
        snapshot = tmp_dir / "snapshot.sqlite3"

        try:
            with _open_sqlite_readonly(db_path) as src, sqlite3.connect(snapshot) as dst:
                src.backup(dst)
            yield snapshot
            return
        except sqlite3.DatabaseError:
            # Fallback below: copy the SQLite family into a writable directory.
            pass

        local_db = tmp_dir / db_path.name
        shutil.copy2(db_path, local_db)
        for suffix in ("-wal", "-shm"):
            sidecar = Path(str(db_path) + suffix)
            if sidecar.is_file():
                shutil.copy2(sidecar, tmp_dir / f"{db_path.name}{suffix}")

        with sqlite3.connect(local_db) as src, sqlite3.connect(snapshot) as dst:
            src.backup(dst)
        yield snapshot


def _safe_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="replace").strip()
        except Exception:
            return value.hex()
    return str(value).strip()


def _parse_rustdesk_info(raw_info: str) -> dict:
    if not raw_info:
        return {}
    try:
        parsed = json.loads(raw_info)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _first_info_value(info: dict, *keys: str) -> str:
    for key in keys:
        value = info.get(key)
        if value:
            return _safe_text(value)
    # Some RustDesk builds may nest details under generic keys.
    for nested_key in ("device", "system", "platform", "host", "hostname"):
        nested = info.get(nested_key)
        if isinstance(nested, dict):
            found = _first_info_value(nested, *keys)
            if found:
                return found
    return ""


def _guess_rustdesk_device_name(rustdesk_id: str, note: str, info: dict) -> str:
    for value in [
        _first_info_value(info, "hostname", "host_name", "computer_name", "device_name", "name", "host"),
        note,
        _first_info_value(info, "username", "user_name", "user"),
    ]:
        clean = value.strip()
        if clean:
            return clean[:180]
    return f"RustDesk {rustdesk_id}"[:180]


def _guess_rustdesk_os(info: dict) -> str:
    return _normalize_os(_first_info_value(info, "os", "platform", "system", "operating_system", "type", "device_type"))[:64]


def _build_rustdesk_import_notes(note: str, raw_info: str, status: str, created_at: str) -> str:
    parts = ["Importiert aus RustDesk Server db_v2.sqlite3."]
    if created_at:
        parts.append(f"created_at: {created_at}")
    if status:
        parts.append(f"status: {status}")
    if note:
        parts.append(f"server_note: {note}")
    if raw_info:
        parts.append(f"server_info: {raw_info[:2000]}")
    return "\n".join(parts)

def _rustdesk_status_to_bool_or_none(value) -> bool | None:
    text = _safe_text(value).lower()
    if not text:
        return None
    if text in {"1", "true", "online", "connected", "active", "yes", "ja", "on"}:
        return True
    if text in {"0", "false", "offline", "disconnected", "inactive", "no", "nein", "off"}:
        return False
    # Unbekannte Werte nicht als offline behandeln, sonst werden manuelle Stati überschrieben.
    return None


def _rustdesk_status_to_bool(value) -> bool:
    parsed = _rustdesk_status_to_bool_or_none(value)
    return bool(parsed)


def _normalize_os(value: str | None) -> str:
    text = _safe_text(value)
    if not text:
        return ""
    low = text.lower()
    if "windows" in low or low.startswith("win"):
        return "Windows"
    if "android" in low:
        return "Android"
    if "darwin" in low or "mac" in low or "osx" in low or "os x" in low:
        return "macOS"
    if "ios" in low or "iphone" in low or "ipad" in low:
        return "iOS"
    if "proxmox" in low or "pve" in low:
        return "Proxmox"
    if "qnap" in low or "qts" in low:
        return "QNAP"
    if "synology" in low or "dsm" in low:
        return "Synology"
    if "linux" in low or "ubuntu" in low or "debian" in low or "fedora" in low or "arch" in low or "rhel" in low or "centos" in low:
        return "Linux"
    for choice in _get_os_choices():
        if text == choice:
            return choice
    return text[:64]


def _os_icon_class(os_name: str | None) -> str:
    normalized = _normalize_os(os_name)
    mapping = {
        "Windows": "bi-windows",
        "Linux": "bi-ubuntu",
        "macOS": "bi-apple",
        "Android": "bi-android2",
        "iOS": "bi-phone",
        "Proxmox": "bi-hdd-network",
        "QNAP": "bi-device-hdd",
        "Synology": "bi-device-hdd",
    }
    return mapping.get(normalized, "bi-pc-display")



def _rustdesk_server_db_status() -> dict:
    configured = current_app.config.get("RUSTDESK_SERVER_DB", "").strip()
    if not configured:
        return {
            "configured": False,
            "exists": False,
            "path": "",
            "message": "RUSTDESK_SERVER_DB ist nicht gesetzt. Direkter DB-Import und DB-Diagnose sind deaktiviert.",
            "badge": "text-bg-secondary",
            "family": {"main": False, "wal": False, "shm": False},
        }
    db_path = Path(configured)
    exists = db_path.is_file()
    family = _sqlite_family_info(db_path) if exists else {"main": False, "wal": False, "shm": False}
    if exists:
        extra = []
        if family.get("wal"):
            extra.append("WAL sichtbar")
        if family.get("shm"):
            extra.append("SHM sichtbar")
        suffix = " (" + ", ".join(extra) + ")" if extra else ""
        return {
            "configured": True,
            "exists": True,
            "path": configured,
            "message": f"Aktiv: {configured}{suffix}",
            "badge": "text-bg-success",
            "family": family,
        }
    return {
        "configured": True,
        "exists": False,
        "path": configured,
        "message": f"RUSTDESK_SERVER_DB ist gesetzt, aber die Datei wurde nicht gefunden: {configured}",
        "badge": "text-bg-warning",
        "family": family,
    }

def _rustdesk_server_db_exists() -> bool:
    configured = current_app.config.get("RUSTDESK_SERVER_DB", "")
    return bool(configured and Path(configured).is_file())


def _get_ssh_import_settings() -> dict:
    data_dir = Path(current_app.config["DATA_DIR"])
    default_key = data_dir / "ssh" / "rustdesk_import_ed25519"
    default_known_hosts = data_dir / "ssh" / "known_hosts"
    try:
        port = int(_get_setting("ssh_import_port", "22") or "22")
    except ValueError:
        port = 22
    try:
        timeout = int(_get_setting("ssh_import_timeout", "15") or "15")
    except ValueError:
        timeout = 15
    return {
        "host": _get_setting("ssh_import_host", "").strip(),
        "port": min(max(port, 1), 65535),
        "user": _get_setting("ssh_import_user", "rab-import").strip() or "rab-import",
        "key_path": _get_setting("ssh_import_key_path", str(default_key)).strip() or str(default_key),
        "known_hosts_path": _get_setting("ssh_import_known_hosts_path", str(default_known_hosts)).strip() or str(default_known_hosts),
        "remote_command": _get_setting("ssh_import_remote_command", "").strip(),
        "timeout": min(max(timeout, 3), 120),
    }


def _save_ssh_import_settings_from_form() -> None:
    host = request.form.get("ssh_host", "").strip()
    user = request.form.get("ssh_user", "rab-import").strip() or "rab-import"
    key_path = request.form.get("ssh_key_path", "").strip()
    known_hosts_path = request.form.get("ssh_known_hosts_path", "").strip()
    remote_command = request.form.get("ssh_remote_command", "").strip()
    try:
        port = min(max(int(request.form.get("ssh_port", "22") or "22"), 1), 65535)
    except ValueError:
        port = 22
    try:
        timeout = min(max(int(request.form.get("ssh_timeout", "15") or "15"), 3), 120)
    except ValueError:
        timeout = 15

    _set_setting("ssh_import_host", host[:255])
    _set_setting("ssh_import_port", str(port))
    _set_setting("ssh_import_user", user[:80])
    _set_setting("ssh_import_key_path", key_path[:500])
    _set_setting("ssh_import_known_hosts_path", known_hosts_path[:500])
    _set_setting("ssh_import_remote_command", remote_command[:500])
    _set_setting("ssh_import_timeout", str(timeout))


def _resolve_ssh_path(raw: str, *, default_name: str, must_exist: bool = False) -> Path:
    data_dir = Path(current_app.config["DATA_DIR"]).resolve()
    ssh_dir = data_dir / "ssh"
    ssh_dir.mkdir(parents=True, exist_ok=True)
    text = (raw or "").strip()
    path = Path(text) if text else ssh_dir / default_name
    if not path.is_absolute():
        path = data_dir / path
    resolved = path.resolve()
    if not resolved.is_relative_to(data_dir):
        raise ValueError(f"SSH-Dateipfad muss unterhalb von {data_dir} liegen: {resolved}")
    if must_exist and not resolved.is_file():
        raise ValueError(f"SSH-Datei wurde nicht gefunden: {resolved}")
    return resolved


def _validate_ssh_text(value: str, field: str, *, allow_empty: bool = False) -> str:
    text = (value or "").strip()
    if not text and allow_empty:
        return ""
    if not text:
        raise ValueError(f"{field} fehlt.")
    if any(ch in text for ch in "\r\n\x00"):
        raise ValueError(f"{field} enthält ungültige Zeichen.")
    return text


@contextmanager
def _ssh_fetch_rustdesk_db_snapshot():
    """Fetch a consistent RustDesk SQLite snapshot over a restricted SSH command.

    Expected remote side: a forced command or explicit command that writes a
    SQLite database to stdout, e.g. a sqlite3 .backup snapshot followed by cat.
    The private key and known_hosts file must live below DATA_DIR.
    """
    settings = _get_ssh_import_settings()
    host = _validate_ssh_text(settings["host"], "SSH Host")
    user = _validate_ssh_text(settings["user"], "SSH Benutzer")
    remote_command = _validate_ssh_text(settings.get("remote_command", ""), "Remote-Kommando", allow_empty=True)
    key_path = _resolve_ssh_path(settings["key_path"], default_name="rustdesk_import_ed25519", must_exist=True)
    known_hosts_path = _resolve_ssh_path(settings["known_hosts_path"], default_name="known_hosts", must_exist=False)
    known_hosts_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        key_path.chmod(0o600)
    except OSError:
        pass

    upload_root = Path(current_app.config["DATA_DIR"]) / "tmp_uploads"
    upload_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rustdesk-ssh-import-", dir=upload_root) as tmp_name:
        tmp_dir = Path(tmp_name)
        snapshot = tmp_dir / "rustdesk-db-snapshot.sqlite3"
        cmd = [
            "ssh",
            "-T",
            "-i", str(key_path),
            "-p", str(settings["port"]),
            "-o", "IdentitiesOnly=yes",
            "-o", "BatchMode=yes",
            "-o", f"ConnectTimeout={settings['timeout']}",
            "-o", f"UserKnownHostsFile={known_hosts_path}",
            "-o", "StrictHostKeyChecking=accept-new",
            f"{user}@{host}",
        ]
        if remote_command:
            cmd.append(remote_command)

        started = time.monotonic()
        try:
            completed = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=settings["timeout"] + 30,
                check=False,
            )
        except FileNotFoundError as exc:
            raise ValueError("Der SSH-Client wurde im Container nicht gefunden. Bitte Image mit openssh-client neu bauen.") from exc
        except subprocess.TimeoutExpired as exc:
            raise ValueError(f"SSH-Übertragung nach {settings['timeout'] + 30} Sekunden abgebrochen.") from exc
        elapsed_ms = int((time.monotonic() - started) * 1000)
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()

        if completed.returncode != 0:
            raise ValueError(f"SSH-Befehl fehlgeschlagen, Exit-Code {completed.returncode}: {stderr[:1000] or 'keine Fehlerausgabe'}")
        if len(completed.stdout) < 100:
            raise ValueError(f"SSH-Übertragung lieferte zu wenig Daten ({len(completed.stdout)} Bytes). stderr={stderr[:500] or '-'}")
        if not completed.stdout.startswith(b"SQLite format 3\x00"):
            preview = completed.stdout[:120].decode("utf-8", errors="replace").replace("\n", " ")
            raise ValueError(f"SSH-Übertragung war keine SQLite-Datenbank. Erste Bytes: {preview!r}. stderr={stderr[:500] or '-'}")

        snapshot.write_bytes(completed.stdout)
        try:
            snapshot.chmod(0o600)
        except OSError:
            pass
        session["_last_ssh_transfer"] = {"bytes": len(completed.stdout), "elapsed_ms": elapsed_ms, "stderr": stderr[:1000]}
        yield snapshot


def _ssh_fetch_and_inspect_rustdesk_db() -> dict:
    with _ssh_fetch_rustdesk_db_snapshot() as snapshot:
        transfer = session.pop("_last_ssh_transfer", {})
        diagnostics = _inspect_rustdesk_sqlite(snapshot)
        try:
            with _open_sqlite_readonly(snapshot) as con:
                integrity = str(con.execute("PRAGMA integrity_check").fetchone()[0])
        except sqlite3.DatabaseError as exc:
            raise ValueError(f"SQLite-Integritätsprüfung fehlgeschlagen: {exc}") from exc
        if not diagnostics.get("peer_exists"):
            raise ValueError("Snapshot übertragen, aber Tabelle 'peer' wurde nicht gefunden.")
        return {
            "ok": True,
            "message": "SSH-Übertragung erfolgreich",
            "bytes": transfer.get("bytes", snapshot.stat().st_size),
            "elapsed_ms": transfer.get("elapsed_ms", 0),
            "stderr": transfer.get("stderr", ""),
            "tables": diagnostics.get("tables", []),
            "columns": diagnostics.get("columns", []),
            "peer_count": diagnostics.get("row_count", 0),
            "integrity": integrity,
        }


def _open_sqlite_readonly(db_path: Path) -> sqlite3.Connection:
    uri = db_path.resolve().as_uri() + "?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only=ON")
    return con


def _read_rustdesk_peer_rows(db_path: Path) -> list[sqlite3.Row]:
    with _sqlite_snapshot(db_path) as snapshot:
        with _open_sqlite_readonly(snapshot) as con:
            table_exists = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='peer'"
            ).fetchone()
            if not table_exists:
                raise ValueError("In der Datei wurde keine RustDesk-Tabelle 'peer' gefunden.")

            columns = {row[1] for row in con.execute("PRAGMA table_info(peer)").fetchall()}
            if "id" not in columns:
                raise ValueError("Die RustDesk-Tabelle 'peer' enthält keine Spalte 'id'.")

            wanted = [c for c in ["id", "note", "info", "status", "created_at", "user"] if c in columns]
            return con.execute(f"SELECT {', '.join(wanted)} FROM peer ORDER BY id COLLATE NOCASE").fetchall()


def _sync_rustdesk_status_from_sqlite(db_path: Path) -> dict[str, int]:
    updated = unknown = status_usable = status_blank = 0
    for row in _read_rustdesk_peer_rows(db_path):
        rustdesk_id = _safe_text(row["id"] if "id" in row.keys() else "")
        if not rustdesk_id:
            continue
        status = _safe_text(row["status"] if "status" in row.keys() else "")
        parsed_status = _rustdesk_status_to_bool_or_none(status)
        if parsed_status is None:
            status_blank += 1
            continue
        status_usable += 1
        device = Device.query.filter_by(rustdesk_id=rustdesk_id).first()
        if not device:
            unknown += 1
            continue
        device.online = parsed_status
        updated += 1
    db.session.commit()
    return {"updated": updated, "unknown": unknown, "status_usable": status_usable, "status_blank": status_blank}


def _inspect_rustdesk_sqlite(db_path: Path) -> dict:
    family = _sqlite_family_info(db_path)
    with _sqlite_snapshot(db_path) as snapshot:
        with _open_sqlite_readonly(snapshot) as con:
            tables = [row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
            if "peer" not in tables:
                return {"db_path": str(db_path), "family": family, "tables": tables, "peer_exists": False}

            columns = [row[1] for row in con.execute("PRAGMA table_info(peer)").fetchall()]
            row_count = con.execute("SELECT COUNT(*) FROM peer").fetchone()[0]
            status_distribution = []
            usable_count = blank_count = 0
            if "status" in columns:
                raw_dist = con.execute(
                    "SELECT COALESCE(CAST(status AS TEXT), '') AS status_value, COUNT(*) AS amount "
                    "FROM peer GROUP BY status_value ORDER BY amount DESC, status_value LIMIT 20"
                ).fetchall()
                for row in raw_dist:
                    value = _safe_text(row["status_value"])
                    amount = int(row["amount"])
                    parsed = _rustdesk_status_to_bool_or_none(value)
                    if parsed is None:
                        blank_count += amount
                    else:
                        usable_count += amount
                    status_distribution.append({"value": value or "<leer>", "count": amount, "interpreted": parsed})

            sample_rows = []
            wanted = [c for c in ["id", "status", "note", "info", "created_at", "user"] if c in columns]
            if wanted:
                for row in con.execute(f"SELECT {', '.join(wanted)} FROM peer ORDER BY id COLLATE NOCASE LIMIT 10").fetchall():
                    item = {}
                    for key in row.keys():
                        value = _safe_text(row[key])
                        item[key] = value[:300]
                    sample_rows.append(item)

            info_keys = Counter()
            if "info" in columns:
                for row in con.execute("SELECT info FROM peer WHERE info IS NOT NULL AND info != '' LIMIT 200").fetchall():
                    parsed = _parse_rustdesk_info(_safe_text(row["info"]))
                    if isinstance(parsed, dict):
                        info_keys.update(parsed.keys())

            return {
                "db_path": str(db_path),
                "family": family,
                "tables": tables,
                "peer_exists": True,
                "columns": columns,
                "row_count": row_count,
                "status_distribution": status_distribution,
                "status_usable": usable_count,
                "status_blank": blank_count,
                "sample_rows": sample_rows,
                "info_keys": info_keys.most_common(30),
            }


def _validate_addressbook_sqlite(db_path: Path) -> None:
    try:
        with _open_sqlite_readonly(db_path) as con:
            integrity = con.execute("PRAGMA integrity_check").fetchone()
            if not integrity or str(integrity[0]).lower() != "ok":
                raise ValueError("SQLite-Integritätsprüfung ist fehlgeschlagen.")
            tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            required = {"users", "devices", "groups"}
            missing = required - tables
            if missing:
                raise ValueError("Diese Datei ist kein gültiges RustDesk-AddressBook-Backup. Fehlende Tabellen: " + ", ".join(sorted(missing)))
    except sqlite3.DatabaseError as exc:
        raise ValueError(f"Die Datei konnte nicht als SQLite-Backup gelesen werden: {exc}") from exc



def _sync_hbbs_live_status(*, trigger: str) -> dict:
    settings = _get_status_settings()
    if not settings["hbbs_host"]:
        raise RustDeskLiveStatusError("hbbs Live-Abfrage ist nicht konfiguriert. Trage unter Einstellungen den hbbs Host ein.")

    devices = Device.query.filter(Device.rustdesk_id.isnot(None)).order_by(Device.id.asc()).all()
    peer_ids = [d.rustdesk_id.strip() for d in devices if d.rustdesk_id and d.rustdesk_id.strip()]
    if not peer_ids:
        raise RustDeskLiveStatusError("Keine RustDesk-IDs im Adressbuch vorhanden.")

    id_to_device = {d.rustdesk_id.strip(): d for d in devices if d.rustdesk_id and d.rustdesk_id.strip()}
    batch_size = settings["hbbs_batch_size"]
    updated = online_count = offline_count = 0
    last_states = ""

    for start in range(0, len(peer_ids), batch_size):
        batch = peer_ids[start : start + batch_size]
        result = query_hbbs_online_status(
            settings["hbbs_host"],
            int(settings["hbbs_port"]),
            batch,
            requester_id=settings["hbbs_requester_id"],
            timeout=float(settings["hbbs_timeout"]),
        )
        last_states = result.response_states_hex
        for peer_id, is_online in result.online.items():
            device = id_to_device.get(peer_id)
            if device is None:
                continue
            if device.online != is_online:
                device.online = is_online
                updated += 1
            if is_online:
                online_count += 1
            else:
                offline_count += 1

    db.session.commit()
    message = f"{online_count} online, {offline_count} offline, {updated} geändert"
    _record_status_check(True, message, trigger=trigger, online=online_count, offline=offline_count, updated=updated, states=last_states)
    return {"updated": updated, "online": online_count, "offline": offline_count, "states": last_states}


def _record_status_check(ok: bool, message: str, *, trigger: str, online: int | None = None, offline: int | None = None, updated: int | None = None, states: str = "") -> None:
    now_epoch = int(time.time())
    _set_setting("status_last_checked_epoch", str(now_epoch))
    _set_setting("status_last_checked_at", datetime.fromtimestamp(now_epoch).strftime("%d.%m.%Y %H:%M:%S"))
    _set_setting("status_last_ok", "1" if ok else "0")
    _set_setting("status_last_trigger", trigger)
    _set_setting("status_last_message", str(message)[:500])
    _set_setting("status_last_online", "" if online is None else str(online))
    _set_setting("status_last_offline", "" if offline is None else str(offline))
    _set_setting("status_last_updated", "" if updated is None else str(updated))
    _set_setting("status_last_states", states[:200])


def _get_status_last_checked_epoch() -> int:
    try:
        return int(_get_setting("status_last_checked_epoch", "0") or "0")
    except ValueError:
        return 0


def _get_status_check_info() -> dict:
    ok_raw = _get_setting("status_last_ok", "")
    return {
        "checked_at": _get_setting("status_last_checked_at", ""),
        "ok": True if ok_raw == "1" else False if ok_raw == "0" else None,
        "trigger": _get_setting("status_last_trigger", ""),
        "message": _get_setting("status_last_message", ""),
        "online": _get_setting("status_last_online", ""),
        "offline": _get_setting("status_last_offline", ""),
        "updated": _get_setting("status_last_updated", ""),
        "states": _get_setting("status_last_states", ""),
    }


def _get_auto_status_settings() -> dict:
    enabled = normalize_bool(_get_setting("auto_status_enabled", "0"))
    unit = _get_setting("auto_status_unit", "minutes").strip().lower()
    try:
        value = int(_get_setting("auto_status_value", "5") or "5")
    except ValueError:
        value = 5
    if unit == "hours":
        value = min(max(value, 1), 24)
        seconds = value * 3600
        label = f"alle {value} Stunde{'n' if value != 1 else ''}"
    else:
        unit = "minutes"
        value = min(max(value, 1), 10)
        seconds = value * 60
        label = f"alle {value} Minute{'n' if value != 1 else ''}"
    return {"enabled": enabled, "unit": unit, "value": value, "interval_seconds": seconds, "label": label}



def _normalize_totp_code(code: str) -> str:
    return "".join(ch for ch in str(code or "") if ch.isdigit())


def _get_user_totp_secret(user: User) -> str:
    return decrypt_value(getattr(user, "totp_secret_encrypted", None))


def _verify_totp_for_user(user: User, code: str) -> bool:
    secret = _get_user_totp_secret(user)
    clean = _normalize_totp_code(code)
    if not secret or len(clean) != 6:
        return False
    try:
        return pyotp.TOTP(secret).verify(clean, valid_window=1)
    except Exception:
        return False


def _totp_provisioning_uri(user: User) -> str:
    secret = _get_user_totp_secret(user)
    if not secret:
        return ""
    issuer = "RustDesk AddressBook"
    label = f"{issuer}:{user.username}"
    return pyotp.TOTP(secret).provisioning_uri(name=label, issuer_name=issuer)


def _totp_qr_data_uri(user: User) -> str:
    uri = _totp_provisioning_uri(user)
    if not uri:
        return ""
    img = qrcode.make(uri)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _normalize_recovery_code(code: str) -> str:
    return "".join(ch for ch in str(code or "").upper() if ch.isalnum())


def _format_recovery_code(raw: str) -> str:
    clean = _normalize_recovery_code(raw)
    return "-".join(clean[i:i + 4] for i in range(0, len(clean), 4))


def _generate_recovery_codes(count: int = 10) -> list[str]:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    codes = []
    for _ in range(count):
        raw = "".join(secrets.choice(alphabet) for _ in range(12))
        codes.append(_format_recovery_code(raw))
    return codes


def _get_recovery_hashes(user: User) -> list[str]:
    raw = getattr(user, "totp_recovery_hashes", None)
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return [str(item) for item in data if item]
    except Exception:
        return []


def _set_recovery_codes_for_user(user: User, codes: list[str]) -> None:
    hashes = [generate_password_hash(_normalize_recovery_code(code)) for code in codes]
    user.totp_recovery_hashes = json.dumps(hashes)


def _recovery_code_count(user: User) -> int:
    return len(_get_recovery_hashes(user))


def _verify_recovery_code_for_user(user: User, code: str, consume: bool = False) -> bool:
    clean = _normalize_recovery_code(code)
    if len(clean) < 8:
        return False
    hashes = _get_recovery_hashes(user)
    for idx, stored_hash in enumerate(hashes):
        try:
            if check_password_hash(stored_hash, clean):
                if consume:
                    del hashes[idx]
                    user.totp_recovery_hashes = json.dumps(hashes) if hashes else None
                return True
        except Exception:
            continue
    return False


def _verify_second_factor_for_user(user: User, code: str, consume_recovery: bool = False) -> tuple[bool, str]:
    if _verify_totp_for_user(user, code):
        return True, "totp"
    if _verify_recovery_code_for_user(user, code, consume=consume_recovery):
        return True, "recovery"
    return False, ""


def _security_audit_report() -> list[dict]:
    items: list[dict] = []

    def add(name: str, status: str, detail: str) -> None:
        items.append({"name": name, "status": status, "detail": detail})

    users = User.query.order_by(User.id.asc()).all()
    if users:
        protected = sum(1 for u in users if getattr(u, "totp_enabled", False))
        add("2FA", "ok" if protected == len(users) else "warn", f"{protected} von {len(users)} Benutzer(n) haben 2FA aktiviert.")
        recovery = sum(_recovery_code_count(u) for u in users)
        add("2FA-Recovery-Codes", "ok" if recovery else "warn", f"Verfügbare Recovery-Codes gesamt: {recovery}.")
        signed = sum(1 for u in users if _verify_user_security_state(u))
        add("DB-Manipulationsschutz Benutzer", "ok" if signed == len(users) else "danger", f"{signed} von {len(users)} Benutzer-Sicherheitszuständen haben eine gültige HMAC-Signatur. Policy: {_user_signature_policy()}.")
    else:
        add("Benutzer", "danger", "Kein Benutzer gefunden.")

    add("Session-Cookie HttpOnly", "ok" if current_app.config.get("SESSION_COOKIE_HTTPONLY") else "danger", f"SESSION_COOKIE_HTTPONLY={current_app.config.get('SESSION_COOKIE_HTTPONLY')}")
    add("Session-Cookie Secure", "ok" if current_app.config.get("SESSION_COOKIE_SECURE") else "warn", "Für reinen HTTPS-Betrieb sollte SESSION_COOKIE_SECURE=true gesetzt werden.")
    add("HSTS", "ok" if current_app.config.get("APP_HSTS") else "warn", "Für produktiven HTTPS-Betrieb sollte APP_HSTS=true gesetzt werden.")
    add("Proxy-Header", "ok" if current_app.config.get("TRUST_PROXY_HEADERS") else "info", "TRUST_PROXY_HEADERS nur hinter vertrauenswürdigem Reverse Proxy aktivieren; sonst false lassen.")

    auth_log = Path(current_app.config.get("AUTH_LOG_FILE"))
    add("Auth-Logdatei", "ok" if auth_log.parent.exists() else "danger", str(auth_log))
    if auth_log.exists():
        mode = oct(auth_log.stat().st_mode & 0o777)
        add("Auth-Log Berechtigungen", "ok" if mode in {"0o600", "0o640"} else "warn", f"Dateimodus: {mode}")

    data_dir = Path(current_app.config["DATA_DIR"])
    cfg = data_dir / "config.json"
    db_file = data_dir / "addressbook.db"
    for label, path, expected_modes in [
        ("Runtime-Secrets", cfg, {"0o600", "0o640"}),
        ("SQLite-Datenbank", db_file, {"0o600", "0o640", "0o644"}),
    ]:
        if path.exists():
            mode = oct(path.stat().st_mode & 0o777)
            add(label, "ok" if mode in expected_modes else "warn", f"{path} Modus {mode}")
        else:
            add(label, "warn", f"{path} existiert aktuell nicht.")

    backup_dir = Path(current_app.config["BACKUP_DIR"])
    plain = len([p for p in backup_dir.glob("*.db") if p.is_file()]) if backup_dir.exists() else 0
    encrypted = len([p for p in backup_dir.glob("*.rabenc") if p.is_file()]) if backup_dir.exists() else 0
    full = len([p for p in backup_dir.glob("*.rabfull") if p.is_file()]) if backup_dir.exists() else 0
    add("Backups", "ok" if full or encrypted or plain == 0 else "warn", f"{full} verschlüsselte Vollbackups .rabfull, {encrypted} verschlüsselte .rabenc, {plain} unverschlüsselte .db Backups.")

    add("SQLite-Dateiverschlüsselung", "info", "Die produktive SQLite-Datei ist nicht vollständig SQLCipher-verschlüsselt. Sensible Gerätepasswörter sind feldweise verschlüsselt; Benutzer-Sicherheitsfelder sind zusätzlich HMAC-signiert.")
    add("Brute-Force-Sperre", "ok", f"Limit {_get_bruteforce_settings()['limit']} Fehlversuche je IP/Benutzer innerhalb {_get_bruteforce_settings()['window_seconds']} Sekunden.")
    return items


def _backup_kdf(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600_000,
    )
    return kdf.derive(password.encode("utf-8"))


def _encrypt_backup_bytes(data: bytes, password: str) -> bytes:
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = _backup_kdf(password, salt)
    encrypted = AESGCM(key).encrypt(nonce, data, None)
    meta = {"v": 1, "kdf": "PBKDF2-HMAC-SHA256", "iterations": 600000, "cipher": "AES-256-GCM"}
    meta_bytes = json.dumps(meta, separators=(",", ":")).encode("utf-8")
    return b"RABENC1\n" + len(meta_bytes).to_bytes(2, "big") + meta_bytes + salt + nonce + encrypted


def _decrypt_backup_bytes(data: bytes, password: str) -> bytes:
    if not data.startswith(b"RABENC1\n"):
        raise ValueError("Diese Datei ist kein verschlüsseltes RustDesk-AddressBook-Backup.")
    if not password:
        raise ValueError("Für dieses verschlüsselte Backup wird das Backup-Passwort benötigt.")
    pos = len(b"RABENC1\n")
    if len(data) < pos + 2 + 16 + 12:
        raise ValueError("Verschlüsseltes Backup ist beschädigt oder unvollständig.")
    meta_len = int.from_bytes(data[pos:pos+2], "big")
    pos += 2
    meta = json.loads(data[pos:pos+meta_len].decode("utf-8"))
    pos += meta_len
    salt = data[pos:pos+16]
    pos += 16
    nonce = data[pos:pos+12]
    pos += 12
    encrypted = data[pos:]
    iterations = int(meta.get("iterations", 600000))
    if iterations != 600000:
        raise ValueError("Nicht unterstützte Backup-KDF-Iterationenzahl.")
    try:
        key = _backup_kdf(password, salt)
        return AESGCM(key).decrypt(nonce, encrypted, None)
    except Exception as exc:
        raise ValueError("Backup konnte nicht entschlüsselt werden. Passwort falsch oder Datei beschädigt.") from exc


def _sqlite_backup_bytes(db_file: Path) -> bytes:
    """Create a consistent SQLite snapshot and return it as bytes."""
    if not db_file.exists():
        raise ValueError(f"SQLite-Datenbank nicht gefunden: {db_file}")
    tmp_dir = Path(current_app.config["DATA_DIR"]) / "tmp_backups"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_file = tmp_dir / f"snapshot-{secrets.token_hex(8)}.db"
    try:
        src = sqlite3.connect(str(db_file))
        dst = sqlite3.connect(str(tmp_file))
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        return tmp_file.read_bytes()
    finally:
        try:
            tmp_file.unlink(missing_ok=True)
        except OSError:
            pass


def _write_secure_file(path: Path, data: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp-{secrets.token_hex(4)}")
    tmp.write_bytes(data)
    try:
        tmp.chmod(mode)
    except PermissionError:
        pass
    tmp.replace(path)


def _create_encrypted_database_backup(db_file: Path, backup_dir: Path, password: str, prefix: str = "addressbook") -> str:
    backup_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db.rabenc"
    data = _sqlite_backup_bytes(db_file)
    _write_secure_file(backup_dir / filename, _encrypt_backup_bytes(data, password))
    return filename


def _create_database_backup(db_file: Path, backup_dir: Path, prefix: str = "addressbook") -> str:
    backup_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
    _write_secure_file(backup_dir / filename, _sqlite_backup_bytes(db_file))
    return filename


def _add_file_to_tar(tar: tarfile.TarFile, source: Path, arcname: str) -> None:
    if not source.exists() or not source.is_file():
        return
    info = tar.gettarinfo(str(source), arcname=arcname)
    # Avoid leaking host ownership into the archive.
    info.uid = info.gid = 0
    info.uname = info.gname = "root"
    with source.open("rb") as fh:
        tar.addfile(info, fh)


def _add_dir_to_tar(tar: tarfile.TarFile, source_dir: Path, arc_prefix: str) -> None:
    if not source_dir.exists() or not source_dir.is_dir():
        return
    for path in sorted(source_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(source_dir).as_posix()
        if any(part in {"tmp_uploads", "tmp_backups", "__pycache__"} for part in path.parts):
            continue
        _add_file_to_tar(tar, path, f"{arc_prefix}/{rel}")


def _create_encrypted_full_backup(db_file: Path, backup_dir: Path, password: str) -> str:
    data_dir = Path(current_app.config["DATA_DIR"])
    backup_dir.mkdir(parents=True, exist_ok=True)
    filename = f"addressbook-full-{datetime.now().strftime('%Y%m%d-%H%M%S')}.rabfull"
    manifest = {
        "format": "rustdesk-addressbook-full-backup",
        "version": 1,
        "app_version": current_app.config.get("APP_VERSION", "unknown"),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "contains": ["addressbook.db", "config.json", "ssh", "certs", "logs"],
        "restore_note": "Nach Restore eines Vollbackups den Container neu starten, damit config.json neu geladen wird.",
    }
    buf = BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        manifest_bytes = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")
        info = tarfile.TarInfo("manifest.json")
        info.size = len(manifest_bytes)
        info.mtime = time.time()
        tar.addfile(info, BytesIO(manifest_bytes))

        db_bytes = _sqlite_backup_bytes(db_file)
        info = tarfile.TarInfo("data/addressbook.db")
        info.size = len(db_bytes)
        info.mtime = time.time()
        info.mode = 0o600
        tar.addfile(info, BytesIO(db_bytes))

        _add_file_to_tar(tar, data_dir / "config.json", "data/config.json")
        _add_dir_to_tar(tar, data_dir / "ssh", "data/ssh")
        _add_dir_to_tar(tar, data_dir / "certs", "data/certs")
        _add_dir_to_tar(tar, data_dir / "logs", "data/logs")

    _write_secure_file(backup_dir / filename, _encrypt_backup_bytes(buf.getvalue(), password))
    return filename


def _safe_extract_full_backup(tar_bytes: bytes, data_dir: Path) -> list[str]:
    allowed_exact = {"manifest.json", "data/addressbook.db", "data/config.json"}
    allowed_prefixes = ("data/ssh/", "data/certs/", "data/logs/")
    tmp_dir = data_dir / "tmp_restore_full" / secrets.token_hex(8)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    restored: list[str] = []
    try:
        with tarfile.open(fileobj=BytesIO(tar_bytes), mode="r:gz") as tar:
            names = tar.getnames()
            if "manifest.json" not in names or "data/addressbook.db" not in names or "data/config.json" not in names:
                raise ValueError("Vollbackup ist unvollständig. manifest.json, data/addressbook.db oder data/config.json fehlt.")
            for member in tar.getmembers():
                name = member.name
                if member.isdir():
                    continue
                if name.startswith("/") or ".." in Path(name).parts:
                    raise ValueError(f"Unsicherer Pfad im Vollbackup: {name}")
                if name not in allowed_exact and not name.startswith(allowed_prefixes):
                    raise ValueError(f"Nicht erlaubter Pfad im Vollbackup: {name}")
                tar.extract(member, tmp_dir)

        candidate_db = tmp_dir / "data" / "addressbook.db"
        _validate_addressbook_sqlite(candidate_db)

        for rel in ["addressbook.db", "config.json"]:
            src = tmp_dir / "data" / rel
            if src.exists():
                dst = data_dir / rel
                _write_secure_file(dst, src.read_bytes(), 0o600)
                restored.append(f"data/{rel}")

        for subdir in ["ssh", "certs", "logs"]:
            src_root = tmp_dir / "data" / subdir
            if not src_root.exists():
                continue
            for src in src_root.rglob("*"):
                if not src.is_file():
                    continue
                rel = src.relative_to(src_root)
                dst = data_dir / subdir / rel
                mode = 0o600 if subdir in {"ssh", "certs"} else 0o640
                _write_secure_file(dst, src.read_bytes(), mode)
                restored.append(f"data/{subdir}/{rel.as_posix()}")

        return restored
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _restore_database_from_file(source: Path, db_file: Path, backup_dir: Path, *, password: str = "") -> str:
    if source.name.lower().endswith(".rabfull"):
        if not password:
            raise ValueError("Für ein verschlüsseltes Vollbackup wird das Backup-Passwort benötigt.")
        # DB-Sicherheitsbackup des aktuellen Stands; config/ssh/certs bitte vorher per Vollbackup sichern.
        safety_backup = _create_database_backup(db_file, backup_dir, prefix="pre-full-restore-addressbook")
        tar_bytes = _decrypt_backup_bytes(source.read_bytes(), password)
        db.session.remove()
        db.engine.dispose()
        restored = _safe_extract_full_backup(tar_bytes, Path(current_app.config["DATA_DIR"]))
        return f"{safety_backup}; Vollbackup-Dateien wiederhergestellt: {len(restored)}. Container-Neustart erforderlich"

    restore_source = source
    tmp_plain: Path | None = None
    if source.name.lower().endswith(".rabenc"):
        upload_root = Path(current_app.config["DATA_DIR"]) / "tmp_uploads"
        upload_root.mkdir(parents=True, exist_ok=True)
        tmp_plain = upload_root / f"decrypted-restore-{secrets.token_hex(8)}.db"
        tmp_plain.write_bytes(_decrypt_backup_bytes(source.read_bytes(), password))
        restore_source = tmp_plain
    try:
        _validate_addressbook_sqlite(restore_source)
        safety_backup = _create_database_backup(db_file, backup_dir, prefix="pre-restore-addressbook")
        db.session.remove()
        db.engine.dispose()
        shutil.copy2(restore_source, db_file)
        return safety_backup
    finally:
        if tmp_plain is not None:
            try:
                tmp_plain.unlink(missing_ok=True)
            except OSError:
                pass


def _fill_device_from_form(device: Device) -> None:
    name = request.form.get("name", "").strip()
    rustdesk_id = request.form.get("rustdesk_id", "").strip()
    if not name or not rustdesk_id:
        abort(400, description="Name und RustDesk-ID sind Pflichtfelder")

    password = request.form.get("password", "")
    group_id = request.form.get("group_id", "").strip()
    clear_password = normalize_bool(request.form.get("clear_password"))

    device.name = name
    device.rustdesk_id = rustdesk_id
    if clear_password:
        device.encrypted_password = None
    elif password:
        device.encrypted_password = encrypt_value(password)
    elif not getattr(device, "id", None):
        device.encrypted_password = None
    device.customer = request.form.get("customer", "").strip() or None
    device.location = request.form.get("location", "").strip() or None
    device.os = _normalize_os(request.form.get("os", "")) or None
    device.tags = request.form.get("tags", "").strip() or None
    device.notes = request.form.get("notes", "").strip() or None
    device.favorite = normalize_bool(request.form.get("favorite"))
    device.online = normalize_bool(request.form.get("online"))
    device.group_id = int(group_id) if group_id.isdigit() else None


def _ui_timestamp() -> str:
    return datetime.now().strftime("%d.%m.%Y %H:%M:%S")


def _get_bruteforce_settings() -> dict:
    try:
        default_limit = int(current_app.config.get("LOGIN_FAIL_LIMIT", 5))
    except (TypeError, ValueError):
        default_limit = 5
    try:
        default_window = int(current_app.config.get("LOGIN_FAIL_WINDOW_SECONDS", 900))
    except (TypeError, ValueError):
        default_window = 900

    try:
        limit = int(_get_setting("login_fail_limit", str(default_limit)) or default_limit)
    except (TypeError, ValueError):
        limit = default_limit
    try:
        window_seconds = int(_get_setting("login_fail_window_seconds", str(default_window)) or default_window)
    except (TypeError, ValueError):
        window_seconds = default_window

    limit = min(max(limit, 2), 50)
    window_seconds = min(max(window_seconds, 60), 86400)
    return {
        "limit": limit,
        "window_seconds": window_seconds,
        "window_minutes": max(int(round(window_seconds / 60)), 1),
    }



def _version_number(value: str) -> int:
    raw = str(value or "")
    match = re.search(r"v(\d{3,})", raw)
    if match:
        return int(match.group(1))
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", raw)
    if match:
        major, minor, patch = (int(part) for part in match.groups())
        return major * 10000 + minor * 100 + patch
    return 0


def _fetch_text_url(url: str, timeout: float = 5.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": f"RustDesk-AddressBook/{_short_app_version(current_app.config.get('APP_VERSION', 'dev'))}"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = response.read(256 * 1024)
    return data.decode("utf-8", errors="replace")


def _normalize_release_notes(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = [str(item).strip() for item in value]
    else:
        items = [line.strip() for line in str(value).replace("\r\n", "\n").split("\n")]
    cleaned: list[str] = []
    for item in items:
        if not item or item.startswith("#"):
            continue
        item = re.sub(r"^[-*•]\s+", "", item).strip()
        if item:
            cleaned.append(item[:500])
    return cleaned[:30]


def _fetch_remote_release_notes(base: str, file_name: str) -> list[str]:
    if not file_name:
        return []
    stem = Path(file_name).stem
    version_match = re.search(r"v(\d+)", file_name)
    version_tag = f"v{version_match.group(1)}" if version_match else ""
    candidates = [
        f"{base}/{stem}.txt",
        f"{base}/{stem}.md",
    ]
    if version_tag:
        candidates.extend([
            f"{base}/release-notes-{version_tag}.txt",
            f"{base}/release-notes-{version_tag}.md",
            f"{base}/releases/{version_tag}.txt",
            f"{base}/releases/{version_tag}.md",
        ])
    for url in candidates:
        try:
            notes = _normalize_release_notes(_fetch_text_url(url))
            if notes:
                return notes
        except Exception:
            continue
    return []


def _online_update_manifest() -> dict:
    base = str(current_app.config.get("RAB_UPDATE_BASE_URL", "https://dl.ab-xnet.de") or "https://dl.ab-xnet.de").rstrip("/")
    errors: list[str] = []

    try:
        text = _fetch_text_url(f"{base}/latest.txt")
        lines = [line.strip() for line in text.splitlines()]
        for idx, line in enumerate(lines):
            candidate = line.split()[0] if line else ""
            if not candidate or candidate.startswith("#"):
                continue
            if re.match(r"^v\d+$", candidate):
                candidate = f"rustdesk-addressbook-update-flat-{candidate}.zip"
            if re.match(r"^rustdesk-addressbook-update-flat-v\d+\.zip$", candidate):
                inline_notes = _normalize_release_notes(lines[idx + 1:])
                file_name = Path(candidate).name
                notes = inline_notes or _fetch_remote_release_notes(base, file_name)
                return {"ok": True, "base_url": base, "file": file_name, "version": "", "source": "latest.txt", "release_notes": notes, "errors": []}
        errors.append("latest.txt enthält keine gültige Update-ZIP.")
    except Exception as exc:
        errors.append(f"latest.txt konnte nicht gelesen werden: {exc}")

    return {"ok": False, "base_url": base, "file": "", "version": "", "source": "latest.txt", "release_notes": [], "errors": errors}


def _check_online_update_available() -> dict:
    current_version = current_app.config.get("APP_VERSION", "0.0.0")
    current_num = _version_number(str(current_version))
    checked_at = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    manifest = _online_update_manifest()
    result = {
        "checked_at": checked_at,
        "ok": bool(manifest.get("ok")),
        "current_version": _short_app_version(str(current_version)),
        "current_version_full": str(current_version),
        "current_num": current_num,
        "base_url": manifest.get("base_url", ""),
        "latest_file": manifest.get("file", ""),
        "latest_version": manifest.get("version") or "",
        "latest_num": 0,
        "download_url": "",
        "update_available": False,
        "source": manifest.get("source", ""),
        "message": "",
        "release_notes": manifest.get("release_notes", []),
        "errors": manifest.get("errors", []),
    }
    if not manifest.get("ok"):
        result["message"] = "Kein gültiges Online-Manifest gefunden."
        return result

    latest_file = str(manifest.get("file") or "")
    latest_num = _version_number(str(manifest.get("version") or latest_file))
    result["latest_num"] = latest_num
    result["download_url"] = f"{str(manifest.get('base_url')).rstrip('/')}/{latest_file}"
    if latest_num > current_num:
        result["update_available"] = True
        result["message"] = f"Update verfügbar: {latest_file}"
    else:
        result["message"] = "Kein Update verfügbar. Die installierte Version ist aktuell oder neuer."
    return result


def _record_update_check(result: dict) -> None:
    _set_setting("update_last_checked_at", str(result.get("checked_at", ""))[:64])
    _set_setting("update_last_checked_ts", str(int(time.time())))
    _set_setting("update_last_ok", "1" if result.get("ok") else "0")
    _set_setting("update_last_message", str(result.get("message", ""))[:500])
    _set_setting("update_last_file", str(result.get("latest_file", ""))[:255])
    _set_setting("update_last_url", str(result.get("download_url", ""))[:500])
    _set_setting("update_last_available", "1" if result.get("update_available") else "0")
    notes = result.get("release_notes") or []
    _set_setting("update_last_release_notes", "\n".join(str(item) for item in notes)[:4000])


def _get_update_check_info() -> dict:
    ok_raw = _get_setting("update_last_ok", "")
    try:
        checked_ts = int(_get_setting("update_last_checked_ts", "0") or "0")
    except ValueError:
        checked_ts = 0
    auto_settings = _get_update_auto_check_settings(checked_ts=checked_ts)
    return {
        "checked_at": _get_setting("update_last_checked_at", ""),
        "checked_ts": checked_ts,
        "ok": True if ok_raw == "1" else False if ok_raw == "0" else None,
        "message": _get_setting("update_last_message", ""),
        "file": _get_setting("update_last_file", ""),
        "url": _get_setting("update_last_url", ""),
        "available": normalize_bool(_get_setting("update_last_available", "0")),
        "release_notes": _normalize_release_notes(_get_setting("update_last_release_notes", "")),
        "stale": auto_settings["stale"],
        "age_seconds": auto_settings["age_seconds"],
    }


def _get_update_auto_check_settings(checked_ts: int | None = None) -> dict:
    enabled = normalize_bool(_get_setting("update_auto_check_enabled", "1"))
    try:
        interval_seconds = int(_get_setting("update_auto_check_interval_seconds", "21600") or "21600")
    except ValueError:
        interval_seconds = 21600
    interval_seconds = min(max(interval_seconds, 3600), 604800)
    if checked_ts is None:
        try:
            checked_ts = int(_get_setting("update_last_checked_ts", "0") or "0")
        except ValueError:
            checked_ts = 0
    age_seconds = int(time.time()) - checked_ts if checked_ts else 999999999
    return {
        "enabled": enabled,
        "interval_seconds": interval_seconds,
        "interval_hours": max(1, int(interval_seconds // 3600)),
        "stale": bool(enabled and age_seconds >= interval_seconds),
        "age_seconds": max(0, age_seconds),
    }

def _get_setting(key: str, default: str = "") -> str:
    setting = Setting.query.filter_by(key=key).first()
    return setting.value if setting else default


def _get_language() -> str:
    lang = _get_setting("language", "de").strip().lower()
    return lang if lang in {key for key, _label in LANGUAGE_CHOICES} else "de"


def _t(key: str, default: str | None = None) -> str:
    lang = _get_language()
    if lang == "de":
        return default if default is not None else key
    return TRANSLATIONS.get(lang, {}).get(key, default if default is not None else key)


def _translated_theme_choices() -> list[tuple[str, str]]:
    return [("light", _t("theme.light", "Heller Modus")), ("dark", _t("theme.dark", "Darkmode"))]


def _translated_status_source_choices() -> list[tuple[str, str]]:
    return [("manual", _t("status.manual", "Nur manuell")), ("hbbs", _t("status.hbbs", "hbbs Live-Abfrage"))]


def _get_theme_mode() -> str:
    mode = _get_setting("theme_mode", "light").strip().lower()
    return mode if mode in {"light", "dark"} else "light"


def _get_status_settings() -> dict:
    source = _get_setting("status_source", "manual").strip().lower()
    allowed = {key for key, _label in STATUS_SOURCE_CHOICES}
    if source not in allowed:
        source = "manual"
    host = _get_setting("hbbs_host", "").strip()
    try:
        port = int(_get_setting("hbbs_port", "21115") or "21115")
    except ValueError:
        port = 21115
    try:
        timeout = float(_get_setting("hbbs_timeout", "3") or "3")
    except ValueError:
        timeout = 3.0
    try:
        batch_size = int(_get_setting("hbbs_batch_size", "50") or "50")
    except ValueError:
        batch_size = 50
    requester_id = _get_setting("hbbs_requester_id", "rustdesk-addressbook").strip() or "rustdesk-addressbook"
    return {
        "source": source,
        "hbbs_host": host,
        "hbbs_port": min(max(port, 1), 65535),
        "hbbs_timeout": min(max(timeout, 1.0), 30.0),
        "hbbs_batch_size": min(max(batch_size, 1), 500),
        "hbbs_requester_id": requester_id[:80],
    }


def _normalize_group_color(value: str | None) -> str:
    text = _safe_text(value) or "secondary"
    allowed = {key for key, _label in GROUP_COLOR_CHOICES}
    return text if text in allowed else "secondary"


def _normalize_group_icon(value: str | None) -> str:
    text = (_safe_text(value) or "collection").lower()
    allowed = {key for key, _label in GROUP_ICON_CHOICES}
    if text in allowed:
        return text
    # Bestehende Altwerte aus früheren Versionen bleiben erhalten,
    # solange sie nur als sichere Bootstrap-Icon-Klasse verwendbar sind.
    if 1 <= len(text) <= 64 and all(ch.isalnum() or ch == "-" for ch in text):
        return text
    return "collection"


def _set_setting(key: str, value: str) -> None:
    setting = Setting.query.filter_by(key=key).first()
    if setting:
        setting.value = value
    else:
        db.session.add(Setting(key=key, value=value))
    db.session.commit()


def _parse_os_choices(raw: str) -> list[str]:
    seen = set()
    choices = []
    for line in raw.replace(",", "\n").splitlines():
        value = line.strip()
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        choices.append(value[:64])
    return choices[:100]


def _get_os_choices() -> list[str]:
    try:
        raw = _get_setting("os_choices", "")
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    choices = [str(x).strip()[:64] for x in parsed if str(x).strip()]
                    if choices:
                        return choices
            except json.JSONDecodeError:
                choices = _parse_os_choices(raw)
                if choices:
                    return choices
    except Exception:
        pass
    return list(DEFAULT_OS_CHOICES)


def _resolve_group_name_from_form(default: str = "RustDesk Server") -> str:
    group_id = request.form.get("group_id", "").strip()
    new_group = request.form.get("group_name_new", "").strip()
    legacy_group = request.form.get("group_name", "").strip()
    if group_id.isdigit():
        group = db.session.get(Group, int(group_id))
        if group:
            return group.name
    if new_group:
        return new_group[:120]
    if legacy_group:
        return legacy_group[:120]
    return default


def _get_or_create_group(name: str | None) -> Group | None:
    if not name:
        return None
    clean = name.strip()
    if not clean:
        return None
    group = Group.query.filter_by(name=clean).first()
    if group:
        return group
    group = Group(name=clean)
    db.session.add(group)
    db.session.flush()
    return group
