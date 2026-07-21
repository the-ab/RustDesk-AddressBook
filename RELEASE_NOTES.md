# Community Address Book for RustDesk 0.5.32 – GitHub Releases as update default

German edition: [`RELEASE_NOTES.de.md`](RELEASE_NOTES.de.md)

## Changed

- Set `https://github.com/the-ab/RustDesk-AddressBook/releases/latest/download` as the default signed online-update source.
- `latest.txt` in the latest published GitHub release selects the current flat update ZIP.
- The updater downloads the selected ZIP and its matching `.zip.sha256` and `.zip.sig` assets from the same release.
- Existing custom non-empty `RAB_UPDATE_BASE_URL` values remain supported.
- `RAB_UPDATE_BASE_URL=disabled` explicitly disables online checks while preserving local signed updates.
- A ready-to-upload `latest.txt` is provided with the release assets.

## Compatibility

No database, authentication, import, backup, or permission behavior was changed. Existing installations with an empty update URL automatically use the project GitHub Releases endpoint after updating.
