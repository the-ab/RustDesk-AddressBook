# Community Address Book for RustDesk – Sicherheitsstatus 0.5.32

**Stand:** 21. Juli 2026  
**Version:** `0.5.32-github-release-update-default`

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


## 0.5.28 Betriebsstabilität

Der eigentliche Webprozess bleibt unprivilegiert. Ein separater, kurzlebiger Init-Dienst erhält ausschließlich die für die Berechtigungsvorbereitung benötigten Capabilities. Der neue Healthcheck prüft Listener und SQLite-Verbindung. Das Basisimage verwendet Debian Trixie.

## Dokumentationssprachen

Reguläre Markdown-Dateien sind standardmäßig englisch; deutsche Fassungen tragen die Endung `*.de.md`. Version 0.5.32 setzt die GitHub-Releases des Projekts als Standardquelle für signierte Updates, ohne GitHub-Automatisierungen wieder einzuführen. Repository-Sicherheitsprüfung, lokale Testreihe, Werkzeuge zur Abhängigkeitsprüfung und die Richtlinie zur vertraulichen Meldung von Schwachstellen bleiben zur manuellen Nutzung erhalten. Diese Repository-Änderung schwächt die bestehenden Laufzeitschutzmaßnahmen nicht.


## Hinweis für öffentliche Repositorys

Das Repository ist für eine öffentliche Quellcode-Veröffentlichung vorbereitet. Produktive Daten, `.env`-Dateien, Datenbanken, Backups, Protokolle, private TLS-Schlüssel und private Release-Signaturschlüssel dürfen jedoch niemals eingecheckt werden. Vor dem ersten Push und vor Releases sollte `python scripts/check_repository_safety.py` ausgeführt werden. Sicherheitsmeldungen erfolgen nach [`SECURITY.de.md`](SECURITY.de.md) und sollen vor einer koordinierten Behebung nicht öffentlich angelegt werden.
