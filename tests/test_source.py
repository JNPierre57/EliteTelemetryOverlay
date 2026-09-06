from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from telemetry.source import SourceError, read_current_trip, read_totals
from telemetry.sqlite_snapshot import stable_snapshot, SnapshotError, file_state
from telemetry.sender import Sender, main as sender_main

SCHEMA = json.loads((Path(__file__).parent / 'fixtures/edeb-schema-279.json').read_text())


def seed(database, wal=False):
    connection = sqlite3.connect(database)
    if wal:
        connection.execute('PRAGMA journal_mode=WAL')
    for _, _, _, sql in SCHEMA['schema']:
        connection.execute(sql)
    connection.execute('PRAGMA user_version=279')
    connection.executemany('INSERT INTO StarSystem(Id,Name,StarClass,IsTripHistory) VALUES (?,?,?,?)',
                           [(1, 'Synthetic current', 'G', 1), (2, 'Synthetic history', 'G', 0)])
    connection.executemany('''INSERT INTO Body
        (Id,StarSystemId,Name,Type,Distance,RingsReserveLevel,CartographicValue,WasReadFromJournal)
        VALUES (?,?,?,0,0,0,?,1)''', [(1, 1, 'Synthetic A', 100), (2, 1, 'Synthetic B', 200), (1, 2, 'Synthetic C', 5000)])
    connection.executemany('''INSERT INTO Genus
        (Name,BodyId,StarSystemId,VistaGenomicsValue,AnalysisComplete) VALUES (?,?,?,?,?)''',
        [('Synthetic A', 1, 1, 700, 1), ('Synthetic B', 1, 1, 900, 1),
         ('Synthetic incomplete', 2, 1, 0, 0), ('Synthetic historical', 1, 2, 99999, 1)])
    connection.commit()
    return connection


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.database = self.root / 'EDEB.db'
        seed(self.database).close()

    def tearDown(self):
        self.temp.cleanup()

    def mutate(self, sql):
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute(sql)

    def test_current_trip_not_history_and_original_bytes_unchanged(self):
        original = self.database.read_bytes()
        self.assertEqual(read_totals(self.database), {'value': 1900, 'cartography': 300, 'biology': 1600})
        self.assertEqual(self.database.read_bytes(), original)
        self.assertEqual(list(self.root.iterdir()), [self.database])

    def test_existing_trip_increases_and_resets_without_baseline(self):
        self.assertEqual(read_current_trip(self.database), 1900)
        self.mutate('UPDATE Body SET CartographicValue=100000000000 WHERE StarSystemId=1 AND Id=1')
        self.assertEqual(read_current_trip(self.database), 100000001800)
        self.mutate('UPDATE StarSystem SET IsTripHistory=0')
        self.assertEqual(read_current_trip(self.database), 0)
        self.mutate('UPDATE StarSystem SET IsTripHistory=1 WHERE Id=2')
        self.assertEqual(read_current_trip(self.database), 104999)

    def test_schema_and_version_changes_fail_closed(self):
        self.mutate('PRAGMA user_version=280')
        with self.assertRaisesRegex(SourceError, 'schema incompatible'):
            read_current_trip(self.database)
        self.mutate('PRAGMA user_version=279')
        self.mutate('ALTER TABLE Body ADD COLUMN Unexpected INTEGER')
        with self.assertRaisesRegex(SourceError, 'schema incompatible'):
            read_current_trip(self.database)

    def test_ambiguous_filter_refuses_to_guess(self):
        self.mutate('UPDATE Genus SET VistaGenomicsValue=123 WHERE AnalysisComplete=0')
        with self.assertRaisesRegex(SourceError, 'filters no longer agree'):
            read_current_trip(self.database)
        self.mutate('UPDATE Genus SET VistaGenomicsValue=0 WHERE AnalysisComplete=0')
        self.mutate('UPDATE Body SET WasReadFromJournal=0 WHERE StarSystemId=1 AND Id=1')
        with self.assertRaisesRegex(SourceError, 'filters no longer agree'):
            read_current_trip(self.database)

    def test_null_negative_fractional_and_orphan_values_fail(self):
        for value in ('NULL', '-1', '1.5'):
            self.mutate(f'UPDATE Body SET CartographicValue={value} WHERE StarSystemId=1 AND Id=1')
            with self.assertRaisesRegex(SourceError, 'invalid values'):
                read_current_trip(self.database)
        self.mutate('UPDATE Body SET CartographicValue=100 WHERE StarSystemId=1 AND Id=1')
        self.mutate('UPDATE Genus SET StarSystemId=99 WHERE StarSystemId=2')
        with self.assertRaisesRegex(SourceError, 'orphan'):
            read_current_trip(self.database)

    def test_invalid_trip_flag(self):
        self.mutate('UPDATE StarSystem SET IsTripHistory=2 WHERE Id=1')
        with self.assertRaisesRegex(SourceError, 'trip flags'):
            read_current_trip(self.database)

    def test_wal_snapshot_never_changes_source_sidecars(self):
        other = self.root / 'wal.db'
        with closing(seed(other, wal=True)) as connection:
            before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.iterdir()}
            self.assertEqual(read_current_trip(other), 1900)
            after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.iterdir()}
            self.assertEqual(before, after)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM Genus').fetchone()[0], 4)

    def test_journal_and_changing_copy_are_retried(self):
        journal = Path(str(self.database) + '-journal')
        journal.write_bytes(b'active transaction')
        with self.assertRaisesRegex(SourceError, 'rollback journal'):
            read_current_trip(self.database)
        journal.unlink()
        before = file_state([self.database])
        with patch('telemetry.sqlite_snapshot.file_state', side_effect=[before, {}]):
            with self.assertRaisesRegex(SourceError, 'changed during snapshot'):
                read_current_trip(self.database)

    def test_byte_change_without_metadata_change_is_rejected(self):
        with patch('telemetry.sqlite_snapshot.stream_hash', side_effect=[b'first', b'different']):
            with self.assertRaisesRegex(SnapshotError, 'bytes changed'):
                with stable_snapshot(self.database):
                    self.fail('must not yield an inconsistent snapshot')

    def test_sender_retains_value_through_source_error_and_recovers(self):
        sent = []
        settings = {'receiver_url': '', 'token': '', 'read_interval': .5}
        sender = Sender(settings, lambda _url, _token, data: sent.append(data['value']))
        with patch('sys.argv', ['sender']), patch('telemetry.sender.config', return_value=settings), \
                patch('telemetry.sender.Sender', return_value=sender), \
                patch('telemetry.sender.time.sleep'), \
                patch('telemetry.sender.read_current_trip', side_effect=[1900, SourceError('busy'), 1900, 2000, 0, KeyboardInterrupt()]):
            sender_main()
        self.assertEqual(sent, [1900, 2000, 0])


if __name__ == '__main__':
    unittest.main()
