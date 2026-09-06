<#
.SYNOPSIS
    Postaví Python prostredie pre Freqtrade vetvu portu.

.DESCRIPTION
    Vytvorí .venv v koreni repozitára, nainštaluje Freqtrade a náš balík `tradebot`
    v editovateľnom režime. Freqtrade beží v izolovanom venv - na rozdiel od
    MultiCharts, ktorý potrebuje globálny Python (viď platforms/multicharts/scripts/setup.ps1).

.EXAMPLE
    .\platforms\freqtrade\scripts\setup.ps1
#>
[CmdletBinding()]
param(
    [string]$Python = "python",
    [switch]$Recreate
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$venv = Join-Path $repo ".venv"

Write-Host "Repozitar: $repo"

if ($Recreate -and (Test-Path $venv)) {
    Write-Host "Mazem existujuci venv..."
    Remove-Item -Recurse -Force $venv
}

if (-not (Test-Path $venv)) {
    Write-Host "Vytvaram venv v $venv"
    & $Python -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw "python -m venv zlyhalo" }
}

$py = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Nenasiel som $py" }

Write-Host "Aktualizujem pip..."
& $py -m pip install --upgrade pip --quiet

Write-Host "Instalujem freqtrade (chvilu to trva)..."
& $py -m pip install freqtrade
if ($LASTEXITCODE -ne 0) { throw "instalacia freqtrade zlyhala" }

Write-Host "Instalujem lokalny balik tradebot (editovatelne)..."
& $py -m pip uninstall -y ibs *> $null   # stary nazov balika (pred premenovanim na tradebot)
& $py -m pip install -e "$repo[dev]"
if ($LASTEXITCODE -ne 0) { throw "instalacia tradebot zlyhala" }

Write-Host ""
& $py -m freqtrade --version
& $py -m pytest $repo -q

Write-Host ""
Write-Host "Hotovo. Dalsi krok:"
Write-Host "  .\platforms\freqtrade\scripts\download-data.ps1"
