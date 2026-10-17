<#
.SYNOPSIS
    Zaregistruje agenta hubu (`python -m tester.hub agent`) ako naplánovanú úlohu pri prihlásení.

.DESCRIPTION
    Obchodná VM (NinjaTrader, MetaTrader 5) je desktopové prostredie bez ľudí: agent musí bežať
    v prihlásenej používateľskej relácii (spúšťa terminály, píše do Documents a %APPDATA%, heslá
    drží cez DPAPI používateľa), nie ako služba v session 0. Preto naplánovaná úloha „pri
    prihlásení“ používateľa. Beží bez okna (conhost --headless, okno sa nedá omylom zavrieť)
    a každých 5 minút ju spustí strážca: run-agent.ps1 agenta naštartuje, len keď nebeží
    (aj po zavretí, páde či reštarte po git pull). Windows musí mať zapnuté automatické
    prihlásenie toho istého používateľa (viď README.md).

    Predpokladá hotový klon s .venv (setup.ps1) a tester/agent.json (python -m tester.hub setup …);
    doinštaluje len závislosti obchodného stroja (extra `live` = pywinauto na preklad NinjaTraderu
    bez človeka), keď v .venv chýbajú. Opakované spustenie úlohu prepíše.

.PARAMETER TaskName
    Názov úlohy (predvolene „TradeBot agent“).

.PARAMETER NoStart
    Úlohu len zaregistruje, nespustí ju hneď.

.EXAMPLE
    .\deploy\agent\install-agent.ps1
    .\deploy\agent\install-agent.ps1 -WhatIf     # len ukáže, čo by zaregistroval
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$TaskName = "TradeBot agent",
    [switch]$NoStart
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $repo ".venv\Scripts\python.exe"
$config = Join-Path $repo "tester\agent.json"
$logDir = Join-Path $repo "tester\live"
$log = Join-Path $logDir "agent.log"

if (-not (Test-Path $python)) { throw "Chýba $python — najprv .\deploy\freqtrade\scripts\setup.ps1" }
if (-not (Test-Path $config)) { throw "Chýba $config — najprv .venv\Scripts\python.exe -m tester.hub setup --name <stroj> --hub-url … --token … --role live --send" }
# Obchodný stroj nepočíta backtesty pre hub (docs/HUB.md „Druhy agentov“) — rola live v configu.
$role = (Get-Content $config -Raw -Encoding UTF8 | ConvertFrom-Json).role
if ($role -ne "live") {
    if ($PSCmdlet.ShouldProcess($config, "nastaviť rolu live (stroj nebude počítať pre hub)")) {
        & $python -m tester.hub setup --role live
        if ($LASTEXITCODE -ne 0) { throw "tester.hub setup --role live zlyhal" }
    }
}
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force $logDir | Out-Null }

# extra `live` (pywinauto): aktualizácia kódu z webapp prekladá NinjaTrader F5 v NinjaScript Editore
& $python -c "import pywinauto" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Inštalujem závislosti obchodného stroja (pywinauto)..."
    & $python -m pip install --disable-pip-version-check -q "pywinauto>=0.6.8"
    if ($LASTEXITCODE -ne 0) { throw "pip install pywinauto zlyhal" }
}

# run-agent.ps1 spustí agenta, len keď nebeží (výstup do logu presmeruje sám);
# conhost --headless = bez okna v relácii používateľa
$runner = Join-Path $PSScriptRoot "run-agent.ps1"
$cmdLine = "--headless powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$runner`""
$user = "$env:USERDOMAIN\$env:USERNAME"

$action = New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\conhost.exe" -Argument $cmdLine -WorkingDirectory $repo
# pri prihlásení + strážca každých 5 minút (beží len v prihlásenej relácii, IgnoreNew = nikdy dve naraz)
$trigger = @(
    (New-ScheduledTaskTrigger -AtLogOn -User $user),
    (New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5))
)
$settings = New-ScheduledTaskSettingsSet `
    -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries
# Interactive = beží v prihlásenej relácii (vidí okná NT/MT5), bez uloženého hesla
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited

if ($PSCmdlet.ShouldProcess($TaskName, "Register-ScheduledTask ($user, pri prihlásení + každých 5 min, conhost $cmdLine)")) {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
        -Principal $principal -Force | Out-Null
    Write-Host "OK: úloha '$TaskName' zaregistrovaná pre $user (pri prihlásení + strážca každých 5 min, bez okna)"
    Write-Host "    príkaz: conhost.exe $cmdLine"
    Write-Host "    log:    $log"
    if (-not $NoStart) {
        Start-ScheduledTask -TaskName $TaskName
        Write-Host "    spustená teraz; stav: Get-ScheduledTask '$TaskName' | Get-ScheduledTaskInfo"
    }
}
