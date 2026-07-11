import csv
import secrets
from io import StringIO
from urllib.parse import quote

from flask import abort, request, session


def csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def validate_csrf() -> None:
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
        if not sent or sent != session.get("csrf_token"):
            abort(400, description="Ungültiger CSRF-Token")


def rustdesk_link(rustdesk_id: str, password: str = "") -> str:
    clean_id = (rustdesk_id or "").strip()
    if password:
        return f"rustdesk://{quote(clean_id)}?password={quote(password)}"
    return f"rustdesk://{quote(clean_id)}"


def normalize_bool(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "ja", "on", "y"}


def parse_csv_upload(file_storage) -> list[dict]:
    raw = file_storage.read().decode("utf-8-sig")
    sample = raw[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(StringIO(raw), dialect=dialect)
    rows: list[dict] = []
    for row in reader:
        rows.append({(k or "").strip().lower(): (v or "").strip() for k, v in row.items()})
    return rows
