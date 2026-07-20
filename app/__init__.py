from __future__ import annotations

import base64
import csv
import hashlib
import hmac
import ipaddress
import json
import os
import re
import secrets
import shutil
import socket
import sqlite3
import subprocess
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timedelta
from functools import wraps
from io import BytesIO, StringIO
from pathlib import Path

import pyotp
import qrcode
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from flask import (
    Flask,
    Response,
    abort,
    current_app,
    flash,
    g,
    has_request_context,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import bindparam, false, or_, text
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from .config import Config
from .crypto import decrypt_value, encrypt_value
from .extensions import db, login_manager, oauth
from .helpers import csrf_token, normalize_bool, parse_csv_upload, rustdesk_link, validate_csrf
from .models import AuthEvent, Device, Group, ImportBlocklistEntry, Setting, TransientSecret, User, utcnow
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
        "nav.toggle": "Toggle navigation",
        "common.save": "Save",
        "common.active": "Active",
        "common.inactive": "Inactive",
        "common.error": "Error",
        "common.ok": "OK",
        "common.search": "Search",
        "common.all": "All",
        "common.never_checked": "never checked",
        "common.no_online_check": "no online status check",
        "common.no_message": "No message received.",
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
        "devices.hbbs_missing_title": "Enter hbbs host under Settings",
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
        "settings.twofa.pending": "Setup pending",
        "settings.twofa.recovery_title": "Recovery codes",
        "settings.twofa.recovery_intro": "Save these codes securely now. They are shown only once. Each code can be used exactly once instead of the authenticator code.",
        "settings.twofa.enabled_msg": "2FA is enabled. The next login requires an authenticator code or a one-time recovery code.",
        "settings.twofa.recovery_available": "Recovery codes available",
        "settings.twofa.recovery_hash_notice": "Codes are stored only as hashes and cannot be read afterwards.",
        "settings.twofa.code_or_recovery": "2FA code or recovery code",
        "settings.twofa.disable_confirm": "Really disable 2FA?",
        "settings.twofa.disable": "Disable 2FA",
        "settings.twofa.regenerate_title": "Regenerate recovery codes",
        "settings.twofa.regenerate_help": "Creates new codes and invalidates all old recovery codes.",
        "settings.twofa.regenerate_confirm": "Create new recovery codes and invalidate all old ones?",
        "settings.twofa.regenerate": "Create new recovery codes",
        "settings.twofa.scan_help": "Scan the QR code with your authenticator app and then confirm a current code. Enabling also creates one-time recovery codes.",
        "settings.twofa.manual_secret": "Secret for manual entry",
        "settings.twofa.app_code": "2FA code from app",
        "settings.twofa.enable": "Enable 2FA",
        "settings.twofa.cancel_setup": "Discard setup",
        "settings.twofa.setup": "Set up 2FA",
        "settings.twofa.setup_help": "After enabling, recovery codes are shown; save them offline.",
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
        "settings.update.help": "Checks the configured release source through latest.txt and shows available changes.",
        "settings.update.disabled": "Online update checks are disabled because RAB_UPDATE_BASE_URL is not configured. Local signed updates remain available.",
        "settings.update.now": "Check now",
        "settings.update.checking": "Checking...",
        "settings.update.failed": "Update check failed",
        "update.error.invalid_manifest": "latest.txt does not contain a valid update ZIP.",
        "update.error.read_failed": "latest.txt could not be read: {error}",
        "update.message.no_manifest": "No valid online manifest found.",
        "update.message.available": "Update available: {file}",
        "update.message.current": "No update available. The installed version is current or newer.",
        "settings.update.none": "No online update check has been performed yet.",
        "settings.update.available": "Update available",
        "settings.update.current": "Current",
        "settings.update.changes": "Changes in this version",
        "settings.update.auto": "Check automatically",
        "settings.update.interval": "Interval",
        "settings.update.save": "Save update check",
        "settings.update.install_hint": "Updates are installed with ./scripts/update.sh. The script always checks local signed ZIP files in updates/ and checks an online release source only when RAB_UPDATE_BASE_URL is configured.",
        "settings.security.title": "Security notes",
        "settings.security.https": "Run the app through HTTPS when it is reachable outside your LAN.",
        "settings.security.fernet": "Device passwords in the database are encrypted with Fernet. The key is stored in ./data/config.json.",
        "settings.security.backups": "For portable backups, create encrypted backups with AES-256-GCM and PBKDF2-HMAC-SHA256.",
        "settings.security.data_backup": "Back up ./data and ./backups regularly. Without ./data/config.json, saved device passwords cannot be decrypted.",
        "common.connect": "Connect",
        "common.edit": "Edit",
        "common.delete": "Delete",
        "common.download": "Download",
        "common.upload": "Upload",
        "common.file": "File",
        "common.group": "Group",
        "common.new_group_optional": "New group optional",
        "common.update_existing": "Update existing devices with the same RustDesk ID",
        "common.password": "Password",
        "common.current_password": "Current password",
        "common.cancel": "Cancel",
        "common.close": "Close",
        "release.title": "Show release changes",
        "common.status": "Status",
        "common.last_check": "Last check",
        "common.changed": "Changed",
        "common.created": "Created",
        "common.updated": "Updated",
        "common.actions": "Actions",
        "common.skipped": "Skipped",
        "common.duration": "Duration",
        "common.bytes": "Transferred",
        "common.notes": "Notes",
        "common.customer": "Customer",
        "common.location": "Location",
        "common.tags": "Tags",
        "common.yes": "Yes",
        "common.no": "No",
        "common.default": "Default",
        "views.label": "View",
        "views.cards": "Cards",
        "views.list": "List",
        "views.icons": "Small icons",
        "device.card.favorite_toggle": "Toggle favorite",
        "device.card.connect": "Connect",
        "device.card.edit": "Edit",
        "device.card.manual_status": "Toggle manual status",
        "device.card.online_title": "Online / last live status online",
        "device.card.offline_title": "Offline / last live status offline",
        "device.card.no_group": "No group",
        "device_form.title_new": "Add device",
        "device_form.title_edit": "Edit device",
        "device_form.subtitle": "Store RustDesk ID and optional password.",
        "device_form.name": "Name",
        "device_form.rustdesk_id": "RustDesk ID",
        "device_form.rustdesk_password": "RustDesk password",
        "device_form.password_placeholder_saved": "Saved password remains unchanged",
        "device_form.password_toggle": "Show or hide password",
        "device_form.password_placeholder_optional": "Optional",
        "device_form.password_help": "Remains unchanged when the field is empty. The password is stored encrypted in SQLite.",
        "device_form.clear_password": "Delete saved password",
        "device_form.group": "Group",
        "device_form.no_group": "No group",
        "device_form.device_type": "Device type / operating system",
        "device_form.favorite": "Favorite",
        "device_form.online_manual": "Manual online status",
        "device_form.save": "Save device",
        "device_form.delete_confirm": "Really delete this device? Its RustDesk ID will be blocked automatically for future imports.",
        "backup.title": "Backup",
        "backup.subtitle": "Back up the database, create encrypted full backups, download and restore.",
        "backup.create": "Create backup",
        "backup.important": "Important",
        "backup.warning": "For a complete restore including device passwords, ./data/config.json is required. Create an encrypted full backup for that. It includes the database, config.json, data/ssh, data/certs and logs. Unencrypted full backups are not offered for security reasons.",
        "backup.file": "File",
        "backup.type": "Type",
        "backup.size": "Size",
        "backup.changed": "Changed",
        "backup.actions": "Actions",
        "backup.full": "Full backup",
        "backup.encrypted": "encrypted",
        "backup.password_placeholder": "Backup password",
        "backup.restore_confirm": "Really restore this backup? Full backups also overwrite config.json, SSH and certificate files. After restoring a full backup, the container must be restarted.",
        "backup.restore": "Restore",
        "backup.delete_confirm": "Really delete this backup?",
        "backup.none": "No backups yet.",
        "backup.host_folder": "Backups are also stored in the host folder ./backups.",
        "backup.full_create": "Create encrypted full backup",
        "backup.full_help": "Includes addressbook.db, config.json, data/ssh, data/certs and data/logs. This is the recommended restore file for server migration or total failure.",
        "backup.full_password": "Full backup password",
        "backup.full_password_help": "At least 16 characters. This backup contains key material and should only be stored encrypted.",
        "backup.repeat": "Repeat password",
        "backup.db_create": "Create encrypted database backup",
        "backup.db_password": "Backup password",
        "backup.db_password_help": "At least 12 characters. Contains only the database; device passwords still require the matching config.json.",
        "backup.upload_title": "Upload backup file",
        "backup.restore_password": "Backup password for .rabenc or .rabfull",
        "backup.upload_confirm": "Really restore uploaded backup? The current state is backed up automatically first.",
        "backup.upload_restore": "Upload & restore",
        "groups.title": "Groups",
        "groups.subtitle": "Groups for customers, locations or device types. Icon and color can be selected directly.",
        "groups.new": "New group",
        "groups.name": "Name",
        "groups.color": "Color",
        "groups.icon": "Icon",
        "groups.preview_help": "The preview on the left shows the selected Bootstrap icon.",
        "groups.create": "Create group",
        "groups.assigned": "device(s) assigned",
        "groups.show_devices": "Show devices",
        "groups.delete_confirm": "Delete group? Devices remain unchanged.",
        "groups.current": "Current",
        "groups.none": "No groups yet.",
        "import.title": "Import / Export",
        "import.subtitle": "CSV import/export, RustDesk server import, SSH snapshot import and optional direct DB import in one place.",
        "import.menu.csv": "CSV import / export",
        "import.menu.server": "Server DB upload",
        "import.menu.ssh": "SSH import",
        "import.menu.direct": "Direct DB import",
        "import.menu.notes": "Notes",
        "import.csv.title": "CSV import",
        "import.csv.file": "CSV file",
        "import.csv.button": "Import CSV",
        "import.csv.expected": "Expected columns",
        "import.csv.help": "Required fields are name and rustdesk_id. Groups are created automatically if they do not exist.",
        "import.export.title": "CSV export",
        "import.export.help": "Export your address book as CSV. For security reasons, export without device passwords is the default.",
        "import.export.no_passwords": "Export without passwords",
        "import.export.with_passwords": "Export with passwords",
        "import.export.password_warning": "This export contains decrypted device passwords in clear text. Continue?",
        "import.server.title": "RustDesk server import",
        "import.server.files": "RustDesk server files",
        "import.server.files_help": "Best as ZIP or as multi-file upload: db_v2.sqlite3, db_v2.sqlite3-wal and optionally db_v2.sqlite3-shm.",
        "import.server.button": "Import server DB",
        "import.ssh.title": "RustDesk SSH import",
        "import.ssh.help": "Fetches a consistent snapshot copy of the RustDesk server database via SSH. A dedicated SSH key with forced command on the RustDesk server is recommended.",
        "import.ssh.host": "SSH host",
        "import.ssh.port": "SSH port",
        "import.ssh.user": "SSH user",
        "import.ssh.timeout": "Timeout seconds",
        "import.ssh.key_path": "Private key path in container",
        "import.ssh.key_help": "For security, the key must be below /data; recommended: /data/ssh/rustdesk_import_ed25519.",
        "import.ssh.known_hosts": "Known hosts file",
        "import.ssh.remote_command": "Remote command optional",
        "import.ssh.remote_help": "Leave empty when authorized_keys uses a restricted forced command.",
        "import.ssh.test": "Test SSH transfer",
        "import.ssh.import": "Import via SSH",
        "import.ssh.last": "Last SSH test / import",
        "import.ssh.time": "Time",
        "import.ssh.peers": "Peers",
        "import.ssh.stderr": "SSH stderr",
        "import.direct.title": "Direct DB import",
        "import.direct.help": "Uses a RustDesk server database mounted read-only. WAL/SHM are considered during the SQLite snapshot.",
        "import.direct.button": "Realtime import from mounted DB",
        "import.direct.diagnose": "DB diagnostics",
        "import.direct.active": "active",
        "import.direct.not_found": "not found",
        "import.direct.disabled": "not enabled",
        "import.direct.disabled_title": "RUSTDESK_SERVER_DB is not set or the file does not exist",
        "db.status.not_set": "RUSTDESK_SERVER_DB is not set. Direct DB import and DB diagnostics are disabled.",
        "db.status.active": "Active",
        "db.status.wal_visible": "WAL visible",
        "db.status.shm_visible": "SHM visible",
        "db.status.not_found": "RUSTDESK_SERVER_DB is set, but the file was not found",
        "import.notes.title": "Notes",
        "import.notes.status": "Online status is no longer imported from peer.status. Use Live status hbbs for that.",
        "import.notes.db": "The server DB remains available for device import, WAL/SHM snapshot and diagnostics.",
        "import.notes.passwords": "Unattended device passwords are normally not stored in the free server database and therefore remain empty.",
        "settings.menu.display_line1": "Display",
        "settings.menu.display_line2": "& language",
        "settings.update.hour_1": "1 hour",
        "settings.update.hour_3": "3 hours",
        "settings.update.hour_6": "6 hours",
        "settings.update.hour_12": "12 hours",
        "settings.update.hour_24": "24 hours",
        "settings.update.hour_48": "2 days",
        "settings.update.hour_168": "7 days",
        "theme.light": "Light mode",
        "theme.dark": "Dark mode",
        "status.manual": "Manual only",
        "status.hbbs": "hbbs live query",
        "sort.online": "Online first",
        "sort.name": "Name A-Z",
        "sort.favorites": "Favorites first",
        "sort.updated": "Recently changed",
        "settings.status.minutes_unit": "Minutes",
        "settings.status.hours_unit": "Hours",
        "security.report.log_rotation_name": "Auth log rotation",
        "security.report.log_rotation_detail": "Every {days} day(s), keeping {keep} rotated file(s).",
        "security.report.update_check_name": "Update check",
        "security.report.update_check_detail": "Automatic update check is {state}. Interval: {hours} hour(s).",
        "security.report.hbbs_name": "hbbs live status",
        "security.report.hbbs_detail": "Status source: {source}. Host configured: {host}.",
        "security.report.https_name": "HTTPS endpoint",
        "security.report.https_detail": "The container provides HTTPS; set SESSION_COOKIE_SECURE and APP_HSTS for production HTTPS.",
    }
}

TRANSLATIONS["en"].update({
    "common.choose_file": "Choose file",
    "common.no_file_selected": "No file selected",
    "common.files_selected": "files selected",
    "common.import": "Import",
    "common.integrity": "Integrity",
    "common.time": "Time",
    "common.details": "Details",
    "devices.search_placeholder": "Name, RustDesk ID, customer, location, tags...",
    "dashboard.search_placeholder": "Name, ID, customer, location...",
    "status.last_summary": "{online} online, {offline} offline, {updated} changed",
    "status.trigger.manual": "Manual",
    "status.trigger.auto": "Automatic",
    "status.flash_success": "hbbs live status updated: {updated} changed, {online} online, {offline} offline. Last response states={states}.",
    "status.flash_error": "hbbs live query failed: {error}",
    "status.flash_removed": "Server DB status was removed. Online status is queried through hbbs live; the server DB remains available for import and diagnostics.",
    "import.csv.created": "Import completed: {count} devices created.",
    "import.server.no_file": "Select db_v2.sqlite3 or a ZIP containing db_v2.sqlite3, db_v2.sqlite3-wal and optionally db_v2.sqlite3-shm.",
    "import.server.read_error": "The file could not be read as a RustDesk SQLite database: {error}",
    "import.server.wal_seen": " WAL was considered.",
    "import.server.no_wal": " No WAL file was found in the upload.",
    "import.server.status_note": " Online status is not imported from the server DB; use Live status hbbs for that.",
    "import.server.done": "RustDesk server import completed: {created} created, {updated} updated, {skipped} skipped.",
    "import.ssh.result_import": "Import",
    "import.ssh.host_fingerprint": "Verified SSH host-key fingerprint",
    "import.ssh.host_fingerprint_help": "Compare the SHA-256 fingerprint with the RustDesk server through a trusted channel. Only the matching host key is stored in known_hosts.",
    "settings.status.host_placeholder": "rustdesk.example.com or IP",
    "settings.status.port_help": "Usually 21115 when your hbbs main port is 21116.",
    "settings.status.requester_help": "Only an identifier for the protocol request. It is not a device ID and not a password.",
    "settings.status.saved": "Online status settings saved.",
    "settings.update.saved": "Update check settings saved.",
    "security.title": "Security",
    "security.subtitle": "Login audit log, brute-force protection and security checks.",
    "security.download_auth_log": "Download auth.log",
    "security.status_title": "Security status",
    "security.fail2ban_title": "Fail2ban / CrowdSec",
    "security.log_intro": "The app writes failed logins to this file:",
    "security.fail_marker": "Failures contain the marker",
    "security.fail_filter": "Example fail2ban filter:",
    "security.internal_lockout": "Internal lockout: {limit} failed attempts per source IP within {window} seconds.",
    "security.log_rotation": "Auth log rotation: every {days} day(s), keeping {keep} rotated file(s).",
    "security.auth_events": "Latest login / 2FA events",
    "security.table.time": "Time",
    "security.table.status": "Status",
    "security.table.event": "Event",
    "security.table.user": "User",
    "security.table.ip": "IP",
    "security.table.details": "Details",
    "security.no_events": "No events yet.",
    "security.sqlite_title": "Note about SQLite encryption",
    "security.sqlite_text": "The running SQLite database is not fully SQLCipher-encrypted. Device passwords are encrypted per field. User security fields such as password hash and 2FA state are additionally signed with an HMAC key from data/config.json. This prevents an attacker with only SQLite write access from silently disabling 2FA. If an attacker obtains both database and runtime secrets, the installation is compromised.",
    "security.signature_policy": "Signature policy: strict. Modified roles, OIDC identities and group assignments are blocked; automatic re-signing during login is disabled.",
    "reauth.title": "Reauthentication",
    "reauth.help": "After the sensitive-action window expires, reauthentication is required before retrieving device passwords, exporting passwords or starting a connection.",
    "reauth.oidc": "Sign in again with OpenID Connect",
    "reauth.totp": "2FA code",
    "reauth.confirm": "Confirm",
    "setup.title": "Initial setup",
    "setup.subtitle": "Create the first admin user.",
    "setup.token": "Setup token",
    "setup.token_help": "Enter the one-time token printed by the installer or read it from /data/config.json on the server.",
    "setup.username": "Username",
    "setup.password": "Password",
    "setup.repeat_password": "Repeat password",
    "setup.create": "Create admin",
    "release.title": "Release notes",
    "release.subtitle": "Change history of the stable 0.5.x line and earlier build versions.",
    "release.installed": "Installed version",
    "release.internal": "Internal identifier",
    "release.help": "Help",
    "release.update_note": "Update note",
    "release.option_a": "Option A: copy the new flat update ZIP into updates/ and start the script without parameters.",
    "release.option_b": "Option B: start only the script. It checks local updates first, then online, shows changes and asks for download/installation.",
    "help.title": "Guide",
    "help.subtitle": "Installation, update, import, backup and security commands.",
    "help.installation": "Installation",
    "help.update": "Update",
    "help.update_text": "Either copy the update ZIP into updates/ manually or simply run the update script and let it check the configured download server.",
    "help.ssh_import": "SSH import",
    "help.backup": "Backup / restore",
    "help.security": "Security",
    "group.color.primary": "Blue",
    "group.color.secondary": "Gray",
    "group.color.success": "Green",
    "group.color.danger": "Red",
    "group.color.warning": "Yellow",
    "group.color.info": "Cyan",
    "group.color.dark": "Dark",
    "group.icon.collection": "Collection",
    "group.icon.hdd-network": "Server / network",
    "group.icon.server": "Server",
    "group.icon.pc-display": "Client / PC",
    "group.icon.pc-display-horizontal": "Desktop",
    "group.icon.laptop": "Notebook",
    "group.icon.windows": "Windows",
    "group.icon.ubuntu": "Linux",
    "group.icon.apple": "Apple / macOS",
    "group.icon.android2": "Android",
    "group.icon.phone": "Mobile device",
    "group.icon.router": "Router",
    "group.icon.ethernet": "Network",
    "group.icon.globe2": "Internet / remote",
    "group.icon.house": "Private / home",
    "group.icon.building": "Company / building",
    "group.icon.person-workspace": "Workstation",
    "group.icon.people": "Customers / users",
    "group.icon.shield-lock": "Security",
    "group.icon.cloud": "Cloud",
    "group.icon.database": "Database",
    "group.icon.device-hdd": "Storage",
    "group.icon.tools": "Maintenance",
    "group.icon.wrench-adjustable": "Service",
    "group.icon.tag": "Tag / category",
    "group.icon.star": "Favorites",
    "group.icon.folder": "Folder",
})


TRANSLATIONS["en"].update({
    "nav.users": "Users",
    "nav.account": "My account",
    "login.title": "Sign in",
    "login.username": "Username",
    "login.password": "Password",
    "login.local": "Sign in locally",
    "login.or": "or",
    "login.oidc": "Sign in with {provider}",
    "users.title": "User management",
    "users.subtitle": "Manage local and OIDC users, roles and visible device groups.",
    "users.oidc_settings": "Configure OIDC",
    "users.permission_title": "Permission model",
    "users.permission_help": "Regular users can only view devices, retrieve passwords and start RustDesk connections. They only see devices in assigned groups; ungrouped devices are visible to administrators only.",
    "users.create": "Create user",
    "users.username": "Username",
    "users.provider": "Authentication",
    "users.provider_local": "Local",
    "users.role": "Role",
    "users.role_user": "User",
    "users.role_admin": "Administrator",
    "users.active": "Active",
    "users.password": "Password",
    "users.password_local_help": "Required for local users only, at least 8 characters.",
    "users.password_repeat": "Repeat password",
    "users.assigned_groups": "Assigned groups",
    "users.no_groups": "No groups exist yet.",
    "users.create_button": "Create user",
    "users.last_login": "Last login",
    "users.disabled": "Disabled",
    "users.oidc_pending": "Not linked to OIDC yet",
    "users.all_devices": "All devices",
    "users.no_access": "No devices visible",
    "users.delete_confirm": "Really delete this user?",
    "users.edit": "Edit user",
    "users.new_password": "New password",
    "users.new_password_help": "Leave empty to keep the current password. A password is required when switching from OIDC to local authentication.",
    "users.admin_groups_help": "Group assignments do not restrict administrators; they always see all devices.",
    "oidc.title": "OpenID Connect",
    "oidc.subtitle": "Configure centralized sign-in through an OAuth 2.0/OpenID Connect provider.",
    "oidc.local_admin_warning_title": "Keep a local emergency account",
    "oidc.local_admin_warning": "The last active local administrator is protected and cannot be removed, so sign-in remains possible if the OIDC provider is unavailable.",
    "oidc.enabled": "Enable OIDC sign-in",
    "oidc.auto": "Automatically create users on first sign-in",
    "oidc.auto_help": "Automatically created accounts receive the User role and initially have no group assignments.",
    "oidc.issuer": "Issuer URL",
    "oidc.provider_name": "Display name",
    "oidc.secret_keep": "Leave empty to keep the stored secret",
    "oidc.secret_help": "The client secret is stored encrypted in the settings database.",
    "oidc.openid_required": "is always added.",
    "oidc.username_claim": "Username claim",
    "oidc.allowed_domains": "Allowed email domains",
    "oidc.allowed_domains_help": "Optional, comma-separated. Empty means no domain restriction.",
    "oidc.insecure": "Explicitly allow an insecure HTTP issuer URL",
    "oidc.insecure_help": "For isolated test networks only. Production authentication must use HTTPS.",
    "oidc.redirect_uri": "Redirect URI for the provider",
    "oidc.save_test": "Save and test discovery",
    "account.title": "My account",
    "account.oidc_title": "OIDC account",
    "account.oidc_help": "Password and multi-factor authentication are managed by the connected OpenID Connect provider.",
    "account.password_title": "Change password",
    "account.password_save": "Change password",
    "account.twofa_title": "Two-factor authentication",
    "account.recovery_once": "These recovery codes are shown only once:",
    "account.recovery_count": "Remaining recovery codes",
    "account.regenerate": "Regenerate recovery codes",
    "account.disable_twofa": "Disable 2FA",
    "account.enable_twofa": "Enable 2FA",
    "account.setup_twofa": "Set up 2FA",
    "device.card.password": "Password",
    "device.password.title": "RustDesk password",
    "device.password.value": "Stored password",
    "device.password.help": "The password is only displayed for devices your user is allowed to access.",
    "device.password.load_failed": "The password could not be loaded.",
    "common.copy": "Copy",
    "security.report.2fa_local": "{protected} of {total} active local user(s) have 2FA enabled; OIDC MFA is managed by the provider.",
    "security.report.rbac_name": "User roles / emergency access",
    "security.report.rbac_detail": "Active administrators: {admins}; local emergency administrators: {local_admins}. Active OIDC users: {oidc_users}.",
    "security.report.oidc_detail": "OIDC is enabled. Provider: {provider}; auto-provisioning: {auto}; insecure HTTP allowed: {insecure}.",
    "security.report.oidc_disabled": "OIDC sign-in is disabled; local sign-in remains available.",
})


TRANSLATIONS["en"].update({
    "account.preferences_title": "Display & language",
    "account.preferences_help": "These settings apply only to your own user account and do not change the view for other users.",
    "account.preferences_saved": "Display and language were saved for your user account.",
    "account.preferences_invalid_theme": "Invalid display mode.",
    "account.preferences_invalid_language": "Invalid language.",
    "devices.deleted_blocked": "The device was deleted and its RustDesk ID was blocked for future imports.",
    "common.device": "Device",
    "import.menu.blocklist": "Import blocklist",
    "import.blocklist.title": "Import blocklist",
    "import.blocklist.help": "When a device is deleted, its RustDesk ID is added automatically. CSV, server database, SSH and direct database imports skip these IDs so deleted devices do not return.",
    "import.blocklist.device_name": "Device name optional",
    "import.blocklist.reason": "Reason optional",
    "import.blocklist.reason_label": "Reason",
    "import.blocklist.add": "Block ID",
    "import.blocklist.entries": "Blocked RustDesk IDs",
    "import.blocklist.created": "Added",
    "import.blocklist.remove": "Unblock",
    "import.blocklist.remove_confirm": "Remove this ID from the blocklist? It can be imported again afterwards.",
    "import.blocklist.empty": "The import blocklist is empty.",
    "import.blocklist.blocked_short": "blocked",
    "import.blocklist.id_required": "Enter a RustDesk ID.",
    "import.blocklist.device_exists": "This RustDesk ID still exists as a device in the address book.",
    "import.blocklist.added": "The RustDesk ID was added to the import blocklist.",
    "import.blocklist.removed": "The RustDesk ID was removed from the import blocklist and can be imported again.",
    "import.csv.done": "CSV import completed: {created} created, {blocked} skipped by blocklist, {skipped} invalid.",
    "import.server.done": "RustDesk server import completed: {created} created, {updated} updated, {skipped} skipped, {blocked} blocked by import blocklist.",
})


def _resolve_device_view(value: str | None = None) -> str:
    allowed = {"cards", "list", "icons"}
    selected = (value or "").strip().lower()
    if selected in allowed:
        session["device_view"] = selected
        return selected
    stored = str(session.get("device_view") or "cards").strip().lower()
    if stored in allowed:
        return stored
    session["device_view"] = "cards"
    return "cards"


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
    oauth.init_app(app)

    if app.config.get("TRUST_PROXY_HEADERS"):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

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
        reseal_all = False

        legacy_columns = {
            "totp_secret_encrypted": "TEXT",
            "totp_enabled": "BOOLEAN NOT NULL DEFAULT 0",
            "totp_recovery_hashes": "TEXT",
        }
        for column, definition in legacy_columns.items():
            if column not in user_cols:
                conn.exec_driver_sql(f"ALTER TABLE users ADD COLUMN {column} {definition}")
                user_cols.add(column)

        security_signature_created = False
        if "security_signature" not in user_cols:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN security_signature TEXT")
            user_cols.add("security_signature")
            security_signature_created = True

        role_created = "role" not in user_cols
        preference_language_created = "preferred_language" not in user_cols
        preference_theme_created = "preferred_theme" not in user_cols
        auth_columns = {
            "role": "VARCHAR(16) NOT NULL DEFAULT 'user'",
            "active": "BOOLEAN NOT NULL DEFAULT 1",
            "auth_provider": "VARCHAR(16) NOT NULL DEFAULT 'local'",
            "oidc_issuer": "VARCHAR(255)",
            "oidc_subject": "VARCHAR(255)",
            "display_name": "VARCHAR(180)",
            "email": "VARCHAR(255)",
            "preferred_language": "VARCHAR(8) NOT NULL DEFAULT 'de'",
            "preferred_theme": "VARCHAR(16) NOT NULL DEFAULT 'light'",
            "session_version": "INTEGER NOT NULL DEFAULT 1",
        }
        for column, definition in auth_columns.items():
            if column not in user_cols:
                conn.exec_driver_sql(f"ALTER TABLE users ADD COLUMN {column} {definition}")
                user_cols.add(column)
                reseal_all = True

        if role_created:
            # Every installation before 0.5.25 had exactly one effective administrator.
            conn.exec_driver_sql("UPDATE users SET role='admin'")
        conn.exec_driver_sql("UPDATE users SET active=1 WHERE active IS NULL")
        conn.exec_driver_sql("UPDATE users SET auth_provider='local' WHERE auth_provider IS NULL OR trim(auth_provider)='' ")
        if preference_language_created:
            conn.exec_driver_sql("UPDATE users SET preferred_language=COALESCE((SELECT value FROM settings WHERE key='language'), 'de')")
        else:
            conn.exec_driver_sql("UPDATE users SET preferred_language='de' WHERE preferred_language IS NULL OR trim(preferred_language)='' ")
        if preference_theme_created:
            conn.exec_driver_sql("UPDATE users SET preferred_theme=COALESCE((SELECT value FROM settings WHERE key='theme_mode'), 'light')")
        else:
            conn.exec_driver_sql("UPDATE users SET preferred_theme='light' WHERE preferred_theme IS NULL OR trim(preferred_theme)='' ")
        conn.exec_driver_sql("UPDATE users SET preferred_language='de' WHERE preferred_language NOT IN ('de','en')")
        conn.exec_driver_sql("UPDATE users SET preferred_theme='light' WHERE preferred_theme NOT IN ('light','dark')")
        conn.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS uq_users_oidc_identity ON users(oidc_issuer, oidc_subject) WHERE oidc_subject IS NOT NULL")
        conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_user_groups_user_id ON user_groups(user_id)")
        conn.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_user_groups_group_id ON user_groups(group_id)")
        conn.exec_driver_sql("UPDATE users SET session_version=1 WHERE session_version IS NULL OR session_version < 1")

        signature_version = int(current_app.config.get("SECURITY_SIGNATURE_VERSION", 2))
        row = conn.exec_driver_sql("SELECT value FROM settings WHERE key='security_signature_version'").fetchone()
        stored_signature_version = int(row[0]) if row and str(row[0]).isdigit() else 0
        if stored_signature_version < signature_version:
            reseal_all = True
            conn.exec_driver_sql(
                "INSERT INTO settings(key, value, updated_at) VALUES('security_signature_version', ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP",
                (str(signature_version),),
            )

        valid_icons = [value for value, _label in GROUP_ICON_CHOICES]
        icon_cleanup = text(
            "UPDATE groups SET icon='collection' WHERE icon IS NULL OR icon NOT IN :valid_icons"
        ).bindparams(bindparam("valid_icons", expanding=True))
        conn.execute(icon_cleanup, {"valid_icons": valid_icons})

        current_app.config["_SECURITY_SIGNATURE_INITIALIZE_MISSING"] = security_signature_created
        current_app.config["_SECURITY_SIGNATURE_RESEAL_ALL"] = reseal_all

        # Clean legacy placeholder values that older templates could save when optional
        # device fields were rendered as Python None.
        legacy_cleanup_queries = (
            "UPDATE devices SET customer=NULL WHERE lower(trim(COALESCE(customer, ''))) IN ('none', 'null')",
            "UPDATE devices SET location=NULL WHERE lower(trim(COALESCE(location, ''))) IN ('none', 'null')",
            "UPDATE devices SET tags=NULL WHERE lower(trim(COALESCE(tags, ''))) IN ('none', 'null')",
            "UPDATE devices SET notes=NULL WHERE lower(trim(COALESCE(notes, ''))) IN ('none', 'null')",
        )
        for cleanup_query in legacy_cleanup_queries:
            conn.exec_driver_sql(cleanup_query)


def admin_required(view):
    """Require an authenticated administrator and enforce it server-side."""
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not getattr(current_user, "is_admin", False):
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def _visible_group_ids() -> list[int]:
    if not current_user.is_authenticated or getattr(current_user, "is_admin", False):
        return []
    return [group.id for group in current_user.groups]


def _visible_device_query():
    if getattr(current_user, "is_admin", False):
        return Device.query
    group_ids = _visible_group_ids()
    if not group_ids:
        return Device.query.filter(false())
    return Device.query.filter(Device.group_id.in_(group_ids))


def _visible_groups() -> list[Group]:
    if getattr(current_user, "is_admin", False):
        return Group.query.order_by(Group.name.asc()).all()
    return sorted(current_user.groups, key=lambda group: group.name.casefold())


def _accessible_device_or_404(device_id: int) -> Device:
    return _visible_device_query().filter(Device.id == device_id).first_or_404()


def _active_local_admin_count(*, exclude_user_id: int | None = None) -> int:
    query = User.query.filter_by(role="admin", active=True, auth_provider="local")
    if exclude_user_id is not None:
        query = query.filter(User.id != exclude_user_id)
    return query.count()


def _normalize_role(value: str | None) -> str:
    return "admin" if str(value or "").strip().lower() == "admin" else "user"


def _normalize_auth_provider(value: str | None) -> str:
    return "oidc" if str(value or "").strip().lower() == "oidc" else "local"

def _valid_username(value: str) -> bool:
    return bool(3 <= len(value) <= 80 and re.fullmatch(r"[A-Za-z0-9._@-]+", value))


def _groups_from_form(field_name: str = "group_ids") -> list[Group]:
    ids = {int(value) for value in request.form.getlist(field_name) if str(value).isdigit()}
    if not ids:
        return []
    return Group.query.filter(Group.id.in_(ids)).order_by(Group.name.asc()).all()


def _safe_next_url(value: str | None, default_endpoint: str = "dashboard") -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return url_for(default_endpoint)
    parsed = urllib.parse.urlparse(candidate)
    if parsed.scheme or parsed.netloc or not candidate.startswith("/") or candidate.startswith("//"):
        return url_for(default_endpoint)
    return candidate


def _legacy_security_signature_payload_v1(user: User) -> str:
    """Return the exact signed payload used by 0.5.25/0.5.26.

    During the one-time migration to signature version 2, an existing signature
    must validate against this payload before it is upgraded. This prevents a
    database modification made before the upgrade from being silently trusted.
    """
    data = {
        "username": user.username or "",
        "password_hash": user.password_hash or "",
        "role": user.role or "user",
        "active": bool(user.active),
        "auth_provider": user.auth_provider or "local",
        "oidc_issuer": user.oidc_issuer or "",
        "oidc_subject": user.oidc_subject or "",
        "display_name": user.display_name or "",
        "email": user.email or "",
        "totp_secret_encrypted": user.totp_secret_encrypted or "",
        "totp_enabled": bool(user.totp_enabled),
        "totp_recovery_hashes": user.totp_recovery_hashes or "",
    }
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _security_signature_payload(user: User) -> str:
    group_ids = sorted(int(group.id) for group in getattr(user, "groups", []) if getattr(group, "id", None) is not None)
    data = {
        "signature_version": int(current_app.config.get("SECURITY_SIGNATURE_VERSION", 2)),
        "username": user.username or "",
        "password_hash": user.password_hash or "",
        "role": user.role or "user",
        "active": bool(user.active),
        "auth_provider": user.auth_provider or "local",
        "oidc_issuer": user.oidc_issuer or "",
        "oidc_subject": user.oidc_subject or "",
        "display_name": user.display_name or "",
        "email": user.email or "",
        "totp_secret_encrypted": user.totp_secret_encrypted or "",
        "totp_enabled": bool(user.totp_enabled),
        "totp_recovery_hashes": user.totp_recovery_hashes or "",
        "session_version": int(getattr(user, "session_version", 1) or 1),
        "group_ids": group_ids,
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


def _verify_legacy_user_security_state_v1(user: User) -> bool:
    stored = getattr(user, "security_signature", None) or ""
    if not stored:
        return False
    expected = _security_hmac(_legacy_security_signature_payload_v1(user))
    return hmac.compare_digest(stored, expected)


def _user_signature_policy() -> str:
    return "strict"


def _reseal_user_after_verified_auth(user: User, *, username: str, reason: str) -> None:
    _sign_user_security_state(user)
    db.session.commit()
    _record_auth_event("security_resealed", username=username, success=True, message=reason)


def _ensure_user_security_signatures() -> None:
    initialize_missing = bool(current_app.config.get("_SECURITY_SIGNATURE_INITIALIZE_MISSING"))
    reseal_all = bool(current_app.config.get("_SECURITY_SIGNATURE_RESEAL_ALL"))
    if not initialize_missing and not reseal_all:
        return

    changed = False
    rejected_users: list[str] = []
    for user in User.query.all():
        stored = getattr(user, "security_signature", None) or ""
        if not stored:
            # Only databases that did not have a signature column at all are
            # initialized automatically. A missing signature in an already
            # protected database remains invalid and cannot be legitimized.
            if initialize_missing:
                _sign_user_security_state(user)
                changed = True
            else:
                rejected_users.append(user.username)
            continue

        if not reseal_all or _verify_user_security_state(user):
            continue

        # Upgrade an old signature only after the exact 0.5.25/0.5.26 payload
        # has validated. Invalid legacy signatures remain invalid, so login is
        # blocked instead of silently accepting a modified role or identity.
        if _verify_legacy_user_security_state_v1(user):
            _sign_user_security_state(user)
            changed = True
        else:
            rejected_users.append(user.username)

    if changed:
        db.session.commit()
    if rejected_users:
        current_app.logger.error(
            "Sicherheitsmigration hat ungültige Benutzersignaturen nicht übernommen: %s",
            ", ".join(sorted(set(rejected_users))),
        )


def _bump_user_session_version(user: User) -> None:
    user.session_version = int(getattr(user, "session_version", 1) or 1) + 1


def _start_user_session(user: User) -> None:
    login_user(user)
    session["auth_session_version"] = int(getattr(user, "session_version", 1) or 1)
    session["auth_time"] = int(time.time())


def _has_recent_auth() -> bool:
    auth_time = session.get("auth_time")
    try:
        age = int(time.time()) - int(auth_time)
    except (TypeError, ValueError):
        return False
    return 0 <= age <= int(current_app.config.get("SENSITIVE_ACTION_REAUTH_SECONDS", 1800))


def _commit_user_security_change(user: User, *, keep_current_session: bool = False) -> None:
    """Persist a security-sensitive user change and revoke older sessions."""
    _bump_user_session_version(user)
    _sign_user_security_state(user)
    db.session.commit()
    if keep_current_session and current_user.is_authenticated and current_user.id == user.id:
        session["auth_session_version"] = int(user.session_version)
        session["auth_time"] = int(time.time())


def _store_transient_secret(user: User, purpose: str, payload, *, ttl_seconds: int = 600) -> str:
    token = secrets.token_urlsafe(48)
    expires_at = utcnow() + timedelta(seconds=max(60, min(int(ttl_seconds), 3600)))
    encrypted_payload = encrypt_value(json.dumps(payload, ensure_ascii=False))
    db.session.add(TransientSecret(
        token=token,
        user_id=user.id,
        purpose=purpose[:64],
        encrypted_payload=encrypted_payload,
        expires_at=expires_at,
    ))
    db.session.commit()
    return token


def _pop_transient_secret(user: User, token: str | None, purpose: str):
    if not token:
        return None
    entry = TransientSecret.query.filter_by(token=token, user_id=user.id, purpose=purpose[:64]).first()
    if entry is None:
        return None
    try:
        db.session.delete(entry)
        db.session.commit()
        if entry.expires_at < utcnow():
            return None
        return json.loads(decrypt_value(entry.encrypted_payload))
    except Exception:
        db.session.rollback()
        return None


def _queue_recovery_codes(user: User, recovery_codes: list[str]) -> None:
    old_token = session.pop("new_recovery_token", None)
    if old_token:
        old = TransientSecret.query.filter_by(token=old_token, user_id=user.id, purpose="recovery_codes").first()
        if old is not None:
            db.session.delete(old)
            db.session.commit()
    session["new_recovery_token"] = _store_transient_secret(user, "recovery_codes", recovery_codes, ttl_seconds=600)


def _consume_recovery_codes(user: User):
    return _pop_transient_secret(user, session.pop("new_recovery_token", None), "recovery_codes")


def _client_ip() -> str:
    if current_app.config.get("TRUST_PROXY_HEADERS"):
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()[:64]
        real_ip = request.headers.get("X-Real-IP", "")
        if real_ip:
            return real_ip.strip()[:64]
    return (request.remote_addr or "unknown")[:64]


def _prune_auth_events_if_needed() -> None:
    now_ts = time.monotonic()
    last = float(current_app.extensions.get("rab_auth_prune_at", 0.0) or 0.0)
    if now_ts - last < 300:
        return
    current_app.extensions["rab_auth_prune_at"] = now_ts
    retention_days = max(1, int(current_app.config.get("AUTH_EVENT_RETENTION_DAYS", 90)))
    max_rows = max(1000, int(current_app.config.get("AUTH_EVENT_MAX_ROWS", 50000)))
    cutoff = utcnow() - timedelta(days=retention_days)
    AuthEvent.query.filter(AuthEvent.created_at < cutoff).delete(synchronize_session=False)
    count = AuthEvent.query.count()
    excess = count - max_rows
    if excess > 0:
        oldest_ids = [row.id for row in AuthEvent.query.with_entities(AuthEvent.id).order_by(AuthEvent.id.asc()).limit(excess).all()]
        if oldest_ids:
            AuthEvent.query.filter(AuthEvent.id.in_(oldest_ids)).delete(synchronize_session=False)
    TransientSecret.query.filter(TransientSecret.expires_at < utcnow()).delete(synchronize_session=False)
    db.session.commit()


def _record_auth_event(event_type: str, *, username: str = "", success: bool = False, message: str = "") -> None:
    username = (username or "").strip()[:120]
    ip = _client_ip()
    user_agent = (request.headers.get("User-Agent", "") or "")[:255]
    message = (message or "")[:1000]
    try:
        _prune_auth_events_if_needed()
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


def _rotate_auth_log_if_needed(auth_log: Path) -> None:
    """Rotate auth.log at most once per ISO week.

    This is intentionally app-level and simple so it works inside the container
    without a host logrotate dependency. Rotated files are kept in the same
    directory as auth.log and fail2ban/CrowdSec can continue watching auth.log.
    """
    try:
        rotate_days = int(current_app.config.get("AUTH_LOG_ROTATE_DAYS", 7) or 7)
        keep = int(current_app.config.get("AUTH_LOG_ROTATE_KEEP", 8) or 8)
    except Exception:
        rotate_days, keep = 7, 8
    if rotate_days <= 0:
        return

    try:
        auth_log.parent.mkdir(parents=True, exist_ok=True)
        state_file = auth_log.with_name(auth_log.name + ".rotation")
        today = utcnow().date()
        # Weekly default: using ISO weeks avoids mtime problems when the log is
        # written every day. For custom values, use a date bucket.
        if rotate_days == 7:
            iso = today.isocalendar()
            bucket = f"{iso.year}-W{iso.week:02d}"
        else:
            ordinal_bucket = today.toordinal() // max(rotate_days, 1)
            bucket = f"d{rotate_days}-{ordinal_bucket}"

        previous = state_file.read_text(encoding="utf-8").strip() if state_file.exists() else ""
        if not previous:
            state_file.write_text(bucket, encoding="utf-8")
            return
        if previous == bucket:
            return
        if auth_log.exists() and auth_log.stat().st_size > 0:
            suffix = previous.replace("/", "-").replace(" ", "_")
            rotated = auth_log.with_name(f"{auth_log.name}.{suffix}")
            counter = 1
            while rotated.exists():
                rotated = auth_log.with_name(f"{auth_log.name}.{suffix}.{counter}")
                counter += 1
            auth_log.replace(rotated)
            try:
                rotated.chmod(0o600)
            except PermissionError:
                pass
        state_file.write_text(bucket, encoding="utf-8")

        rotated_files = sorted(
            [p for p in auth_log.parent.glob(auth_log.name + ".*") if p.name != state_file.name and not p.name.endswith(".rotation")],
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )
        for old in rotated_files[max(keep, 0):]:
            try:
                old.unlink()
            except OSError:
                pass
    except OSError:
        pass


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
        _rotate_auth_log_if_needed(auth_log)
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
    # A username-wide hard lock lets an unauthenticated attacker deny access to
    # a known account. Enforce the blocking threshold per source IP instead.
    if ip_count >= limit:
        oldest = base.filter(AuthEvent.ip_address == ip).order_by(AuthEvent.created_at.asc()).first()
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
    app.jinja_env.globals["group_icon_choices"] = _translated_group_icon_choices
    app.jinja_env.globals["safe_group_icon"] = _safe_group_icon
    app.jinja_env.globals["group_color_choices"] = _translated_group_color_choices
    app.jinja_env.globals["theme_choices"] = THEME_CHOICES
    app.jinja_env.globals["csp_nonce"] = lambda: getattr(g, "csp_nonce", "")
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
    app.jinja_env.globals["get_oidc_settings"] = _get_oidc_settings

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
            "oidc_settings": _get_oidc_settings(),
            "is_admin": bool(current_user.is_authenticated and getattr(current_user, "is_admin", False)),
            "group_icon_choices": _translated_group_icon_choices(),
            "group_color_choices": _translated_group_color_choices(),
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
        g.csp_nonce = secrets.token_urlsafe(24)
        validate_csrf()
        if request.endpoint in {"static", "setup", "healthz"}:
            return None
        has_user = db.session.query(User.id).first() is not None
        if not has_user:
            return redirect(url_for("setup"))
        if current_user.is_authenticated and not getattr(current_user, "active", True):
            username = getattr(current_user, "username", "")
            _record_auth_event("disabled_session", username=username, success=False, message="Aktive Sitzung eines deaktivierten Benutzers beendet")
            logout_user()
            session.clear()
            flash("Dieses Benutzerkonto wurde deaktiviert.", "warning")
            return redirect(url_for("login"))
        if current_user.is_authenticated and not _verify_user_security_state(current_user):
            username = getattr(current_user, "username", "")
            _record_auth_event("security_signature_invalid_session", username=username, success=False, message="Aktive Sitzung beendet: Benutzer-Sicherheitsdatenbank-Signatur ungültig")
            logout_user()
            session.clear()
            flash("Sitzung wurde aus Sicherheitsgründen beendet. Bitte melde dich erneut an.", "warning")
            return redirect(url_for("login"))
        if current_user.is_authenticated:
            expected = int(getattr(current_user, "session_version", 1) or 1)
            try:
                actual = int(session.get("auth_session_version", -1))
            except (TypeError, ValueError):
                actual = -1
            if actual != expected:
                username = getattr(current_user, "username", "")
                _record_auth_event("session_revoked", username=username, success=False, message="Sitzung wegen geänderter Sicherheits- oder Kontodaten widerrufen")
                logout_user()
                session.clear()
                flash("Deine Sitzung wurde widerrufen. Bitte melde dich erneut an.", "warning")
                return redirect(url_for("login"))
        return None

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        nonce = getattr(g, "csp_nonce", "")
        response.headers.setdefault("Content-Security-Policy", f"default-src 'self'; script-src 'self' 'nonce-{nonce}'; style-src 'self' 'unsafe-inline'; font-src 'self' data:; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-src 'none'; frame-ancestors 'self'; base-uri 'self'; form-action 'self'; upgrade-insecure-requests")
        if current_app.config.get("APP_HSTS") and request.is_secure:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


def register_routes(app: Flask) -> None:
    @app.route("/healthz")
    def healthz():
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify(status="ok")
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Healthcheck-Datenbankprüfung fehlgeschlagen")
            return jsonify(status="error"), 503

    @app.route("/setup", methods=["GET", "POST"])
    def setup():
        if db.session.query(User.id).first() is not None:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            password2 = request.form.get("password2", "")
            setup_token = request.form.get("setup_token", "")

            if not secrets.compare_digest(setup_token, str(current_app.config.get("SETUP_TOKEN", ""))):
                _record_auth_event("setup_token_fail", username=username, success=False, message="Ungültiges Setup-Token")
                flash("Das Setup-Token ist ungültig. Lies es auf dem Server aus data/config.json oder über docker exec.", "danger")
            elif not username:
                flash("Benutzername fehlt.", "danger")
            elif len(password) < 8:
                flash("Das Passwort muss mindestens 8 Zeichen haben.", "danger")
            elif password != password2:
                flash("Die Passwörter stimmen nicht überein.", "danger")
            else:
                user = User(username=username, role="admin", active=True, auth_provider="local")
                user.set_password(password)
                _sign_user_security_state(user)
                db.session.add(user)
                db.session.commit()
                _record_auth_event("setup_login", username=username, success=True, message="Installation abgeschlossen und Admin angemeldet")
                _start_user_session(user)
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

            if user and not user.active:
                _record_auth_event("login_disabled", username=username, success=False, message="Deaktiviertes Benutzerkonto")
                flash("Dieses Benutzerkonto ist deaktiviert.", "danger")
                return render_template("login.html")

            if user and user.check_password(password):
                next_url = _safe_next_url(request.args.get("next"))
                if not signature_ok:
                    _record_auth_event("security_signature_invalid", username=username, success=False, message="Benutzer-Sicherheitsdatenbank-Signatur ungültig; Login blockiert")
                    flash("Anmeldung blockiert: Die Sicherheitsdaten dieses Kontos wurden verändert. Stelle eine vertrauenswürdige Sicherung wieder her oder verwende ein anderes Administratorkonto.", "danger")
                    return render_template("login.html")

                if getattr(user, "totp_enabled", False):
                    _record_auth_event("password_ok_2fa_required", username=username, success=True, message="Passwort korrekt; 2FA erforderlich")
                    session["pending_2fa_user_id"] = user.id
                    session["pending_2fa_next"] = next_url or url_for("dashboard")
                    return redirect(url_for("login_2fa"))

                user.last_login_at = utcnow()
                _sign_user_security_state(user)
                db.session.commit()
                flash("Angemeldet.", "success")
                _record_auth_event("login_success", username=username, success=True, message="Login ohne 2FA erfolgreich")
                _start_user_session(user)
                return redirect(next_url)
            _record_auth_event("password_fail", username=username, success=False, message="Ungültiger Benutzername oder Passwort")
            time.sleep(0.2)
            flash("Benutzername oder Passwort ist falsch.", "danger")

        return render_template("login.html")

    @app.route("/reauth", methods=["GET", "POST"])
    @login_required
    def reauth():
        next_url = _safe_next_url(request.values.get("next")) or url_for("dashboard")
        if request.method == "POST":
            if current_user.auth_provider == "oidc":
                username = current_user.username
                logout_user()
                session.pop("auth_session_version", None)
                session.pop("auth_time", None)
                session["oidc_next"] = next_url
                session["oidc_force_reauth"] = True
                _record_auth_event("reauth_oidc_start", username=username, success=True, message="Erneute OIDC-Authentifizierung gestartet")
                return redirect(url_for("oidc_login", next=next_url, reauth="1"))

            password = request.form.get("current_password", "")
            second_factor = request.form.get("totp_code", "")
            if not current_user.check_password(password):
                _record_auth_event("reauth_fail", username=current_user.username, success=False, message="Passwort für erneute Authentifizierung falsch")
                time.sleep(0.2)
                flash("Aktuelles Passwort ist falsch.", "danger")
            elif current_user.totp_enabled and not _verify_second_factor_for_user(current_user, second_factor, consume_recovery=False)[0]:
                _record_auth_event("reauth_fail", username=current_user.username, success=False, message="Zweiter Faktor für erneute Authentifizierung falsch")
                time.sleep(0.2)
                flash("2FA-Code ist ungültig oder abgelaufen.", "danger")
            else:
                session["auth_time"] = int(time.time())
                _record_auth_event("reauth_success", username=current_user.username, success=True, message="Erneute Authentifizierung erfolgreich")
                return redirect(next_url)
        response = render_template("reauth.html", next_url=next_url)
        return response

    @app.route("/login/oidc")
    def oidc_login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        settings = _get_oidc_settings()
        if not settings["enabled"] or not settings["configured"]:
            flash("OIDC-Anmeldung ist nicht verfügbar.", "danger")
            return redirect(url_for("login"))
        try:
            client = _configure_oidc_client()
            session["oidc_next"] = _safe_next_url(request.args.get("next")) or session.get("oidc_next")
            force_reauth = request.args.get("reauth") == "1" or bool(session.pop("oidc_force_reauth", False))
            redirect_uri = url_for("oidc_callback", _external=True)
            if force_reauth:
                return client.authorize_redirect(redirect_uri, prompt="login", max_age=0)
            return client.authorize_redirect(redirect_uri)
        except Exception as exc:
            _record_auth_event("oidc_start_fail", success=False, message=f"OIDC-Anmeldung konnte nicht gestartet werden: {exc}")
            flash("OIDC-Anmeldung konnte nicht gestartet werden. Bitte Konfiguration und Provider-Erreichbarkeit prüfen.", "danger")
            return redirect(url_for("login"))

    @app.route("/login/oidc/callback")
    def oidc_callback():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        settings = _get_oidc_settings()
        try:
            client = _configure_oidc_client()
            token = client.authorize_access_token()
            userinfo = token.get("userinfo") or {}
            subject = str(userinfo.get("sub") or "").strip()
            if not subject:
                raise ValueError("OIDC-Antwort enthält keinen sub-Claim.")
            issuer = _validate_oidc_issuer_url(settings["issuer_url"], allow_insecure=settings["allow_insecure"])
            email = str(userinfo.get("email") or "").strip()[:255]
            if settings.get("allowed_domains") and userinfo.get("email_verified") is not True:
                raise PermissionError("Für die Domainfreigabe ist ein vom OIDC-Provider bestätigter email_verified-Claim erforderlich.")
            if not _oidc_email_allowed(email, settings):
                raise PermissionError("Die E-Mail-Domain ist für diese Anwendung nicht freigegeben.")

            user = User.query.filter_by(oidc_issuer=issuer, oidc_subject=subject).first()
            claimed_username = _oidc_claim_username(userinfo, settings)
            if user is None:
                if settings["auto_provision"]:
                    user = User(
                        username=_unique_username(claimed_username),
                        password_hash="",
                        role="user",
                        active=True,
                        auth_provider="oidc",
                        oidc_issuer=issuer,
                        oidc_subject=subject,
                        session_version=1,
                    )
                    db.session.add(user)
                else:
                    raise PermissionError("Für diese Kombination aus OIDC-Issuer und Subject wurde noch kein Benutzer angelegt.")
            elif not _verify_user_security_state(user):
                raise PermissionError("Die Benutzer-Sicherheitsdaten haben keine gültige Signatur.")

            if user.auth_provider != "oidc":
                raise PermissionError("Der Benutzername ist bereits einem lokalen Konto zugeordnet.")
            if not user.active:
                raise PermissionError("Dieses Benutzerkonto ist deaktiviert.")

            user.display_name = str(userinfo.get("name") or userinfo.get("preferred_username") or "").strip()[:180] or None
            user.email = email or None
            user.last_login_at = utcnow()
            _sign_user_security_state(user)
            db.session.commit()
            _start_user_session(user)
            next_url = session.pop("oidc_next", None) or url_for("dashboard")
            _record_auth_event("oidc_login_success", username=user.username, success=True, message=f"OIDC-Anmeldung über {settings['provider_name']} erfolgreich")
            flash("Über OpenID Connect angemeldet.", "success")
            return redirect(_safe_next_url(next_url))
        except PermissionError as exc:
            db.session.rollback()
            _record_auth_event("oidc_login_denied", success=False, message=str(exc))
            flash(str(exc), "danger")
        except Exception as exc:
            db.session.rollback()
            _record_auth_event("oidc_login_fail", success=False, message=f"OIDC-Callback fehlgeschlagen: {exc}")
            flash("OIDC-Anmeldung ist fehlgeschlagen. Bitte Provider- und Client-Konfiguration prüfen.", "danger")
        return redirect(url_for("login"))

    @app.route("/login/2fa", methods=["GET", "POST"])
    def login_2fa():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        user_id = session.get("pending_2fa_user_id")
        user = db.session.get(User, int(user_id)) if str(user_id).isdigit() else None
        if not user or not getattr(user, "active", True) or not getattr(user, "totp_enabled", False):
            session.pop("pending_2fa_user_id", None)
            session.pop("pending_2fa_next", None)
            flash("Bitte erneut anmelden.", "warning")
            return redirect(url_for("login"))
        signature_ok = _verify_user_security_state(user)
        if not signature_ok:
            _record_auth_event("security_signature_invalid", username=getattr(user, "username", ""), success=False, message="2FA-Anmeldung blockiert: Benutzer-Sicherheitsdatenbank-Signatur ungültig")
            session.pop("pending_2fa_user_id", None)
            session.pop("pending_2fa_next", None)
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
                _sign_user_security_state(user)
                db.session.commit()
                _record_auth_event("login_success_2fa", username=user.username, success=True, message=("Login mit Wiederherstellungscode" if method == "recovery" else "Login mit TOTP"))
                _start_user_session(user)
                next_url = session.pop("pending_2fa_next", None) or url_for("dashboard")
                session.pop("pending_2fa_user_id", None)
                if method == "recovery":
                    remaining = _recovery_code_count(user)
                    flash(f"Angemeldet. Ein Wiederherstellungscode wurde verbraucht. Verbleibend: {remaining}.", "warning")
                else:
                    flash("Angemeldet.", "success")
                return redirect(next_url)
            _record_auth_event("2fa_fail", username=user.username, success=False, message="Ungültiger 2FA- oder Wiederherstellungscode")
            time.sleep(0.2)
            flash("2FA-Code oder Wiederherstellungscode ist ungültig.", "danger")

        return render_template("login_2fa.html")

    @app.route("/logout", methods=["POST"])
    @login_required
    def logout():
        username = current_user.username if current_user.is_authenticated else ""
        _record_auth_event("logout", username=username, success=True, message="Benutzer abgemeldet")
        logout_user()
        session.clear()
        flash("Abgemeldet.", "info")
        return redirect(url_for("login"))

    @app.route("/users", methods=["GET", "POST"])
    @admin_required
    def users():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            provider = _normalize_auth_provider(request.form.get("auth_provider"))
            role = _normalize_role(request.form.get("role"))
            active = normalize_bool(request.form.get("active"))
            password = request.form.get("password", "")
            password2 = request.form.get("password2", "")
            oidc_issuer = request.form.get("oidc_issuer", "").strip()
            oidc_subject = request.form.get("oidc_subject", "").strip()[:255]
            if provider == "oidc" and oidc_issuer:
                try:
                    oidc_issuer = _validate_oidc_issuer_url(oidc_issuer, allow_insecure=_get_oidc_settings()["allow_insecure"])
                except ValueError as exc:
                    flash(str(exc), "danger")
                    return redirect(url_for("users"))

            if not _valid_username(username):
                flash("Benutzername muss 3 bis 80 Zeichen lang sein und darf nur Buchstaben, Zahlen, Punkt, Unterstrich, Bindestrich und @ enthalten.", "danger")
            elif User.query.filter_by(username=username).first():
                flash("Dieser Benutzername existiert bereits.", "warning")
            elif provider == "local" and len(password) < 8:
                flash("Lokale Benutzer benötigen ein Passwort mit mindestens 8 Zeichen.", "danger")
            elif provider == "local" and password != password2:
                flash("Die Passwörter stimmen nicht überein.", "danger")
            elif provider == "oidc" and (not oidc_issuer or not oidc_subject):
                flash("OIDC-Benutzer müssen mit der eindeutigen Kombination aus Issuer und Subject angelegt werden.", "danger")
            elif provider == "oidc" and User.query.filter_by(oidc_issuer=oidc_issuer, oidc_subject=oidc_subject).first():
                flash("Diese OIDC-Identität ist bereits einem Benutzer zugeordnet.", "warning")
            else:
                user = User(
                    username=username,
                    role=role,
                    active=active,
                    auth_provider=provider,
                    password_hash="",
                    oidc_issuer=oidc_issuer if provider == "oidc" else None,
                    oidc_subject=oidc_subject if provider == "oidc" else None,
                    session_version=1,
                )
                if provider == "local":
                    user.set_password(password)
                user.groups = _groups_from_form()
                _sign_user_security_state(user)
                db.session.add(user)
                db.session.commit()
                _record_auth_event("user_created", username=current_user.username, success=True, message=f"Benutzer {username} angelegt; Rolle={role}; Provider={provider}")
                flash("Benutzer wurde angelegt.", "success")
                return redirect(url_for("users"))

        return render_template(
            "users.html",
            users=User.query.order_by(User.username.asc()).all(),
            groups=Group.query.order_by(Group.name.asc()).all(),
            local_admin_count=_active_local_admin_count(),
        )

    @app.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
    @admin_required
    def user_edit(user_id: int):
        user = db.session.get(User, user_id) or abort(404)
        all_groups = Group.query.order_by(Group.name.asc()).all()
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            provider = _normalize_auth_provider(request.form.get("auth_provider"))
            role = _normalize_role(request.form.get("role"))
            active = normalize_bool(request.form.get("active"))
            new_password = request.form.get("new_password", "")
            password2 = request.form.get("new_password2", "")
            oidc_issuer = request.form.get("oidc_issuer", "").strip()
            oidc_subject = request.form.get("oidc_subject", "").strip()[:255]
            if provider == "oidc" and oidc_issuer:
                try:
                    oidc_issuer = _validate_oidc_issuer_url(oidc_issuer, allow_insecure=_get_oidc_settings()["allow_insecure"])
                except ValueError as exc:
                    flash(str(exc), "danger")
                    return redirect(url_for("user_edit", user_id=user.id))

            duplicate = User.query.filter(User.username == username, User.id != user.id).first()
            duplicate_oidc = User.query.filter(User.oidc_issuer == oidc_issuer, User.oidc_subject == oidc_subject, User.id != user.id).first() if provider == "oidc" and oidc_issuer and oidc_subject else None
            removes_local_admin = user.role == "admin" and user.active and user.auth_provider == "local" and not (role == "admin" and active and provider == "local")

            if not _valid_username(username):
                flash("Benutzername ist ungültig.", "danger")
            elif duplicate:
                flash("Dieser Benutzername existiert bereits.", "warning")
            elif user.id == current_user.id and (not active or role != "admin"):
                flash("Das aktuell verwendete Administratorkonto kann sich nicht selbst deaktivieren oder herabstufen.", "danger")
            elif removes_local_admin and _active_local_admin_count(exclude_user_id=user.id) == 0:
                flash("Der letzte aktive lokale Administrator kann nicht deaktiviert, gelöscht, herabgestuft oder auf OIDC umgestellt werden.", "danger")
            elif new_password and len(new_password) < 8:
                flash("Das neue Passwort muss mindestens 8 Zeichen haben.", "danger")
            elif new_password and new_password != password2:
                flash("Die neuen Passwörter stimmen nicht überein.", "danger")
            elif provider == "local" and user.auth_provider != "local" and not new_password:
                flash("Beim Wechsel auf lokale Anmeldung muss ein neues Passwort gesetzt werden.", "danger")
            elif provider == "oidc" and (not oidc_issuer or not oidc_subject):
                flash("OIDC-Benutzer benötigen eine eindeutige Issuer-/Subject-Zuordnung.", "danger")
            elif duplicate_oidc:
                flash("Diese OIDC-Identität ist bereits einem anderen Benutzer zugeordnet.", "warning")
            else:
                provider_changed = provider != user.auth_provider
                user.username = username
                user.role = role
                user.active = active
                user.auth_provider = provider
                user.groups = _groups_from_form()
                if provider_changed:
                    user.display_name = None
                    user.email = None
                    user.totp_enabled = False
                    user.totp_secret_encrypted = None
                    user.totp_recovery_hashes = None
                    if provider == "oidc":
                        user.password_hash = ""
                if provider == "oidc":
                    user.oidc_issuer = oidc_issuer
                    user.oidc_subject = oidc_subject
                else:
                    user.oidc_issuer = None
                    user.oidc_subject = None
                if new_password:
                    user.set_password(new_password)
                _bump_user_session_version(user)
                _sign_user_security_state(user)
                db.session.commit()
                _record_auth_event("user_updated", username=current_user.username, success=True, message=f"Benutzer {username} aktualisiert; Rolle={role}; Provider={provider}; aktiv={active}")
                flash("Benutzer wurde gespeichert.", "success")
                return redirect(url_for("users"))

        return render_template("user_form.html", user=user, groups=all_groups)

    @app.route("/users/<int:user_id>/delete", methods=["POST"])
    @admin_required
    def user_delete(user_id: int):
        user = db.session.get(User, user_id) or abort(404)
        if user.id == current_user.id:
            flash("Das aktuell verwendete Administratorkonto kann nicht gelöscht werden.", "danger")
        elif user.role == "admin" and user.active and user.auth_provider == "local" and _active_local_admin_count(exclude_user_id=user.id) == 0:
            flash("Der letzte aktive lokale Administrator kann nicht gelöscht werden.", "danger")
        else:
            username = user.username
            db.session.delete(user)
            db.session.commit()
            _record_auth_event("user_deleted", username=current_user.username, success=True, message=f"Benutzer {username} gelöscht")
            flash("Benutzer wurde gelöscht.", "info")
        return redirect(url_for("users"))

    @app.route("/settings/oidc", methods=["GET", "POST"])
    @admin_required
    def oidc_settings_page():
        if request.method == "POST":
            enabled = normalize_bool(request.form.get("oidc_enabled"))
            auto_provision = normalize_bool(request.form.get("oidc_auto_provision"))
            allow_insecure = normalize_bool(request.form.get("oidc_allow_insecure"))
            issuer = request.form.get("oidc_issuer_url", "").strip()
            client_id = request.form.get("oidc_client_id", "").strip()[:255]
            client_secret = request.form.get("oidc_client_secret", "")
            provider_name = request.form.get("oidc_provider_name", "OpenID Connect").strip()[:80] or "OpenID Connect"
            scopes = " ".join(dict.fromkeys((request.form.get("oidc_scopes", "openid profile email") or "openid profile email").split()))
            username_claim = request.form.get("oidc_username_claim", "preferred_username").strip()[:80] or "preferred_username"
            allowed_domains = ",".join(item.strip().lower() for item in request.form.get("oidc_allowed_domains", "").split(",") if item.strip())
            existing_secret = _get_setting("oidc_client_secret", "")

            try:
                normalized_issuer = _validate_oidc_issuer_url(issuer, allow_insecure=allow_insecure) if issuer else ""
                if enabled and (not normalized_issuer or not client_id or (not client_secret and not existing_secret)):
                    raise ValueError("Zum Aktivieren von OIDC werden Issuer-URL, Client-ID und Client-Secret benötigt.")
                if "openid" not in scopes.split():
                    scopes = "openid " + scopes
                values = {
                    "oidc_enabled": "true" if enabled else "false",
                    "oidc_auto_provision": "true" if auto_provision else "false",
                    "oidc_allow_insecure": "true" if allow_insecure else "false",
                    "oidc_issuer_url": normalized_issuer,
                    "oidc_client_id": client_id,
                    "oidc_provider_name": provider_name,
                    "oidc_scopes": scopes,
                    "oidc_username_claim": username_claim,
                    "oidc_allowed_domains": allowed_domains,
                }
                if client_secret:
                    values["oidc_client_secret"] = encrypt_value(client_secret)
                _set_settings_bulk(values)
                _record_auth_event("oidc_settings_changed", username=current_user.username, success=True, message=f"OIDC aktiviert={enabled}; Issuer={normalized_issuer}; Auto-Provisioning={auto_provision}")

                if request.form.get("action") == "test" and normalized_issuer:
                    try:
                        discovery_url = f"{normalized_issuer}/.well-known/openid-configuration"
                        req = urllib.request.Request(discovery_url, headers={"Accept": "application/json", "User-Agent": "RustDesk-AddressBook-OIDC-Test"})
                        # URL scheme and credentials are validated above.
                        with urllib.request.urlopen(req, timeout=10) as response:  # nosec B310
                            raw = response.read(1024 * 1024)
                        metadata = json.loads(raw.decode("utf-8"))
                        required = ["issuer", "authorization_endpoint", "token_endpoint", "jwks_uri"]
                        missing = [key for key in required if not metadata.get(key)]
                        if missing:
                            raise ValueError("OIDC-Discovery unvollständig: " + ", ".join(missing))
                        discovered_issuer = str(metadata.get("issuer") or "").rstrip("/")
                        if discovered_issuer != normalized_issuer:
                            raise ValueError("Der von Discovery gemeldete Issuer stimmt nicht mit der konfigurierten Issuer-URL überein.")
                    except Exception as exc:
                        flash(f"OIDC-Konfiguration wurde gespeichert, aber der Discovery-Test ist fehlgeschlagen: {exc}", "warning")
                    else:
                        flash("OIDC-Konfiguration gespeichert und Discovery erfolgreich geprüft.", "success")
                else:
                    flash("OIDC-Konfiguration wurde gespeichert.", "success")
                return redirect(url_for("oidc_settings_page"))
            except Exception as exc:
                db.session.rollback()
                flash(f"OIDC-Konfiguration konnte nicht gespeichert werden: {exc}", "danger")

        settings = _get_oidc_settings()
        return render_template(
            "oidc_settings.html",
            settings=settings,
            redirect_uri=url_for("oidc_callback", _external=True),
        )

    @app.route("/account", methods=["GET", "POST"])
    @login_required
    def account():
        if request.method == "POST":
            action = request.form.get("action", "")

            if action == "preferences":
                theme_mode = request.form.get("theme_mode", "light").strip().lower()
                language = request.form.get("language", "de").strip().lower()
                if theme_mode not in {"light", "dark"}:
                    flash(_t("account.preferences_invalid_theme", "Ungültiger Darstellungsmodus."), "danger")
                elif language not in {key for key, _label in LANGUAGE_CHOICES}:
                    flash(_t("account.preferences_invalid_language", "Ungültige Sprache."), "danger")
                else:
                    current_user.preferred_theme = theme_mode
                    current_user.preferred_language = language
                    db.session.commit()
                    flash(_t("account.preferences_saved", "Darstellung und Sprache wurden für dein Benutzerkonto gespeichert."), "success")
                return redirect(url_for("account"))

            if current_user.auth_provider != "local":
                flash("Passwort und Mehrfaktor-Authentifizierung werden für dieses Konto vom OIDC-Provider verwaltet.", "info")
                return redirect(url_for("account"))
            current_password = request.form.get("current_password", "")

            if action == "password":
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
                    _commit_user_security_change(current_user, keep_current_session=True)
                    _record_auth_event("password_changed", username=current_user.username, success=True, message="Eigenes Passwort geändert")
                    flash("Passwort wurde geändert.", "success")
                return redirect(url_for("account"))

            if action == "totp_prepare":
                if not current_user.check_password(current_password):
                    flash("Aktuelles Passwort ist falsch.", "danger")
                else:
                    current_user.totp_secret_encrypted = encrypt_value(pyotp.random_base32())
                    current_user.totp_enabled = False
                    current_user.totp_recovery_hashes = None
                    _commit_user_security_change(current_user, keep_current_session=True)
                    flash("Scanne den QR-Code und bestätige anschließend einen Code.", "success")
                return redirect(url_for("account"))

            if action == "totp_enable":
                code = request.form.get("totp_code", "")
                if not current_user.check_password(current_password):
                    flash("Aktuelles Passwort ist falsch.", "danger")
                elif not _verify_totp_for_user(current_user, code):
                    flash("2FA-Code ist ungültig oder abgelaufen.", "danger")
                else:
                    recovery_codes = _generate_recovery_codes()
                    _set_recovery_codes_for_user(current_user, recovery_codes)
                    current_user.totp_enabled = True
                    _commit_user_security_change(current_user, keep_current_session=True)
                    _queue_recovery_codes(current_user, recovery_codes)
                    _record_auth_event("2fa_enabled", username=current_user.username, success=True, message="2FA im Benutzerkonto aktiviert")
                    flash("2FA wurde aktiviert. Speichere die Wiederherstellungscodes sicher ab.", "success")
                return redirect(url_for("account"))

            if action == "totp_disable":
                code = request.form.get("totp_code", "")
                if not current_user.check_password(current_password):
                    flash("Aktuelles Passwort ist falsch.", "danger")
                else:
                    ok, _method = _verify_second_factor_for_user(current_user, code, consume_recovery=True)
                    if not ok:
                        flash("2FA-Code oder Wiederherstellungscode ist ungültig.", "danger")
                    else:
                        current_user.totp_enabled = False
                        current_user.totp_secret_encrypted = None
                        current_user.totp_recovery_hashes = None
                        _commit_user_security_change(current_user, keep_current_session=True)
                        _record_auth_event("2fa_disabled", username=current_user.username, success=True, message="2FA im Benutzerkonto deaktiviert")
                        flash("2FA wurde deaktiviert.", "info")
                return redirect(url_for("account"))

            if action == "totp_recovery_regenerate":
                code = request.form.get("totp_code", "")
                if not current_user.totp_enabled:
                    flash("2FA ist nicht aktiviert.", "danger")
                elif not current_user.check_password(current_password):
                    flash("Aktuelles Passwort ist falsch.", "danger")
                else:
                    ok, _method = _verify_second_factor_for_user(current_user, code, consume_recovery=True)
                    if not ok:
                        flash("2FA-Code oder Wiederherstellungscode ist ungültig.", "danger")
                    else:
                        recovery_codes = _generate_recovery_codes()
                        _set_recovery_codes_for_user(current_user, recovery_codes)
                        _commit_user_security_change(current_user, keep_current_session=True)
                        _queue_recovery_codes(current_user, recovery_codes)
                        flash("Neue Wiederherstellungscodes wurden erstellt.", "success")
                return redirect(url_for("account"))

            if action == "totp_cancel":
                if not current_user.totp_enabled:
                    current_user.totp_secret_encrypted = None
                    current_user.totp_recovery_hashes = None
                    _commit_user_security_change(current_user, keep_current_session=True)
                    flash("2FA-Einrichtung wurde verworfen.", "info")
                return redirect(url_for("account"))

            flash("Unbekannte Konto-Aktion.", "danger")
            return redirect(url_for("account"))

        return render_template(
            "account.html",
            totp_secret=_get_user_totp_secret(current_user) if current_user.auth_provider == "local" else "",
            totp_qr_data_uri=_totp_qr_data_uri(current_user) if current_user.auth_provider == "local" else "",
            recovery_code_count=_recovery_code_count(current_user),
            new_recovery_codes=_consume_recovery_codes(current_user),
        )

    @app.route("/")
    @login_required
    def dashboard():
        device_view = _resolve_device_view(request.args.get("view"))
        visible_devices = _visible_device_query()
        total_devices = visible_devices.count()
        favorite_devices = visible_devices.filter(Device.favorite.is_(True)).count()
        online_devices = visible_devices.filter(Device.online.is_(True)).count()
        groups = _visible_groups()
        favorites = visible_devices.filter(Device.favorite.is_(True)).order_by(Device.name.asc()).limit(8).all()
        recent = visible_devices.order_by(Device.updated_at.desc()).limit(8).all()
        return render_template(
            "dashboard.html",
            total_devices=total_devices,
            favorite_devices=favorite_devices,
            online_devices=online_devices,
            groups=groups,
            favorites=favorites,
            recent=recent,
            device_view=device_view,
        )

    @app.route("/devices")
    @login_required
    def devices():
        q = request.args.get("q", "").strip()
        group_id = request.args.get("group", "").strip()
        fav = request.args.get("fav", "").strip()
        os_filter = request.args.get("os", "").strip()
        sort = request.args.get("sort", "online").strip().lower()
        device_view = _resolve_device_view(request.args.get("view"))

        query = _visible_device_query()
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
        groups = _visible_groups()
        available_os = sorted({row[0] for row in _visible_device_query().with_entities(Device.os).filter(Device.os.isnot(None)).all() if row[0]})
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
            device_view=device_view,
        )

    @app.route("/devices/new", methods=["GET", "POST"])
    @admin_required
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
    @admin_required
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
    @admin_required
    def device_delete(device_id: int):
        device = db.session.get(Device, device_id) or abort(404)
        rustdesk_id = _normalize_import_block_id(device.rustdesk_id)
        if rustdesk_id:
            _add_import_blocklist_entry(
                rustdesk_id,
                device_name=device.name,
                reason="Beim Löschen aus dem Adressbuch automatisch gesperrt",
                created_by=current_user.username,
            )
        device_name = device.name
        db.session.delete(device)
        db.session.commit()
        _record_auth_event("device_deleted_blocked", username=current_user.username, success=True, message=f"Gerät {device_name} gelöscht; RustDesk-ID {rustdesk_id} für Importe gesperrt")
        flash(_t("devices.deleted_blocked", "Gerät wurde gelöscht und seine RustDesk-ID für zukünftige Importe gesperrt."), "info")
        return redirect(url_for("devices"))

    @app.route("/devices/<int:device_id>/connect")
    @login_required
    def device_connect(device_id: int):
        device = _accessible_device_or_404(device_id)
        if not _has_recent_auth():
            return redirect(url_for("reauth", next=request.path))
        _record_auth_event("device_connect", username=current_user.username, success=True, message=f"RustDesk-Verbindung für Gerät {device.name} ({device.rustdesk_id}) gestartet")
        response = redirect(rustdesk_link(device.rustdesk_id, decrypt_value(device.encrypted_password)))
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.route("/devices/<int:device_id>/password", methods=["POST"])
    @login_required
    def device_password(device_id: int):
        device = _accessible_device_or_404(device_id)
        if not _has_recent_auth():
            response = jsonify({"error": "reauth_required", "reauth_url": url_for("reauth", next=url_for("devices"))})
            response.status_code = 401
            response.headers["Cache-Control"] = "no-store"
            return response
        _record_auth_event("device_password_view", username=current_user.username, success=True, message=f"Gerätepasswort für {device.name} ({device.rustdesk_id}) abgerufen")
        response = jsonify({"password": decrypt_value(device.encrypted_password)})
        response.headers["Cache-Control"] = "no-store"
        return response


    @app.route("/devices/<int:device_id>/favorite", methods=["POST"])
    @admin_required
    def device_toggle_favorite(device_id: int):
        device = db.session.get(Device, device_id) or abort(404)
        device.favorite = not device.favorite
        db.session.commit()
        return redirect(request.referrer or url_for("devices"))

    @app.route("/devices/<int:device_id>/online", methods=["POST"])
    @admin_required
    def device_toggle_online(device_id: int):
        device = db.session.get(Device, device_id) or abort(404)
        device.online = not device.online
        db.session.commit()
        return redirect(request.referrer or url_for("devices"))

    @app.route("/groups", methods=["GET", "POST"])
    @admin_required
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
    @admin_required
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
    @admin_required
    def group_delete(group_id: int):
        group = db.session.get(Group, group_id) or abort(404)
        Device.query.filter_by(group_id=group.id).update({"group_id": None})
        affected_users = list(group.users)
        group.users.clear()
        for affected_user in affected_users:
            _bump_user_session_version(affected_user)
            _sign_user_security_state(affected_user)
        db.session.delete(group)
        db.session.commit()
        flash("Gruppe wurde gelöscht. Zugeordnete Geräte bleiben erhalten.", "info")
        return redirect(url_for("groups"))

    @app.route("/import", methods=["GET", "POST"])
    @admin_required
    def import_devices():
        if request.method == "POST":
            upload = request.files.get("csv_file")
            if not upload or not upload.filename:
                flash("Bitte eine CSV-Datei auswählen.", "danger")
                return redirect(url_for("import_devices"))
            rows = parse_csv_upload(upload)
            count = blocked = skipped = 0
            blocked_ids = _blocked_import_ids()
            for row in rows:
                name = row.get("name") or row.get("gerät") or row.get("device")
                rustdesk_id = _normalize_import_block_id(row.get("rustdesk_id") or row.get("rustdesk-id") or row.get("id"))
                if not name or not rustdesk_id:
                    skipped += 1
                    continue
                if rustdesk_id in blocked_ids:
                    blocked += 1
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
            flash(
                _t("import.csv.done", "CSV-Import abgeschlossen: {created} neu, {blocked} durch Blockliste übersprungen, {skipped} ungültig.").format(
                    created=count, blocked=blocked, skipped=skipped
                ),
                "success",
            )
            return redirect(url_for("devices"))
        return render_template(
            "import.html",
            groups=Group.query.order_by(Group.name.asc()).all(),
            blocklist_entries=ImportBlocklistEntry.query.order_by(ImportBlocklistEntry.created_at.desc(), ImportBlocklistEntry.id.desc()).all(),
        )

    @app.route("/import/blocklist/add", methods=["POST"])
    @admin_required
    def import_blocklist_add():
        rustdesk_id = _normalize_import_block_id(request.form.get("rustdesk_id"))
        if not rustdesk_id:
            flash(_t("import.blocklist.id_required", "Bitte eine RustDesk-ID eingeben."), "danger")
        elif Device.query.filter_by(rustdesk_id=rustdesk_id).first():
            flash(_t("import.blocklist.device_exists", "Diese RustDesk-ID ist aktuell noch als Gerät im Adressbuch vorhanden."), "warning")
        else:
            _add_import_blocklist_entry(
                rustdesk_id,
                device_name=request.form.get("device_name", "").strip()[:180],
                reason=request.form.get("reason", "").strip()[:255] or "Manuell zur Import-Blockliste hinzugefügt",
                created_by=current_user.username,
            )
            db.session.commit()
            _record_auth_event("import_blocklist_added", username=current_user.username, success=True, message=f"RustDesk-ID {rustdesk_id} zur Import-Blockliste hinzugefügt")
            flash(_t("import.blocklist.added", "RustDesk-ID wurde zur Import-Blockliste hinzugefügt."), "success")
        return redirect(url_for("import_devices") + "#blocklist")

    @app.route("/import/blocklist/<int:entry_id>/remove", methods=["POST"])
    @admin_required
    def import_blocklist_remove(entry_id: int):
        entry = db.session.get(ImportBlocklistEntry, entry_id) or abort(404)
        rustdesk_id = entry.rustdesk_id
        db.session.delete(entry)
        db.session.commit()
        _record_auth_event("import_blocklist_removed", username=current_user.username, success=True, message=f"RustDesk-ID {rustdesk_id} aus der Import-Blockliste entfernt")
        flash(_t("import.blocklist.removed", "RustDesk-ID wurde aus der Import-Blockliste entfernt und kann wieder importiert werden."), "info")
        return redirect(url_for("import_devices") + "#blocklist")

    @app.route("/import/rustdesk-server", methods=["GET", "POST"])
    @admin_required
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
                flash(_t("import.server.no_file", "Bitte db_v2.sqlite3 oder ein ZIP mit db_v2.sqlite3, db_v2.sqlite3-wal und optional db_v2.sqlite3-shm auswählen."), "danger")
                return redirect(url_for("import_rustdesk_server"))

            try:
                with _stage_rustdesk_sqlite_uploads(uploads) as staged_db:
                    result = _import_from_rustdesk_sqlite(staged_db, default_group_name, update_existing)
            except sqlite3.DatabaseError as exc:
                flash(_t("import.server.read_error", "Die Datei konnte nicht als RustDesk-SQLite-Datenbank gelesen werden: {error}").format(error=exc), "danger")
                return redirect(url_for("import_rustdesk_server"))
            except ValueError as exc:
                flash(str(exc), "danger")
                return redirect(url_for("import_rustdesk_server"))

            wal_note = _t("import.server.wal_seen", " WAL wurde berücksichtigt.") if result.get("wal_seen") else _t("import.server.no_wal", " Keine WAL-Datei im Upload gefunden.")
            status_note = _t("import.server.status_note", " Online-Status wird nicht aus der Server-DB übernommen; nutze dafür Live-Status hbbs.")
            flash(
                _t("import.server.done", "RustDesk-Server-Import abgeschlossen: {created} neu, {updated} aktualisiert, {skipped} übersprungen, {blocked} durch Blockliste gesperrt.").format(
                    created=result["created"], updated=result["updated"], skipped=result["skipped"], blocked=result.get("blocked", 0)
                ) + wal_note + status_note,
                "success",
            )
            return redirect(url_for("devices"))

        return render_template("import_rustdesk_server.html", groups=Group.query.order_by(Group.name.asc()).all())

    @app.route("/sync/rustdesk-status", methods=["POST"])
    @admin_required
    def sync_rustdesk_status():
        flash(_t("status.flash_removed", "Status aus Server-DB wurde entfernt. Der Online-Status wird jetzt über hbbs Live abgefragt; die Server-DB bleibt für Import und Diagnose erhalten."), "info")
        return redirect(request.referrer or url_for("devices"))

    @app.route("/sync/rustdesk-live-status", methods=["POST"])
    @admin_required
    def sync_rustdesk_live_status():
        try:
            result = _sync_hbbs_live_status(trigger="manual")
        except RustDeskLiveStatusError as exc:
            db.session.rollback()
            _record_status_check(False, str(exc), trigger="manual")
            flash(_t("status.flash_error", "hbbs Live-Abfrage fehlgeschlagen: {error}").format(error=exc), "danger")
            return redirect(request.referrer or url_for("devices"))

        flash(
            _t("status.flash_success", "hbbs Live-Status aktualisiert: {updated} geändert, {online} online, {offline} offline. Letzte Response states={states}.").format(
                updated=result["updated"],
                online=result["online"],
                offline=result["offline"],
                states=result.get("states") or "-",
            ),
            "success",
        )
        return redirect(request.referrer or url_for("devices"))


    @app.route("/api/status/auto-check", methods=["POST"])
    @admin_required
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
    @admin_required
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
            f"{result['updated']} aktualisiert, {result['skipped']} übersprungen, "
            f"{result.get('blocked', 0)} durch Blockliste gesperrt.{wal_note}",
            "success",
        )
        return redirect(request.referrer or url_for("import_rustdesk_server"))

    @app.route("/import/rustdesk-ssh/test", methods=["POST"])
    @admin_required
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
    @admin_required
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
            "blocked": result.get("blocked", 0),
            "wal_seen": result.get("wal_seen", False),
            "finished_at": _ui_timestamp(),
        }
        session["ssh_import_result"] = ssh_result
        flash(
            f"SSH-Import abgeschlossen: {result['created']} neu, "
            f"{result['updated']} aktualisiert, {result['skipped']} übersprungen, "
            f"{result.get('blocked', 0)} durch Blockliste gesperrt. "
            f"Remote-Snapshot enthielt {diagnostics.get('row_count', 0)} Peers.",
            "success",
        )
        return redirect(url_for("devices"))

    @app.route("/import/rustdesk-server/diagnose")
    @admin_required
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
    @admin_required
    def export_devices():
        include_passwords = request.args.get("include_passwords") == "1"
        if include_passwords and not _has_recent_auth():
            return redirect(url_for("reauth", next=request.full_path.rstrip("?")))
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
            writer.writerow({key: _csv_safe_cell(value) for key, value in row.items()})

        _record_auth_event(
            "devices_export",
            username=current_user.username,
            success=True,
            message=("Geräteexport mit entschlüsselten Passwörtern" if include_passwords else "Geräteexport ohne Passwörter"),
        )
        suffix = "with-passwords" if include_passwords else "no-passwords"
        filename = f"rustdesk-addressbook-{suffix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"
        return Response(
            output.getvalue(),
            content_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    @app.route("/backup", methods=["GET", "POST"])
    @admin_required
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
    @admin_required
    def backup_download(filename: str):
        safe = secure_filename(filename)
        if safe != filename:
            abort(404)
        return send_from_directory(current_app.config["BACKUP_DIR"], filename, as_attachment=True)

    @app.route("/security")
    @admin_required
    def security():
        events = AuthEvent.query.order_by(AuthEvent.created_at.desc()).limit(250).all()
        return render_template(
            "security.html",
            auth_events=events,
            report=_security_audit_report(),
            auth_log_file=str(current_app.config.get("AUTH_LOG_FILE")),
            fail_limit=_get_bruteforce_settings()["limit"],
            fail_window=_get_bruteforce_settings()["window_seconds"],
            auth_log_rotate_days=current_app.config.get("AUTH_LOG_ROTATE_DAYS", 7),
            auth_log_rotate_keep=current_app.config.get("AUTH_LOG_ROTATE_KEEP", 8),
        )

    @app.route("/security/auth-log/download")
    @admin_required
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
    @admin_required
    def api_update_check():
        result = _check_online_update_available()
        _record_update_check(result)
        return jsonify(result)


    @app.route("/settings", methods=["GET", "POST"])
    @admin_required
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
                    _commit_user_security_change(current_user, keep_current_session=True)
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
                    _commit_user_security_change(current_user, keep_current_session=True)
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
                    current_user.preferred_theme = theme_mode
                    current_user.preferred_language = language
                    db.session.commit()
                    flash(_t("account.preferences_saved", "Darstellung und Sprache wurden für dein Benutzerkonto gespeichert."), "success")
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
                    auto_value = max(auto_value, 1)
                else:
                    auto_unit = "minutes"
                    auto_value = max(auto_value, 1)

                _set_setting("status_source", source)
                _set_setting("hbbs_host", hbbs_host)
                _set_setting("hbbs_port", str(hbbs_port))
                _set_setting("hbbs_timeout", str(hbbs_timeout))
                _set_setting("hbbs_batch_size", str(hbbs_batch_size))
                _set_setting("hbbs_requester_id", hbbs_requester_id[:80])
                _set_setting("auto_status_enabled", "1" if auto_enabled else "0")
                _set_setting("auto_status_value", str(auto_value))
                _set_setting("auto_status_unit", auto_unit)
                flash(_t("settings.status.saved", "Online-Status-Einstellungen wurden gespeichert."), "success")
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
                flash(_t("settings.update.saved", "Update-Check-Einstellungen wurden gespeichert."), "success")
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
                    current_user.totp_recovery_hashes = None
                    _commit_user_security_change(current_user, keep_current_session=True)
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
                    _commit_user_security_change(current_user, keep_current_session=True)
                    _record_auth_event("2fa_enabled", username=current_user.username, success=True, message="2FA aktiviert und Recovery-Codes erstellt")
                    _queue_recovery_codes(current_user, recovery_codes)
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
                        _commit_user_security_change(current_user, keep_current_session=True)
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
                        _commit_user_security_change(current_user, keep_current_session=True)
                        _record_auth_event("2fa_recovery_regenerated", username=current_user.username, success=True, message="2FA-Recovery-Codes neu erstellt")
                        _queue_recovery_codes(current_user, recovery_codes)
                        if method == "recovery":
                            flash("Neue Wiederherstellungscodes wurden erstellt. Der eingegebene alte Wiederherstellungscode wurde ersetzt.", "warning")
                        else:
                            flash("Neue Wiederherstellungscodes wurden erstellt. Speichere sie jetzt sicher ab; sie werden nur einmal angezeigt.", "success")
                return redirect(url_for("settings"))

            if action == "totp_cancel":
                if not getattr(current_user, "totp_enabled", False):
                    current_user.totp_secret_encrypted = None
                    current_user.totp_recovery_hashes = None
                    _commit_user_security_change(current_user, keep_current_session=True)
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
            new_recovery_codes=_consume_recovery_codes(current_user),
        )



def _csv_safe_cell(value) -> str:
    """Prevent spreadsheet formula execution while preserving exported text."""
    text = "" if value is None else str(value)
    probe = text.lstrip(" \t\r\n")
    if probe.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def _import_from_rustdesk_sqlite(db_path: Path, default_group_name: str, update_existing: bool) -> dict[str, int]:
    group = _get_or_create_group(default_group_name)
    created = updated = skipped = blocked = status_values_seen = 0
    blocked_ids = _blocked_import_ids()

    for row in _read_rustdesk_peer_rows(db_path):
        rustdesk_id = _normalize_import_block_id(row["id"])
        if not rustdesk_id:
            skipped += 1
            continue
        if rustdesk_id in blocked_ids:
            blocked += 1
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
        "blocked": blocked,
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
    max_members = 16
    max_total = min(int(current_app.config.get("MAX_CONTENT_LENGTH", 100 * 1024 * 1024)), 256 * 1024 * 1024)
    total_size = 0
    try:
        with zipfile.ZipFile(zip_path) as zf:
            infos = [info for info in zf.infolist() if not info.is_dir()]
            if len(infos) > max_members:
                raise ValueError(f"ZIP-Datei enthält zu viele Dateien (maximal {max_members}).")
            for info in infos:
                if info.file_size < 0 or info.file_size > max_total:
                    raise ValueError("Eine Datei im ZIP überschreitet die zulässige Größe.")
                total_size += info.file_size
                if total_size > max_total:
                    raise ValueError("Der entpackte ZIP-Inhalt überschreitet die zulässige Gesamtgröße.")
                filename = secure_filename(Path(info.filename).name)
                if not filename or not _is_rustdesk_sqlite_family_file(filename):
                    continue
                target = target_dir / filename
                with zf.open(info) as src, target.open("wb") as dst:
                    remaining = info.file_size
                    while remaining > 0:
                        chunk = src.read(min(1024 * 1024, remaining))
                        if not chunk:
                            break
                        dst.write(chunk)
                        remaining -= len(chunk)
                    if remaining != 0:
                        raise ValueError("Eine ZIP-Datei konnte nicht vollständig oder konsistent entpackt werden.")
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
            "message": _t("db.status.not_set", "RUSTDESK_SERVER_DB ist nicht gesetzt. Direkter DB-Import und DB-Diagnose sind deaktiviert."),
            "badge": "text-bg-secondary",
            "family": {"main": False, "wal": False, "shm": False},
        }
    db_path = Path(configured)
    exists = db_path.is_file()
    family = _sqlite_family_info(db_path) if exists else {"main": False, "wal": False, "shm": False}
    if exists:
        extra = []
        if family.get("wal"):
            extra.append(_t("db.status.wal_visible", "WAL sichtbar"))
        if family.get("shm"):
            extra.append(_t("db.status.shm_visible", "SHM sichtbar"))
        suffix = " (" + ", ".join(extra) + ")" if extra else ""
        return {
            "configured": True,
            "exists": True,
            "path": configured,
            "message": f"{_t('db.status.active', 'Aktiv')}: {configured}{suffix}",
            "badge": "text-bg-success",
            "family": family,
        }
    return {
        "configured": True,
        "exists": False,
        "path": configured,
        "message": f"{_t('db.status.not_found', 'RUSTDESK_SERVER_DB ist gesetzt, aber die Datei wurde nicht gefunden')}: {configured}",
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
        "host_key_fingerprint": _get_setting("ssh_import_host_key_fingerprint", "").strip(),
        "remote_command": _get_setting("ssh_import_remote_command", "").strip(),
        "timeout": min(max(timeout, 3), 120),
    }


def _save_ssh_import_settings_from_form() -> None:
    host = request.form.get("ssh_host", "").strip()
    user = request.form.get("ssh_user", "rab-import").strip() or "rab-import"
    key_path = request.form.get("ssh_key_path", "").strip()
    known_hosts_path = request.form.get("ssh_known_hosts_path", "").strip()
    host_key_fingerprint = request.form.get("ssh_host_key_fingerprint", "").strip()
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
    _set_setting("ssh_import_host_key_fingerprint", host_key_fingerprint[:120])
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


def _verify_and_store_ssh_host_key(host: str, port: int, expected_fingerprint: str, known_hosts_path: Path, timeout: int) -> None:
    expected = str(expected_fingerprint or "").strip()
    if not expected.startswith("SHA256:"):
        raise ValueError("Für den SSH-Import muss der zuvor separat geprüfte Hostschlüssel-Fingerprint im Format SHA256:... hinterlegt werden.")
    ssh_keyscan = shutil.which("ssh-keyscan")
    ssh_keygen = shutil.which("ssh-keygen")
    if not ssh_keyscan or not ssh_keygen:
        raise ValueError("ssh-keyscan oder ssh-keygen wurde im Container nicht gefunden.")
    try:
        scan = subprocess.run(
            [ssh_keyscan, "-T", str(min(max(timeout, 3), 30)), "-p", str(port), host],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=min(max(timeout, 3), 30) + 5, check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise ValueError("SSH-Hostschlüssel konnte nicht sicher abgefragt werden.") from exc
    lines = [line for line in scan.stdout.decode("utf-8", errors="replace").splitlines() if line and not line.startswith("#")]
    if not lines:
        raise ValueError("Der SSH-Server hat keinen Hostschlüssel geliefert.")
    matching_line = None
    with tempfile.TemporaryDirectory(prefix="ssh-hostkey-") as tmp_name:
        key_file = Path(tmp_name) / "hostkey.pub"
        for line in lines:
            key_file.write_text(line + "\n", encoding="utf-8")
            result = subprocess.run([ssh_keygen, "-lf", str(key_file), "-E", "sha256"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            output = result.stdout.decode("utf-8", errors="replace")
            if expected in output.split():
                matching_line = line
                break
    if matching_line is None:
        raise ValueError("Der gelieferte SSH-Hostschlüssel stimmt nicht mit dem hinterlegten SHA256-Fingerprint überein.")
    known_hosts_path.parent.mkdir(parents=True, exist_ok=True)
    known_hosts_path.touch(mode=0o600, exist_ok=True)
    target = host if port == 22 else f"[{host}]:{port}"
    subprocess.run([ssh_keygen, "-R", target, "-f", str(known_hosts_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    with known_hosts_path.open("a", encoding="utf-8") as fh:
        fh.write(matching_line + "\n")
    try:
        known_hosts_path.chmod(0o600)
    except OSError:
        pass


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
    _verify_and_store_ssh_host_key(host, settings["port"], settings.get("host_key_fingerprint", ""), known_hosts_path, settings["timeout"])

    try:
        key_path.chmod(0o600)
    except OSError:
        pass

    upload_root = Path(current_app.config["DATA_DIR"]) / "tmp_uploads"
    upload_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rustdesk-ssh-import-", dir=upload_root) as tmp_name:
        tmp_dir = Path(tmp_name)
        snapshot = tmp_dir / "rustdesk-db-snapshot.sqlite3"
        ssh_client = shutil.which("ssh")
        if not ssh_client:
            raise ValueError("Der SSH-Client wurde im Container nicht gefunden. Bitte Image mit openssh-client neu bauen.")
        cmd = [
            ssh_client,
            "-T",
            "-i", str(key_path),
            "-p", str(settings["port"]),
            "-o", "IdentitiesOnly=yes",
            "-o", "BatchMode=yes",
            "-o", f"ConnectTimeout={settings['timeout']}",
            "-o", f"UserKnownHostsFile={known_hosts_path}",
            "-o", "StrictHostKeyChecking=yes",
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
            # Column names are selected exclusively from the fixed whitelist above.
            return con.execute(f"SELECT {', '.join(wanted)} FROM peer ORDER BY id COLLATE NOCASE").fetchall()  # nosec B608


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
                # Column names are selected exclusively from the fixed whitelist above.
                for row in con.execute(f"SELECT {', '.join(wanted)} FROM peer ORDER BY id COLLATE NOCASE LIMIT 10").fetchall():  # nosec B608
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
    message = _t("status.last_summary", "{online} online, {offline} offline, {updated} geändert").format(online=online_count, offline=offline_count, updated=updated)
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
    online = _get_setting("status_last_online", "")
    offline = _get_setting("status_last_offline", "")
    updated = _get_setting("status_last_updated", "")
    message = _get_setting("status_last_message", "")
    if ok_raw == "1" and online != "" and offline != "" and updated != "":
        message = _t("status.last_summary", "{online} online, {offline} offline, {updated} geändert").format(online=online, offline=offline, updated=updated)
    trigger_raw = _get_setting("status_last_trigger", "")
    trigger = _t("status.trigger.manual", "Manuell") if trigger_raw == "manual" else (_t("status.trigger.auto", "Automatisch") if trigger_raw == "auto" else trigger_raw)
    return {
        "checked_at": _get_setting("status_last_checked_at", ""),
        "ok": True if ok_raw == "1" else False if ok_raw == "0" else None,
        "trigger": trigger,
        "message": message,
        "online": online,
        "offline": offline,
        "updated": updated,
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
        value = max(value, 1)
        seconds = value * 3600
        label = f"alle {value} Stunde{'n' if value != 1 else ''}"
    else:
        unit = "minutes"
        value = max(value, 1)
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
        local_users = [u for u in users if u.auth_provider == "local" and u.active]
        oidc_users = [u for u in users if u.auth_provider == "oidc" and u.active]
        protected = sum(1 for u in local_users if getattr(u, "totp_enabled", False))
        twofa_status = "ok" if not local_users or protected == len(local_users) else "warn"
        add("2FA", twofa_status, _t("security.report.2fa_local", "{protected} von {total} aktiven lokalen Benutzer(n) haben 2FA aktiviert; OIDC-MFA wird durch den Provider verwaltet.").format(protected=protected, total=len(local_users)))
        recovery = sum(_recovery_code_count(u) for u in local_users)
        add(_t("security.report.recovery_name", "2FA-Recovery-Codes"), "ok" if recovery or not local_users else "warn", _t("security.report.recovery", "Verfügbare Recovery-Codes gesamt: {count}.").format(count=recovery))
        signed = sum(1 for u in users if _verify_user_security_state(u))
        add(_t("security.report.sign_name", "DB-Manipulationsschutz Benutzer"), "ok" if signed == len(users) else "danger", _t("security.report.sign", "{signed} von {total} Benutzer-Sicherheitszuständen haben eine gültige HMAC-Signatur. Policy: {policy}.").format(signed=signed, total=len(users), policy=_user_signature_policy()))
        active_admins = sum(1 for u in users if u.active and u.role == "admin")
        local_admins = sum(1 for u in users if u.active and u.role == "admin" and u.auth_provider == "local")
        add(_t("security.report.rbac_name", "Benutzerrollen / Notfallzugang"), "ok" if active_admins and local_admins else "danger", _t("security.report.rbac_detail", "Aktive Administratoren: {admins}; davon lokale Notfall-Administratoren: {local_admins}. Aktive OIDC-Benutzer: {oidc_users}.").format(admins=active_admins, local_admins=local_admins, oidc_users=len(oidc_users)))
    else:
        add(_t("security.report.users_name", "Benutzer"), "danger", _t("security.report.no_users", "Kein Benutzer gefunden."))

    oidc_settings = _get_oidc_settings()
    if oidc_settings["enabled"]:
        add("OpenID Connect", "ok" if oidc_settings["configured"] and not oidc_settings["allow_insecure"] else "warn", _t("security.report.oidc_detail", "OIDC ist aktiviert. Provider: {provider}; Auto-Provisioning: {auto}; unsicheres HTTP erlaubt: {insecure}.").format(provider=oidc_settings["provider_name"], auto=("ja" if oidc_settings["auto_provision"] else "nein"), insecure=("ja" if oidc_settings["allow_insecure"] else "nein")))
    else:
        add("OpenID Connect", "info", _t("security.report.oidc_disabled", "OIDC-Anmeldung ist deaktiviert; lokale Anmeldung bleibt verfügbar."))

    add("Session-Cookie HttpOnly", "ok" if current_app.config.get("SESSION_COOKIE_HTTPONLY") else "danger", f"SESSION_COOKIE_HTTPONLY={current_app.config.get('SESSION_COOKIE_HTTPONLY')}")
    add("Session-Cookie Secure", "ok" if current_app.config.get("SESSION_COOKIE_SECURE") else "warn", _t("security.report.cookie_secure", "Für reinen HTTPS-Betrieb sollte SESSION_COOKIE_SECURE=true gesetzt werden."))
    add("HSTS", "ok" if current_app.config.get("APP_HSTS") else "warn", _t("security.report.hsts", "Für produktiven HTTPS-Betrieb sollte APP_HSTS=true gesetzt werden."))
    add(_t("security.report.proxy_name", "Proxy-Header"), "ok" if current_app.config.get("TRUST_PROXY_HEADERS") else "info", _t("security.report.proxy", "TRUST_PROXY_HEADERS nur hinter vertrauenswürdigem Reverse Proxy aktivieren; sonst false lassen."))

    auth_log = Path(current_app.config.get("AUTH_LOG_FILE"))
    add(_t("security.report.auth_log", "Auth-Logdatei"), "ok" if auth_log.parent.exists() else "danger", str(auth_log))
    if auth_log.exists():
        mode = oct(auth_log.stat().st_mode & 0o777)
        add(_t("security.report.auth_log_perms", "Auth-Log Berechtigungen"), "ok" if mode in {"0o600", "0o640"} else "warn", _t("security.report.file_mode", "Dateimodus: {mode}").format(mode=mode))

    data_dir = Path(current_app.config["DATA_DIR"])
    cfg = data_dir / "config.json"
    db_file = data_dir / "addressbook.db"
    for label, path, expected_modes in [
        (_t("security.report.runtime_secrets", "Runtime-Secrets"), cfg, {"0o600", "0o640"}),
        (_t("security.report.sqlite_db", "SQLite-Datenbank"), db_file, {"0o600", "0o640", "0o644"}),
    ]:
        if path.exists():
            mode = oct(path.stat().st_mode & 0o777)
            add(label, "ok" if mode in expected_modes else "warn", _t("security.report.path_mode", "{path} Modus {mode}").format(path=path, mode=mode))
        else:
            add(label, "warn", _t("security.report.path_missing", "{path} existiert aktuell nicht.").format(path=path))

    backup_dir = Path(current_app.config["BACKUP_DIR"])
    plain = len([p for p in backup_dir.glob("*.db") if p.is_file()]) if backup_dir.exists() else 0
    encrypted = len([p for p in backup_dir.glob("*.rabenc") if p.is_file()]) if backup_dir.exists() else 0
    full = len([p for p in backup_dir.glob("*.rabfull") if p.is_file()]) if backup_dir.exists() else 0
    add(_t("security.report.backups", "Backups"), "ok" if full or encrypted or plain == 0 else "warn", _t("security.report.backups_detail", "{full} verschlüsselte Vollbackups .rabfull, {encrypted} verschlüsselte .rabenc, {plain} unverschlüsselte .db Backups.").format(full=full, encrypted=encrypted, plain=plain))

    add(_t("security.report.sqlite_enc", "SQLite-Dateiverschlüsselung"), "info", _t("security.report.sqlite_enc_detail", "Die produktive SQLite-Datei ist nicht vollständig SQLCipher-verschlüsselt. Sensible Gerätepasswörter sind feldweise verschlüsselt; Benutzer-Sicherheitsfelder sind zusätzlich HMAC-signiert."))
    settings = _get_bruteforce_settings()
    add(_t("security.report.bruteforce", "Brute-Force-Sperre"), "ok", _t("security.report.bruteforce_detail", "Limit {limit} Fehlversuche je IP/Benutzer innerhalb {window} Sekunden.").format(limit=settings["limit"], window=settings["window_seconds"]))

    try:
        rotate_days = int(current_app.config.get("AUTH_LOG_ROTATE_DAYS", 7))
    except (TypeError, ValueError):
        rotate_days = 7
    try:
        rotate_keep = int(current_app.config.get("AUTH_LOG_ROTATE_KEEP", 8))
    except (TypeError, ValueError):
        rotate_keep = 8
    add(_t("security.report.log_rotation_name", "Auth-Logrotation"), "ok" if rotate_days > 0 and rotate_keep > 0 else "warn", _t("security.report.log_rotation_detail", "Alle {days} Tag(e), Aufbewahrung {keep} rotierte Datei(en).").format(days=rotate_days, keep=rotate_keep))

    auto_update = _get_update_auto_check_settings()
    add(_t("security.report.update_check_name", "Update-Check"), "ok" if auto_update.get("enabled") else "info", _t("security.report.update_check_detail", "Automatischer Update-Check ist {state}. Intervall: {hours} Stunde(n).").format(state=("aktiv" if auto_update.get("enabled") else "inaktiv"), hours=auto_update.get("interval_hours")))

    status_settings = _get_status_settings()
    add(_t("security.report.hbbs_name", "hbbs Live-Status"), "ok" if status_settings.get("source") == "hbbs" and status_settings.get("hbbs_host") else "info", _t("security.report.hbbs_detail", "Statusquelle: {source}. Host gesetzt: {host}.").format(source=status_settings.get("source"), host=("ja" if status_settings.get("hbbs_host") else "nein")))

    add(_t("security.report.https_name", "HTTPS-Endpunkt"), "ok", _t("security.report.https_detail", "Der Container stellt HTTPS bereit; für produktiven HTTPS-Betrieb SESSION_COOKIE_SECURE und APP_HSTS aktivieren."))
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
    max_members = max(10, int(current_app.config.get("FULL_BACKUP_MAX_MEMBERS", 5000)))
    max_total = max(1024 * 1024, int(current_app.config.get("FULL_BACKUP_MAX_TOTAL_BYTES", 512 * 1024 * 1024)))
    max_file = max(1024 * 1024, int(current_app.config.get("FULL_BACKUP_MAX_FILE_BYTES", 128 * 1024 * 1024)))
    tmp_dir = data_dir / "tmp_restore_full" / secrets.token_hex(8)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    restored: list[str] = []
    try:
        with tarfile.open(fileobj=BytesIO(tar_bytes), mode="r:gz") as tar:
            members = tar.getmembers()
            if len(members) > max_members:
                raise ValueError(f"Vollbackup enthält zu viele Einträge (maximal {max_members}).")
            names = {member.name for member in members}
            if not {"manifest.json", "data/addressbook.db", "data/config.json"}.issubset(names):
                raise ValueError("Vollbackup ist unvollständig. manifest.json, data/addressbook.db oder data/config.json fehlt.")
            total_size = 0
            seen: set[str] = set()
            root = tmp_dir.resolve()
            for member in members:
                name = str(member.name or "")
                if len(name) > 512 or name.startswith("/") or ".." in Path(name).parts:
                    raise ValueError(f"Unsicherer Pfad im Vollbackup: {name}")
                if name in seen:
                    raise ValueError(f"Doppelter Pfad im Vollbackup: {name}")
                seen.add(name)
                if member.isdir():
                    continue
                if not member.isreg():
                    raise ValueError(f"Nicht unterstützter Dateityp im Vollbackup: {name}")
                if name not in allowed_exact and not name.startswith(allowed_prefixes):
                    raise ValueError(f"Nicht erlaubter Pfad im Vollbackup: {name}")
                if member.size < 0 or member.size > max_file:
                    raise ValueError(f"Datei im Vollbackup ist zu groß: {name}")
                total_size += member.size
                if total_size > max_total:
                    raise ValueError("Entpackter Vollbackup-Inhalt überschreitet die zulässige Gesamtgröße.")
                target = (tmp_dir / name).resolve()
                if root not in target.parents:
                    raise ValueError(f"Pfad verlässt das Restore-Verzeichnis: {name}")
                source = tar.extractfile(member)
                if source is None:
                    raise ValueError(f"Datei im Vollbackup konnte nicht gelesen werden: {name}")
                target.parent.mkdir(parents=True, exist_ok=True)
                written = 0
                with target.open("xb") as dst:
                    while written < member.size:
                        chunk = source.read(min(1024 * 1024, member.size - written))
                        if not chunk:
                            break
                        dst.write(chunk)
                        written += len(chunk)
                if written != member.size:
                    raise ValueError(f"Datei im Vollbackup ist unvollständig: {name}")

        manifest = json.loads((tmp_dir / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("format") != "rustdesk-addressbook-full-backup" or int(manifest.get("version", 0)) != 1:
            raise ValueError("Vollbackup-Manifest hat ein unbekanntes Format oder eine nicht unterstützte Version.")
        candidate_db = tmp_dir / "data" / "addressbook.db"
        _validate_addressbook_sqlite(candidate_db)

        for rel in ["addressbook.db", "config.json"]:
            src = tmp_dir / "data" / rel
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
    except (tarfile.TarError, json.JSONDecodeError) as exc:
        raise ValueError(f"Vollbackup konnte nicht sicher gelesen werden: {exc}") from exc
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


def _clean_optional_text(value: str | None) -> str | None:
    """Normalize optional form/device fields.

    Older builds could accidentally render/save Python None as the literal text
    "None" in optional fields. Treat these placeholder values as empty.
    """
    cleaned = str(value or "").strip()
    if cleaned.lower() in {"none", "null"}:
        return None
    return cleaned or None


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
    device.customer = _clean_optional_text(request.form.get("customer", ""))
    device.location = _clean_optional_text(request.form.get("location", ""))
    device.os = _normalize_os(request.form.get("os", "")) or None
    device.tags = _clean_optional_text(request.form.get("tags", ""))
    device.notes = _clean_optional_text(request.form.get("notes", ""))
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
    parsed = urllib.parse.urlparse(str(url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Update-URL muss eine vollständige HTTP- oder HTTPS-Adresse sein.")
    req = urllib.request.Request(parsed.geturl(), headers={"User-Agent": f"RustDesk-AddressBook/{_short_app_version(current_app.config.get('APP_VERSION', 'dev'))}"})
    # Only HTTP(S) URLs with a host are accepted above.
    with urllib.request.urlopen(req, timeout=timeout) as response:  # nosec B310
        final_url = urllib.parse.urlparse(response.geturl())
        if final_url.scheme not in {"http", "https"} or not final_url.netloc:
            raise ValueError("Update-Server hat auf eine unzulässige Adresse umgeleitet.")
        data = response.read(256 * 1024)
    return data.decode("utf-8", errors="replace")


def _normalize_release_notes(value, lang: str | None = None) -> list[str]:
    if value is None:
        return []
    selected_lang = (lang or _get_language()).strip().lower()
    if isinstance(value, list):
        raw_lines = [str(item).strip() for item in value]
    else:
        raw_lines = [line.strip() for line in str(value).replace("\r\n", "\n").split("\n")]

    # Supports bilingual latest.txt/release files:
    #   rustdesk-addressbook-update-flat-v0519.zip
    #   [de]
    #   - Änderung ...
    #   [en]
    #   - Change ...
    # Also supports one-line prefixes: de: ... / en: ...
    sectioned: dict[str, list[str]] = {"de": [], "en": []}
    active_section: str | None = None
    generic: list[str] = []
    for line in raw_lines:
        if not line or line.startswith("#"):
            continue
        marker = line.strip().lower()
        if marker in {"[de]", "de:", "de"}:
            active_section = "de"
            continue
        if marker in {"[en]", "en:", "en"}:
            active_section = "en"
            continue
        pref = re.match(r"^(de|en)\s*[:|-]\s*(.+)$", line, flags=re.I)
        if pref:
            sectioned[pref.group(1).lower()].append(pref.group(2).strip())
            continue
        if active_section in sectioned:
            sectioned[active_section].append(line)
        else:
            generic.append(line)

    items = sectioned.get(selected_lang) or generic or sectioned.get("de") or sectioned.get("en") or []
    cleaned: list[str] = []
    for item in items:
        if not item or item.startswith("#"):
            continue
        item = re.sub(r"^[-*•]\s+", "", item).strip()
        if item:
            cleaned.append(item[:500])
    return cleaned[:30]


def _fetch_remote_release_notes(base: str, file_name: str, lang: str | None = None) -> list[str]:
    if not file_name:
        return []
    stem = Path(file_name).stem
    selected_lang = (lang or _get_language()).strip().lower()
    version_match = re.search(r"v(\d+)", file_name)
    version_tag = f"v{version_match.group(1)}" if version_match else ""
    candidates = [
        f"{base}/{stem}.{selected_lang}.txt",
        f"{base}/{stem}.{selected_lang}.md",
        f"{base}/{stem}.txt",
        f"{base}/{stem}.md",
    ]
    if version_tag:
        candidates.extend([
            f"{base}/release-notes-{version_tag}.{selected_lang}.txt",
            f"{base}/release-notes-{version_tag}.{selected_lang}.md",
            f"{base}/release-notes-{version_tag}.txt",
            f"{base}/release-notes-{version_tag}.md",
            f"{base}/releases/{version_tag}.{selected_lang}.txt",
            f"{base}/releases/{version_tag}.{selected_lang}.md",
            f"{base}/releases/{version_tag}.txt",
            f"{base}/releases/{version_tag}.md",
        ])
    for url in candidates:
        try:
            notes = _normalize_release_notes(_fetch_text_url(url), lang=selected_lang)
            if notes:
                return notes
        except Exception:
            continue
    return []


def _online_update_manifest() -> dict:
    base = str(current_app.config.get("RAB_UPDATE_BASE_URL", "") or "").strip().rstrip("/")
    if not base:
        return {
            "ok": False,
            "disabled": True,
            "base_url": "",
            "file": "",
            "version": "",
            "source": "",
            "release_notes": [],
            "errors": [_t("settings.update.disabled", "Online-Update-Prüfungen sind deaktiviert, weil RAB_UPDATE_BASE_URL nicht konfiguriert ist.")],
        }
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
                inline_notes = _normalize_release_notes(lines[idx + 1:], lang=_get_language())
                file_name = Path(candidate).name
                notes = inline_notes or _fetch_remote_release_notes(base, file_name, lang=_get_language())
                return {"ok": True, "base_url": base, "file": file_name, "version": "", "source": "latest.txt", "release_notes": notes, "errors": []}
        errors.append(_t("update.error.invalid_manifest", "latest.txt enthält keine gültige Update-ZIP."))
    except Exception as exc:
        errors.append(_t("update.error.read_failed", "latest.txt konnte nicht gelesen werden: {error}").format(error=exc))

    return {"ok": False, "base_url": base, "file": "", "version": "", "source": "latest.txt", "release_notes": [], "errors": errors}


def _check_online_update_available() -> dict:
    current_version = current_app.config.get("APP_VERSION", "0.0.0")
    current_num = _version_number(str(current_version))
    checked_at = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    manifest = _online_update_manifest()
    result = {
        "checked_at": checked_at,
        "ok": bool(manifest.get("ok")),
        "disabled": bool(manifest.get("disabled")),
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
    if manifest.get("disabled"):
        result["message"] = _t("settings.update.disabled", "Online-Update-Prüfungen sind deaktiviert, weil RAB_UPDATE_BASE_URL nicht konfiguriert ist.")
        return result
    if not manifest.get("ok"):
        result["message"] = _t("update.message.no_manifest", "Kein gültiges Online-Manifest gefunden.")
        return result

    latest_file = str(manifest.get("file") or "")
    latest_num = _version_number(str(manifest.get("version") or latest_file))
    result["latest_num"] = latest_num
    result["download_url"] = f"{str(manifest.get('base_url')).rstrip('/')}/{latest_file}"
    if latest_num > current_num:
        result["update_available"] = True
        result["message"] = _t("update.message.available", "Update verfügbar: {file}").format(file=latest_file)
    else:
        result["message"] = _t("update.message.current", "Kein Update verfügbar. Die installierte Version ist aktuell oder neuer.")
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
    configured = bool(str(current_app.config.get("RAB_UPDATE_BASE_URL", "") or "").strip())
    return {
        "configured": configured,
        "checked_at": _get_setting("update_last_checked_at", ""),
        "checked_ts": checked_ts,
        "ok": True if ok_raw == "1" else False if ok_raw == "0" else None,
        "message": _get_setting("update_last_message", ""),
        "file": _get_setting("update_last_file", ""),
        "url": _get_setting("update_last_url", ""),
        "available": normalize_bool(_get_setting("update_last_available", "0")),
        "release_notes": _normalize_release_notes(_get_setting("update_last_release_notes", ""), lang=_get_language()),
        "stale": auto_settings["stale"],
        "age_seconds": auto_settings["age_seconds"],
    }


def _get_update_auto_check_settings(checked_ts: int | None = None) -> dict:
    configured = bool(str(current_app.config.get("RAB_UPDATE_BASE_URL", "") or "").strip())
    enabled = configured and normalize_bool(_get_setting("update_auto_check_enabled", "0"))
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
        "configured": configured,
        "interval_seconds": interval_seconds,
        "interval_hours": max(1, int(interval_seconds // 3600)),
        "stale": bool(enabled and age_seconds >= interval_seconds),
        "age_seconds": max(0, age_seconds),
    }

def _parse_bool_setting(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on", "ja"}


def _host_resolves_to_private_network(hostname: str) -> bool:
    host = str(hostname or "").strip().lower().rstrip(".")
    if not host:
        return True
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".local", ".internal", ".localhost")):
        return True
    try:
        addresses = {item[4][0].split("%", 1)[0] for item in socket.getaddrinfo(host, None)}
    except socket.gaierror as exc:
        raise ValueError("Der OIDC-Issuer-Hostname konnte nicht aufgelöst werden.") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            return True
    return False


def _validate_oidc_issuer_url(value: str, *, allow_insecure: bool = False) -> str:
    issuer = str(value or "").strip().rstrip("/")
    parsed = urllib.parse.urlparse(issuer)
    allowed_schemes = {"https"} | ({"http"} if allow_insecure else set())
    if parsed.scheme not in allowed_schemes or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("Die OIDC-Issuer-URL ist ungültig. Standardmäßig ist ausschließlich HTTPS erlaubt.")
    if parsed.query or parsed.fragment:
        raise ValueError("Die OIDC-Issuer-URL darf keine Query-Parameter oder Fragmente enthalten.")
    if not current_app.config.get("OIDC_ALLOW_PRIVATE_ISSUER") and _host_resolves_to_private_network(parsed.hostname or ""):
        raise ValueError("Private, lokale oder reservierte OIDC-Issuer-Adressen sind gesperrt. Für einen bewusst internen Provider OIDC_ALLOW_PRIVATE_ISSUER=true setzen.")
    return issuer


def _get_oidc_settings(*, include_secret: bool = False) -> dict:
    allow_insecure = _parse_bool_setting(_get_setting("oidc_allow_insecure", "false"))
    issuer = _get_setting("oidc_issuer_url", "").strip().rstrip("/")
    scopes = " ".join(dict.fromkeys((_get_setting("oidc_scopes", "openid profile email") or "openid profile email").split()))
    if "openid" not in scopes.split():
        scopes = "openid " + scopes
    settings = {
        "enabled": _parse_bool_setting(_get_setting("oidc_enabled", "false")),
        "issuer_url": issuer,
        "client_id": _get_setting("oidc_client_id", "").strip(),
        "scopes": scopes,
        "provider_name": (_get_setting("oidc_provider_name", "OpenID Connect").strip() or "OpenID Connect")[:80],
        "username_claim": (_get_setting("oidc_username_claim", "preferred_username").strip() or "preferred_username")[:80],
        "auto_provision": _parse_bool_setting(_get_setting("oidc_auto_provision", "false")),
        "allowed_domains": [item.strip().lower() for item in _get_setting("oidc_allowed_domains", "").split(",") if item.strip()],
        "allow_insecure": allow_insecure,
        "configured": bool(issuer and _get_setting("oidc_client_id", "").strip() and _get_setting("oidc_client_secret", "")),
    }
    if include_secret:
        encrypted = _get_setting("oidc_client_secret", "")
        try:
            settings["client_secret"] = decrypt_value(encrypted) if encrypted else ""
        except Exception:
            settings["client_secret"] = ""
    return settings


def _configure_oidc_client():
    settings = _get_oidc_settings(include_secret=True)
    if not settings["enabled"] or not settings["configured"] or not settings.get("client_secret"):
        raise ValueError("OIDC ist nicht vollständig konfiguriert oder nicht aktiviert.")
    issuer = _validate_oidc_issuer_url(settings["issuer_url"], allow_insecure=settings["allow_insecure"])
    return oauth.register(
        "rustdesk_oidc",
        overwrite=True,
        client_id=settings["client_id"],
        client_secret=settings["client_secret"],
        server_metadata_url=f"{issuer}/.well-known/openid-configuration",
        client_kwargs={
            "scope": settings["scopes"],
            "code_challenge_method": "S256",
        },
    )


def _oidc_claim_username(userinfo: dict, settings: dict) -> str:
    claim = settings.get("username_claim") or "preferred_username"
    raw = userinfo.get(claim) or userinfo.get("preferred_username") or userinfo.get("email") or userinfo.get("name") or userinfo.get("sub")
    value = str(raw or "").strip()
    value = re.sub(r"[^A-Za-z0-9._@-]+", "-", value).strip("-.")[:80]
    return value or f"oidc-{str(userinfo.get('sub') or secrets.token_hex(4))[:32]}"


def _unique_username(base: str) -> str:
    candidate = base[:80]
    if not User.query.filter_by(username=candidate).first():
        return candidate
    for number in range(2, 10000):
        suffix = f"-{number}"
        candidate = f"{base[:80-len(suffix)]}{suffix}"
        if not User.query.filter_by(username=candidate).first():
            return candidate
    raise ValueError("Für den OIDC-Benutzer konnte kein eindeutiger Benutzername erzeugt werden.")


def _oidc_email_allowed(email: str, settings: dict) -> bool:
    domains = settings.get("allowed_domains") or []
    if not domains:
        return True
    email = str(email or "").strip().lower()
    if "@" not in email:
        return False
    return email.rsplit("@", 1)[1] in domains


def _set_settings_bulk(values: dict[str, str]) -> None:
    for key, value in values.items():
        setting = Setting.query.filter_by(key=key).first()
        if setting:
            setting.value = str(value)
        else:
            db.session.add(Setting(key=key, value=str(value)))
    db.session.commit()


def _normalize_import_block_id(value) -> str:
    return str(value or "").strip()[:80]


def _blocked_import_ids() -> set[str]:
    return {row[0] for row in db.session.query(ImportBlocklistEntry.rustdesk_id).all() if row[0]}


def _add_import_blocklist_entry(
    rustdesk_id: str,
    *,
    device_name: str = "",
    reason: str = "",
    created_by: str = "",
) -> ImportBlocklistEntry:
    normalized = _normalize_import_block_id(rustdesk_id)
    if not normalized:
        raise ValueError("RustDesk-ID darf nicht leer sein.")
    entry = ImportBlocklistEntry.query.filter_by(rustdesk_id=normalized).first()
    if entry is None:
        entry = ImportBlocklistEntry(rustdesk_id=normalized)
        db.session.add(entry)
    if device_name:
        entry.device_name = str(device_name).strip()[:180]
    if reason:
        entry.reason = str(reason).strip()[:255]
    if created_by:
        entry.created_by = str(created_by).strip()[:80]
    entry.created_at = utcnow()
    return entry


def _get_setting(key: str, default: str = "") -> str:
    setting = Setting.query.filter_by(key=key).first()
    return setting.value if setting else default


def _get_language() -> str:
    allowed = {key for key, _label in LANGUAGE_CHOICES}
    if has_request_context() and current_user.is_authenticated:
        lang = str(getattr(current_user, "preferred_language", "") or "").strip().lower()
        if lang in allowed:
            return lang
    lang = _get_setting("language", "de").strip().lower()
    return lang if lang in allowed else "de"


def _t(key: str, default: str | None = None) -> str:
    lang = _get_language()
    if lang == "de":
        return default if default is not None else key
    return TRANSLATIONS.get(lang, {}).get(key, default if default is not None else key)


def _translated_group_color_choices() -> list[tuple[str, str]]:
    return [(value, _t(f"group.color.{value}", label)) for value, label in GROUP_COLOR_CHOICES]


def _safe_group_icon(value: str | None) -> str:
    allowed = {item for item, _label in GROUP_ICON_CHOICES}
    candidate = str(value or "").strip().lower()
    return candidate if candidate in allowed else "collection"


def _translated_group_icon_choices() -> list[tuple[str, str]]:
    return [(value, _t(f"group.icon.{value}", label)) for value, label in GROUP_ICON_CHOICES]


def _translated_theme_choices() -> list[tuple[str, str]]:
    return [("light", _t("theme.light", "Heller Modus")), ("dark", _t("theme.dark", "Darkmode"))]


def _translated_status_source_choices() -> list[tuple[str, str]]:
    return [("manual", _t("status.manual", "Nur manuell")), ("hbbs", _t("status.hbbs", "hbbs Live-Abfrage"))]


def _get_theme_mode() -> str:
    if has_request_context() and current_user.is_authenticated:
        mode = str(getattr(current_user, "preferred_theme", "") or "").strip().lower()
        if mode in {"light", "dark"}:
            return mode
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
