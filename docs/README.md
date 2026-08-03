# Documentation

The repository root contains only files that GitHub, installers, contributors, or users commonly expect there. Detailed historical and security-status documents are organized below.

> English is the default documentation language. Every maintained information document must have a substantively equivalent German edition using the same path and filename with `.de.md` before the `.md` suffix. Example: `GUIDE.md` and `GUIDE.de.md`.

## Language and file policy

- `FILE.md` is always English.
- `FILE.de.md` is always German.
- Both editions must be created, moved, renamed, updated, and removed together.
- Links in each language should prefer the matching language edition.
- A pull request that changes one edition must update the other edition in the same scope.
- Technical source files, licenses, machine-readable configuration, generated assets, and code are not information-document language pairs.
- The repository safety check validates the mandatory documentation pairs used by this project.

## User and administrator documentation

- [`../README.md`](../README.md) – project overview and installation
- [`../ADMIN-GUIDE.md`](../ADMIN-GUIDE.md) – detailed administration and operation guide
- [`../docker-compose/README.md`](../docker-compose/README.md) – GHCR Compose environment reference

## Release documentation

- [`releases/RELEASE_NOTES.md`](releases/RELEASE_NOTES.md)
- [`releases/RELEASE_NOTES.de.md`](releases/RELEASE_NOTES.de.md)

## Security documentation

- [`../SECURITY.md`](../SECURITY.md) – vulnerability reporting policy
- [`security/SECURITY-REPORT.md`](security/SECURITY-REPORT.md) – published security status
- [`security/SECURITY-REPORT.de.md`](security/SECURITY-REPORT.de.md) – German security status

## Repository scope

Internal handover documents, private decisions, unreleased plans, and private operational notes are maintained outside this public repository. Secrets, productive configuration, databases, backups, logs, and private signing keys must never be committed.
