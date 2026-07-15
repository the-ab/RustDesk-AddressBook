# RustDesk AddressBook

Selfhosted RustDesk-Adressbuch als Docker-Projekt mit Flask, SQLite, lokaler Anmeldung und OpenID Connect, Benutzer-/Gruppenrechten, Geräteverwaltung, Import/Export, Backup/Restore, HTTPS, hbbs-Live-Status und SSH-Import der RustDesk-Serverdatenbank.

## Neu in 0.5.26

- Darstellung und Sprache werden jetzt pro Benutzerkonto gespeichert. Lokale und OIDC-Benutzer können unter **Mein Konto** unabhängig voneinander Hell-/Dunkelmodus sowie Deutsch/Englisch wählen.
- Bestehende Benutzer übernehmen beim Update einmalig die bisherige globale Darstellung und Sprache; spätere Änderungen wirken nur noch auf das jeweilige Konto.
- Neue persistente Import-Blockliste für gelöschte RustDesk-IDs. Beim Löschen eines Geräts wird seine ID automatisch gesperrt.
- CSV-, Server-DB-, SSH- und direkte DB-Importe prüfen die Blockliste und überspringen gesperrte IDs. Administratoren können Einträge unter **Import / Export → Import-Blockliste** ergänzen oder wieder freigeben.

## Neuinstallation

```bash
cd /opt
wget https://dl.ab-xnet.de/rustdesk-addressbook-v0526.zip
unzip rustdesk-addressbook-v0526.zip
cd rustdesk-addressbook
chmod +x scripts/install.sh scripts/update.sh
./scripts/install.sh
```

Das Installationsscript fragt Zeitzone, Container-/Image-Name, Daten- und Backup-Pfad, HTTPS-Port, optionales HTTP, Zertifikatsnamen, Reverse-Proxy-Vertrauen, Update-URL, optionalen read-only RustDesk-DB-Mount sowie Brute-Force- und Auth-Logrotationswerte ab. Vorhandene Werte aus `.env` werden beim erneuten Aufruf als Defaults verwendet.

Standardadresse:

```text
https://SERVER-IP:5443
```

## Update

```bash
cd /opt/rustdesk-addressbook
wget https://dl.ab-xnet.de/rustdesk-addressbook-update-flat-v0526.zip -O updates/rustdesk-addressbook-update-flat-v0526.zip
./scripts/update.sh
```

Ohne lokal abgelegte neue ZIP kann nur `./scripts/update.sh` gestartet werden. Das Script prüft zuerst `updates/`, danach `RAB_UPDATE_BASE_URL/latest.txt`, zeigt Änderungen an und fragt vor Download und Installation. Vor dem Update werden `data/`, `backups/`, `.env`, Compose-Dateien und `updates/` gesichert. Bei bestehenden Installationen wird das bisherige Konto automatisch als aktiver lokaler Administrator übernommen.

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
- **RustDesk-Verbindung:** `rustdesk://`-Direktlink; gespeichertes Passwort wird erst beim ausdrücklichen Abruf serverseitig entschlüsselt.
- **Gruppen:** Name, Farbe und Icon; beim Löschen einer Gruppe bleiben Geräte erhalten und werden nur aus der Gruppe gelöst.
- **Online-Status:** Manuell oder per hbbs OnlineRequest/OnlineResponse; frei wählbares Intervall in Minuten oder Stunden, solange eine Administrator-WebUI geöffnet ist.
- **CSV:** Import erstellt neue Geräte, überspringt Zeilen ohne Name oder RustDesk-ID sowie gesperrte IDs aus der Import-Blockliste und legt angegebene Gruppen bei Bedarf an. Export ist mit oder ohne entschlüsselte Passwörter möglich.
- **RustDesk-Server-DB:** Upload von `db_v2.sqlite3` plus optional WAL/SHM oder ZIP, read-only Mount, Diagnose sowie SSH-Snapshot. Alle Importwege berücksichtigen die persistente Import-Blockliste.
- **Backups:** Unverschlüsselte SQLite-Sicherung, verschlüsseltes `.rabenc`-DB-Backup und verschlüsseltes `.rabfull`-Vollbackup. Vor jedem Restore wird automatisch ein Sicherheitsbackup erstellt.
- **Sicherheit:** lokale TOTP-2FA, einmalige gehashte Recovery-Codes, OIDC-Anmeldung, HMAC-Signatur sensibler Benutzerfelder, CSRF-Schutz, Auditlog, interne Brute-Force-Sperre und fail2ban/CrowdSec-kompatibles `auth.log` mit Rotation.
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
rustdesk-addressbook-update-flat-v0526.zip
[de]
- Deutsche Änderung
[en]
- English change
```

Alternativ werden gleichnamige `.txt`-/`.md`-Dateien und sprachspezifische Dateien wie `release-notes-v0526.de.txt` oder `release-notes-v0526.en.txt` unterstützt.

## Version prüfen

```bash
docker exec -it rustdesk-addressbook grep -n "0.5.26-user-preferences-import-blocklist" /app/app/config.py
```

## Dokumentation

Die vollständige Anleitung steht in der WebUI unter **Anleitung** und zusätzlich in `ADMIN-GUIDE.md`. Die Kernoberfläche, Anleitung und Release-Historie sind Deutsch/Englisch; technische Logs und importierte Inhalte werden nicht übersetzt.

## Sicherheitshinweis

Die SQLite-Datei ist nicht vollständig mit SQLCipher verschlüsselt. Gerätepasswörter und das OIDC-Client-Secret werden feldweise verschlüsselt; sensible Benutzer-Sicherheitsfelder werden HMAC-signiert. Wer Datenbank und `data/config.json` zusammen erhält, muss als kompromittiert betrachtet werden. Öffentlichen Zugriff nur über abgesichertes HTTPS, starke lokale Notfall-Zugangsdaten, 2FA und restriktive Serverrechte bereitstellen.
