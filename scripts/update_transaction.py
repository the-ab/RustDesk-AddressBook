#!/usr/bin/env python3
"""Snapshot and roll back a stopped ZIP installation, including custom mounts."""

from __future__ import annotations

import json
import shutil
import sys
import zipfile
from pathlib import Path

DIRECTORIES = {"app", "static", "templates", "scripts", "docs", "docker-compose", "tests", "contrib"}
LOCAL_FILES = {".env", "install-config.env", "docker-compose.override.yml"}


def managed(path: Path) -> bool:
    if path.as_posix() in {"updates", "updates/.gitkeep", "updates/README.md", "updates/README.de.md", "sample-import.csv"}:
        return True
    return (
        path.parts[0] in DIRECTORIES
        or (len(path.parts) == 1 and (path.suffix in {".md", ".txt", ".py", ".sh", ".yml", ".toml"} or path.name in {"Dockerfile", "VERSION", "LICENSE", "NOTICE", ".env.example", ".dockerignore", ".gitignore"}))
    ) and "__pycache__" not in path.parts


def snapshot(root: Path, backup: Path, package: Path, data: Path, backups: Path) -> None:
    targets = {p.relative_to(root) for p in root.iterdir() if p.is_file() and managed(p.relative_to(root))}
    for name in DIRECTORIES:
        targets.update(p.relative_to(root) for p in (root / name).rglob("*") if p.is_file() and managed(p.relative_to(root)))
    targets.update(Path(name) for name in LOCAL_FILES)
    with zipfile.ZipFile(package) as archive:
        for info in archive.infolist():
            relative = Path(info.filename)
            if relative.is_absolute() or ".." in relative.parts or not managed(relative):
                raise ValueError(f"Nicht erlaubter Update-Pfad: {relative}")
            if not info.is_dir():
                targets.add(relative)
    records = []
    for relative in sorted(targets):
        source = root / relative
        if source.is_symlink() or any(part.is_symlink() for part in source.parents if part != root.parent):
            raise ValueError(f"Update-Ziel darf kein symbolischer Link sein: {relative}")
        if source.exists():
            destination = backup / "source" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        records.append({"path": str(relative), "exists": source.exists()})
    persist = []
    for label, path in (("data", data), ("backups", backups)):
        resolved = path.resolve()
        if resolved == root or resolved in root.parents:
            raise ValueError(f"Ungeeigneter persistenter Pfad: {resolved}")
        if resolved == backup or resolved in backup.parents or any(resolved == root / name or root / name in resolved.parents for name in DIRECTORIES):
            raise ValueError(f"Persistenter Pfad überlappt Quellcode oder Sicherungsziel: {resolved}")
        exists = path.exists()
        if exists:
            shutil.copytree(path, backup / label, symlinks=True)
        persist.append({"label": label, "path": str(resolved), "exists": exists})
    (backup / "transaction.json").write_text(json.dumps({"root": str(root), "files": records, "persist": persist}, indent=2), encoding="utf-8")


def rollback(backup: Path) -> None:
    state = json.loads((backup / "transaction.json").read_text(encoding="utf-8"))
    root = Path(state["root"])
    for record in state["files"]:
        relative = Path(record["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Ungültiger Pfad im Update-Rückweg.")
        destination = root / relative
        if record["exists"]:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup / "source" / relative, destination)
        else:
            destination.unlink(missing_ok=True)
    for record in state["persist"]:
        destination = Path(record["path"])
        if destination.exists():
            shutil.rmtree(destination)
        if record["exists"]:
            shutil.copytree(backup / record["label"], destination, symlinks=True)


if __name__ == "__main__":
    if sys.argv[1] == "snapshot":
        snapshot(*(Path(value).resolve() for value in sys.argv[2:]))
    elif sys.argv[1] == "rollback":
        rollback(Path(sys.argv[2]).resolve())
    else:
        raise SystemExit("Unbekannte Transaktionsoperation.")
