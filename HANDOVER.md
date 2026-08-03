# Project Handover

> English is the default documentation language. The German edition is available as [`HANDOVER.de.md`](HANDOVER.de.md).

This document is the public technical handover for continuing development in a new chat, with another maintainer, or from a fresh working copy. Keep internal-only decisions outside the public repository.

## Repository identity

- Repository: `the-ab/RustDesk-AddressBook`
- Default branch: `main`
- Current release: read from `VERSION`
- Public image: `ghcr.io/the-ab/rustdesk-addressbook`
- License: Apache-2.0
- Default update endpoint: `https://github.com/the-ab/RustDesk-AddressBook/releases/latest/download`

## Start of every development session

1. Read `VERSION`, `PROJECT_STATUS.md`, `RELEASE_CHECKLIST.md`, `RELEASE_NOTES.md`, and `SECURITY.md`.
2. Inspect the latest commit and all open pull requests.
3. Confirm that the work starts from the current `main` branch or from an explicitly named branch.
4. Do not use a productive installation directory as a source tree.
5. Confirm that no `.env`, database, log, backup, update ZIP, or private key is present in the working tree.
6. Run `python scripts/check_repository_safety.py` before committing.

## Non-negotiable project rules

- Standard Markdown files are English; German editions use `*.de.md`.
- Release archives, checksums, signatures, documentation, and `latest.txt` use dotted versions such as `v0.6.1`.
- `VERSION` contains only the plain semantic version such as `0.6.1`.
- The footer shows the application version and release date.
- Update ZIPs are signed with Ed25519 and accompanied by `.zip.sha256` and `.zip.sig`.
- The private update-signing key must never enter the repository, a release archive, a container image, or GitHub release assets.
- `.github/dependabot.yml` and `.github/workflows/ci.yml` must not be reintroduced.
- GitHub-hosted automatic dependency updates, tests, and container builds are intentionally not part of this repository.
- Local tests and manually executable checks remain part of the project.
- The project is independent and is not affiliated with RustDesk or Purslane Ltd.

## Architecture baseline

- Flask application with SQLite and SQLAlchemy.
- Docker runtime based on Debian Trixie through the official Python slim image.
- Main web container runs unprivileged.
- A short-lived init container prepares persistent directory permissions and is removed automatically.
- Docker health check uses the internal `/healthz` endpoint and validates SQLite availability.
- User roles are `admin` and `user`.
- Regular users can only view and use devices from assigned groups; ungrouped devices are administrator-only.
- Regular users cannot create, edit, or delete devices or administrative data.
- Language and appearance are stored per user.
- OIDC identities are bound by issuer and subject.
- Deleted RustDesk IDs can be retained in the persistent import blocklist.

## Security baseline

Preserve these controls unless a documented replacement is stronger:

- strict server-side role and object authorization;
- global CSRF protection for state-changing requests;
- encrypted stored device passwords and OIDC client secret;
- strict integrity protection for security-relevant user state and group assignments;
- session revocation after password, role, group, or security changes;
- recent reauthentication for sensitive password and connection actions;
- setup token removed after creation of the first administrator;
- safe full-backup restore without symlinks, hardlinks, path traversal, special files, or unbounded extraction;
- SSH import requires a separately verified SHA-256 host-key fingerprint;
- local frontend assets and restrictive CSP;
- signed update verification before extraction;
- non-root runtime and reduced container privileges.

## Release files

For version `X.Y.Z`, build:

```text
rustdesk-addressbook-update-flat-vX.Y.Z.zip
rustdesk-addressbook-update-flat-vX.Y.Z.zip.sha256
rustdesk-addressbook-update-flat-vX.Y.Z.zip.sig
rustdesk-addressbook-vX.Y.Z.zip
rustdesk-addressbook-vX.Y.Z.zip.sha256
rustdesk-addressbook-vX.Y.Z.zip.sig
latest.txt
```

`latest.txt` must be offered under exactly that name and its first valid line must be:

```text
rustdesk-addressbook-update-flat-vX.Y.Z.zip
```

Successful local updates move their ZIP, checksum, and signature into `updates/installed/`.

## Git and pull-request workflow

1. Create a focused branch from `main`, preferably `agent/<description>` for assistant-driven changes.
2. Change only files belonging to the requested scope.
3. Update both documentation languages when user-visible behavior changes.
4. Update `VERSION`, application version, release date, release notes, Web UI release history, image tags, examples, and `latest.txt` together for a release.
5. Run all checks from `RELEASE_CHECKLIST.md`.
6. Commit with a concise scope-specific message.
7. Push the branch and open a draft pull request.
8. Merge only after the maintainer has reviewed the diff and release outputs.

## GitHub release workflow

GitHub releases are manual by project policy.

1. Merge the approved release PR.
2. Create tag `vX.Y.Z` from the intended release commit.
3. Create the GitHub release and mark it as the latest stable release.
4. Upload `latest.txt`, update ZIP, update checksum, and update signature together.
5. Optionally upload the complete archive and its checksum/signature.
6. Publish GHCR tags `X.Y.Z` and `latest` through the separate maintainer-controlled build process.
7. Verify the fixed latest URLs after publication.

## End of every development session

Update these documents when relevant:

- `PROJECT_STATUS.md` / `PROJECT_STATUS.de.md`
- `HANDOVER.md` / `HANDOVER.de.md`
- `RELEASE_CHECKLIST.md` / `RELEASE_CHECKLIST.de.md`
- `RELEASE_NOTES.md` / `RELEASE_NOTES.de.md`

Record:

- current branch and pull-request number;
- implemented and tested changes;
- known limitations or unverified areas;
- next intended version;
- release assets already built and where they are stored;
- any migration, backup, restore, security, or compatibility risk.

## New-chat startup prompt

A new development chat can start with:

```text
Continue the RustDesk AddressBook project from repository the-ab/RustDesk-AddressBook. Read VERSION, PROJECT_STATUS.md, HANDOVER.md, RELEASE_CHECKLIST.md, RELEASE_NOTES.md, and SECURITY.md first. Inspect the latest main branch and open pull requests before making changes. Preserve all documented repository, security, versioning, signing, documentation-language, and release rules.
```
