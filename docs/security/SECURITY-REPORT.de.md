# Community Address Book for RustDesk – Sicherheitsstatus, Release 0.6.4

**Stand:** 02.10.2026

**Version:** `0.6.4-shell-script-permissions` (Release 0.6.4)

## Änderungen in 0.6.3 und 0.6.4

- Alle fünf mitgelieferten Shellskripte in Git und beiden ZIP-Paketen ausführbar speichern; Ausführungsrechte nach dem Entpacken ausdrücklich wiederherstellen.
- Unterstütztes SQLite-Schema, Gruppenzuordnungen, Benutzersignaturen und verschlüsselte Felder vor dem Datenbank-Restore prüfen.
- Vollrestores durch exklusive Wartungssperre und dauerhaftes Rückwegjournal schützen; unterbrochene Restores beim Anwendungsstart wiederherstellen und Schlüssel in allen Webprozessen neu laden.
- Eindeutige Backupnamen erzeugen, ohne vorhandene Backups zu überschreiben.
- Fehlerhafte CSV und mehrdeutige Datenbank-/WAL-/SHM-ZIP-Namen vor dem Import abweisen; Stapelabfragen vor der Änderung des Gerätestatus vollständig abschließen.
- Dienst vor der Sicherung konfigurierter Daten-/Backuppfade und sämtlicher verwalteter Quellen stoppen; ZIP-Updates bei Build-, Start- oder Health-Fehlern zurückrollen und einen Health-Timeout als Fehler melden.
- Gleichzeitige Updater-Aufrufe mit flock sperren und ausschließlich den konfigurierten Containernamen verwenden.
- cryptography auf 50.0.2, requests auf 2.34.2, pytest auf 9.1.1 und die Python-Containerbasis auf 3.13.15 aktualisieren.

Der bestehende öffentliche Update-Prüfschlüssel bleibt erhalten. Start-Recovery, Restore-Sperre, Schema-/Schlüsselprüfung und Updater-Rückweg sind durch lokale Regressionen geprüft; ein echter Docker-Wechsel von der signierten 0.6.2 erhält Administrator, verschlüsselte Gerätedaten und Konfiguration. Dies ist eine technische Prüfung, keine vollständige Produktions- oder Sicherheitsabnahme. Vor einem Wechsel mit dem installierten 0.6.2-Updater das [Administratorhandbuch](../../ADMIN-GUIDE.de.md#quellcode-upgrade-von-062) beachten.

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

Reguläre Markdown-Dateien sind standardmäßig englisch; deutsche Fassungen tragen die Endung `*.de.md`. README, Administratorhandbuch, WebUI-Hilfe und Release Notes beschreiben 0.6.4; historische Release-Einträge und Beispiele veröffentlichter GHCR-Images behalten ihren ursprünglichen Versionsstand. Die bestehende signierte Updateprüfung, Rollen- und Berechtigungsgrenzen, Setup-Token-Bereinigung, Repository-Sicherheitsprüfung und lokale Testreihe bleiben erhalten.

## Hinweis für öffentliche Repositorys

Das Repository ist für eine öffentliche Quellcode-Veröffentlichung vorbereitet. Produktive Daten, `.env`-Dateien, Datenbanken, Backups, Protokolle, private TLS-Schlüssel und private Release-Signaturschlüssel dürfen jedoch niemals eingecheckt werden. Vor dem ersten Push und vor Releases sollte `python scripts/check_repository_safety.py` ausgeführt werden. Sicherheitsmeldungen erfolgen nach [`../../SECURITY.de.md`](../../SECURITY.de.md) und sollen vor einer koordinierten Behebung nicht öffentlich angelegt werden.
