<#
.SYNOPSIS
    Surové Dukascopy dáta -> dáta pre Tester (webapp) aj pre MultiCharts (QuoteManager).

.DESCRIPTION
    Obal nad `python -m tradebot.tools.dukas_import` z koreňa repozitára. Všetky
    prepínače idú ďalej nezmenené; bez parametrov vypíše nápovedu.
    Podrobne: docs/DATA.md.

.EXAMPLE
    .\dukas-import.ps1 C:\dukas\NAS100_M1_10Y.csv --symbol NAS100
.EXAMPLE
    .\dukas-import.ps1 C:\dukas\NAS100_M1_10Y.csv --symbol NAS100 --target multicharts --from 2021-01-01
.EXAMPLE
    .\dukas-import.ps1 C:\dukas\EURUSD_M1.csv --symbol EURUSD --point-value 100000 --tick 0.00001
#>
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot
$py = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    throw "Chyba .venv - spusti najprv .\platforms\freqtrade\scripts\setup.ps1"
}

Set-Location $repo
if (-not $Args -or $Args.Count -eq 0) {
    & $py -m tradebot.tools.dukas_import --help
} else {
    & $py -m tradebot.tools.dukas_import @Args
}
exit $LASTEXITCODE
