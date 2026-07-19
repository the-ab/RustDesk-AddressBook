# Updates

> Dies ist die deutsche Fassung. Die englische Standardfassung steht in [`README.md`](README.md).

Kopiere neue Flat-Update-ZIP-Dateien hier hinein, zum Beispiel:

```bash
cp rustdesk-addressbook-update-flat-v0529.zip updates/
./scripts/update.sh
```

Das Updatescript sucht automatisch die höchste `rustdesk-addressbook-update-flat-v*.zip`, vergleicht sie mit der aktuell installierten Version, prüft Ed25519-Signatur und signierte SHA-256-Prüfsumme und führt das Update nur aus, wenn die ZIP neuer ist.
