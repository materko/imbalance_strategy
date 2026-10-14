<#
.SYNOPSIS
    Pripraví obchodnú VM (Windows) jedným príkazom: Python prostredie, agent hubu s tokenom, automatické
    prihlásenie Windows, MetaTrader 5 a NinjaTrader 8 s kódom TradeBotu a úlohu „TradeBot agent“.

.DESCRIPTION
    Spúšťa sa z klonu repozitára (deploy\agent\bootstrap.ps1). Každý krok je idempotentný: čo už je hotové,
    preskočí, takže sa dá spustiť znova (napr. po doinštalovaní NT). Kroky:

      1. Python prostredie (.venv) — deploy\freqtrade\scripts\setup.ps1 -NoTests, keď .venv chýba
      2. agent hubu — tester\agent.json (python -m tester.hub setup … --no-accept --send), keď je -HubUrl/-Token
      3. automatické prihlásenie Windows (Sysinternals Autologon, heslo v LSA, nie v registri čitateľne) —
         s -AutologonPassword; bez neho sa len skontroluje a vypíše, či je zapnuté
      4. MetaTrader 5 — s -Mt5Installer (URL alebo cesta k mt5setup.exe brokera, inštaluje sa potichu `/auto`),
         prvý štart terminálu (vznikne dátový adresár), potom `python -m tradebot.adapters.mt5 install`
      5. NinjaTrader 8 — s -NtInstaller (.msi potichu `msiexec /qn`, .exe s `/quiet`), potom
         `python -m tradebot.adapters.ninjatrader install` (+ `--compile`, keď NT beží a je prihlásený)
      6. úloha „TradeBot agent“ (install-agent.ps1): agent pri prihlásení + strážca každých 5 minút

    Čo ostáva človeku (raz, nedá sa za neho): založiť účet u brokera / prop firmy, prvé prihlásenie do NT
    konta so zaškrtnutým „Remember“ a pripojenie brokera v NT (Connections). Všetko ostatné — štart a reštart
    terminálov, Log In v NT, nasadenie stratégií, aktualizácia kódu — robí agent sám (docs/MT5.md,
    docs/NINJATRADER.md, docs/LIVE.md).

    Neoverené na čistej VM: tichá inštalácia MT5/NT a Autologon. Kroky, ktoré potrebujú správcu (Autologon,
    inštalácie), si práva vypýtajú — skript spusti v PowerShelli ako správca, alebo ich preskoč.

.PARAMETER HubUrl
    Adresa hubu (napr. https://hub.example.com:8790).

.PARAMETER Token
    Token agenta — vygeneruje ho webapp na karte Hub (z hlavného tokenu) alebo `python -m tester.hub token add <meno>`.

.PARAMETER Name
    Meno stroja pre hub (predvolene názov počítača).

.PARAMETER AutologonPassword
    Heslo používateľa Windows pre automatické prihlásenie po reštarte (SecureString). Bez neho sa krok len skontroluje.

.PARAMETER Mt5Installer
    URL alebo cesta k inštalátoru MetaTrader 5 brokera (mt5setup.exe); bez neho sa MT5 neinštaluje.

.PARAMETER NtInstaller
    Cesta alebo URL k inštalátoru NinjaTrader 8 (.msi alebo .exe); bez neho sa NT neinštaluje.

.EXAMPLE
    .\deploy\agent\bootstrap.ps1 -HubUrl https://hub:8790 -Token abc… -AutologonPassword (Read-Host -AsSecureString) `
        -Mt5Installer https://download.mql5.com/cdn/web/ftmo.s.r.o/mt5/ftmo5setup.exe

.EXAMPLE
    .\deploy\agent\bootstrap.ps1 -WhatIf      # len ukáže, čo by spravil
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$HubUrl,
    [string]$Token,
    [string]$Name = $env:COMPUTERNAME,
    [System.Security.SecureString]$AutologonPassword,
    [string]$Mt5Installer,
    [string]$NtInstaller,
    [switch]$SkipAgentTask
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $repo ".venv\Scripts\python.exe"
$config = Join-Path $repo "tester\agent.json"
$downloads = Join-Path $repo "tester\live\bootstrap"
$todo = New-Object System.Collections.Generic.List[string]

function Step([string]$text) { Write-Host ""; Write-Host "== $text" -ForegroundColor Cyan }
function Ok([string]$text) { Write-Host "   OK: $text" -ForegroundColor Green }
function Skip([string]$text) { Write-Host "   -- $text" -ForegroundColor DarkGray }
function Todo([string]$text) { Write-Host "   !! $text" -ForegroundColor Yellow; $todo.Add($text) }

function Test-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    return (New-Object Security.Principal.WindowsPrincipal $id).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# URL sa stiahne do tester\live\bootstrap (gitignored), cesta sa vráti, ako je
function Get-Installer([string]$source) {
    if ($source -match '^https?://') {
        if (-not (Test-Path $downloads)) { New-Item -ItemType Directory -Force $downloads | Out-Null }
        $file = Join-Path $downloads ([IO.Path]::GetFileName(([Uri]$source).AbsolutePath))
        if (-not (Test-Path $file)) {
            Write-Host "   sťahujem $source"
            Invoke-WebRequest -Uri $source -OutFile $file -UseBasicParsing
        }
        return $file
    }
    if (-not (Test-Path $source)) { throw "inštalátor $source neexistuje" }
    return (Resolve-Path $source).Path
}

function Find-Mt5Terminal {
    foreach ($root in @($env:ProgramFiles, ${env:ProgramFiles(x86)})) {
        if (-not $root) { continue }
        $found = Get-ChildItem -Path $root -Filter terminal64.exe -Recurse -Depth 2 -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) { return $found.FullName }
    }
    return $null
}

# dátový adresár terminálu (%APPDATA%\MetaQuotes\Terminal\<hash>, origin.txt ukazuje na inštaláciu)
function Find-Mt5DataDir([string]$exe) {
    $base = Join-Path $env:APPDATA "MetaQuotes\Terminal"
    if (-not (Test-Path $base)) { return $null }
    foreach ($d in Get-ChildItem $base -Directory) {
        $origin = Join-Path $d.FullName "origin.txt"
        if ((Test-Path $origin) -and (([IO.File]::ReadAllText($origin)).Trim() -eq (Split-Path $exe -Parent))) { return $d.FullName }
    }
    return $null
}

function Find-NtExe {
    foreach ($root in @($env:ProgramFiles, ${env:ProgramFiles(x86)})) {
        if ($root -and (Test-Path (Join-Path $root "NinjaTrader 8\bin\NinjaTrader.exe"))) { return (Join-Path $root "NinjaTrader 8\bin\NinjaTrader.exe") }
    }
    return $null
}

# ---------------------------------------------------------------------------------------------- #
Step "1/6 Python prostredie (.venv)"
if (Test-Path $python) { Skip ".venv už je ($python)" }
elseif ($PSCmdlet.ShouldProcess(".venv", "setup.ps1 -NoTests")) {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            Write-Host "   Python chýba — inštalujem cez winget (Python 3.12)"
            winget install --id Python.Python.3.12 -e --silent --accept-package-agreements --accept-source-agreements
            $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
        } else { throw "Python chýba a winget nie je — nainštaluj Python 3.12 a spusti znova" }
    }
    & (Join-Path $repo "deploy\freqtrade\scripts\setup.ps1") -NoTests
    Ok ".venv postavené"
}

# ---------------------------------------------------------------------------------------------- #
Step "2/6 Agent hubu (tester\agent.json)"
if ($HubUrl -or $Token) {
    if (-not ($HubUrl -and $Token)) { throw "agent potrebuje -HubUrl aj -Token" }
    if ($PSCmdlet.ShouldProcess($config, "tester.hub setup --name $Name --hub-url $HubUrl --no-accept --send")) {
        & $python -m tester.hub setup --name $Name --hub-url $HubUrl --token $Token --no-accept --send
        if ($LASTEXITCODE -ne 0) { throw "tester.hub setup zlyhal" }
        Ok "agent $Name -> $HubUrl"
    }
} elseif (Test-Path $config) { Skip "agent.json už je (zmena: -HubUrl … -Token …)" }
else { Todo "agent nie je nastavený: spusti znova s -HubUrl a -Token (token z webapp, karta Hub)" }

# ---------------------------------------------------------------------------------------------- #
Step "3/6 Automatické prihlásenie Windows (po reštarte VM)"
$winlogon = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
$auto = (Get-ItemProperty $winlogon -ErrorAction SilentlyContinue).AutoAdminLogon
if ($AutologonPassword) {
    if (-not (Test-Admin)) { throw "Autologon potrebuje správcu — spusti PowerShell ako správca" }
    if ($PSCmdlet.ShouldProcess("$env:USERDOMAIN\$env:USERNAME", "Sysinternals Autologon (heslo v LSA)")) {
        $tool = Get-Installer "https://live.sysinternals.com/Autologon64.exe"
        $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($AutologonPassword))
        try { & $tool $env:USERNAME $env:USERDOMAIN $plain /accepteula | Out-Null } finally { $plain = $null }
        Ok "automatické prihlásenie $env:USERDOMAIN\$env:USERNAME zapnuté"
    }
} elseif ($auto -eq "1") { Skip "automatické prihlásenie je zapnuté" }
else { Todo "automatické prihlásenie Windows nie je zapnuté — po reštarte VM nič nenabehne (spusti znova s -AutologonPassword)" }

# ---------------------------------------------------------------------------------------------- #
Step "4/6 MetaTrader 5"
$mt5 = Find-Mt5Terminal
if (-not $mt5 -and $Mt5Installer) {
    if ($PSCmdlet.ShouldProcess($Mt5Installer, "tichá inštalácia MT5 (/auto)")) {
        $setup = Get-Installer $Mt5Installer
        Start-Process -FilePath $setup -ArgumentList "/auto" -Wait
        $mt5 = Find-Mt5Terminal
        if (-not $mt5) { throw "po inštalácii sa terminal64.exe nenašiel v Program Files" }
        Ok "MT5 nainštalovaný: $mt5"
    }
}
if ($mt5) {
    $data = Find-Mt5DataDir $mt5
    if (-not $data -and $PSCmdlet.ShouldProcess($mt5, "prvý štart (vznikne dátový adresár)")) {
        $p = Start-Process -FilePath $mt5 -PassThru
        for ($i = 0; $i -lt 60 -and -not $data; $i++) { Start-Sleep 2; $data = Find-Mt5DataDir $mt5 }
        Stop-Process -Id $p.Id -ErrorAction SilentlyContinue
        if (-not $data) { throw "terminál nevytvoril dátový adresár do 2 minút" }
    }
    if ($data -and $PSCmdlet.ShouldProcess($data, "python -m tradebot.adapters.mt5 install")) {
        & $python -m tradebot.adapters.mt5 install --mt5-dir (Join-Path $data "MQL5")
        if ($LASTEXITCODE -ne 0) { throw "tradebot.adapters.mt5 install zlyhal" }
        Ok "TradeBot v MT5 ($data)"
    }
    Todo "MT5 účet: pridaj ho vo webapp (karta Live → účet s loginom, serverom a heslom) — prihlási ho agent"
} else { Skip "MT5 nie je (inštalácia: -Mt5Installer <URL mt5setup.exe brokera>)" }

# ---------------------------------------------------------------------------------------------- #
Step "5/6 NinjaTrader 8"
$nt = Find-NtExe
if (-not $nt -and $NtInstaller) {
    if (-not (Test-Admin)) { throw "inštalácia NT potrebuje správcu — spusti PowerShell ako správca" }
    if ($PSCmdlet.ShouldProcess($NtInstaller, "tichá inštalácia NinjaTrader 8")) {
        $setup = Get-Installer $NtInstaller
        if ($setup -match '\.msi$') { Start-Process msiexec.exe -ArgumentList "/i `"$setup`" /qn /norestart" -Wait }
        else { Start-Process -FilePath $setup -ArgumentList "/quiet /norestart" -Wait }
        $nt = Find-NtExe
        if (-not $nt) { throw "po inštalácii sa NinjaTrader.exe nenašiel (tichá inštalácia neprešla? spusti inštalátor ručne)" }
        Ok "NinjaTrader nainštalovaný: $nt"
    }
}
if ($nt) {
    $custom = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "NinjaTrader 8\bin\Custom"
    if (-not (Test-Path $custom)) {
        Todo "NinjaTrader: spusti ho raz, prihlás sa do NT konta so zaškrtnutým Remember a v Connections nastav pripojenie brokera; potom bootstrap spusti znova"
    } elseif ($PSCmdlet.ShouldProcess($custom, "python -m tradebot.adapters.ninjatrader install")) {
        $running = Get-Process NinjaTrader -ErrorAction SilentlyContinue
        $extra = @(); if ($running) { $extra = @("--compile") }
        & $python -m tradebot.adapters.ninjatrader install @extra
        if ($LASTEXITCODE -ne 0) { throw "tradebot.adapters.ninjatrader install zlyhal" }
        if ($running) { Ok "TradeBot v NT nakopírovaný a preložený (F5 v NinjaScript Editore)" }
        else { Ok "TradeBot v NT nakopírovaný; preklad urobí agent ('Aktualizovať kód'), keď NT beží" }
    }
} else { Skip "NinjaTrader nie je (inštalácia: -NtInstaller <cesta k .msi/.exe>)" }

# ---------------------------------------------------------------------------------------------- #
Step "6/6 Úloha 'TradeBot agent' (pri prihlásení + strážca každých 5 min)"
if ($SkipAgentTask) { Skip "-SkipAgentTask" }
elseif (-not (Test-Path $config)) { Skip "agent.json chýba — úloha sa registruje, až keď je agent nastavený" }
elseif ($PSCmdlet.ShouldProcess("TradeBot agent", "install-agent.ps1")) {
    & (Join-Path $PSScriptRoot "install-agent.ps1")
    Ok "agent beží a po reštarte nabehne sám"
}

# ---------------------------------------------------------------------------------------------- #
Write-Host ""
if ($todo.Count -eq 0) {
    Write-Host "Hotovo — stroj je pripravený. Stratégie nasadzuj vo webapp (karta Live → Nasadiť)." -ForegroundColor Green
} else {
    Write-Host "Hotovo s výnimkou toho, čo musí urobiť človek:" -ForegroundColor Yellow
    foreach ($t in $todo) { Write-Host "  - $t" }
}
