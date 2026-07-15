# RustDesk AddressBook Security Report

Version: `0.5.26-user-preferences-import-blocklist`

## Sicherheitsrelevante Architektur

- Rollenmodell mit `admin` und `user`; Verwaltungs- und Schreibaktionen werden serverseitig durch geschützte Flask-Routen begrenzt.
- Normale Benutzer sehen ausschließlich Geräte aus zugewiesenen Gruppen. Geräte ohne Gruppe werden nur Administratoren bereitgestellt; nicht sichtbare Geräte liefern auch über direkte URLs keine Daten.
- Der aktuelle Administrator und der letzte aktive lokale Administrator sind gegen versehentliches Löschen, Deaktivieren, Herabstufen oder Provider-Wechsel geschützt.
- Lokale Konten unterstützen Passwort, TOTP und einmalige gehashte Recovery-Codes.
- OIDC verwendet Discovery sowie Authorization Code mit PKCE, `state`/`nonce` über Authlib und eine eindeutige Kontobindung über Issuer plus `sub`.
- Das OIDC-Client-Secret wird mit Fernet verschlüsselt in der Datenbank gespeichert. Gerätepasswörter werden ebenfalls feldweise verschlüsselt.
- Sicherheitsrelevante Benutzerfelder werden HMAC-signiert; Bestandskonten werden beim Schema-Upgrade neu versiegelt.
- OIDC-Auto-Provisioning legt ausschließlich normale Benutzer ohne Gruppenzugriff an. Eine optionale Domain-Positivliste kann die automatische Anlage begrenzen.
- Unsichere HTTP-Issuer sind standardmäßig abgewiesen und müssen ausdrücklich für isolierte Testumgebungen aktiviert werden.
- CSRF-Schutz, sichere Redirect-Prüfung, Security Header, Login-Auditlog, interne Brute-Force-Sperre und fail2ban/CrowdSec-kompatibles `auth.log` bleiben aktiv.

## Durchgeführte Build-Prüfungen

- Python-Kompilierung und statische Prüfung aller App- und Scriptdateien
- Jinja2-Syntaxprüfung aller HTML-Templates
- JavaScript-Syntaxprüfung
- Shell-Syntaxprüfung der Installations-, Update- und Entrypoint-Scripte
- Migrationstest von einer Datenbank im 0.5.24-Schema
- Funktionsprüfung für Admin- und Benutzerrollen, Gruppensichtbarkeit, ungruppierte Geräte und geschützte Verwaltungsrouten
- Prüfung von lokalem Benutzeranlegen, Deaktivierung und Schutz des letzten lokalen Administrators
- OIDC-Konfigurationsprüfung inklusive verschlüsselter Speicherung des Client-Secrets
- simulierte OIDC-Callback-Prüfung mit automatischer Anlage eines normalen Benutzers ohne Gruppen
- SQLite-Integritätsprüfung und ZIP-Strukturprüfung

## Betriebsanforderungen

- Produktiv ausschließlich HTTPS verwenden.
- `TRUST_PROXY_HEADERS=true` nur hinter einem vertrauenswürdigen Reverse Proxy setzen, der die Anwendung exklusiv erreicht.
- Mindestens einen starken lokalen Administrator mit TOTP als Notfallzugang behalten.
- Beim OIDC-Provider MFA erzwingen; die Anwendung kann den externen MFA-Status nicht selbst verifizieren.
- Gruppen nach dem Minimalprinzip zuweisen und automatisch angelegte OIDC-Benutzer vor Freigabe prüfen.
- Backups mit `addressbook.db` und `data/config.json` nur verschlüsselt und getrennt geschützt speichern.

## Rest-Risiken

- Die SQLite-Datenbank ist nicht vollständig mit SQLCipher verschlüsselt. Wer `addressbook.db` und `data/config.json` gemeinsam erlangt, kann verschlüsselte Felder entschlüsseln und gilt als vollständiger Kompromiss.
- Ein echter End-to-End-Test gegen jeden möglichen OIDC-Provider ist nicht möglich; Claim-Namen, Logout-Verhalten und Provider-Richtlinien können variieren.
- CDN-basierte Bootstrap-/Icon-Ressourcen benötigen Browserzugriff nach außen. Für eine vollständig offline betriebene oder strengere CSP-Variante müssten diese Dateien lokal eingebunden werden.
- Die hbbs-Live-Abfrage nutzt keine offiziell dokumentierte Web-API und kann sich nach RustDesk-Serverupdates ändern.
- Ein externer Penetrationstest mit OWASP ZAP/Burp Suite wurde in dieser Build-Umgebung nicht durchgeführt.
