# Community Address Book for RustDesk — Security Status 0.5.31

**Date:** July 21, 2026  
**Version:** `0.5.31-github-automation-removal`

> English is the default documentation language. The German edition is available as [`SECURITY-REPORT.de.md`](SECURITY-REPORT.de.md).

## Addressed security areas

- Update packages are verified before extraction using Ed25519 and a signed SHA-256 checksum.
- Full-backup restore accepts only regular files in approved paths and limits member count, individual file size, and total extracted size.
- Existing 0.5.26 user signatures are migrated only after successful validation of the old signature format. From 0.5.27 onward, signatures also cover group assignments and session state.
- Security-relevant account changes revoke existing sessions.
- OIDC identities are bound only by issuer and `sub`; domain filters require `email_verified=true`.
- Initial setup requires a server-generated setup token.
- Password retrieval, RustDesk connection start, and password CSV export require recent authentication and are audited.
- SSH import requires a previously verified SHA-256 host-key fingerprint and uses `StrictHostKeyChecking=yes`.
- CSV formula injection, stored icon DOM injection, unlimited authentication-event growth, and external JavaScript dependencies have been addressed.
- The main container runs as an unprivileged user with dropped capabilities, `no-new-privileges`, a read-only root filesystem, and a limited tmpfs.
- Python dependencies and the Python base image are pinned to explicit versions.

## Intentionally retained operating options

- HTTP can still be enabled explicitly, but remains disabled by default. HTTPS is required for production access.
- Private OIDC issuers remain possible but must be explicitly allowed with `OIDC_ALLOW_PRIVATE_ISSUER=true`.
- Unsigned local updates are available only as an explicit interactive emergency path through `RAB_ALLOW_UNSIGNED_LOCAL_UPDATES=true`; automated unsigned updates remain blocked.
- The SQLite database is not fully encrypted. Device passwords and the OIDC client secret are encrypted field by field. Protect and back up `data/config.json` accordingly.

## Migration note

The old 0.5.26 signature format did not include group assignments. During the one-time upgrade, existing assignments are accepted only after the old user identity has been validated and are then protected by the new signature format. Direct changes to roles, identity, session state, or group assignments are detected after migration and block login or the active session.

## Container runtime and health

The web process remains unprivileged. A separate short-lived init service receives only the capabilities required to prepare persistent directory permissions. The health check verifies the listener and SQLite connection. The base image uses Debian Trixie.

## Documentation language layout

Standard Markdown files are English and German editions use the `*.de.md` suffix. Version 0.5.31 removes GitHub-hosted automation. Repository safety checks, the local test suite, dependency auditing tools, and the private vulnerability-reporting policy remain available for manual use. This repository change does not weaken the existing runtime controls.


## Public repository note

The repository is prepared for public source publication, but production data, `.env` files, databases, backups, logs, TLS private keys, and private release-signing keys must never be committed. Run `python scripts/check_repository_safety.py` before every initial or release push. Security reports should follow [`SECURITY.md`](SECURITY.md) and must not be opened publicly before coordinated remediation.
