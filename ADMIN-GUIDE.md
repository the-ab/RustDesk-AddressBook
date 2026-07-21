# Community Address Book for RustDesk – Admin Guide

This guide describes installation, updates, operation, imports, backups, security, and troubleshooting for version `0.5.32-github-release-update-default`.

> English is the default documentation language. The German edition is available as [`ADMIN-GUIDE.de.md`](ADMIN-GUIDE.de.md).

## Overview

Community Address Book for RustDesk is an independent web address book for self-hosted RustDesk environments. It is not affiliated with, endorsed by, sponsored by, or maintained by RustDesk or Purslane Ltd. Version 0.5.32 uses the project GitHub Releases endpoint as the default signed online-update source while retaining local signed updates and custom release sources.

**Device management**  
Name, RustDesk ID, password, group, customer, location, OS/device type, tags and notes.

**Live status**  
Online/offline checks using the RustDesk hbbs OnlineRequest/OnlineResponse flow.

**Import / Export**  
CSV, RustDesk server DB upload, mounted DB import and SSH snapshot import.

**Security**  
Admin/user roles, assigned groups, local 2FA, OIDC, audit log, brute-force lockout and encrypted backups.

## Installation and update

### Fresh installation

```
cd /opt
unzip /path/to/rustdesk-addressbook-v0532.zip
cd rustdesk-addressbook
chmod +x scripts/install.sh scripts/update.sh
./scripts/install.sh
```

The installer asks for timezone, container/image name, data and backup directories, HTTPS port, optional HTTP port, certificate names, reverse-proxy trust, optional read-only RustDesk DB mount, brute-force values and the update download base URL. After the first start it prints the one-time setup token for the initial administrator.

The values are written to `.env`. When you run `./scripts/install.sh` again, the existing `.env` values are used as defaults.

### Manual update with ZIP in `updates/`

```
cd /opt/rustdesk-addressbook
cp /path/to/rustdesk-addressbook-update-flat-v0532.zip* updates/
./scripts/update.sh
```

### Automatic online update check

```
cd /opt/rustdesk-addressbook
./scripts/update.sh
```

The update script first checks local ZIP files in `updates/`. Every package is verified with an Ed25519 signature and a signed SHA-256 checksum before extraction. Online checking uses `https://github.com/the-ab/RustDesk-AddressBook/releases/latest/download` by default. Set `RAB_UPDATE_BASE_URL=disabled` to turn it off explicitly; local signed updates remain available.

### Web UI

```
https://SERVER-IP:5443
```

HTTP is disabled by default. If no own certificate is configured, a self-signed certificate is generated and the browser warning is expected.

## First setup

1. Open the Web UI.
2. Enter the one-time setup token printed by the installer and create the first local administrator.
3. Enable TOTP under **Account** and store recovery codes offline.
4. Configure appearance, language and hbbs under **Settings**.
5. Create local or OIDC users under **Users** and assign groups.
6. Optionally configure the identity provider under **Settings → OpenID Connect**.
7. Create an encrypted full backup after the base setup.

The `data/` directory contains the database, config, logs, SSH keys and certificates. Use encrypted `.rabfull` full backups for complete disaster recovery.

## Dashboard and device views

The dashboard shows counters, online devices, favorites and recently changed devices within the current user's visibility. Administrators can refresh all online states with **Live status hbbs**; regular users receive a read-only dashboard for their assigned groups.

- **Card view**: current detailed layout.
- **List view**: compact rows for many devices.
- **Small icon view**: very compact overview.

The selected view is stored in the session and used on Dashboard and Devices. On small screens, list tables are transformed into labelled cards instead of forcing the entire page to scroll sideways.

## Devices

- Administrators can create, edit and delete devices. Regular users cannot change device data. Deleting a device automatically blocks its RustDesk ID for future imports.
- **Connect**: opens a `rustdesk://` link. A stored password is decrypted only when the link is requested. After the sensitive-action window expires, reauthentication is required and the action is audited.
- **Eye icon**: all authorized users can explicitly fetch the password of a visible device after recent authentication. Password retrieval and password CSV exports are recorded in the audit log. Only administrators see the edit form, where an empty field keeps it unchanged and the checkbox removes it.
- **Favorite / Online**: administrators can toggle these values and refresh online state using hbbs.
- **Search/filter**: name, ID, customer, location, OS/device type, tags and notes; filters for group, favourite and device type.
- **Sort**: online first, name, favourites or last changed.

## Groups

Groups help structure devices by customer, site, device type or purpose. Each group has a name, color and icon.

- Icons are selected from a dropdown with preview.
- Existing groups can be edited.
- Deleting a group removes its device and user assignments; the devices themselves remain available to administrators as ungrouped devices.

## Users, roles and OpenID Connect

- **Administrator**: full access to all devices, ungrouped devices, groups, users, imports, backups, security, settings and updates.
- **User**: read-only access to Dashboard, Devices, Account and Help. Only devices in assigned groups are visible; connect and explicit password retrieval remain available. Every user can set their own theme and UI language under Account.
- Disabled accounts cannot sign in. The current administrator and the last active local administrator are protected from accidental removal, deactivation or demotion.
- OIDC uses provider discovery and Authorization Code with PKCE. The client secret is encrypted; the account binding uses issuer and `sub`.
- Auto-provisioned OIDC users start with role User and no groups. Optional allowed email domains can restrict all OIDC sign-ins; the provider must then supply an `email_verified=true` email claim from an allowed domain.

Pre-created OIDC accounts must contain the exact issuer and immutable `sub`; usernames or email addresses are never used to bind an identity. Private/local issuer addresses are blocked by default unless `OIDC_ALLOW_PRIVATE_ISSUER=true` is explicitly configured.

Copy the displayed redirect URI to the OIDC provider exactly. Behind a trusted TLS reverse proxy, enable `TRUST_PROXY_HEADERS=true` so the external HTTPS URL is generated correctly. Keep at least one active local administrator as an emergency login.

## Online status via hbbs

The live status is queried from the RustDesk ID server. In the tested setup the working port is usually TCP `21115`.

```
docker exec -it rustdesk-addressbook python - <<'PY'
import socket
host = "YOUR-RUSTDESK-SERVER"
port = 21115
s = socket.create_connection((host, port), timeout=3)
print("TCP connection OK")
s.close()
PY
```

- **Status source**: hbbs live query.
- **hbbs host**: IP or DNS name of the RustDesk ID server.
- **hbbs port**: usually `21115`.
- **Automatic check**: minute/hour interval while the Web UI is open.
- **Last result**: shown on Dashboard and Devices next to the hbbs button.

The hbbs query uses RustDesk protocol messages, but it is not an officially documented Web API. Retest after RustDesk server upgrades.

## Import / Export

The Import / Export page is grouped by categories on the left and details on the right.

### CSV import/export

```
name,rustdesk_id,password,customer,location,os,tags,notes,favorite,online,group
```

- CSV import always creates new devices, skips rows without name or RustDesk ID, detects comma/semicolon/tab delimiters and creates named groups when needed.
- Export without passwords is recommended. Export with passwords writes decrypted values and should only be used in trusted environments.

### RustDesk server DB upload

Upload a single SQLite DB or a ZIP containing:

```
db_v2.sqlite3
db_v2.sqlite3-wal
db_v2.sqlite3-shm
```

The import uses a consistent read-only snapshot. Existing devices can optionally be updated by RustDesk ID; online state is never copied from the server DB.

### Import blocklist

Deleting a device automatically adds its RustDesk ID to the persistent blocklist. CSV, server DB upload, mounted DB and SSH imports skip blocked IDs. Administrators can add entries manually or unblock them under **Import / Export → Import blocklist**.

### Mounted DB import

Expert option for read-only mounts. The UI shows whether `RUSTDESK_SERVER_DB` is configured, missing or usable. The diagnostics check the main file, WAL/SHM, SQLite header and integrity, tables, peer count and sample records.

```
volumes:
  - /docker_data/rustdesk:/rustdesk-server:ro

environment:
  RUSTDESK_SERVER_DB: /rustdesk-server/db_v2.sqlite3
```

## RustDesk SSH import

Recommended for separate servers: AddressBook pulls a consistent SQLite snapshot from the RustDesk server via SSH. The SSH key should be restricted to one forced command.

### 1. Prepare RustDesk server

```
apt update
apt install sqlite3 openssh-server acl
adduser --disabled-password --gecos "" rab-import
```

### 2. Create export script

```
cat > /usr/local/sbin/rab-rustdesk-db-export <<'EOSCRIPT'
#!/bin/bash
set -euo pipefail
DB="/docker_data/rustdesk/db_v2.sqlite3"
TMP="$(mktemp /tmp/rustdesk-db-export.XXXXXX.sqlite3)"
cleanup() { rm -f "$TMP"; }
trap cleanup EXIT
if [ ! -r "$DB" ]; then
  echo "ERROR: RustDesk DB not readable: $DB" >&2
  exit 1
fi
sqlite3 "$DB" ".backup '$TMP'"
cat "$TMP"
EOSCRIPT
chmod 755 /usr/local/sbin/rab-rustdesk-db-export
```

### 3. Permissions

```
setfacl -m u:rab-import:rx /docker_data
setfacl -m u:rab-import:rx /docker_data/rustdesk
setfacl -m u:rab-import:r /docker_data/rustdesk/db_v2.sqlite3
setfacl -m u:rab-import:r /docker_data/rustdesk/db_v2.sqlite3-wal 2>/dev/null || true
setfacl -m u:rab-import:r /docker_data/rustdesk/db_v2.sqlite3-shm 2>/dev/null || true
```

### 4. Restricted SSH key

```
restrict,no-pty,no-agent-forwarding,no-X11-forwarding,no-port-forwarding,command="/usr/local/sbin/rab-rustdesk-db-export" ssh-ed25519 AAAA...
```

### 5. Local key path

```
mkdir -p data/ssh
cp rustdesk_import_ed25519 data/ssh/
chmod 600 data/ssh/rustdesk_import_ed25519
```

In the Web UI use `/data/ssh/rustdesk_import_ed25519` and enter the expected SHA-256 host-key fingerprint. The key is stored only after an exact match and `StrictHostKeyChecking=yes` remains active. The SSH test reports connection, transfer size, SQLite header, integrity check, peer table and peer count.

## Backup / restore

- **DB backup**: unencrypted SQLite copy.
- **Encrypted DB backup `.rabenc`**: database only; requires the matching `config.json` for stored device passwords.
- **Encrypted full backup `.rabfull`**: recommended for migration and disaster recovery. Includes database, `config.json`, SSH keys, certificates, logs and a manifest.
- Existing backups can be downloaded, restored or deleted. Restore also accepts uploaded `.db`, SQLite, `.rabenc` and `.rabfull` files.
- Before every restore, the previous database state is saved automatically as a safety backup.

Passwords require at least 12 characters for `.rabenc` and 16 for `.rabfull`. Store them outside the server. After restoring a full backup, restart the container so the restored `config.json` is reloaded.

## Settings

The settings page uses a category navigation and a detail area. On small screens, the categories are horizontally scrollable.

- **Display & language**: stored per user account. The Account page is available to local and OIDC users; changing it never changes another user’s view.
- **OpenID Connect**: issuer, client credentials, scopes, username claim, auto-provisioning and allowed domains.
- **Account**: local users change their own password and TOTP outside the admin settings; OIDC users are managed by the provider.
- **Device types**: customize OS/device type presets.
- **Online status**: hbbs host, port, timeout, batch size and automatic checks.
- **Brute-force lockout**: failed attempts and time window.
- **Update check**: automatic online checks from 1 to 168 hours; it reports updates but does not install them.
- **Security notes**: encryption, backup and key-material guidance.

## Update check and release notes

The Web UI checks `latest.txt` at `https://github.com/the-ab/RustDesk-AddressBook/releases/latest/download` by default. Custom non-empty sources remain supported. Set `RAB_UPDATE_BASE_URL=disabled` to disable online checks explicitly; local signed updates remain available.

```
rustdesk-addressbook-update-flat-v0532.zip
[de]
- Deutsche Änderung 1
[en]
- English change 1
```

If no language sections exist, all lines below the ZIP filename are shown as release notes. The Web UI only reports an update; installation is performed with `./scripts/update.sh`.

## Security

- Use HTTPS. Reverse proxy TLS is recommended for public access.
- Enable local 2FA and store recovery codes offline; enforce MFA at the identity provider for OIDC users.
- Keep at least one active local emergency administrator and assign groups according to least privilege.
- Use encrypted full backups for anything containing `config.json`, OIDC secrets, SSH keys or TLS keys.
- The Security page checks administrators, OIDC state, local 2FA/recovery codes, HMAC signatures, cookie/HSTS/proxy settings, logs and permissions, runtime secrets, database and backups, lockout/rotation, update check, hbbs and HTTPS.
- Do not run the address book on the RustDesk server if you want stronger separation.

## fail2ban / CrowdSec

Failed login attempts are written to:

```
data/logs/auth.log
```

Failed authentication lines contain:

```
RAB_AUTH_FAIL
```

Example files are included under `contrib/fail2ban/`. The application rotates `auth.log` itself; defaults are every 7 days with 8 rotated files.

## Troubleshooting

```
docker compose ps
docker compose logs -f
docker exec -it rustdesk-addressbook grep -n "0.5.32-github-release-update-default" /app/app/config.py
docker exec -it rustdesk-addressbook ls -lh /rustdesk-server/db_v2.sqlite3* 2>/dev/null || true
docker exec -it rustdesk-addressbook python /app/scripts/reset_security_lockout.py
```

- **Update conflict:** current update script removes an existing container with the same name before recreating it.
- **SSH import:** use the built-in SSH test first and check transfer size, integrity and peer count.
- **Online status:** test TCP access to hbbs port `21115`.


## Public repository and legal notices

- The project is licensed under Apache License 2.0; see `LICENSE` and `NOTICE`.
- Do not commit from a productive installation directory. Run `python scripts/check_repository_safety.py` before pushing.
- `.env`, databases, logs, backups, downloaded release assets, TLS private keys, and private update-signing keys are excluded by `.gitignore`.
- `scripts/keys/update-signing-public-v1.pem` is the public verification key and is intentionally versioned.
- Portions were developed with assistance from OpenAI ChatGPT; all code remains reviewed, adapted, and maintained under human responsibility.
- Security issues must be reported privately as described in `SECURITY.md`.
