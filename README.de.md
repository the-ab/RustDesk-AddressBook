# RustDesk AddressBook

> Dies ist die deutsche Dokumentation. Die englische Standardfassung steht in [`README.md`](README.md).

Selfhosted RustDesk-Adressbuch als Docker-Projekt mit Flask, SQLite, lokaler Anmeldung und OpenID Connect, Benutzer-/Gruppenrechten, Geräteverwaltung, Import/Export, Backup/Restore, HTTPS, hbbs-Live-Status und SSH-Import der RustDesk-Serverdatenbank.

## Neu in 0.5.29

- Alle regulären Markdown-Dateien sind standardmäßig auf Englisch.
- Deutsche Dokumentationen verwenden einheitlich die Endung `*.de.md`.
- `RELEASE_NOTES.md` und `RELEASE_NOTES.de.md` wurden als eigene Release-Dokumente ergänzt.
- Interne Dokumentationsverweise und Paketbestandteile wurden an das neue Sprachschema angepasst.

## Neu in 0.5.28

- Neustartschleife bei bestehenden, root-eigenen Datenverzeichnissen behoben: Ein separater Init-Dienst korrigiert die Bind-Mount-Berechtigungen, bevor die weiterhin unprivilegierte Webanwendung startet.
- Basisimage auf `python:3.13.14-slim-trixie` umgestellt.
- Docker-Healthcheck mit `/healthz` und SQLite-Test ergänzt. `docker compose ps` zeigt dadurch `healthy` beziehungsweise `unhealthy`.
- Update-Script kontrolliert nach dem Neustart den Health-Status und zeigt bei Fehlern die letzten Containerlogs.

## Neuinstallation

```bash
cd /opt
wget https://dl.ab-xnet.de/rustdesk-addressbook-v0529.zip
unzip rustdesk-addressbook-v0529.zip
cd rustdesk-addressbook
chmod +x scripts/install.sh scripts/update.sh
./scripts/install.sh
```

Das Installationsscript fragt Zeitzone, Container-/Image-Name, Daten- und Backup-Pfad, HTTPS-Port, optionales HTTP, Zertifikatsnamen, Reverse-Proxy-Vertrauen, Update-URL, optionalen read-only RustDesk-DB-Mount sowie Brute-Force- und Auth-Logrotationswerte ab. Vorhandene Werte aus `.env` werden beim erneuten Aufruf als Defaults verwendet. Nach dem ersten Start zeigt es das einmalige Setup-Token für das erste Administratorkonto an.

Standardadresse:

```text
https://SERVER-IP:5443
```

## Update

```bash
cd /opt/rustdesk-addressbook
wget https://dl.ab-xnet.de/rustdesk-addressbook-update-flat-v0529.zip -O updates/rustdesk-addressbook-update-flat-v0529.zip
wget https://dl.ab-xnet.de/rustdesk-addressbook-update-flat-v0529.zip.sha256 -O updates/rustdesk-addressbook-update-flat-v0529.zip.sha256
wget https://dl.ab-xnet.de/rustdesk-addressbook-update-flat-v0529.zip.sig -O updates/rustdesk-addressbook-update-flat-v0529.zip.sig
./scripts/update.sh
```

Ohne lokal abgelegte neue ZIP kann nur `./scripts/update.sh` gestartet werden. Das Script prüft zuerst `updates/`, danach `RAB_UPDATE_BASE_URL/latest.txt`, zeigt Änderungen an und fragt vor Download und Installation. Vor dem Update werden `data/`, `backups/`, `.env`, Compose-Dateien und `updates/` gesichert. Bei bestehenden Installationen bleibt das bisherige Konto erhalten. Beim Sprung von 0.5.26 wird die alte Benutzersignatur vor der Migration geprüft; ungültige Sicherheitszustände bleiben gesperrt.

## Rollen und Sichtbarkeit

- **Administrator:** Zugriff auf alle Geräte und Gruppen, auch auf Geräte ohne Gruppe, sowie auf Benutzerverwaltung, Gruppen, Import/Export, Backups, Sicherheit, Einstellungen und Updates.
- **Benutzer:** Zugriff auf Dashboard, Geräte, eigenes Konto und Anleitung. Sichtbar sind ausschließlich Geräte in zugewiesenen Gruppen. Verbindungen und die gezielte Anzeige gespeicherter Gerätepasswörter bleiben möglich; Änderungen an Geräten oder Systemdaten sind nicht erlaubt. Darstellung und Sprache kann jeder Benutzer nur für sein eigenes Konto ändern.
- Gruppen werden in **Benutzer** einem Konto zugewiesen. Ein automatisch über OIDC angelegter Benutzer besitzt zunächst keine Gruppenzuweisung und sieht daher noch keine Geräte.
- Rechte werden in den Backend-Routen geprüft. Ausgeblendete Menüpunkte allein sind nicht die Sicherheitsgrenze.

## OpenID Connect

OIDC wird unter **Einstellungen → OpenID Connect** eingerichtet:

- Issuer-URL mit Discovery unter `/.well-known/openid-configuration`
- Client-ID und verschlüsselt gespeichertes Client-Secret
- Redirect-URI aus der WebUI beim Provider hinterlegen
- Scopes, Benutzername-Claim und Anzeigename des Providers
- optionale automatische Benutzeranlage und eine Positivliste erlaubter E-Mail-Domains
- optionales unsicheres HTTP nur für ausdrücklich aktivierte interne Testumgebungen

Für produktiven Betrieb HTTPS verwenden und hinter einem Reverse Proxy `TRUST_PROXY_HEADERS=true` nur setzen, wenn dessen Forwarded-Header vertrauenswürdig sind. Mindestens ein aktiver lokaler Administrator bleibt als Notfallzugang erhalten.

## Funktionen

- **Geräte:** Anlegen, bearbeiten, löschen, suchen und nach Gruppe, Favorit oder Gerätetyp filtern; Sortierung nach Online-Status, Name, Favoriten oder Änderung. Felder: Name, RustDesk-ID, verschlüsseltes Passwort, Gruppe, Kunde, Standort, Gerätetyp/OS, Tags, Notizen, Favorit und Online-Status.
- **Ansichten:** Karten, kompakte Liste und kleine Symbole; Auswahl gilt für Dashboard und Geräte-Seite.
- **RustDesk-Verbindung:** `rustdesk://`-Direktlink; gespeichertes Passwort wird erst beim ausdrücklichen Abruf serverseitig entschlüsselt. Nach Ablauf des Sicherheitsfensters ist vorher eine erneute Anmeldung erforderlich; Abruf und Verbindungsstart werden protokolliert.
- **Gruppen:** Name, Farbe und Icon; beim Löschen einer Gruppe bleiben Geräte erhalten und werden nur aus der Gruppe gelöst.
- **Online-Status:** Manuell oder per hbbs OnlineRequest/OnlineResponse; frei wählbares Intervall in Minuten oder Stunden, solange eine Administrator-WebUI geöffnet ist.
- **CSV:** Import erstellt neue Geräte, überspringt Zeilen ohne Name oder RustDesk-ID sowie gesperrte IDs aus der Import-Blockliste und legt angegebene Gruppen bei Bedarf an. Export ist mit oder ohne entschlüsselte Passwörter möglich.
- **RustDesk-Server-DB:** Upload von `db_v2.sqlite3` plus optional WAL/SHM oder ZIP, read-only Mount, Diagnose sowie SSH-Snapshot. Alle Importwege berücksichtigen die persistente Import-Blockliste.
- **Backups:** Unverschlüsselte SQLite-Sicherung, verschlüsseltes `.rabenc`-DB-Backup und verschlüsseltes `.rabfull`-Vollbackup. Vor jedem Restore wird automatisch ein Sicherheitsbackup erstellt. Vollbackup-Archive werden vor dem Schreiben strikt nach Pfaden, Dateitypen, Anzahl und entpackter Größe geprüft.
- **Sicherheit:** lokale TOTP-2FA, einmalige gehashte Recovery-Codes, OIDC-Anmeldung, HMAC-Signatur von Benutzerzustand und Gruppenzuweisungen, Sitzungswiderruf, CSRF-Schutz, Auditlog, IP-basierte Brute-Force-Sperre und fail2ban/CrowdSec-kompatibles `auth.log` mit Rotation und Datenbankbegrenzung.
- **Import-Blockliste:** Gelöschte Geräte-IDs werden automatisch gespeichert und bei allen Geräteimporten übersprungen; Administratoren können IDs manuell sperren oder freigeben.
- **Responsive WebUI:** Login, Dashboard, Geräte, Benutzer, Gruppen, Import, Backup, OIDC, Konto, Einstellungen, Sicherheit, Anleitung und Release-Ansicht sind für Smartphone, Tablet und Desktop ausgelegt.

## Backup-Hinweise

Wichtige Daten liegen unter:

```text
data/addressbook.db
data/config.json
data/ssh/
data/certs/
data/logs/
backups/
```

`data/config.json` enthält Schlüsselmaterial für Gerätepasswörter und das OIDC-Client-Secret. Ein `.rabenc`-Backup enthält nur die Datenbank und benötigt weiterhin die passende `config.json`. Für Umzug oder Totalausfall ist ein verschlüsseltes `.rabfull`-Vollbackup empfohlen. Nach einem `.rabfull`-Restore den Container neu starten.

## Download-Server / latest.txt

```text
rustdesk-addressbook-update-flat-v0529.zip
[de]
- Deutsche Änderung
[en]
- English change
```

Neben der Update-ZIP müssen die gleichnamigen Dateien `.zip.sha256` und `.zip.sig` veröffentlicht werden. `scripts/update.sh` lädt und prüft diese automatisch. Alternativ werden gleichnamige `.txt`-/`.md`-Dateien und sprachspezifische Dateien wie `release-notes-v0529.de.txt` oder `release-notes-v0529.en.txt` unterstützt. Der private Ed25519-Schlüssel gehört ausschließlich in eine offline beziehungsweise getrennt geschützte Release-Umgebung und niemals auf den Downloadserver.

## Version prüfen

```bash
docker exec -it rustdesk-addressbook grep -n "0.5.29-english-default-markdown-docs" /app/app/config.py
```

## Dokumentation

Die vollständige deutsche Anleitung steht in der WebUI unter **Anleitung** und zusätzlich in `ADMIN-GUIDE.de.md`. Die englische Standardfassung liegt in `ADMIN-GUIDE.md`. Die Kernoberfläche, Anleitung und Release-Historie sind Deutsch/Englisch; technische Logs und importierte Inhalte werden nicht übersetzt.

## Sicherheitshinweis

Die SQLite-Datei ist nicht vollständig mit SQLCipher verschlüsselt. Gerätepasswörter und das OIDC-Client-Secret werden feldweise verschlüsselt; sensible Benutzer-Sicherheitsfelder einschließlich Rollen, OIDC-Identität, Sitzungsstand und Gruppenzuweisungen werden HMAC-signiert. Wer Datenbank und `data/config.json` zusammen erhält, muss als kompromittiert betrachtet werden. Öffentlichen Zugriff nur über abgesichertes HTTPS, starke lokale Notfall-Zugangsdaten, 2FA und restriktive Serverrechte bereitstellen.

## Containerstatus prüfen

```bash
docker compose ps
docker inspect --format '{{.State.Health.Status}}' rustdesk-addressbook
docker logs --tail 100 rustdesk-addressbook
```

Beim Start führt `rustdesk-addressbook-init` einmalig die Berechtigungsvorbereitung für Daten und Backups aus. Der eigentliche Container `rustdesk-addressbook` läuft anschließend weiterhin mit UID/GID 10001 und ohne Linux-Capabilities.
