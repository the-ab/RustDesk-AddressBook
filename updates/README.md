# Updates

Kopiere neue Flat-Update-ZIP-Dateien hier hinein, zum Beispiel:

```bash
cp rustdesk-addressbook-update-flat-v058.zip updates/
./scripts/update.sh
```

Das Updatescript sucht automatisch die höchste `rustdesk-addressbook-update-flat-v*.zip`, vergleicht sie mit der aktuell installierten Version und führt das Update nur aus, wenn die ZIP neuer ist.
