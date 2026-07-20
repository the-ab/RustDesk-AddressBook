# Contributing

German edition: [`CONTRIBUTING.de.md`](CONTRIBUTING.de.md)

Contributions are welcome when they preserve the project's security model, upgrade compatibility, and English/German documentation structure.

## Before opening a pull request

1. Create a focused branch and keep unrelated changes separate.
2. Never commit production data, `.env`, databases, logs, backups, private keys, tokens, or downloaded update artifacts.
3. Add or update automated tests for functional changes.
4. Update both the English `*.md` documentation and the matching German `*.de.md` edition when behavior changes.
5. Update `RELEASE_NOTES.md`, `RELEASE_NOTES.de.md`, and the WebUI release history when preparing a release.
6. Run the checks below.

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

## Security-sensitive changes

Changes to authentication, OIDC, encryption, backup/restore, update verification, SSH import, permissions, or session handling require tests for both allowed and denied behavior. Security vulnerabilities must be reported privately according to [`SECURITY.md`](SECURITY.md).

## Licensing

By submitting a contribution, you agree that it may be distributed under the Apache License 2.0 contained in [`LICENSE`](LICENSE). Only submit code and assets that you have the right to contribute. Preserve third-party notices and add new notices when required.

## AI-assisted contributions

AI-assisted code is accepted only when the contributor has reviewed, adapted, and tested it. The contributor remains responsible for correctness, licensing, security, and disclosure in the pull request.
