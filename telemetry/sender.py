import argparse
import http.client
import json
import logging
import socket
import time
from urllib.parse import urlsplit
from .common import allowed_ip, config, credits, timestamp
from .source import read_current_trip, UnverifiedSourceError


class HTTPStatusError(ConnectionError):
    def __init__(self, status):
        self.status = status
        super().__init__(f'HTTP {status}')


def send(url, token, data):
    target = urlsplit(url)
    if target.scheme != 'http' or target.username or target.password or target.query or target.fragment or target.path not in ('', '/'):
        raise ValueError('receiver_url must be http://Tailscale-host:port')
    addresses = socket.getaddrinfo(target.hostname, target.port or 80, socket.AF_INET, socket.SOCK_STREAM)
    if not addresses or any(not allowed_ip(item[4][0]) for item in addresses):
        raise ValueError('receiver must resolve exclusively to Tailscale IPv4 or loopback')
    # Connect to the validated address; no proxies, redirects or second DNS lookup.
    connection = http.client.HTTPConnection(addresses[0][4][0], target.port or 80, timeout=3)
    try:
        connection.request('POST', '/api/value', json.dumps(data), {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
        response = connection.getresponse()
        result = response.read(4096)
        if response.status != 200:
            raise HTTPStatusError(response.status)
        if json.loads(result).get('ok') is not True:
            raise ConnectionError('invalid acknowledgement')
    finally:
        connection.close()


class Sender:
    def __init__(self, settings, transport=send):
        self.settings = settings
        self.transport = transport
        self.last_sent = None
        self.failures = 0
        self.next_retry = 0

    def step(self, value, source='edeb-current-trip', now=None):
        credits(value)
        now = time.monotonic() if now is None else now
        if value == self.last_sent or now < self.next_retry:
            return False
        try:
            self.transport(self.settings['receiver_url'], self.settings['token'], {'value': value, 'timestamp': timestamp(), 'source': source})
        except (OSError, ValueError, http.client.HTTPException) as error:
            self.failures += 1
            delay = min(30, 2 ** min(self.failures, 5))
            self.next_retry = now + delay
            reason = f'HTTP {error.status}' if isinstance(error, HTTPStatusError) else type(error).__name__
            logging.warning('[NETWORK] Update failed (%s); retry in %ss', reason, delay)
            return False
        self.last_sent = value
        self.failures = 0
        self.next_retry = 0
        logging.info('[NETWORK] Sent %s Cr', f'{value:,}')
        return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config.local.json')
    parser.add_argument('--demo', action='store_true')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    settings = config(args.config)
    sender = Sender(settings)
    try:
        if args.demo:
            for value in [1000000000, 1025000000, 2450000000, 12847563420, 12847563420, 250, 0]:
                while value != sender.last_sent:
                    sender.step(value, 'demo')
                    time.sleep(settings['read_interval'])
                time.sleep(2)
            return
        previous = None
        while True:
            value = read_current_trip()
            if value != previous:
                logging.info('[EDEB] Current trip value: %s Cr', f'{value:,}')
                previous = value
            sender.step(value)
            time.sleep(settings['read_interval'])
    except UnverifiedSourceError as error:
        logging.error('[EDEB] %s', error)
        raise SystemExit(2) from None
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
