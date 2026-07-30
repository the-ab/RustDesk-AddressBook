# Community Address Book for RustDesk 0.6.0 – GHCR image installation and setup-token cleanup

Release date: 2026-07-30

- Added the root-level `VERSION` file with value `0.6.0`.
- Added `docker-compose/compose.yaml` and `docker-compose/.env.example` for installation from `ghcr.io/the-ab/rustdesk-addressbook:latest` or the fixed `0.6.0` image tag without project source files.
- Updated README, Admin Guide and Web UI help with the GHCR image installation path.
- Kept the existing source-build installation and signed ZIP update path unchanged.
- Removed the one-time `SETUP_TOKEN` from `data/config.json` after the first administrator account is created successfully.
- Existing installations with an administrator automatically remove the legacy setup token on application startup.
