$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
& py -3 -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11+ required"'
if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.11 or newer from python.org.' }
& py -3 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
& .\.venv\Scripts\python.exe -m telemetry.setup_config
if ($LASTEXITCODE -ne 0) { throw 'Configuration creation failed.' }
Write-Host 'Ready. Edit config.local.json; see docs/INSTALL.md before starting.'
