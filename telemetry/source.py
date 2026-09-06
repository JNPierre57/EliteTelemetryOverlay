"""Read EDEB's stored current-trip values without opening originals in SQLite."""
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time
from .common import credits
from .sqlite_snapshot import SnapshotError, stable_snapshot

# Observed in the user's Shadow report. Unknown schema/version combinations fail closed.
SUPPORTED_SCHEMAS = {
    279: 'baab7ca412995e8f91c36f2baa8b51b50206e1ff8368335758ad0cc450e4fdf5',
}


class SourceError(RuntimeError):
    """No usable reading; retain receiver state and retry without posting zero."""


def default_database():
    local = os.environ.get('LOCALAPPDATA')
    if not local:
        raise SourceError('LOCALAPPDATA unavailable; run on Shadow or set edeb_db_path')
    return Path(local) / 'Elite Dangerous Exploration Buddy' / 'db' / 'EDEB.db'


def validate_schema(connection):
    version = connection.execute('PRAGMA user_version').fetchone()[0]
    schema = connection.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name").fetchall()
    fingerprint = hashlib.sha256(json.dumps(schema).encode()).hexdigest()
    if SUPPORTED_SCHEMAS.get(version) != fingerprint:
        raise SourceError(f'EDEB schema incompatible (user_version {version}); run tools/inspect-edeb.ps1 after any update')


def stored_totals(connection):
    validate_schema(connection)
    if connection.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
        raise SourceError('EDEB snapshot integrity check failed')
    invalid_flags = connection.execute("SELECT COUNT(*) FROM StarSystem WHERE typeof(IsTripHistory) != 'integer' OR IsTripHistory NOT IN (0,1)").fetchone()[0]
    if invalid_flags:
        raise SourceError('Unexpected EDEB trip flags; no value sent')
    values = {}
    for table, field, flag in [('Body', 'CartographicValue', 'WasReadFromJournal'),
                               ('Genus', 'VistaGenomicsValue', 'AnalysisComplete')]:
        # No Body-to-Genus join: multiple genera must not multiply body values.
        invalid, ambiguous, total = connection.execute(f'''
            SELECT
                COALESCE(SUM(CASE WHEN typeof(t."{field}") != 'integer'
                    OR t."{field}" < 0 THEN 1 ELSE 0 END),0),
                COALESCE(SUM(CASE WHEN COALESCE(t."{flag}",0) != 1
                    AND t."{field}" != 0 THEN 1 ELSE 0 END),0),
                COALESCE(SUM(t."{field}"),0)
            FROM "{table}" t WHERE EXISTS (
                SELECT 1 FROM StarSystem s
                WHERE s.Id = t.StarSystemId AND s.IsTripHistory = 1)
        ''').fetchone()
        orphan = connection.execute(f'''SELECT COUNT(*) FROM "{table}" t
            WHERE NOT EXISTS (SELECT 1 FROM StarSystem s WHERE s.Id=t.StarSystemId)''').fetchone()[0]
        if invalid or orphan:
            raise SourceError(f'EDEB {table} contains NULL/invalid values or orphan rows; inspect the database')
        if ambiguous:
            raise SourceError(f'EDEB {table} filters no longer agree; run the value comparison diagnostic')
        values[table] = credits(total)
    return {'value': credits(values['Body'] + values['Genus']),
            'cartography': values['Body'], 'biology': values['Genus']}


def read_totals(database=None):
    try:
        path = Path(os.path.expandvars(str(database))).expanduser() if database else default_database()
        with stable_snapshot(path) as copy:
            with closing(sqlite3.connect(copy, timeout=.2)) as connection:
                connection.execute('PRAGMA query_only=ON')
                deadline = time.monotonic() + 2
                connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
                return stored_totals(connection)
    except (OSError, sqlite3.Error, SnapshotError, ValueError) as error:
        raise SourceError(f'EDEB read unavailable: {error}') from None


def read_current_trip(database=None):
    return read_totals(database)['value']


def main():
    parser = argparse.ArgumentParser(description='Read current EDEB trip once; no network, token or config required.')
    parser.add_argument('--database', type=Path, help='override the standard Windows EDEB.db path')
    args = parser.parse_args()
    try:
        result = read_totals(args.database)
    except SourceError as error:
        parser.exit(2, f'[EDEB] {error}\n')
    print(f"[EDEB] Current trip value: {result['value']:,} Cr")
    print(f"[EDEB] Cartography: {result['cartography']:,} Cr; Biology: {result['biology']:,} Cr")


if __name__ == '__main__':
    main()
