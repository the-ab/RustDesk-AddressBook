# Community-Adressbuch für RustDesk 0.5.30 – Vorbereitung für GitHub-Veröffentlichung

Englische Standardfassung: [`RELEASE_NOTES.md`](RELEASE_NOTES.md)

## Ergänzt

- Apache License 2.0 und Projektdatei `NOTICE`.
- `.gitignore`-Schutz für lokale Konfiguration, Datenbanken, Logs, Backups, heruntergeladene Update-Dateien, private TLS-Schlüssel und private Release-Signaturschlüssel.
- `SECURITY.md` und `CONTRIBUTING.md` einschließlich deutscher `*.de.md`-Fassungen.
- GitHub-Actions-CI für Repository-Richtlinie, Python-/JavaScript-/Shell-Prüfungen, Ruff, Bandit, pytest, Abhängigkeitsprüfung und Docker-Build.
- Dependabot-Konfiguration für Python, Docker und GitHub Actions.
- Erste automatisierte Tests für Setup-Token, Rollen-/Gruppensichtbarkeit, Sperre administrativer Bereiche, Healthcheck, Ablehnung von Links im Restore, CSV-Formelschutz und deaktivierte Online-Updates.
- Repository-Sicherheitsprüfung unter `scripts/check_repository_safety.py`.

## Geändert

- Das Projekt wird eindeutig als unabhängiges Community-Projekt dargestellt und enthält einen klaren RustDesk-/Purslane-Zugehörigkeits- und Markenhinweis.
- Transparenter Hinweis auf Unterstützung durch OpenAI ChatGPT und Verantwortung des Maintainers ergänzt.
- `RAB_UPDATE_BASE_URL` ist standardmäßig leer. Online-Update-Prüfungen bleiben deaktiviert, bis eine vertrauenswürdige Quelle gesetzt wird; lokale signierte Updates funktionieren weiterhin.
- Bestehende Installationen behalten beim Upgrade ihren aktuellen Update-URL-Wert aus `.env`.
- Dokumentationsbeispiele setzen den bisherigen vom Maintainer betriebenen Downloaddienst nicht mehr voraus und beschreiben stattdessen Repository-Releases oder einen selbst kontrollierten signierten Mirror.

## Kompatibilität

Datenbankschema sowie Geräte- und Benutzerfunktionen wurden nicht verändert. Bestehende Installationen können regulär aktualisiert werden und behalten ihre lokale Konfiguration.
