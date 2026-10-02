# Signed updates

From an installed 0.6.3, use the normal signed update path. If update.sh is not executable, invoke `bash scripts/update.sh` until 0.6.4 restores the shipped script permissions.

Before the first source upgrade from 0.6.2, follow the [one-time updater preparation](../ADMIN-GUIDE.md#source-upgrade-from-062). The 0.6.4 candidate is transferred locally until it is published on GitHub.

Copy a flat update ZIP and both matching verification sidecars into this directory:

```bash
cp /path/to/rustdesk-addressbook-update-flat-v0.6.4.zip updates/
cp /path/to/rustdesk-addressbook-update-flat-v0.6.4.zip.sha256 updates/
cp /path/to/rustdesk-addressbook-update-flat-v0.6.4.zip.sig updates/
./scripts/update.sh
```

After a successful installation and a healthy container check, the ZIP, checksum manifest, and signature are moved to `updates/installed/`. Failed or inconclusive updates remain in `updates/` for diagnosis. The permission preparation runs as `docker compose run --rm rustdesk-addressbook-init`, so no stopped init container is retained.

The updater selects the highest local `rustdesk-addressbook-update-flat-v*.zip`, validates the signed SHA-256 manifest with the embedded Ed25519 public key, checks the ZIP structure, creates a rollback backup, and installs the package only when it is newer.

Online checks use `https://github.com/the-ab/RustDesk-AddressBook/releases/latest/download` by default. The latest published release must provide `latest.txt`, the ZIP named in it, `.zip.sha256`, and `.zip.sig`. Set `RAB_UPDATE_BASE_URL=disabled` to turn online checks off explicitly. Never store the private release-signing key in this directory or in the repository.

The German edition is available as [`README.de.md`](README.de.md).
