# RustDesk AddressBook Admin Guide

Diese Anleitung beschreibt Installation, Update, Bedienung, Import, Backup, Sicherheit und Fehlerdiagnose für Version `0.5.24-mobile-ui-docs-audit`.

## 1. Installation

```bash
cd /opt
wget https://dl.ab-xnet.de/rustdesk-addressbook-v0524.zip
unzip rustdesk-addressbook-v0524.zip
cd rustdesk-addressbook
chmod +x scripts/install.sh scripts/update.sh
./scripts/install.sh
```

Das Script fragt folgende Werte ab und speichert sie in `.env`:

- Zeitzone, Container-Name und Docker-Image-Name
- Daten- und Backup-Verzeichnis
- HTTPS-Port und Bind-Adresse
- optionaler HTTP-Port über `docker-compose.override.yml`
- Common Name und SubjectAltNames für das selbstsignierte Zertifikat
- Vertrauen in Reverse-Proxy-Header
- Download-Basis-URL für Updates
- optionaler read-only Mount der RustDesk-Serverdatenbank
- Brute-Force-Limit und Zeitfenster
- Intervall und Aufbewahrung der Auth-Logrotation

Beim erneuten Aufruf dienen vorhandene `.env`-Werte als Defaults. Standardmäßig ist die WebUI erreichbar unter:

```text
https://SERVER-IP:5443
```

HTTP ist standardmäßig aus. Ohne eigenes Zertifikat erstellt der Container ein selbstsigniertes Zertifikat; die Browserwarnung ist dann normal.

### 1.1 Manuelle Installation

```bash
cd /opt
wget https://dl.ab-xnet.de/rustdesk-addressbook-v0524.zip
unzip rustdesk-addressbook-v0524.zip
cd rustdesk-addressbook
cp .env.example .env
mkdir -p data backups updates
docker compose up -d --build
```

## 2. Update

### 2.1 Update-ZIP lokal ablegen

```bash
cd /opt/rustdesk-addressbook
wget https://dl.ab-xnet.de/rustdesk-addressbook-update-flat-v0524.zip -O updates/rustdesk-addressbook-update-flat-v0524.zip
./scripts/update.sh
```

### 2.2 Online prüfen

```bash
cd /opt/rustdesk-addressbook
./scripts/update.sh
```

Das Script prüft zuerst passende ZIP-Dateien in `updates/`. Ist dort nichts Neueres vorhanden, liest es `RAB_UPDATE_BASE_URL/latest.txt`, zeigt die Release-Notizen und fragt vor Download und Installation. Vor der Installation wird eine Sicherung angelegt:

```text
../rustdesk-addressbook-preupdate-YYYYmmdd-HHMMSS/
```

Gesichert werden `data/`, `backups/`, `.env`, `docker-compose.yml`, `docker-compose.override.yml` und `updates/`. Nach dem Update Browser mit `Strg+F5` neu laden.

### 2.3 latest.txt

```text
rustdesk-addressbook-update-flat-v0524.zip
[de]
- Deutsche Änderung
[en]
- English change
```

Alternativ unterstützt die App gleichnamige `.txt`-/`.md`-Dateien, `release-notes-v0524.txt` sowie sprachspezifische `.de.txt`-/`.en.txt`-Dateien. Die WebUI meldet Updates nur; installiert wird weiterhin über `./scripts/update.sh`.

### 2.4 Manueller Fallback

```bash
cd /opt/rustdesk-addressbook
docker compose down
cp -a data ../rustdesk-addressbook-data-backup
cp -a backups ../rustdesk-addressbook-backups-backup 2>/dev/null || true
unzip -o updates/rustdesk-addressbook-update-flat-v0524.zip
docker compose build --no-cache
docker compose up -d --force-recreate --remove-orphans
```

## 3. Ersteinrichtung

1. WebUI öffnen und Admin-Benutzer anlegen.
2. Unter **Einstellungen → Darstellung & Sprache** Theme und Sprache wählen.
3. Unter **Einstellungen → 2FA** TOTP aktivieren und Recovery-Codes offline sichern.
4. Unter **Einstellungen → Online-Status** hbbs Host/Port konfigurieren.
5. Ein verschlüsseltes `.rabfull`-Vollbackup erstellen.

## 4. Dashboard und Geräteansichten

Das Dashboard zeigt Geräteanzahl, Favoriten, Online-Geräte, Favoritenliste, zuletzt geänderte Geräte, Schnellsuche und Gruppen. Dashboard und Geräte-Seite unterstützen:

- Kartenansicht
- kompakte Listenansicht
- kleine Symbolansicht

Die gewählte Ansicht wird in der Sitzung gespeichert. Auf Smartphones werden Listenzeilen als beschriftete Karten dargestellt.

## 5. Geräteverwaltung

Felder:

- Name und RustDesk-ID, beide Pflicht
- verschlüsseltes RustDesk-Passwort
- Gruppe, Kunde, Standort
- Gerätetyp/Betriebssystem
- Tags und Notizen
- Favorit und manueller Online-Status

Funktionen:

- Anlegen, bearbeiten und löschen
- Suche in Name, ID, Kunde, Standort, Gerätetyp, Tags und Notizen
- Filter nach Gruppe, Favorit und Gerätetyp
- Sortierung: Online zuerst, Name, Favoriten oder zuletzt geändert
- `rustdesk://`-Direktlink; ein gespeichertes Passwort wird erst beim Klick entschlüsselt und in den RustDesk-Link eingefügt
- Passwort-Auge im Bearbeitungsformular lädt das gespeicherte Passwort nur nach ausdrücklichem Klick
- bleibt das Passwortfeld leer, bleibt das Passwort unverändert; über die Checkbox kann es gelöscht werden
- optionale Werte `None`/`null` werden beim Speichern als leer bereinigt

## 6. Gruppen

Gruppen besitzen Name, Farbe und Bootstrap-Icon. Sie können angelegt und direkt in der Liste bearbeitet werden. Beim Löschen einer Gruppe werden zugeordnete Geräte **nicht** gelöscht; nur deren Gruppenzuordnung wird entfernt.

## 7. Online-Status über hbbs

Der Live-Status nutzt RustDesk `OnlineRequest/OnlineResponse`. Üblicher Port ist TCP `21115`.

```bash
docker exec -it rustdesk-addressbook python - <<'PY'
import socket
socket.create_connection(("DEIN-RUSTDESK-SERVER", 21115), timeout=3).close()
print("TCP Verbindung OK")
PY
```

Konfigurierbar sind Quelle, Host, Port, Timeout, Batchgröße, Requester-ID sowie automatische Abfrage. Das Intervall kann frei als Minuten oder Stunden gesetzt werden. Die automatische Prüfung läuft nur, solange eine WebUI-Seite geöffnet ist. Scheitert eine Abfrage, bleiben vorhandene Online-Stati unverändert. Das letzte Ergebnis erscheint auf Dashboard, Geräte-Seite und in den Einstellungen.

Die hbbs-Nachrichten sind keine offiziell dokumentierte Web-API; nach RustDesk-Serverupdates erneut testen.

## 8. Import / Export

### 8.1 CSV-Import

Unterstützte Spalten:

```text
name,rustdesk_id,password,customer,location,os,tags,notes,favorite,online,group
```

Auch deutsche Alternativnamen für zentrale Spalten werden erkannt. Der CSV-Import:

- erstellt immer neue Geräte
- überspringt Zeilen ohne Name oder RustDesk-ID
- erkennt Komma, Semikolon oder Tabulator
- legt benannte Gruppen bei Bedarf automatisch an
- verschlüsselt importierte Passwörter

### 8.2 CSV-Export

- **Ohne Passwörter:** Standard und empfohlen
- **Mit Passwörtern:** entschlüsselt die Werte für die CSV; nur in einer geschützten Umgebung verwenden

### 8.3 RustDesk-DB per Upload

Akzeptiert `db_v2.sqlite3`, optional `db_v2.sqlite3-wal` und `db_v2.sqlite3-shm`, einzeln oder in einer ZIP. ZIP-Pfade werden sicher extrahiert. Der Import liest eine konsistente SQLite-Kopie, schreibt niemals in die RustDesk-DB und kann bestehende Geräte optional über die RustDesk-ID aktualisieren. Der Online-Status wird bewusst nicht aus der Server-DB übernommen.

### 8.4 Gemountete RustDesk-DB

```yaml
volumes:
  - /docker_data/rustdesk:/rustdesk-server:ro
environment:
  RUSTDESK_SERVER_DB: /rustdesk-server/db_v2.sqlite3
```

Die Importseite zeigt nur bei konfiguriertem Mount den Direktimport und die Diagnose. Die Diagnose prüft Pfad, Hauptdatei, WAL/SHM, SQLite-Header, Integrität, Tabellen, Peer-Anzahl und Beispieldatensätze.

## 9. RustDesk SSH-Import

Empfohlen bei getrennten Servern. Das Adressbuch ruft einen konsistenten SQLite-Snapshot über einen auf ein Exportkommando beschränkten SSH-Key ab.

### 9.1 RustDesk-Server vorbereiten

```bash
apt update
apt install sqlite3 openssh-server acl
adduser --disabled-password --gecos "" rab-import
```

### 9.2 Export-Script

```bash
cat > /usr/local/sbin/rab-rustdesk-db-export <<'EOSCRIPT'
#!/bin/bash
set -euo pipefail
DB="/docker_data/rustdesk/db_v2.sqlite3"
TMP="$(mktemp /tmp/rustdesk-db-export.XXXXXX.sqlite3)"
cleanup() { rm -f "$TMP"; }
trap cleanup EXIT
[ -r "$DB" ] || { echo "ERROR: RustDesk DB not readable: $DB" >&2; exit 1; }
sqlite3 "$DB" ".backup '$TMP'"
cat "$TMP"
EOSCRIPT
chmod 755 /usr/local/sbin/rab-rustdesk-db-export
```

### 9.3 Leserechte

```bash
setfacl -m u:rab-import:rx /docker_data
setfacl -m u:rab-import:rx /docker_data/rustdesk
setfacl -m u:rab-import:r /docker_data/rustdesk/db_v2.sqlite3
setfacl -m u:rab-import:r /docker_data/rustdesk/db_v2.sqlite3-wal 2>/dev/null || true
setfacl -m u:rab-import:r /docker_data/rustdesk/db_v2.sqlite3-shm 2>/dev/null || true
```

### 9.4 Key einschränken

In `authorized_keys`:

```text
restrict,no-pty,no-agent-forwarding,no-X11-forwarding,no-port-forwarding,command="/usr/local/sbin/rab-rustdesk-db-export" ssh-ed25519 AAAA...
```

Privaten Key im Adressbuch ablegen:

```bash
mkdir -p data/ssh
cp rustdesk_import_ed25519 data/ssh/
chmod 600 data/ssh/rustdesk_import_ed25519
```

WebUI-Pfad: `/data/ssh/rustdesk_import_ed25519`. Der eingebaute Test prüft Verbindung, Laufzeit, Bytes, SQLite-Header, `integrity_check`, Peer-Tabelle und Peer-Anzahl. Erst danach den Import starten. Host, Port, Benutzer, Key-Pfad und Host-Key-Datei werden in den Einstellungen gespeichert.

## 10. Backup / Restore

Backup-Arten:

- `.db`: unverschlüsselte SQLite-Sicherung
- `.rabenc`: AES-256-GCM-verschlüsselte Datenbank; Passwort mindestens 12 Zeichen
- `.rabfull`: verschlüsseltes Vollbackup; Passwort mindestens 16 Zeichen; enthält Datenbank, `config.json`, SSH-Keys, Zertifikate, Logs und Manifest

Vorhandene Backups können heruntergeladen, wiederhergestellt oder gelöscht werden. Restore ist auch per Upload von `.db`, `.sqlite`, `.sqlite3`, `.rabenc` und `.rabfull` möglich. Vor jedem Restore erzeugt die App automatisch ein unverschlüsseltes Sicherheitsbackup des bisherigen Datenbankstands.

Wichtig:

- `.rabenc` enthält nur die Datenbank und benötigt die dazugehörige `data/config.json`, um Gerätepasswörter zu entschlüsseln.
- `.rabfull` ist für Umzug/Totalausfall empfohlen.
- Nach `.rabfull`-Restore Container neu starten, damit `config.json` und Schlüssel neu geladen werden.
- Backup-Passwörter außerhalb des Servers aufbewahren.

## 11. Einstellungen

- **Darstellung & Sprache:** Light/Dark und Deutsch/Englisch
- **Admin-Konto:** Benutzername und Passwort jeweils nach Prüfung des aktuellen Passworts ändern
- **2FA:** Einrichtung vorbereiten, QR/Secret anzeigen, TOTP aktivieren, einmalige Recovery-Codes erzeugen, Codes erneuern oder 2FA mit Passwort plus TOTP/Recovery-Code deaktivieren
- **Gerätetypen:** ein Wert pro Zeile als Vorauswahl im Geräteformular
- **Online-Status:** hbbs-Parameter und automatisches Intervall
- **Brute-Force-Sperre:** 2–50 Fehlversuche, Zeitfenster 1–1440 Minuten; Änderung erfordert Admin-Passwort
- **Update-Check:** automatischer Check 1–168 Stunden; installiert keine Updates
- **Sicherheitshinweise:** Verschlüsselungs- und Backup-Hinweise

Auf Smartphone und Tablet werden die Kategorien als horizontal scrollbar bedienbare Navigation dargestellt.

## 12. Sicherheit

Die Sicherheitsseite zeigt bis zu 250 Login-/2FA-Ereignisse in einem auf ungefähr 10 sichtbare Zeilen begrenzten Scrollbereich und bietet den Download von `auth.log`.

Der Sicherheitsstatus prüft:

- 2FA-Abdeckung und vorhandene Recovery-Codes
- HMAC-Signaturen sensibler Benutzer-Sicherheitsfelder
- HttpOnly-/Secure-Cookie und HSTS
- Proxy-Header-Konfiguration
- Auth-Log und Dateirechte
- `config.json` und SQLite-Dateirechte
- unverschlüsselte/verschlüsselte Backups
- interne Brute-Force-Sperre
- Auth-Logrotation
- Update-Check, hbbs-Konfiguration und HTTPS-Endpunkt

Die SQLite-Datenbank ist nicht vollständig SQLCipher-verschlüsselt. Gerätepasswörter sind feldweise mit Fernet verschlüsselt; Benutzer-Sicherheitsfelder sind zusätzlich HMAC-signiert. Datenbank plus `config.json` gelten zusammen als sensibles Schlüsselmaterial.

### 12.1 Auth-Logrotation

```env
AUTH_LOG_ROTATE_DAYS=7
AUTH_LOG_ROTATE_KEEP=8
```

Diese Werte werden über Compose in den Container weitergereicht. Fehlversuche enthalten `RAB_AUTH_FAIL`.

### 12.2 fail2ban

```bash
cp contrib/fail2ban/filter.d/rustdesk-addressbook.conf /etc/fail2ban/filter.d/
cp contrib/fail2ban/jail.d/rustdesk-addressbook.local.example /etc/fail2ban/jail.d/rustdesk-addressbook.local
systemctl restart fail2ban
fail2ban-client status rustdesk-addressbook
```

`TRUST_PROXY_HEADERS=true` nur hinter einem vertrauenswürdigen Reverse Proxy setzen.

## 13. HTTPS

Eigene Zertifikate:

```bash
mkdir -p data/certs
cp fullchain.pem data/certs/addressbook.crt
cp privkey.pem data/certs/addressbook.key
chmod 600 data/certs/addressbook.key
docker compose up -d --force-recreate
```

Für öffentlichen Zugriff zusätzlich `SESSION_COOKIE_SECURE=true`, `APP_HSTS=true`, 2FA und restriktive Firewall-/Proxy-Regeln verwenden.

## 14. Mobile Bedienung

Alle Seiten sind für 320 px Smartphonebreite, größere Smartphones, Tablets und Desktop ausgelegt. Tabellen für Geräte, Backups, Sicherheitsereignisse und Diagnose wechseln mobil zu beschrifteten Karten. Lange Pfade, URLs, IDs und Logtexte brechen um. Kategorienavigation in Einstellungen, Import und Anleitung kann horizontal gescrollt werden. Das Hauptmenü wird über den mobilen Navbar-Schalter geöffnet.

## 15. Fehlerdiagnose

```bash
cd /opt/rustdesk-addressbook
docker compose ps
docker compose logs -f --tail=200
sqlite3 data/addressbook.db "PRAGMA integrity_check;"
docker exec -it rustdesk-addressbook grep -n "APP_VERSION" /app/app/config.py
docker exec -it rustdesk-addressbook ls -l /data/ssh/rustdesk_import_ed25519
docker exec -it rustdesk-addressbook python /app/scripts/reset_security_lockout.py
```

Bei Problemen:

- **Update:** ZIP-Struktur prüfen; Flat-Update muss Dateien direkt im Archivwurzelverzeichnis enthalten.
- **SSH:** zuerst WebUI-Test ausführen und Bytes, Header, Integrität und Peer-Anzahl prüfen.
- **hbbs:** TCP-Port `21115` aus dem Container testen.
- **RustDesk-DB:** Diagnose aufrufen und WAL/SHM sowie Peer-Tabelle prüfen.
- **Login-Sperre:** `reset_security_lockout.py` nur mit Serverzugriff ausführen.
- **Browserdarstellung nach Update:** `Strg+F5` oder Cache leeren.

## 16. Sprache

Kernoberfläche, Anleitung und Release-Historie sind Deutsch/Englisch. Technische Logs, importierte Daten und bereits gespeicherte historische Meldungen werden nicht verändert. Für englische Shell-Release-Notizen:

```bash
RAB_UPDATE_LANG=en ./scripts/update.sh
```
