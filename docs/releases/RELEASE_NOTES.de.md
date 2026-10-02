# Community-Adressbuch für RustDesk – Releasehistorie

## Community-Adressbuch für RustDesk 0.6.4 – Skriptrechte und Dokumentation

Versionsdatum: 02.10.2026. Status: signierter Quellkandidat; GitHub-Release und GHCR-Image noch nicht veröffentlicht.

- Alle fünf mitgelieferten Shellskripte in Git und beiden ZIP-Paketen ausführbar speichern; Ausführungsrechte nach dem Entpacken ausdrücklich wiederherstellen.
- Vollständige 0.6.3- und 0.6.4-Einträge in der englischen/deutschen WebUI-Releasehistorie ergänzen und aktuelle Installations-/Hilfe-/Updatebeispiele abstimmen.
- Bestehende Quellinstallationen mit 0.6.3 können dieses signierte Wartungsupdate 0.6.4 regulär installieren; fehlt dem alten Updater das Ausführungsrecht, mit bash starten.

Bei installierter 0.6.3 mit fehlenden Ausführungsrechten `bash scripts/update.sh /pfad/rustdesk-addressbook-update-flat-v0.6.4.zip` starten. Reguläre Signatur-/SHA-Prüfung, Persistenzsicherung und Rückweg bleiben aktiv. Bei installierter 0.6.2 zuerst die [einmalige Updater-Vorbereitung](../../ADMIN-GUIDE.de.md#quellcode-upgrade-von-062) durchführen.

## Community-Adressbuch für RustDesk 0.6.3 – Zuverlässiger Restore, Import und Updatepfad

Versionsdatum: 02.10.2026. Status: signierter Quellkandidat; GitHub-Release und GHCR-Image noch nicht veröffentlicht.

- Unterstütztes SQLite-Schema, Gruppenzuordnungen, Benutzersignaturen und verschlüsselte Felder vor dem Datenbank-Restore prüfen.
- Vollrestores durch exklusive Wartungssperre und dauerhaftes Rückwegjournal schützen; unterbrochene Restores beim Anwendungsstart wiederherstellen und Schlüssel in allen Webprozessen neu laden.
- Eindeutige Backupnamen erzeugen, ohne vorhandene Backups zu überschreiben.
- Jede RustDesk-ID pro hbbs-Stapel nur einmal abfragen und alle Geräte mit derselben ID aktualisieren.
- Fehlerhafte CSV und mehrdeutige Datenbank-/WAL-/SHM-ZIP-Namen vor dem Import abweisen; Stapelabfragen vor der Änderung des Gerätestatus vollständig abschließen.
- Einstellungen einmal pro Anfrage laden und den Cache bei Änderungen verwerfen.
- Dienst vor der Sicherung konfigurierter Daten-/Backuppfade und sämtlicher verwalteter Quellen stoppen; ZIP-Updates bei Build-, Start- oder Health-Fehlern zurückrollen und einen Health-Timeout als Fehler melden.
- Gleichzeitige Updater-Aufrufe mit flock sperren und ausschließlich den konfigurierten Containernamen verwenden.
- cryptography auf 50.0.2, requests auf 2.34.2, pytest auf 9.1.1 und die Python-Containerbasis auf 3.13.15 aktualisieren.
- Englische/deutsche Dokumentation, Installationsbeispiele, WebUI-Hilfe und Änderungshistorie auf 0.6.3 abstimmen.

### Hinweise zum Wechsel

Vor dem ersten Quellcode-Upgrade von 0.6.2 das signierte neue Paket prüfen und beide korrigierten Updater-Dateien gemäß [Administratorhandbuch](../../ADMIN-GUIDE.de.md#quellcode-upgrade-von-062) übernehmen. Der in 0.6.2 enthaltene Updater bietet den neuen vollständigen Rückweg noch nicht. Pre-Update-Sicherung behalten.

Nach einem Vollrestore erneut anmelden. Wurden TLS-Zertifikate wiederhergestellt, den Container neu starten. Verhindern parallele Anfragen die exklusive Restore-Sperre, den Restore in einer ruhigen Phase erneut versuchen. GHCR-Installationen verwenden ihren veröffentlichten Image-Updatepfad.

## Community-Adressbuch für RustDesk 0.6.2 – Anzeige der Wiederherstellungscodes und zuverlässiger Updatepfad

Release-Datum: 2026-08-14

- Behoben: Nach dem Neuerstellen von Zwei-Faktor-Wiederherstellungscodes wurden die Codes trotz Erfolgsmeldung nicht angezeigt. Ablaufzeitstempel kurzlebiger Secrets erhalten nach SQLite-Roundtrips wieder eindeutig die UTC-Zeitzone, sodass die einmalige Code-Ausgabe zuverlässig funktioniert.
- Behoben: Der Quellcode-ZIP-Updater erkennt verwaltete punktierte Docker-Image-Namen wieder korrekt. Namen wie `rustdesk-addressbook-v0.6.1` werden auf `rustdesk-addressbook-v0.6.2` weitergeführt; tatsächlich benutzerdefinierte Image-Namen bleiben unverändert.
- Behoben: WebUI und `scripts/update.sh` erkennen in `latest.txt` wieder punktierte Release-Dateinamen wie `rustdesk-addressbook-update-flat-v0.6.2.zip`. Das ältere kompakte Namensformat bleibt für vorhandene Installationen rückwärtskompatibel lesbar.
- **Einmaliger Übergangshinweis:** Eine laufende 0.6.1-Installation kann v0.6.2 wegen des alten Online-Parsers nicht automatisch über `latest.txt` entdecken. Das signierte v0.6.2-Triplett daher einmal lokal nach `updates/` kopieren und `./scripts/update.sh` ausführen. Die Signaturprüfung von 0.6.1 akzeptiert das v0.6.2-Paket; nach dem Update funktioniert die punktierte Online-Erkennung wieder.
- Die aktuelle Repository-Dokumentationsstruktur unter `docs/` sowie die Sicherheitsprüfung verpflichtender englischer/deutscher Dokumentationspaare sind Bestandteil dieses Releases. Beim Update werden die vier nach `docs/` verschobenen alten Stammdateien gezielt entfernt, damit keine veralteten Duplikate zurückbleiben.
- Der vollständige Inhalt von Quellcode-Installer und Flat-Update-Paket wurde gegen den aktuellen `main`-Stand geprüft, einschließlich Docker-Builddateien, Update-Verifikation, Skripten, Templates, statischen Dateien, Tests und Dokumentation.
- Die bestehende Ed25519-Vertrauenskette für Updates bleibt unverändert; die Release-ZIPs werden mit dem vorhandenen v1-Release-Schlüssel signiert und mit dem im Paket enthaltenen öffentlichen Schlüssel geprüft.
