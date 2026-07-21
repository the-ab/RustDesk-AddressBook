# Community-Adressbuch für RustDesk 0.5.31 – GitHub-Automatisierungen entfernt

Englische Standardfassung: [`RELEASE_NOTES.md`](RELEASE_NOTES.md)

## Entfernt

- `.github/dependabot.yml` und alle automatischen Vorschläge für Abhängigkeitsupdates.
- `.github/workflows/ci.yml` und alle bei GitHub ausgeführten automatischen Tests und Container-Builds.
- Dokumentationshinweise, die automatische Tests, Abhängigkeitsprüfungen oder Container-Builds bei GitHub beschrieben haben.

## Beibehalten

- Die lokale pytest-Testreihe.
- `scripts/check_repository_safety.py`.
- Ruff-, Bandit-, pip-audit-, Python-, JavaScript- und Shell-Prüfungen zur manuellen Ausführung.
- Manuelle Quellcodebereitstellung und manuell erstellte GitHub-Releases.

## Kompatibilität

An Anwendung, Datenbankschema, Anmeldung, Import, Backup und Update-Verifikation wurde nichts geändert. Bestehende Installationen können normal aktualisiert werden.
