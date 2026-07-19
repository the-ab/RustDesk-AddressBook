# RustDesk AddressBook

Self-hosted RustDesk address book packaged as a Docker project with Flask, SQLite, local and OpenID Connect authentication, user/group permissions, device management, import/export, backup/restore, HTTPS, hbbs live status, and SSH import of the RustDesk server database.

> English is the default documentation language. The German edition is available as [`README.de.md`](README.de.md).

## New in 0.5.29

- Standardized all Markdown documentation: every regular `*.md` file is now English.
- Added matching German `*.de.md` editions for README, admin guide, release notes, security report, third-party notices, and the updates directory.
- Added dedicated `RELEASE_NOTES.md` and `RELEASE_NOTES.de.md` files.
- Updated internal documentation links and package contents to make the language convention explicit.

## Fresh installation

```bash
cd /opt
wget https://dl.ab-xnet.de/rustdesk-addressbook-v0529.zip
unzip rustdesk-addressbook-v0529.zip
cd rustdesk-addressbook
chmod +x scripts/install.sh scripts/update.sh
./scripts/install.sh
```

The installer asks for timezone, container/image name, data and backup paths, HTTPS port, optional HTTP, certificate names, reverse-proxy trust, update URL, an optional read-only RustDesk DB mount, and brute-force/auth-log rotation settings. Existing `.env` values are reused as defaults when the installer is run again. After the first start, the installer prints the one-time setup token for the initial administrator.

Default address:

```text
https://SERVER-IP:5443
```

## Update

```bash
cd /opt/rustdesk-addressbook
wget https://dl.ab-xnet.de/rustdesk-addressbook-update-flat-v0529.zip -O updates/rustdesk-addressbook-update-flat-v0529.zip
wget https://dl.ab-xnet.de/rustdesk-addressbook-update-flat-v0529.zip.sha256 -O updates/rustdesk-addressbook-update-flat-v0529.zip.sha256
wget https://dl.ab-xnet.de/rustdesk-addressbook-update-flat-v0529.zip.sig -O updates/rustdesk-addressbook-update-flat-v0529.zip.sig
./scripts/update.sh
```

Without a local update ZIP, run only `./scripts/update.sh`. The script checks `updates/` first and then `RAB_UPDATE_BASE_URL/latest.txt`, displays the release notes, and asks before download and installation. Update packages are verified with an Ed25519 signature and signed SHA-256 checksum. Before installation, the script backs up `data/`, `backups/`, `.env`, Compose files, and `updates/`.

## Roles and visibility

- **Administrator:** full access to all devices and groups, including ungrouped devices, plus users, groups, import/export, backups, security, settings, and updates.
- **User:** access to Dashboard, Devices, Account, and Help. Only devices in assigned groups are visible. Connections and explicit retrieval of stored device passwords remain available; users cannot create, edit, or delete devices or system data. Each user can change only their own appearance and language.
- Groups are assigned to accounts under **Users**. An automatically provisioned OIDC user initially has no group assignments and therefore sees no devices.
- Permissions are enforced in backend routes; hidden navigation entries are not the security boundary.

## OpenID Connect

Configure OIDC under **Settings → OpenID Connect**:

- issuer URL with discovery at `/.well-known/openid-configuration`
- client ID and encrypted client secret
- redirect URI copied exactly to the provider
- scopes, username claim, and provider display name
- optional automatic user provisioning and allowed email-domain allowlist
- optional insecure HTTP only for explicitly enabled internal test environments

Use HTTPS in production. Behind a reverse proxy, enable `TRUST_PROXY_HEADERS=true` only when its forwarded headers are trustworthy. Keep at least one active local administrator as an emergency login.

## Features

- **Devices:** create, edit, delete, search, filter, and sort by online state, name, favorites, or modification time. Fields include name, RustDesk ID, encrypted password, group, customer, location, device type/OS, tags, notes, favorite, and online status.
- **Views:** cards, compact list, and small icons; the selection applies to Dashboard and Devices.
- **RustDesk connection:** direct `rustdesk://` links. Stored passwords are decrypted only after an explicit request. Sensitive actions require recent authentication and are audited.
- **Groups:** name, color, and icon. Deleting a group removes assignments but preserves its devices as ungrouped administrator-visible devices.
- **Online status:** manual or hbbs OnlineRequest/OnlineResponse checks with a configurable interval in minutes or hours.
- **CSV:** import and export with optional decrypted passwords. Imports skip incomplete rows and IDs on the persistent import blocklist.
- **RustDesk server DB:** SQLite/WAL/SHM upload, ZIP upload, read-only mount, diagnostics, and SSH snapshot import.
- **Backups:** plain SQLite, encrypted `.rabenc` database backup, and encrypted `.rabfull` full backup. Restore archives are validated for paths, file types, member count, and extracted size.
- **Security:** TOTP 2FA, hashed one-time recovery codes, OIDC, HMAC-protected user state and group assignments, session revocation, CSRF protection, audit logging, IP-based brute-force limiting, and fail2ban/CrowdSec-compatible auth logging.
- **Import blocklist:** deleted RustDesk IDs are stored and skipped by every device import; administrators can block or unblock IDs manually.
- **Responsive WebUI:** all major pages are designed for smartphone, tablet, and desktop use.

## Backup notes

Important data is stored under:

```text
data/addressbook.db
data/config.json
data/ssh/
data/certs/
data/logs/
backups/
```

`data/config.json` contains key material for device passwords and the OIDC client secret. A `.rabenc` file contains only the database and still requires the matching `config.json`. Use an encrypted `.rabfull` backup for migration or disaster recovery. Restart the container after restoring a `.rabfull` backup.

## Download server / latest.txt

```text
rustdesk-addressbook-update-flat-v0529.zip
[de]
- Deutsche Änderung
[en]
- English change
```

Publish the matching `.zip.sha256` and `.zip.sig` files next to the update ZIP. `scripts/update.sh` downloads and verifies them automatically. Matching `.txt`/`.md` files and language-specific release-note files are also supported. Keep the private Ed25519 signing key only in an offline or separately protected release environment, never on the download server.

## Check installed version

```bash
docker exec -it rustdesk-addressbook grep -n "0.5.29-english-default-markdown-docs" /app/app/config.py
```

## Documentation

- English: [`ADMIN-GUIDE.md`](ADMIN-GUIDE.md), [`RELEASE_NOTES.md`](RELEASE_NOTES.md), [`SECURITY-REPORT.md`](SECURITY-REPORT.md)
- German: [`ADMIN-GUIDE.de.md`](ADMIN-GUIDE.de.md), [`RELEASE_NOTES.de.md`](RELEASE_NOTES.de.md), [`SECURITY-REPORT.de.md`](SECURITY-REPORT.de.md)

The WebUI help and release history remain available in German and English. Technical logs and imported content are not translated.

## Security note

The SQLite database is not fully encrypted with SQLCipher. Device passwords and the OIDC client secret are encrypted field by field. Sensitive user-security fields, including roles, OIDC identity, session state, and group assignments, are HMAC-signed. Treat access to both the database and `data/config.json` as a compromise. Expose the application only through hardened HTTPS with strong emergency credentials, 2FA, and restrictive server permissions.

## Check container health

```bash
docker compose ps
docker inspect --format '{{.State.Health.Status}}' rustdesk-addressbook
docker logs --tail 100 rustdesk-addressbook
```

At startup, `rustdesk-addressbook-init` prepares data and backup permissions once. The main `rustdesk-addressbook` container then runs as UID/GID 10001 without Linux capabilities.
