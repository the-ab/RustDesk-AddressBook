# RustDesk AddressBook Admin Guide

Diese Anleitung beschreibt Installation, Update, Funktionen und die wichtigsten Kommandos für den Betrieb.

## 1. Installation

Empfohlen ist das interaktive Installationsscript. Die Komplettversion entpackt immer in den Ordner `rustdesk-addressbook/`:

```bash
cd /opt
wget https://dl.ab-xnet.de/rustdesk-addressbook-v0518.zip
unzip rustdesk-addressbook-v0518.zip
cd rustdesk-addressbook
chmod +x scripts/install.sh scripts/update.sh
./scripts/install.sh
```

Das Script fragt ab:

- Zeitzone
- Container-Name
- Docker-Image-Name
- Datenverzeichnis
- Backup-Verzeichnis
- HTTPS-Port und Bind-Adresse
- ob HTTP zusätzlich aktiviert werden soll
- HTTPS Common Name / SubjectAltNames
- ob Reverse-Proxy-Header vertraut werden soll
- Update-Download-Basis-URL, Standard: `https://dl.ab-xnet.de`
- ob read-only Zugriff auf eine lokale RustDesk-Serverdatenbank aktiviert werden soll
- Brute-Force-Sperrwerte

Die gesetzten Werte werden in `.env` gespeichert. Wenn `./scripts/install.sh` erneut ausgeführt wird, nutzt es die Werte aus `.env` als neue Default-Werte. Dadurch ist ein schnelles Neuaufsetzen oder Nachjustieren möglich.

Standard nach Installation:

```text
https://SERVER-IP:5443
```

HTTP ist standardmäßig deaktiviert. Wenn HTTP im Installationsscript aktiviert wird, erzeugt das Script eine passende `docker-compose.override.yml`.

### 1.1 Manuelle Installation

```bash
cd /opt
wget https://dl.ab-xnet.de/rustdesk-addressbook-v0518.zip
unzip rustdesk-addressbook-v0518.zip
cd rustdesk-addressbook
cp .env.example .env
mkdir -p data backups updates
docker compose up -d --build
```

## 2. Update

Es gibt zwei empfohlene Wege. In beiden Fällen wird am Ende nur das Update-Script ohne Zusatzparameter ausgeführt.

### 2.1 Update-ZIP manuell in `updates/` ablegen

```bash
cd /opt/rustdesk-addressbook
wget https://dl.ab-xnet.de/rustdesk-addressbook-update-flat-v0518.zip -O updates/rustdesk-addressbook-update-flat-v0518.zip
./scripts/update.sh
```

Das Script erkennt die höchste passende Version im Ordner `updates/` automatisch.

### 2.2 Automatischer Online-Check und Download

```bash
cd /opt/rustdesk-addressbook
./scripts/update.sh
```

Wenn lokal keine neuere ZIP vorhanden ist, prüft das Script automatisch online unter `RAB_UPDATE_BASE_URL`. Wird eine neue Version gefunden, zeigt es die Release-Notizen an und fragt:

1. ob die Update-ZIP heruntergeladen werden soll,
2. ob das Update anschließend installiert werden soll.

Die früheren Optionen `--check-online` und `--online` sind für den normalen Betrieb nicht mehr nötig. Der Standardaufruf erledigt die Prüfung automatisch.

### 2.3 Download-Server mit `latest.txt` vorbereiten

Minimale Variante:

```text
rustdesk-addressbook-update-flat-v0518.zip
```

Empfohlene Variante mit Änderungen für WebUI und Update-Script:

```text
rustdesk-addressbook-update-flat-v0518.zip
- Update-Check nutzt latest.txt ohne latest.json-Prüfung.
- Update-Script zeigt Änderungen vor Download und Installation.
- Ja/Nein-Abfragen nutzen [J/n] und [j/N].
```

Alternativ kann neben der ZIP eine separate Notizdatei liegen:

```text
rustdesk-addressbook-update-flat-v0518.txt
release-notes-v0518.txt
releases/v0518.txt
```


In der WebUI gibt es zusätzlich unter **Einstellungen → Update-Check** eine Anzeige, ob online eine neue Version verfügbar ist und welche Änderungen diese Version enthält. Installiert wird weiterhin über `./scripts/update.sh`.

Das Script erstellt vorher eine Sicherung neben dem Projektordner:

```text
../rustdesk-addressbook-preupdate-YYYYmmdd-HHMMSS/
```

Gesichert werden:

```text
data/
backups/
.env
docker-compose.yml
docker-compose.override.yml
updates/
```

Danach im Browser `Strg + F5` drücken.

### 2.4 Manueller Fallback

Nur falls das Script nicht nutzbar ist:

```bash
cd /opt/rustdesk-addressbook
docker compose down
cp -a data ../rustdesk-addressbook-data-backup
cp -a backups ../rustdesk-addressbook-backups-backup 2>/dev/null || true
unzip -o updates/rustdesk-addressbook-update-flat-v0518.zip
docker compose build --no-cache
docker compose up -d --force-recreate --remove-orphans
```

## 3. Ersteinrichtung

1. WebUI öffnen.
2. Admin-Benutzer und Passwort erstellen.
3. Unter **Einstellungen → 2FA** TOTP aktivieren.
4. Recovery-Codes offline speichern.
5. Unter **Einstellungen → Online-Status** hbbs konfigurieren.

## 4. Geräteverwaltung

Felder:

- Name
- RustDesk-ID
- Passwort
- Gruppe
- Kunde
- Standort
- Gerätetyp / Betriebssystem
- Tags
- Notizen
- Favorit
- Online-Status

Verbindung erfolgt per `rustdesk://`-Link. Gespeicherte Passwörter werden nicht direkt im HTML-Link angezeigt.

## 5. Gruppen

Gruppen haben Name, Farbe und Icon. Icons werden per Auswahlfeld mit Vorschau gesetzt. Bestehende Gruppen können bearbeitet werden.

## 6. hbbs Live-Status

Einstellungen:

```text
Statusquelle: hbbs Live-Abfrage
hbbs Host: RUSTDESK-SERVER-IP oder DNS
hbbs Port: 21115
Timeout: 3
Batchgröße: 50
```

Test aus dem Container:

```bash
docker exec -it rustdesk-addressbook python - <<'PY'
import socket
host = "DEIN-RUSTDESK-SERVER"
port = 21115
s = socket.create_connection((host, port), timeout=3)
print("TCP Verbindung OK")
s.close()
PY
```

## 7. Import / Export

### CSV-Import

Unterstützte Spalten:

```text
name,rustdesk_id,password,customer,location,os,tags,notes,favorite,online,group
```

### CSV-Export

- Export ohne Passwörter: empfohlen.
- Export mit Passwörtern: nur in geschützter Umgebung verwenden.

### RustDesk-DB Upload

Akzeptiert:

```text
db_v2.sqlite3
db_v2.sqlite3-wal
db_v2.sqlite3-shm
```

Oder ZIP mit diesen Dateien.

### Gemountete RustDesk-DB

Diese Option kann direkt im Installationsscript aktiviert werden:

```bash
./scripts/install.sh
```

Bei der Frage

```text
Optionalen read-only Zugriff auf RustDesk db_v2.sqlite3 aktivieren?
```

mit `ja` antworten und das RustDesk-Datenverzeichnis angeben, zum Beispiel:

```text
/docker_data/rustdesk
```

Manuell entspricht das ungefähr:

```yaml
environment:
  RUSTDESK_SERVER_DB: /rustdesk-server/db_v2.sqlite3
volumes:
  - /docker_data/rustdesk:/rustdesk-server:ro
```

## 8. RustDesk SSH-Import

Der SSH-Import ist empfohlen, wenn RustDesk-Server und AddressBook auf getrennten Servern laufen.

### 8.1 RustDesk-Server vorbereiten

```bash
apt update
apt install sqlite3 openssh-server acl
adduser --disabled-password --gecos "" rab-import
```

### 8.2 Export-Script erstellen

```bash
cat > /usr/local/sbin/rab-rustdesk-db-export <<'EOSCRIPT'
#!/bin/bash
set -euo pipefail

DB="/docker_data/rustdesk/db_v2.sqlite3"
TMP="$(mktemp /tmp/rustdesk-db-export.XXXXXX.sqlite3)"

cleanup() {
  rm -f "$TMP"
}
trap cleanup EXIT

if [ ! -r "$DB" ]; then
  echo "ERROR: RustDesk DB not readable: $DB" >&2
  exit 1
fi

sqlite3 "$DB" ".backup '$TMP'"
cat "$TMP"
EOSCRIPT
chmod 755 /usr/local/sbin/rab-rustdesk-db-export
```

### 8.3 Rechte setzen

```bash
setfacl -m u:rab-import:rx /docker_data
setfacl -m u:rab-import:rx /docker_data/rustdesk
setfacl -m u:rab-import:r /docker_data/rustdesk/db_v2.sqlite3
setfacl -m u:rab-import:r /docker_data/rustdesk/db_v2.sqlite3-wal 2>/dev/null || true
setfacl -m u:rab-import:r /docker_data/rustdesk/db_v2.sqlite3-shm 2>/dev/null || true
```

### 8.4 SSH-Key erzeugen

Auf dem AddressBook-Server:

```bash
cd /opt/rustdesk-addressbook
mkdir -p data/ssh
ssh-keygen -t ed25519 -f data/ssh/rustdesk_import_ed25519 -N ""
chmod 600 data/ssh/rustdesk_import_ed25519
cat data/ssh/rustdesk_import_ed25519.pub
```

### 8.5 Public Key einschränken

Auf dem RustDesk-Server:

```bash
mkdir -p /home/rab-import/.ssh
nano /home/rab-import/.ssh/authorized_keys
```

Zeile eintragen:

```text
restrict,no-pty,no-agent-forwarding,no-X11-forwarding,no-port-forwarding,command="/usr/local/sbin/rab-rustdesk-db-export" ssh-ed25519 AAAA...
```

Rechte:

```bash
chown -R rab-import:rab-import /home/rab-import/.ssh
chmod 700 /home/rab-import/.ssh
chmod 600 /home/rab-import/.ssh/authorized_keys
```

### 8.6 Manueller Test

```bash
ssh -T \
  -i ./data/ssh/rustdesk_import_ed25519 \
  -o IdentitiesOnly=yes \
  -o BatchMode=yes \
  rab-import@RUSTDESK-SERVER-IP \
  > /tmp/rustdesk-db-snapshot.sqlite3

file /tmp/rustdesk-db-snapshot.sqlite3
sqlite3 /tmp/rustdesk-db-snapshot.sqlite3 ".tables"
sqlite3 /tmp/rustdesk-db-snapshot.sqlite3 "PRAGMA integrity_check;"
sqlite3 /tmp/rustdesk-db-snapshot.sqlite3 "SELECT COUNT(*) FROM peer;"
```

Erwartet:

```text
peer
ok
ANZAHL
```

### 8.7 WebUI konfigurieren

Unter **Import / Export → RustDesk SSH-Import**:

```text
SSH Host: RUSTDESK-SERVER-IP
SSH Port: 22
SSH Benutzer: rab-import
Private-Key-Pfad: /data/ssh/rustdesk_import_ed25519
Remote-Kommando: leer lassen, wenn forced command aktiv ist
```

Danach zuerst **SSH-Übertragung testen**, dann **Per SSH importieren**.

## 9. Backups

Backup in der WebUI:

- Normales SQLite-Backup nur der Datenbank
- Verschlüsseltes `.rabenc`-Backup nur der Datenbank
- Verschlüsseltes `.rabfull`-Vollbackup mit:
  - `data/addressbook.db`
  - `data/config.json`
  - `data/ssh/`
  - `data/certs/`
  - `data/logs/`
- Restore vorhandener Backups
- Restore per Upload
- Löschen alter Backups

Empfehlung: Für Serverumzug, Totalausfall oder externe Ablage immer `.rabfull` verwenden. Das Vollbackup enthält Schlüsselmaterial und wird deshalb ausschließlich verschlüsselt erzeugt. Nach Restore eines `.rabfull`-Backups den Container neu starten, damit `config.json` neu geladen wird.

Hostseitige Sicherung:

```bash
cd /opt
borg create /backup/rustdesk-addressbook::rab-$(date +%F-%H%M) rustdesk-addressbook/data rustdesk-addressbook/backups
```

Wichtig:

```text
data/addressbook.db
data/config.json
backups/
```

## 10. HTTPS

Selbstsigniertes Zertifikat wird automatisch erstellt. Eigene Zertifikate:

```bash
mkdir -p data/certs
cp fullchain.pem data/certs/addressbook.crt
cp privkey.pem data/certs/addressbook.key
chmod 600 data/certs/addressbook.key
docker compose up -d --force-recreate
```

## 11. Sicherheit

### 2FA

Unter **Einstellungen → 2FA** aktivieren. Recovery-Codes offline sichern.

### Brute-Force-Sperre

Unter **Einstellungen → Brute-Force-Sperre** konfigurierbar:

- Fehlversuche
- Zeitraum

### Auth-Log

```bash
tail -f /opt/rustdesk-addressbook/data/logs/auth.log
```

Fehlversuche enthalten:

```text
RAB_AUTH_FAIL
```

## 12. fail2ban

```bash
cp contrib/fail2ban/filter.d/rustdesk-addressbook.conf /etc/fail2ban/filter.d/
cp contrib/fail2ban/jail.d/rustdesk-addressbook.local.example /etc/fail2ban/jail.d/rustdesk-addressbook.local
systemctl restart fail2ban
fail2ban-client status rustdesk-addressbook
```

Wenn die App hinter einem Reverse Proxy läuft, `TRUST_PROXY_HEADERS=true` nur dann setzen, wenn der Proxy vertrauenswürdig ist.

## 13. Fehlerdiagnose

Containerlogs:

```bash
docker compose logs -f --tail=200
```

Datenbankintegrität:

```bash
sqlite3 data/addressbook.db "PRAGMA integrity_check;"
```

Version:

```bash
docker exec -it rustdesk-addressbook grep -n "APP_VERSION" /app/app/config.py
```

SSH-Key im Container:

```bash
docker exec -it rustdesk-addressbook ls -l /data/ssh/rustdesk_import_ed25519
```

hbbs-Port:

```bash
docker exec -it rustdesk-addressbook python - <<'PY'
import socket
socket.create_connection(("DEIN-RUSTDESK-SERVER", 21115), timeout=3).close()
print("OK")
PY
```

## Sprache und Einstellungen

Ab Version 0.5.18 kann die WebUI zwischen Deutsch und Englisch umgeschaltet werden.
Die Auswahl befindet sich unter **Einstellungen → Darstellung & Sprache**.

Der Einstellungsbereich ist in eine linke Navigation und einen rechten Detailbereich aufgeteilt.
Dadurch sind Admin-Konto, 2FA, Online-Status, Update-Check und weitere Optionen schneller erreichbar.

Hinweis: Die Kernoberfläche ist übersetzt. Technische Logs, Import-Inhalte und einige Diagnosemeldungen bleiben bewusst unverändert oder deutschsprachig, damit bestehende Hinweise und Logs kompatibel bleiben.

