<#
.SYNOPSIS
    Spustí webovú aplikáciu pre testerov (bez Dockeru) a otvorí prehliadač.

.DESCRIPTION
    Stačí mať Python 3.11+ (64-bit) a git. Ak chýba .venv, skript ho sám postaví
    (setup.ps1: freqtrade + balík tradebot, trvá ~10 minút, len prvýkrát). Ak chýbajú
    pracovné dáta, webapp ich pri štarte zloží z data_archive/.

    Formulár so všetkými parametrami stratégie, výber páru a obdobia, fronta
    backtestov, história behov (user_data/runs/, commituje sa) s vyhľadávaním
    a grafom výnosnosti ako v TradingView. Viď docs/WEBAPP.md.

.EXAMPLE
    .\platforms\freqtrade\scripts\webapp.ps1
    .\platforms\freqtrade\scripts\webapp.ps1 -Port 9000 -NoBrowser
#>
[CmdletBinding()]
param(
    [int]$Port = 8765,
    [string]$BindHost = "127.0.0.1",
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$py = Join-Path $repo ".venv\Scripts\python.exe"

if (-not (Test-Path $py)) {
    Write-Host "Chyba .venv - staviam prostredie (prvykrat ~10 minut)..." -ForegroundColor Yellow
    & (Join-Path $PSScriptRoot "setup.ps1")
    if (-not (Test-Path $py)) { throw "setup.ps1 nevytvoril $py" }
}

$env:TRADEBOT_WEB_PORT = "$Port"
$env:TRADEBOT_WEB_HOST = $BindHost
Set-Location $repo

$url = "http://$BindHost`:$Port"
Write-Host "IBS webapp: $url  (Ctrl+C ukonci)" -ForegroundColor Green

if (-not $NoBrowser) {
    # Prehliadac otvorime, ked server zacne odpovedat - v samostatnom jobe,
    # aby hlavne vlakno mohlo drzat server v popredi.
    Start-Job -ScriptBlock {
        param($u)
        for ($i = 0; $i -lt 60; $i++) {
            try { Invoke-WebRequest -Uri "$u/api/queue" -UseBasicParsing -TimeoutSec 2 | Out-Null; Start-Process $u; break }
            catch { Start-Sleep -Seconds 1 }
        }
    } -ArgumentList $url | Out-Null
}

& $py -m tradebot.webapp
