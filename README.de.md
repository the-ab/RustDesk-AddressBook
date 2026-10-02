# Community-Adressbuch für RustDesk

## Kandidat 0.6.3 — zuverlässiger Restore und Import

Vorbereitet am 02.10.2026; dieser Quellkandidat ist noch nicht veröffentlicht. Die Beispiele für veröffentlichte Images darunter beziehen sich bis zur neuen Image-Veröffentlichung auf 0.6.2.

- Restore prüft unterstütztes SQLite-Schema, Gruppenzuordnungen, Benutzersignaturen und verschlüsselte Felder vor dem Austausch. Vollrestores verwenden eine exklusive Wartungssperre und ein dauerhaftes Rückwegjournal. Ein unterbrochener Restore sperrt Anfragen, bis die Wiederherstellung beim Anwendungsstart den vorherigen Stand hergestellt hat. Laufzeitschlüssel werden pro Webprozess neu geladen; nach Restore erneut anmelden. Nach Wiederherstellung von TLS-Zertifikaten den Container neu starten.
- Backupnamen sind eindeutig; vorhandene Backups werden nie ersetzt. Doppelte RustDesk-IDs teilen eine hbbs-Abfrage, deren Ergebnis alle passenden Geräte erhalten. Fehlerhafte CSV und mehrdeutige DB/WAL/SHM-ZIP-Namen werden vor dem Import abgewiesen. Einstellungen werden einmal pro Anfrage geladen und bei Änderungen neu eingelesen.
- Der korrigierte ZIP-Updater stoppt den Dienst vor der Sicherung der konfigurierten `RAB_DATA_DIR` und `RAB_BACKUP_DIR`, sichert sämtliche verwalteten Quelldateien und lokale Konfigurationen und führt bei Build-/Start-/Health-Fehlern einen Rückweg aus. Ein Health-Timeout gilt als Fehler. `flock` (util-linux) verhindert gleichzeitige Updater-Aufrufe im selben Updateverzeichnis.
- Laufzeitabhängigkeiten: cryptography 50.0.2, requests 2.34.2; Testabhängigkeit: pytest 9.1.1; Python-Containerbasis: 3.13.15.

### Quellcode-Upgrade von 0.6.2

Der bereits in 0.6.2 installierte Updater besitzt keinen vollständigen Rückweg. Vor dem ersten Upgrade die neue Flat-ZIP samt signierter Prüfsumme mit dem vorhandenen vertrauenswürdigen öffentlichen Schlüssel prüfen und anschließend beide korrigierten Updater-Dateien im bestehenden Verzeichnis `scripts/` installieren:

```bash
openssl pkeyutl -verify -pubin -inkey scripts/keys/update-signing-public-v1.pem -rawin -in /pfad/rustdesk-addressbook-update-flat-v0.6.3.zip.sha256 -sigfile /pfad/rustdesk-addressbook-update-flat-v0.6.3.zip.sig
(cd /pfad && sha256sum -c rustdesk-addressbook-update-flat-v0.6.3.zip.sha256)
unzip -o /pfad/rustdesk-addressbook-update-flat-v0.6.3.zip scripts/update.sh scripts/update_transaction.py -d .
bash scripts/update.sh /pfad/rustdesk-addressbook-update-flat-v0.6.3.zip
```

Das erzeugte Pre-Update-Verzeichnis behalten. Falls Host oder Updater vor dem automatischen Rückweg hart beendet werden, Dienst stoppen und `python3 /pfad/preupdate/update_transaction.py rollback /pfad/preupdate` ausführen; anschließend die wiederhergestellte Compose-Installation bauen/starten und den Health-Status prüfen. Kein zweites Update gegen eine nur teilweise wiederhergestellte Installation starten. Bei GHCR-Installationen das gewünschte veröffentlichte Image über `docker-compose/` holen und neu starten; der Quell-ZIP-Updater ist für Quellinstallationen vorgesehen.

Ein selbst gehostetes Web-Adressbuch für RustDesk-Umgebungen als Docker-Projekt mit Flask, SQLite, lokaler und OpenID-Connect-Anmeldung, Benutzer-/Gruppenrechten, Geräteverwaltung, Import/Export, Backup/Restore, HTTPS, hbbs-Live-Status und SSH-Import der RustDesk-Serverdatenbank.

> **Unabhängiges Projekt:** Dies ist ein unabhängiges Community-Projekt. Es ist nicht mit RustDesk oder Purslane Ltd. verbunden und wird von diesen weder unterstützt, gesponsert noch gepflegt. RustDesk ist eine Marke des jeweiligen Rechteinhabers.

> Die englische Dokumentation ist die Standardfassung. Deutsche Dateien tragen die Endung `*.de.md`.

## Neu in 0.6.2

- Behebt, dass neu erzeugte 2FA-Wiederherstellungscodes nach der Erfolgsmeldung nicht angezeigt wurden, indem Ablaufzeiten kurzlebiger Secrets nach SQLite-Roundtrips wieder eindeutig als UTC behandelt werden.
- Behebt den quellcodebasierten Updatepfad: verwaltete punktierte Docker-Image-Namen wie `rustdesk-addressbook-v0.6.1` werden auf den neuen punktierten Release-Namen weitergeführt und nicht mehr fälschlich als benutzerdefiniert behandelt.
- Korrigiert die Online-Update-Erkennung in WebUI und `update.sh`, sodass punktierte `latest.txt`-Dateinamen wie `v0.6.2` wieder erkannt werden; kompakte Altformate bleiben lesbar.
- **Update-Hinweis für 0.6.1:** Da der in 0.6.1 installierte Online-Parser genau den hier behobenen Fehler enthält, 0.6.2 einmal über das signierte lokale Update-Triplett im Ordner `updates/` installieren; danach funktioniert die Online-Erkennung wieder regulär.
- Enthält die aktuelle zweisprachige `docs/`-Struktur sowie die Repository-Prüfung für vollständige englische/deutsche Informationsdateipaare.
- Prüft die vollständige Installer- und Flat-Update-Paketstruktur für das Release `v0.6.2` erneut.

## Installation

### Installation über das GHCR-Image

Das veröffentlichte Container-Image steht unter folgenden Tags bereit:

```text
ghcr.io/the-ab/rustdesk-addressbook:latest
ghcr.io/the-ab/rustdesk-addressbook:0.6.2
```

Der Ordner `docker-compose/` enthält die dafür vorgesehene `compose.yaml` und `.env.example`. Alle Umgebungsvariablen sind in [`docker-compose/README.de.md`](docker-compose/README.de.md) beschrieben; die englische Fassung liegt unter [`docker-compose/README.md`](docker-compose/README.md). Für diese Installationsart werden keine Projektquellcode-Dateien benötigt:

```bash
cd docker-compose
cp .env.example .env
docker compose pull
docker compose up -d
docker exec rustdesk-addressbook python -c 'import json; print(json.load(open("/data/config.json"))["SETUP_TOKEN"])'
```

Der letzte Befehl zeigt das einmalige Setup-Token an. Nach erfolgreicher Erstellung des ersten Administrators wird es aus `config.json` entfernt.

Mit `RAB_IMAGE_TAG=latest` wird immer das neueste veröffentlichte Image verwendet. Mit `RAB_IMAGE_TAG=0.6.2` bleibt die Installation auf dieser Version. Persistente Daten und Backups liegen in den in `.env` eingestellten Hostpfaden.

### Installation aus dem Release-Archiv mit lokalem Build

Ein aktuelles Release-Archiv von der Releases-Seite des Repositorys herunterladen und anschließend:

```bash
cd /opt
unzip rustdesk-addressbook-v0.6.2.zip
cd rustdesk-addressbook
chmod +x scripts/install.sh scripts/update.sh
./scripts/install.sh
```

Das Installationsscript fragt Zeitzone, Container-/Image-Name, Daten- und Backup-Pfade, HTTPS-Port, optionales HTTP, Zertifikatsnamen, Proxy-Vertrauen, signierte Updatequelle, optionalen read-only RustDesk-DB-Mount sowie Brute-Force-/Logrotationswerte ab. Vorhandene `.env`-Werte werden beim erneuten Aufruf übernommen.

Es gibt keine festen Erstzugangsdaten. Nach dem ersten Start wird das einmalige Setup-Token durch das Installationsscript ausgegeben oder kann aus `/data/config.json` gelesen werden. Sobald das erste Administratorkonto erfolgreich angelegt wurde, entfernt die Anwendung das Token automatisch aus `config.json`.

Standardadresse:

```text
https://SERVER-IP:5443
```

## Updates

Signierte Update-Dateien nach `updates/` kopieren:

```bash
cd /opt/rustdesk-addressbook
cp /pfad/rustdesk-addressbook-update-flat-v0.6.2.zip* updates/
./scripts/update.sh
```

Zur Update-ZIP gehören die gleichnamigen Dateien `.zip.sha256` und `.zip.sig`. Vor dem Entpacken wird mit dem eingebetteten öffentlichen Ed25519-Schlüssel geprüft.

Online-Prüfungen verwenden standardmäßig die GitHub-Releases des Projekts:

```dotenv
RAB_UPDATE_BASE_URL=https://github.com/the-ab/RustDesk-AddressBook/releases/latest/download
```

Im neuesten veröffentlichten Release müssen `latest.txt`, Update-ZIP sowie die passenden Dateien `.zip.sha256` und `.zip.sig` gemeinsam vorhanden sein. Die erste gültige Zeile der `latest.txt` nennt die Update-ZIP. Bestehende eigene, nicht leere URLs bleiben unterstützt. Zum ausdrücklichen Abschalten wird `RAB_UPDATE_BASE_URL=disabled` gesetzt; lokale signierte Updates bleiben vollständig nutzbar.

## Rollen und Sichtbarkeit

- **Administrator:** vollständiger Zugriff auf alle Geräte und Gruppen einschließlich ungruppierter Geräte sowie Benutzer, Import/Export, Backups, Sicherheit, Einstellungen und Updates.
- **Benutzer:** Zugriff auf Dashboard, Geräte, eigenes Konto und Anleitung. Sichtbar sind ausschließlich Geräte zugewiesener Gruppen. Verbindung und ausdrücklicher Passwortabruf bleiben möglich; Anlegen, Bearbeiten und Löschen sind gesperrt. Darstellung und Sprache gelten nur für das eigene Konto.
- Gruppen werden unter **Benutzer** zugewiesen. Automatisch angelegte OIDC-Benutzer besitzen zunächst keine Gruppen und sehen daher keine Geräte.
- Berechtigungen werden serverseitig geprüft; ausgeblendete Navigation ist nicht die Sicherheitsgrenze.

## Hauptfunktionen

- Geräte- und Gruppenverwaltung mit verschlüsselten RustDesk-Passwörtern
- Lokale Konten, Admin-/Benutzerrollen, TOTP-2FA, Recovery-Codes und OIDC
- Benutzerindividuelle Sprache und Hell-/Dunkelmodus
- CSV- und RustDesk-Serverdatenbank-Import einschließlich SSH-Snapshots
- Bearbeitbare CSV-Beispieldatei: [`sample-import.csv`](sample-import.csv)
- Persistente Blockliste für gelöschte RustDesk-IDs
- hbbs-Online-Statusabfragen
- Unverschlüsselte, verschlüsselte DB- und verschlüsselte Vollbackups
- Responsive Oberfläche für Smartphone, Tablet und Desktop
- Signierte Updates und gehärteter unprivilegierter Containerbetrieb

Die vollständige Bedienungsanleitung steht in [`ADMIN-GUIDE.de.md`](ADMIN-GUIDE.de.md).

## Repository-Sicherheit

Nicht direkt aus einem produktiven Installationsverzeichnis committen. Mit einem sauberen Release-/Quellarchiv beginnen und vor dem Push prüfen:

```bash
python scripts/check_repository_safety.py
```

Die Prüfung weist typische Laufzeitdateien und privates Schlüsselmaterial ab. `.gitignore` schließt `.env`, Datenbanken, Logs, Backups, heruntergeladene Release-Dateien sowie private Signatur-/TLS-Schlüssel aus. Der öffentliche Prüfschlüssel `scripts/keys/update-signing-public-v1.pem` wird absichtlich versioniert.

## Lokale Entwicklung und Prüfungen

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python scripts/check_repository_safety.py
python -m compileall -q app scripts tests wsgi.py
ruff check app scripts tests wsgi.py
bandit -q -r app scripts -x tests -ll
pytest -q
node --check app/static/js/app.js
bash -n entrypoint.sh scripts/*.sh
```

Diese Prüfungen werden vom Maintainer oder von Mitwirkenden manuell ausgeführt. Das Repository enthält keine GitHub-basierte CI, keine automatischen Abhängigkeitsupdates und keine automatischen Container-Builds.

## Dokumentation

- Dokumentationsübersicht: [`docs/README.de.md`](docs/README.de.md)
- Englisch: [`ADMIN-GUIDE.md`](ADMIN-GUIDE.md), [`docs/releases/RELEASE_NOTES.md`](docs/releases/RELEASE_NOTES.md), [`SECURITY.md`](SECURITY.md), [`CONTRIBUTING.md`](CONTRIBUTING.md), [`docs/security/SECURITY-REPORT.md`](docs/security/SECURITY-REPORT.md)
- Deutsch: [`ADMIN-GUIDE.de.md`](ADMIN-GUIDE.de.md), [`docs/releases/RELEASE_NOTES.de.md`](docs/releases/RELEASE_NOTES.de.md), [`SECURITY.de.md`](SECURITY.de.md), [`CONTRIBUTING.de.md`](CONTRIBUTING.de.md), [`docs/security/SECURITY-REPORT.de.md`](docs/security/SECURITY-REPORT.de.md)
- Lizenz und Hinweise: [`LICENSE`](LICENSE), [`NOTICE`](NOTICE), [`THIRD-PARTY-NOTICES.de.md`](THIRD-PARTY-NOTICES.de.md)

## Lizenz

Das Projekt steht unter der [Apache License 2.0](LICENSE). Drittanbieterkomponenten behalten ihre jeweiligen Lizenzen.

## Hinweis zur KI-Unterstützung

Teile dieses Projekts wurden mit Unterstützung von OpenAI ChatGPT entwickelt. Der Projekt-Maintainer hat den erzeugten Code geprüft, angepasst und getestet und übernimmt die Verantwortung für die veröffentlichte Software.

## Sicherheit

Vor dem Betrieb [`SECURITY.de.md`](SECURITY.de.md) lesen und vermutete Schwachstellen über den privaten Meldeweg übermitteln. `data/config.json`, Datenbanken, Backups, Sitzungsmaterial, OIDC-Geheimnisse und private Release-Signaturschlüssel gehören nicht in das Repository.
