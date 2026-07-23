# Community-Adressbuch für RustDesk – Administratorhandbuch

> Dies ist die deutsche Fassung. Die englische Standardfassung steht in [`ADMIN-GUIDE.md`](ADMIN-GUIDE.md).

> **Unabhängiges Projekt:** Dieses Community-Projekt ist nicht mit RustDesk oder Purslane Ltd. verbunden und wird von diesen weder unterstützt, gesponsert noch gepflegt. RustDesk ist eine Marke des jeweiligen Rechteinhabers.

Diese Anleitung beschreibt Installation, Update, Bedienung, Import, Backup, Sicherheit und Fehlerdiagnose für Version `0.5.33-v0533-update-cleanup-installed-archive`.

## 1. Installation

```bash
cd /opt
unzip /pfad/rustdesk-addressbook-v0533.zip
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
unzip /pfad/rustdesk-addressbook-v0533.zip
cd rustdesk-addressbook
cp .env.example .env
mkdir -p data backups updates
chown -R 10001:10001 data backups
docker compose up -d --build
```

## 2. Update

### 2.1 Update-ZIP lokal ablegen

```bash
cd /opt/rustdesk-addressbook
cp /pfad/rustdesk-addressbook-update-flat-v0533.zip* updates/
./scripts/update.sh
```

### 2.2 Online prüfen

```bash
cd /opt/rustdesk-addressbook
./scripts/update.sh
```

Das Script prüft zuerst passende ZIP-Dateien in `updates/`. Vor dem Entpacken müssen eine gültige Ed25519-Signatur und die signierte SHA-256-Prüfsumme vorliegen. Online-Prüfungen verwenden standardmäßig `https://github.com/the-ab/RustDesk-AddressBook/releases/latest/download`. Mit `RAB_UPDATE_BASE_URL=disabled` werden sie ausdrücklich abgeschaltet; lokale signierte Updates bleiben weiterhin nutzbar. Vor der Installation wird eine Sicherung angelegt:

```text
../rustdesk-addressbook-preupdate-YYYYmmdd-HHMMSS/
```

Gesichert werden `data/`, `backups/`, `.env`, `docker-compose.yml`, `docker-compose.override.yml` und `updates/`. Nach einem bestätigten erfolgreichen Healthcheck werden die installierte ZIP, die SHA-256-Datei und die Signatur nach `updates/installed/` verschoben. Bei Fehlern oder nicht eindeutig bestätigtem Health-Status bleiben sie in `updates/`. Nach dem Update Browser mit `Strg+F5` neu laden.

### 2.3 latest.txt

```text
rustdesk-addressbook-update-flat-v0533.zip
[de]
- Deutsche Änderung
[en]
- English change
```

Beim GitHub-Release müssen `latest.txt`, die darin genannte ZIP sowie die gleichnamigen Dateien `.zip.sha256` und `.zip.sig` gemeinsam als Release Assets hochgeladen werden. Der feste Pfad `/releases/latest/download` wird von GitHub auf das neueste veröffentlichte Release weitergeleitet. Neben der ZIP müssen an jeder benutzerdefinierten Updatequelle ebenfalls die gleichnamigen Dateien `.zip.sha256` und `.zip.sig` liegen. Alternativ unterstützt die App gleichnamige `.txt`-/`.md`-Dateien, `release-notes-v0533.txt` sowie sprachspezifische `.de.txt`-/`.en.txt`-Dateien. Die WebUI meldet Updates nur; installiert wird weiterhin über `./scripts/update.sh`. Der private Signaturschlüssel darf nicht auf dem Downloadserver oder im Projektverzeichnis gespeichert werden.

### 2.4 Manueller Fallback

Der direkte manuelle Entpackweg umgeht die Sicherheitslogik des Updaters und ist deshalb nicht empfohlen. Nutze auch bei lokal übertragenen Dateien bevorzugt:

```bash
cd /opt/rustdesk-addressbook
cp /sicherer/pfad/rustdesk-addressbook-update-flat-v0533.zip* updates/
./scripts/update.sh
```

Nur für eine kontrollierte Wiederherstellung mit bereits unabhängig geprüften Dateien kann ein Administrator den Container manuell stoppen, Daten sichern und das Archiv entpacken. Unsignierte Updates lassen sich ausschließlich interaktiv und nach explizitem Setzen von `RAB_ALLOW_UNSIGNED_LOCAL_UPDATES=true` freigeben; für automatisierte Abläufe bleiben sie gesperrt.

## 3. Ersteinrichtung

1. WebUI öffnen, das vom Installationsscript ausgegebene einmalige Setup-Token eingeben und den ersten lokalen Administrator anlegen. Alternativer Abruf: `docker exec rustdesk-addressbook python -c 'import json; print(json.load(open("/data/config.json"))["SETUP_TOKEN"])'`.
2. Unter **Konto** TOTP aktivieren und Recovery-Codes offline sichern.
3. Unter **Mein Konto → Darstellung & Sprache** Theme und Sprache individuell für das eigene Konto wählen.
4. Unter **Einstellungen → Online-Status** hbbs Host/Port konfigurieren.
5. Weitere lokale oder OIDC-Benutzer unter **Benutzer** anlegen und Gruppen zuweisen.
6. OIDC optional unter **Einstellungen → OpenID Connect** konfigurieren.
7. Ein verschlüsseltes `.rabfull`-Vollbackup erstellen.

Bei einem Update von 0.5.24 oder älter wird das vorhandene Benutzerkonto automatisch als aktiver lokaler Administrator übernommen. Beim Update von 0.5.26 wird die vorhandene alte Signatur vor der Migration geprüft; eine bereits manipulierte Rolle oder Identität wird nicht neu signiert und bleibt für die Anmeldung gesperrt. Mindestens ein aktiver lokaler Administrator muss als Notfallzugang bestehen bleiben.

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
- `rustdesk://`-Direktlink; ein gespeichertes Passwort wird erst beim Klick entschlüsselt und in den RustDesk-Link eingefügt. Nach Ablauf des konfigurierten Sicherheitsfensters ist eine erneute lokale oder OIDC-Anmeldung erforderlich
- Passwort-Auge im Bearbeitungsformular lädt das gespeicherte Passwort nur nach ausdrücklichem Klick; Passwortabruf, Passwort-CSV-Export und Verbindungsstart werden im Auditlog erfasst
- bleibt das Passwortfeld leer, bleibt das Passwort unverändert; über die Checkbox kann es gelöscht werden
- optionale Werte `None`/`null` werden beim Speichern als leer bereinigt

## 6. Gruppen

Gruppen besitzen Name, Farbe und Bootstrap-Icon. Sie können angelegt und direkt in der Liste bearbeitet werden. Beim Löschen einer Gruppe werden zugeordnete Geräte **nicht** gelöscht; nur deren Gruppenzuordnung wird entfernt. Die Gruppe wird dabei ebenfalls aus allen Benutzerzuweisungen entfernt.

### 6.1 Benutzer und Rollen

Unter **Benutzer** verwalten Administratoren lokale und OIDC-Konten:

- **Administrator:** sieht alle Geräte und Gruppen, einschließlich ungruppierter Geräte, und besitzt Zugriff auf alle Verwaltungsbereiche.
- **Benutzer:** sieht ausschließlich Geräte aus den ihm zugewiesenen Gruppen. Er darf diese Geräte suchen, anzeigen, verbinden und gespeicherte Gerätepasswörter nach ausdrücklichem Klick abrufen.
- Normale Benutzer dürfen keine Geräte, Gruppen oder Benutzer anlegen, bearbeiten oder löschen. Import/Export, Backups, Sicherheit, Einstellungen, Statusänderungen und Update-Funktionen sind serverseitig gesperrt.
- Geräte ohne Gruppe sind ausschließlich für Administratoren sichtbar.
- Ein Benutzer kann mehreren Gruppen zugeordnet werden; eine Gruppe kann mehreren Benutzern zugeordnet werden.
- Konten können deaktiviert werden. Deaktivierte Benutzer können sich nicht anmelden; aktive Sitzungen werden beim nächsten geschützten Aufruf beendet.
- Der aktuell angemeldete Administrator kann sich nicht selbst löschen, deaktivieren oder zur Benutzerrolle herabstufen. Der letzte aktive lokale Administrator ist zusätzlich geschützt.

Jeder Benutzer kann unter **Mein Konto** seine Darstellung und Sprache unabhängig von anderen Konten festlegen. Lokale Benutzer verwalten dort zusätzlich Passwort und TOTP-2FA. Für OIDC-Benutzer werden Passwort und MFA beim Identitätsanbieter verwaltet; Darstellung und Sprache bleiben trotzdem lokal pro Konto einstellbar.

### 6.2 OpenID Connect / OIDC

OIDC wird unter **Einstellungen → OpenID Connect** eingerichtet. Unterstützt werden Discovery und der Authorization-Code-Flow mit PKCE. Benötigt werden:

- Issuer-URL des Identitätsanbieters
- Client-ID und Client-Secret
- die in der WebUI angezeigte Redirect-URI, die exakt beim Provider hinterlegt werden muss
- Scopes, mindestens `openid`; üblich sind `openid profile email`
- Claim für den Benutzernamen, standardmäßig `preferred_username`

Das Client-Secret wird mit dem Schlüssel aus `data/config.json` verschlüsselt in der Datenbank gespeichert. Die eindeutige Bindung eines OIDC-Kontos erfolgt über Issuer und `sub`, nicht nur über den sichtbaren Benutzernamen.

Optionen:

- **Automatische Benutzeranlage:** Beim ersten erfolgreichen Login wird ein Benutzerkonto mit Rolle **Benutzer** angelegt. Es besitzt zunächst keine Gruppen und sieht deshalb keine Geräte, bis ein Administrator Gruppen zuweist.
- **Erlaubte E-Mail-Domains:** Kommagetrennte Positivliste für alle OIDC-Anmeldungen. Ist sie gesetzt, muss der Provider eine bestätigte E-Mail-Adresse (`email_verified=true`) aus einer erlaubten Domain liefern; andernfalls wird die Anmeldung abgewiesen.
- **Vorab angelegtes OIDC-Konto:** Ein Administrator trägt Issuer und das unveränderliche OIDC-`sub` bereits beim Anlegen ein. Es gibt keine automatische Bindung über Benutzername oder E-Mail; die eindeutige Identität ist ausschließlich die Kombination aus Issuer und `sub`.
- **Unsicheres HTTP zulassen:** Nur für ausdrücklich isolierte Testumgebungen. Produktiv HTTPS verwenden. Private, lokale oder reservierte Issuer-Adressen sind zusätzlich standardmäßig blockiert; ein bewusst interner Provider benötigt `OIDC_ALLOW_PRIVATE_ISSUER=true`.

Hinter einem TLS-Reverse-Proxy muss `TRUST_PROXY_HEADERS=true` nur dann gesetzt werden, wenn ausschließlich der vertrauenswürdige Proxy die Anwendung erreicht. Dadurch kann die externe HTTPS-Redirect-URI korrekt erzeugt werden. Die lokale Anmeldung bleibt als Notfallzugang verfügbar; mindestens ein aktiver lokaler Administrator kann nicht entfernt werden.

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

### 8.5 Import-Blockliste

Beim Löschen eines Geräts wird dessen RustDesk-ID automatisch dauerhaft in der Tabelle `import_blocklist` gespeichert. Dadurch erscheint ein noch in der RustDesk-Serverdatenbank vorhandenes Gerät beim nächsten Import nicht erneut.

Die Blockliste wird bei allen Geräteimporten geprüft:

- CSV-Import
- Upload der RustDesk-Serverdatenbank
- direkter Import aus einer gemounteten Datenbank
- SSH-Snapshot-Import

Unter **Import / Export → Import-Blockliste** können Administratoren Einträge ansehen, manuell ergänzen und wieder freigeben. Nach dem Freigeben kann die ID beim nächsten Import wieder angelegt werden. Die Blockliste liegt in `data/addressbook.db` und ist deshalb in Datenbank- und Vollbackups enthalten.

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

WebUI-Pfad: `/data/ssh/rustdesk_import_ed25519`. Zusätzlich muss der erwartete SHA-256-Hostschlüssel-Fingerprint des RustDesk-Servers eingetragen werden, zum Beispiel aus `ssh-keyscan -p 22 SERVER 2>/dev/null | ssh-keygen -lf - -E sha256`. Erst bei Übereinstimmung wird der Schlüssel in `known_hosts` übernommen; `StrictHostKeyChecking=yes` bleibt aktiv. Der eingebaute Test prüft anschließend Verbindung, Laufzeit, Bytes, SQLite-Header, `integrity_check`, Peer-Tabelle und Peer-Anzahl.

## 10. Backup / Restore

Backup-Arten:

- `.db`: unverschlüsselte SQLite-Sicherung
- `.rabenc`: AES-256-GCM-verschlüsselte Datenbank; Passwort mindestens 12 Zeichen
- `.rabfull`: verschlüsseltes Vollbackup; Passwort mindestens 16 Zeichen; enthält Datenbank, `config.json`, SSH-Keys, Zertifikate, Logs und Manifest

Vorhandene Backups können heruntergeladen, wiederhergestellt oder gelöscht werden. Restore ist auch per Upload von `.db`, `.sqlite`, `.sqlite3`, `.rabenc` und `.rabfull` möglich. Vor jedem Restore erzeugt die App automatisch ein unverschlüsseltes Sicherheitsbackup des bisherigen Datenbankstands.

Wichtig:

- `.rabenc` enthält nur die Datenbank und benötigt die dazugehörige `data/config.json`, um Gerätepasswörter zu entschlüsseln.
- `.rabfull` ist für Umzug/Totalausfall empfohlen.
- Nach `.rabfull`-Restore Container neu starten, damit `config.json` und Schlüssel neu geladen werden. Der Restore akzeptiert nur reguläre Dateien in festgelegten Pfaden und begrenzt Dateianzahl, Einzelgröße und entpackte Gesamtgröße; Links und Gerätedateien werden abgewiesen.
- Backup-Passwörter außerhalb des Servers aufbewahren.

## 11. Einstellungen

Die Einstellungen sind nur für Administratoren verfügbar:

- **Darstellung & Sprache:** wird pro Benutzer unter **Mein Konto** gespeichert; der Bereich in den Administratoreinstellungen ändert ebenfalls nur das aktuell angemeldete Administratorkonto
- **OpenID Connect:** Provider, Issuer, Client-Zugangsdaten, Scopes, Username-Claim, Auto-Provisioning und erlaubte Domains
- **Gerätetypen:** ein Wert pro Zeile als Vorauswahl im Geräteformular
- **Online-Status:** hbbs-Parameter und automatisches Intervall
- **Brute-Force-Sperre:** 2–50 Fehlversuche pro Quell-IP, Zeitfenster 1–1440 Minuten; Änderung erfordert Admin-Passwort. Dadurch kann ein Angreifer kein fremdes Konto allein über dessen Benutzernamen sperren
- **Update-Check:** automatischer Check 1–168 Stunden; installiert keine Updates
- **Sicherheitshinweise:** Verschlüsselungs- und Backup-Hinweise

Das eigene lokale Passwort und TOTP werden unabhängig von der Administratorrolle unter **Konto** verwaltet. OIDC-Konten zeigen dort Provider, E-Mail und Rollen-/Gruppeninformationen; Passwort und MFA bleiben beim Provider.

Auf Smartphone und Tablet werden die Kategorien als horizontal scrollbar bedienbare Navigation dargestellt.

## 12. Sicherheit

Die Sicherheitsseite zeigt bis zu 250 Login-/2FA-Ereignisse in einem auf ungefähr 10 sichtbare Zeilen begrenzten Scrollbereich und bietet den Download von `auth.log`.

Der Sicherheitsstatus prüft:

- aktive Administratoren, lokale Notfall-Administratoren und OIDC-Konten
- lokale 2FA-Abdeckung und vorhandene Recovery-Codes; OIDC-MFA wird beim Provider verwaltet und kann lokal nicht verifiziert werden
- OIDC-Aktivierung, Issuer, Client-ID, verschlüsseltes Client-Secret und Auto-Provisioning
- HMAC-Signaturen von Benutzerrolle, Kontostatus, OIDC-Identität, 2FA-Zustand, Sitzungsstand und Gruppenzuweisungen
- HttpOnly-/Secure-Cookie und HSTS
- Proxy-Header-Konfiguration
- Auth-Log und Dateirechte
- `config.json` und SQLite-Dateirechte
- unverschlüsselte/verschlüsselte Backups
- IP-basierte interne Brute-Force-Sperre sowie automatische Alters-/Mengenbegrenzung der Auth-Ereignisse
- Auth-Logrotation
- Update-Check, hbbs-Konfiguration und HTTPS-Endpunkt

Die SQLite-Datenbank ist nicht vollständig SQLCipher-verschlüsselt. Gerätepasswörter und das OIDC-Client-Secret sind feldweise mit Fernet verschlüsselt; Benutzer-Sicherheitszustand und Gruppenzuweisungen sind zusätzlich HMAC-signiert. Sicherheitsänderungen erhöhen eine Sitzungsversionsnummer und widerrufen bereits ausgestellte Sitzungen. Rollen- und Gruppenzugriffe werden in den Backend-Routen geprüft. Datenbank plus `config.json` gelten zusammen als sensibles Schlüsselmaterial.

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


### 12.3 Container- und Frontend-Härtung

Der Container läuft mit UID/GID `10001`, ohne Linux-Capabilities, mit `no-new-privileges`, schreibgeschütztem Root-Dateisystem und begrenztem `/tmp`-tmpfs. Schreibbar bleiben nur die eingebundenen Daten- und Backup-Verzeichnisse. Bootstrap und Bootstrap Icons werden lokal ausgeliefert; ausführbare Frontend-Ressourcen werden nicht mehr von einem externen CDN geladen. Die Content Security Policy verwendet einen pro Antwort erzeugten Script-Nonce.

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

Alle Seiten sind für 320 px Smartphonebreite, größere Smartphones, Tablets und Desktop ausgelegt. Tabellen für Geräte, Benutzer, Backups, Sicherheitsereignisse und Diagnose wechseln mobil zu beschrifteten Karten. Lange Pfade, URLs, IDs und Logtexte brechen um. Kategorienavigation in Einstellungen, Import und Anleitung kann horizontal gescrollt werden. Das Hauptmenü wird über den mobilen Navbar-Schalter geöffnet. Normale Benutzer sehen dort nur Dashboard, Geräte, Konto und Anleitung.

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

- **Update:** ZIP-Struktur prüfen; Flat-Update muss Dateien direkt im Archivwurzelverzeichnis enthalten. Zusätzlich müssen `.zip.sha256` und `.zip.sig` denselben Basisnamen besitzen und mit dem eingebauten öffentlichen Schlüssel verifizierbar sein.
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

## Container-Init und Healthcheck

Ab 0.5.28 bereitet der kurzlebige Dienst `rustdesk-addressbook-init` die eingebundenen Daten- und Backup-Verzeichnisse vor. Damit starten auch bestehende Installationen, deren Host-Verzeichnisse noch `root` gehören. Der eigentliche Webcontainer läuft weiterhin als UID/GID 10001.

Status prüfen:

```bash
docker compose ps
docker inspect --format '{{.State.Health.Status}}' rustdesk-addressbook
docker logs --tail 100 rustdesk-addressbook
```

Der Healthcheck ruft intern je nach aktivierter Konfiguration `https://127.0.0.1:5443/healthz` oder `http://127.0.0.1:5000/healthz` auf und prüft dabei zusätzlich die SQLite-Verbindung. Selbstsignierte lokale Zertifikate werden für diesen ausschließlich internen Test akzeptiert. Installations- und Updatescript führen den profilierten Init-Dienst über `docker compose run --rm --no-deps rustdesk-addressbook-init` aus. Docker entfernt diesen einmaligen Container unmittelbar nach erfolgreichem Abschluss; der Webcontainer bleibt separat und unprivilegiert.


## 16. Öffentliches Repository und rechtliche Hinweise

- Das Projekt steht unter Apache License 2.0; siehe `LICENSE` und `NOTICE`.
- Nicht aus einem produktiven Installationsverzeichnis committen. Vor dem Push `python scripts/check_repository_safety.py` ausführen.
- `.env`, Datenbanken, Logs, Backups, heruntergeladene Release-Dateien, private TLS-Schlüssel und private Update-Signaturschlüssel werden über `.gitignore` ausgeschlossen.
- `scripts/keys/update-signing-public-v1.pem` ist der öffentliche Prüfschlüssel und soll versioniert bleiben.
- Teile wurden mit Unterstützung von OpenAI ChatGPT entwickelt; Prüfung, Anpassung, Wartung und Verantwortung liegen beim menschlichen Maintainer.
- Sicherheitsprobleme entsprechend `SECURITY.de.md` privat melden.
