param(
    [string]$DataPath = "$env:LOCALAPPDATA\Elite Dangerous Exploration Buddy",
    [string]$OutputPath = (Join-Path $PSScriptRoot '..\reports\edeb-inspection.json'),
    [switch]$IncludeSamples
)
$ErrorActionPreference = 'Stop'
$Inspector = Join-Path $PSScriptRoot 'inspect_edeb.py'
$Arguments = @('-3', $Inspector, '--root', $DataPath, '--output', $OutputPath)
if ($IncludeSamples) { $Arguments += '--include-samples' }
& py @Arguments
if ($LASTEXITCODE -ne 0) { throw 'EDEB inspection failed. See the error above.' }
