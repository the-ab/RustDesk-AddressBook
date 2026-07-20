# Community Address Book for RustDesk 0.5.30 – GitHub publication readiness

German edition: [`RELEASE_NOTES.de.md`](RELEASE_NOTES.de.md)

## Added

- Apache License 2.0 and a project `NOTICE` file.
- `.gitignore` protection for local configuration, databases, logs, backups, downloaded update assets, TLS private keys, and private release-signing keys.
- `SECURITY.md` and `CONTRIBUTING.md`, each with a German `*.de.md` edition.
- GitHub Actions CI for repository policy, Python/JavaScript/Shell checks, Ruff, Bandit, pytest, dependency auditing, and Docker build validation.
- Dependabot configuration for Python, Docker, and GitHub Actions.
- Initial automated tests for setup-token protection, role/group visibility, administrative access denial, health checks, restore link rejection, CSV formula protection, and disabled online-update behavior.
- Repository safety scanner at `scripts/check_repository_safety.py`.

## Changed

- The project is presented as an independent community project and includes an explicit RustDesk/Purslane affiliation and trademark disclaimer.
- Added a transparent OpenAI ChatGPT assistance disclosure with maintainer responsibility.
- `RAB_UPDATE_BASE_URL` is empty by default. Online update checks are disabled until a trusted source is configured; local signed updates continue to work.
- Existing installations preserve their current `.env` update URL during upgrades.
- Documentation examples no longer require the previous maintainer-operated download service and instead describe repository Releases or a self-controlled signed mirror.

## Compatibility

No database schema or device/user behavior was changed. Existing installations can update normally and retain their local configuration.
