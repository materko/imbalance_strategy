# Ako to celé spustiť

Tri spôsoby, podľa toho, čo práve robíš:

| Prostredie | Na čo | Platformy |
|---|---|---|
| **Docker** | server, CI, „nech to proste beží" | Windows / macOS / Linux |
| **Natívny venv** | vývoj Freqtrade vetvy | Windows / macOS / Linux |
| **Globálny Python** | MultiCharts | **len Windows** |

> **MultiCharts na macOS nebeží** a **nedá sa kontajnerizovať** — je to Windows desktop
> aplikácia s GUI a licenciou viazanou na stroj. Na Macu aj v Dockeri sa dá robiť jadro
> (`tradebot/`), testy a celá Freqtrade vetva; samotná MultiCharts študia potrebuje Windows.

---

## A. Docker

Všetko sa spúšťa z koreňa repozitára.

```bash
# testy jadra (vrátane parity s Pine súborom)
docker compose -f docker/docker-compose.yml run --rm tests

# stiahnutie dát
DAYS=60 docker compose -f docker/docker-compose.yml run --rm download
DAYS=60 docker compose -f docker/docker-compose.yml run --rm download-coinbase

# backtest
docker compose -f docker/docker-compose.yml run --rm backtest

# bot (toto sa nasadzuje na server)
docker compose -f docker/docker-compose.yml up -d freqtrade
docker compose -f docker/docker-compose.yml logs -f freqtrade
```

### Dva image

| Image | Základ | Na čo |
|---|---|---|
| `ibs-core` | `python:3.12-slim` | testy a CI. Jadro nemá závislosti mimo stdlib, takže je malý a beží aj na arm64 Macu. |
| `ibs-freqtrade` | `freqtradeorg/freqtrade:stable` | download, backtest, live bot |

Balík `tradebot` sa do Freqtrade image nedáva cez `pip`, ale cez `PYTHONPATH=/app`. Compose potom
mountuje `../ibs:/app/ibs:ro`, takže **zmeny v jadre sa prejavia bez rebuildu** — a image
funguje aj samostatne bez mountu. Build navyše na konci spustí sanity check profilov,
takže rozbitý config zhodí build, nie až server.

### Nasadenie na server

```bash
git clone <repo> && cd imbalance_strategy
cp .env.example .env          # ak potrebuješ API kľúče / TZ
docker compose -f docker/docker-compose.yml up -d --build freqtrade
```

- Bot má `restart: unless-stopped` a rotáciu logov (5 × 10 MB).
- REST API / FreqUI je naviazané na `127.0.0.1:8080` — **zámerne nie na 0.0.0.0**.
  Na server pred to daj reverse proxy s TLS a autentifikáciou.
- `config.binance.json` má `"dry_run": true`. Živé obchodovanie je vedomé prepnutie
  plus doplnenie kľúčov (do `.env`, nie do configu v gite).

> Docker samotný som v tomto prostredí nemal k dispozícii, takže **image sa zatiaľ
> nebuildoval**. YAML aj anchors sú overené, že sa správne parsujú a mergujú, ale prvý
> `docker compose build` prosím spusti ty — ak niečo spadne, pošli mi výstup.

---

## B. Natívne prostredie

### Predpoklady

Python **3.11+, 64-bit**:
```bash
python -c "import sys,struct;print(sys.version,struct.calcsize('P')*8)"
```

Na macOS ešte natívna knižnica pre TA-Lib, ktorú Freqtrade potrebuje:
```bash
brew install ta-lib
```

### Inštalácia

**Windows**
```powershell
.\platforms\freqtrade\scripts\setup.ps1
```
**macOS / Linux**
```bash
./platforms/freqtrade/scripts/setup.sh
```

Skript vytvorí `.venv`, nainštaluje Freqtrade a `tradebot` v editovateľnom režime, vypíše verziu
a prebehne testy. `-Recreate` (PS) resp. `RECREATE=1` (sh) začne odznova.

Ručný ekvivalent:
```bash
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip     # Windows: .venv/Scripts/python.exe
.venv/bin/python -m pip install freqtrade
.venv/bin/python -m pip install -e ".[dev]"
```

---

## C. Dáta

```powershell
.\platforms\freqtrade\scripts\download-data.ps1              # Windows
```
```bash
./platforms/freqtrade/scripts/download-data.sh               # macOS / Linux
TIMERANGE=20260801-20260905 ./platforms/freqtrade/scripts/download-data.sh
SKIP_COINBASE=1 DAYS=180 ./platforms/freqtrade/scripts/download-data.sh
```

### Sťahujú sa len oficiálne timeframy búrz

| Burza | Pár | Stiahne sa | Pozn. |
|---|---|---|---|
| Binance | `BTC/USDT:USDT` futures | **1m, 3m, 5m** + `mark`, `funding_rate` | vie všetky tri priamo |
| Coinbase | `BTC/USD` spot | **1m, 5m** | **3m neponúka** — ccxt hlási len `1m/5m/15m/30m/1h/2h/6h/1d` |

**Coinbase 3m sa nikde neukladá ako súbor.** Poskladá si ho až Freqtrade stratégia
z 1m dát vlastnými prostriedkami. Na disku sú len skutočné burzové sviečky — žiadne
umelo dorobené timeframy, ktoré by sa dali omylom zameniť za reálne dáta.

### Načo sú tie tri timeframy

| TF | Úloha | Kde je to rozhodnuté |
|---|---|---|
| **3m** | timeframe stratégie — signály; všetky `*MaxBars` limity sa počítajú v **baroch** | ARCHITECTURE_port.md §7 |
| **5m** | `zoneDetectionTF` — detekcia SD zón, ťahá sa ako informative pair | §3 |
| **1m** | `--timeframe-detail` — rozlíšenie SL/TP vnútri 3m sviečky v backteste | §7 |

> ⚠️ **Stratégiu nikdy nespúšťaj priamo na 1m.** `state2MaxBars=15` je na 3m grafe
> 45 minút, na 1m by to bolo 15 minút — iná stratégia.

### Dáta sú v gite

`platforms/freqtrade/user_data/data/` sa **commituje**, aby backtesty boli reprodukovateľné
a server nemusel nič sťahovať. `.gitattributes` má `*.feather binary`, takže ich EOL
normalizácia nepoškodí.

Čo je práve stiahnuté:
```bash
.venv/bin/python -m freqtrade list-data --userdir platforms/freqtrade/user_data --config platforms/freqtrade/config.binance.json
```

---

## C2. Archív dát (ročné súbory)

V gite **nie sú** pracovné súbory Freqtradu, ale archív rozdelený po rokoch:

```
platforms/freqtrade/user_data/data_archive/binance/futures/
    BTC_USDT_USDT-1m-futures.2019.feather    4.7 MB
    BTC_USDT_USDT-1m-futures.2020.feather   15.2 MB
    ...
    BTC_USDT_USDT-1m-futures.2026.feather    9.8 MB   <- jediný, ktorý sa mení
```

**Prečo:** Freqtrade drží celý pár+TF v jednom súbore, ktorý sa pri každom sťahovaní
prepíše celý. Git si pamätá každú verziu — 86 MB `1m` súbor by tak pri každom
doťahovaní dát pridal do histórie ďalších 86 MB, ktoré sa už nedajú odstrániť bez
prepísania histórie. Rok, ktorý sa skončil, sa už nikdy nezmení, takže jeho blob
v histórii existuje raz. Denne rastie iba súbor za aktuálny rok (~10 MB/rok pri 1m).

```bash
python -m tradebot.tools.data_archive status    # čo je kde
python -m tradebot.tools.data_archive merge     # archív -> pracovné súbory (po klonovaní)
python -m tradebot.tools.data_archive split     # pracovné súbory -> archív (po stiahnutí)
```

`download-data.ps1` aj `.sh` volajú `split` samy, takže po stiahnutí stačí commitnúť
`data_archive/`. **Po čerstvom klone treba spustiť `merge`**, inak backtest ani testy
nemajú z čoho čítať.

Delenie je bezstratové — `merge(split(x))` dá presne to isté, čo bolo v `x`
(`tradebot/tests/test_data_archive.py`). Sviečky sa nikde nedopočítavajú.

---

## D. Backtest

```powershell
.\platforms\freqtrade\scripts\backtest.ps1 -Timerange 20260801-20260905
```
```bash
TIMERANGE=20260801-20260905 ./platforms/freqtrade/scripts/backtest.sh
```

Ekvivalent:
```bash
.venv/bin/python -m freqtrade backtesting \
  --config platforms/freqtrade/config.binance.json \
  --userdir platforms/freqtrade/user_data \
  --strategy IBSImbalanceStrategy \
  --timeframe-detail 1m \
  --timerange 20260801-20260905 \
  --cache none
```

> ⚠️ **`--cache none` je povinné.** Freqtrade cachuje výsledok podľa hashu súboru
> stratégie, ale naše nastavenia sú v profile **mimo neho** (`TRADEBOT_PROFILE`). Zmena
> profilu teda cache nezneplatní a dostaneš ticho starý výsledok — v logu je to vidieť
> len ako riadok `Loading backtest result from …zip`. Skripty `backtest.ps1`/`.sh` to
> pridávajú samy; pri ručnom volaní na to netreba zabudnúť.

Stratégia je v [`tradebot/adapters/freqtrade/strategy.py`](../tradebot/adapters/freqtrade/strategy.py);
súbor v `user_data/strategies/` je len ukazovateľ. Profil sa prepína cez `TRADEBOT_PROFILE`:

```bash
TRADEBOT_PROFILE=golden_coinbase_btcusd_3m ./platforms/freqtrade/scripts/backtest.sh
```

> ⚠️ **Pozor na veľkosť pozície.** `maxLossDollar = 350` pri SL vzdialenosti ~$87 znamená
> ~4 BTC, teda cca **$313 000 notional** — na peňaženke 10 000 USDT bez páky sa to nezmestí
> a Freqtrade stake oreže na ~3 % žiadanej veľkosti. Riziko na obchod je potom v skutočnosti
> oveľa menšie než $350. Adaptér to **hlási warningom** (`stake orezany z … na …`), aby to
> nebolo ticho. Riešenie: väčší `dry_run_wallet`, páka, alebo nižší `maxLossDollar`.

### Report ako v TradingView

```bash
.venv/bin/python -m tradebot.tools.report            # posledny backtest -> HTML vedla zipu
.venv/bin/python -m tradebot.tools.report --list     # ake vysledky su k dispozicii
```

Z `backtest_results/*.zip` spraví stránku s rovnakými štyrmi číslami, aké má hore
Strategy Tester (Total PnL, Max drawdown, Profitable trades, Profit factor), s krivkou
kumulatívneho PnL proti buy-and-hold a so zoznamom obchodov. Nič sa neprepočítava,
len sa kreslí to, čo je v zipe — takže sa to dá klásť vedľa screenshotu z TradingView.

---

## D1. Webová aplikácia pre testerov

```powershell
.\platforms\freqtrade\scripts\webapp.ps1
```
```bash
./platforms/freqtrade/scripts/webapp.sh
```

http://127.0.0.1:8765 — formulár so všetkými parametrami stratégie, výber páru
a obdobia, fronta behov, história s vyhľadávaním podľa parametrov a graf výnosnosti
ako v TradingView. História sa ukladá do `user_data/runs/` a commituje sa.
Podrobne v [WEBAPP.md](WEBAPP.md).

---

## D2. Hyperopt

```powershell
.\platforms\freqtrade\scripts\hyperopt.ps1 -Timerange 20260601-20260904 -Epochs 200
.\platforms\freqtrade\scripts\hyperopt.ps1 -Timerange 20250901-20260904 -Epochs 300
```
```bash
./platforms/freqtrade/scripts/hyperopt.sh 20260601-20260904 200
```

Prvý beh potrebuje závislosti navyše:

```bash
python -m pip install cmaes filelock "optuna>4.0.0" scikit-learn "joblib==1.4.2"
```

> `joblib` musí byť **1.4.2**. Od 1.5 sa z neho vybralo `joblib.externals.cloudpickle`,
> ktoré Freqtrade 2026.8 v hyperopte stále importuje, a padne to na
> `cannot import name 'cloudpickle'`.

### Čo sa ladí a čo nie

| ladí sa | neladí sa |
|---|---|
| prahy v jednotke `atr` (`minImbSizePoints`, `pbMinRangePoints`, `engMinRangePoints`, `liqSweepMinWick`, `srClusterPoints`) | session okná |
| `rrRatio` | STATE timeouty |
| prepínače entry modelov (`enablePinBarEntry`, `enableEngulfingEntry`) | sizing a `maxLossDollar` |
| `enableSrTrading`, `enableLqTrading` | `enableImbEntry` — základný model |

Prahy v `atr` sú jediné čísla v profile, ktoré **nie sú prevzaté z TradingView** —
sú to štartovacie odhady (ARCHITECTURE_port.md §3b). Všetko ostatné by sa ladením
rozišlo s paritou, ktorú stráži `test_golden_tv_binance.py`.

### Na čo si dať pozor

**Počet obchodov musí byť strážený.** Skripty používajú vlastnú loss funkciu
`IBSHyperOptLoss` (`user_data/hyperopts/`) — je to Calmar, ale epochy pod ~25 obchodov
na 90 dní dostanú tvrdú penalizáciu. Bez toho vyhlásil štandardný `CalmarHyperOptLoss`
za víťaza epochu so **7 obchodmi** a +17 %, len preto, že mala malý drawdown.

### Sizing musí sedieť, inak porovnávaš dva rôzne experimenty

Profil `docs/profily_archiv/ibs/btcusdt_3m_binance_hyper.json` má zámerne `legacyPineSizing: true`
a `tickDollarValue: 0.5`. Na BTC to dáva `qty = 1 BTC` pri každom reálnom SL
(`floor(350 / (SLdist/0.1 × 0.5)) = 0 → max(1,0) = 1`), takže `maxLossDollar`
sa neuplatní a riziko na obchod je rovné SL vzdialenosti v dolároch — presne to,
čo robil TradingView strategy tester.

Risk-based sizing (`legacyPineSizing: false`, riziko $350 na obchod) je na
obchodovanie správnejšie, ale robí z toho **iný experiment**: mení váhu
jednotlivých obchodov, a teda aj profit factor. Tie isté obchody na 365 dňoch:

| sizing | PnL | max DD |
|---|---|---|
| risk-based ($350/obchod) | −48,9 % | 66,7 % |
| legacy Pine (1 BTC) | −26,4 % | 57,0 % |

**Pretrénovanie.** Priestor má 10 parametrov a stratégia robí rádovo 150–200 obchodov
za rok. To je málo dát na 10 stupňov voľnosti. Výsledok vždy over na inom okne, než
na akom si ladil — presne ten efekt, ktorý sa ukázal pri manuálnom prieskume
v TradingView (vysoké RR vyzeralo dobre na 365 dňoch a strácalo na posledných 90).

**`--analyze-per-epoch` je povinné** (skripty ho pridávajú samy). Freqtrade
štandardne počíta `populate_indicators` len **raz** pre celý beh a per-epochu
prepočítava iba `populate_entry_trend` — predpokladá, že parametre priestoru „buy"
ovplyvňujú len signály. Celý náš engine ale beží v `populate_indicators`. Bez toho
prepínača dá každá epocha **identický výsledok** a hyperopt vyhlási za víťaza
prvú epochu. Spoznáš to tak, že všetky epochy majú ten istý PnL aj počet obchodov.

**Hyperopt beží bez `--timeframe-detail`.** S 1m detailom je jedna epocha rádovo
pomalšia. Najlepší výsledok potom over bežným backtestom **s** detailom — až ten
hovorí niečo o skutočných fill cenách.

**Runner sa pri zmene parametrov prestavuje.** `EngineRunner` je inkrementálny a drží
stav; bez toho by epochy ticho počítali so starými hodnotami. Rieši to odtlačok
configu v `_runner()` — keby si pridával ďalšie parametre, musia byť v `IBSConfig`,
inak ich odtlačok neuvidí.

---

## E. MultiCharts (len Windows)

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
Ak PowerShell odmietne skript spustiť: `powershell -ExecutionPolicy Bypass -File .\platforms\multicharts\scripts\setup.ps1`.

Potom v MultiCharts:
1. **PowerLanguage .NET Editor**
2. **File → New → Signal**, jazyk **Python**, názov **rovnaký ako trieda v šablóne**
   (`IBS`, `DemoBreakout`) — MultiCharts hľadá triedu podľa mena študie
3. Vlož obsah šablóny stratégie z [`platforms/multicharts/`](../platforms/multicharts)
   (`IBS_Signal.py` pre IBS, `DemoBreakout_Signal.py` pre demo) — trieda, ktorá len
   deleguje na balík `tradebot` (MultiCharts vyžaduje metódy `Create`/`CalcBar` priamo
   v triede študie, zdedené nevidí); profil nastav v `PROFILE` (názov alebo cesta). Skompiluj (F7).
4. Na graf pridaj **Data1** = graf TF (napr. MNQ 3m) a, ak stratégia potrebuje informatívny
   TF, **Data2** = ten TF (IBS: `zoneDetectionTF`, štandardne 5m; demo stratégia Data2 nemá).
   Graf musí mať **Time Zone: Exchange** a burza symbolu pásmo GMT — adaptér berie čas
   baru ako UTC.
5. **Insert → Signal** na graf, potom **View → Output**: študia vypíše profil a prvý bar
   (`prvy bar grafu Time[0]=… -> otvorenie …`), z ktorého vidno, či pásmo a razenie baru sedia.
   Obchody: View → Strategy Performance Report → List of Trades.

> **Data2 v bete (15.0.27717) Python študii nefunguje**: `BarsOfData(2)` padá v
> `PriceSeriesImpl.ReBind`, hoci `MaxDataStream` hlási 2 série a Data1 ide. Adaptér má
> preto zálohu: v šablóne nastav `HTF_CSV` na 1m Dukascopy CSV (alebo premennú
> prostredia `TRADEBOT_MC_HTF_CSV`) a informatívny TF sa poskladá zo súboru
> (`tradebot/adapters/multicharts/htf_csv.py`, ~8 s pre desaťročný export). Sú to tie
> isté 5m bary, aké má QuoteManager aj offline simulátor. Ak Data2 jedného dňa pôjde,
> adaptér ju uprednostní a CSV sa nepoužije.

> **FPU výnimky.** Po prvom spracovanom obchode necháva MultiCharts vo vlákne študie
> odmaskované FPU výnimky (control word `0x00080007`: neplatná operácia a delenie nulou
> nie sú maskované). Python s tým nepočíta — prvé porovnanie s NaN zhodí CalcBar ako
> `System.ArithmeticException: Overflow or underflow…` bez Python tracebacku. Adaptér
> preto pri každom `CalcBar` volá `_controlfp` a masky vráti (`fpu_mask_exceptions`);
> v Output okne/logu to hlási riadok „FPU vynimky boli odmaskovane".

> **Obchod vnútri jedného baru.** Market vstup sa v MultiCharts vyplní na otvorení
> ďalšieho baru a TP/SL môže trafiť ešte v tom istom bare — na close je pozícia nula.
> Runner to pozná z `TotalTrades` (`closed_trades`) a vyplnený order už neposiela znova;
> bez toho by sa ten istý market vstup opakoval každý bar.

**Log a zoznam obchodov.** Študia píše všetko, čo ide do Output okna, aj do
`%LOCALAPPDATA%\tradebot\multicharts.log` (`TRADEBOT_MC_LOG`), plus `[trace]` riadky
(každý `Send`, zmeny pozície) a `[trade]` riadok pri každom uzavretom obchode. Zoznam
obchodov z posledného behu:

```bash
.venv/Scripts/python.exe -m tradebot.tools.mc_log_trades --from 2025-01-01 --to 2025-01-31
```

vedľa neho `scan_trades --csv … --from 2025-01-01 --to 2025-01-31`, alebo rovno
`python -m tradebot.tools.mc_compare --csv … --profile … --from … --to …`, ktorý oba
zoznamy spáruje podľa vstupnej ceny a vypíše rozdiely — to je porovnanie MultiCharts
vs. jadro (výsledok pre NAS100: `docs/NAS100_dukas_simulator_2026-09-06.md`).
**Po každej zmene v `tradebot/` treba MultiCharts naozaj reštartovať**: `File → Exit`
nechá bežať `StudyServer.NET`, `tsServer` a ďalšie procesy, ktoré držia Python so starým
kódom — ukonči ich (`Get-Process MultiCharts64, tsServer, StudyServer.NET, TradingServer,
ATCenterServer, PLEditor.NET | Stop-Process -Force`) a spusti MultiCharts znova.

Rozhranie MultiCharts x Python (nie C# `SignalObject`): študia je obyčajná trieda,
MultiCharts volá `Create(ctx)`, `StartCalc`, `CalcBar`, `Destroy`; ordre musia vzniknúť
v `Create`, preto má `TradebotSignal` pevný pool vstupných orderov (`ENTRY_POOL`, 4 na
stranu) a meno konkrétneho orderu (`LONG_<uid>`) dosadí pri každom `Send`.

> **IBS bez Data2 nevytvorí ani jednu SD zónu.** Študia to napíše do Output okna,
> ale inak beží ďalej — je to ľahké prehliadnuť.

Profil sa prepína cez `TRADEBOT_PROFILE` (predvolene default profil stratégie, IBS
`multicharts_mnq_3m`) alebo natvrdo cez `PROFILE` v šablóne, rovnako ako vo Freqtrade.
Ordery študie sa volajú `tb_sl`, `tb_tp` a `tb_session_end`.

Čo robí adaptér:

| súbor | zodpovednosť |
|---|---|
| `tradebot/adapters/multicharts/runner.py` | `MCRunner`: prevedie engine stratégie cez `CalcBar`, drží živé ordre a informatívne okno (feeder zo `StrategySpec`) |
| `tradebot/adapters/multicharts/drawing.py` | `DrawCommand` → `DrwRectangle` / `DrwTrendLine` / `DrwText` |
| `tradebot/adapters/multicharts/signal.py` | `TradebotSignal` — jediný súbor, ktorý sa dotýka PowerLanguage API; stratégia je podtrieda (`tradebot/strategies/<key>/multicharts.py`) |

Prvé dva sú zámerne bez závislosti na PowerLanguage, takže sa testujú na obyčajnom
Pythone (`tradebot/tests/test_multicharts.py`) — vrátane testu, že MultiCharts runner dá
z tých istých barov tie isté zóny ako Freqtrade.

### Dáta z CSV (Dukascopy) do QuoteManagera

MultiCharts študia číta bary z grafu, teda z QuoteManagera — CSV sa doň musí najprv
importovať. Dukascopy 1m export (`dt,o,h,l,c,vol`, bid strana, UTC) sa priamo importovať
nedá: má riadok pre každú minútu vrátane víkendov (plochý bar s poslednou cenou, ~40 %
súboru), razí bar časom otvorenia (MultiCharts časom zatvorenia) a niektoré súbory majú
dni s cenou ×1000 (US500 2015–2019). Prevod:

```powershell
.venv\Scripts\python.exe -m tradebot.tools.dukas_to_mc C:\dukas\NAS100_M1_10Y.csv
# -> C:\dukas\NAS100_M1_mc.csv, hlavička Date,Time,Open,High,Low,Close,Volume
# --from 2021-01-01 --to 2026-09-05   orezanie obdobia
# --fix-scale                          oprava ×1000 dní (nástroj ich vždy nahlási)
# --stamp open                         ak import berie čas otvorenia baru
# --volume-scale 100                   objem ako celé číslo (QuoteManager "0.01" odmietne)
```

Potom v QuoteManageri:
1. **Add Symbol → Manually**: Exchange (napr. `Dukascopy`), Category podľa trhu,
   **Price Scale 1/1000, Min. Movement 1** (dáta majú tri desatinné miesta),
   **Big Point Value 1** (1 USD za bod na jednotku CFD — over si to v obchodných
   podmienkach), **Time Zone GMT/UTC** a session template 24/7 alebo podľa trhu.
   Adaptér berie čas grafu ako UTC, takže iné pásmo symbolu posunie seansy.
2. **Import Data → ASCII** na tom symbole: čas súboru = GMT, rozlíšenie 1 minute,
   stĺpce podľa hlavičky.
   Kontrola po importe: Edit Data v pásme GMT, nedeľa 5. 1. 2025 — prvý bar **23:01**
   (trh otvára 18:00 New York, v zime 23:00 UTC, v lete 22:00 UTC; bar je razený
   zatvorením, preto :01). Graf s Time Zone Exchange ukáže to isté.
3. Na graf Data1 = 3m, Data2 = 5m (obe si MultiCharts poskladá z 1m), profil
   `TRADEBOT_PROFILE=docs/profily_archiv/ibs/nas100_dukas_3m.json` (inštrument
   `nas100_dukascopy`, prahy v bodoch rovnaké ako `multicharts_mnq_3m`).

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

> **Optimalizáciu parametrov nerob v MultiCharts** — Python tam beží pod GIL a je výrazne
> pomalší než PowerLanguage/C#. Laď cez Freqtrade `hyperopt` a výsledok len prenes.

---

## F. Testy

```bash
python -m pytest                       # lokálne
docker compose -f docker/docker-compose.yml run --rm tests
```

231 testov:
- `test_config.py` — validácia configu, sizing, krížové kontroly s inštrumentom
- `test_clock.py` — session okná, pásma, okná cez polnoc, letný/zimný čas
- `test_zones.py` — `snapMode`, detekcia SD patternu, evidencia zón, kreslenie
- `test_statemachine.py` — STATE 0-5, hľadanie gapu, Pin Bar/Engulfing, SL/TP, OCO, ATR
- `test_ta_modules.py` — Market Structure, S/R, likvidita, Elliott
- `test_drawing.py` — identita objektov, prehratie `set_*` zmien
- `test_freqtrade_runner.py` — prevod engine cez DataFrame, dohľadanie signálu, HTF okno
- `test_freqtrade_exits.py` — TP ide cez `custom_roi`, nie cez exit-signál
- `test_multicharts.py` — MultiCharts runner, mapovanie kreslenia a zhoda s Freqtrade
- `test_golden_tv_binance.py` — **parita obchodov a zón** s TradingView (77 zón, 5 obchodov)
- `test_golden_tv_draw.py` — **parita kreslenia** s TradingView (76 objektov)
- `test_pine_parity.py` — **parsuje `pine/imbalance_strategy_FULL.pine`** a stráži, že všetky
  portované vstupy, ich defaulty aj rozsahy stále sedia, a že vedome odstránené vstupy
  (`REMOVED_INPUTS`) sa nevrátili. Hlavná poistka portu: keby sa jeden vstup stratil,
  spadne test namiesto toho, aby stratégia ticho obchodovala inak.

Okrem testov sú tu dva nástroje na overenie proti reálnym dátam:
```bash
.venv/bin/python -m tradebot.tools.scan_zones    --exchange binance   # aké zóny by vznikli
.venv/bin/python -m tradebot.tools.scan_trades   --exchange binance   # celý STATE 0-5 + ordre
# to isté nad Dukascopy 1m CSV (NAS100 pre MultiCharts) — bez MultiCharts aj bez Freqtrade
.venv/bin/python -m tradebot.tools.scan_trades --csv C:/dukas/NAS100_M1_10Y.csv \
    --profile docs/profily_archiv/ibs/nas100_dukas_3m.json --from 2025-01-01 --to 2025-01-31
```

`--csv` číta surový Dukascopy export (vypchávku zahodí rovnako ako `dukas_to_mc`), graf
aj detekčný TF skladá z 1m v pamäti a vyplnenie rozhoduje po 1m sviečkach. Fill model je
naivný a poplatky nepočíta — je to na porovnanie zoznamu obchodov so študiou
v MultiCharts, nie na PnL.

---

## G. Konfiguračné profily

Profily sú per stratégia v `tradebot/configs/<stratégia>/` (kľúč `_strategy`), načítajú sa
menom (`load_profile("ibs/golden_binance_btcusdt_3m")`, holé meno = stratégia `ibs`) alebo
cestou k JSON. Po premenovaní balíka `ibs` → `tradebot` (2026-09-06) treba v existujúcom
prostredí raz `pip install -e .` (setup skripty to robia a starý balík `ibs` odinštalujú).

Nastavenia stratégie **nie sú** vo Freqtrade configu — tie sú v `tradebot/configs/ibs/`:

| Profil | Burza / inštrument | Použitie |
|---|---|---|
| `multicharts_mnq_3m` | MNQ (CME) | základ pre MultiCharts futures/akcie, jednotky `abs` = 1:1 s TradingView |
| `golden_coinbase_btcusd_3m` | Coinbase BTC/USD | referenčný — golden test proti TradingView |
| `golden_binance_btcusdt_3m` | Binance BTC/USDT perp | referenčný — golden test proti TradingView na Binance |
| `docs/profily_archiv/ibs/*.json` | Binance BTC a ETH | skúšané konfigurácie z vývoja, načítajú sa cestou (viď README archívu) |

```python
from tradebot.core import load_profile
cfg, inst = load_profile("golden_binance_btcusdt_3m")
print(cfg.check_instrument(inst))   # varovania ku kombinácii config × inštrument
```

Freqtrade config (`platforms/freqtrade/config.*.json`) rieši len burzu, páry, peňaženku
a trading mode. Logika stratégie ide výhradne z `tradebot/configs/ibs/`.

---

## Riešenie problémov

**`Invalid timeframe '3m'. This exchange supports: [...]`**
Správne správanie — Coinbase 3m neponúka. Sťahuj z nej len `1m 5m`; 3m si poskladá stratégia.

**MultiCharts nenájde modul `tradebot`**
Má nastavený iný Python, než do ktorého sa inštalovalo. Zisti ktorý a spusti
`platforms\multicharts\scripts\setup.ps1 -Python <cesta>`. Nikdy to nesmie byť `.venv`.

**`pip install -e .` v globálnom Pythone hlási chýbajúce oprávnenia**
PowerShell ako správca, alebo `--user`. Editovateľná inštalácia je zámerná — zmeny v `tradebot/`
sa prejavia bez preinštalovania.

**Testy nevidia `tradebot`**
Balík nie je v tom Pythone, ktorým púšťaš pytest. Buď `pip install -e ".[dev]"`, alebo pytest
spúšťaj z koreňa repa.

**Backtest hlási, že stratégia neexistuje**
Správne — adaptér je krok 4 (ARCHITECTURE_port.md §8). Zatiaľ je hotový krok 1.

**macOS: inštalácia padá na `ta-lib`**
`brew install ta-lib`, potom setup skript znova.

---

## Mapa repozitára

```
tradebot/                          spoločné jadro (žiadny import z Freqtrade ani MultiCharts)
  core/types.py               Bar, HTFWindow, InstrumentSpec, SizeSpec
  core/config.py              IBSConfig - Pine vstupy + validácia
  configs/*.json              profily (len odchýlky od Pine defaultov)
  tests/                      pytest
platforms/
  freqtrade/
    config.binance.json       exekučná burza, futures
    config.coinbase.json      referenčná burza, spot
    user_data/data/           stiahnuté sviečky - COMMITUJÚ sa
    user_data/strategies/     sem príde adaptér (krok 4)
    scripts/                  setup / download-data / backtest, .ps1 aj .sh
  multicharts/
    scripts/setup.ps1         inštalácia ibs do globálneho Pythonu
docker/
  Dockerfile.core             jadro + testy (CI)
  Dockerfile.freqtrade        freqtrade + jadro (server)
  docker-compose.yml          tests / download / backtest / freqtrade
docs/
  ARCHITECTURE_port.md        návrh, rozhodnutia, mapovanie Pine -> Python
  RUNNING.md                  tento súbor
  tv_settings_2026-09-03.md   nastavenia z TradingView
pine/imbalance_strategy_FULL.pine  referenčná Pine implementácia (+ staršie buildy)
```
