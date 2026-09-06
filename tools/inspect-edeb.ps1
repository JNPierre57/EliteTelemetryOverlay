param(
    [string]$DataPath = "$env:LOCALAPPDATA\Elite Dangerous Exploration Buddy",
    [string]$OutputPath = (Join-Path $PSScriptRoot '..\reports\edeb-inspection.json'),
    [switch]$IncludeSamples,
    [Nullable[long]]$TripValue,
    [Nullable[long]]$HistoryValue
)
$ErrorActionPreference = 'Stop'
$Inspector = Join-Path $PSScriptRoot 'inspect_edeb.py'
$Arguments = @('-3', $Inspector, '--root', $DataPath, '--output', $OutputPath)
if ($IncludeSamples) { $Arguments += '--include-samples' }
if ($null -ne $TripValue -or $null -ne $HistoryValue) {
    if ($null -eq $TripValue -or $null -eq $HistoryValue -or $TripValue -lt 0 -or $HistoryValue -lt 0) {
        throw 'Supply both -TripValue and -HistoryValue as nonnegative integers.'
    }
    $Arguments += @('--trip-value', [string]$TripValue, '--history-value', [string]$HistoryValue)
}
& py @Arguments
if ($LASTEXITCODE -ne 0) { throw 'EDEB inspection failed. See the error above.' }
