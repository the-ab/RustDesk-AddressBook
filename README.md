# RustDesk AddressBook

Selfhosted RustDesk-Adressbuch als Docker-Projekt mit Flask, SQLite, Login/2FA, Gruppen, Geräteverwaltung, Import/Export, Backup/Restore, HTTPS, hbbs-Live-Status und SSH-Import der RustDesk-Serverdatenbank.

## Neu in 0.5.24

- Alle WebUI-Seiten für Smartphone, Tablet und Desktop überarbeitet. Breite Tabellen werden mobil als Karten dargestellt; Navigationen, Formulare und Aktionen bleiben ohne Seitenüberlauf bedienbar.
- Vollständige Fehlerprüfung: Dateiauswahl-JavaScript korrigiert, Passwort-Auge für gespeicherte Gerätepasswörter wiederhergestellt, Docker-Weitergabe von Update-URL und Auth-Logrotation ergänzt und CSV-Header bereinigt.
- WebUI-Anleitung, README und Admin-Guide mit dem tatsächlichen Funktionsumfang abgeglichen.

## Neuinstallation

```bash
cd /opt
wget https://dl.ab-xnet.de/rustdesk-addressbook-v0524.zip
unzip rustdesk-addressbook-v0524.zip
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
wget https://dl.ab-xnet.de/rustdesk-addressbook-update-flat-v0524.zip -O updates/rustdesk-addressbook-update-flat-v0524.zip
./scripts/update.sh
```

Ohne lokal abgelegte neue ZIP kann nur `./scripts/update.sh` gestartet werden. Das Script prüft zuerst `updates/`, danach `RAB_UPDATE_BASE_URL/latest.txt`, zeigt Änderungen an und fragt vor Download und Installation. Vor dem Update werden `data/`, `backups/`, `.env`, Compose-Dateien und `updates/` gesichert.

## Funktionen

- **Geräte:** Anlegen, bearbeiten, löschen, suchen und nach Gruppe, Favorit oder Gerätetyp filtern; Sortierung nach Online-Status, Name, Favoriten oder Änderung. Felder: Name, RustDesk-ID, verschlüsseltes Passwort, Gruppe, Kunde, Standort, Gerätetyp/OS, Tags, Notizen, Favorit und Online-Status.
- **Ansichten:** Karten, kompakte Liste und kleine Symbole; Auswahl gilt für Dashboard und Geräte-Seite.
- **RustDesk-Verbindung:** `rustdesk://`-Direktlink; gespeichertes Passwort wird erst beim Klick serverseitig entschlüsselt. Im Bearbeitungsformular lässt es sich über das Auge gezielt abrufen, unverändert lassen oder löschen.
- **Gruppen:** Name, Farbe und Icon; beim Löschen einer Gruppe bleiben Geräte erhalten und werden nur aus der Gruppe gelöst.
- **Online-Status:** Manuell oder per hbbs OnlineRequest/OnlineResponse; frei wählbares Intervall in Minuten oder Stunden, solange die WebUI geöffnet ist. Bei Fehlern bleiben bestehende Stati unverändert.
- **CSV:** Import erstellt neue Geräte, überspringt Zeilen ohne Name oder RustDesk-ID und legt angegebene Gruppen bei Bedarf an. Export ist mit oder ohne entschlüsselte Passwörter möglich.
- **RustDesk-Server-DB:** Upload von `db_v2.sqlite3` plus optional WAL/SHM oder ZIP, read-only Mount, Diagnose sowie SSH-Snapshot. Bestehende Geräte können beim Server-Import optional aktualisiert werden; der Online-Status wird nicht aus der DB übernommen.
- **Backups:** Unverschlüsselte SQLite-Sicherung, verschlüsseltes `.rabenc`-DB-Backup und verschlüsseltes `.rabfull`-Vollbackup. Vor jedem Restore wird automatisch ein Sicherheitsbackup erstellt. Vorhandene Backups können heruntergeladen, wiederhergestellt oder gelöscht werden; Restore per Upload ist ebenfalls möglich.
- **Sicherheit:** Admin-Login, TOTP-2FA, einmalige gehashte Recovery-Codes, HMAC-Signatur sensibler Benutzerfelder, CSRF-Schutz, Auditlog, interne Brute-Force-Sperre und fail2ban/CrowdSec-kompatibles `auth.log` mit Rotation.
- **Einstellungen:** Darstellung/Sprache, Admin-Name/Passwort, 2FA, Gerätetypen, hbbs, automatische Statusabfrage, Brute-Force-Sperre und Update-Check.
- **Update-Check:** Meldet neue Versionen und Release-Änderungen in der WebUI; die Installation erfolgt kontrolliert über `scripts/update.sh`.
- **Responsive WebUI:** Login, Setup, Dashboard, Geräte, Gruppen, Import, Diagnose, Backup, Einstellungen, Sicherheit, Anleitung und Release-Ansicht sind für Smartphone, Tablet und Desktop ausgelegt.

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

`data/config.json` enthält Schlüsselmaterial für gespeicherte Gerätepasswörter. Ein `.rabenc`-Backup enthält nur die Datenbank und benötigt weiterhin die passende `config.json`. Für Umzug oder Totalausfall ist deshalb ein verschlüsseltes `.rabfull`-Vollbackup empfohlen. Nach einem `.rabfull`-Restore den Container neu starten.

## Download-Server / latest.txt

```text
rustdesk-addressbook-update-flat-v0524.zip
[de]
- Deutsche Änderung
[en]
- English change
```

Alternativ werden gleichnamige `.txt`-/`.md`-Dateien und sprachspezifische Dateien wie `release-notes-v0524.de.txt` oder `release-notes-v0524.en.txt` unterstützt.

## Version prüfen

```bash
docker exec -it rustdesk-addressbook grep -n "0.5.24-mobile-ui-docs-audit" /app/app/config.py
```

## Dokumentation

Die vollständige Anleitung steht in der WebUI unter **Anleitung** und zusätzlich in `ADMIN-GUIDE.md`. Die Kernoberfläche, Anleitung und Release-Historie sind Deutsch/Englisch; technische Logs und importierte Inhalte werden nicht übersetzt.

## Sicherheitshinweis

Die SQLite-Datei ist nicht vollständig mit SQLCipher verschlüsselt. Gerätepasswörter werden feldweise verschlüsselt und sensible Benutzer-Sicherheitsfelder HMAC-signiert. Wer Datenbank und `data/config.json` zusammen erhält, muss als kompromittiert betrachtet werden. Öffentlichen Zugriff nur über abgesichertes HTTPS, starke Zugangsdaten, 2FA und restriktive Serverrechte bereitstellen.
