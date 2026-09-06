param([switch]$Demo)
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
$Arguments = @('-m', 'telemetry.sender', '--config', 'config.local.json')
if ($Demo) { $Arguments += '--demo' }
& .\.venv\Scripts\python.exe @Arguments
exit $LASTEXITCODE
