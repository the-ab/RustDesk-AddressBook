# Signed updates

Copy a flat update ZIP and both matching verification sidecars into this directory:

```bash
cp /path/to/rustdesk-addressbook-update-flat-v0532.zip updates/
cp /path/to/rustdesk-addressbook-update-flat-v0532.zip.sha256 updates/
cp /path/to/rustdesk-addressbook-update-flat-v0532.zip.sig updates/
./scripts/update.sh
```

The updater selects the highest local `rustdesk-addressbook-update-flat-v*.zip`, validates the signed SHA-256 manifest with the embedded Ed25519 public key, checks the ZIP structure, creates a rollback backup, and installs the package only when it is newer.

Online checks use `https://github.com/the-ab/RustDesk-AddressBook/releases/latest/download` by default. The latest published release must provide `latest.txt`, the ZIP named in it, `.zip.sha256`, and `.zip.sig`. Set `RAB_UPDATE_BASE_URL=disabled` to turn online checks off explicitly. Never store the private release-signing key in this directory or in the repository.

The German edition is available as [`README.de.md`](README.de.md).
