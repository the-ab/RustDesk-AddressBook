# Dokumentation

Im Repository-Stamm bleiben nur Dateien, die GitHub, Installationsabläufe, Mitwirkende oder Benutzer dort üblicherweise erwarten. Ausführliche historische Dokumente und Sicherheitsstatusberichte sind nachfolgend geordnet.

> Englisch ist die Standardsprache der öffentlichen Dokumentation. Jede gepflegte Informationsdatei benötigt eine inhaltlich gleichwertige deutsche Fassung am selben Pfad und mit demselben Dateinamen, ergänzt um `.de.md` vor der Endung `.md`. Beispiel: `GUIDE.md` und `GUIDE.de.md`.

## Sprach- und Dateiregel

- `DATEI.md` ist immer Englisch.
- `DATEI.de.md` ist immer Deutsch.
- Beide Fassungen werden gemeinsam erstellt, verschoben, umbenannt, aktualisiert und entfernt.
- Links sollen in jeder Sprachfassung bevorzugt auf die entsprechende Sprachdatei verweisen.
- Ändert ein Pull Request eine Fassung, muss die andere Fassung im selben Umfang mitgepflegt werden.
- Quellcode, Lizenzen, maschinenlesbare Konfiguration, generierte Dateien und technische Artefakte sind keine sprachgebundenen Informationsdateipaare.
- Die Repository-Sicherheitsprüfung kontrolliert die für dieses Projekt verbindlichen Dokumentationspaare.

## Benutzer- und Administrationsdokumentation

- [`../README.de.md`](../README.de.md) – Projektübersicht und Installation
- [`../ADMIN-GUIDE.de.md`](../ADMIN-GUIDE.de.md) – ausführliche Administrator- und Bedienungsanleitung
- [`../docker-compose/README.de.md`](../docker-compose/README.de.md) – Referenz der GHCR-Compose-Umgebung

## Release-Dokumentation

- [`releases/RELEASE_NOTES.md`](releases/RELEASE_NOTES.md)
- [`releases/RELEASE_NOTES.de.md`](releases/RELEASE_NOTES.de.md)

## Sicherheitsdokumentation

- [`../SECURITY.de.md`](../SECURITY.de.md) – Richtlinie zur Meldung von Schwachstellen
- [`security/SECURITY-REPORT.md`](security/SECURITY-REPORT.md) – veröffentlichter Sicherheitsstatus
- [`security/SECURITY-REPORT.de.md`](security/SECURITY-REPORT.de.md) – deutscher Sicherheitsstatus

## Umfang des öffentlichen Repositorys

Interne Übergaben, private Entscheidungen, unveröffentlichte Planungen und private Betriebsnotizen werden außerhalb dieses öffentlichen Repositorys gepflegt. Geheimnisse, produktive Konfigurationen, Datenbanken, Backups, Protokolle und private Signaturschlüssel dürfen niemals eingecheckt werden.
