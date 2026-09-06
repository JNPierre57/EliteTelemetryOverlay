"""Generate, but do not load, a per-user macOS LaunchAgent."""
from pathlib import Path
import plistlib
import sys

root = Path(__file__).resolve().parent.parent
if sys.platform != 'darwin':
    raise SystemExit('This tool is for macOS only.')
python = root / '.venv/bin/python'
if not python.exists():
    raise SystemExit('Run sh scripts/install-mac.sh first.')
label = 'local.EliteTelemetryOverlay.receiver'
path = Path.home() / 'Library/LaunchAgents' / (label + '.plist')
path.parent.mkdir(parents=True, exist_ok=True)
(root / 'data').mkdir(exist_ok=True)
agent = {'Label': label, 'ProgramArguments': [str(python), '-m', 'telemetry.receiver', '--config', str(root / 'config.local.json')], 'WorkingDirectory': str(root), 'RunAtLoad': True, 'KeepAlive': True, 'ThrottleInterval': 15, 'StandardOutPath': str(root / 'data/receiver.log'), 'StandardErrorPath': str(root / 'data/receiver.log')}
with path.open('xb') as stream:
    plistlib.dump(agent, stream)
print('Generated:', path)
print('Load: launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.EliteTelemetryOverlay.receiver.plist')
print('Stop: launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/local.EliteTelemetryOverlay.receiver.plist')
print('Remove the plist after stopping to disable future login startup.')
