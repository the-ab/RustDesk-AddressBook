# Community-Adressbuch für RustDesk 0.6.2 – Anzeige der Wiederherstellungscodes und zuverlässiger Updatepfad

Release-Datum: 2026-08-14

- Behoben: Nach dem Neuerstellen von Zwei-Faktor-Wiederherstellungscodes wurden die Codes trotz Erfolgsmeldung nicht angezeigt. Ablaufzeitstempel kurzlebiger Secrets erhalten nach SQLite-Roundtrips wieder eindeutig die UTC-Zeitzone, sodass die einmalige Code-Ausgabe zuverlässig funktioniert.
- Behoben: Der Quellcode-ZIP-Updater erkennt verwaltete punktierte Docker-Image-Namen wieder korrekt. Namen wie `rustdesk-addressbook-v0.6.1` werden auf `rustdesk-addressbook-v0.6.2` weitergeführt; tatsächlich benutzerdefinierte Image-Namen bleiben unverändert.
- Behoben: WebUI und `scripts/update.sh` erkennen in `latest.txt` wieder punktierte Release-Dateinamen wie `rustdesk-addressbook-update-flat-v0.6.2.zip`. Das ältere kompakte Namensformat bleibt für vorhandene Installationen rückwärtskompatibel lesbar.
- **Einmaliger Übergangshinweis:** Eine laufende 0.6.1-Installation kann v0.6.2 wegen des alten Online-Parsers nicht automatisch über `latest.txt` entdecken. Das signierte v0.6.2-Triplett daher einmal lokal nach `updates/` kopieren und `./scripts/update.sh` ausführen. Die Signaturprüfung von 0.6.1 akzeptiert das v0.6.2-Paket; nach dem Update funktioniert die punktierte Online-Erkennung wieder.
- Die aktuelle Repository-Dokumentationsstruktur unter `docs/` sowie die Sicherheitsprüfung verpflichtender englischer/deutscher Dokumentationspaare sind Bestandteil dieses Releases. Beim Update werden die vier nach `docs/` verschobenen alten Stammdateien gezielt entfernt, damit keine veralteten Duplikate zurückbleiben.
- Der vollständige Inhalt von Quellcode-Installer und Flat-Update-Paket wurde gegen den aktuellen `main`-Stand geprüft, einschließlich Docker-Builddateien, Update-Verifikation, Skripten, Templates, statischen Dateien, Tests und Dokumentation.
- Die bestehende Ed25519-Vertrauenskette für Updates bleibt unverändert; die Release-ZIPs werden mit dem vorhandenen v1-Release-Schlüssel signiert und mit dem im Paket enthaltenen öffentlichen Schlüssel geprüft.
