<#
.SYNOPSIS
    Spustí webovú aplikáciu pre testerov (http://127.0.0.1:8765).

.DESCRIPTION
    Formulár so všetkými parametrami stratégie, výber páru a obdobia, fronta backtestov,
    história behov (ukladá sa do platforms/freqtrade/user_data/runs/ a commituje sa)
    s vyhľadávaním podľa parametrov a grafom výnosnosti ako v TradingView.
    Viď docs/WEBAPP.md.

.EXAMPLE
    .\platforms\freqtrade\scripts\webapp.ps1
    .\platforms\freqtrade\scripts\webapp.ps1 -Port 9000
#>
[CmdletBinding()]
param(
    [int]$Port = 8765,
    [string]$BindHost = "127.0.0.1"
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$py = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Chyba .venv - spusti najprv platforms\freqtrade\scripts\setup.ps1" }

$env:IBS_WEB_PORT = "$Port"
$env:IBS_WEB_HOST = $BindHost
Set-Location $repo
& $py -m ibs.webapp
