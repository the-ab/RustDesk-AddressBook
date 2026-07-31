# GHCR-Docker-Compose-Konfiguration

Dieser Ordner enthält die beiden Dateien, die für den Betrieb des Community-Adressbuchs für RustDesk direkt über das veröffentlichte Container-Image benötigt werden:

- `compose.yaml`
- `.env.example`

Für diesen Installationsweg sind keine Projektquellcode-Dateien erforderlich.

> Dies ist ein unabhängiges Community-Projekt. Es ist nicht mit RustDesk oder Purslane Ltd. verbunden und wird von diesen weder unterstützt, gesponsert noch gepflegt.

Englische Dokumentation: [`README.md`](README.md)

## Schnellstart

```bash
mkdir -p /opt/rustdesk-addressbook
cd /opt/rustdesk-addressbook
cp /pfad/zu/docker-compose/compose.yaml .
cp /pfad/zu/docker-compose/.env.example .env
nano .env
docker compose pull
docker compose up -d
```

Container prüfen:

```bash
docker compose ps
docker logs --tail 100 rustdesk-addressbook
```

Das einmalige Setup-Token vor der Erstellung des ersten Administrators auslesen:

```bash
docker exec rustdesk-addressbook python -c \
  'import json; print(json.load(open("/data/config.json"))["SETUP_TOKEN"])'
```

Nach erfolgreicher Erstellung des ersten Administratorkontos entfernt die Anwendung das Setup-Token automatisch aus `/data/config.json`.

## Werte, die normalerweise geprüft werden müssen

Für eine normale Installation sollten mindestens folgende Werte in `.env` geprüft werden:

| Variable | Zweck | Typischer Wert |
|---|---|---|
| `RAB_IMAGE_TAG` | Auszuführende Image-Version | `latest` oder `0.6.1` |
| `RAB_DATA_DIR` | Persistente Anwendungsdaten auf dem Host | `/docker_data/rustdesk-addressbook/data` |
| `RAB_BACKUP_DIR` | Persistente Backups auf dem Host | `/docker_data/rustdesk-addressbook/backups` |
| `RAB_HTTPS_PUBLISH_PORT` | Auf dem Host veröffentlichter HTTPS-Port | `5443` |
| `HTTPS_COMMON_NAME` | Hauptname im automatisch erzeugten Zertifikat | DNS-Name des Servers |
| `HTTPS_ALT_NAMES` | Weitere DNS-Namen und IP-Adressen für das Zertifikat | `localhost,127.0.0.1,addressbook.example.org` |
| `TZ` | Zeitzone des Containers | `Europe/Berlin` |

Die übrigen Standardwerte können normalerweise unverändert bleiben, solange keine abweichenden Ports, ein Reverse Proxy, eigene Zertifikate, ein RustDesk-Datenbank-Mount oder ein privater OIDC-Provider benötigt werden.

## Image und Container

### `RAB_IMAGE_TAG`

Legt den Tag von `ghcr.io/the-ab/rustdesk-addressbook` fest.

```dotenv
RAB_IMAGE_TAG=latest
```

- `latest`: verwendet jeweils das neueste veröffentlichte Image.
- `0.6.1`: verwendet dauerhaft genau dieses Release.

Für einen vorhersehbaren Produktivbetrieb empfiehlt sich ein fester Release-Tag, der bewusst aktualisiert wird.

### `RAB_CONTAINER_NAME`

Docker-Containername. Standard:

```dotenv
RAB_CONTAINER_NAME=rustdesk-addressbook
```

Nur ändern, wenn auf demselben Docker-Host mehrere voneinander getrennte Installationen betrieben werden.

### `RAB_HOSTNAME`

Hostname innerhalb des Containers:

```dotenv
RAB_HOSTNAME=rustdesk-addressbook
```

Dieser Wert muss normalerweise nicht geändert werden.

## Persistente Speicherung

### `RAB_DATA_DIR`

Hostverzeichnis, das nach `/data` eingebunden wird. Dort liegen SQLite-Datenbank, Laufzeitkonfiguration, Zertifikate, SSH-Dateien, Protokolle und weitere persistente Anwendungsdaten.

```dotenv
RAB_DATA_DIR=/docker_data/rustdesk-addressbook/data
```

Dieses Verzeichnis sichern und niemals in das Git-Repository aufnehmen.

### `RAB_BACKUP_DIR`

Hostverzeichnis, das für durch die Anwendung erzeugte Backups nach `/backups` eingebunden wird:

```dotenv
RAB_BACKUP_DIR=/docker_data/rustdesk-addressbook/backups
```

Das Verzeichnis muss auf persistentem Speicher liegen. Für zusätzlichen Schutz sollten die Inhalte auf ein weiteres System kopiert werden.

### `RAB_RUNTIME_UID` und `RAB_RUNTIME_GID`

Numerische Benutzer- und Gruppen-ID des unprivilegierten Anwendungsprozesses:

```dotenv
RAB_RUNTIME_UID=10001
RAB_RUNTIME_GID=10001
```

Der Container bereitet die eingebundenen Verzeichnisse für diese IDs vor und verwirft anschließend seine erhöhten Rechte. Die Standardwerte nur ändern, wenn die Berechtigungen bewusst an ein vorhandenes Hostkonto angepasst werden sollen. Beide Werte müssen positive Ganzzahlen sein.

## HTTPS und HTTP

### `APP_ENABLE_HTTPS`

Aktiviert den HTTPS-Listener im Container:

```dotenv
APP_ENABLE_HTTPS=true
```

Für direkten Zugriff sollte HTTPS aktiviert bleiben.

### `RAB_HTTPS_BIND`

Hostschnittstelle, an der der HTTPS-Port veröffentlicht wird:

```dotenv
RAB_HTTPS_BIND=0.0.0.0
```

- `0.0.0.0`: über alle Hostschnittstellen erreichbar, abhängig von den Firewallregeln.
- `127.0.0.1`: nur lokal erreichbar, sinnvoll hinter einem Reverse Proxy auf demselben Host.
- Eine bestimmte Host-IP: Veröffentlichung nur auf dieser Schnittstelle.

### `RAB_HTTPS_PUBLISH_PORT`

Externer HTTPS-Port:

```dotenv
RAB_HTTPS_PUBLISH_PORT=5443
```

Der interne Containerport bleibt `5443`.

### `APP_ENABLE_HTTP`

Aktiviert den unverschlüsselten HTTP-Listener:

```dotenv
APP_ENABLE_HTTP=false
```

Nur aktivieren, wenn HTTP in einem vertrauenswürdigen Netz oder hinter einem lokalen Reverse Proxy ausdrücklich benötigt wird. Zugangsdaten niemals über eine nicht vertrauenswürdige HTTP-Verbindung übertragen.

### `RAB_HTTP_BIND` und `RAB_HTTP_PUBLISH_PORT`

Hostbindung und externer Port für HTTP:

```dotenv
RAB_HTTP_BIND=0.0.0.0
RAB_HTTP_PUBLISH_PORT=5055
```

Diese Werte werden erst mit `APP_ENABLE_HTTP=true` wirksam.

## Zertifikate

### `HTTPS_CERT_FILE` und `HTTPS_KEY_FILE`

Pfade im Container zum TLS-Zertifikat und privaten Schlüssel:

```dotenv
HTTPS_CERT_FILE=/data/certs/addressbook.crt
HTTPS_KEY_FILE=/data/certs/addressbook.key
```

Für eigene Zertifikate beide Dateien im entsprechenden Hostverzeichnis unter `RAB_DATA_DIR/certs/` ablegen. Fehlen sie, erzeugt die Anwendung ein selbstsigniertes Zertifikat.

### `HTTPS_COMMON_NAME`

Common Name für das automatisch erzeugte selbstsignierte Zertifikat:

```dotenv
HTTPS_COMMON_NAME=rustdesk-addressbook.local
```

Hier sollte der DNS-Name stehen, über den die Anwendung normalerweise geöffnet wird.

### `HTTPS_ALT_NAMES`

Kommagetrennte Subject Alternative Names für das erzeugte Zertifikat:

```dotenv
HTTPS_ALT_NAMES=localhost,127.0.0.1,rustdesk-addressbook.local
```

Alle DNS-Namen und IP-Adressen ergänzen, über die Clients auf die Anwendung zugreifen. Keine Leerzeichen um die Kommas einfügen.

## Anwendungsserver

### `APP_WORKERS`

Anzahl der Gunicorn-Workerprozesse:

```dotenv
APP_WORKERS=1
```

Ein Worker ist für die SQLite-basierte Installation der sicherste Standard. Nur nach Tests mit der eigenen Last und dem Datenbankverhalten erhöhen.

### `APP_THREADS`

Threads pro Gunicorn-Worker:

```dotenv
APP_THREADS=4
```

Der Standard eignet sich für normale kleine und mittlere Installationen.

### `APP_TIMEOUT`

Maximale Dauer einer Gunicorn-Anfrage in Sekunden:

```dotenv
APP_TIMEOUT=60
```

Nur erhöhen, wenn legitime Importe oder Backupvorgänge regelmäßig länger als der Standard dauern.

## Sitzung und Proxy-Sicherheit

### `SESSION_COOKIE_SECURE`

Beschränkt das Anmelde-Cookie auf HTTPS-Verbindungen:

```dotenv
SESSION_COOKIE_SECURE=true
```

Bei HTTPS aktiviert lassen. Nur für eine bewusst unverschlüsselte Testinstallation auf `false` setzen.

### `APP_HSTS`

Aktiviert den HTTP-Strict-Transport-Security-Header:

```dotenv
APP_HSTS=false
```

Erst aktivieren, wenn HTTPS dauerhaft eingerichtet ist und alle Clients dem Zertifikat vertrauen. Browser merken sich HSTS und verweigern anschließend HTTP-Zugriffe.

### `TRUST_PROXY_HEADERS`

Erlaubt der Anwendung, weitergeleiteten Protokoll- und Client-IP-Headern zu vertrauen:

```dotenv
TRUST_PROXY_HEADERS=false
```

Nur auf `true` setzen, wenn die Anwendung ausschließlich über einen vertrauenswürdigen Reverse Proxy erreichbar ist, der diese Header überschreibt. Nicht aktivieren, wenn Clients den Container direkt erreichen können.

## Login-Schutz und Sicherheitsprotokolle

### `LOGIN_FAIL_LIMIT`

Maximale Anzahl fehlgeschlagener Anmeldungen von einer Quell-IP innerhalb des eingestellten Zeitfensters:

```dotenv
LOGIN_FAIL_LIMIT=5
```

### `LOGIN_FAIL_WINDOW_SECONDS`

Länge des Auswertungszeitfensters für Fehlanmeldungen in Sekunden:

```dotenv
LOGIN_FAIL_WINDOW_SECONDS=900
```

`900` Sekunden entsprechen 15 Minuten.

### `AUTH_LOG_ROTATE_DAYS`

Alter in Tagen, nach dem `auth.log` rotiert wird:

```dotenv
AUTH_LOG_ROTATE_DAYS=7
```

### `AUTH_LOG_ROTATE_KEEP`

Anzahl aufbewahrter rotierter Authentifizierungsprotokolle:

```dotenv
AUTH_LOG_ROTATE_KEEP=8
```

### `AUTH_EVENT_RETENTION_DAYS`

Maximales Alter der in SQLite gespeicherten Authentifizierungsereignisse:

```dotenv
AUTH_EVENT_RETENTION_DAYS=90
```

### `AUTH_EVENT_MAX_ROWS`

Maximale Anzahl gespeicherter Authentifizierungsereignisse in SQLite:

```dotenv
AUTH_EVENT_MAX_ROWS=50000
```

Alters- und Zeilenlimit verhindern gemeinsam ein unbegrenztes Wachstum der Datenbank.

### `SENSITIVE_ACTION_REAUTH_SECONDS`

Zeitraum, in dem eine kürzlich erfolgte Anmeldung für sensible Aktionen wie das Anzeigen eines Gerätepassworts gilt:

```dotenv
SENSITIVE_ACTION_REAUTH_SECONDS=1800
```

`1800` Sekunden entsprechen 30 Minuten. Danach muss sich der Benutzer erneut authentifizieren.

## Upload- und Backup-Grenzen

Die folgenden Größenwerte werden in Bytes angegeben.

### `MAX_CONTENT_LENGTH`

Maximale HTTP-Uploadgröße:

```dotenv
MAX_CONTENT_LENGTH=104857600
```

Der Standard entspricht 100 MiB.

### `FULL_BACKUP_MAX_MEMBERS`

Maximale Anzahl von Einträgen in einem Vollbackup-Archiv:

```dotenv
FULL_BACKUP_MAX_MEMBERS=5000
```

### `FULL_BACKUP_MAX_TOTAL_BYTES`

Maximale unkomprimierte Gesamtgröße eines Vollbackup-Archivs:

```dotenv
FULL_BACKUP_MAX_TOTAL_BYTES=536870912
```

Der Standard entspricht 512 MiB.

### `FULL_BACKUP_MAX_FILE_BYTES`

Maximale unkomprimierte Größe einer einzelnen Datei im Vollbackup:

```dotenv
FULL_BACKUP_MAX_FILE_BYTES=134217728
```

Der Standard entspricht 128 MiB.

Diese Grenzen nur erhöhen, wenn die erwartete Backupgröße dies erfordert und ausreichend Arbeitsspeicher sowie Speicherplatz vorhanden sind.

## OpenID Connect

### `OIDC_ALLOW_PRIVATE_ISSUER`

Erlaubt OIDC-Issuer-URLs, die auf private oder lokale Netzwerkadressen zeigen:

```dotenv
OIDC_ALLOW_PRIVATE_ISSUER=false
```

Für öffentliche Provider deaktiviert lassen. Nur für einen bewusst eingesetzten, vertrauenswürdigen internen Identity Provider aktivieren. Der eigentliche OIDC-Issuer, Client-ID, Client-Secret, Claims und die Benutzeranlage werden später durch einen Administrator in der WebUI konfiguriert.

## Optionaler RustDesk-Serverdatenbank-Mount

### `RUSTDESK_SERVER_DB_HOST_PATH`

Hostpfad zu einer vorhandenen RustDesk-Datei `db_v2.sqlite3`:

```dotenv
RUSTDESK_SERVER_DB_HOST_PATH=/dev/null
```

`/dev/null` deaktiviert den optionalen Mount sicher. Für die Aktivierung einen absoluten Pfad zur vorhandenen Datenbankdatei eintragen, zum Beispiel:

```dotenv
RUSTDESK_SERVER_DB_HOST_PATH=/docker_data/rustdesk/db_v2.sqlite3
```

Die Datei muss bereits vor `docker compose up` vorhanden sein. Sie wird read-only eingebunden.

### `RUSTDESK_SERVER_DB`

Von der Anwendung im Container verwendeter Pfad:

```dotenv
RUSTDESK_SERVER_DB=
```

Leer lassen, wenn kein direkter Datenbankzugriff benötigt wird. Zur Aktivierung gemeinsam mit dem obigen Hostpfad setzen:

```dotenv
RUSTDESK_SERVER_DB=/rustdesk-server/db_v2.sqlite3
```

Beide Variablen müssen gemeinsam gesetzt werden. Dieser direkte Mount ist unabhängig von CSV-, Upload- und SSH-Snapshot-Importen.

## Signierte Online-Updates

### `RAB_UPDATE_BASE_URL`

Basisadresse für die Prüfung auf signierte ZIP-Updates:

```dotenv
RAB_UPDATE_BASE_URL=https://github.com/the-ab/RustDesk-AddressBook/releases/latest/download
```

Dort müssen verfügbar sein:

- `latest.txt`
- die in `latest.txt` genannte Update-ZIP
- die zugehörige `.zip.sha256`
- die zugehörige `.zip.sig`

Zum Abschalten der Online-Prüfung bei weiterhin möglichen lokalen signierten Updates:

```dotenv
RAB_UPDATE_BASE_URL=disabled
```

Container-Image-Updates und ZIP-basierte Anwendungsupdates sind getrennte Verfahren. Bei der GHCR-Compose-Installation wird das Image normalerweise so aktualisiert:

```bash
docker compose pull
docker compose up -d
```

## Zeitzone

### `TZ`

Zeitzone für Protokolle, Zeitpläne und angezeigte Zeitstempel:

```dotenv
TZ=Europe/Berlin
```

Einen IANA-Zeitzonennamen wie `Europe/Berlin`, `Europe/Vienna` oder `UTC` verwenden.

## Änderungen anwenden

Nach einer Änderung der `.env` den Dienst neu erstellen:

```bash
docker compose up -d --force-recreate
```

Bei geändertem Image-Tag oder einem neuen `latest`-Image:

```bash
docker compose pull
docker compose up -d
```

Anschließend prüfen:

```bash
docker compose ps
docker inspect --format '{{.State.Health.Status}}' rustdesk-addressbook
```
