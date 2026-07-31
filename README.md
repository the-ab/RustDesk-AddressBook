# Community Address Book for RustDesk

A self-hosted web address book for RustDesk environments, packaged as a Docker project with Flask, SQLite, local and OpenID Connect authentication, user/group permissions, device management, import/export, backup/restore, HTTPS, hbbs live status, and SSH import of the RustDesk server database.

> **Independent project:** This is an independent community project. It is not affiliated with, endorsed by, sponsored by, or maintained by RustDesk or Purslane Ltd. RustDesk is a trademark of its respective owner.

> English is the default documentation language. The German edition is available as [`README.de.md`](README.de.md).

## New in 0.6.1

- Adds complete English and German documentation for every variable in `docker-compose/.env.example`.
- Links the GHCR Compose documentation directly from the main README files.
- Centers the project, version, release date, and license notice below unauthenticated pages such as the login screen.
- Uses the dotted `v0.6.1` format consistently for release archives, signatures, checksums, examples, and `latest.txt`.

## Installation

### GHCR image installation

The published container image is available as:

```text
ghcr.io/the-ab/rustdesk-addressbook:latest
ghcr.io/the-ab/rustdesk-addressbook:0.6.1
```

The `docker-compose/` directory contains the dedicated image-based `compose.yaml` and `.env.example`. All environment variables are documented in [`docker-compose/README.md`](docker-compose/README.md); the German edition is available as [`docker-compose/README.de.md`](docker-compose/README.de.md). No project source files are required for this installation method:

```bash
cd docker-compose
cp .env.example .env
docker compose pull
docker compose up -d
docker exec rustdesk-addressbook python -c 'import json; print(json.load(open("/data/config.json"))["SETUP_TOKEN"])'
```

The final command prints the one-time setup token. After the first administrator is created successfully, the token is removed from `config.json`.

Use `RAB_IMAGE_TAG=latest` to track the newest published image or `RAB_IMAGE_TAG=0.6.1` to pin this release. Persistent data and backups are stored in the host paths configured in `.env`.

### Source/release archive installation

Download a current release archive from the repository's Releases page, then:

```bash
cd /opt
unzip rustdesk-addressbook-v0.6.1.zip
cd rustdesk-addressbook
chmod +x scripts/install.sh scripts/update.sh
./scripts/install.sh
```

The installer asks for timezone, container/image name, data and backup paths, HTTPS port, optional HTTP, certificate names, reverse-proxy trust, signed update source, an optional read-only RustDesk DB mount, and brute-force/auth-log rotation settings. Existing `.env` values are reused as defaults when the installer is run again.

There are no fixed initial credentials. After the first start, read the one-time setup token printed by the installer or from `/data/config.json`, create the first administrator, and then the application removes the token from `config.json` automatically.

Default address:

```text
https://SERVER-IP:5443
```

## Updates

Place the signed update assets in `updates/`:

```bash
cd /opt/rustdesk-addressbook
cp /path/to/rustdesk-addressbook-update-flat-v0.6.1.zip* updates/
./scripts/update.sh
```

The update ZIP requires its matching `.zip.sha256` and `.zip.sig` files. Packages are checked with the embedded Ed25519 public key before extraction.

Online checks use the project GitHub Releases endpoint by default:

```dotenv
RAB_UPDATE_BASE_URL=https://github.com/the-ab/RustDesk-AddressBook/releases/latest/download
```

The latest published release must expose `latest.txt`, the update ZIP, and the matching `.zip.sha256` and `.zip.sig` assets. The first valid line in `latest.txt` names the update ZIP. Existing custom non-empty URLs remain supported. To disable online checks explicitly, set `RAB_UPDATE_BASE_URL=disabled`; local signed updates remain fully available.

## Roles and visibility

- **Administrator:** full access to all devices and groups, including ungrouped devices, plus users, groups, import/export, backups, security, settings, and updates.
- **User:** access to Dashboard, Devices, Account, and Help. Only devices in assigned groups are visible. Connections and explicit retrieval of stored device passwords remain available; users cannot create, edit, or delete devices or system data. Each user can change only their own appearance and language.
- Groups are assigned under **Users**. An automatically provisioned OIDC user initially has no group assignments and therefore sees no devices.
- Permissions are enforced in backend routes; hidden navigation entries are not the security boundary.

## Main features

- Device and group management with encrypted RustDesk passwords
- Local accounts, administrator/user roles, TOTP 2FA, recovery codes, and OIDC
- Per-user language and light/dark appearance settings
- CSV and RustDesk server database import, including SSH snapshots
- Editable CSV example: [`sample-import.csv`](sample-import.csv)
- Persistent blocklist for deleted RustDesk IDs
- hbbs online-state checks
- Plain, encrypted database, and encrypted full backups
- Responsive smartphone, tablet, and desktop UI
- Signed update packages and hardened non-root container runtime

The detailed operating guide is available in [`ADMIN-GUIDE.md`](ADMIN-GUIDE.md).

## Repository safety

Do not create commits from a productive installation directory. Start from a clean release/source archive and verify before pushing:

```bash
python scripts/check_repository_safety.py
```

The policy rejects common runtime artifacts and private-key material. `.gitignore` excludes `.env`, database files, logs, backups, downloaded release assets, and private signing/TLS keys. The public verification key at `scripts/keys/update-signing-public-v1.pem` is intentionally versioned.

## Local development and checks

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

These checks are run manually by the maintainer or contributors. The repository does not contain GitHub-hosted CI, automatic dependency-update, or automatic container-build configuration.

## Documentation

- English: [`ADMIN-GUIDE.md`](ADMIN-GUIDE.md), [`RELEASE_NOTES.md`](RELEASE_NOTES.md), [`SECURITY.md`](SECURITY.md), [`CONTRIBUTING.md`](CONTRIBUTING.md), [`SECURITY-REPORT.md`](SECURITY-REPORT.md)
- German: [`ADMIN-GUIDE.de.md`](ADMIN-GUIDE.de.md), [`RELEASE_NOTES.de.md`](RELEASE_NOTES.de.md), [`SECURITY.de.md`](SECURITY.de.md), [`CONTRIBUTING.de.md`](CONTRIBUTING.de.md), [`SECURITY-REPORT.de.md`](SECURITY-REPORT.de.md)
- License and attribution: [`LICENSE`](LICENSE), [`NOTICE`](NOTICE), [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md)

## License

The project is licensed under the [Apache License 2.0](LICENSE). Third-party components remain under their respective licenses.

## AI assistance disclosure

Portions of this project were developed with assistance from OpenAI ChatGPT. All generated code was reviewed, adapted, and tested by the project maintainer, who assumes responsibility for the published software.

## Security

Read [`SECURITY.md`](SECURITY.md) before deployment and use the private reporting process for suspected vulnerabilities. Keep `data/config.json`, databases, backups, session material, OIDC secrets, and private release-signing keys out of the repository.
