"""Run with python -m telemetry.receiver --config config.local.json."""
import argparse
import hmac
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from .common import ROOT, allowed_ip, atomic_json, config, payload, timestamp


class State:
    def __init__(self, path, allow_demo=False):
        self.path = Path(path)
        self.allow_demo = allow_demo
        self.lock = threading.Lock()
        self.data = {'value': None, 'timestamp': None, 'source': None}
        if self.path.exists():
            self.data = payload(json.loads(self.path.read_text()), allow_demo)

    def update(self, incoming):
        incoming = payload(incoming, self.allow_demo)
        with self.lock:
            # Persist before acknowledging; a retry of the same value is harmless.
            if incoming == self.data:
                return False
            atomic_json(self.path, incoming)
            changed = incoming['value'] != self.data['value']
            self.data = incoming
            return changed

    def read(self):
        with self.lock:
            return dict(self.data)


def handler(state, settings):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def log_message(self, *_args):
            pass

        def reply(self, status, body, kind='application/json'):
            if not isinstance(body, bytes):
                body = json.dumps(body).encode()
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            routes = {'/overlay/': ('index.html', 'text/html; charset=utf-8'), '/overlay/style.css': ('style.css', 'text/css'), '/overlay/app.js': ('app.js', 'text/javascript'), '/overlay/format.js': ('format.js', 'text/javascript')}
            if self.path == '/api/value':
                self.reply(200, state.read())
            elif self.path == '/api/config':
                self.reply(200, settings['overlay'])
            elif self.path == '/health':
                self.reply(200, {'status': 'ok', 'timestamp': timestamp()})
            elif self.path in routes:
                name, kind = routes[self.path]
                self.reply(200, (ROOT / 'overlay' / name).read_bytes(), kind)
            else:
                self.reply(404, {'error': 'not found'})

        def do_POST(self):
            if self.path != '/api/value':
                return self.reply(404, {'error': 'not found'})
            supplied = self.headers.get('Authorization', '')
            if not hmac.compare_digest(supplied.encode(), ('Bearer ' + settings['token']).encode()):
                return self.reply(401, {'error': 'unauthorized'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 4096 or self.headers.get('Transfer-Encoding'):
                    raise ValueError('body must be 1..4096 bytes')
                if self.headers.get_content_type() != 'application/json':
                    raise ValueError('Content-Type must be application/json')
                changed = state.update(json.loads(self.rfile.read(length)))
                if changed:
                    logging.info('[VALUE] %s Cr', f"{state.read()['value']:,}")
                self.reply(200, {'ok': True, 'changed': changed})
            except (ValueError, UnicodeError):
                self.reply(400, {'error': 'invalid value, source, timestamp or JSON body'})
            except OSError:
                logging.error('[STATE] Persistence failed; update not acknowledged')
                self.reply(503, {'error': 'persistence unavailable'})
    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config.local.json')
    parser.add_argument('--demo', action='store_true', help='isolated demo state; accept demo updates')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    settings = config(args.config)
    hosts = ['127.0.0.1']
    if settings.get('tailscale_ip'):
        host = settings['tailscale_ip']
        if not allowed_ip(host) or host.startswith('127.'):
            raise ValueError('tailscale_ip must be a Tailscale IPv4 address')
        hosts.append(host)
    state_path = settings['state_file'] + ('.demo' if args.demo else '')
    state = State(state_path, args.demo)
    servers = []
    started = []
    try:
        for host in hosts:
            server = ThreadingHTTPServer((host, settings['port']), handler(state, settings))
            servers.append(server)
        for server in servers:
            threading.Thread(target=server.serve_forever, daemon=True).start()
            started.append(server)
        logging.info('[RECEIVER] Listening on %s port %s%s', ', '.join(hosts), settings['port'], ' (DEMO)' if args.demo else '')
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        for server in servers:
            if server in started:
                server.shutdown()
            server.server_close()


if __name__ == '__main__':
    main()
