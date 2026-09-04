<#
.SYNOPSIS
    Stiahne sviečkové dáta pre obe burzy do platforms/freqtrade/user_data/data.

.DESCRIPTION
    Timeframy majú v tomto porte konkrétnu úlohu (ARCHITECTURE_port.md §7):
      3m = timeframe stratégie (signály; všetky *MaxBars limity sú v BAROCH)
      5m = zoneDetectionTF - detekcia SD zón cez informative pair
      1m = timeframe_detail pre backtest - rozlíšenie SL/TP vnútri 3m sviečky

    Binance  = exekučná burza, futures perp. Vie všetky tri TF priamo,
               a keďže config má trading_mode=futures, dotiahne aj mark a funding_rate.
    Coinbase = referenčná burza (to, čo je na TradingView screenshotoch), spot.
               NEVIE 3m - cez ccxt ponúka len 1m/5m/15m/30m/1h/2h/6h/1d.
               Sťahujú sa preto len oficiálne TF (1m, 5m). 3m si z 1m poskladá
               samotná Freqtrade stratégia svojimi vlastnými prostriedkami -
               na disk sa žiadny umelý timeframe neukladá.

.EXAMPLE
    .\platforms\freqtrade\scripts\download-data.ps1
.EXAMPLE
    .\platforms\freqtrade\scripts\download-data.ps1 -Timerange 20260801-20260905
.EXAMPLE
    .\platforms\freqtrade\scripts\download-data.ps1 -SkipCoinbase -Days 180
#>
[CmdletBinding()]
param(
    [string]$Timerange,
    [int]$Days = 60,
    [switch]$SkipBinance,
    [switch]$SkipCoinbase,
    [switch]$Erase
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$ft = Join-Path $repo "platforms\freqtrade"
$userdir = Join-Path $ft "user_data"
$py = Join-Path $repo ".venv\Scripts\python.exe"

if (-not (Test-Path $py)) { throw "Chyba .venv - spusti najprv platforms\freqtrade\scripts\setup.ps1" }

$range = if ($Timerange) { @("--timerange", $Timerange) } else { @("--days", "$Days") }
$eraseArg = if ($Erase) { @("--erase") } else { @() }

function Invoke-Download {
    param([string]$Label, [string]$ConfigName, [string[]]$Tf)

    Write-Host ""
    Write-Host "=== $Label ===" -ForegroundColor Cyan
    Write-Host "timeframes: $($Tf -join ' ')"

    & $py -m freqtrade download-data `
        --config (Join-Path $ft $ConfigName) `
        --userdir $userdir `
        --timeframes $Tf `
        @range @eraseArg

    if ($LASTEXITCODE -ne 0) {
        Write-Warning "$Label - download zlyhal (exit $LASTEXITCODE). Viz docs/RUNNING.md."
        return $false
    }
    return $true
}

if (-not $SkipBinance) {
    Invoke-Download -Label "Binance BTC/USDT:USDT (futures)" `
        -ConfigName "config.binance.json" -Tf @("1m", "3m", "5m") | Out-Null
}

if (-not $SkipCoinbase) {
    $ok = Invoke-Download -Label "Coinbase BTC/USD (spot, referencne)" `
        -ConfigName "config.coinbase.json" -Tf @("1m", "5m")

    if ($ok) {
        Write-Host "Coinbase 3m sa nesťahuje - burza ho neponúka. Stratégia si ho poskladá z 1m." -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "=== Co je stiahnute ===" -ForegroundColor Cyan
& $py -m freqtrade list-data --userdir $userdir --config (Join-Path $ft "config.binance.json")
& $py -m freqtrade list-data --userdir $userdir --config (Join-Path $ft "config.coinbase.json")

Write-Host ""
Write-Host "=== Delim na rocne subory pre git ===" -ForegroundColor Cyan
& $py -m ibs.tools.data_archive split
Write-Host ""
Write-Host "Commituj len user_data\data_archive\ - pracovne subory v data\ su" -ForegroundColor Green
Write-Host "v .gitignore. Po klonovani sa poskladaju prikazom:" -ForegroundColor Green
Write-Host "  python -m ibs.tools.data_archive merge"
