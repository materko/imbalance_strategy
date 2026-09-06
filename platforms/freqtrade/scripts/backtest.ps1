<#
.SYNOPSIS
    Spustí backtest s 1m detailom (rozlíšenie fillov vnútri 3m sviečky).

.DESCRIPTION
    `--timeframe-detail 1m` je zámerné rozhodnutie z ARCHITECTURE_port.md §7:
    signály sa naďalej generujú na uzavretých 3m sviečkach (ako v TradingView),
    ale SL/TP sa vnútri sviečky prehráva po 1m krokoch. Stratégiu NIKDY nespúšťaj
    priamo na 1m - všetky *MaxBars limity sú v baroch, nie v minútach.

.EXAMPLE
    .\platforms\freqtrade\scripts\backtest.ps1 -Timerange 20260801-20260905
#>
[CmdletBinding()]
param(
    [string]$Strategy = "IBSImbalanceStrategy",
    [string]$Config = "config.binance.json",
    [string]$Timerange,
    [string]$TimeframeDetail = "1m",
    [switch]$NoDetail,
    [switch]$Export
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$ft = Join-Path $repo "platforms\freqtrade"
$userdir = Join-Path $ft "user_data"
$py = Join-Path $repo ".venv\Scripts\python.exe"

if (-not (Test-Path $py)) { throw "Chyba .venv - spusti najprv platforms\freqtrade\scripts\setup.ps1" }

$stratFile = Join-Path $userdir "strategies\$Strategy.py"
if (-not (Test-Path $stratFile)) {
    throw "Strategia $Strategy este neexistuje ($stratFile). Adapter sa pise v kroku 4 - viz docs/ARCHITECTURE_port.md par. 8."
}

# --cache none je POVINNE. Freqtrade cachuje vysledok podla hashu suboru
# strategie, ale nase nastavenia su v profile mimo neho (TRADEBOT_PROFILE), takze
# zmena profilu cache nezneplatni a dostanes ticho stary vysledok.
$args = @(
    "-m", "freqtrade", "backtesting",
    "--config", (Join-Path $ft $Config),
    "--userdir", $userdir,
    "--strategy", $Strategy,
    "--cache", "none"
)
if (-not $NoDetail) { $args += @("--timeframe-detail", $TimeframeDetail) }
if ($Timerange) { $args += @("--timerange", $Timerange) }
if ($Export) { $args += @("--export", "signals") }

Write-Host "freqtrade $($args[1..($args.Length-1)] -join ' ')" -ForegroundColor DarkGray
& $py @args
