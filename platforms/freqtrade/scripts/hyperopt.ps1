<#
.SYNOPSIS
    Preladí prahy stratégie hyperoptom.

.DESCRIPTION
    Optimalizujú sa VÝHRADNE veci, ktoré nie sú prevzaté z TradingView:
      - prahy v jednotke `atr` (minImbSize, pbMinRange, engMinRange, liqSweepMinWick,
        srClusterPoints) - to sú štartovacie odhady, nie odmerané hodnoty
      - `rrRatio`
      - prepínače entry modelov a S/R / likviditného obchodovania

    Session okná, STATE timeouty ani sizing sa NELADIA - tie sú z TradingView
    a ich zmena by rozbila paritu (docs/GOLDEN_binance_2026-08-24.md).

    Bez `--timeframe-detail` zámerne: s 1m detailom je jedna epocha rádovo pomalšia.
    Najlepší výsledok si potom over bežným backtestom S detailom - to je až
    ten beh, ktorý hovorí niečo o skutočných fill cenách.

.PARAMETER Timerange
    Napr. 20250901-20260904 (365 dní) alebo 20260601-20260904 (~90 dní).

.PARAMETER Epochs
    Počet epoch. Pri 10 parametroch má zmysel aspoň 300.

.PARAMETER Loss
    Predvolene CalmarHyperOptLoss - zisk vážený max drawdownom. Presne to,
    čo bolo pri manuálnom prieskume dôležité (vysoké RR vyzeralo dobre na 365d,
    ale na 90d strácalo).

.EXAMPLE
    .\platforms\freqtrade\scripts\hyperopt.ps1 -Timerange 20250901-20260904 -Epochs 300
.EXAMPLE
    .\platforms\freqtrade\scripts\hyperopt.ps1 -Timerange 20260601-20260904 -Epochs 200 -Loss SharpeHyperOptLoss
#>
[CmdletBinding()]
param(
    [string]$Strategy = "IBSImbalanceStrategy",
    [string]$Config = "config.binance.json",
    [Parameter(Mandatory = $true)][string]$Timerange,
    [int]$Epochs = 300,
    [string]$Loss = "CalmarHyperOptLoss",
    [string]$Profile = "btcusdt_3m_binance_hyper",
    [string]$Spaces = "buy sell",
    [int]$Jobs = -1
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$ft = Join-Path $repo "platforms\freqtrade"
$userdir = Join-Path $ft "user_data"
$py = Join-Path $repo ".venv\Scripts\python.exe"

if (-not (Test-Path $py)) { throw "Chyba .venv - spusti najprv platforms\freqtrade\scripts\setup.ps1" }

$env:IBS_PROFILE = $Profile
Write-Host "Profil: $Profile" -ForegroundColor Cyan
Write-Host "Okno:   $Timerange   epoch: $Epochs   loss: $Loss" -ForegroundColor Cyan
Write-Host ""
Write-Host "POZOR: pri 10 parametroch a rádovo stovkách obchodov je pretrénovanie" -ForegroundColor Yellow
Write-Host "realne. Vysledok VZDY over na inom okne, nez na akom si ladil." -ForegroundColor Yellow
Write-Host ""

$args = @(
    "-m", "freqtrade", "hyperopt",
    "--config", (Join-Path $ft $Config),
    "--userdir", $userdir,
    "--strategy", $Strategy,
    "--hyperopt-loss", $Loss,
    "--timerange", $Timerange,
    "--epochs", "$Epochs",
    "--job-workers", "$Jobs"
)
$args += @("--spaces") + ($Spaces -split "\s+")

Write-Host "freqtrade $($args[1..($args.Length-1)] -join ' ')" -ForegroundColor DarkGray
& $py @args
