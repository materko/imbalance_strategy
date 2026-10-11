<#
.SYNOPSIS
    Spustí agenta hubu (`python -m tester.hub agent`), ak ešte nebeží. Volá ho úloha „TradeBot agent“.

.DESCRIPTION
    Úloha sa spúšťa pri prihlásení a potom každých 5 minút (strážca). Keď agent beží, skript hneď
    skončí, takže nevznikne druhá kópia ani po `git pull`: agent sa vtedy reštartuje cez
    `os.execv`, čo na Windows spustí nový proces a pôvodný ukončí — úloha tým skončí, ale agent
    beží ďalej a strážca ho nájde. Výstup agenta ide do tester\live\agent.log (cez cmd, aby
    ostalo kódovanie ako doteraz).
#>
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $repo ".venv\Scripts\python.exe"
$log = Join-Path $repo "tester\live\agent.log"

$running = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'tester\.hub\s+agent' }
if ($running) { exit 0 }

Set-Location $repo
& cmd.exe /c "`"`"$python`" -m tester.hub agent >> `"$log`" 2>&1`""
exit $LASTEXITCODE
