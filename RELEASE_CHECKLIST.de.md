# Release-Checkliste

> Die englische Dokumentation ist die Standardfassung. Diese Datei ist die deutsche Ausgabe von [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md).

Diese Checkliste für jedes Release verwenden. Erst veröffentlichen, wenn alle anwendbaren Punkte abgeschlossen sind.

## 1. Umfang und Quellstand

- [ ] Der vorgesehene Release-Umfang ist dokumentiert und enthält keine fremden Änderungen.
- [ ] Die Arbeit begann vom aktuellen `main`-Branch oder einer ausdrücklich freigegebenen Basis.
- [ ] Offene Pull Requests wurden auf Überschneidungen geprüft.
- [ ] Der Arbeitsbaum enthält keine `.env`, Datenbanken, Logs, Backups, heruntergeladenen Update-Assets, privaten Schlüssel oder produktiven Daten.
- [ ] `python scripts/check_repository_safety.py` ist erfolgreich.
- [ ] `.github/dependabot.yml` oder `.github/workflows/ci.yml` wurden nicht hinzugefügt.

## 2. Version und Release-Metadaten

Für Release `X.Y.Z`:

- [ ] `VERSION` enthält exakt `X.Y.Z`.
- [ ] Die Anwendungsversion verwendet konsistent `X.Y.Z`.
- [ ] Das Release-Datum wurde überall einheitlich aktualisiert.
- [ ] Die Fußzeile zeigt aktuelle Version und Release-Datum.
- [ ] Die WebUI-Release-Historie enthält das neue Release auf Deutsch und Englisch.
- [ ] `RELEASE_NOTES.md` und `RELEASE_NOTES.de.md` wurden aktualisiert.
- [ ] `PROJECT_STATUS.md` und `PROJECT_STATUS.de.md` nennen das neue aktuelle Release.
- [ ] Aktuelle Beispiele in README und Admin-Handbuch verwenden `vX.Y.Z`.
- [ ] GHCR-Beispiele verwenden `ghcr.io/the-ab/rustdesk-addressbook:X.Y.Z` sowie bei Bedarf `:latest`.
- [ ] In aktuellen Release-Verweisen bleiben keine kompakten Formen wie `v0601` zurück.

## 3. Dokumentation

- [ ] Jede normale Markdown-Datei ist standardmäßig englisch.
- [ ] Jede benutzerrelevante deutsche Datei verwendet die Endung `*.de.md`.
- [ ] Deutsche und englische Dokumentation beschreiben denselben Funktionsumfang.
- [ ] `docker-compose/README.md` und `docker-compose/README.de.md` beschreiben jede Variable aus `docker-compose/.env.example`.
- [ ] Links in README, Admin-Handbuch, Sicherheitsrichtlinie, Handover, Projektstatus und Release-Checkliste sind gültig.
- [ ] Unabhängigkeits-, Marken-, Lizenz- und KI-Unterstützungshinweise bleiben enthalten.
- [ ] Entferntes oder veraltetes Verhalten wird nicht weiter beschrieben.

## 4. Datenbank- und Migrationssicherheit

- [ ] Das Upgrade von der vorherigen unterstützten Version wurde mit einer bestehenden Datenbank getestet.
- [ ] Bestehende Administrator- und Benutzerkonten bleiben nutzbar.
- [ ] Rollen, Gruppenzuweisungen, OIDC-Identitäten, Sprache und Darstellung bleiben bei der Migration erhalten.
- [ ] Gültiger Benutzerzustand wird nicht stillschweigend zurückgesetzt.
- [ ] Die Sicherheitsintegritätsprüfung weist manipulierte Altdaten ab.
- [ ] Nach vorhandenem Administrator ist kein Setup-Token mehr gespeichert.
- [ ] Eine berechtigt leere/zurückgesetzte Installation kann wieder einen Setup-Token erzeugen.
- [ ] Bei jeder Änderung am Schema oder an persistenten Dateien wurden Backup- und Restore-Auswirkungen geprüft.

## 5. Autorisierung und Authentifizierung

- [ ] Administratorseiten liefern für normale Benutzer HTTP 403 oder eine gleichwertige Sperre.
- [ ] Normale Benutzer sehen ausschließlich Geräte zugewiesener Gruppen.
- [ ] Ungruppierte Geräte bleiben ausschließlich Administratoren vorbehalten.
- [ ] Normale Benutzer können keine Geräte, Gruppen, Benutzer, Importe, Backups oder Einstellungen anlegen, ändern oder löschen.
- [ ] Passwort- und sensible Verbindungsaktionen verlangen wie vorgesehen eine aktuelle Anmeldung.
- [ ] Passwort-, Rollen-, Gruppen- und Sicherheitsänderungen widerrufen betroffene Sitzungen.
- [ ] Lokale Anmeldung, TOTP-2FA, Wiederherstellungscodes und OIDC funktionieren weiterhin.
- [ ] OIDC-Bindung basiert weiterhin auf Issuer und Subject.

## 6. Import, Export und Blockliste

- [ ] CSV-Import funktioniert mit gültigen Daten und weist ungültige Eingaben sicher ab.
- [ ] RustDesk-Serverdatenbank-Import funktioniert über die unterstützten Wege.
- [ ] SSH-Import erzwingt den geprüften SHA-256-Hostschlüssel-Fingerprint.
- [ ] Gelöschte oder manuell gesperrte RustDesk-IDs werden von jedem Importweg übersprungen.
- [ ] Administratoren können IDs bewusst wieder freigeben.
- [ ] CSV-Export bleibt gegen Formelinjektion geschützt.
- [ ] Verhalten und Warnungen beim Passwortexport bleiben eindeutig.

## 7. Backup-, Restore- und Update-Sicherheit

- [ ] Unverschlüsseltes Datenbankbackup funktioniert.
- [ ] Verschlüsseltes Datenbankbackup funktioniert.
- [ ] Verschlüsseltes Vollbackup funktioniert.
- [ ] Restore weist Pfad-Traversal, Symlinks, Hardlinks, Spezialdateien und übergroße Archive ab.
- [ ] Restore prüft die Datenbank vor dem Austausch produktiver Daten.
- [ ] Update-ZIP-Prüfung verlangt die passende signierte Prüfsumme und Ed25519-Signatur.
- [ ] Veränderte, unsignierte oder nicht passende Pakete werden abgewiesen.
- [ ] Der private Signaturschlüssel befindet sich weder im Repository noch in Archiven.
- [ ] Erfolgreiche Updates verschieben ZIP, Prüfsumme und Signatur nach `updates/installed/`.
- [ ] Fehlgeschlagene Updates behalten Diagnosedateien in `updates/`.

## 8. Container und Bereitstellung

- [ ] Das Dockerfile verwendet das vorgesehene Debian-Trixie-basierte Image.
- [ ] Der Hauptcontainer läuft mit der vorgesehenen unprivilegierten UID/GID.
- [ ] Der kurzlebige Init-Container korrigiert persistente Rechte und wird automatisch entfernt.
- [ ] Schreibschutz-, Capability- und Privilegienbeschränkungen bleiben erhalten.
- [ ] `/healthz` meldet Anwendungs- und SQLite-Zustand.
- [ ] Der Docker-Healthstatus wird bei HTTP sowie unterstütztem HTTPS mit selbstsigniertem Zertifikat `healthy`.
- [ ] Die Compose-Datei für den lokalen Build ist gültig.
- [ ] `docker-compose/compose.yaml` für GHCR ist gültig.
- [ ] `docker-compose/.env.example` enthält keine Geheimnisse und stimmt mit der Dokumentation überein.

## 9. Responsive Darstellung und UI

- [ ] Login, Setup, 2FA, Dashboard, Geräte, Gruppen, Benutzer, Import/Export, Backup, Einstellungen, Sicherheit, Hilfe und Konto werden korrekt dargestellt.
- [ ] Mobile Prüfung mindestens bei 320, 375 und 768 Pixel Breite.
- [ ] Kein unbeabsichtigter horizontaler Seitenüberlauf.
- [ ] Breite Tabellen bleiben als mobile Karten oder kontrollierte Scrollbereiche lesbar.
- [ ] Login-/Setup-Fußzeile bleibt zentriert; die angemeldete Fußzeile bleibt bewusst gestaltet.
- [ ] Deutsche und englische UI-Texte sind vollständig.

## 10. Statische und funktionale Prüfungen

Manuell ausführen:

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

- [ ] Python-Kompilierung erfolgreich.
- [ ] Ruff ohne Fehler.
- [ ] Bandit ohne mittlere oder hohe Befunde oder jede Ausnahme ist dokumentiert.
- [ ] Alle lokalen pytest-Tests erfolgreich.
- [ ] JavaScript-Syntax erfolgreich.
- [ ] Shell-Syntax erfolgreich.
- [ ] Jinja-Templates kompilieren im echten Flask-Anwendungskontext.
- [ ] Abhängigkeits-/CVE-Scan bei verfügbarem Netzwerk ausgeführt; Einschränkungen andernfalls dokumentiert.

## 11. Paketerstellung

Für Release `X.Y.Z` erzeugen:

```text
rustdesk-addressbook-update-flat-vX.Y.Z.zip
rustdesk-addressbook-update-flat-vX.Y.Z.zip.sha256
rustdesk-addressbook-update-flat-vX.Y.Z.zip.sig
rustdesk-addressbook-vX.Y.Z.zip
rustdesk-addressbook-vX.Y.Z.zip.sha256
rustdesk-addressbook-vX.Y.Z.zip.sig
latest.txt
```

- [ ] `latest.txt` wird direkt unter genau diesem Namen bereitgestellt.
- [ ] Die erste gültige Zeile nennt `rustdesk-addressbook-update-flat-vX.Y.Z.zip`.
- [ ] Deutsche und englische Release-Hinweise sind korrekt.
- [ ] ZIP-Struktur ist wie vorgesehen flach/vollständig.
- [ ] Ausführbare Skripte behalten ihre Ausführungsrechte.
- [ ] Keine verwaisten, doppelten, Cache-, Testausgabe-, Laufzeit- oder privaten Dateien enthalten.
- [ ] SHA-256-Manifeste stimmen mit den finalen Archiven überein.
- [ ] Ed25519-Signaturen werden mit dem eingebetteten öffentlichen Schlüssel erfolgreich geprüft.
- [ ] Die finalen Archive wurden entpackt und geprüft, nicht nur das Quell-Staging-Verzeichnis.

## 12. Pull Request und Veröffentlichung

- [ ] Ein klar abgegrenzter Draft-Pull-Request wurde geöffnet.
- [ ] Die PR-Beschreibung nennt Änderung, Grund, Auswirkung, Migrations-/Sicherheitsrisiken und ausgeführte Prüfungen.
- [ ] Der Maintainer hat Diff und Release-Ausgaben geprüft und freigegeben.
- [ ] Der PR wurde nach `main` gemergt.
- [ ] Tag `vX.Y.Z` zeigt auf den vorgesehenen Release-Commit.
- [ ] Das GitHub-Release ist als neuestes stabiles Release markiert.
- [ ] `latest.txt`, Update-ZIP, Prüfsumme und Signatur wurden gemeinsam hochgeladen.
- [ ] Komplettarchiv, Prüfsumme und Signatur wurden hochgeladen, falls vorgesehen.
- [ ] GHCR-Tags `X.Y.Z` und `latest` wurden über den kontrollierten Buildprozess des Maintainers veröffentlicht.
- [ ] Feste Latest-Download-URLs liefern die erwarteten Dateien.
- [ ] Eine Neuinstallation und ein Upgrade von der Vorversion wurden mit den veröffentlichten Assets getestet.

## 13. Sitzungsübergabe

- [ ] `HANDOVER.md` / `HANDOVER.de.md` beschreiben weiterhin aktuelle Architektur und Richtlinien.
- [ ] Aktueller Branch, PR-Nummer, abgeschlossene Arbeit, Tests, bekannte Einschränkungen und nächste Schritte sind festgehalten.
- [ ] Außerhalb von GitHub gespeicherte Release-Assets sind eindeutig benannt.
- [ ] Keine ausschließlich interne Versionierungslogik oder privaten Schlüsseldetails wurden öffentlich dokumentiert.
