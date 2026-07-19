from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.error
import urllib.request


def _enabled(name: str, default: str) -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _port(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} ist kein gültiger Port") from exc
    if not 1 <= value <= 65535:
        raise ValueError(f"{name} liegt außerhalb des gültigen Portbereichs")
    return value


def _probe(url: str) -> tuple[bool, str]:
    # Ausschließlich für den internen Loopback-Healthcheck. Das lokale Zertifikat
    # darf selbstsigniert sein; Zielhost und Schema werden nicht von Benutzerdaten übernommen.
    context = ssl._create_unverified_context() if url.startswith("https://") else None  # nosec B323
    request = urllib.request.Request(url, headers={"User-Agent": "rustdesk-addressbook-healthcheck"})
    try:
        with urllib.request.urlopen(request, timeout=4, context=context) as response:  # nosec B310
            payload = json.loads(response.read(4096).decode("utf-8"))
            if response.status == 200 and payload.get("status") == "ok":
                return True, "ok"
            return False, f"HTTP {response.status}: {payload!r}"
    except (OSError, ValueError, urllib.error.URLError) as exc:
        return False, str(exc)


def main() -> int:
    urls: list[str] = []
    if _enabled("APP_ENABLE_HTTPS", "true"):
        urls.append(f"https://127.0.0.1:{_port('APP_HTTPS_PORT', 5443)}/healthz")
    if _enabled("APP_ENABLE_HTTP", "false"):
        urls.append(f"http://127.0.0.1:{_port('APP_HTTP_PORT', 5000)}/healthz")

    if not urls:
        print("Kein HTTP- oder HTTPS-Listener für den Healthcheck aktiviert.", file=sys.stderr)
        return 1

    errors: list[str] = []
    for url in urls:
        ok, detail = _probe(url)
        if ok:
            return 0
        errors.append(f"{url}: {detail}")

    print("; ".join(errors), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
