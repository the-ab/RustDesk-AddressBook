# Projektstatus

> Die englische Dokumentation ist die Standardfassung. Diese Datei ist die deutsche Ausgabe von [`PROJECT_STATUS.md`](PROJECT_STATUS.md).

**Letzte Aktualisierung:** 03.08.2026  
**Aktuelles Release:** `0.6.1`  
**Release-Datum:** 31.07.2026  
**Repository:** `the-ab/RustDesk-AddressBook`  
**Standardbranch:** `main`  
**Lizenz:** Apache-2.0

## Aktueller Produktstand

Community Address Book for RustDesk ist eine selbst gehostete Flask-/SQLite-Webanwendung, die als Docker-Projekt und als vorgefertigtes GHCR-Image bereitgestellt wird.

Umgesetzt sind unter anderem:

- Geräte- und Gruppenverwaltung mit verschlüsselt gespeicherten RustDesk-Passwörtern;
- lokale Benutzer, Administrator-/Benutzerrollen, TOTP-2FA, Wiederherstellungscodes und OIDC;
- benutzerindividuelle Sprache sowie Hell-/Dunkelmodus;
- gruppenbasierte Sichtbarkeit für normale Benutzer und ausschließlich administrativer Zugriff auf ungruppierte Geräte;
- CSV-, RustDesk-Serverdatenbank-, direkter Datenbank- und SSH-Snapshot-Import;
- persistente Import-Blockliste für gelöschte RustDesk-IDs;
- hbbs-Online-Statusabfragen;
- unverschlüsselte, verschlüsselte Datenbank- und verschlüsselte Vollbackups;
- signierte Updatepakete, Online-Updateprüfung über GitHub Releases und lokale Updates;
- responsive Darstellung für Smartphone, Tablet und Desktop;
- gehärteter unprivilegierter Containerbetrieb und Docker-Healthcheck.

## Unterstützte Installationswege

### GHCR-Image

```text
ghcr.io/the-ab/rustdesk-addressbook:latest
ghcr.io/the-ab/rustdesk-addressbook:0.6.1
```

Die Image-basierte Installation befindet sich im Ordner `docker-compose/`.

### Release-/Quellarchiv

Das vollständige Release-Archiv verwendet das punktierte Versionsformat:

```text
rustdesk-addressbook-v0.6.1.zip
```

## Update-Infrastruktur

Standardmäßige Update-Basisadresse:

```text
https://github.com/the-ab/RustDesk-AddressBook/releases/latest/download
```

Jedes veröffentlichte Release muss diese Assets gemeinsam enthalten:

```text
latest.txt
rustdesk-addressbook-update-flat-vX.Y.Z.zip
rustdesk-addressbook-update-flat-vX.Y.Z.zip.sha256
rustdesk-addressbook-update-flat-vX.Y.Z.zip.sig
```

Das Komplettarchiv sowie dessen Prüfsummen- und Signaturdateien sind optional, aber als Release-Assets empfohlen.

Updatepakete werden mit dem öffentlichen Ed25519-Schlüssel geprüft:

```text
scripts/keys/update-signing-public-v1.pem
```

Der zugehörige private Signaturschlüssel muss offline bleiben und darf niemals committed, in ein Archiv eingebettet oder als Release-Asset hochgeladen werden.

## Repository-Richtlinie

- GitHub dient für Quellcodeverwaltung, Pull Requests, manuelle Releases und Projektdokumentation.
- Das Repository enthält bewusst keine GitHub-CI, keine Dependabot-Konfiguration und keinen automatischen Container-Build-Workflow.
- Tests und Sicherheitsprüfungen werden vor jedem Release manuell ausgeführt.
- Normale Markdown-Dateien sind englisch; deutsche Fassungen verwenden `*.de.md`.
- Laufzeitdaten, `.env`, Datenbanken, Logs, Backups, heruntergeladene Update-Assets und private Schlüssel dürfen nicht committed werden.
- Release-Dateinamen verwenden das punktierte Format `vX.Y.Z`; kompakte Formen wie `v0601` sind veraltet.

## Aktuelle Dokumentation

- [`HANDOVER.md`](HANDOVER.md) / [`HANDOVER.de.md`](HANDOVER.de.md)
- [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) / [`RELEASE_CHECKLIST.de.md`](RELEASE_CHECKLIST.de.md)
- [`ADMIN-GUIDE.md`](ADMIN-GUIDE.md) / [`ADMIN-GUIDE.de.md`](ADMIN-GUIDE.de.md)
- [`SECURITY.md`](SECURITY.md) / [`SECURITY.de.md`](SECURITY.de.md)
- [`RELEASE_NOTES.md`](RELEASE_NOTES.md) / [`RELEASE_NOTES.de.md`](RELEASE_NOTES.de.md)

## Pflege des Projektstatus

Diese Datei nach jedem Release aktualisieren, wenn sich einer dieser Punkte ändert:

- aktuelle Version oder Release-Datum;
- unterstützter Installationsweg oder Image-Name;
- Update-Infrastruktur oder erforderliche Assets;
- Sicherheitsgrundlage;
- Repository-Richtlinie;
- wesentliche neue oder entfernte Funktionen.
