# Signed updates

Copy a flat update ZIP and both matching verification sidecars into this directory:

```bash
cp /path/to/rustdesk-addressbook-update-flat-v0531.zip updates/
cp /path/to/rustdesk-addressbook-update-flat-v0531.zip.sha256 updates/
cp /path/to/rustdesk-addressbook-update-flat-v0531.zip.sig updates/
./scripts/update.sh
```

The updater selects the highest local `rustdesk-addressbook-update-flat-v*.zip`, validates the signed SHA-256 manifest with the embedded Ed25519 public key, checks the ZIP structure, creates a rollback backup, and installs the package only when it is newer.

Online checks are optional and disabled when `RAB_UPDATE_BASE_URL` is empty. A configured source must provide `latest.txt`, the ZIP, `.zip.sha256`, and `.zip.sig`. Never store the private release-signing key in this directory or in the repository.

The German edition is available as [`README.de.md`](README.de.md).
