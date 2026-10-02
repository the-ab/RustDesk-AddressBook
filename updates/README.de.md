# Signierte Updates

Von einer installierten 0.6.3 den regulären signierten Updateweg verwenden. Ist update.sh nicht ausführbar, vorübergehend mit `bash scripts/update.sh` starten; 0.6.4 stellt die Skriptrechte wieder her.

Vor dem ersten Quellcode-Upgrade von 0.6.2 die [einmalige Updater-Vorbereitung](../ADMIN-GUIDE.de.md#quellcode-upgrade-von-062) durchführen. Signierte Pakete 0.6.4 stehen in GitHub Releases und über die konfigurierte Online-Updatequelle bereit.

Kopiere ein Flat-Update-ZIP und beide passenden Prüfdateien in dieses Verzeichnis:

```bash
cp /pfad/rustdesk-addressbook-update-flat-v0.6.4.zip updates/
cp /pfad/rustdesk-addressbook-update-flat-v0.6.4.zip.sha256 updates/
cp /pfad/rustdesk-addressbook-update-flat-v0.6.4.zip.sig updates/
./scripts/update.sh
```

Nach erfolgreicher Installation und bestätigtem Container-Healthcheck werden ZIP, Prüfsummenmanifest und Signatur nach `updates/installed/` verschoben. Fehlgeschlagene oder nicht eindeutig bestätigte Updates bleiben zur Diagnose in `updates/`. Die Berechtigungsvorbereitung läuft als `docker compose run --rm rustdesk-addressbook-init`, sodass kein beendeter Init-Container zurückbleibt.

Der Updater wählt das höchste lokale `rustdesk-addressbook-update-flat-v*.zip`, prüft das signierte SHA-256-Manifest mit dem eingebetteten öffentlichen Ed25519-Schlüssel, kontrolliert die ZIP-Struktur, erstellt eine Rollback-Sicherung und installiert nur eine neuere Version.

Online-Prüfungen verwenden standardmäßig `https://github.com/the-ab/RustDesk-AddressBook/releases/latest/download`. Das neueste veröffentlichte Release muss `latest.txt`, die darin genannte ZIP, `.zip.sha256` und `.zip.sig` bereitstellen. Mit `RAB_UPDATE_BASE_URL=disabled` werden Online-Prüfungen ausdrücklich abgeschaltet. Der private Release-Signaturschlüssel darf niemals in diesem Verzeichnis oder im Repository gespeichert werden.

Die englische Standardfassung befindet sich in [`README.md`](README.md).
