# Community-Adressbuch für RustDesk – Releasehistorie

## Kandidat 0.6.3 — zuverlässiger Restore und Import

Vorbereitet am 02.10.2026; dieser Quellkandidat ist noch nicht veröffentlicht. Die Beispiele für veröffentlichte Images darunter beziehen sich bis zur neuen Image-Veröffentlichung auf 0.6.2.

- Restore prüft unterstütztes SQLite-Schema, Gruppenzuordnungen, Benutzersignaturen und verschlüsselte Felder vor dem Austausch. Vollrestores verwenden eine exklusive Wartungssperre und ein dauerhaftes Rückwegjournal. Ein unterbrochener Restore sperrt Anfragen, bis die Wiederherstellung beim Anwendungsstart den vorherigen Stand hergestellt hat. Laufzeitschlüssel werden pro Webprozess neu geladen; nach Restore erneut anmelden. Nach Wiederherstellung von TLS-Zertifikaten den Container neu starten.
- Backupnamen sind eindeutig; vorhandene Backups werden nie ersetzt. Doppelte RustDesk-IDs teilen eine hbbs-Abfrage, deren Ergebnis alle passenden Geräte erhalten. Fehlerhafte CSV und mehrdeutige DB/WAL/SHM-ZIP-Namen werden vor dem Import abgewiesen. Einstellungen werden einmal pro Anfrage geladen und bei Änderungen neu eingelesen.
- Der korrigierte ZIP-Updater stoppt den Dienst vor der Sicherung der konfigurierten `RAB_DATA_DIR` und `RAB_BACKUP_DIR`, sichert sämtliche verwalteten Quelldateien und lokale Konfigurationen und führt bei Build-/Start-/Health-Fehlern einen Rückweg aus. Ein Health-Timeout gilt als Fehler. `flock` (util-linux) verhindert gleichzeitige Updater-Aufrufe im selben Updateverzeichnis.
- Laufzeitabhängigkeiten: cryptography 50.0.2, requests 2.34.2; Testabhängigkeit: pytest 9.1.1; Python-Containerbasis: 3.13.15.

### Quellcode-Upgrade von 0.6.2

Der bereits in 0.6.2 installierte Updater besitzt keinen vollständigen Rückweg. Vor dem ersten Upgrade die neue Flat-ZIP samt signierter Prüfsumme mit dem vorhandenen vertrauenswürdigen öffentlichen Schlüssel prüfen und anschließend beide korrigierten Updater-Dateien im bestehenden Verzeichnis `scripts/` installieren:

```bash
openssl pkeyutl -verify -pubin -inkey scripts/keys/update-signing-public-v1.pem -rawin -in /pfad/rustdesk-addressbook-update-flat-v0.6.3.zip.sha256 -sigfile /pfad/rustdesk-addressbook-update-flat-v0.6.3.zip.sig
(cd /pfad && sha256sum -c rustdesk-addressbook-update-flat-v0.6.3.zip.sha256)
unzip -o /pfad/rustdesk-addressbook-update-flat-v0.6.3.zip scripts/update.sh scripts/update_transaction.py -d .
bash scripts/update.sh /pfad/rustdesk-addressbook-update-flat-v0.6.3.zip
```

Das erzeugte Pre-Update-Verzeichnis behalten. Falls Host oder Updater vor dem automatischen Rückweg hart beendet werden, Dienst stoppen und `python3 /pfad/preupdate/update_transaction.py rollback /pfad/preupdate` ausführen; anschließend die wiederhergestellte Compose-Installation bauen/starten und den Health-Status prüfen. Kein zweites Update gegen eine nur teilweise wiederhergestellte Installation starten. Bei GHCR-Installationen das gewünschte veröffentlichte Image über `docker-compose/` holen und neu starten; der Quell-ZIP-Updater ist für Quellinstallationen vorgesehen.

## Community-Adressbuch für RustDesk 0.6.2 – Anzeige der Wiederherstellungscodes und zuverlässiger Updatepfad

Release-Datum: 2026-08-14

- Behoben: Nach dem Neuerstellen von Zwei-Faktor-Wiederherstellungscodes wurden die Codes trotz Erfolgsmeldung nicht angezeigt. Ablaufzeitstempel kurzlebiger Secrets erhalten nach SQLite-Roundtrips wieder eindeutig die UTC-Zeitzone, sodass die einmalige Code-Ausgabe zuverlässig funktioniert.
- Behoben: Der Quellcode-ZIP-Updater erkennt verwaltete punktierte Docker-Image-Namen wieder korrekt. Namen wie `rustdesk-addressbook-v0.6.1` werden auf `rustdesk-addressbook-v0.6.2` weitergeführt; tatsächlich benutzerdefinierte Image-Namen bleiben unverändert.
- Behoben: WebUI und `scripts/update.sh` erkennen in `latest.txt` wieder punktierte Release-Dateinamen wie `rustdesk-addressbook-update-flat-v0.6.2.zip`. Das ältere kompakte Namensformat bleibt für vorhandene Installationen rückwärtskompatibel lesbar.
- **Einmaliger Übergangshinweis:** Eine laufende 0.6.1-Installation kann v0.6.2 wegen des alten Online-Parsers nicht automatisch über `latest.txt` entdecken. Das signierte v0.6.2-Triplett daher einmal lokal nach `updates/` kopieren und `./scripts/update.sh` ausführen. Die Signaturprüfung von 0.6.1 akzeptiert das v0.6.2-Paket; nach dem Update funktioniert die punktierte Online-Erkennung wieder.
- Die aktuelle Repository-Dokumentationsstruktur unter `docs/` sowie die Sicherheitsprüfung verpflichtender englischer/deutscher Dokumentationspaare sind Bestandteil dieses Releases. Beim Update werden die vier nach `docs/` verschobenen alten Stammdateien gezielt entfernt, damit keine veralteten Duplikate zurückbleiben.
- Der vollständige Inhalt von Quellcode-Installer und Flat-Update-Paket wurde gegen den aktuellen `main`-Stand geprüft, einschließlich Docker-Builddateien, Update-Verifikation, Skripten, Templates, statischen Dateien, Tests und Dokumentation.
- Die bestehende Ed25519-Vertrauenskette für Updates bleibt unverändert; die Release-ZIPs werden mit dem vorhandenen v1-Release-Schlüssel signiert und mit dem im Paket enthaltenen öffentlichen Schlüssel geprüft.
