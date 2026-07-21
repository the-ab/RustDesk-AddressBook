# Signierte Updates

Kopiere ein Flat-Update-ZIP und beide passenden Prüfdateien in dieses Verzeichnis:

```bash
cp /pfad/rustdesk-addressbook-update-flat-v0532.zip updates/
cp /pfad/rustdesk-addressbook-update-flat-v0532.zip.sha256 updates/
cp /pfad/rustdesk-addressbook-update-flat-v0532.zip.sig updates/
./scripts/update.sh
```

Der Updater wählt das höchste lokale `rustdesk-addressbook-update-flat-v*.zip`, prüft das signierte SHA-256-Manifest mit dem eingebetteten öffentlichen Ed25519-Schlüssel, kontrolliert die ZIP-Struktur, erstellt eine Rollback-Sicherung und installiert nur eine neuere Version.

Online-Prüfungen verwenden standardmäßig `https://github.com/the-ab/RustDesk-AddressBook/releases/latest/download`. Das neueste veröffentlichte Release muss `latest.txt`, die darin genannte ZIP, `.zip.sha256` und `.zip.sig` bereitstellen. Mit `RAB_UPDATE_BASE_URL=disabled` werden Online-Prüfungen ausdrücklich abgeschaltet. Der private Release-Signaturschlüssel darf niemals in diesem Verzeichnis oder im Repository gespeichert werden.

Die englische Standardfassung befindet sich in [`README.md`](README.md).
