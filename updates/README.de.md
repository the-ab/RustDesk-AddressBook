# Signierte Updates

Kopiere ein Flat-Update-ZIP und beide passenden Prüfdateien in dieses Verzeichnis:

```bash
cp /pfad/rustdesk-addressbook-update-flat-v0531.zip updates/
cp /pfad/rustdesk-addressbook-update-flat-v0531.zip.sha256 updates/
cp /pfad/rustdesk-addressbook-update-flat-v0531.zip.sig updates/
./scripts/update.sh
```

Der Updater wählt das höchste lokale `rustdesk-addressbook-update-flat-v*.zip`, prüft das signierte SHA-256-Manifest mit dem eingebetteten öffentlichen Ed25519-Schlüssel, kontrolliert die ZIP-Struktur, erstellt eine Rollback-Sicherung und installiert nur eine neuere Version.

Online-Prüfungen sind optional und bei leerer `RAB_UPDATE_BASE_URL` deaktiviert. Eine konfigurierte Quelle muss `latest.txt`, das ZIP, `.zip.sha256` und `.zip.sig` bereitstellen. Der private Release-Signaturschlüssel darf niemals in diesem Verzeichnis oder im Repository gespeichert werden.

Die englische Standardfassung befindet sich in [`README.md`](README.md).
