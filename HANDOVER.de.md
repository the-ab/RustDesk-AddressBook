# Projektübergabe

> Die englische Dokumentation ist die Standardfassung. Diese Datei ist die deutsche Ausgabe von [`HANDOVER.md`](HANDOVER.md).

Dieses Dokument ist die öffentliche technische Übergabe für die Fortsetzung der Entwicklung in einem neuen Chat, durch einen anderen Maintainer oder aus einer frischen Arbeitskopie. Ausschließlich interne Entscheidungen gehören nicht in das öffentliche Repository.

## Repository-Identität

- Repository: `the-ab/RustDesk-AddressBook`
- Standardbranch: `main`
- Aktuelle Version: aus `VERSION` lesen
- Öffentliches Image: `ghcr.io/the-ab/rustdesk-addressbook`
- Lizenz: Apache-2.0
- Standardmäßiger Update-Endpunkt: `https://github.com/the-ab/RustDesk-AddressBook/releases/latest/download`

## Beginn jeder Entwicklungssitzung

1. `VERSION`, `PROJECT_STATUS.de.md`, `RELEASE_CHECKLIST.de.md`, `RELEASE_NOTES.de.md` und `SECURITY.de.md` lesen.
2. Den neuesten Commit und alle offenen Pull Requests prüfen.
3. Sicherstellen, dass die Arbeit vom aktuellen `main`-Branch oder von einem ausdrücklich genannten Branch ausgeht.
4. Kein produktives Installationsverzeichnis als Quellbaum verwenden.
5. Prüfen, dass keine `.env`, Datenbank, Logs, Backups, Update-ZIPs oder privaten Schlüssel im Arbeitsbaum liegen.
6. Vor dem Commit `python scripts/check_repository_safety.py` ausführen.

## Verbindliche Projektregeln

- Standard-Markdown-Dateien sind englisch; deutsche Fassungen verwenden `*.de.md`.
- Release-Archive, Prüfsummen, Signaturen, Dokumentation und `latest.txt` verwenden punktierte Versionen wie `v0.6.1`.
- `VERSION` enthält nur die reine semantische Version, beispielsweise `0.6.1`.
- Die Fußzeile zeigt Anwendungsversion und Release-Datum.
- Update-ZIPs werden mit Ed25519 signiert und besitzen passende `.zip.sha256`- und `.zip.sig`-Dateien.
- Der private Update-Signaturschlüssel darf niemals in das Repository, ein Release-Archiv, ein Container-Image oder GitHub-Release-Assets gelangen.
- `.github/dependabot.yml` und `.github/workflows/ci.yml` dürfen nicht erneut hinzugefügt werden.
- Automatische GitHub-Abhängigkeitsupdates, Tests und Container-Builds sind bewusst nicht Bestandteil dieses Repositorys.
- Lokale Tests und manuell ausführbare Prüfungen bleiben Bestandteil des Projekts.
- Das Projekt ist unabhängig und nicht mit RustDesk oder Purslane Ltd. verbunden.

## Architekturgrundlage

- Flask-Anwendung mit SQLite und SQLAlchemy.
- Docker-Laufzeit auf Debian Trixie über das offizielle Python-Slim-Image.
- Der Webcontainer läuft unprivilegiert.
- Ein kurzlebiger Init-Container bereitet die Rechte persistenter Verzeichnisse vor und wird automatisch entfernt.
- Der Docker-Healthcheck verwendet `/healthz` und prüft die SQLite-Erreichbarkeit.
- Benutzerrollen sind `admin` und `user`.
- Normale Benutzer können nur Geräte zugewiesener Gruppen sehen und verwenden; ungruppierte Geräte sind ausschließlich für Administratoren sichtbar.
- Normale Benutzer dürfen keine Geräte oder administrativen Daten anlegen, bearbeiten oder löschen.
- Sprache und Darstellung werden pro Benutzer gespeichert.
- OIDC-Identitäten werden über Issuer und Subject gebunden.
- Gelöschte RustDesk-IDs können in der persistenten Import-Blockliste gehalten werden.

## Sicherheitsgrundlage

Diese Kontrollen beibehalten, solange keine dokumentierte stärkere Lösung eingesetzt wird:

- strikte serverseitige Rollen- und Objektberechtigungen;
- globaler CSRF-Schutz für zustandsändernde Requests;
- verschlüsselt gespeicherte Gerätepasswörter und OIDC-Client-Secret;
- strikter Integritätsschutz für sicherheitsrelevanten Benutzerzustand und Gruppenzuweisungen;
- Sitzungswiderruf nach Passwort-, Rollen-, Gruppen- oder Sicherheitsänderungen;
- erneute Anmeldung für sensible Passwort- und Verbindungsaktionen;
- Entfernung des Setup-Tokens nach Erstellung des ersten Administrators;
- sicherer Vollbackup-Restore ohne Symlinks, Hardlinks, Pfad-Traversal, Spezialdateien oder unbegrenztes Entpacken;
- SSH-Import nur mit separat geprüftem SHA-256-Hostschlüssel-Fingerprint;
- lokale Frontend-Ressourcen und restriktive CSP;
- Signaturprüfung von Updates vor dem Entpacken;
- unprivilegierte Laufzeit und reduzierte Containerrechte.

## Release-Dateien

Für Version `X.Y.Z` erstellen:

```text
rustdesk-addressbook-update-flat-vX.Y.Z.zip
rustdesk-addressbook-update-flat-vX.Y.Z.zip.sha256
rustdesk-addressbook-update-flat-vX.Y.Z.zip.sig
rustdesk-addressbook-vX.Y.Z.zip
rustdesk-addressbook-vX.Y.Z.zip.sha256
rustdesk-addressbook-vX.Y.Z.zip.sig
latest.txt
```

`latest.txt` muss direkt unter genau diesem Namen angeboten werden. Die erste gültige Zeile lautet:

```text
rustdesk-addressbook-update-flat-vX.Y.Z.zip
```

Erfolgreich installierte lokale Updates verschieben ZIP, Prüfsumme und Signatur nach `updates/installed/`.

## Git- und Pull-Request-Ablauf

1. Einen klar abgegrenzten Branch von `main` erstellen, für assistentengesteuerte Änderungen vorzugsweise `agent/<beschreibung>`.
2. Nur Dateien ändern, die zum angeforderten Umfang gehören.
3. Bei sichtbaren Funktionsänderungen beide Dokumentationssprachen aktualisieren.
4. Für ein Release `VERSION`, Anwendungsversion, Release-Datum, Release Notes, WebUI-Release-Historie, Image-Tags, Beispiele und `latest.txt` gemeinsam aktualisieren.
5. Alle Prüfungen aus `RELEASE_CHECKLIST.de.md` ausführen.
6. Mit einer kurzen, auf den Umfang bezogenen Nachricht committen.
7. Branch pushen und einen Draft-Pull-Request öffnen.
8. Erst nach Prüfung von Diff und Release-Ausgaben durch den Maintainer mergen.

## GitHub-Release-Ablauf

GitHub-Releases erfolgen gemäß Projektvorgabe manuell.

1. Den freigegebenen Release-PR mergen.
2. Tag `vX.Y.Z` auf dem vorgesehenen Release-Commit erstellen.
3. GitHub-Release erstellen und als neuestes stabiles Release markieren.
4. `latest.txt`, Update-ZIP, Update-Prüfsumme und Update-Signatur gemeinsam hochladen.
5. Optional Komplettarchiv und dessen Prüfsumme/Signatur hochladen.
6. GHCR-Tags `X.Y.Z` und `latest` über den separaten, vom Maintainer kontrollierten Buildprozess veröffentlichen.
7. Nach Veröffentlichung die festen Latest-URLs prüfen.

## Ende jeder Entwicklungssitzung

Bei Bedarf diese Dokumente aktualisieren:

- `PROJECT_STATUS.md` / `PROJECT_STATUS.de.md`
- `HANDOVER.md` / `HANDOVER.de.md`
- `RELEASE_CHECKLIST.md` / `RELEASE_CHECKLIST.de.md`
- `RELEASE_NOTES.md` / `RELEASE_NOTES.de.md`

Festhalten:

- aktueller Branch und Pull-Request-Nummer;
- umgesetzte und getestete Änderungen;
- bekannte Einschränkungen oder ungeprüfte Bereiche;
- nächste vorgesehene Version;
- bereits erzeugte Release-Assets und deren Ablageort;
- Migrations-, Backup-, Restore-, Sicherheits- oder Kompatibilitätsrisiken.

## Starttext für einen neuen Chat

```text
Setze das Projekt RustDesk AddressBook aus dem Repository the-ab/RustDesk-AddressBook fort. Lies zuerst VERSION, PROJECT_STATUS.de.md, HANDOVER.de.md, RELEASE_CHECKLIST.de.md, RELEASE_NOTES.de.md und SECURITY.de.md. Prüfe vor Änderungen den neuesten main-Branch und offene Pull Requests. Halte alle dokumentierten Repository-, Sicherheits-, Versions-, Signatur-, Sprach- und Release-Regeln ein.
```
