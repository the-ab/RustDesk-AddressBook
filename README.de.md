# Community-Adressbuch für RustDesk

Ein selbst gehostetes Web-Adressbuch für RustDesk-Umgebungen als Docker-Projekt mit Flask, SQLite, lokaler und OpenID-Connect-Anmeldung, Benutzer-/Gruppenrechten, Geräteverwaltung, Import/Export, Backup/Restore, HTTPS, hbbs-Live-Status und SSH-Import der RustDesk-Serverdatenbank.

> **Unabhängiges Projekt:** Dies ist ein unabhängiges Community-Projekt. Es ist nicht mit RustDesk oder Purslane Ltd. verbunden und wird von diesen weder unterstützt, gesponsert noch gepflegt. RustDesk ist eine Marke des jeweiligen Rechteinhabers.

> Die englische Dokumentation ist die Standardfassung. Deutsche Dateien tragen die Endung `*.de.md`.

## Neu in 0.5.30

- Apache License 2.0, `NOTICE`, Beitrags- und Sicherheitsrichtlinien ergänzt.
- `.gitignore` für Installationsdaten, Backups, Datenbanken, Logs, Update-Artefakte, TLS-Schlüssel und private Release-Signaturschlüssel ergänzt.
- GitHub-Actions-CI, Dependabot, Repository-Sicherheitsprüfung und automatisierte Anwendungs-/Sicherheitstests ergänzt.
- Fest eingetragene öffentliche Updatequelle entfernt. `RAB_UPDATE_BASE_URL` ist optional und standardmäßig leer; lokale signierte Updates funktionieren weiterhin.
- Klare Unabhängigkeits-, Marken- und KI-Unterstützungshinweise ergänzt.

## Installation

Ein aktuelles Release-Archiv von der Releases-Seite des Repositorys herunterladen und anschließend:

```bash
cd /opt
unzip rustdesk-addressbook-v0530.zip
cd rustdesk-addressbook
chmod +x scripts/install.sh scripts/update.sh
./scripts/install.sh
```

Das Installationsscript fragt Zeitzone, Container-/Image-Name, Daten- und Backup-Pfade, HTTPS-Port, optionales HTTP, Zertifikatsnamen, Proxy-Vertrauen, optionale Update-URL, optionalen read-only RustDesk-DB-Mount sowie Brute-Force-/Logrotationswerte ab. Vorhandene `.env`-Werte werden beim erneuten Aufruf übernommen. Nach dem ersten Start wird das einmalige Setup-Token für den ersten Administrator angezeigt.

Standardadresse:

```text
https://SERVER-IP:5443
```

## Updates

Signierte Update-Dateien nach `updates/` kopieren:

```bash
cd /opt/rustdesk-addressbook
cp /pfad/rustdesk-addressbook-update-flat-v0530.zip* updates/
./scripts/update.sh
```

Zur Update-ZIP gehören die gleichnamigen Dateien `.zip.sha256` und `.zip.sig`. Vor dem Entpacken wird mit dem eingebetteten öffentlichen Ed25519-Schlüssel geprüft.

Online-Prüfungen sind optional. In `.env` kann eine vertrauenswürdige Release-Quelle gesetzt werden, zum Beispiel:

```dotenv
RAB_UPDATE_BASE_URL=https://github.com/OWNER/REPOSITORY/releases/latest/download
```

Dort müssen `latest.txt`, Update-ZIP und Signaturdateien gemeinsam liegen. Ein leerer Wert deaktiviert Online-Prüfungen; lokale signierte Updates bleiben vollständig nutzbar. Bestehende Installationen behalten beim Update ihren aktuellen `.env`-Wert.

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

## Entwicklung und CI

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

GitHub Actions führt Repository-Prüfung, Syntax-/statische Analyse, Tests, Abhängigkeitsprüfung und Docker-Build aus. Dependabot überwacht Python-, Docker- und GitHub-Actions-Abhängigkeiten.

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
