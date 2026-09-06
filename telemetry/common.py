import ipaddress
import json
import os
from pathlib import Path
from datetime import datetime, timezone

MAX_VALUE = 9_007_199_254_740_991
ROOT = Path(__file__).resolve().parent.parent


def credits(value):
    if type(value) is not int or not 0 <= value <= MAX_VALUE:
        raise ValueError(f'value must be an integer between 0 and {MAX_VALUE}')
    return value


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def payload(data, allow_demo=False):
    if not isinstance(data, dict):
        raise ValueError('JSON object required')
    credits(data.get('value'))
    if data.get('source') not in (['edeb-current-trip', 'demo'] if allow_demo else ['edeb-current-trip']):
        raise ValueError('unsupported source')
    try:
        date = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        if date.tzinfo is None:
            raise ValueError()
    except (KeyError, TypeError, AttributeError, ValueError):
        raise ValueError('timestamp must be ISO 8601 with timezone') from None
    return {key: data[key] for key in ('value', 'timestamp', 'source')}


def allowed_ip(address):
    ip = ipaddress.ip_address(address)
    return ip.is_loopback or (ip.version == 4 and ip in ipaddress.ip_network('100.64.0.0/10'))


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    try:
        with temp.open('w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def config(path):
    path = Path(path).resolve()
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    token = data.get('token', '')
    if not isinstance(token, str) or len(token) < 32 or token == 'CHANGE_ME_' * 4 or not token.isascii():
        raise ValueError('configure a shared ASCII token of at least 32 characters')
    for key, low, high in [('port', 1024, 65535), ('read_interval', .1, 60), ('poll_ms', 250, 5000), ('animation_ms', 0, 5000), ('font_size', 12, 200), ('decimals', 0, 2)]:
        value = data[key] if key in data else data.get('overlay', {}).get(key)
        if type(value) not in (int, float) or not low <= value <= high:
            raise ValueError(f'invalid configuration: {key}')
        if key in ('port', 'decimals') and type(value) is not int:
            raise ValueError(f'{key} must be an integer')
    visual = data['overlay']
    for key, limit in [('label', 120), ('suffix', 20), ('font_family', 200), ('thousands_separator', 4)]:
        if not isinstance(visual.get(key), str) or len(visual[key]) > limit:
            raise ValueError(f'invalid overlay text: {key}')
    if not isinstance(data.get('state_file'), str) or not data['state_file']:
        raise ValueError('state_file must be a nonempty path')
    if not isinstance(data.get('receiver_url'), str):
        raise ValueError('receiver_url must be a URL string')
    data['state_file'] = str(path.parent / data['state_file'])
    return data
