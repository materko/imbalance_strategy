<#
.SYNOPSIS
    Databento export (CME futures po kontraktoch) -> front-month 1m pre Tester aj MultiCharts.

.DESCRIPTION
    Obal nad `python -m tester.bento_import` z koreňa repozitára. Všetky
    prepínače idú ďalej nezmenené; bez parametrov vypíše nápovedu.
    Podrobne: docs/DATA.md.

.EXAMPLE
    .\bento-import.ps1 C:\bento\glbx-mdp3.ohlcv-1m.csv --symbol MNQ
.EXAMPLE
    .\bento-import.ps1 C:\bento\glbx-mdp3.ohlcv-1m.csv --symbol MNQ --from 2020-01-01
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
    & $py -m tester.bento_import --help
} else {
    & $py -m tester.bento_import @Args
}
exit $LASTEXITCODE
