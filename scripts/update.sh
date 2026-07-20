#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

COMPOSE=""
require_compose() {
  if docker compose version >/dev/null 2>&1; then
    COMPOSE="docker compose"
  elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE="docker-compose"
  else
    echo "FEHLER: Docker Compose wurde nicht gefunden." >&2
    return 1
  fi
}

CURRENT_VERSION_FILE="app/config.py"
UPDATES_DIR="updates"
UPDATE_PUBLIC_KEY="scripts/keys/update-signing-public-v1.pem"
mkdir -p "$UPDATES_DIR"

is_tty=0
if [ -t 0 ]; then is_tty=1; fi

usage() {
  cat <<'USAGE'
RustDesk AddressBook Update

Recommended:
  ./scripts/update.sh

Without parameters the script:
  1. checks updates/ for newer signed flat-update ZIPs;
  2. checks RAB_UPDATE_BASE_URL only when that variable is configured;
  3. shows release notes and asks before installation.

Manual local update:
  cp /path/to/rustdesk-addressbook-update-flat-v0530.zip* updates/
  ./scripts/update.sh

Direct ZIP paths remain supported:
  ./scripts/update.sh /path/to/rustdesk-addressbook-update-flat-v0530.zip

Optional online source:
  Set RAB_UPDATE_BASE_URL in .env to a trusted location containing latest.txt,
  the update ZIP, and its matching .zip.sha256 and .zip.sig files.

GitHub Releases example:
  RAB_UPDATE_BASE_URL=https://github.com/OWNER/REPOSITORY/releases/latest/download

Leaving RAB_UPDATE_BASE_URL empty disables online checks. Local signed updates
remain fully supported.
USAGE
}

prompt_yes_no() {
  local text="$1" default="$2" answer default_l prompt_suffix
  default_l="$(printf '%s' "$default" | tr '[:upper:]' '[:lower:]')"
  case "$default_l" in
    ja|j|yes|y|true|1) default_l="ja"; prompt_suffix="J/n" ;;
    *) default_l="nein"; prompt_suffix="j/N" ;;
  esac
  if [ "$is_tty" -ne 1 ]; then
    [ "$default_l" = "ja" ] && return 0 || return 1
  fi
  while true; do
    read -r -p "$text [$prompt_suffix]: " answer || true
    answer="${answer:-$default_l}"
    case "$(printf '%s' "$answer" | tr '[:upper:]' '[:lower:]')" in
      j|ja|y|yes) return 0 ;;
      n|nein|no) return 1 ;;
      *) echo "Bitte J oder N eingeben." ;;
    esac
  done
}

extract_version_number() {
  local input="$1"
  if [[ "$input" =~ v([0-9]{3,}) ]]; then
    echo "${BASH_REMATCH[1]}"
    return 0
  fi
  if [[ "$input" =~ ([0-9]+)\.([0-9]+)\.([0-9]+) ]]; then
    printf '%d%02d%02d\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}" "${BASH_REMATCH[3]}"
    return 0
  fi
  echo "000"
}

current_version_string() {
  if [ -f "$CURRENT_VERSION_FILE" ]; then
    sed -n 's/.*APP_VERSION *= *"\([^"]*\)".*/\1/p' "$CURRENT_VERSION_FILE" | head -n1
  else
    echo "0.0.0"
  fi
}

zip_version_string() {
  local zip="$1" cfg
  cfg="$(unzip -p "$zip" app/config.py 2>/dev/null || true)"
  if [ -n "$cfg" ]; then
    printf '%s\n' "$cfg" | sed -n 's/.*APP_VERSION *= *"\([^"]*\)".*/\1/p' | head -n1
  fi
}

find_latest_update_zip() {
  local latest="" latest_num="000" f n
  shopt -s nullglob
  for f in "$UPDATES_DIR"/rustdesk-addressbook-update-flat-v*.zip; do
    [ -f "$f" ] || continue
    n="$(extract_version_number "$(basename "$f")")"
    if (( 10#$n > 10#$latest_num )); then
      latest="$f"
      latest_num="$n"
    fi
  done
  shopt -u nullglob
  echo "$latest"
}

read_env_value() {
  local key="$1" default="$2" value=""
  if [ -f .env ]; then
    value="$(grep -E "^${key}=" .env | tail -n1 | cut -d= -f2- || true)"
    if [ -n "${value:-}" ]; then echo "$value"; return 0; fi
  fi
  echo "$default"
}

set_env_value() {
  local key="$1" value="$2"
  touch .env
  if grep -qE "^${key}=" .env; then
    sed -i "s|^${key}=.*|${key}=${value}|" .env
  else
    printf '\n%s=%s\n' "$key" "$value" >> .env
  fi
}

need_downloader() {
  if command -v curl >/dev/null 2>&1; then echo "curl"; return 0; fi
  if command -v wget >/dev/null 2>&1; then echo "wget"; return 0; fi
  echo "FEHLER: Für Online-Updates wird curl oder wget benötigt." >&2
  exit 1
}

fetch_url() {
  local url="$1" out="$2" dl
  dl="$(need_downloader)"
  if [ "$dl" = "curl" ]; then
    curl -fsSL --connect-timeout 10 --max-time 60 -o "$out" "$url"
  else
    wget -q -O "$out" "$url"
  fi
}

fetch_url_optional() {
  local url="$1" out="$2"
  fetch_url "$url" "$out" >/dev/null 2>&1
}

allow_unsigned_local_update() {
  local value
  value="$(read_env_value RAB_ALLOW_UNSIGNED_LOCAL_UPDATES 'false' | tr '[:upper:]' '[:lower:]')"
  case "$value" in true|1|yes|y|ja|j) return 0 ;; *) return 1 ;; esac
}

validate_update_zip_structure() {
  local zip="$1"
  python3 - "$zip" <<'PYZIP'
import stat, sys, zipfile
from pathlib import PurePosixPath
path = sys.argv[1]
with zipfile.ZipFile(path) as zf:
    infos = zf.infolist()
    if not infos or len(infos) > 20000:
        raise SystemExit("Update-ZIP ist leer oder enthält zu viele Einträge.")
    total = 0
    seen = set()
    for info in infos:
        name = info.filename.replace('\\', '/')
        parts = PurePosixPath(name).parts
        if not name or name.startswith('/') or '..' in parts or name in seen:
            raise SystemExit(f"Unsicherer oder doppelter ZIP-Pfad: {name}")
        seen.add(name)
        mode = (info.external_attr >> 16) & 0xFFFF
        if stat.S_ISLNK(mode):
            raise SystemExit(f"Symbolische Links sind in Update-ZIPs nicht erlaubt: {name}")
        total += max(0, info.file_size)
        if info.file_size > 256 * 1024 * 1024 or total > 1024 * 1024 * 1024:
            raise SystemExit("Update-ZIP überschreitet die zulässigen Entpackgrößen.")
PYZIP
}

verify_update_package() {
  local zip checksum_file signature_file
  zip="$1"
  checksum_file="${zip}.sha256"
  signature_file="${zip}.sig"
  if [ ! -s "$checksum_file" ] || [ ! -s "$signature_file" ]; then
    if allow_unsigned_local_update; then
      echo "WARNUNG: Unsigiertes lokales Update wurde ausdrücklich über RAB_ALLOW_UNSIGNED_LOCAL_UPDATES=true freigegeben." >&2
      if ! prompt_yes_no "Unsigiertes Update wirklich verwenden?" "nein"; then
        echo "Update abgebrochen." >&2
        return 1
      fi
      validate_update_zip_structure "$zip"
      return 0
    fi
    echo "FEHLER: Signaturdateien fehlen. Erwartet: ${checksum_file} und ${signature_file}" >&2
    echo "Unsigierte Updates sind standardmäßig gesperrt." >&2
    return 1
  fi
  command -v openssl >/dev/null 2>&1 || { echo "FEHLER: openssl wird für die Update-Signaturprüfung benötigt." >&2; return 1; }
  command -v sha256sum >/dev/null 2>&1 || { echo "FEHLER: sha256sum wurde nicht gefunden." >&2; return 1; }
  [ -s "$UPDATE_PUBLIC_KEY" ] || { echo "FEHLER: Öffentlicher Update-Schlüssel fehlt: $UPDATE_PUBLIC_KEY" >&2; return 1; }
  if ! openssl pkeyutl -verify -pubin -inkey "$UPDATE_PUBLIC_KEY" -rawin -in "$checksum_file" -sigfile "$signature_file" >/dev/null 2>&1; then
    echo "FEHLER: Die digitale Ed25519-Signatur des Update-Manifests ist ungültig." >&2
    return 1
  fi
  local expected filename actual
  expected="$(awk 'NR==1 {print $1}' "$checksum_file")"
  filename="$(awk 'NR==1 {print $2}' "$checksum_file" | sed 's/^\*//')"
  if ! [[ "$expected" =~ ^[0-9a-fA-F]{64}$ ]]; then
    echo "FEHLER: Ungültige SHA-256-Datei." >&2
    return 1
  fi
  if [ -n "$filename" ] && [ "$filename" != "$(basename "$zip")" ]; then
    echo "FEHLER: SHA-256-Datei gehört zu '$filename', nicht zu '$(basename "$zip")'." >&2
    return 1
  fi
  actual="$(sha256sum "$zip" | awk '{print $1}')"
  if [ "${actual,,}" != "${expected,,}" ]; then
    echo "FEHLER: SHA-256-Prüfsumme des Updatepakets stimmt nicht." >&2
    return 1
  fi
  validate_update_zip_structure "$zip"
  echo "Update-Signatur und SHA-256-Prüfsumme erfolgreich geprüft."
}

print_notes_file() {
  local file="$1" line printed=0 lang="${RAB_UPDATE_LANG:-de}" section="" use_line=1
  [ -s "$file" ] || return 1
  while IFS= read -r line || [ -n "$line" ]; do
    line="$(printf '%s' "$line" | tr -d '\r' | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"
    [ -z "$line" ] && continue
    [ "${line#\#}" != "$line" ] && continue
    case "$(printf '%s' "$line" | tr '[:upper:]' '[:lower:]')" in
      '[de]'|'de:'|'de') section='de'; continue;;
      '[en]'|'en:'|'en') section='en'; continue;;
    esac
    if printf '%s' "$line" | grep -Eiq '^(de|en)[[:space:]]*[:|-][[:space:]]+'; then
      prefix="$(printf '%s' "$line" | sed -E 's/^([Dd][Ee]|[Ee][Nn])[[:space:]]*[:|-].*/\1/' | tr '[:upper:]' '[:lower:]')"
      [ "$prefix" = "$lang" ] || continue
      line="$(printf '%s' "$line" | sed -E 's/^([Dd][Ee]|[Ee][Nn])[[:space:]]*[:|-][[:space:]]+//')"
    elif [ -n "$section" ] && [ "$section" != "$lang" ]; then
      continue
    fi
    line="$(printf '%s' "$line" | sed -E 's/^[-*•][[:space:]]+//; s/^[[:space:]]+//; s/[[:space:]]+$//')"
    [ -z "$line" ] && continue
    if [ "$printed" -eq 0 ]; then
      echo
      if [ "$lang" = "en" ]; then echo "Changes in the available version:"; else echo "Änderungen der verfügbaren Version:"; fi
      printed=1
    fi
    echo "  - $line"
  done < "$file"
  [ "$printed" -eq 1 ]
}

print_zip_release_notes() {
  local zip="$1" tmp
  tmp="$(mktemp)"
  if unzip -p "$zip" RELEASE-NOTES.txt > "$tmp" 2>/dev/null; then
    print_notes_file "$tmp" || true
  fi
  rm -f "$tmp"
}

print_online_release_notes() {
  local base="$1" file="$2" tmp stem version_tag candidate
  [ -n "$base" ] && [ -n "$file" ] || return 0
  tmp="$(mktemp -d)"

  if fetch_url_optional "${base%/}/latest.txt" "$tmp/latest.txt"; then
    awk -v target="$file" '
      BEGIN{found=0}
      /^[[:space:]]*#/ || /^[[:space:]]*$/ {next}
      found==0 { if ($1==target) {found=1; next} else {next} }
      found==1 {print}
    ' "$tmp/latest.txt" > "$tmp/notes.txt" || true
    if print_notes_file "$tmp/notes.txt"; then rm -rf "$tmp"; return 0; fi
  fi

  stem="${file%.zip}"
  version_tag=""
  if [[ "$file" =~ v([0-9]+) ]]; then version_tag="v${BASH_REMATCH[1]}"; fi
  for candidate in \
    "${base%/}/${stem}.${RAB_UPDATE_LANG:-de}.txt" \
    "${base%/}/${stem}.${RAB_UPDATE_LANG:-de}.md" \
    "${base%/}/${stem}.txt" \
    "${base%/}/${stem}.md" \
    "${base%/}/release-notes-${version_tag}.${RAB_UPDATE_LANG:-de}.txt" \
    "${base%/}/release-notes-${version_tag}.${RAB_UPDATE_LANG:-de}.md" \
    "${base%/}/release-notes-${version_tag}.txt" \
    "${base%/}/release-notes-${version_tag}.md" \
    "${base%/}/releases/${version_tag}.${RAB_UPDATE_LANG:-de}.txt" \
    "${base%/}/releases/${version_tag}.${RAB_UPDATE_LANG:-de}.md" \
    "${base%/}/releases/${version_tag}.txt" \
    "${base%/}/releases/${version_tag}.md"; do
    [ -n "$version_tag" ] || case "$candidate" in *release-notes-*|*/releases/*) continue;; esac
    if fetch_url_optional "$candidate" "$tmp/notes.txt"; then
      if print_notes_file "$tmp/notes.txt"; then rm -rf "$tmp"; return 0; fi
    fi
  done
  rm -rf "$tmp"
}

online_latest_file() {
  local base="$1" tmp txt_file result=""
  tmp="$(mktemp -d)"
  txt_file="$tmp/latest.txt"
  if fetch_url "${base%/}/latest.txt" "$txt_file" >/dev/null 2>&1; then
    result="$(grep -E 'rustdesk-addressbook-update-flat-v[0-9]+\.zip|^v[0-9]+' "$txt_file" | head -n1 | tr -d '\r' | awk '{print $1}')"
  fi
  rm -rf "$tmp"
  if [[ "$result" =~ ^v([0-9]+)$ ]]; then
    result="rustdesk-addressbook-update-flat-${result}.zip"
  fi
  echo "$result"
}

check_online_update() {
  local base latest file current_str current_num target_num
  base="$(read_env_value RAB_UPDATE_BASE_URL '')"
  current_str="$(current_version_string)"
  current_num="$(extract_version_number "$current_str")"
  if [ -z "${base//[[:space:]]/}" ]; then
    echo "STATUS=disabled"
    echo "MESSAGE=Online-Update-Prüfung ist deaktiviert, weil RAB_UPDATE_BASE_URL nicht gesetzt ist. Lokale signierte Updates bleiben verfügbar."
    echo "BASE="
    echo "CURRENT_STR=$current_str"
    echo "CURRENT_NUM=$current_num"
    echo "UPDATE_AVAILABLE=0"
    return 0
  fi
  latest="$(online_latest_file "$base")"
  if [ -z "$latest" ]; then
    echo "STATUS=manifest_missing"
    echo "MESSAGE=Kein gültiges Online-Manifest gefunden. Erwartet wird ${base%/}/latest.txt mit einer Update-ZIP in der ersten nicht-leeren Zeile."
    echo "BASE=$base"
    echo "CURRENT_STR=$current_str"
    echo "CURRENT_NUM=$current_num"
    return 0
  fi
  file="$(basename "$latest")"
  target_num="$(extract_version_number "$file")"
  echo "STATUS=ok"
  echo "BASE=$base"
  echo "FILE=$file"
  echo "URL=${base%/}/$file"
  echo "CURRENT_STR=$current_str"
  echo "CURRENT_NUM=$current_num"
  echo "TARGET_NUM=$target_num"
  if (( 10#$target_num > 10#$current_num )); then
    echo "UPDATE_AVAILABLE=1"
    echo "MESSAGE=Update verfügbar: $file"
  else
    echo "UPDATE_AVAILABLE=0"
    echo "MESSAGE=Kein Online-Update verfügbar. Installierte Version ist aktuell oder neuer."
  fi
}

value_from_check() {
  local key="$1" file="$2"
  grep -E "^${key}=" "$file" | tail -n1 | cut -d= -f2-
}

download_online_update_to_updates() {
  local info_file="$1" file url target tmp_dir
  file="$(value_from_check FILE "$info_file")"
  url="$(value_from_check URL "$info_file")"
  target="$UPDATES_DIR/$file"
  tmp_dir="$(mktemp -d "$UPDATES_DIR/.download.XXXXXX")"
  trap 'rm -rf "$tmp_dir"' RETURN
  echo "Lade signiertes Update herunter: $url"
  fetch_url "$url" "$tmp_dir/$file"
  fetch_url "${url}.sha256" "$tmp_dir/${file}.sha256"
  fetch_url "${url}.sig" "$tmp_dir/${file}.sig"
  verify_update_package "$tmp_dir/$file"
  mv "$tmp_dir/$file" "$target"
  mv "$tmp_dir/${file}.sha256" "${target}.sha256"
  mv "$tmp_dir/${file}.sig" "${target}.sig"
  rm -rf "$tmp_dir"
  trap - RETURN
  echo "Gespeichert und geprüft: $target"
  echo "$target"
}

remove_existing_container_if_needed() {
  local cname="$1"
  [ -n "$cname" ] || return 0
  local ids
  ids="$(docker ps -aq --filter "name=^/${cname}$" || true)"
  if [ -n "$ids" ]; then
    echo "Vorhandener Container mit Namen '${cname}' gefunden. Stoppe und entferne ihn vor dem Neuaufbau."
    docker rm -f $ids >/dev/null 2>&1 || true
  fi
}

remove_known_containers() {
  local configured default_name
  configured="$(read_env_value RAB_CONTAINER_NAME '')"
  default_name="rustdesk-addressbook"
  for name in "$configured" "$default_name"; do
    remove_existing_container_if_needed "$name"
  done
}

maybe_update_image_name() {
  local target_num="$1" current_image
  current_image="$(read_env_value RAB_IMAGE_NAME '')"
  if [ -z "$current_image" ]; then
    set_env_value RAB_IMAGE_NAME "rustdesk-addressbook-v${target_num}"
    echo "Docker-Image-Name gesetzt: rustdesk-addressbook-v${target_num}"
    return 0
  fi
  if [[ "$current_image" =~ ^rustdesk-addressbook-v[0-9]+$ ]]; then
    set_env_value RAB_IMAGE_NAME "rustdesk-addressbook-v${target_num}"
    echo "Docker-Image-Name aktualisiert: ${current_image} -> rustdesk-addressbook-v${target_num}"
  else
    echo "Benutzerdefinierter Docker-Image-Name bleibt erhalten: ${current_image}"
  fi
}

copy_if_exists() {
  local src="$1" dst="$2"
  if [ -e "$src" ]; then cp -a "$src" "$dst"; fi
}

perform_update() {
  local zip_file="$1" current_str current_num target_str target_num target_num_from_cfg ts backup_root
  if [ ! -f "$zip_file" ]; then
    echo "FEHLER: ZIP nicht gefunden: $zip_file" >&2
    exit 1
  fi
  verify_update_package "$zip_file" || exit 1

  current_str="$(current_version_string)"
  current_num="$(extract_version_number "$current_str")"
  target_str="$(zip_version_string "$zip_file")"
  target_num="$(extract_version_number "$(basename "$zip_file")")"
  if [ -n "$target_str" ]; then
    target_num_from_cfg="$(extract_version_number "$target_str")"
    if (( 10#$target_num_from_cfg > 0 )); then target_num="$target_num_from_cfg"; fi
  else
    target_str="$(basename "$zip_file")"
  fi

  cat <<INFO
Aktuelle Version: ${current_str} (${current_num})
Update-ZIP:       ${zip_file}
Zielversion:      ${target_str} (${target_num})
INFO

  print_zip_release_notes "$zip_file"

  if (( 10#$target_num <= 10#$current_num )); then
    echo "Kein Update nötig: Zielversion ist nicht neuer als die installierte Version."
    exit 0
  fi

  require_compose || exit 1

  if ! prompt_yes_no "Update jetzt installieren?" "ja"; then
    echo "Update abgebrochen. ZIP bleibt unverändert liegen: $zip_file"
    exit 0
  fi

  ts="$(date +%Y%m%d-%H%M%S)"
  backup_root="../rustdesk-addressbook-preupdate-${ts}"
  mkdir -p "$backup_root"

  copy_if_exists data "$backup_root/data"
  copy_if_exists backups "$backup_root/backups"
  copy_if_exists .env "$backup_root/.env"
  copy_if_exists install-config.env "$backup_root/install-config.env"
  copy_if_exists docker-compose.override.yml "$backup_root/docker-compose.override.yml"
  copy_if_exists docker-compose.yml "$backup_root/docker-compose.yml"
  copy_if_exists updates "$backup_root/updates"

  cat <<INFO
Pre-Update-Sicherung erstellt:
  ${backup_root}
INFO

  $COMPOSE down --remove-orphans || true
  remove_known_containers

  unzip -o "$zip_file"

  # Lokale Konfiguration wiederherstellen, falls die ZIP Defaults überschrieben hat.
  copy_if_exists "$backup_root/.env" .env
  copy_if_exists "$backup_root/docker-compose.override.yml" docker-compose.override.yml

  # Automatischen Image-Namen auf Zielversion aktualisieren, aber benutzerdefinierte Namen nicht überschreiben.
  maybe_update_image_name "$target_num"

  remove_known_containers

  data_dir="$(read_env_value RAB_DATA_DIR './data')"
  backup_dir="$(read_env_value RAB_BACKUP_DIR './backups')"
  mkdir -p "$data_dir" "$backup_dir"
  if ! chown -R 10001:10001 "$data_dir" "$backup_dir"; then
    echo "WARNUNG: Host-Verzeichnisse konnten nicht vorab auf UID/GID 10001 gesetzt werden." >&2
    echo "Der Docker-Init-Dienst übernimmt die Berechtigungskorrektur beim Start." >&2
  fi

  $COMPOSE build --no-cache
  $COMPOSE up -d --force-recreate --remove-orphans

  container_name="$(read_env_value RAB_CONTAINER_NAME 'rustdesk-addressbook')"
  echo "Warte auf Container-Healthcheck ..."
  health=""
  for _ in $(seq 1 30); do
    health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container_name" 2>/dev/null || true)"
    case "$health" in
      healthy) break ;;
      unhealthy)
        echo "FEHLER: Container ist laut Healthcheck nicht funktionsfähig." >&2
        docker logs --tail 100 "$container_name" >&2 || true
        exit 1
        ;;
    esac
    sleep 2
  done
  if [ "$health" != "healthy" ]; then
    echo "WARNUNG: Healthcheck wurde innerhalb des Prüfzeitraums nicht 'healthy' (Status: ${health:-unbekannt})." >&2
    docker logs --tail 50 "$container_name" >&2 || true
  fi

  echo
  echo "Update abgeschlossen auf: ${target_str}"
  echo "Sicherung liegt unter: ${backup_root}"
  echo "Browser danach mit Strg+F5 neu laden."
}

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then usage; exit 0; fi

if [ "${1:-}" = "--check-online" ]; then
  info="$(mktemp)"
  check_online_update > "$info"
  cat "$info" | sed -n 's/^MESSAGE=//p'
  if [ "$(value_from_check STATUS "$info")" = "ok" ]; then
    echo "Aktuelle Version: $(value_from_check CURRENT_STR "$info")"
    if [ "$(value_from_check UPDATE_AVAILABLE "$info")" = "1" ]; then
      echo "Verfügbare Datei: $(value_from_check FILE "$info")"
      echo "Download: $(value_from_check URL "$info")"
      print_online_release_notes "$(value_from_check BASE "$info")" "$(value_from_check FILE "$info")"
    fi
  fi
  rm -f "$info"
  exit 0
fi

ZIP_FILE="${1:-}"

if [ "${1:-}" = "--online" ] || [ "${1:-}" = "--download-online" ]; then
  info="$(mktemp)"
  check_online_update > "$info"
  cat "$info" | sed -n 's/^MESSAGE=//p'
  if [ "$(value_from_check UPDATE_AVAILABLE "$info")" != "1" ]; then
    rm -f "$info"
    exit 0
  fi
  print_online_release_notes "$(value_from_check BASE "$info")" "$(value_from_check FILE "$info")"
  ZIP_FILE="$(download_online_update_to_updates "$info" | tail -n1)"
  rm -f "$info"
fi

if [ -z "$ZIP_FILE" ]; then
  ZIP_FILE="$(find_latest_update_zip)"
  if [ -n "$ZIP_FILE" ]; then
    # Wenn eine lokale ZIP vorhanden ist, aber nicht neuer als installiert, prüfen wir trotzdem online.
    local_current="$(extract_version_number "$(current_version_string)")"
    local_target="$(extract_version_number "$(basename "$ZIP_FILE")")"
    if (( 10#$local_target <= 10#$local_current )); then
      ZIP_FILE=""
    fi
  fi
fi

if [ -z "$ZIP_FILE" ]; then
  info="$(mktemp)"
  check_online_update > "$info"
  message="$(value_from_check MESSAGE "$info")"
  echo "$message"
  if [ "$(value_from_check UPDATE_AVAILABLE "$info")" = "1" ]; then
    echo "Verfügbare Datei: $(value_from_check FILE "$info")"
    echo "Download: $(value_from_check URL "$info")"
    print_online_release_notes "$(value_from_check BASE "$info")" "$(value_from_check FILE "$info")"
    if prompt_yes_no "Update-ZIP jetzt herunterladen?" "ja"; then
      ZIP_FILE="$(download_online_update_to_updates "$info" | tail -n1)"
    else
      echo "Kein Download ausgeführt."
      rm -f "$info"
      exit 0
    fi
  else
    if [ "$(value_from_check STATUS "$info")" = "disabled" ]; then
      echo "Kein lokales neues Update gefunden."
    else
      echo "Kein lokales oder online verfügbares neues Update gefunden."
    fi
    rm -f "$info"
    exit 0
  fi
  rm -f "$info"
else
  case "$ZIP_FILE" in
    updates/*) ;;
    *) echo "Hinweis: Direkte ZIP-Pfade werden unterstützt. Empfohlen ist: ZIP nach updates/ kopieren und ./scripts/update.sh ohne Parameter starten." ;;
  esac
fi

perform_update "$ZIP_FILE"
