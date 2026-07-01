from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def _san_entry(value: str):
    value = value.strip()
    if not value:
        return None
    try:
        return x509.IPAddress(ip_address(value))
    except ValueError:
        return x509.DNSName(value)


def main() -> None:
    cert_file = Path(os.environ.get("HTTPS_CERT_FILE", "/data/certs/addressbook.crt"))
    key_file = Path(os.environ.get("HTTPS_KEY_FILE", "/data/certs/addressbook.key"))
    cn = os.environ.get("HTTPS_COMMON_NAME", "rustdesk-addressbook.local").strip() or "rustdesk-addressbook.local"
    sans_raw = os.environ.get("HTTPS_ALT_NAMES", "localhost,127.0.0.1,rustdesk-addressbook.local")

    cert_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.parent.mkdir(parents=True, exist_ok=True)

    if cert_file.exists() and key_file.exists():
        return

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(timezone.utc)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, cn),
    ])

    san_entries = [_san_entry(cn)]
    san_entries.extend(_san_entry(item) for item in sans_raw.split(","))
    san_entries = [entry for entry in san_entries if entry is not None]

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=825))
        .add_extension(x509.SubjectAlternativeName(san_entries), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )

    key_file.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    cert_file.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_file.chmod(0o600)
    cert_file.chmod(0o644)


if __name__ == "__main__":
    main()
