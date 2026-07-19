# Updates

Copy new flat update ZIP files and their verification sidecars into this directory, for example:

```bash
cp rustdesk-addressbook-update-flat-v0529.zip* updates/
./scripts/update.sh
```

The update script automatically selects the highest `rustdesk-addressbook-update-flat-v*.zip`, compares it with the installed version, verifies its Ed25519 signature and signed SHA-256 checksum, and installs it only when it is newer.

The German edition is available as [`README.de.md`](README.de.md).
