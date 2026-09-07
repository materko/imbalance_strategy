# TradeBot — porty TradingView stratégií do Freqtrade a MultiCharts

Repozitár sú **dva celky**:

| | čo to je | kde |
|---|---|---|
| **TradeBot** | produkt, ktorý obchoduje: generické jadro, stratégie a dva tenké adaptéry — **Freqtrade** (Docker alebo priamo) a **MultiCharts** (Windows aplikácia). Stratégia je natoľko generická, že tá istá beží cez oba. | [`tradebot/`](tradebot) |
| **TradeBot Tester** | čím sa to skúša: sťahovanie a čistenie dát, porovnávacie behy (Pine ↔ port, MultiCharts ↔ emulátor ↔ Freqtrade), reporty a webová aplikácia pre testerov. | [`tester/`](tester) |

Závislosť ide jedným smerom — Tester importuje `tradebot`, produkt o Testeri nevie.
Cieľ je rovnaké obchody aj rovnaké vykreslovanie ako v TradingView; parita je overená
golden testom na cent ([GOLDEN_binance_2026-08-24.md](docs/GOLDEN_binance_2026-08-24.md)).

Stratégie v registry (ako pridať ďalšiu: [docs/STRATEGIE.md](docs/STRATEGIE.md)):

| kľúč | stratégia | Pine zdroj |
|---|---|---|
| `ibs` | **IBS Imbalance Breakout** — na detekčnom TF (5m) vznikajú supply/demand zóny, v nich sa hľadá imbalance (gap), Pin Bar alebo Engulfing, vstup je limitka na cene gapu, SL zo swingu, TP z pomeru RR; seansy (New York), long only, štruktúrny filter, filter tesného SL | [`pine/imbalance_strategy_FULL.pine`](pine/imbalance_strategy_FULL.pine) |
| `demo_breakout` | **Demo Donchian Breakout** — ukážka, ktorá overuje rámec end-to-end (8 parametrov); nie je to obchodné odporúčanie | [`pine/demo_breakout.pine`](pine/demo_breakout.pine) |

---

## Rýchly štart

### Tester — webová aplikácia

**macOS jedným príkazom** (doinštaluje Homebrew, Python, TA-Lib, spýta sa kam klonovať
a aké meno testera použiť, postaví prostredie, zloží dáta, dá spúšťač na Plochu):

```bash
curl -fsSL https://raw.githubusercontent.com/materko/imbalance_strategy/main/install-macos.sh | bash
```

**Inak** potrebuješ Python 3.11+ (64-bit) a git; na macOS ešte `brew install ta-lib`. Prvé
spustenie postaví prostredie (~10 min) a otvorí prehliadač na http://127.0.0.1:8765.

```powershell
.\webapp.ps1        # Windows (alebo dvojklik na webapp.cmd)
```
```bash
./webapp.sh         # macOS / Linux
```

Vo webapp si vyberieš stratégiu, nastavíš parametre (všetky jej Pine vstupy, zoskupené ako
v TradingView), vyberieš pár a obdobie, spustíš backtest a vidíš kartu s výsledkami, graf výnosnosti ako v Strategy
Testeri, graf páru so všetkým, čo engine v tom behu nakreslil (zóny, TP/SL boxy, štítky,
štruktúra, S/R…) aj s obchodmi, a zoznam obchodov. História behov vrátane kresieb sa ukladá
do gitu a dá sa v nej hľadať podľa parametrov. Podrobne: [docs/WEBAPP.md](docs/WEBAPP.md).

### Vývojár — venv, testy, backtest z príkazového riadku

```powershell
.\platforms\freqtrade\scripts\setup.ps1           # .venv + freqtrade + tradebot (Windows)
.\platforms\freqtrade\scripts\backtest.ps1 -Timerange 20250904-20260904
```
```bash
./platforms/freqtrade/scripts/setup.sh            # macOS / Linux
TRADEBOT_PROFILE=docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json ./platforms/freqtrade/scripts/backtest.sh
.venv/bin/python -m pytest                        # 440 testov vrátane parity s Pine
```

### Dáta z Dukascopy (NAS100, forex, CFD) do Testera aj do MultiCharts

```powershell
.\dukas-import.ps1 C:\dukas\NAS100_M1_10Y.csv --symbol NAS100
```
```bash
./dukas-import.sh ~/dukas/NAS100_M1_10Y.csv --symbol NAS100
```

Vyčistí surový export, zapíše ročné sviečky do archívu MultiCharts (Tester ich uvidí po
reštarte webapp) a vyrobí ASCII súbor pre QuoteManager. `--target freqtrade` k tomu poskladá
3m a 5m sviečky, aby sa na symbole dal spustiť hyperopt
([docs/FREQTRADE.md §G](docs/FREQTRADE.md)). Nový symbol pridá sám
(`--symbol EURUSD --point-value 100000 --tick 0.00001`). Podrobne: [docs/DATA.md](docs/DATA.md).

---

## Rozcestník dokumentácie

| chcem… | kam |
|---|---|
| spúšťať backtesty, pozerať a zdieľať históriu | [docs/WEBAPP.md](docs/WEBAPP.md) |
| krypto: prostredie, backtest, hyperopt, Docker, server | [docs/FREQTRADE.md](docs/FREQTRADE.md) |
| MultiCharts: študia, QuoteManager, emulátor | [docs/MULTICHARTS.md](docs/MULTICHARTS.md) |
| dáta: archív, Dukascopy import, nový symbol | [docs/DATA.md](docs/DATA.md) |
| pridať ďalšiu stratégiu | [docs/STRATEGIE.md](docs/STRATEGIE.md) |
| ako je to postavené a prečo | [docs/ARCHITECTURE_port.md](docs/ARCHITECTURE_port.md) |
| čísla z meraní | [docs/merania/](docs/merania/README.md) |
| kde čo beží a mapa repozitára | [docs/RUNNING.md](docs/RUNNING.md) |

---

## Mapa repozitára

| Cesta | Čo tam je |
|---|---|
| **TradeBot — produkt** | |
| [`tradebot/core/`](tradebot/core) | Generické jadro bez závislostí: `StrategyConfig` (báza configu, profily), `Engine`/`EngineOutput`, `OrderIntent`/`TradePlan`, `BarHistory`, hodiny seáns, `DrawCommand` + `DrawKind` registr, inštrumenty, skladanie TF z 1m (`candles`), čítanie Dukascopy exportu (`dukascopy`), `paths.py` so všetkými cestami repozitára. |
| [`tradebot/strategies/`](tradebot/strategies) | Registry `STRATEGIES` a jedna stratégia = jeden balík: `ibs/` (config, engine, stavový automat zón, `ta/`, HTF feeder, Freqtrade a MultiCharts podtriedy, meta pre webapp), `demo_breakout/`. Postup: [docs/STRATEGIE.md](docs/STRATEGIE.md). |
| [`tradebot/adapters/freqtrade/`](tradebot/adapters/freqtrade) | Generická Freqtrade stratégia `TradebotStrategyBase` + `EngineRunner` (engine nad DataFrame, fill model) + export kresieb. |
| [`tradebot/adapters/multicharts/`](tradebot/adapters/multicharts) | Generická študia `TradebotSignal`, `MCRunner`, kreslenie (len Windows) a **emulátor** MultiCharts (beží všade). |
| [`tradebot/configs/<stratégia>/`](tradebot/configs) | JSON profily — len odchýlky od Pine defaultov, viď nižšie. |
| [`tradebot/tests/`](tradebot/tests) | Testy produktu: jadro, stratégie, oba adaptéry. |
| [`pine/`](pine) | Pine zdroje stratégií: `imbalance_strategy_FULL.pine` (**referenčný IBS**, v5, 115 vstupov — zdroj pravdy pre logiku, defaulty aj tooltipy) a `demo_breakout.pine`. |
| [`platforms/freqtrade/`](platforms/freqtrade) | Configy búrz (`config.binance.json`, `config.coinbase.json`, `config.dukascopy.json`), skripty (setup, download, backtest, hyperopt), `user_data/` (shim na stratégiu, hyperopt loss, `data_archive/<zdroj>/` so sviečkami). |
| [`platforms/multicharts/`](platforms/multicharts) | Šablóny študií (`IBS_Signal.py`, `DemoBreakout_Signal.py`), inštalačný skript a `data_archive/<zdroj>/` s 1m sviečkami. |
| [`docker/`](docker) | `docker-compose.yml` (tests, download, backtest, freqtrade bot, webapp). |
| **TradeBot Tester** | |
| [`tester/webapp/`](tester/webapp) | Webová aplikácia pre testerov (FastAPI + Plotly) a jej CLI. |
| [`tester/compare/`](tester/compare) | Porovnávacie behy: `scan_zones`/`scan_trades` (engine offline nad burzou alebo surovým CSV), `mc_log_trades` (obchody z logu MultiCharts študie), `mc_compare` (spárovanie oboch zoznamov). |
| `tester/dukas_import.py`, `tester/data_archive.py` | Prevod a čistenie surových exportov, ročný archív sviečok. |
| `tester/report.py`, `tester/fees.py`, `tester/plot.py` | HTML report ako Strategy Tester, maker/taker a break-even, grafy. |
| [`tester/tests/`](tester/tests) | Testy nástrojov Testera a **golden testy** proti TradingView (`golden/`). |
| `tester/runs/`, `tester/profiles/` | História behov vrátane kresieb a vlastné configy testerov; oboje sa commituje a zdieľa cez GitHub. |
| `tester/scripts/` | Spúšťač webapp. |
| **Ostatné** | |
| `webapp.cmd`, `webapp.ps1`, `webapp.sh` | Spúšťače Testera z koreňa repozitára (obaly nad `tester/scripts/`). |
| `dukas-import.ps1`, `dukas-import.sh` | Import surových Dukascopy dát (obaly nad `tester.dukas_import`). |
| [`CLAUDE.md`](CLAUDE.md) | Pokyny pre Claude Code v dvoch režimoch podľa `.ibs-role` (gitignored, pýta sa raz): **tester** = backtesty do histórie cez `python -m tester.webapp.cli`, bez zásahov do kódu; **developer** = bez obmedzení, len konvencie. |
| `install-macos.sh` | Inštalátor pre macOS jedným príkazom (`curl \| bash`). |
| [`docs/`](docs) | Návody a architektúra; merania v [`docs/merania/`](docs/merania/README.md), archív profilov v [`docs/profily_archiv/`](docs/profily_archiv/ibs/README.md). |

---

## Profily (`tradebot/configs/<stratégia>/`)

Profil = Pine defaulty stratégie + odchýlky + `_strategy` + `_instrument`. Prepína sa cez
`TRADEBOT_PROFILE=<meno alebo cesta>` alebo vo webapp. Profily IBS (`tradebot/configs/ibs/`):

| Profil | Na čo |
|---|---|
| `golden_binance_btcusdt_3m` | **Referenčný na golden test** — presne nastavenia z grafu TradingView na Binance BTCUSDT.P (RR 1, trailing, 1 BTC). Nie na obchodovanie. |
| `golden_coinbase_btcusd_3m` | Referenčný pre Coinbase BTCUSD — parita jadra s TradingView screenshotmi (MultiCharts a testy). |
| `multicharts_mnq_3m` | MNQ futures pre MultiCharts, 1:1 s Pine jednotkami. |
| `nas100_dukas_3m` (archív) | NAS100 CFD z Dukascopy — rovnaké prahy v bodoch ako MNQ. Beží vo webapp na „burze" MultiCharts aj v MultiCharts samotnom ([docs/MULTICHARTS.md](docs/MULTICHARTS.md)). |
| `demo_breakout/binance_btcusdt_5m` | Jediný profil ukážkovej stratégie (Pine defaulty, páka 5). |
| ostatné | Skúšané konfigurácie (NY seansa, SL filter, risk sizing, hyperopt…) sú v [docs/profily_archiv/](docs/profily_archiv/ibs/README.md) s tabuľkou odchýlok; načítajú sa cestou (`--profile docs/profily_archiv/ibs/<nazov>.json`). Odporúčaný štart na nasadenie je `btcusdt_3m_binance_ny_sl_risk1` odtiaľ. |

---

## Kde sme s výsledkami (2026-09-05)

Kľúčové číslo je **break-even poplatok** — koľko smie burza brať na stranu, aby stratégia vyšla
na nulu. Binance taker berie 0,05 %. Päť rokov BTC/USDT.P 3m, bez poplatkov, 1 BTC na obchod:

| krok | break-even | obchodov / rok | dokument |
|---|---|---|---|
| pôvodné nastavenie (RR 1, trailing) | 0,0050 % | 166 | [BACKTEST_rok_btcusdt](docs/merania/BACKTEST_rok_btcusdt_2026-09-04.md) |
| RR 5, bez trailingu, `slLookback` 20 | 0,0226 % | 203 | [SWEEP_rr_a_tf](docs/merania/SWEEP_rr_a_tf_2026-09-04.md) |
| + štruktúrny filter (BOS/CHoCH) | 0,0423 % | 96 | [FILTRE_vstupu](docs/merania/FILTRE_vstupu_2026-09-04.md) |
| + len NY seansa | 0,0879 % | 43 | [SEANSY](docs/merania/SEANSY_2026-09-05.md) |
| **+ `minSlDistance` 0,20 % ceny** | **0,1410 %** | **30** | [OPTIMALIZACIA](docs/merania/OPTIMALIZACIA_2026-09-05.md) |

Každý krok zdvojnásobil edge tým, že **odobral** obchody, nie že pridal. Ladenie prahov
hyperoptom overfitovalo; prežili len binárne rozhodnutia s mechanizmom. NY seansa aj filter SL
sa potvrdili **bez ladenia na ETH** (break-even 0,056 → 0,096 %).

S reálnymi poplatkami a risk-based sizingom 1 % účtu (`*_ny_sl_risk1`): BTC **+42,8 %** za päť
rokov (3 z 5 rokov ziskové, max DD 12 %), ETH **+40,5 %** (4 z 5, max DD 8 %). Bez filtra SL
je ten istý sizing +0,2 % — filter a risk sizing patria k sebe.

Čo nefunguje: shorty (PF < 1), londýnska seansa (edge 0), volume filter, trendové HTF filtre,
časový stop, vyšší timeframe grafu, ATR ako jednotka filtra SL, páka (mení len mierku).

Všetky merania po rokoch: [docs/merania/](docs/merania/README.md).

---

## Parita s TradingView

- [GOLDEN_binance_2026-08-24.md](docs/GOLDEN_binance_2026-08-24.md) — golden test: zóny, obchody, kresby, Elliott sedia na cent
- [AUDIT_pine_2026-09-05.md](docs/AUDIT_pine_2026-09-05.md) — systematický prechod Pine skriptu, čo chýbalo
- [OPRAVY_adapter_2026-09-05.md](docs/OPRAVY_adapter_2026-09-05.md) — štyri opravy Freqtrade adaptéra a ich vplyv
- [tv_settings_2026-09-03.md](docs/tv_settings_2026-09-03.md), [chart_reference_BTCUSD_3m.md](docs/chart_reference_BTCUSD_3m.md) — nastavenia grafu a čo stratégia kreslí

---

## Pravidlá práce s repozitárom

- **Dáta** sa sťahujú len v oficiálnych timeframoch búrz a commitujú sa po rokoch do
  `data_archive/` príslušnej platformy; pracovné súbory zloží
  `python -m tester.data_archive merge` ([docs/DATA.md](docs/DATA.md)).
- **Backtest vždy s `--timeframe-detail 1m` a `--cache none`** — skripty to robia samy.
  Stratégiu nikdy nespúšťať priamo na 1m (limity `*MaxBars` sú v baroch).
- **Parita pred optimalizáciou**: každá zmena jadra musí prejsť golden testom
  (`pytest tester/tests/test_golden_tv_binance.py`). Rozšírenia mimo Pine majú default, pri ktorom
  sa správanie rovná Pine, a sú v `PORT_ONLY_FIELDS`.
- **Merania sa zapisujú** ako datované dokumenty v `docs/merania/` s číslami po rokoch, nie len
  súhrn — jeden rok o stratégii nič nepovie.
