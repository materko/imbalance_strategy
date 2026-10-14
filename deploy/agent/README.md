# Agent hubu na obchodnej VM (Windows, bez ľudí)

Agent je jeden proces na stroj: číta spool NinjaTradera aj MetaTradera 5, posiela ho na hub a
zosúlaďuje nasadenia (spúšťa terminály, píše profily a control súbory) — [docs/LIVE.md](../../docs/LIVE.md).
NT aj MT5 sú desktopové aplikácie, preto agent **nebeží ako služba ani v Dockeri**, ale v prihlásenej
relácii používateľa ako naplánovaná úloha „pri prihlásení“.

## Príprava VM jedným príkazom

V PowerShelli **ako správca**, z klonu repozitára (token agenta vygeneruje webapp na karte Hub):

```powershell
.\deploy\agent\bootstrap.ps1 -HubUrl https://hub:8790 -Token <token agenta> `
    -AutologonPassword (Read-Host -AsSecureString "heslo Windows") `
    -Mt5Installer <URL mt5setup.exe brokera> -NtInstaller <cesta k inštalátoru NT>
```

Spraví kroky 1, 3–7 nižšie (Python prostredie, agent, Autologon cez Sysinternals — heslo v LSA, tichá inštalácia
MT5 a NT, kód TradeBotu do oboch, úloha „TradeBot agent“); čo je hotové, preskočí, takže sa dá spustiť znova
(napr. po prvom prihlásení do NT). `-WhatIf` len ukáže, čo by spravil. Na konci vypíše, čo ostáva človeku:
prvé prihlásenie do NT konta s „Remember“ a pripojenie brokera v NT (Connections), MT5 účet vo webapp.
Tichá inštalácia MT5/NT a Autologon sú **neoverené na čistej VM** — keď niektorý krok zlyhá, urob ho ručne podľa
postupu nižšie a bootstrap spusti znova.

## Príprava VM (raz, ručne)

1. **Automatické prihlásenie** používateľa Windows (napr. `netplwiz` → zrušiť „Používatelia musia zadať
   meno a heslo“; alebo Sysinternals Autologon). Bez toho po reštarte VM nikto nenabehne.
2. **NinjaTrader 8**: nainštalovať, prihlásiť sa do NT konta so zapamätaným prihlásením, v *Connections*
   nakonfigurovať pripojenie brokera (heslo si NT drží sám; z kódu sa nové pripojenie založiť nedá).
   Po reštarte VM agent NT spustí a tlačidlo **Log In** stlačí sám (heslo musí byť v NT zapamätané —
   docs/NINJATRADER.md); človek sa prihlasuje len raz.
3. **MetaTrader 5**: nainštalovať terminál brokera a raz sa prihlásiť (aby existoval `servers.dat`);
   ďalšie účty už pridá agent z hubu (ini s loginom, heslo cez DPAPI).
4. **Klon repozitára** + Python prostredie: `.\deploy\freqtrade\scripts\setup.ps1`.
5. **Kód do platforiem**: `.venv\Scripts\python.exe -m tradebot.adapters.mt5 install` a
   `… -m tradebot.adapters.ninjatrader install` (v NT potom F5 v NinjaScript Editore — prvýkrát ručne).
6. **Agent**: `.venv\Scripts\python.exe -m tester.hub setup --name <meno-stroja> --hub-url https://hub:8790 --token <token agenta> --no-accept --send`
   (`--no-accept` = stroj nepočíta backtesty pre hub, len obchoduje; `tester/agent.json` je gitignored).
   Token vydá správca hubu: `python -m tester.hub token add <meno-stroja>`.

## Registrácia úlohy

```powershell
.\deploy\agent\install-agent.ps1          # -WhatIf len ukáže, čo spraví
```

Úloha „TradeBot agent“ sa spustí pri prihlásení používateľa a potom **každých 5 minút** (strážca).
Spúšťa `deploy\agent\run-agent.ps1` **bez okna** (`conhost --headless`), ktorý agenta naštartuje,
len keď ešte nebeží — po zavretí, páde aj inom skončení je agent späť do 5 minút a druhá kópia
nevznikne. Výstup ide do `tester\live\agent.log`. Stav: `Get-ScheduledTask 'TradeBot agent' | Get-ScheduledTaskInfo`.
Odstránenie: `.\deploy\agent\uninstall-agent.ps1`.

Agent sa po `git pull` (aktualizácia kódu z hubu) sám reštartuje (`os.execv`). Na Windows to spustí
nový proces a pôvodný skončí, takže úloha prejde do stavu „Ready“, ale agent beží ďalej — strážca
ho nájde a nič nespúšťa. Agent preto hľadaj podľa procesu, nie podľa stavu úlohy:
`Get-CimInstance Win32_Process -Filter "Name='python.exe'" | ? CommandLine -match 'tester.hub agent'`.

## Kontrola, že to žije

- na VM: `.venv\Scripts\python.exe -m tradebot.live status` (spool, kurzor), `Get-Content tester\live\agent.log -Tail 20`
- na hube / vo webapp: karta **Hub** (agent online, `drivers: mt5, ninjatrader`) a karta **Live**
  (inštancie, nasadenia, stav kódu).
