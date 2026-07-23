# Community-Adressbuch für RustDesk 0.5.33 – Update-Bereinigung und Installed-Archiv

Englische Standardfassung: [`RELEASE_NOTES.md`](RELEASE_NOTES.md)

## Geändert

- `rustdesk-addressbook-init` wird ausdrücklich als einmaliger Wartungsdienst über `docker compose run --rm` ausgeführt, sodass nach Installation und Updates kein beendeter Init-Container zurückbleibt.
- Erfolgreich installierte Update-ZIPs, SHA-256-Manifeste und Ed25519-Signaturen werden nach bestätigtem Healthcheck aus `updates/` nach `updates/installed/` verschoben.
- Bei fehlgeschlagenen Updates oder nicht bestätigtem Health-Status bleiben die Dateien zur Diagnose in `updates/` liegen.
- Das Release-Datum wird neben der Versionsnummer in der Fußzeile angezeigt.
- Paket-Tag-Normalisierung korrigiert, damit automatisch verwaltete Docker-Image-Namen mit `v0533` übereinstimmen.
- Die veraltete, nicht referenzierte Datei `UPDATE-CHECK.txt` wurde nach einer Prüfung auf verwaiste Paketdateien entfernt.

## Kompatibilität

Datenbank, Anmeldung, Import, Backup, Berechtigungen, OIDC, signierte Online-Updates und eigene Updatequellen bleiben unverändert.
