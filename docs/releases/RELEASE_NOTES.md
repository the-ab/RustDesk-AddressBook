# Community Address Book for RustDesk 0.6.2 – Recovery-code display and update-path reliability

Release date: 2026-08-14

- Fixed regenerated two-factor recovery codes not being displayed after the success message. Transient-secret expiry timestamps now restore explicit UTC timezone information after SQLite round-trips, so the one-time recovery-code payload can be consumed reliably.
- Fixed the source ZIP updater for managed Docker image names. Dotted names such as `rustdesk-addressbook-v0.6.1` are now recognized as project-managed and advanced to `rustdesk-addressbook-v0.6.2`; genuinely custom image names remain untouched.
- Fixed online update discovery in both the Web UI and `scripts/update.sh` so `latest.txt` accepts dotted release filenames such as `rustdesk-addressbook-update-flat-v0.6.2.zip`. The older compact filename form remains readable for backward compatibility.
- **One-time transition note:** an installed 0.6.1 instance cannot auto-discover 0.6.2 through `latest.txt` because the old online parser contains the defect fixed by this release. Copy the signed v0.6.2 triplet into `updates/` once and run `./scripts/update.sh`. The 0.6.1 signature verifier accepts the v0.6.2 package; dotted online discovery works normally afterwards.
- Included the current repository documentation layout under `docs/` and the repository safety validation for mandatory English/German documentation pairs. The updater removes the four obsolete root-level documents that were moved into `docs/`, preventing stale duplicates after an upgrade.
- Revalidated the complete source installer and flat-update package contents against the current `main` branch, including Docker build inputs, update verification files, scripts, templates, static assets, tests, and documentation.
- Kept the established Ed25519 update trust chain unchanged; release ZIPs are signed with the existing v1 release key and verified by the public key embedded in the package.
