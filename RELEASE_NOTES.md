# Community Address Book for RustDesk 0.5.31 – GitHub automation removal

German edition: [`RELEASE_NOTES.de.md`](RELEASE_NOTES.de.md)

## Removed

- `.github/dependabot.yml` and all automatic dependency-update configuration.
- `.github/workflows/ci.yml` and all GitHub-hosted test and container-build automation.
- Documentation statements that implied tests, dependency audits, or container builds run automatically on GitHub.

## Retained

- The local pytest test suite.
- `scripts/check_repository_safety.py`.
- Ruff, Bandit, pip-audit, Python, JavaScript, and Shell checks that can be run manually.
- Manual source publication and manually created GitHub releases.

## Compatibility

No application behavior, database schema, authentication, import, backup, or update-verification behavior was changed. Existing installations can update normally.
