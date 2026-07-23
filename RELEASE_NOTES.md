# Community Address Book for RustDesk 0.5.33 – Update cleanup and installed archive

German edition: [`RELEASE_NOTES.de.md`](RELEASE_NOTES.de.md)

## Changed

- Runs `rustdesk-addressbook-init` explicitly as a one-shot `docker compose run --rm` maintenance service, so no stopped init container remains after installation or updates.
- Moves successfully installed update ZIPs, SHA-256 manifests, and Ed25519 signatures from `updates/` to `updates/installed/` after a confirmed healthy start.
- Leaves update files in `updates/` when installation fails or the health status cannot be confirmed.
- Displays the release date next to the version number in the footer.
- Corrected package-tag normalization so managed Docker image names stay aligned with `v0533`.
- Removed the obsolete, unreferenced `UPDATE-CHECK.txt` artifact after auditing the package for orphaned files.

## Compatibility

Database, authentication, imports, backups, permissions, OIDC, signed online updates, and custom update sources remain unchanged.
