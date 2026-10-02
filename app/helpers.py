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
    try:
        raw = file_storage.read().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV-Datei muss als UTF-8 gespeichert sein.") from exc
    try:
        dialect = csv.Sniffer().sniff(raw[:2048], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(StringIO(raw), dialect=dialect, strict=True)
    try:
        headers = [(value or "").strip().lower() for value in (reader.fieldnames or [])]
        if not headers or any(not value for value in headers) or len(set(headers)) != len(headers):
            raise ValueError("CSV-Kopfzeile fehlt oder enthält leere/doppelte Spaltennamen.")
        if not set(headers) & {"name", "gerät", "device"} or not set(headers) & {"rustdesk_id", "rustdesk-id", "id"}:
            raise ValueError("CSV benötigt eine Name- und eine RustDesk-ID-Spalte.")
        reader.fieldnames = headers
        rows = []
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"CSV-Zeile {reader.line_num}: Spaltenzahl stimmt nicht mit der Kopfzeile überein.")
            rows.append({key: value.strip() for key, value in row.items()})
        return rows
    except csv.Error as exc:
        raise ValueError(f"CSV konnte nicht gelesen werden (Zeile {reader.line_num}).") from exc
