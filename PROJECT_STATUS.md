# Project Status

> English is the default documentation language. The German edition is available as [`PROJECT_STATUS.de.md`](PROJECT_STATUS.de.md).

**Last updated:** 2026-08-03  
**Current release:** `0.6.1`  
**Release date:** 2026-07-31  
**Repository:** `the-ab/RustDesk-AddressBook`  
**Default branch:** `main`  
**License:** Apache-2.0

## Current product state

Community Address Book for RustDesk is a self-hosted Flask/SQLite web application delivered as a Docker project and as a prebuilt GHCR image.

Implemented areas include:

- device and group management with encrypted stored RustDesk passwords;
- local users, administrator/user roles, TOTP 2FA, recovery codes, and OIDC;
- per-user language and light/dark appearance settings;
- group-scoped visibility for regular users and administrator-only access to ungrouped devices;
- CSV, RustDesk server database, direct database, and SSH snapshot imports;
- persistent import blocklist for deleted RustDesk IDs;
- hbbs online-state checks;
- plain, encrypted database, and encrypted full backups;
- signed update packages, online update discovery through GitHub Releases, and local updates;
- responsive smartphone, tablet, and desktop layouts;
- hardened non-root container runtime and Docker health check.

## Supported installation paths

### GHCR image

```text
ghcr.io/the-ab/rustdesk-addressbook:latest
ghcr.io/the-ab/rustdesk-addressbook:0.6.1
```

The image-based installation files are in `docker-compose/`.

### Release/source archive

The complete release archive is named with the dotted version format:

```text
rustdesk-addressbook-v0.6.1.zip
```

## Update infrastructure

Default update base URL:

```text
https://github.com/the-ab/RustDesk-AddressBook/releases/latest/download
```

Every published release must provide these assets together:

```text
latest.txt
rustdesk-addressbook-update-flat-vX.Y.Z.zip
rustdesk-addressbook-update-flat-vX.Y.Z.zip.sha256
rustdesk-addressbook-update-flat-vX.Y.Z.zip.sig
```

The complete archive and its checksum/signature files are optional but recommended release assets.

Update packages are verified with the public Ed25519 key stored at:

```text
scripts/keys/update-signing-public-v1.pem
```

The matching private signing key must remain offline and must never be committed, embedded in an archive, or uploaded to a release.

## Repository policy

- GitHub is used for source control, pull requests, manual releases, and project documentation.
- The repository intentionally contains no GitHub-hosted CI workflow, Dependabot configuration, or automatic container-build workflow.
- Tests and security checks are executed manually before each release.
- Standard Markdown files are English. German editions use the `*.de.md` suffix.
- Runtime data, `.env`, databases, logs, backups, downloaded update assets, and private keys must never be committed.
- Release asset names use the dotted form `vX.Y.Z`; compact forms such as `v0601` are obsolete.

## Current documentation set

- [`HANDOVER.md`](HANDOVER.md) / [`HANDOVER.de.md`](HANDOVER.de.md)
- [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) / [`RELEASE_CHECKLIST.de.md`](RELEASE_CHECKLIST.de.md)
- [`ADMIN-GUIDE.md`](ADMIN-GUIDE.md) / [`ADMIN-GUIDE.de.md`](ADMIN-GUIDE.de.md)
- [`SECURITY.md`](SECURITY.md) / [`SECURITY.de.md`](SECURITY.de.md)
- [`RELEASE_NOTES.md`](RELEASE_NOTES.md) / [`RELEASE_NOTES.de.md`](RELEASE_NOTES.de.md)

## Status maintenance

Update this file after every release when any of the following changes:

- current version or release date;
- supported installation path or image name;
- update infrastructure or required assets;
- security baseline;
- repository policy;
- major implemented or removed functionality.
