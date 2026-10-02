# Community Address Book for RustDesk — security status, candidate 0.6.3

## 0.6.3 candidate — restore and import reliability

Prepared on 2026-10-02; this source candidate has not been released. Published image examples below refer to 0.6.2 until a new image is published.

- Restores validate supported SQLite schema, group references, user signatures and encrypted fields before replacing data. Full restores use an exclusive maintenance lock and a durable rollback journal. An interrupted restore blocks requests until startup recovery restores the previous generation. Runtime keys reload across workers; sign in again after restore. Restart the container after restoring TLS certificates.
- Backup names are unique and existing backups are never replaced. Duplicate RustDesk IDs share one hbbs query and every matching device receives the result. Malformed CSV and ambiguous DB/WAL/SHM ZIP names are rejected before import. Settings are loaded once per request and invalidated on changes.
- The corrected ZIP updater stops the service before backing up the configured `RAB_DATA_DIR` and `RAB_BACKUP_DIR`, saves the complete managed source set and local configuration, and rolls back on build/start/health failure. A health timeout returns failure. The update directory serializes concurrent updater invocations with `flock` (util-linux).
- Runtime dependencies: cryptography 50.0.2, requests 2.34.2; test dependency: pytest 9.1.1; Python container base: 3.13.15.

### Source upgrade from 0.6.2

The updater already installed in 0.6.2 has no complete rollback. Before the first upgrade, verify the new flat ZIP and its checksum signature with your existing trusted public key, then install both corrected updater files into the existing `scripts/` directory:

```bash
openssl pkeyutl -verify -pubin -inkey scripts/keys/update-signing-public-v1.pem -rawin -in /path/to/rustdesk-addressbook-update-flat-v0.6.3.zip.sha256 -sigfile /path/to/rustdesk-addressbook-update-flat-v0.6.3.zip.sig
(cd /path/to && sha256sum -c rustdesk-addressbook-update-flat-v0.6.3.zip.sha256)
unzip -o /path/to/rustdesk-addressbook-update-flat-v0.6.3.zip scripts/update.sh scripts/update_transaction.py -d .
bash scripts/update.sh /path/to/rustdesk-addressbook-update-flat-v0.6.3.zip
```

Keep the generated pre-update directory. If the host or updater is killed before automatic rollback completes, stop the service and run `python3 /path/to/preupdate/update_transaction.py rollback /path/to/preupdate`, then build/start the restored Compose installation and check its health. Do not start a second update against a partially restored installation. For GHCR installations, pull/recreate the chosen published image through `docker-compose/`; the source ZIP updater is for source installations.

## Published baseline 0.6.2

**Date:** August 14, 2026  
**Version:** `0.6.2-recovery-codes-update-image-fix`

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

The web process remains unprivileged. A separate profiled init service receives only the capabilities required to prepare persistent directory permissions and is invoked as `docker compose run --rm`, so Docker removes it immediately after completion. The health check verifies the listener and SQLite connection. The base image uses Debian Trixie.

## Documentation language layout

Standard Markdown files are English and German editions use the `*.de.md` suffix. Version 0.6.2 fixes one-time display of regenerated recovery codes by restoring explicit UTC semantics for transient SQLite timestamps and corrects the managed Docker image name in the source-update path. Existing signed-update verification, authorization boundaries, setup-token cleanup, repository safety checks, and the local test suite remain in place.

## Public repository note

The repository is prepared for public source publication, but production data, `.env` files, databases, backups, logs, TLS private keys, and private release-signing keys must never be committed. Run `python scripts/check_repository_safety.py` before every initial or release push. Security reports should follow [`../../SECURITY.md`](../../SECURITY.md) and must not be opened publicly before coordinated remediation.
