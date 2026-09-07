# MultiCharts vetva: študia, dáta, emulátor

MultiCharts pokrýva to, čo Freqtrade nevie: futures (MNQ), akcie, forex a CFD z Dukascopy.
Beží **len na Windows** a **nedá sa kontajnerizovať** — je to desktop aplikácia s GUI
a licenciou viazanou na stroj. Na macOS aj v Dockeri sa dá robiť jadro (`tradebot/`), testy
aj celá Freqtrade vetva ([FREQTRADE.md](FREQTRADE.md)); samotná študia potrebuje Windows.

Sú tri spôsoby, ako tú istú logiku spustiť na MultiCharts dátach — od najľahšieho:

| kde | čo to je | treba na to |
|---|---|---|
| **Tester (webapp)** | „burza" MultiCharts: emulátor `MCRunner` nad 1m sviečkami z archívu | nič navyše, beží aj na Macu |
| **offline simulátor** | `scan_trades --csv` nad surovým Dukascopy exportom | nič navyše |
| **MultiCharts študia** | skutočný MultiCharts, referencia pre adaptér | Windows + licencia |

Na **hyperopt** (a FreqAI) sa ten istý symbol dá prehnať aj cez Freqtrade —
[FREQTRADE.md §G](FREQTRADE.md). Signály sú rovnaké, fill model nie, takže výsledok
z hyperoptu treba overiť emulátorom.

---

## A. Inštalácia študie (Windows)

```powershell
.\platforms\multicharts\scripts\setup.ps1
.\platforms\multicharts\scripts\setup.ps1 -Python "C:\Python313\python.exe"
```

MultiCharts **nepoužíva virtuálne prostredie** — volá jednu konkrétnu globálnu 64-bitovú
inštaláciu CPythonu cez pythonnet. Preto sa `tradebot` musí nainštalovať do nej, nie do `.venv`.
Skript to overí (odmietne venv aj 32-bit) a na záver skúsi načítať profil. Ktorý Python
to je: MultiCharts x Python (od verzie 15) ho hľadá cez `where python`, teda prvý v PATH,
prípadne cez premennú `PYTHONNET_PYDLL`. **Po inštalácii MultiCharts reštartuj** — StudyServer
si Python drží od štartu a nový balík inak nevidí („No module named tradebot").
Ak PowerShell odmietne skript spustiť:
`powershell -ExecutionPolicy Bypass -File .\platforms\multicharts\scripts\setup.ps1`.

Potom v MultiCharts:

1. **PowerLanguage .NET Editor**
2. **File → New → Signal**, jazyk **Python**, názov **rovnaký ako trieda v šablóne**
   (`IBS`, `DemoBreakout`) — MultiCharts hľadá triedu podľa mena študie
3. Vlož obsah šablóny z [`platforms/multicharts/`](../platforms/multicharts)
   (`IBS_Signal.py`, `DemoBreakout_Signal.py`) — trieda, ktorá len deleguje na balík
   `tradebot` (MultiCharts vyžaduje metódy `Create`/`CalcBar` priamo v triede študie,
   zdedené nevidí); profil nastav v `PROFILE` (názov alebo cesta). Skompiluj (F7).
4. Na graf pridaj **Data1** = graf TF (napr. MNQ 3m) a, ak stratégia potrebuje informatívny
   TF, **Data2** = ten TF (IBS: `zoneDetectionTF`, štandardne 5m; demo stratégia Data2 nemá).
   Graf musí mať **Time Zone: Exchange** a burza symbolu pásmo GMT — adaptér berie čas
   baru ako UTC.
5. **Insert → Signal** na graf, potom **View → Output**: študia vypíše profil a prvý bar
   (`prvy bar grafu Time[0]=… -> otvorenie …`), z ktorého vidno, či pásmo a razenie baru sedia.
   Obchody: View → Strategy Performance Report → List of Trades.

Profil sa prepína cez `TRADEBOT_PROFILE` (predvolene default profil stratégie, IBS
`multicharts_mnq_3m`) alebo natvrdo cez `PROFILE` v šablóne, rovnako ako vo Freqtrade.
Ordery študie sa volajú `tb_sl`, `tb_tp` a `tb_session_end`.

> **IBS bez Data2 nevytvorí ani jednu SD zónu.** Študia to napíše do Output okna,
> ale inak beží ďalej — je to ľahké prehliadnuť.

> **Optimalizáciu parametrov nerob v MultiCharts** — Python tam beží pod GIL a je výrazne
> pomalší než PowerLanguage/C#. Laď cez Freqtrade `hyperopt` a výsledok len prenes.

---

## B. Dáta do QuoteManagera

MultiCharts študia číta bary z grafu, teda z QuoteManagera — CSV sa doň musí najprv
importovať. Prevod surového Dukascopy exportu (vypchávka, čas baru, mierka, objem) rieši
jeden príkaz, popísaný v [DATA.md §B](DATA.md):

```powershell
.\dukas-import.ps1 C:\dukas\NAS100_M1_10Y.csv --symbol NAS100 --target multicharts
# -> C:\dukas\NAS100_M1_mc.csv, hlavička Date,Time,Open,High,Low,Close,Volume
```

Potom v QuoteManageri:

1. **Add Symbol → Manually**: Data Source ten, čo ponúka graf; Exchange (napr. `Dukascopy`)
   s pásmom **GMT bez letného času**; Category podľa trhu; **Price Scale 1/1000,
   Min. Movement 1** (dáta majú tri desatinné miesta); **Big Point Value 1** (1 USD za bod
   na jednotku CFD — over si to v obchodných podmienkach a daj tú istú hodnotu do
   `--point-value` pri importe); session template 24/7 alebo podľa trhu.
   Adaptér berie čas grafu ako UTC, takže iné pásmo symbolu posunie seansy.
2. **Import Data → ASCII** na tom symbole: Time Zone **GMT**, Field **Trade**, rozlíšenie
   **1 Minute**, stĺpce podľa hlavičky.
   Kontrola po importe: Edit Data v pásme GMT, nedeľa 5. 1. 2025 — prvý bar **23:01**
   (trh otvára 18:00 New York, v zime 23:00 UTC, v lete 22:00 UTC; bar je razený
   zatvorením, preto :01). Graf s Time Zone Exchange ukáže to isté.
3. Na graf Data1 = 3m, Data2 = 5m (obe si MultiCharts poskladá z 1m), profil
   `TRADEBOT_PROFILE=docs/profily_archiv/ibs/nas100_dukas_3m.json`.

---

## C. Čo robí adaptér

| súbor | zodpovednosť |
|---|---|
| [`adapters/multicharts/runner.py`](../tradebot/adapters/multicharts/runner.py) | `MCRunner`: prevedie engine stratégie cez `CalcBar`, drží živé ordre a informatívne okno (feeder zo `StrategySpec`) |
| [`adapters/multicharts/signal.py`](../tradebot/adapters/multicharts/signal.py) | `TradebotSignal` — jediný súbor, ktorý sa dotýka PowerLanguage API; stratégia je podtrieda (`tradebot/strategies/<key>/multicharts.py`) |
| [`adapters/multicharts/drawing.py`](../tradebot/adapters/multicharts/drawing.py) | `DrawCommand` → `DrwRectangle` / `DrwTrendLine` / `DrwText` |
| [`adapters/multicharts/emulator.py`](../tradebot/adapters/multicharts/emulator.py) | broker podľa MultiCharts pre webapp — beh bez MultiCharts (§E) |
| [`adapters/multicharts/htf_csv.py`](../tradebot/adapters/multicharts/htf_csv.py) | informatívny TF zo súboru, keď Data2 nejde (§D) |

Runner, emulátor a kreslenie sú zámerne bez závislosti na PowerLanguage, takže sa testujú
na obyčajnom Pythone (`tradebot/tests/test_multicharts*.py`) — vrátane testu, že MultiCharts
runner dá z tých istých barov tie isté zóny ako Freqtrade.

Rozhranie MultiCharts x Python (nie C# `SignalObject`): študia je obyčajná trieda,
MultiCharts volá `Create(ctx)`, `StartCalc`, `CalcBar`, `Destroy`; ordre musia vzniknúť
v `Create`, preto má `TradebotSignal` pevný pool vstupných orderov (`ENTRY_POOL`, 4 na
stranu) a meno konkrétneho orderu (`LONG_<uid>`) dosadí pri každom `Send`.

### Tri rozdiely oproti Pine, ktoré treba vedieť

**Bar je razený časom zatvorenia.** `Bars.Time[0]` 3m baru 10:00–10:03 je 10:03; jadro
pracuje s časom otvorenia ako Pine, takže adaptér odpočíta rozlíšenie série
(`TradebotSignal._bar`). Bez toho by seansy aj okno Data2 sedeli o bar neskôr. Kreslenie ide
opačným smerom: objekty jadra majú x = otvorenie baru, plátno pripočíta TF, aby sedeli na bary.

**Ordre platia len jeden bar.** V Pine `strategy.entry` položí order, ktorý leží, kým
ho niekto nezruší. V MultiCharts platí order len na nasledujúci bar — runner ich preto
posiela **znova každý bar**, kým sú živé.

**MultiCharts nepozná priehľadnosť.** Pine kreslí zóny s výplňou na 85 % priehľadnosti;
`DrwRectangle` má len plnú farbu, takže sa alfa zahodí a graf bude sýtejší než
v TradingView. Pozadie seansy (`bgcolor()`) sa nekreslí vôbec — nemá náprotivok.

---

## D. Známe problémy bety MultiCharts x Python

> **Data2 v bete (15.0.27717) nefunguje**: `BarsOfData(2)` padá v
> `PriceSeriesImpl.ReBind`, hoci `MaxDataStream` hlási 2 série a Data1 ide. Adaptér má
> preto zálohu: v šablóne nastav `HTF_CSV` na 1m Dukascopy CSV (alebo premennú
> prostredia `TRADEBOT_MC_HTF_CSV`) a informatívny TF sa poskladá zo súboru
> (`adapters/multicharts/htf_csv.py`, ~8 s pre desaťročný export). Sú to tie isté 5m bary,
> aké má QuoteManager aj offline simulátor. Ak Data2 jedného dňa pôjde, adaptér ju
> uprednostní a CSV sa nepoužije.

> **FPU výnimky.** Po prvom spracovanom obchode necháva MultiCharts vo vlákne študie
> odmaskované FPU výnimky (control word `0x00080007`: neplatná operácia a delenie nulou
> nie sú maskované). Python s tým nepočíta — prvé porovnanie s NaN zhodí CalcBar ako
> `System.ArithmeticException: Overflow or underflow…` bez Python tracebacku. Adaptér
> preto pri každom `CalcBar` volá `_controlfp` a masky vráti (`fpu_mask_exceptions`);
> v Output okne/logu to hlási riadok „FPU vynimky boli odmaskovane".

> **Obchod vnútri jedného baru.** Market vstup sa vyplní na otvorení ďalšieho baru a TP/SL
> môže trafiť ešte v tom istom bare — na close je pozícia nula. Runner to pozná
> z `TotalTrades` (`closed_trades`) a vyplnený order už neposiela znova; bez toho by sa
> ten istý market vstup opakoval každý bar.

> **Bar Magnifier neúčinkuje.** Zapnutie na 1 minútu (Strategy Properties → Backtesting)
> nezmenilo výsledok ani o cent — v logu `CreateDetailedSeries res_size=1` dostal rovnaký
> počet barov ako 3m graf, takže detailná séria sa zo symbolu pod Market Data Sim neberie
> z 1m dát QuoteManagera.

**Po každej zmene v `tradebot/` treba MultiCharts naozaj reštartovať**: `File → Exit`
nechá bežať `StudyServer.NET`, `tsServer` a ďalšie procesy, ktoré držia Python so starým
kódom:

```powershell
Get-Process MultiCharts64, tsServer, StudyServer.NET, TradingServer, ATCenterServer, PLEditor.NET | Stop-Process -Force
```

**MultiCharts nenájde modul `tradebot`** — má nastavený iný Python, než do ktorého sa
inštalovalo. Zisti ktorý a spusti `platforms\multicharts\scripts\setup.ps1 -Python <cesta>`.
Nikdy to nesmie byť `.venv`. Ak `pip install -e .` v globálnom Pythone hlási chýbajúce
oprávnenia: PowerShell ako správca, alebo `--user`.

---

## E. Beh bez MultiCharts

**Tester (webapp).** Webapp má „burzu" **MultiCharts**: 1m sviečky z Dukascopy ležia
v `platforms/multicharts/data/`, pár sa v ponuke volá ako v MultiCharts (`NAS100`) a beh
nejde cez Freqtrade, ale cez **emulátor** — ten istý `MCRunner`, ktorý beží v študii, plus
broker podľa MultiCharts (jedna pozícia, order platí na ďalší bar, market na otvorení,
limitka pri dotyku, SL/TP po 1m sviečkach, koniec seansy na close baru). Výsledok má
rovnaký tvar ako Freqtrade beh, história ich nerozlišuje; v `result.engine` je
`multicharts-emulator`. Dáta pripraví [DATA.md §B](DATA.md).

**Offline simulátor a párovanie so študiou.** Zoznam obchodov z posledného behu študie
sa dá vytiahnuť z jej logu (`%LOCALAPPDATA%\tradebot\multicharts.log`, premenná
`TRADEBOT_MC_LOG`; `[trace]` riadky = každý `Send` a zmena pozície, `[trade]` = uzavretý
obchod):

```bash
PY -m tradebot.tools.mc_log_trades --from 2025-01-01 --to 2025-01-31
PY -m tradebot.tools.scan_trades --csv C:/dukas/NAS100_M1_10Y.csv \
    --profile docs/profily_archiv/ibs/nas100_dukas_3m.json --from 2025-01-01 --to 2025-01-31
PY -m tradebot.tools.mc_compare --csv … --profile … --from … --to …
```

`mc_compare` oba zoznamy spáruje podľa vstupnej ceny a vypíše rozdiely — to je porovnanie
MultiCharts vs. jadro. Ako to dopadlo na NAS100 (a čo bolo treba opraviť):
[merania/NAS100_dukas_simulator_2026-09-06.md](merania/NAS100_dukas_simulator_2026-09-06.md).
Emulátor tam dal na januári 2025 +1 992 USD proti +1 991,66 USD z MultiCharts.
