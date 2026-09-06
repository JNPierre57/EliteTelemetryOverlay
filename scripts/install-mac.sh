#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
python3 -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ required"'
python3 -m venv .venv
.venv/bin/python -m telemetry.setup_config
printf '%s\n' 'Ready. Edit config.local.json; then run sh scripts/start-mac.sh'
