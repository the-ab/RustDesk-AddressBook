"""Process-wide maintenance locking and recoverable file replacement on Linux."""

from __future__ import annotations

import fcntl
import json
import os
import shutil
from contextlib import contextmanager
from pathlib import Path


def _sync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_write(path: Path, data: bytes, mode: int = 0o600) -> None:
    import tempfile

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as output:
            os.fchmod(output.fileno(), mode)
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        _sync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def write_new_file(path: Path, data: bytes, mode: int = 0o600) -> None:
    """Publish atomically without replacing an existing backup."""
    import tempfile

    fd, name = tempfile.mkstemp(prefix=".backup-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as output:
            os.fchmod(output.fileno(), mode)
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.link(temporary, path)
        _sync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def maintenance_lock(data_dir: Path, *, exclusive: bool = False, blocking: bool = True):
    data_dir.mkdir(parents=True, exist_ok=True)
    with (data_dir / ".restore.lock").open("a+b") as handle:
        operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        fcntl.flock(handle, operation | (0 if blocking else fcntl.LOCK_NB))
        try:
            yield handle
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def recover_pending_restore(data_dir: Path) -> bool:
    """Called under the exclusive lock, before opening config or the database.

    A prepared journal is rolled back even after SIGKILL. Until rollback
    completes it stays on disk, so live workers refuse further requests.
    """
    journal = data_dir / ".restore-transaction"
    manifest = journal / "manifest.json"
    if not manifest.exists():
        if journal.exists():
            shutil.rmtree(journal)
        return False
    records = json.loads(manifest.read_text(encoding="utf-8"))
    for record in records:
        relative = Path(record["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Ungültiges Restore-Journal; manueller Rückweg erforderlich.")
        destination = data_dir / relative
        if record["exists"]:
            atomic_write(destination, (journal / "old" / relative).read_bytes(), record["mode"])
        else:
            destination.unlink(missing_ok=True)
            if destination.parent.exists():
                _sync_directory(destination.parent)
    # Old workers must also discard pooled SQLite connections after a rollback.
    atomic_write(data_dir / ".restore-generation", os.urandom(16))
    manifest.unlink()
    _sync_directory(journal)
    shutil.rmtree(journal)
    _sync_directory(data_dir)
    return True


def replace_files(data_dir: Path, files: dict[str, tuple[bytes, int]], *, database_snapshot: bytes) -> None:
    """Replace a validated generation; preserve every touched file for rollback."""
    journal = data_dir / ".restore-transaction"
    if journal.exists():
        raise ValueError("Ein früherer Restore muss vor weiteren Änderungen wiederhergestellt werden.")
    journal.mkdir(mode=0o700)
    prepared = False
    try:
        records = []
        # Never let old WAL frames contaminate the newly installed database.
        for relative in [*files, "addressbook.db-wal", "addressbook.db-shm"]:
            destination = data_dir / relative
            if destination.is_symlink() or any(parent.is_symlink() for parent in destination.parents if parent != data_dir.parent):
                raise ValueError(f"Restore-Ziel darf kein symbolischer Link sein: {relative}")
            exists = destination.exists()
            mode = destination.stat().st_mode & 0o777 if exists else 0o600
            # The consistent snapshot includes WAL. Sidecars are removed on rollback.
            saved_exists = exists and not relative.endswith(("-wal", "-shm"))
            records.append({"path": relative, "exists": saved_exists, "mode": mode})
            if saved_exists:
                content = database_snapshot if relative == "addressbook.db" else destination.read_bytes()
                atomic_write(journal / "old" / relative, content, mode)
        atomic_write(journal / "manifest.json", json.dumps(records).encode("utf-8"))
        prepared = True
        for suffix in ("-wal", "-shm"):
            (data_dir / f"addressbook.db{suffix}").unlink(missing_ok=True)
        for relative, (content, mode) in files.items():
            atomic_write(data_dir / relative, content, mode)
        atomic_write(data_dir / ".restore-generation", os.urandom(16))
        # Removing the manifest is the commit point after every file is durable.
        (journal / "manifest.json").unlink()
        _sync_directory(journal)
        prepared = False
    except Exception:
        if prepared:
            recover_pending_restore(data_dir)
        raise
    finally:
        # On SIGKILL the manifest and originals survive for startup recovery.
        if not prepared and journal.exists():
            shutil.rmtree(journal)


class MaintenanceMiddleware:
    """Keep a shared lock until the WSGI response has finished streaming."""

    def __init__(self, application, data_dir: Path, refresh):
        self.application = application
        self.data_dir = data_dir
        self.refresh = refresh

    def __call__(self, environ, start_response):
        def response():
            with maintenance_lock(self.data_dir) as handle:
                if (self.data_dir / ".restore-transaction" / "manifest.json").exists():
                    start_response("503 Service Unavailable", [("Content-Type", "text/plain; charset=utf-8"), ("Retry-After", "5")])
                    yield b"Restore unterbrochen. Anwendung zur Wiederherstellung neu starten."
                    return
                self.refresh()
                environ["rab.maintenance_lock"] = handle
                result = self.application(environ, start_response)
                try:
                    yield from result
                finally:
                    if hasattr(result, "close"):
                        result.close()
        return response()
