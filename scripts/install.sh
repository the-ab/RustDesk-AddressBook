#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

is_tty=0
if [ -t 0 ]; then is_tty=1; fi


read_value_from_file() {
  local file="$1" key="$2"
  [ -f "$file" ] || return 1
  grep -E "^${key}=" "$file" | tail -n1 | cut -d= -f2- || true
}

saved_default() {
  local key="$1" fallback="$2" value=""
  # .env ist die aktive Installationskonfiguration und dient als Preset-Datei.
  value="$(read_value_from_file .env "$key" || true)"
  if [ -n "${value:-}" ]; then echo "$value"; return 0; fi
  echo "$fallback"
}

yesno_default() {
  local value="$1" fallback="$2"
  value="$(printf '%s' "${value:-$fallback}" | tr '[:upper:]' '[:lower:]')"
  case "$value" in
    true|1|yes|y|ja|j) echo "ja" ;;
    false|0|no|n|nein) echo "nein" ;;
    *) echo "$fallback" ;;
  esac
}

prompt() {
  local text="$1" default="$2" value
  if [ "$is_tty" -eq 1 ]; then
    read -r -p "$text [$default]: " value || true
    echo "${value:-$default}"
  else
    echo "$default"
  fi
}

prompt_yes_no() {
  local text="$1" default="$2" value default_l
  default_l="$(yesno_default "$default" "nein")"
  while true; do
    if [ "$is_tty" -eq 1 ]; then
      read -r -p "$text [$default_l]: " value || true
      value="${value:-$default_l}"
    else
      value="$default_l"
    fi
    case "$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]')" in
      y|yes|j|ja) echo "true"; return 0 ;;
      n|no|nein) echo "false"; return 0 ;;
      *) echo "Bitte ja/nein eingeben." >&2 ;;
    esac
  done
}

valid_port() {
  [[ "$1" =~ ^[0-9]+$ ]] && [ "$1" -ge 1 ] && [ "$1" -le 65535 ]
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "FEHLER: '$1' wurde nicht gefunden." >&2
    exit 1
  }
}

need_cmd docker
if docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE="docker-compose"
else
  echo "FEHLER: Docker Compose wurde nicht gefunden." >&2
  exit 1
fi

cat <<'BANNER'
RustDesk AddressBook Installer
------------------------------
HTTPS ist standardmäßig aktiv. HTTP ist standardmäßig deaktiviert.
Die WebUI erzeugt bei Bedarf automatisch ein selbstsigniertes Zertifikat.

Beim erneuten Aufruf werden die zuletzt gesetzten Werte aus .env gelesen und
als neue Default-Werte vorgeschlagen. Fehlt .env, ist es eine Erstinstallation.
BANNER

TZ_DEFAULT="$(saved_default TZ 'Europe/Berlin')"
CONTAINER_DEFAULT="$(saved_default RAB_CONTAINER_NAME 'rustdesk-addressbook')"
IMAGE_DEFAULT="$(saved_default RAB_IMAGE_NAME 'rustdesk-addressbook-v0529')"
DATA_DEFAULT="$(saved_default RAB_DATA_DIR './data')"
BACKUP_DEFAULT="$(saved_default RAB_BACKUP_DIR './backups')"
HTTPS_BIND_DEFAULT="$(saved_default RAB_HTTPS_BIND '0.0.0.0')"
HTTPS_PORT_DEFAULT="$(saved_default RAB_HTTPS_PUBLISH_PORT '5443')"
ENABLE_HTTP_DEFAULT="$(yesno_default "$(saved_default APP_ENABLE_HTTP 'false')" 'nein')"
HTTP_BIND_DEFAULT="$(saved_default RAB_HTTP_BIND '0.0.0.0')"
HTTP_PORT_DEFAULT="$(saved_default RAB_HTTP_PUBLISH_PORT '5055')"
COMMON_NAME_DEFAULT="$(saved_default HTTPS_COMMON_NAME 'rustdesk-addressbook.local')"
ALT_NAMES_DEFAULT="$(saved_default HTTPS_ALT_NAMES 'localhost,127.0.0.1,rustdesk-addressbook.local')"
HSTS_DEFAULT="$(yesno_default "$(saved_default APP_HSTS 'false')" 'nein')"
TRUST_PROXY_DEFAULT="$(yesno_default "$(saved_default TRUST_PROXY_HEADERS 'false')" 'nein')"
RUSTDESK_DB_DEFAULT="$(saved_default RUSTDESK_SERVER_DB '')"
RUSTDESK_MOUNT_DEFAULT="nein"
if [ -n "$RUSTDESK_DB_DEFAULT" ]; then RUSTDESK_MOUNT_DEFAULT="ja"; fi
RUSTDESK_DIR_DEFAULT="$(saved_default RAB_RUSTDESK_DIR '/docker_data/rustdesk')"
LOGIN_FAIL_LIMIT_DEFAULT="$(saved_default LOGIN_FAIL_LIMIT '5')"
LOGIN_FAIL_WINDOW_SECONDS_DEFAULT="$(saved_default LOGIN_FAIL_WINDOW_SECONDS '900')"
LOGIN_FAIL_WINDOW_MINUTES_DEFAULT="$((LOGIN_FAIL_WINDOW_SECONDS_DEFAULT / 60))"
AUTH_LOG_ROTATE_DAYS_DEFAULT="$(saved_default AUTH_LOG_ROTATE_DAYS '7')"
AUTH_LOG_ROTATE_KEEP_DEFAULT="$(saved_default AUTH_LOG_ROTATE_KEEP '8')"
UPDATE_BASE_URL_DEFAULT="$(saved_default RAB_UPDATE_BASE_URL 'https://dl.ab-xnet.de')"

TZ_VALUE="$(prompt 'Zeitzone' "$TZ_DEFAULT")"
CONTAINER_NAME="$(prompt 'Container-Name' "$CONTAINER_DEFAULT")"
IMAGE_NAME="$(prompt 'Docker-Image-Name' "$IMAGE_DEFAULT")"
DATA_DIR="$(prompt 'Datenverzeichnis auf dem Host' "$DATA_DEFAULT")"
BACKUP_DIR="$(prompt 'Backup-Verzeichnis auf dem Host' "$BACKUP_DEFAULT")"
HTTPS_BIND="$(prompt 'HTTPS Bind-Adresse' "$HTTPS_BIND_DEFAULT")"
HTTPS_PORT="$(prompt 'HTTPS Port auf dem Host' "$HTTPS_PORT_DEFAULT")"
while ! valid_port "$HTTPS_PORT"; do HTTPS_PORT="$(prompt 'Ungültig. HTTPS Port auf dem Host' "$HTTPS_PORT_DEFAULT")"; done

ENABLE_HTTP="$(prompt_yes_no 'HTTP zusätzlich aktivieren?' "$ENABLE_HTTP_DEFAULT")"
HTTP_BIND="$HTTP_BIND_DEFAULT"
HTTP_PORT="$HTTP_PORT_DEFAULT"
if [ "$ENABLE_HTTP" = "true" ]; then
  HTTP_BIND="$(prompt 'HTTP Bind-Adresse' "$HTTP_BIND_DEFAULT")"
  HTTP_PORT="$(prompt 'HTTP Port auf dem Host' "$HTTP_PORT_DEFAULT")"
  while ! valid_port "$HTTP_PORT"; do HTTP_PORT="$(prompt 'Ungültig. HTTP Port auf dem Host' "$HTTP_PORT_DEFAULT")"; done
fi

COMMON_NAME="$(prompt 'HTTPS Common Name' "$COMMON_NAME_DEFAULT")"
ALT_NAMES="$(prompt 'HTTPS SubjectAltNames' "$ALT_NAMES_DEFAULT")"
HSTS="$(prompt_yes_no 'HSTS aktivieren? Nur mit gültigem HTTPS-Zertifikat empfohlen' "$HSTS_DEFAULT")"
TRUST_PROXY="$(prompt_yes_no 'Reverse-Proxy Header vertrauen? Nur hinter vertrauenswürdigem Proxy aktivieren' "$TRUST_PROXY_DEFAULT")"
UPDATE_BASE_URL="$(prompt 'Update-Download-Basis-URL' "$UPDATE_BASE_URL_DEFAULT")"

ENABLE_DB_MOUNT="$(prompt_yes_no 'Optionalen read-only Zugriff auf RustDesk db_v2.sqlite3 aktivieren?' "$RUSTDESK_MOUNT_DEFAULT")"
RUSTDESK_DIR=""
RUSTDESK_SERVER_DB=""
if [ "$ENABLE_DB_MOUNT" = "true" ]; then
  RUSTDESK_DIR="$(prompt 'RustDesk-Datenverzeichnis auf dem Host' "$RUSTDESK_DIR_DEFAULT")"
  RUSTDESK_SERVER_DB="/rustdesk-server/db_v2.sqlite3"
fi

LOGIN_FAIL_LIMIT="$(prompt 'Brute-Force Fehlversuche bis Sperre' "$LOGIN_FAIL_LIMIT_DEFAULT")"
LOGIN_FAIL_WINDOW_MINUTES="$(prompt 'Brute-Force Zeitfenster in Minuten' "$LOGIN_FAIL_WINDOW_MINUTES_DEFAULT")"
LOGIN_FAIL_WINDOW_SECONDS=$((LOGIN_FAIL_WINDOW_MINUTES * 60))
AUTH_LOG_ROTATE_DAYS="$(prompt 'Auth-Logrotation in Tagen' "$AUTH_LOG_ROTATE_DAYS_DEFAULT")"
AUTH_LOG_ROTATE_KEEP="$(prompt 'Anzahl rotierter Auth-Logs aufbewahren' "$AUTH_LOG_ROTATE_KEEP_DEFAULT")"

mkdir -p "$DATA_DIR" "$BACKUP_DIR" "$(dirname "$DATA_DIR")"
mkdir -p "$DATA_DIR/certs" "$DATA_DIR/logs" "$DATA_DIR/ssh"
mkdir -p "$BACKUP_DIR" updates
chmod 700 "$DATA_DIR" || true
chmod 700 "$BACKUP_DIR" || true
chmod 700 "$DATA_DIR/ssh" || true
# Der Container läuft ab 0.5.27 als UID/GID 10001 statt als root.
if ! chown -R 10001:10001 "$DATA_DIR" "$BACKUP_DIR"; then
  echo "WARNUNG: Host-Verzeichnisse konnten nicht vorab auf UID/GID 10001 gesetzt werden." >&2
  echo "Der Docker-Init-Dienst versucht die Berechtigungen beim Start erneut zu korrigieren." >&2
fi

cat > .env <<ENVEOF
TZ=${TZ_VALUE}
RAB_CONTAINER_NAME=${CONTAINER_NAME}
RAB_IMAGE_NAME=${IMAGE_NAME}
RAB_DATA_DIR=${DATA_DIR}
RAB_BACKUP_DIR=${BACKUP_DIR}
RAB_HTTPS_BIND=${HTTPS_BIND}
RAB_HTTPS_PUBLISH_PORT=${HTTPS_PORT}
RAB_HTTP_BIND=${HTTP_BIND}
RAB_HTTP_PUBLISH_PORT=${HTTP_PORT}
RAB_UPDATE_BASE_URL=${UPDATE_BASE_URL}
RAB_RUSTDESK_DIR=${RUSTDESK_DIR}
APP_ENABLE_HTTPS=true
APP_ENABLE_HTTP=${ENABLE_HTTP}
HTTPS_CERT_FILE=/data/certs/addressbook.crt
HTTPS_KEY_FILE=/data/certs/addressbook.key
HTTPS_COMMON_NAME=${COMMON_NAME}
HTTPS_ALT_NAMES=${ALT_NAMES}
SESSION_COOKIE_SECURE=true
APP_HSTS=${HSTS}
TRUST_PROXY_HEADERS=${TRUST_PROXY}
LOGIN_FAIL_LIMIT=${LOGIN_FAIL_LIMIT}
LOGIN_FAIL_WINDOW_SECONDS=${LOGIN_FAIL_WINDOW_SECONDS}
AUTH_LOG_ROTATE_DAYS=${AUTH_LOG_ROTATE_DAYS}
AUTH_LOG_ROTATE_KEEP=${AUTH_LOG_ROTATE_KEEP}
USER_SIGNATURE_POLICY=strict
AUTH_EVENT_RETENTION_DAYS=90
AUTH_EVENT_MAX_ROWS=50000
SENSITIVE_ACTION_REAUTH_SECONDS=1800
FULL_BACKUP_MAX_MEMBERS=5000
FULL_BACKUP_MAX_TOTAL_BYTES=536870912
FULL_BACKUP_MAX_FILE_BYTES=134217728
OIDC_ALLOW_PRIVATE_ISSUER=false
RAB_ALLOW_UNSIGNED_LOCAL_UPDATES=false
RUSTDESK_SERVER_DB=${RUSTDESK_SERVER_DB}
ENVEOF


cat > docker-compose.override.yml <<OVERRIDE
services:
  rustdesk-addressbook:
    environment: {}
OVERRIDE

if [ "$ENABLE_HTTP" = "true" ]; then
  cat >> docker-compose.override.yml <<OVERRIDE
    ports:
      - "${HTTP_BIND}:${HTTP_PORT}:5000"
OVERRIDE
fi

if [ "$ENABLE_DB_MOUNT" = "true" ]; then
  cat >> docker-compose.override.yml <<OVERRIDE
    volumes:
      - "${RUSTDESK_DIR}:/rustdesk-server:ro"
OVERRIDE
fi

cat <<SUMMARY

Konfiguration geschrieben:
  .env
  docker-compose.override.yml

Datenverzeichnis:  ${DATA_DIR}
Backupverzeichnis: ${BACKUP_DIR}
Docker-Image:      ${IMAGE_NAME}
Update-Ordner:     ./updates
Update-URL:        ${UPDATE_BASE_URL}
HTTPS:             https://${HTTPS_BIND}:${HTTPS_PORT}
HTTP:              ${ENABLE_HTTP}
RustDesk-DB-Mount: ${ENABLE_DB_MOUNT}
SUMMARY

START_NOW="$(prompt_yes_no 'Container jetzt bauen und starten?' 'ja')"
if [ "$START_NOW" = "true" ]; then
  $COMPOSE build --no-cache
  $COMPOSE up -d --force-recreate
  echo "Warte auf Container-Healthcheck ..."
  health=""
  for _ in $(seq 1 30); do
    health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$CONTAINER_NAME" 2>/dev/null || true)"
    case "$health" in
      healthy) break ;;
      unhealthy)
        echo "FEHLER: Container ist laut Healthcheck nicht funktionsfähig." >&2
        docker logs --tail 100 "$CONTAINER_NAME" >&2 || true
        exit 1
        ;;
    esac
    sleep 2
  done
  if [ "$health" != "healthy" ]; then
    echo "WARNUNG: Healthcheck wurde innerhalb des Prüfzeitraums nicht 'healthy' (Status: ${health:-unbekannt})." >&2
    docker logs --tail 50 "$CONTAINER_NAME" >&2 || true
  fi
  echo
  echo "Fertig. Öffne: https://SERVER-IP:${HTTPS_PORT}"
  echo
  SETUP_TOKEN_VALUE="$(docker exec "$CONTAINER_NAME" python -c 'import json; print(json.load(open("/data/config.json", encoding="utf-8"))["SETUP_TOKEN"])' 2>/dev/null || true)"
  if [ -n "$SETUP_TOKEN_VALUE" ]; then
    echo "Einmaliges Setup-Token für das erste Administratorkonto:"
    echo "  $SETUP_TOKEN_VALUE"
    echo "Das Token wird nur benötigt, solange noch kein Benutzerkonto existiert."
  else
    echo "Hinweis: Das Setup-Token konnte nicht automatisch ausgelesen werden."
    echo "Abruf: docker exec $CONTAINER_NAME python -c 'import json; print(json.load(open(\"/data/config.json\"))[\"SETUP_TOKEN\"])'"
  fi
fi
