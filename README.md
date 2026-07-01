# RustDesk AddressBook

Selfhosted RustDesk-Adressbuch als Docker-Projekt mit Flask, SQLite, Login, 2FA, Gruppen, Geräteverwaltung, Import/Export, Backups, HTTPS direkt im Container, hbbs-Live-Status und SSH-Import der RustDesk-Serverdatenbank.

## Neu in 0.5.17

- Sprachumschaltung Deutsch/Englisch ergänzt.
- Einstellungsbereich neu strukturiert: linke Navigation, rechter Detailbereich.
- Dashboard, Geräte-Seite und Einstellungen nutzen zentrale Übersetzungen für die wichtigsten Texte.
- Darstellung und Sprache werden gemeinsam unter **Einstellungen → Darstellung & Sprache** gespeichert.
- Die Einstellungen sind in Bereiche wie Admin-Konto, 2FA, Gerätetypen, Online-Status, Brute-Force, Update-Check und Sicherheitshinweise aufgeteilt.

## Download / Neuinstallation

```bash
cd /opt
wget https://dl.ab-xnet.de/rustdesk-addressbook-v0517.zip
unzip rustdesk-addressbook-v0517.zip
cd rustdesk-addressbook
chmod +x scripts/install.sh scripts/update.sh
./scripts/install.sh
```

Das Script fragt unter anderem ab:

- HTTPS-Port
- ob HTTP zusätzlich aktiviert werden soll
- Datenverzeichnis
- Backup-Verzeichnis
- optionaler read-only RustDesk-DB-Mount
- Brute-Force-Grundwerte
- Update-Download-Basis-URL

Beim ersten Aufruf werden Default-Werte vorgeschlagen. Bei jedem späteren Aufruf werden die zuletzt gespeicherten Werte aus `.env` als neue Default-Werte genutzt.

Danach ist die WebUI standardmäßig erreichbar unter:

```text
https://SERVER-IP:5443
```

## Update

### Variante A: Update-ZIP manuell in `updates/` kopieren

```bash
cd /opt/rustdesk-addressbook
wget https://dl.ab-xnet.de/rustdesk-addressbook-update-flat-v0517.zip -O updates/rustdesk-addressbook-update-flat-v0517.zip
./scripts/update.sh
```

### Variante B: Automatischer Online-Check und Download

```bash
cd /opt/rustdesk-addressbook
./scripts/update.sh
```

Das Script prüft zuerst den vorhandenen Ordner `updates/`. Wenn dort keine neuere ZIP liegt, prüft es automatisch `RAB_UPDATE_BASE_URL`, zeigt bei verfügbarer Version die Änderungen an und fragt dann, ob die ZIP heruntergeladen und installiert werden soll.

### Download-Server vorbereiten

Du nutzt `latest.txt`. Die minimale Variante ist:

```text
rustdesk-addressbook-update-flat-v0517.zip
```

Damit WebUI und Update-Script zusätzlich die Änderungen anzeigen können, kannst du die Änderungen direkt darunter schreiben:

```text
rustdesk-addressbook-update-flat-v0517.zip
- Update-Check nutzt latest.txt ohne latest.json-Prüfung.
- Update-Script zeigt Änderungen vor Download und Installation.
- Ja/Nein-Abfragen nutzen [J/n] und [j/N].
```

Alternativ kannst du neben der ZIP eine Datei mit gleichem Namen und `.txt` oder `.md` ablegen, zum Beispiel:

```text
https://dl.ab-xnet.de/rustdesk-addressbook-update-flat-v0517.txt
```

oder:

```text
https://dl.ab-xnet.de/release-notes-v0517.txt
```


In der WebUI gibt es unter **Einstellungen → Update-Check** eine Anzeige, ob online eine neue Version verfügbar ist und welche Änderungen diese Version enthält. Installiert wird weiterhin über `./scripts/update.sh`.

Das Updatescript sichert vorab:

```text
data/
backups/
.env
docker-compose.yml
docker-compose.override.yml
updates/
```

Danach im Browser hart neu laden: `Strg + F5`.

## Wichtige Funktionen

- Geräteverwaltung mit Gruppen, Favoriten, Suche, Tags und Notizen.
- RustDesk-Direktlinks per `rustdesk://`.
- Gerätepasswörter verschlüsselt gespeichert und per Auge-Symbol abrufbar.
- Online-Status per hbbs Live-Abfrage.
- Automatische Online-Abfrage, solange die WebUI geöffnet ist.
- CSV-Import und CSV-Export unter **Import / Export**.
- RustDesk-Server-DB-Import per Upload, Mount oder SSH-Snapshot.
- Backup/Restore inklusive verschlüsselter `.rabenc`-Datenbankbackups und `.rabfull`-Vollbackups.
- Admin-Login mit optionaler 2FA und Recovery-Codes.
- Auditlog und fail2ban/CrowdSec-kompatibles Auth-Log.
- Brute-Force-Sperre konfigurierbar.
- Light/Darkmode und konfigurierbare Gerätetyp-Auswahl.
- Anleitung direkt in der WebUI.

## Anleitung

In der WebUI gibt es den Menüpunkt:

```text
Anleitung
```

Die gleiche ausführliche Betriebsdokumentation liegt zusätzlich als Datei vor:

```text
ADMIN-GUIDE.md
```

## Daten sichern

Diese Ordner sind wichtig:

```text
data/
backups/
```

Besonders wichtig:

```text
data/addressbook.db
data/config.json
data/ssh/
data/certs/
```

Ohne `data/config.json` können gespeicherte Gerätepasswörter nicht entschlüsselt werden. Für einen vollständigen Restore ist daher das verschlüsselte `.rabfull`-Vollbackup empfohlen.

## Version prüfen

Im Footer der WebUI steht:

```text
RustDesk AddressBook 0.5.17
```

Zusätzlich:

```bash
docker exec -it rustdesk-addressbook grep -n "0.5.17-language-settings-layout" /app/app/config.py
```

## Sicherheitshinweis

Die App verschlüsselt Gerätepasswörter feldweise und bietet verschlüsselte Backups. Die laufende SQLite-Datenbank ist aber keine SQLCipher-Vollverschlüsselung. Wer `addressbook.db` und `data/config.json` zusammen erhält, muss als kritisch betrachtet werden. Für externe Ablage daher bevorzugt verschlüsselte `.rabfull`-Vollbackups verwenden und den Serverzugriff streng absichern. `.rabenc` enthält nur die Datenbank und benötigt zusätzlich die passende `config.json`.

## Sprache und Einstellungen

Ab Version 0.5.17 kann die WebUI zwischen Deutsch und Englisch umgeschaltet werden.
Die Auswahl befindet sich unter **Einstellungen → Darstellung & Sprache**.

Der Einstellungsbereich ist in eine linke Navigation und einen rechten Detailbereich aufgeteilt.
Dadurch sind Admin-Konto, 2FA, Online-Status, Update-Check und weitere Optionen schneller erreichbar.

Hinweis: Die Kernoberfläche ist übersetzt. Technische Logs, Import-Inhalte und einige Diagnosemeldungen bleiben bewusst unverändert oder deutschsprachig, damit bestehende Hinweise und Logs kompatibel bleiben.

