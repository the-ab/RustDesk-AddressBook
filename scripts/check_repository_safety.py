#!/usr/bin/env python3
"""Fail when repository policy files, bilingual docs, or likely secrets are invalid."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache"}
FORBIDDEN_EXACT = {".env", "docker-compose.override.yml", "install-config.env"}
FORBIDDEN_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".log", ".rabenc", ".rabfull", ".p12", ".pfx", ".key"}
PRIVATE_NAME = re.compile(r"(?:^|[-_.])private(?:[-_.]|$)", re.IGNORECASE)
PRIVATE_KEY_MARKER = re.compile(rb"-----BEGIN (?:OPENSSH |RSA |EC |DSA |ENCRYPTED )?PRIVATE KEY-----")

# Public information documents that must always exist as English/German pairs.
MANDATORY_DOCUMENT_PAIRS = (
    ("README.md", "README.de.md"),
    ("ADMIN-GUIDE.md", "ADMIN-GUIDE.de.md"),
    ("CONTRIBUTING.md", "CONTRIBUTING.de.md"),
    ("SECURITY.md", "SECURITY.de.md"),
    ("THIRD-PARTY-NOTICES.md", "THIRD-PARTY-NOTICES.de.md"),
    ("docs/README.md", "docs/README.de.md"),
    ("docs/releases/RELEASE_NOTES.md", "docs/releases/RELEASE_NOTES.de.md"),
    ("docs/security/SECURITY-REPORT.md", "docs/security/SECURITY-REPORT.de.md"),
    ("docker-compose/README.md", "docker-compose/README.de.md"),
)


def iter_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.is_file():
            files.append(path)
    return files


def check_document_pairs(problems: list[str]) -> None:
    for english_rel, german_rel in MANDATORY_DOCUMENT_PAIRS:
        english = ROOT / english_rel
        german = ROOT / german_rel
        if english.is_file() and german.is_file():
            continue
        if not english.is_file():
            problems.append(f"missing English information document: {english_rel}")
        if not german.is_file():
            problems.append(f"missing German information document: {german_rel}")


def main() -> int:
    problems: list[str] = []
    for path in iter_files():
        rel = path.relative_to(ROOT)
        rel_posix = rel.as_posix()
        name = path.name

        if name in FORBIDDEN_EXACT:
            problems.append(f"forbidden local configuration: {rel_posix}")
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            problems.append(f"forbidden runtime/secret file: {rel_posix}")
        if rel.parts and rel.parts[0] == "updates" and path.suffix.lower() in {".zip", ".sha256", ".sig"}:
            problems.append(f"downloaded release artifact must not be tracked: {rel_posix}")
        if PRIVATE_NAME.search(name) and name != "check_repository_safety.py":
            problems.append(f"private-key-like filename: {rel_posix}")

        try:
            if path.stat().st_size <= 2 * 1024 * 1024 and PRIVATE_KEY_MARKER.search(path.read_bytes()):
                problems.append(f"private key material detected: {rel_posix}")
        except OSError as exc:
            problems.append(f"could not inspect {rel_posix}: {exc}")

    public_key = ROOT / "scripts" / "keys" / "update-signing-public-v1.pem"
    if not public_key.is_file():
        problems.append("public update verification key is missing")

    check_document_pairs(problems)

    if problems:
        print("Repository safety check failed:", file=sys.stderr)
        for problem in sorted(set(problems)):
            print(f"- {problem}", file=sys.stderr)
        return 1

    print("Repository safety check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
