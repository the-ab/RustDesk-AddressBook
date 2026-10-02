# Community Address Book for RustDesk — release notes

## Community Address Book for RustDesk 0.6.4 – Shell script permissions and documentation

Version date: 2026-10-02. Status: signed source candidate; GitHub release and GHCR image not yet published.

- Store all five shipped shell scripts as executable in Git and both ZIP packages; restore execute bits explicitly after ZIP extraction.
- Add complete 0.6.3 and 0.6.4 entries to the English/German Web UI release history and align current installation/help/update examples.
- Allow installed 0.6.3 source installations to apply this signed 0.6.4 maintenance update normally; if the old updater lacks execute permission, start it with bash.

For an installed 0.6.3 with missing execute bits, run `bash scripts/update.sh /path/to/rustdesk-addressbook-update-flat-v0.6.4.zip`. The normal signature/SHA checks, persistence snapshot and rollback remain active. For an installed 0.6.2, follow the [one-time updater preparation](../../ADMIN-GUIDE.md#source-upgrade-from-062) first.

## Community Address Book for RustDesk 0.6.3 – Restore, import and update reliability

Version date: 2026-10-02. Status: signed source candidate; GitHub release and GHCR image not yet published.

- Validate supported SQLite schemas, group references, user signatures and encrypted fields before restoring a database.
- Protect full restores with an exclusive maintenance lock and a durable rollback journal; recover interrupted restores at application startup and reload keys across web workers.
- Create unique backup filenames without overwriting existing backups.
- Query each RustDesk ID once per hbbs batch and update every device sharing that ID.
- Reject malformed CSV and ambiguous database/WAL/SHM ZIP filenames before import; complete batch queries before changing device status.
- Load settings once per request and invalidate the cache when settings change.
- Stop the service before snapshotting configured data/backup paths and all managed sources; roll back ZIP updates on build, start or health failure and report a health timeout as failure.
- Serialize updater invocations with flock and target only the configured container name.
- Update cryptography to 50.0.2, requests to 2.34.2, pytest to 9.1.1 and the Python container base to 3.13.15.
- Align English/German documentation, installation examples, Web UI help and release history with 0.6.3.

### Upgrade notes

Before the first source upgrade from 0.6.2, verify the signed new package and install both corrected updater files as described in the [Admin Guide](../../ADMIN-GUIDE.md#source-upgrade-from-062). The updater shipped in 0.6.2 does not provide the new complete rollback. Keep the pre-update backup.

After a full restore, sign in again. Restart the container if TLS certificates were restored. If concurrent requests prevent the exclusive restore lock, retry during a quiet period. GHCR installations use their published image update path.

## Community Address Book for RustDesk 0.6.2 – Recovery-code display and update-path reliability

Release date: 2026-08-14

- Fixed regenerated two-factor recovery codes not being displayed after the success message. Transient-secret expiry timestamps now restore explicit UTC timezone information after SQLite round-trips, so the one-time recovery-code payload can be consumed reliably.
- Fixed the source ZIP updater for managed Docker image names. Dotted names such as `rustdesk-addressbook-v0.6.1` are now recognized as project-managed and advanced to `rustdesk-addressbook-v0.6.2`; genuinely custom image names remain untouched.
- Fixed online update discovery in both the Web UI and `scripts/update.sh` so `latest.txt` accepts dotted release filenames such as `rustdesk-addressbook-update-flat-v0.6.2.zip`. The older compact filename form remains readable for backward compatibility.
- **One-time transition note:** an installed 0.6.1 instance cannot auto-discover 0.6.2 through `latest.txt` because the old online parser contains the defect fixed by this release. Copy the signed v0.6.2 triplet into `updates/` once and run `./scripts/update.sh`. The 0.6.1 signature verifier accepts the v0.6.2 package; dotted online discovery works normally afterwards.
- Included the current repository documentation layout under `docs/` and the repository safety validation for mandatory English/German documentation pairs. The updater removes the four obsolete root-level documents that were moved into `docs/`, preventing stale duplicates after an upgrade.
- Revalidated the complete source installer and flat-update package contents against the current `main` branch, including Docker build inputs, update verification files, scripts, templates, static assets, tests, and documentation.
- Kept the established Ed25519 update trust chain unchanged; release ZIPs are signed with the existing v1 release key and verified by the public key embedded in the package.
