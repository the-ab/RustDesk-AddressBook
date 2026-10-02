# Community Address Book for RustDesk — release notes

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

## Community Address Book for RustDesk 0.6.2 – Recovery-code display and update-path reliability

Release date: 2026-08-14

- Fixed regenerated two-factor recovery codes not being displayed after the success message. Transient-secret expiry timestamps now restore explicit UTC timezone information after SQLite round-trips, so the one-time recovery-code payload can be consumed reliably.
- Fixed the source ZIP updater for managed Docker image names. Dotted names such as `rustdesk-addressbook-v0.6.1` are now recognized as project-managed and advanced to `rustdesk-addressbook-v0.6.2`; genuinely custom image names remain untouched.
- Fixed online update discovery in both the Web UI and `scripts/update.sh` so `latest.txt` accepts dotted release filenames such as `rustdesk-addressbook-update-flat-v0.6.2.zip`. The older compact filename form remains readable for backward compatibility.
- **One-time transition note:** an installed 0.6.1 instance cannot auto-discover 0.6.2 through `latest.txt` because the old online parser contains the defect fixed by this release. Copy the signed v0.6.2 triplet into `updates/` once and run `./scripts/update.sh`. The 0.6.1 signature verifier accepts the v0.6.2 package; dotted online discovery works normally afterwards.
- Included the current repository documentation layout under `docs/` and the repository safety validation for mandatory English/German documentation pairs. The updater removes the four obsolete root-level documents that were moved into `docs/`, preventing stale duplicates after an upgrade.
- Revalidated the complete source installer and flat-update package contents against the current `main` branch, including Docker build inputs, update verification files, scripts, templates, static assets, tests, and documentation.
- Kept the established Ed25519 update trust chain unchanged; release ZIPs are signed with the existing v1 release key and verified by the public key embedded in the package.
