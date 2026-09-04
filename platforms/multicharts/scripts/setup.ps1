<#
.SYNOPSIS
    Sprístupní balík `ibs` Pythonu, ktorý používa MultiCharts.

.DESCRIPTION
    POZOR - MultiCharts NEPOUŽÍVA virtuálne prostredie. Volá jednu konkrétnu
    globálnu 64-bitovú inštaláciu CPythonu cez Python.NET. Preto sa `ibs`
    NEDÁ nainštalovať do .venv, ktoré používa Freqtrade - musí ísť do toho
    globálneho interpretera.

    Skript:
      1. overí, že cieľový Python je 64-bitový,
      2. nainštaluje `ibs` v editovateľnom režime (pip install -e),
      3. overí, že sa dá naimportovať a načítať profil.

.PARAMETER Python
    Cesta k python.exe, ktorý má MultiCharts nastavený. Ak ho nezadáš, použije
    sa `python` z PATH - čo je väčšinou správne, lebo MultiCharts vyžaduje
    Python pridaný do PATH.

.EXAMPLE
    .\platforms\multicharts\scripts\setup.ps1
.EXAMPLE
    .\platforms\multicharts\scripts\setup.ps1 -Python "C:\Python313\python.exe"
#>
[CmdletBinding()]
param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path

$exe = (Get-Command $Python -ErrorAction SilentlyContinue).Source
if (-not $exe) { throw "Nenasiel som python '$Python'. Zadaj cestu cez -Python." }

Write-Host "Cielovy interpreter: $exe"

if ($exe -like "*\.venv\*") {
    throw "Toto je venv ($exe). MultiCharts potrebuje GLOBALNY Python - zadaj ho cez -Python."
}

$info = & $exe -c "import sys,struct;print(sys.version.split()[0]);print(struct.calcsize('P')*8)"
$ver, $bits = $info -split "`n" | ForEach-Object { $_.Trim() }
Write-Host "Verzia: $ver   architektura: ${bits}-bit"

if ($bits -ne "64") {
    throw "MultiCharts x64 potrebuje 64-bitovy Python, tento je ${bits}-bit."
}

Write-Host "Instalujem ibs do globalneho Pythonu (editovatelne)..."
& $exe -m pip install -e $repo
if ($LASTEXITCODE -ne 0) { throw "pip install -e zlyhalo" }

Write-Host "Overujem import..."
& $exe -c @"
from ibs.core import load_profile, list_profiles
print('profily:', list_profiles())
cfg, inst = load_profile('mnq_3m')
print('mnq_3m ->', inst.symbol, 'tick', inst.tick_size, 'point_value', inst.point_value)
"@
if ($LASTEXITCODE -ne 0) { throw "import ibs zlyhal" }

Write-Host ""
Write-Host "Hotovo. V MultiCharts:" -ForegroundColor Green
Write-Host "  1. Otvor PowerLanguage .NET Editor"
Write-Host "  2. File -> New -> Signal (alebo Indicator), jazyk: Python.NET"
Write-Host "  3. V kode uz mozes robit: from ibs.core import load_profile"
Write-Host ""
Write-Host "Ak MultiCharts hlasi, ze modul nenasiel, ma nastaveny INY Python."
Write-Host "Skontroluj jeho nastavenie a spusti tento skript s -Python <cesta>."
