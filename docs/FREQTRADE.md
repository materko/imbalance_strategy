# Freqtrade vetva: prostredie, backtest, hyperopt, Docker

Táto vetva pokrýva krypto na Binance (futures aj spot) a referenčný Coinbase. Beží
na Windows, macOS aj Linuxe a dá sa kontajnerizovať. MultiCharts je samostatná vetva —
[MULTICHARTS.md](MULTICHARTS.md). Dáta majú vlastný dokument — [DATA.md](DATA.md).

Všetko sa spúšťa **z koreňa repozitára**. `PY` = Python z `.venv`
(`.venv\Scripts\python.exe` na Windows, `.venv/bin/python` inde).

---

## A. Prostredie (venv)

Python **3.11+, 64-bit**:
```bash
python -c "import sys,struct;print(sys.version,struct.calcsize('P')*8)"
```

Na macOS ešte natívna knižnica pre TA-Lib, ktorú Freqtrade potrebuje:
```bash
brew install ta-lib
```

**Windows**
```powershell
.\platforms\freqtrade\scripts\setup.ps1
```
**macOS / Linux**
```bash
./platforms/freqtrade/scripts/setup.sh
```

Skript vytvorí `.venv`, nainštaluje Freqtrade a `tradebot` v editovateľnom režime, vypíše
verziu a prebehne testy. `-Recreate` (PS) resp. `RECREATE=1` (sh) začne odznova.

Ručný ekvivalent:
```bash
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip     # Windows: .venv\Scripts\python.exe
.venv/bin/python -m pip install freqtrade
.venv/bin/python -m pip install -e ".[dev]"
```

---

## B. Backtest

```powershell
.\platforms\freqtrade\scripts\backtest.ps1 -Timerange 20260801-20260905
```
```bash
TIMERANGE=20260801-20260905 ./platforms/freqtrade/scripts/backtest.sh
```

Ekvivalent:
```bash
PY -m freqtrade backtesting \
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
> len ako riadok `Loading backtest result from …zip`. Skripty to pridávajú samy; pri
> ručnom volaní na to netreba zabudnúť.

> ⚠️ **Backtest, ktorý má byť v histórii Testera, spúšťaj cez
> `PY -m tradebot.webapp.cli run …`** — holý Freqtrade CLI do `tester/runs/` nezapíše nič
> ([WEBAPP.md](WEBAPP.md)).

Stratégia je v [`tradebot/adapters/freqtrade/strategy.py`](../tradebot/adapters/freqtrade/strategy.py);
súbor v `user_data/strategies/` je len shim pre resolver. Profil sa prepína cez
`TRADEBOT_PROFILE` (názov z `tradebot/configs/<stratégia>/` alebo cesta k JSON):

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
PY -m tradebot.tools.report            # posledny backtest -> HTML vedla zipu
PY -m tradebot.tools.report --list     # ake vysledky su k dispozicii
```

Z `backtest_results/*.zip` spraví stránku s rovnakými štyrmi číslami, aké má hore
Strategy Tester (Total PnL, Max drawdown, Profitable trades, Profit factor), s krivkou
kumulatívneho PnL proti buy-and-hold a so zoznamom obchodov. Nič sa neprepočítava,
len sa kreslí to, čo je v zipe — takže sa to dá klásť vedľa screenshotu z TradingView.

---

## C. Hyperopt

```powershell
.\platforms\freqtrade\scripts\hyperopt.ps1 -Timerange 20260601-20260904 -Epochs 200
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
sú to štartovacie odhady ([ARCHITECTURE_port.md §3b](ARCHITECTURE_port.md)). Všetko ostatné
by sa ladením rozišlo s paritou, ktorú stráži `test_golden_tv_binance.py`.

### Na čo si dať pozor

**Počet obchodov musí byť strážený.** Skripty používajú vlastnú loss funkciu
`IBSHyperOptLoss` (`user_data/hyperopts/`) — je to Calmar, ale epochy pod ~25 obchodov
na 90 dní dostanú tvrdú penalizáciu. Bez toho vyhlásil štandardný `CalmarHyperOptLoss`
za víťaza epochu so **7 obchodmi** a +17 %, len preto, že mala malý drawdown.

**Sizing musí sedieť, inak porovnávaš dva rôzne experimenty.** Profil
`docs/profily_archiv/ibs/btcusdt_3m_binance_hyper.json` má zámerne `legacyPineSizing: true`
a `tickDollarValue: 0.5`. Na BTC to dáva `qty = 1 BTC` pri každom reálnom SL
(`floor(350 / (SLdist/0.1 × 0.5)) = 0 → max(1,0) = 1`), takže `maxLossDollar`
sa neuplatní a riziko na obchod je rovné SL vzdialenosti v dolároch — presne to,
čo robil TradingView strategy tester. Risk-based sizing je na obchodovanie správnejší,
ale mení váhu jednotlivých obchodov, a teda aj profit factor:

| sizing | PnL | max DD |
|---|---|---|
| risk-based ($350/obchod) | −48,9 % | 66,7 % |
| legacy Pine (1 BTC) | −26,4 % | 57,0 % |

**Pretrénovanie.** Priestor má 10 parametrov a stratégia robí rádovo 150–200 obchodov
za rok. To je málo dát na 10 stupňov voľnosti. Výsledok vždy over na inom okne, než
na akom si ladil — presne ten efekt, ktorý sa ukázal pri manuálnom prieskume
v TradingView (vysoké RR vyzeralo dobre na 365 dňoch a strácalo na posledných 90).
Ako to dopadlo: [merania/HYPEROPT_btcusdt_2026-09-04.md](merania/HYPEROPT_btcusdt_2026-09-04.md).

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
configu v `_runner()` — keby si pridával ďalšie parametre, musia byť v confige
stratégie, inak ich odtlačok neuvidí.

---

## D. Docker

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

| Image | Základ | Na čo |
|---|---|---|
| `tradebot-core` | `python:3.12-slim` | testy a CI. Jadro nemá závislosti mimo stdlib, takže je malý a beží aj na arm64 Macu. |
| `tradebot-freqtrade` | `freqtradeorg/freqtrade:stable` | download, backtest, live bot |

Balík `tradebot` sa do Freqtrade image nedáva cez `pip`, ale cez `PYTHONPATH=/app`. Compose
mountuje `../tradebot:/app/tradebot:ro`, takže **zmeny v jadre sa prejavia bez rebuildu** —
a image funguje aj samostatne bez mountu. Build navyše na konci spustí sanity check
profilov, takže rozbitý config zhodí build, nie až server.

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

> Docker som v tomto prostredí nemal k dispozícii, takže **image sa zatiaľ nebuildoval**.
> YAML aj anchors sú overené, že sa správne parsujú a mergujú, ale prvý
> `docker compose build` prosím spusti ty — ak niečo spadne, pošli mi výstup.

---

## E. Konfiguračné profily

Profily sú per stratégia v `tradebot/configs/<stratégia>/` (kľúč `_strategy`), načítajú sa
menom (`load_profile("ibs/golden_binance_btcusdt_3m")`, holé meno = stratégia `ibs`) alebo
cestou k JSON.

| Profil | Burza / inštrument | Použitie |
|---|---|---|
| `golden_binance_btcusdt_3m` | Binance BTC/USDT perp | referenčný — golden test proti TradingView |
| `golden_coinbase_btcusd_3m` | Coinbase BTC/USD | referenčný — golden test proti TradingView |
| `multicharts_mnq_3m` | MNQ (CME) | základ pre MultiCharts, jednotky `abs` = 1:1 s TradingView |
| `docs/profily_archiv/ibs/*.json` | Binance BTC a ETH, Dukascopy NAS100 | skúšané konfigurácie z vývoja, načítajú sa cestou ([README archívu](profily_archiv/ibs/README.md)) |

```python
from tradebot.core import load_profile
cfg, inst = load_profile("golden_binance_btcusdt_3m")
print(cfg.check_instrument(inst))   # varovania ku kombinácii config × inštrument
```

Freqtrade config (`platforms/freqtrade/config.*.json`) rieši len burzu, páry, peňaženku
a trading mode. Logika stratégie ide výhradne z profilu.

---

## F. Testy

```bash
PY -m pytest                       # lokálne, ~20 s
docker compose -f docker/docker-compose.yml run --rm tests
```

440 testov, z toho tie, ktoré držia port pohromade:

- `test_config.py` — validácia configu, sizing, krížové kontroly s inštrumentom
- `test_clock.py` — session okná, pásma, okná cez polnoc, letný/zimný čas
- `test_zones.py`, `test_statemachine.py`, `test_ta_modules.py` — zóny, STATE 0–5, TA moduly
- `test_freqtrade_runner.py`, `test_freqtrade_exits.py` — prevod enginu cez DataFrame, TP cez `custom_roi`
- `test_multicharts*.py` — MultiCharts runner, emulátor, kreslenie, zhoda s Freqtrade
- `test_golden_tv_binance.py`, `test_golden_tv_draw.py`, `test_golden_tv_elliott.py` —
  **parita obchodov, zón a kreslenia** s TradingView
- `test_pine_parity.py` — **parsuje `pine/imbalance_strategy_FULL.pine`** a stráži, že všetky
  portované vstupy, ich defaulty aj rozsahy stále sedia, a že vedome odstránené vstupy
  (`REMOVED_INPUTS`) sa nevrátili. Hlavná poistka portu: keby sa jeden vstup stratil,
  spadne test namiesto toho, aby stratégia ticho obchodovala inak.
- `test_registry.py` — každá stratégia v registry má profil, Pine súbor, shim aj šablónu

---

## G. Dukascopy symboly cez Freqtrade (hyperopt, FreqAI)

Dukascopy CFD (NAS100, forex, komodity) bežia v Testeri cez emulátor MultiCharts, ktorý
sa zhoduje so skutočným MultiCharts na cent — ale **hyperopt a FreqAI vie len Freqtrade**.
Preto sa dá ten istý symbol prehnať aj cez Freqtrade vetvu:

```bash
PY -m tradebot.tools.dukas_import C:/dukas/NAS100_M1_10Y.csv --symbol NAS100 --target freqtrade

TRADEBOT_PROFILE=docs/profily_archiv/ibs/nas100_dukas_3m.json PY -m freqtrade backtesting \
  --config platforms/freqtrade/config.dukascopy.json \
  --userdir platforms/freqtrade/user_data \
  --datadir platforms/freqtrade/user_data/data/dukascopy \
  --strategy IBSImbalanceStrategy --timeframe 3m --timeframe-detail 1m \
  --timerange 20250106-20250201 --fee 0 --cache none
```

### Čo si to vyžiadalo a prečo

Freqtrade je postavený na ccxt burzách a Dukascopy medzi nimi nie je. Prekážky sú tri
a všetky rieši `config.dukascopy.json` plus adaptér:

| prekážka | prečo | riešenie |
|---|---|---|
| burza musí byť z ccxt | `validate_stakecurrency` aj `validate_timeframes` sa volajú aj v backteste | ako **nosič** sa použije `bitstamp` — jediné, čo od nej chceme, je USD ako quote mena a znalosť 3m (Coinbase 3m nemá, Binance zase USD). Žiadne dáta sa z nej neberú. |
| pár `NAS100/USD` na nej neexistuje | `StaticPairList` by ho vyhodil | `"allow_inactive": true` v pairliste |
| chýba market info páru | pri vstupe do obchodu si Freqtrade pýta `exchange.markets[pair]` a bez neho padne na `Can't get market information for symbol …` | `TradebotStrategyBase.bot_start` ho doplní z `InstrumentSpec` (tick, krok množstva, min) — sú to presnejšie čísla, než keby sme ich požičali od cudzieho páru. Robí sa to len pre inštrument mimo burzy a len pre pár, ktorý na nosnej burze naozaj nie je. |

`trading_mode` je **spot**: futures režim by chcel `funding_rate` a `mark` sviečky, ktoré CFD
nemá, a IBS je aj tak long only. Peňaženka je zámerne 1 000 000 — profil má `legacyPineSizing`
(qty v jednotkách po 1 USD/bod), takže pri 10 000 by Freqtrade stake orezal a PnL by
neznamenalo nič. **Poplatok zadaj vždy sám** (`--fee`): z nosnej burzy sa nemá odkiaľ vziať
a syntetický market má nulu.

### Výsledok nie je zameniteľný s emulátorom

Signály sú identické, líši sa **fill model**. Január 2025, `--fee 0`, profil `nas100_dukas_3m`:

| | obchodov | W / L | PnL |
|---|---|---|---|
| emulátor MultiCharts (Tester) | 12 | 9 / 3 | +1 992 USD |
| MultiCharts študia | 12 | 9 / 3 | +1 991,66 USD |
| **Freqtrade** | **13** | **9 / 4** | **+1 833 USD** |

Každý spárovaný obchod má rovnakú vstupnú aj výstupnú cenu; rozdiely sú dva:

- **jeden obchod navyše** (6. 1. 16:28) — vstup hneď na ďalšej sviečke po výstupe. V Pine
  aj v MultiCharts order po zavretí pozície zaniká, Freqtrade ho nechá vyplniť.
- **veľkosť pozície** sa pri market vstupoch líši o cent vo vstupnej cene, a keďže
  `legacyPineSizing` počíta `qty = floor(maxLossDollar / SL vzdialenosť)`, blízko hranice
  zaokrúhlenia to zmení qty aj o polovicu (24. 1.: −174 vs −360 USD pri tej istej cene).

Preto: **laď cez Freqtrade, ale záver over emulátorom.** Referencia pre NAS100 ostáva
emulátor, lebo ten sedí s tým, čo v MultiCharts naozaj pobeží.

### FreqAI

Kód FreqAI je súčasťou Freqtradu, chýbajú mu len závislosti:
`pip install "freqtrade[freqai]"` (`datasieve`, `lightgbm`/`xgboost`/`catboost`).

Stratégia je deterministický stavový automat, ktorého parita s Pine je zmyslom celého portu,
takže sa nedá nahradiť modelom bez toho, aby prestala byť tou stratégiou. Zmysluplné napojenie
je jediné: engine nájde setup ako doteraz a model predpovie pravdepodobnosť, že **tento**
setup skončí ako výhra (features: veľkosť zóny, vzdialenosť SL, ATR, hodina, štruktúra, RR);
vstup sa vykoná len nad prahom. To je presne ten istý druh zásahu ako štruktúrny filter,
NY seansa a filter tesného SL — každý z nich zdvojnásobil edge tým, že obchody **odobral**
([merania/OPTIMALIZACIA_2026-09-05.md](merania/OPTIMALIZACIA_2026-09-05.md)). Ako rozšírenie
mimo Pine by patril do `PORT_ONLY_FIELDS` s defaultom „vypnuté", takže parita ostane nedotknutá.

Pozor na to isté, čo pri hyperopte, len horšie: stratégia robí 30–200 obchodov za rok a model
má rádovo viac stupňov voľnosti než 10 parametrov, ktoré už raz overfitovali. Bez walk-forward
(FreqAI ho má vstavaný) a overenia na inom okne to nemá výpovednú hodnotu.

---

## Riešenie problémov

**`Invalid timeframe '3m'. This exchange supports: [...]`**
Správne správanie — Coinbase 3m neponúka. Sťahuj z nej len `1m 5m`.

**`No history for <pár>, <typ>, <TF> found` a `No data found. Terminating.`**
Pre `--timeframe` chýba súbor. Freqtrade vyšší TF z 1m **nedopočíta** — resampluje len
z obchodov (`trades-to-ohlcv`), a `--timeframe-detail 1m` rieši výlučne rozlíšenie vnútri
sviečky základného TF. Buď stiahni ten TF, alebo si ho vyrob ako súbor ([DATA.md](DATA.md)).

**Backtest nič neobchoduje a v logu je `Loading backtest result from …zip`**
Chýba `--cache none` — dostal si starý výsledok spred zmeny profilu.

**„chýbajú dáta" / prázdny zoznam párov**
`PY -m tradebot.tools.data_archive merge` ([DATA.md](DATA.md)).

**Testy nevidia `tradebot`**
Balík nie je v tom Pythone, ktorým púšťaš pytest. Buď `pip install -e ".[dev]"`, alebo pytest
spúšťaj z koreňa repa.

**macOS: inštalácia padá na `ta-lib`**
`brew install ta-lib`, potom setup skript znova.
