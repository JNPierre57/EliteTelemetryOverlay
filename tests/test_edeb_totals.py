from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from tools.edeb_totals import compare_totals
from tools.inspect_edeb import inspect

SCHEMA = json.loads((Path(__file__).parent / 'fixtures/edeb-schema-279.json').read_text())


def fixture(connection):
    for _, _, _, sql in SCHEMA['schema']:
        connection.execute(sql)
    connection.executemany('INSERT INTO StarSystem(Id,Name,StarClass,IsTripHistory) VALUES (?,?,?,?)',
                           [(1, 'Synthetic trip', 'G', 1), (2, 'Synthetic old', 'G', 0)])
    connection.executemany('''INSERT INTO Body
        (Id,StarSystemId,Name,Type,Distance,RingsReserveLevel,CartographicValue,WasReadFromJournal)
        VALUES (?,?,?,0,0,0,?,?)''',
        [(1, 1, 'Synthetic A', 100, 1), (2, 1, 'Synthetic B', 200, 0),
         (1, 2, 'Synthetic C', 1000, 1), (3, 1, 'Synthetic D', None, 1)])
    connection.executemany('''INSERT INTO Genus
        (Name,BodyId,StarSystemId,VistaGenomicsValue,AnalysisComplete) VALUES (?,?,?,?,?)''',
        [('Synthetic A', 1, 1, 500, 1), ('Synthetic B', 1, 1, 700, 1),
         ('Synthetic C', 2, 1, 900, 0), ('Synthetic D', 1, 2, 3000, 1)])
    connection.commit()


class TotalsTests(unittest.TestCase):
    def test_independent_sums_avoid_biology_join_multiplication(self):
        with closing(sqlite3.connect(':memory:')) as connection:
            fixture(connection)
            report = compare_totals(connection, {'trip': 1500, 'history': 5500})
            trip = report['scopes']['trip_flag_1']
            self.assertEqual(trip['cartography']['all_bodies']['sum'], 300)
            self.assertEqual(trip['cartography']['all_bodies']['null_values'], 1)
            self.assertEqual(trip['biology']['completed_genera']['sum'], 1200)
            self.assertEqual(report['matching_pairs'], ['all_bodies+completed_genera'])
            self.assertEqual(trip['candidates']['all_bodies+all_genera']['value'], 2400)

    def test_mismatch_does_not_choose_a_candidate(self):
        with closing(sqlite3.connect(':memory:')) as connection:
            fixture(connection)
            self.assertEqual(compare_totals(connection, {'trip': 42, 'history': 55})['matching_pairs'], [])

    def test_invalid_values_and_orphans_are_reported(self):
        with closing(sqlite3.connect(':memory:')) as connection:
            fixture(connection)
            connection.execute('UPDATE Body SET CartographicValue=-100 WHERE StarSystemId=1 AND Id=1')
            connection.execute("INSERT INTO Genus(Name,BodyId,StarSystemId,VistaGenomicsValue) VALUES ('orphan',1,99,999)")
            result = compare_totals(connection, {'trip': 1300, 'history': 5300})
            self.assertEqual(result['matching_pairs'], [])
            self.assertEqual(result['orphan_rows']['Genus'], 1)
            self.assertEqual(result['scopes']['trip_flag_1']['cartography']['all_bodies']['invalid_values'], 1)

    def test_missing_column_is_explicit(self):
        with closing(sqlite3.connect(':memory:')) as connection:
            fixture(connection)
            connection.execute('ALTER TABLE Genus RENAME COLUMN VistaGenomicsValue TO UnsupportedValue')
            result = compare_totals(connection)
            self.assertEqual(result['status'], 'unsupported_schema')
            self.assertIn('VistaGenomicsValue', result['missing_columns']['Genus'])

    def test_reset_flag_and_aggregate_report_without_private_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / 'EDEB.db'
            with closing(sqlite3.connect(database)) as connection:
                fixture(connection)
                connection.execute('UPDATE StarSystem SET IsTripHistory=0')
                connection.commit()
            original = database.read_bytes()
            report = inspect(root, expected={'trip': 0, 'history': 5500})
            comparison = report['files'][0]['inspection']['edeb_value_comparison']
            self.assertEqual(comparison['scopes']['trip_flag_1']['candidates']['all_bodies+completed_genera']['value'], 0)
            self.assertNotIn('Synthetic', json.dumps(report))
            self.assertEqual(database.read_bytes(), original)
            self.assertEqual(list(root.iterdir()), [database])


if __name__ == '__main__':
    unittest.main()
