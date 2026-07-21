# Security Policy

German edition: [`SECURITY.de.md`](SECURITY.de.md)

## Supported versions

Only the latest published release is supported with security fixes. Older release archives are provided for historical reference and should not be exposed to untrusted networks.

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability.

1. Use the repository's **Security** tab and create a private security advisory.
2. Include the affected version, reproduction steps, expected impact, and any relevant logs with secrets removed.
3. Do not include production databases, passwords, private keys, session cookies, OIDC tokens, or full backup archives.

The maintainer will confirm receipt, assess severity, coordinate a fix, and publish release notes after affected users have had a reasonable opportunity to update. No fixed response-time guarantee is provided.

## Security expectations

- Run the application only over HTTPS.
- Keep at least one protected local administrator account even when OIDC is enabled.
- Store `data/config.json`, database backups, and the private release-signing key separately and securely.
- Never commit `.env`, databases, logs, backups, TLS private keys, or release-signing private keys.
- Signed update packages are verified using `scripts/keys/update-signing-public-v1.pem`.
- The default signed update source is `https://github.com/the-ab/RustDesk-AddressBook/releases/latest/download`. If you configure another source, it must be controlled and trusted. Set `RAB_UPDATE_BASE_URL=disabled` to disable online checks explicitly; local signed updates remain available.

## Scope

The policy covers the application code and release artifacts in this repository. Vulnerabilities in RustDesk itself, an OIDC provider, the host operating system, Docker, reverse proxies, or third-party infrastructure should also be reported to the respective upstream project.
