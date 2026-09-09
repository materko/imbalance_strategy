# Hyperopt s priestorom, ktory strategia odporucuje (jej `hyperopt_cls.SUGGESTED`).
# Vlastny priestor sa zadava priamo prikazom, nie tymto obalom:
#
#   PY -m tester.webapp.cli hyperopt --param rrRatio=2:8:0.5 --param slLookback=5:40:1 `
#      --goal break_even --min-trades 15 --timerange 20250904-20260904
#
# Podrobnosti a ako nastavit hranice: docs/HYPEROPT.md
#
#   .\deploy\freqtrade\scripts\hyperopt.ps1 20250904-20260904 200
param(
    [Parameter(Mandatory = $true)][string]$Timerange,
    [int]$Epochs = 200,
    [string]$Goal = "break_even"
)
$ErrorActionPreference = "Stop"

$repo = (Resolve-Path "$PSScriptRoot\..\..\..").Path
$py = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "chyba .venv - spusti deploy\freqtrade\scripts\setup.ps1" }

Set-Location $repo
& $py -m tester.webapp.cli hyperopt --suggested `
    --timerange $Timerange --epochs $Epochs --goal $Goal `
    --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json `
    --note "hyperopt: odporucany priestor, okno $Timerange"
exit $LASTEXITCODE
