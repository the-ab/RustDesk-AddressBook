# Community-Adressbuch für RustDesk

Ein selbst gehostetes Web-Adressbuch für RustDesk-Umgebungen als Docker-Projekt mit Flask, SQLite, lokaler und OpenID-Connect-Anmeldung, Benutzer-/Gruppenrechten, Geräteverwaltung, Import/Export, Backup/Restore, HTTPS, hbbs-Live-Status und SSH-Import der RustDesk-Serverdatenbank.

> **Unabhängiges Projekt:** Dies ist ein unabhängiges Community-Projekt. Es ist nicht mit RustDesk oder Purslane Ltd. verbunden und wird von diesen weder unterstützt, gesponsert noch gepflegt. RustDesk ist eine Marke des jeweiligen Rechteinhabers.

> Die englische Dokumentation ist die Standardfassung. Deutsche Dateien tragen die Endung `*.de.md`.

## Neu in 0.5.32

- GitHub Releases des Projekts sind jetzt die feste Standardquelle für signierte Online-Updates.
- Der Updater liest `latest.txt` aus dem neuesten veröffentlichten Release und lädt die dort genannte ZIP sowie `.sha256` und `.sig` aus demselben Release.
- Bestehende eigene, nicht leere `RAB_UPDATE_BASE_URL`-Werte bleiben unterstützt. Mit `RAB_UPDATE_BASE_URL=disabled` lassen sich Online-Prüfungen ausdrücklich abschalten.
- Eine fertig vorbereitete `latest.txt` wird als eigene Release-Datei mitgeliefert.

## Installation

Ein aktuelles Release-Archiv von der Releases-Seite des Repositorys herunterladen und anschließend:

```bash
cd /opt
unzip rustdesk-addressbook-v0532.zip
cd rustdesk-addressbook
chmod +x scripts/install.sh scripts/update.sh
./scripts/install.sh
```

Das Installationsscript fragt Zeitzone, Container-/Image-Name, Daten- und Backup-Pfade, HTTPS-Port, optionales HTTP, Zertifikatsnamen, Proxy-Vertrauen, signierte Updatequelle, optionalen read-only RustDesk-DB-Mount sowie Brute-Force-/Logrotationswerte ab. Vorhandene `.env`-Werte werden beim erneuten Aufruf übernommen. Nach dem ersten Start wird das einmalige Setup-Token für den ersten Administrator angezeigt.

Standardadresse:

```text
https://SERVER-IP:5443
```

## Updates

Signierte Update-Dateien nach `updates/` kopieren:

```bash
cd /opt/rustdesk-addressbook
cp /pfad/rustdesk-addressbook-update-flat-v0532.zip* updates/
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

- Englisch: [`ADMIN-GUIDE.md`](ADMIN-GUIDE.md), [`RELEASE_NOTES.md`](RELEASE_NOTES.md), [`SECURITY.md`](SECURITY.md), [`CONTRIBUTING.md`](CONTRIBUTING.md), [`SECURITY-REPORT.md`](SECURITY-REPORT.md)
- Deutsch: [`ADMIN-GUIDE.de.md`](ADMIN-GUIDE.de.md), [`RELEASE_NOTES.de.md`](RELEASE_NOTES.de.md), [`SECURITY.de.md`](SECURITY.de.md), [`CONTRIBUTING.de.md`](CONTRIBUTING.de.md), [`SECURITY-REPORT.de.md`](SECURITY-REPORT.de.md)
- Lizenz und Hinweise: [`LICENSE`](LICENSE), [`NOTICE`](NOTICE), [`THIRD-PARTY-NOTICES.de.md`](THIRD-PARTY-NOTICES.de.md)

## Lizenz

Das Projekt steht unter der [Apache License 2.0](LICENSE). Drittanbieterkomponenten behalten ihre jeweiligen Lizenzen.

## Hinweis zur KI-Unterstützung

Teile dieses Projekts wurden mit Unterstützung von OpenAI ChatGPT entwickelt. Der Projekt-Maintainer hat den erzeugten Code geprüft, angepasst und getestet und übernimmt die Verantwortung für die veröffentlichte Software.

## Sicherheit

Vor dem Betrieb [`SECURITY.de.md`](SECURITY.de.md) lesen und vermutete Schwachstellen über den privaten Meldeweg übermitteln. `data/config.json`, Datenbanken, Backups, Sitzungsmaterial, OIDC-Geheimnisse und private Release-Signaturschlüssel gehören nicht in das Repository.
