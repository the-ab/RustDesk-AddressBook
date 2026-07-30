# Community-Adressbuch für RustDesk 0.6.0 – GHCR-Image-Installation und Setup-Token-Bereinigung

Release-Datum: 2026-07-30

- Datei `VERSION` mit dem Wert `0.6.0` im Projektstamm ergänzt.
- `docker-compose/compose.yaml` und `docker-compose/.env.example` für die Installation über `ghcr.io/the-ab/rustdesk-addressbook:latest` oder den festen Image-Tag `0.6.0` ohne Projektquellcode ergänzt.
- README, Administratorhandbuch und WebUI-Anleitung um die GHCR-Image-Installation erweitert.
- Bestehende Installation mit lokalem Build und der signierte ZIP-Updateweg bleiben unverändert nutzbar.
- Einmaliges `SETUP_TOKEN` wird nach erfolgreicher Erstellung des ersten Administratorkontos aus `data/config.json` entfernt.
- Bestehende Installationen mit Administrator entfernen das bisher gespeicherte Setup-Token beim Anwendungsstart automatisch.
