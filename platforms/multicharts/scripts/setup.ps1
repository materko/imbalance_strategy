<#
.SYNOPSIS
    Sprístupní balík `tradebot` Pythonu, ktorý používa MultiCharts.

.DESCRIPTION
    POZOR - MultiCharts NEPOUŽÍVA virtuálne prostredie. Volá jednu konkrétnu
    globálnu 64-bitovú inštaláciu CPythonu cez Python.NET. Preto sa `tradebot`
    NEDÁ nainštalovať do .venv, ktoré používa Freqtrade - musí ísť do toho
    globálneho interpretera.

    Skript:
      1. overí, že cieľový Python je 64-bitový,
      2. nainštaluje `tradebot` v editovateľnom režime (pip install -e),
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

Write-Host "Instalujem tradebot do globalneho Pythonu (editovatelne)..."
& $exe -m pip uninstall -y ibs *> $null   # stary nazov balika (pred premenovanim na tradebot)
& $exe -m pip install -e $repo
if ($LASTEXITCODE -ne 0) { throw "pip install -e zlyhalo" }

Write-Host "Overujem import..."
& $exe -c @"
import importlib
from tradebot.core import load_profile, list_profiles
from tradebot.strategies import STRATEGIES
from tradebot.adapters.multicharts import MCRunner, MCDrawSink
for key, spec in STRATEGIES.items():
    print(key, '- profily:', list_profiles(key))
    cfg, inst = load_profile(f'{key}/{spec.default_profile}')
    runner = MCRunner(cfg, inst, 3, spec=spec)
    cls = getattr(importlib.import_module(f'tradebot.strategies.{key}.multicharts'), spec.multicharts_class)
    print(' ', spec.default_profile, '->', inst.symbol, 'tick', inst.tick_size, '| studia', cls.__name__, '| sablona', spec.multicharts_template)
print('adapter: MCRunner + MCDrawSink OK')
"@
if ($LASTEXITCODE -ne 0) { throw "import tradebot zlyhal" }

Write-Host ""
Write-Host "Hotovo. V MultiCharts:" -ForegroundColor Green
Write-Host "  1. Otvor PowerLanguage .NET Editor"
Write-Host "  2. File -> New -> Signal, jazyk: Python.NET"
Write-Host "  3. Vloz obsah sablony platforms\multicharts\<Strategia>_Signal.py (IBS: IBS_Signal.py)"
Write-Host "  4. Na graf pridaj DVE serie: Data1 = graf TF, Data2 = informativny TF strategie (IBS: 5m)"
Write-Host "     Bez Data2 nevznikne ani jedna SD zona."
Write-Host ""
Write-Host "Ak MultiCharts hlasi, ze modul nenasiel, ma nastaveny INY Python."
Write-Host "Skontroluj jeho nastavenie a spusti tento skript s -Python <cesta>."
