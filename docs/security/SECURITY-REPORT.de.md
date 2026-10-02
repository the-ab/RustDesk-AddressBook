# Community Address Book for RustDesk – Sicherheitsstatus, Kandidat 0.6.3

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

## Veröffentlichte Basis 0.6.2

**Stand:** 14. August 2026  
**Version:** `0.6.2-recovery-codes-update-image-fix`

> Dies ist die deutsche Fassung. Die englische Standardfassung steht in [`SECURITY-REPORT.md`](SECURITY-REPORT.md).

## Behobene Schwerpunkte

- Updatepakete werden vor dem Entpacken über Ed25519 und eine signierte SHA-256-Prüfsumme verifiziert.
- Der Vollbackup-Restore akzeptiert nur reguläre Dateien in erlaubten Pfaden und begrenzt Anzahl, Einzelgröße und entpackte Gesamtgröße.
- Bestehende 0.5.26-Benutzersignaturen werden nur nach erfolgreicher Prüfung des alten Signaturformats migriert. Ab 0.5.27 umfasst die Signatur auch Gruppenzuweisungen und Sitzungsstand.
- Sicherheitsrelevante Kontoänderungen widerrufen bereits bestehende Sitzungen.
- OIDC-Identitäten werden ausschließlich über die Kombination aus Issuer und `sub` gebunden; Domain-Filter verlangen `email_verified=true`.
- Die Ersteinrichtung benötigt ein serverseitig erzeugtes Setup-Token.
- Passwortabruf, RustDesk-Verbindungsstart und CSV-Export mit Passwörtern erfordern eine aktuelle Authentifizierung und werden protokolliert.
- SSH-Import verlangt einen vorab bekannten SHA-256-Hostschlüssel-Fingerprint und verwendet `StrictHostKeyChecking=yes`.
- CSV-Formelinjektion, gespeicherte Icon-DOM-Injektion, unbegrenztes Auth-Ereigniswachstum und externe JavaScript-Abhängigkeiten wurden adressiert.
- Der Container läuft als unprivilegierter Benutzer mit entfernten Capabilities, `no-new-privileges`, schreibgeschütztem Root-Dateisystem und begrenztem tmpfs.
- Python-Abhängigkeiten und das Python-Basisimage sind auf konkrete Versionen festgelegt.

## Bewusst erhaltene Betriebsoptionen

- HTTP kann weiterhin ausdrücklich aktiviert werden, bleibt aber standardmäßig deaktiviert. Für produktiven Zugriff ist HTTPS erforderlich.
- Interne OIDC-Provider bleiben möglich, müssen aber bewusst über `OIDC_ALLOW_PRIVATE_ISSUER=true` freigegeben werden.
- Unsignierte lokale Updates sind nur als expliziter interaktiver Notfallweg über `RAB_ALLOW_UNSIGNED_LOCAL_UPDATES=true` möglich; automatisierte Nutzung bleibt gesperrt.
- Die SQLite-Datenbank ist weiterhin nicht vollständig verschlüsselt. Gerätepasswörter und OIDC-Client-Secret werden feldweise verschlüsselt; `data/config.json` muss entsprechend geschützt und gesichert werden.

## Migrationshinweis

Das alte 0.5.26-Signaturformat enthielt noch keine Gruppenzuweisungen. Beim einmaligen Upgrade werden deshalb die vorhandenen Gruppenzuweisungen nach erfolgreicher Validierung der alten Benutzeridentität als Ausgangszustand übernommen und anschließend mit der neuen Signatur geschützt. Ab diesem Zeitpunkt werden direkte Änderungen an Rollen, Identität, Sitzungsstand oder Gruppenzuweisungen erkannt und die Anmeldung beziehungsweise Sitzung blockiert.

## Containerlaufzeit und Healthcheck

Der eigentliche Webprozess bleibt unprivilegiert. Ein separater profilierter Init-Dienst erhält ausschließlich die für die Berechtigungsvorbereitung benötigten Capabilities und wird über `docker compose run --rm` ausgeführt, sodass Docker ihn direkt nach Abschluss entfernt. Der Healthcheck prüft Listener und SQLite-Verbindung. Das Basisimage verwendet Debian Trixie.

## Dokumentationssprachen

Reguläre Markdown-Dateien sind standardmäßig englisch; deutsche Fassungen tragen die Endung `*.de.md`. Version 0.6.2 behebt die einmalige Anzeige neu erzeugter Wiederherstellungscodes durch UTC-sichere Behandlung kurzlebiger SQLite-Zeitwerte und korrigiert den verwalteten Docker-Image-Namen im Quellcode-Updatepfad. Die bestehende signierte Updateprüfung, Rollen- und Berechtigungsgrenzen, Setup-Token-Bereinigung, Repository-Sicherheitsprüfung und lokale Testreihe bleiben erhalten.

## Hinweis für öffentliche Repositorys

Das Repository ist für eine öffentliche Quellcode-Veröffentlichung vorbereitet. Produktive Daten, `.env`-Dateien, Datenbanken, Backups, Protokolle, private TLS-Schlüssel und private Release-Signaturschlüssel dürfen jedoch niemals eingecheckt werden. Vor dem ersten Push und vor Releases sollte `python scripts/check_repository_safety.py` ausgeführt werden. Sicherheitsmeldungen erfolgen nach [`../../SECURITY.de.md`](../../SECURITY.de.md) und sollen vor einer koordinierten Behebung nicht öffentlich angelegt werden.
