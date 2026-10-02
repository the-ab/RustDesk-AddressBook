#!/bin/sh
set -eu

runtime_uid="${RAB_RUNTIME_UID:-10001}"
runtime_gid="${RAB_RUNTIME_GID:-10001}"

case "$runtime_uid:$runtime_gid" in
  *[!0-9:]*|:|*:|:* )
    echo "Ungültige RAB_RUNTIME_UID/RAB_RUNTIME_GID-Konfiguration." >&2
    exit 1
    ;;
esac

mkdir -p /data /data/certs /data/logs /data/ssh /backups

# Bind-Mounts bestehender Installationen gehören häufig root. Der kurzlebige
# Init-Dienst korrigiert ausschließlich die persistenten Anwendungsverzeichnisse.
chown -R "$runtime_uid:$runtime_gid" /data /backups
chmod 700 /data /data/certs /data/logs /data/ssh /backups

printf 'Persistente Verzeichnisse für UID/GID %s:%s vorbereitet.\n' "$runtime_uid" "$runtime_gid"
