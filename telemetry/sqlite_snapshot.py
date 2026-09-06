"""Bounded byte-only access to EDEB; SQLite opens only disposable local copies."""
from contextlib import contextmanager
import hashlib
from pathlib import Path
import tempfile
import time


class SnapshotError(RuntimeError):
    pass


def file_state(paths):
    result = {}
    for path in paths:
        try:
            stat = path.stat()
            result[path.name] = (stat.st_size, stat.st_mtime_ns)
        except FileNotFoundError:
            pass
    return result


def stream_hash(path, deadline, destination=None):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        while True:
            if time.monotonic() > deadline:
                raise SnapshotError('EDEB snapshot timed out; retrying later')
            block = source.read(1024 * 1024)
            if not block:
                return digest.digest()
            digest.update(block)
            if destination is not None:
                destination.write(block)


@contextmanager
def stable_snapshot(database):
    """Double-checked raw copy, not an application-level atomic snapshot.

    Do not open source using SQLite: even mode=ro can create/update WAL SHM files.
    Rebuild SHM only inside the temporary directory from the copied WAL instead.
    """
    database = Path(database).resolve()
    wal = Path(str(database) + '-wal')
    journal = Path(str(database) + '-journal')
    paths = [database, wal, journal]
    deadline = time.monotonic() + 2
    before = file_state(paths)
    if database.name not in before:
        raise SnapshotError('EDEB.db not found; check EDEB and edeb_db_path')
    if before.get(journal.name, (0,))[0]:
        raise SnapshotError('EDEB rollback journal present; wait for EDEB to finish its transaction')
    if sum(size for size, _ in before.values()) > 512 * 1024 * 1024:
        raise SnapshotError('EDEB snapshot exceeds 512 MiB safety limit')
    with tempfile.TemporaryDirectory(prefix='eto-read-') as directory:
        hashes = {}
        for path in (database, wal):
            if path.name in before:
                with (Path(directory) / path.name).open('wb') as output:
                    hashes[path.name] = stream_hash(path, deadline, output)
        if file_state(paths) != before:
            raise SnapshotError('EDEB changed during snapshot; retrying later')
        for path in (database, wal):
            if path.name in hashes and stream_hash(path, deadline) != hashes[path.name]:
                raise SnapshotError('EDEB bytes changed during snapshot; retrying later')
        if file_state(paths) != before:
            raise SnapshotError('EDEB changed during snapshot verification; retrying later')
        yield Path(directory) / database.name
