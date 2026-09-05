<#
.SYNOPSIS
    Spustí webovú aplikáciu pre testerov z koreňa repozitára.
    Tenký obal nad platforms\freqtrade\scripts\webapp.ps1 - viď docs/WEBAPP.md.

.EXAMPLE
    .\webapp.ps1
    .\webapp.ps1 -Port 9000 -NoBrowser
#>
[CmdletBinding()]
param(
    [int]$Port = 8765,
    [string]$BindHost = "127.0.0.1",
    [switch]$NoBrowser
)
& (Join-Path $PSScriptRoot "platforms\freqtrade\scripts\webapp.ps1") -Port $Port -BindHost $BindHost -NoBrowser:$NoBrowser
