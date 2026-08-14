# GHCR Docker Compose configuration

This directory contains the two files required to run Community Address Book for RustDesk directly from the published container image:

- `compose.yaml`
- `.env.example`

No project source files are required for this installation method.

> This is an independent community project. It is not affiliated with, endorsed by, sponsored by, or maintained by RustDesk or Purslane Ltd.

German documentation: [`README.de.md`](README.de.md)

## Quick start

```bash
mkdir -p /opt/rustdesk-addressbook
cd /opt/rustdesk-addressbook
cp /path/to/docker-compose/compose.yaml .
cp /path/to/docker-compose/.env.example .env
nano .env
docker compose pull
docker compose up -d
```

Check the container:

```bash
docker compose ps
docker logs --tail 100 rustdesk-addressbook
```

Read the one-time setup token before creating the first administrator:

```bash
docker exec rustdesk-addressbook python -c \
  'import json; print(json.load(open("/data/config.json"))["SETUP_TOKEN"])'
```

After the first administrator account has been created successfully, the application removes the setup token from `/data/config.json` automatically.

## Values that normally must be reviewed

For a normal installation, review at least these values in `.env`:

| Variable | Purpose | Typical value |
|---|---|---|
| `RAB_IMAGE_TAG` | Image version to run | `latest` or `0.6.2` |
| `RAB_DATA_DIR` | Persistent application data on the host | `/docker_data/rustdesk-addressbook/data` |
| `RAB_BACKUP_DIR` | Persistent backups on the host | `/docker_data/rustdesk-addressbook/backups` |
| `RAB_HTTPS_PUBLISH_PORT` | HTTPS port exposed on the host | `5443` |
| `HTTPS_COMMON_NAME` | Main name in an automatically generated certificate | Server DNS name |
| `HTTPS_ALT_NAMES` | Additional DNS names and IP addresses for the certificate | `localhost,127.0.0.1,addressbook.example.org` |
| `TZ` | Container timezone | `Europe/Berlin` |

The remaining defaults can normally stay unchanged unless your environment requires different ports, a reverse proxy, custom certificates, a RustDesk server database mount, or a private OIDC provider.

## Image and container

### `RAB_IMAGE_TAG`

Selects the tag of `ghcr.io/the-ab/rustdesk-addressbook`.

```dotenv
RAB_IMAGE_TAG=latest
```

- `latest`: follows the newest published image.
- `0.6.2`: pins this exact release.

For predictable production operation, use a fixed release tag and update it deliberately.

### `RAB_CONTAINER_NAME`

Docker container name. The default is:

```dotenv
RAB_CONTAINER_NAME=rustdesk-addressbook
```

Change it only when several independent installations run on the same Docker host.

### `RAB_HOSTNAME`

Hostname inside the container:

```dotenv
RAB_HOSTNAME=rustdesk-addressbook
```

This normally does not need to be changed.

## Persistent storage

### `RAB_DATA_DIR`

Host directory mounted to `/data`. It contains the SQLite database, runtime configuration, certificates, SSH files, logs, and other persistent application data.

```dotenv
RAB_DATA_DIR=/docker_data/rustdesk-addressbook/data
```

Back up this directory and do not place it inside the Git repository.

### `RAB_BACKUP_DIR`

Host directory mounted to `/backups` for backups created by the application:

```dotenv
RAB_BACKUP_DIR=/docker_data/rustdesk-addressbook/backups
```

Keep it on persistent storage. For additional protection, copy its contents to another system.

### `RAB_RUNTIME_UID` and `RAB_RUNTIME_GID`

Numeric user and group IDs used by the unprivileged application process:

```dotenv
RAB_RUNTIME_UID=10001
RAB_RUNTIME_GID=10001
```

The container prepares the mounted directories for these IDs before dropping privileges. Keep the defaults unless you intentionally align permissions with an existing host-side account. Both values must be positive integers.

## HTTPS and HTTP

### `APP_ENABLE_HTTPS`

Enables the HTTPS listener inside the container:

```dotenv
APP_ENABLE_HTTPS=true
```

Keep HTTPS enabled for direct access.

### `RAB_HTTPS_BIND`

Host interface on which the HTTPS port is published:

```dotenv
RAB_HTTPS_BIND=0.0.0.0
```

- `0.0.0.0`: reachable through all host interfaces, subject to firewall rules.
- `127.0.0.1`: reachable only locally, useful behind a reverse proxy on the same host.
- A specific host IP: publish only on that interface.

### `RAB_HTTPS_PUBLISH_PORT`

External HTTPS port:

```dotenv
RAB_HTTPS_PUBLISH_PORT=5443
```

The internal container port remains `5443`.

### `APP_ENABLE_HTTP`

Enables the unencrypted HTTP listener:

```dotenv
APP_ENABLE_HTTP=false
```

Leave it disabled unless HTTP is required inside a trusted network or behind a local reverse proxy. Never transmit login credentials over an untrusted HTTP connection.

### `RAB_HTTP_BIND` and `RAB_HTTP_PUBLISH_PORT`

Host binding and external port for HTTP:

```dotenv
RAB_HTTP_BIND=0.0.0.0
RAB_HTTP_PUBLISH_PORT=5055
```

These values only become useful when `APP_ENABLE_HTTP=true`.

## Certificates

### `HTTPS_CERT_FILE` and `HTTPS_KEY_FILE`

Paths inside the container to the TLS certificate and private key:

```dotenv
HTTPS_CERT_FILE=/data/certs/addressbook.crt
HTTPS_KEY_FILE=/data/certs/addressbook.key
```

To use your own certificate, place both files in the corresponding host directory below `RAB_DATA_DIR/certs/`. If the files are missing, the application creates a self-signed certificate.

### `HTTPS_COMMON_NAME`

Common Name used when generating the self-signed certificate:

```dotenv
HTTPS_COMMON_NAME=rustdesk-addressbook.local
```

Set this to the DNS name normally used to open the application.

### `HTTPS_ALT_NAMES`

Comma-separated Subject Alternative Names for the generated certificate:

```dotenv
HTTPS_ALT_NAMES=localhost,127.0.0.1,rustdesk-addressbook.local
```

Add every DNS name and IP address through which clients access the application. Do not add spaces around the commas.

## Application server

### `APP_WORKERS`

Number of Gunicorn worker processes:

```dotenv
APP_WORKERS=1
```

One worker is the safest default for the SQLite-based installation. Increase only after testing your workload and database behavior.

### `APP_THREADS`

Threads per Gunicorn worker:

```dotenv
APP_THREADS=4
```

The default is suitable for normal small and medium installations.

### `APP_TIMEOUT`

Maximum Gunicorn request duration in seconds:

```dotenv
APP_TIMEOUT=60
```

Increase only when legitimate imports or backup operations regularly exceed the default.

## Session and proxy security

### `SESSION_COOKIE_SECURE`

Restricts the login cookie to HTTPS connections:

```dotenv
SESSION_COOKIE_SECURE=true
```

Keep this enabled when accessing the application through HTTPS. Set it to `false` only for a deliberate HTTP-only test installation.

### `APP_HSTS`

Enables the HTTP Strict Transport Security response header:

```dotenv
APP_HSTS=false
```

Enable it only after HTTPS is permanently configured and trusted by all clients. Browsers remember HSTS and will refuse later HTTP access.

### `TRUST_PROXY_HEADERS`

Allows the application to trust forwarded protocol and client-address headers:

```dotenv
TRUST_PROXY_HEADERS=false
```

Set it to `true` only when the application is exclusively reachable through a trusted reverse proxy that overwrites these headers. Do not enable it when clients can reach the container directly.

## Login protection and security logs

### `LOGIN_FAIL_LIMIT`

Maximum failed login attempts from one source IP within the configured window:

```dotenv
LOGIN_FAIL_LIMIT=5
```

### `LOGIN_FAIL_WINDOW_SECONDS`

Length of the failed-login evaluation window in seconds:

```dotenv
LOGIN_FAIL_WINDOW_SECONDS=900
```

`900` seconds equals 15 minutes.

### `AUTH_LOG_ROTATE_DAYS`

Age in days after which `auth.log` is rotated:

```dotenv
AUTH_LOG_ROTATE_DAYS=7
```

### `AUTH_LOG_ROTATE_KEEP`

Number of rotated authentication logs retained:

```dotenv
AUTH_LOG_ROTATE_KEEP=8
```

### `AUTH_EVENT_RETENTION_DAYS`

Maximum age of authentication events stored in SQLite:

```dotenv
AUTH_EVENT_RETENTION_DAYS=90
```

### `AUTH_EVENT_MAX_ROWS`

Maximum number of authentication-event rows retained in SQLite:

```dotenv
AUTH_EVENT_MAX_ROWS=50000
```

The age and row-count limits work together to prevent unlimited database growth.

### `SENSITIVE_ACTION_REAUTH_SECONDS`

How long a recent login remains valid for sensitive actions such as revealing a device password:

```dotenv
SENSITIVE_ACTION_REAUTH_SECONDS=1800
```

`1800` seconds equals 30 minutes. After this period, the user must authenticate again.

## Upload and backup limits

All byte values below use bytes, not megabytes.

### `MAX_CONTENT_LENGTH`

Maximum HTTP upload size:

```dotenv
MAX_CONTENT_LENGTH=104857600
```

The default is 100 MiB.

### `FULL_BACKUP_MAX_MEMBERS`

Maximum number of entries accepted in a full-backup archive:

```dotenv
FULL_BACKUP_MAX_MEMBERS=5000
```

### `FULL_BACKUP_MAX_TOTAL_BYTES`

Maximum uncompressed total size accepted from a full-backup archive:

```dotenv
FULL_BACKUP_MAX_TOTAL_BYTES=536870912
```

The default is 512 MiB.

### `FULL_BACKUP_MAX_FILE_BYTES`

Maximum uncompressed size of a single file in a full-backup archive:

```dotenv
FULL_BACKUP_MAX_FILE_BYTES=134217728
```

The default is 128 MiB.

Increase these limits only when the expected backup size requires it and sufficient memory and disk space are available.

## OpenID Connect

### `OIDC_ALLOW_PRIVATE_ISSUER`

Allows OIDC issuer URLs that resolve to private or local network addresses:

```dotenv
OIDC_ALLOW_PRIVATE_ISSUER=false
```

Keep it disabled for public providers. Enable it only when intentionally using a trusted internal identity provider. The actual OIDC issuer, client ID, client secret, claims, and provisioning behavior are configured later in the Web UI by an administrator.

## Optional RustDesk server database mount

### `RUSTDESK_SERVER_DB_HOST_PATH`

Host path of an existing RustDesk `db_v2.sqlite3` file:

```dotenv
RUSTDESK_SERVER_DB_HOST_PATH=/dev/null
```

`/dev/null` disables the optional mount safely. To enable it, use an absolute path to the existing database file, for example:

```dotenv
RUSTDESK_SERVER_DB_HOST_PATH=/docker_data/rustdesk/db_v2.sqlite3
```

The file must already exist before `docker compose up` is executed. The mount is read-only.

### `RUSTDESK_SERVER_DB`

Path used inside the application container:

```dotenv
RUSTDESK_SERVER_DB=
```

Leave it empty when direct database access is not needed. To enable it together with the host path above:

```dotenv
RUSTDESK_SERVER_DB=/rustdesk-server/db_v2.sqlite3
```

Both variables must be set together. This direct mount is separate from CSV, upload, and SSH snapshot imports.

## Signed online updates

### `RAB_UPDATE_BASE_URL`

Base URL used by the signed ZIP update check:

```dotenv
RAB_UPDATE_BASE_URL=https://github.com/the-ab/RustDesk-AddressBook/releases/latest/download
```

The location must provide:

- `latest.txt`
- the update ZIP named in `latest.txt`
- the matching `.zip.sha256`
- the matching `.zip.sig`

To disable online checks while retaining local signed updates:

```dotenv
RAB_UPDATE_BASE_URL=disabled
```

Container-image updates and ZIP-based application updates are separate mechanisms. With the GHCR Compose installation, normally update the image with:

```bash
docker compose pull
docker compose up -d
```

## Timezone

### `TZ`

Timezone used for logs, schedules, and displayed timestamps:

```dotenv
TZ=Europe/Berlin
```

Use an IANA timezone name such as `Europe/Berlin`, `Europe/Vienna`, or `UTC`.

## Applying changes

After editing `.env`, recreate the service:

```bash
docker compose up -d --force-recreate
```

For a changed image tag or a new `latest` image:

```bash
docker compose pull
docker compose up -d
```

Then verify:

```bash
docker compose ps
docker inspect --format '{{.State.Health.Status}}' rustdesk-addressbook
```
