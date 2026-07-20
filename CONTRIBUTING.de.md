# Beitragen

Englische Standardfassung: [`CONTRIBUTING.md`](CONTRIBUTING.md)

Beiträge sind willkommen, wenn sie das Sicherheitsmodell, die Update-Kompatibilität und die englisch/deutsche Dokumentationsstruktur erhalten.

## Vor einem Pull Request

1. Einen klar abgegrenzten Branch verwenden und unabhängige Änderungen trennen.
2. Niemals produktive Daten, `.env`, Datenbanken, Logs, Backups, private Schlüssel, Tokens oder heruntergeladene Update-Artefakte committen.
3. Bei funktionalen Änderungen automatisierte Tests ergänzen oder anpassen.
4. Bei Verhaltensänderungen sowohl die englische `*.md`-Datei als auch die passende deutsche `*.de.md`-Fassung aktualisieren.
5. Für Releases `RELEASE_NOTES.md`, `RELEASE_NOTES.de.md` und die WebUI-Release-Historie aktualisieren.
6. Die nachstehenden Prüfungen ausführen.

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

## Sicherheitsrelevante Änderungen

Änderungen an Anmeldung, OIDC, Verschlüsselung, Backup/Restore, Updateprüfung, SSH-Import, Berechtigungen oder Sitzungen benötigen Tests für erlaubte und abgewiesene Abläufe. Schwachstellen müssen entsprechend [`SECURITY.md`](SECURITY.md) privat gemeldet werden.

## Lizenzierung

Mit einem Beitrag stimmst du zu, dass dieser unter der in [`LICENSE`](LICENSE) enthaltenen Apache License 2.0 veröffentlicht werden darf. Es dürfen nur Code und Inhalte eingereicht werden, für die die erforderlichen Rechte bestehen. Drittanbieterhinweise müssen erhalten und bei Bedarf ergänzt werden.

## KI-unterstützte Beiträge

KI-unterstützter Code ist zulässig, wenn er durch den Beitragenden geprüft, angepasst und getestet wurde. Der Beitragende bleibt für Korrektheit, Lizenzierung, Sicherheit und die Offenlegung im Pull Request verantwortlich.
