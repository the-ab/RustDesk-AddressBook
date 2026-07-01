#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if docker compose version >/dev/null 2>&1; then
  COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE="docker-compose"
else
  echo "FEHLER: Docker Compose wurde nicht gefunden." >&2
  exit 1
fi

CURRENT_VERSION_FILE="app/config.py"
UPDATES_DIR="updates"
mkdir -p "$UPDATES_DIR"

is_tty=0
if [ -t 0 ]; then is_tty=1; fi

usage() {
  cat <<'USAGE'
RustDesk AddressBook Update

Empfohlener Standard:
  ./scripts/update.sh

Ablauf ohne Parameter:
  1. Prüft zuerst updates/ auf lokale Flat-Update-ZIPs.
  2. Wenn lokal nichts Neues vorhanden ist, prüft es online per RAB_UPDATE_BASE_URL.
  3. Bei verfügbarem Online-Update fragt es, ob heruntergeladen und installiert werden soll.

Manuelles Update:
  wget https://dl.ab-xnet.de/rustdesk-addressbook-update-flat-v0516.zip -O updates/rustdesk-addressbook-update-flat-v0516.zip
  ./scripts/update.sh

Standard-Aufruf:
  ./scripts/update.sh

Das Script prüft zuerst lokale Update-ZIPs in updates/.
Wenn dort keine neuere Version liegt, wird automatisch online unter RAB_UPDATE_BASE_URL geprüft.
Bei verfügbarer Online-Version werden die Änderungen angezeigt und das Script fragt nach Download und Installation.

Manuelles Update bleibt möglich:
  cp rustdesk-addressbook-update-flat-v0516.zip updates/
  ./scripts/update.sh

Direkte ZIP-Pfade bleiben unterstützt:
  ./scripts/update.sh /pfad/rustdesk-addressbook-update-flat-v0516.zip

Online-Manifest unter RAB_UPDATE_BASE_URL:
  latest.txt  erste Zeile: rustdesk-addressbook-update-flat-v0516.zip
              Folgezeilen optional als Release-Notizen
Alternativ kann neben der ZIP eine Datei rustdesk-addressbook-update-flat-v0516.txt oder release-notes-v0516.txt liegen.
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

print_notes_file() {
  local file="$1" line printed=0
  [ -s "$file" ] || return 1
  while IFS= read -r line || [ -n "$line" ]; do
    line="$(printf '%s' "$line" | tr -d '\r' | sed -E 's/^[-*•][[:space:]]+//; s/^[[:space:]]+//; s/[[:space:]]+$//')"
    [ -z "$line" ] && continue
    [ "${line#\#}" != "$line" ] && continue
    if [ "$printed" -eq 0 ]; then
      echo
      echo "Änderungen der verfügbaren Version:"
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
    "${base%/}/${stem}.txt" \
    "${base%/}/${stem}.md" \
    "${base%/}/release-notes-${version_tag}.txt" \
    "${base%/}/release-notes-${version_tag}.md" \
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
  base="$(read_env_value RAB_UPDATE_BASE_URL 'https://dl.ab-xnet.de')"
  latest="$(online_latest_file "$base")"
  current_str="$(current_version_string)"
  current_num="$(extract_version_number "$current_str")"
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
  local info_file="$1" file url target
  file="$(value_from_check FILE "$info_file")"
  url="$(value_from_check URL "$info_file")"
  target="$UPDATES_DIR/$file"
  echo "Lade herunter: $url"
  fetch_url "$url" "$target"
  echo "Gespeichert: $target"
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

  $COMPOSE build --no-cache
  $COMPOSE up -d --force-recreate --remove-orphans

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
    echo "Kein lokales oder online verfügbares neues Update gefunden."
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
