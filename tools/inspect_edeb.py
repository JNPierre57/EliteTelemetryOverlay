"""Inventory original bytes; inspect SQLite only on private temporary copies.

No database engine ever opens the source. A stable raw copy is a discovery aid,
not proof of transaction consistency. WAL/journal companions are included.
"""
import argparse
from contextlib import closing
import hashlib
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path
import time


def signature(path):
    with path.open('rb') as stream:
        header = stream.read(64)
    if header.startswith(b'SQLite format 3\0'):
        return 'SQLite 3'
    return 'unknown (requires format-specific investigation)'


def stamp(path):
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns


def inspect_sqlite(path, include_samples=False):
    companions = [Path(str(path) + suffix) for suffix in ('', '-wal', '-shm', '-journal')]
    with tempfile.TemporaryDirectory(prefix='eto-inspect-') as directory:
        before = {str(p): stamp(p) for p in companions if p.exists()}
        if sum(size for size, _ in before.values()) > 512 * 1024 * 1024:
            raise ValueError('snapshot exceeds 512 MiB limit; arrange offline investigation')
        for p in companions:
            if str(p) in before:
                shutil.copyfile(p, Path(directory) / p.name)
        after = {str(p): stamp(p) for p in companions if p.exists()}
        if before != after:
            raise ValueError('files changed during copy; retry later; no consistent snapshot claimed')
        copy = Path(directory) / path.name
        # Recovery/sidecar writes, if necessary, occur ONLY inside the temporary directory.
        with closing(sqlite3.connect(copy, timeout=.2)) as connection:
            deadline = time.monotonic() + 3
            connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
            connection.execute('PRAGMA query_only=ON')
            schema = connection.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name").fetchall()
            result = {'schema': schema, 'schema_sha256': hashlib.sha256(json.dumps(schema).encode()).hexdigest(), 'user_version': connection.execute('PRAGMA user_version').fetchone()[0], 'snapshot_note': 'raw copy stable by size/mtime; not a guaranteed application-consistent snapshot'}
            if include_samples:
                samples = {}
                for kind, name, _, _ in schema:
                    if kind == 'table':
                        escaped = name.replace('"', '""')
                        cursor = connection.execute(f'SELECT * FROM "{escaped}" LIMIT 3')
                        samples[name] = {'columns': [item[0] for item in cursor.description], 'rows': [[v if isinstance(v, (int, float, type(None))) else str(v)[:200] for v in row] for row in cursor.fetchall()]}
                result['samples_PRIVATE'] = samples
            return result


def inspect(root, samples=False):
    result = {'format_version': 1, 'source': '%LOCALAPPDATA%/Elite Dangerous Exploration Buddy', 'files': [], 'conclusion': 'Trip boundaries and total semantics NOT verified by this report.'}
    for path in sorted(root.rglob('*')):
        if path.is_symlink() or not path.is_file():
            continue
        entry = {'file': str(path.relative_to(root))}
        try:
            entry['size'] = path.stat().st_size
            entry['format'] = signature(path)
            if entry['format'] == 'SQLite 3':
                entry['inspection'] = inspect_sqlite(path, samples)
        except (OSError, sqlite3.Error, ValueError) as error:
            entry['error'] = f'{type(error).__name__}: {error}'
        result['files'].append(entry)
        if len(result['files']) >= 2000:
            result['truncated'] = True
            break
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--include-samples', action='store_true')
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    if not root.is_dir():
        parser.error('EDEB data directory does not exist')
    if output.is_relative_to(root):
        parser.error('report must be outside the EDEB directory')
    report = inspect(root, args.include_samples)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Report: {output}. Inspect locally before sharing; never commit it.')


if __name__ == '__main__':
    main()
