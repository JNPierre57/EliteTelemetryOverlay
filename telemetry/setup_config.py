"""Create local configuration exclusively; never replace existing secrets."""
import json
import os
from pathlib import Path
import secrets
from .common import ROOT


def main():
    path = ROOT / 'config.local.json'
    data = json.loads((ROOT / 'config.example.json').read_text())
    data['token'] = secrets.token_urlsafe(32)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print('Existing config.local.json preserved.')
        return
    with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2)
    print('Created config.local.json with a generated secret. Copy the token privately to the other machine.')


if __name__ == '__main__':
    main()
