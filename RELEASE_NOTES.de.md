# Community-Adressbuch für RustDesk 0.5.32 – GitHub Releases als Update-Standard

Englische Standardfassung: [`RELEASE_NOTES.md`](RELEASE_NOTES.md)

## Geändert

- `https://github.com/the-ab/RustDesk-AddressBook/releases/latest/download` als feste Standardquelle für signierte Online-Updates gesetzt.
- Die `latest.txt` im neuesten veröffentlichten GitHub-Release bestimmt die aktuelle Flat-Update-ZIP.
- Der Updater lädt die gewählte ZIP sowie die passenden Dateien `.zip.sha256` und `.zip.sig` aus demselben Release.
- Bestehende eigene, nicht leere `RAB_UPDATE_BASE_URL`-Werte bleiben unterstützt.
- `RAB_UPDATE_BASE_URL=disabled` schaltet Online-Prüfungen ausdrücklich ab; lokale signierte Updates bleiben verfügbar.
- Eine fertig vorbereitete `latest.txt` wird zusammen mit den Release-Dateien bereitgestellt.

## Kompatibilität

Datenbank, Anmeldung, Import, Backup und Berechtigungen bleiben unverändert. Bestehende Installationen mit leerer Update-URL verwenden nach dem Update automatisch die GitHub-Releases des Projekts.
