import hashlib
from contextlib import closing
import http.client
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from telemetry.common import MAX_VALUE, ROOT, credits, payload, timestamp, allowed_ip, config
from telemetry.receiver import State, handler
from telemetry.sender import Sender, send
from telemetry.source import read_current_trip, UnverifiedSourceError
from tools.inspect_edeb import inspect


class ValidationTests(unittest.TestCase):
    def test_values(self):
        for value in (0, 12847563420, 999999999999, MAX_VALUE):
            self.assertEqual(credits(value), value)
        for value in (-1, True, 1.5, '12', None, MAX_VALUE + 1, float('nan')):
            with self.assertRaises(ValueError):
                credits(value)

    def test_source_and_time(self):
        valid = {'value': 1, 'timestamp': timestamp(), 'source': 'edeb-current-trip'}
        self.assertEqual(payload(valid), valid)
        for key, value in [('source', 'lifetime'), ('timestamp', '2026-01-01'), ('timestamp', None)]:
            with self.assertRaises(ValueError):
                payload({**valid, key: value})

    def test_config_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.json'
            data = json.loads((ROOT / 'config.example.json').read_text())
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                config(path)
            data['token'] = 'test-only-secret-' * 3
            path.write_text(json.dumps(data))
            self.assertEqual(config(path)['state_file'], str(Path(directory).resolve() / 'data/last-value.json'))
            data['overlay']['decimals'] = 1.5
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                config(path)

    def test_no_unverified_read(self):
        with self.assertRaises(UnverifiedSourceError):
            read_current_trip()

    def test_network_scope(self):
        for ip in ('127.0.0.1', '100.64.0.1', '100.127.255.254'):
            self.assertTrue(allowed_ip(ip))
        for ip in ('0.0.0.0', '192.168.1.1', '8.8.8.8', '100.128.0.1'):
            self.assertFalse(allowed_ip(ip))
        with self.assertRaises(ValueError):
            send('http://8.8.8.8:8765', 'x', {})


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.state = State(Path(self.temp.name) / 'value.json')
        self.settings = json.loads((ROOT / 'config.example.json').read_text())
        self.settings['token'] = 'test-only-secret-' * 3
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), handler(self.state, self.settings))
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def post(self, data, token=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        connection.request('POST', '/api/value', json.dumps(data), {'Authorization': 'Bearer ' + (token or self.settings['token']), 'Content-Type': 'application/json'})
        response = connection.getresponse()
        result = response.status, json.loads(response.read())
        connection.close()
        return result

    def data(self, value):
        return {'value': value, 'timestamp': timestamp(), 'source': 'edeb-current-trip'}

    def test_updates_reset_and_restart(self):
        self.assertIsNone(self.state.read()['value'])
        for value in (12847563420, MAX_VALUE, 100, 0):
            data = self.data(value)
            self.assertEqual(self.post(data), (200, {'ok': True, 'changed': True}))
            self.assertEqual(self.post(data), (200, {'ok': True, 'changed': False}))
            self.assertEqual(State(self.state.path).read()['value'], value)

    def test_auth_and_invalid(self):
        self.assertEqual(self.post(self.data(10), 'wrong')[0], 401)
        for value in (-1, True, '100', MAX_VALUE + 1):
            self.assertEqual(self.post(self.data(value))[0], 400)
        self.assertEqual(self.post({**self.data(1), 'source': 'demo'})[0], 400)
        self.assertIsNone(self.state.read()['value'])

    def test_persistence_failure(self):
        with patch('telemetry.receiver.atomic_json', side_effect=OSError()):
            self.assertEqual(self.post(self.data(42))[0], 503)
        self.assertIsNone(self.state.read()['value'])

    def test_real_transport(self):
        send(self.url, self.settings['token'], self.data(12000))
        self.assertEqual(self.state.read()['value'], 12000)

    def test_static_and_secret_not_exposed(self):
        for path in ('/api/config', '/api/value', '/health', '/overlay/', '/overlay/app.js', '/overlay/style.css', '/overlay/format.js'):
            connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
            connection.request('GET', path)
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertNotIn(self.settings['token'].encode(), response.read())
            connection.close()

    def test_corrupt_state_does_not_reset(self):
        self.state.path.write_text('invalid')
        with self.assertRaises(ValueError):
            State(self.state.path)


class SenderTests(unittest.TestCase):
    def test_retry_latest_and_dedup(self):
        calls = []
        def transport(_url, _token, data):
            calls.append(data['value'])
            if len(calls) == 1:
                raise ConnectionError('offline')
        sender = Sender({'receiver_url': '', 'token': ''}, transport)
        self.assertFalse(sender.step(100, now=0))
        self.assertFalse(sender.step(200, now=1))
        self.assertTrue(sender.step(300, now=2))
        self.assertFalse(sender.step(300, now=3))
        self.assertTrue(sender.step(0, now=4))
        self.assertEqual(calls, [100, 300, 0])


class InspectorTests(unittest.TestCase):
    def test_fixture_read_only_and_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / 'fixture.db'
            with closing(sqlite3.connect(database)) as connection, connection:
                connection.execute('CREATE TABLE synthetic_trip (value INTEGER)')
                connection.execute('INSERT INTO synthetic_trip VALUES (12847563420)')
            digest = hashlib.sha256(database.read_bytes()).hexdigest()
            report = inspect(root, True)
            info = report['files'][0]['inspection']
            self.assertEqual(info['samples_PRIVATE']['synthetic_trip']['rows'], [[12847563420]])
            self.assertEqual(digest, hashlib.sha256(database.read_bytes()).hexdigest())
            self.assertEqual(list(root.iterdir()), [database])

    def test_wal_snapshot_preserves_uncheckpointed_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / 'fixture.db'
            connection = sqlite3.connect(database)
            try:
                connection.execute('PRAGMA journal_mode=WAL')
                connection.execute('CREATE TABLE synthetic_trip (value INTEGER)')
                connection.execute('INSERT INTO synthetic_trip VALUES (42)')
                connection.commit()
                before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir()}
                report = inspect(root, True)
                info = next(f for f in report['files'] if f['file'] == 'fixture.db')['inspection']
                self.assertEqual(info['samples_PRIVATE']['synthetic_trip']['rows'], [[42]])
                after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir()}
                self.assertEqual(before, after)
            finally:
                connection.close()

    def test_unknown_format(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'unknown.db').write_bytes(b'not sqlite')
            self.assertTrue(inspect(Path(directory))['files'][0]['format'].startswith('unknown'))


if __name__ == '__main__':
    unittest.main()
