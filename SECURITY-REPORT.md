# Security Report

Version: `0.5.6-installer-update-scripts`

## Änderungen

- Installationsscript erzeugt `.env` und `docker-compose.override.yml`.
- HTTPS ist standardmäßig aktiv, HTTP standardmäßig deaktiviert.
- Daten- und Backup-Verzeichnisse können außerhalb des Projektordners liegen.
- Optionaler RustDesk-DB-Mount ist read-only und wird nur auf Wunsch eingerichtet.
- Updatescript erstellt vor dem Austausch eine Sicherung von Daten, Backups und Compose-Konfiguration.

# RustDesk AddressBook 0.5.1 Security Test Report

Durchgeführte Prüfungen in dieser Build-Umgebung:

- Python-Syntaxprüfung aller App-Dateien mit `py_compile`: OK
- Jinja2-Template-Syntaxprüfung aller HTML-Templates: OK
- statische Suche nach offensichtlichen gefährlichen Python-Mustern wie `eval`, `exec`, `pickle.loads`, `os.system`, `shell=True`: OK, keine Treffer
- Prüfung der Flask-Routen auf fehlendes `login_required`: OK; öffentlich bleiben nur Setup, Login und 2FA-Login
- Prüfung der POST-Templates auf CSRF-Token: OK
- Sicherheitsheader vorhanden: X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, Content-Security-Policy, optional HSTS
- Login-Auditlog und fail2ban-taugliche Logausgabe ergänzt
- interne Brute-Force-Sperre ergänzt
- HMAC-Manipulationsschutz für Benutzer-Sicherheitsfelder ergänzt

Nicht vollständig in dieser Umgebung geprüft:

- vollständiger Docker-Build mit Paketdownload
- dynamischer Browser-Test gegen einen laufenden Container
- externer Pentest mit Tools wie OWASP ZAP oder Burp Suite
- echte SQLCipher-Datenbankverschlüsselung, da der aktuelle Stack Standard-SQLite verwendet

Rest-Risiken:

- Hat ein Angreifer Schreib-/Leserechte auf `data/config.json` und `addressbook.db`, ist die Installation kompromittiert.
- CDN-basierte Bootstrap/Icons-Ressourcen benötigen ausgehenden Browserzugriff. Für eine komplett offline/härtere CSP müssten Bootstrap und Icons lokal vendored werden.
- Die hbbs-Live-Abfrage ist keine offiziell dokumentierte Web-API und kann sich mit RustDesk-Versionen ändern.


## Nachtest 0.5.2

Korrigiert wurde ein Lockout-Fehler aus 0.5.1:

- GET `/login` verursacht keinen Auth-Fehlversuch.
- Signaturfehler werden als Security-Events protokolliert, zählen aber nicht in die Login-Rate-Limit-Sperre.
- Ungültige Benutzer-HMAC kann im Standardmodus nach vollständiger erfolgreicher Authentifizierung neu versiegelt werden.
- Für Produktionsbetrieb mit maximaler Härtung kann `USER_SIGNATURE_POLICY=strict` gesetzt werden.
