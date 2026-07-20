# Sicherheitsrichtlinie

Englische Standardfassung: [`SECURITY.md`](SECURITY.md)

## Unterstützte Versionen

Nur die jeweils neueste veröffentlichte Version erhält Sicherheitskorrekturen. Ältere Archive dienen ausschließlich der historischen Nachvollziehbarkeit und sollten nicht in nicht vertrauenswürdigen Netzen betrieben werden.

## Schwachstellen melden

Bitte vermutete Schwachstellen nicht als öffentliches Issue veröffentlichen.

1. Im Repository unter **Security** eine private Security Advisory erstellen.
2. Betroffene Version, reproduzierbare Schritte, erwartete Auswirkungen und relevante, von Geheimnissen bereinigte Logs angeben.
3. Keine produktiven Datenbanken, Passwörter, privaten Schlüssel, Sitzungscookies, OIDC-Tokens oder vollständigen Backup-Archive übermitteln.

Der Maintainer bestätigt den Eingang, bewertet die Schwere, koordiniert eine Korrektur und veröffentlicht Release-Informationen, nachdem betroffene Nutzer eine angemessene Aktualisierungsmöglichkeit hatten. Eine feste Reaktionszeit wird nicht garantiert.

## Sicherheitserwartungen

- Anwendung ausschließlich über HTTPS betreiben.
- Auch bei aktiviertem OIDC mindestens ein geschütztes lokales Administratorkonto behalten.
- `data/config.json`, Datenbanksicherungen und den privaten Release-Signaturschlüssel getrennt und sicher verwahren.
- `.env`, Datenbanken, Logs, Backups, private TLS-Schlüssel und private Release-Schlüssel niemals committen.
- Signierte Updatepakete werden über `scripts/keys/update-signing-public-v1.pem` geprüft.
- `RAB_UPDATE_BASE_URL` nur auf eine selbst kontrollierte und vertrauenswürdige Release-Quelle setzen. Ein leerer Wert deaktiviert Online-Prüfungen; lokale signierte Updates bleiben möglich.

## Geltungsbereich

Diese Richtlinie umfasst Anwendungscode und Release-Artefakte dieses Repositorys. Schwachstellen in RustDesk selbst, einem OIDC-Provider, dem Hostsystem, Docker, Reverse Proxies oder weiterer Drittinfrastruktur sollten zusätzlich beim jeweiligen Upstream-Projekt gemeldet werden.
