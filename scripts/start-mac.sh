#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
exec .venv/bin/python -m telemetry.receiver --config config.local.json "$@"
