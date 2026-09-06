param(
    [string]$TaskName = 'EliteTelemetryOverlay Sender'
)

$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
$Python = (Resolve-Path '.\.venv\Scripts\python.exe').Path
$Config = (Resolve-Path '.\config.local.json').Path

if (-not (Test-Path $Python)) { throw 'Run install-shadow.ps1 first.' }
if (-not (Test-Path $Config)) { throw 'Create and configure config.local.json first.' }

$Action = New-ScheduledTaskAction -Execute $Python -Argument "-m telemetry.sender --config `"$Config`"" -WorkingDirectory (Get-Location).Path
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$Settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Days 3650)
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
$Task = New-ScheduledTask -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description 'Reads EDEB Current Exploration Trip and sends updates to the Mac over Tailscale.'
Register-ScheduledTask -TaskName $TaskName -InputObject $Task -Force | Out-Null
Write-Host "Installed '$TaskName' for $env:USERNAME. It starts at interactive logon."
Write-Host "Start now: Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "Inspect:  Get-ScheduledTask -TaskName '$TaskName' | Get-ScheduledTaskInfo"
Write-Host "Remove:   Unregister-ScheduledTask -TaskName '$TaskName'"
