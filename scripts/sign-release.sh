#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Verwendung: $0 /sicherer/pfad/update-signing-private.pem DATEI.zip [weitere.zip ...]" >&2
  exit 1
fi

PRIVATE_KEY="$1"
shift
[ -s "$PRIVATE_KEY" ] || { echo "Privater Signaturschlüssel fehlt: $PRIVATE_KEY" >&2; exit 1; }
command -v openssl >/dev/null 2>&1 || { echo "openssl wurde nicht gefunden." >&2; exit 1; }
command -v sha256sum >/dev/null 2>&1 || { echo "sha256sum wurde nicht gefunden." >&2; exit 1; }

for archive in "$@"; do
  [ -s "$archive" ] || { echo "Datei fehlt: $archive" >&2; exit 1; }
  checksum_file="${archive}.sha256"
  signature_file="${archive}.sig"
  (cd "$(dirname "$archive")" && sha256sum "$(basename "$archive")") > "$checksum_file"
  openssl pkeyutl -sign -inkey "$PRIVATE_KEY" -rawin -in "$checksum_file" -out "$signature_file"
  chmod 0644 "$checksum_file" "$signature_file"
  echo "Signiert: $archive"
done
