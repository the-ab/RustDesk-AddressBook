# Release Checklist

> English is the default documentation language. The German edition is available as [`RELEASE_CHECKLIST.de.md`](RELEASE_CHECKLIST.de.md).

Use this checklist for every release. Do not publish until all applicable checks are complete.

## 1. Scope and source state

- [ ] The intended release scope is documented and contains no unrelated changes.
- [ ] Work started from the current `main` branch or an explicitly approved base.
- [ ] Open pull requests were checked for overlapping changes.
- [ ] The working tree contains no `.env`, databases, logs, backups, downloaded update assets, private keys, or productive data.
- [ ] `python scripts/check_repository_safety.py` succeeds.
- [ ] No `.github/dependabot.yml` or `.github/workflows/ci.yml` has been introduced.

## 2. Version and release metadata

For release `X.Y.Z`:

- [ ] `VERSION` contains exactly `X.Y.Z`.
- [ ] The application version uses `X.Y.Z` consistently.
- [ ] The release date is updated consistently.
- [ ] The footer displays the current version and release date.
- [ ] Web UI release history includes the new release in English and German.
- [ ] `RELEASE_NOTES.md` and `RELEASE_NOTES.de.md` are updated.
- [ ] `PROJECT_STATUS.md` and `PROJECT_STATUS.de.md` reflect the new current release.
- [ ] Current README and admin-guide examples use `vX.Y.Z`.
- [ ] GHCR examples use `ghcr.io/the-ab/rustdesk-addressbook:X.Y.Z` and `:latest` where appropriate.
- [ ] No compact version forms such as `v0601` remain in current release references.

## 3. Documentation

- [ ] Every regular Markdown document is English by default.
- [ ] Every user-facing German document uses the `*.de.md` suffix.
- [ ] English and German documentation describe the same functionality.
- [ ] `docker-compose/README.md` and `docker-compose/README.de.md` cover every variable in `docker-compose/.env.example`.
- [ ] README, admin guide, security policy, handover, project status, and release checklist links are valid.
- [ ] Independence, trademark, license, and AI-assistance notices remain present where required.
- [ ] Removed or obsolete behavior is no longer described.

## 4. Database and migration safety

- [ ] Upgrade from the previous supported release was tested with an existing database.
- [ ] Existing administrator and user accounts remain usable.
- [ ] Roles, group assignments, OIDC identities, language, and appearance survive migration.
- [ ] No valid user state is silently reset.
- [ ] Security-integrity validation rejects manipulated legacy data.
- [ ] The setup token is absent after an administrator exists.
- [ ] A legitimate empty/reset installation can still generate a new setup token.
- [ ] Backup and restore compatibility was considered for every schema or persistent-file change.

## 5. Authorization and authentication

- [ ] Administrator-only routes return 403 or an equivalent denial for regular users.
- [ ] Regular users see only devices in assigned groups.
- [ ] Ungrouped devices remain administrator-only.
- [ ] Regular users cannot create, edit, or delete devices, groups, users, imports, backups, or settings.
- [ ] Password and sensitive connection actions enforce recent authentication where designed.
- [ ] Password, role, group, and security changes revoke affected sessions.
- [ ] Local login, TOTP 2FA, recovery codes, and OIDC flows remain functional.
- [ ] OIDC binding remains based on issuer and subject.

## 6. Import, export, and blocklist

- [ ] CSV import works with valid data and rejects invalid input safely.
- [ ] RustDesk server database import works for supported paths.
- [ ] SSH import enforces the verified SHA-256 host-key fingerprint.
- [ ] Deleted or manually blocked RustDesk IDs are skipped by every import path.
- [ ] Administrators can unblock IDs intentionally.
- [ ] CSV export remains protected against formula injection.
- [ ] Password export behavior and warnings remain explicit.

## 7. Backup, restore, and update security

- [ ] Plain database backup works.
- [ ] Encrypted database backup works.
- [ ] Encrypted full backup works.
- [ ] Restore rejects path traversal, symlinks, hardlinks, special files, and oversized archives.
- [ ] Restore validates the database before replacing production data.
- [ ] Update ZIP verification requires the matching signed checksum and Ed25519 signature.
- [ ] Modified, unsigned, or mismatched packages are rejected.
- [ ] The private signing key is not present anywhere in the repository or archives.
- [ ] Successful updates move ZIP, checksum, and signature into `updates/installed/`.
- [ ] Failed updates keep diagnostic files in `updates/`.

## 8. Container and deployment

- [ ] Dockerfile uses the intended Debian Trixie-based image.
- [ ] Main application container runs as the intended unprivileged UID/GID.
- [ ] Short-lived init container fixes persistent permissions and is removed automatically.
- [ ] Root filesystem, capability, and privilege restrictions remain in place.
- [ ] `/healthz` reports application and SQLite health.
- [ ] Docker health status becomes `healthy` under HTTP and supported HTTPS/self-signed setups.
- [ ] Source-build Compose remains valid.
- [ ] `docker-compose/compose.yaml` for GHCR remains valid.
- [ ] `docker-compose/.env.example` contains no secrets and matches its documentation.

## 9. Responsive and UI checks

- [ ] Login, setup, 2FA, dashboard, devices, groups, users, import/export, backup, settings, security, help, and account pages render correctly.
- [ ] Mobile checks cover at least 320, 375, and 768 pixel widths.
- [ ] No unintended horizontal page overflow exists.
- [ ] Wide tables remain readable as mobile cards or controlled scroll areas.
- [ ] Login/setup footer remains centered; authenticated footer remains intentional.
- [ ] German and English UI labels remain complete.

## 10. Static and functional checks

Run manually:

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

- [ ] Python compilation succeeds.
- [ ] Ruff reports no errors.
- [ ] Bandit reports no medium or high findings, or every exception is documented.
- [ ] All local pytest tests pass.
- [ ] JavaScript syntax succeeds.
- [ ] Shell syntax succeeds.
- [ ] Jinja templates compile in the real Flask application context.
- [ ] Dependency/CVE scan was run when network access was available; limitations are documented otherwise.

## 11. Package construction

For release `X.Y.Z`, create:

```text
rustdesk-addressbook-update-flat-vX.Y.Z.zip
rustdesk-addressbook-update-flat-vX.Y.Z.zip.sha256
rustdesk-addressbook-update-flat-vX.Y.Z.zip.sig
rustdesk-addressbook-vX.Y.Z.zip
rustdesk-addressbook-vX.Y.Z.zip.sha256
rustdesk-addressbook-vX.Y.Z.zip.sig
latest.txt
```

- [ ] `latest.txt` is provided under exactly that filename.
- [ ] Its first valid line names `rustdesk-addressbook-update-flat-vX.Y.Z.zip`.
- [ ] German and English release summaries are correct.
- [ ] ZIP structure is flat/complete as intended.
- [ ] Executable scripts retain executable permissions.
- [ ] No orphaned, duplicate, cache, test-output, runtime, or private files are included.
- [ ] SHA-256 manifests match the final archives.
- [ ] Ed25519 signatures verify against the embedded public key.
- [ ] Final archives were extracted and checked, not only the source staging directory.

## 12. Pull request and release publication

- [ ] A focused draft pull request was opened.
- [ ] PR description states what changed, why, impact, migration/security concerns, and checks run.
- [ ] Maintainer reviewed and approved the diff and release outputs.
- [ ] PR was merged to `main`.
- [ ] Tag `vX.Y.Z` points to the intended release commit.
- [ ] GitHub release is marked as the latest stable release.
- [ ] `latest.txt`, update ZIP, checksum, and signature were uploaded together.
- [ ] Complete archive, checksum, and signature were uploaded if intended.
- [ ] GHCR tags `X.Y.Z` and `latest` were published through the maintainer-controlled build process.
- [ ] Fixed latest download URLs return the expected files.
- [ ] A clean installation and an upgrade from the previous release were tested from the published assets.

## 13. Session handover

- [ ] `HANDOVER.md` / `HANDOVER.de.md` still describe the current architecture and policies.
- [ ] Current branch, PR number, completed work, tests, known limitations, and next work are recorded.
- [ ] Any release assets stored outside GitHub are clearly identified.
- [ ] No internal-only versioning or private-key details were added to the public repository.
