# TradeBot — porty TradingView stratégií do Freqtrade a MultiCharts

Rámec pre viac stratégií: **jedno generické jadro** (`tradebot/core`), **registry stratégií**
(`tradebot/strategies`, každá s vlastným Pine zdrojom, configom, enginom a profilmi) a dva tenké
adaptéry — **Freqtrade** (krypto futures, Binance) a **MultiCharts** (MNQ, akcie, forex) — plus
webová aplikácia pre testerov. Cieľ je rovnaké obchody aj rovnaké vykreslovanie ako
v TradingView; parita je overená golden testom na cent
([GOLDEN_binance_2026-08-24.md](docs/GOLDEN_binance_2026-08-24.md)).

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
.venv/bin/python -m pytest                        # 315 testov vrátane parity s Pine
```

Docker, sťahovanie dát, hyperopt, MultiCharts a riešenie problémov: [docs/RUNNING.md](docs/RUNNING.md).

---

## Mapa repozitára

| Cesta | Čo tam je |
|---|---|
| [`pine/`](pine) | Pine zdroje stratégií: `imbalance_strategy_FULL.pine` (**referenčný IBS**, v5, 115 vstupov — zdroj pravdy pre logiku, defaulty aj tooltipy; staršie buildy `imbalance_strategy_SD_IMB.pine` a `Imbalance_strategy.pine` sú len na porovnanie) a `demo_breakout.pine`. |
| [`tradebot/core/`](tradebot/core) | Generické jadro bez závislostí: `StrategyConfig` (báza configu, profily), `Engine`/`EngineOutput`, `OrderIntent`/`TradePlan`, `BarHistory`, hodiny seáns, `DrawCommand` + `DrawKind` registr, inštrumenty. |
| [`tradebot/strategies/`](tradebot/strategies) | Registry `STRATEGIES` a jedna stratégia = jeden balík: `ibs/` (config, engine, stavový automat zón, `ta/`, HTF feeder, Freqtrade a MultiCharts podtriedy, meta pre webapp), `demo_breakout/`. Postup: [docs/STRATEGIE.md](docs/STRATEGIE.md). |
| [`tradebot/adapters/freqtrade/`](tradebot/adapters/freqtrade) | Generická Freqtrade stratégia `TradebotStrategyBase` + `EngineRunner` (engine nad DataFrame, fill model) + export kresieb. |
| [`tradebot/adapters/multicharts/`](tradebot/adapters/multicharts) | Generická študia `TradebotSignal`, `MCRunner` a kreslenie (len Windows). |
| [`tradebot/configs/<stratégia>/`](tradebot/configs) | JSON profily — len odchýlky od Pine defaultov, viď nižšie. |
| [`tradebot/webapp/`](tradebot/webapp) | Webová aplikácia pre testerov (FastAPI + Plotly). |
| [`tradebot/tools/`](tradebot/tools) | `report` (HTML ako Strategy Tester), `fees` (maker/taker, break-even), `scan_trades`/`scan_zones` (diagnostika), `data_archive` (ročné súbory dát), `plot`. |
| [`tradebot/tests/`](tradebot/tests) | Testy jadra, adaptérov, webapp a **golden testy** proti TradingView (`golden/`). |
| [`platforms/freqtrade/`](platforms/freqtrade) | Freqtrade configy (`config.binance.json`, `config.coinbase.json`), skripty, `user_data/` (shim na stratégiu v `strategies/`, hyperopt loss, `data_archive/` so sviečkami, `runs/` s históriou behov z webapp). |
| [`platforms/multicharts/`](platforms/multicharts) | Šablóny študií pre MultiCharts (`IBS_Signal.py`, `DemoBreakout_Signal.py`) a inštalačný skript. |
| [`docker/`](docker) | `docker-compose.yml` (tests, download, backtest, freqtrade bot, webapp). |
| `webapp.cmd`, `webapp.ps1`, `webapp.sh` | Spúšťače webapp z koreňa repozitára (obaly nad `platforms/freqtrade/scripts/`). |
| [`CLAUDE.md`](CLAUDE.md) | Pokyny pre Claude Code v dvoch režimoch podľa `.ibs-role` (gitignored, pýta sa raz): **tester** = backtesty do histórie cez `python -m tradebot.webapp.cli`, reštart a aktualizácia webapp, Pull/Push histórie, bez zásahov do kódu; **developer** = bez obmedzení, len konvencie. |
| `install-macos.sh` | Inštalátor pre macOS jedným príkazom (`curl \| bash`): Homebrew, Python, TA-Lib, klon, venv, dáta, spúšťač na Ploche. |
| [`docs/`](docs) | Architektúra, návody, parita a všetky merania (zoznam nižšie). |

---

## Profily (`tradebot/configs/<stratégia>/`)

Profil = Pine defaulty stratégie + odchýlky + `_strategy` + `_instrument`. Prepína sa cez
`TRADEBOT_PROFILE=<meno alebo cesta>` alebo vo webapp. Profily IBS (`tradebot/configs/ibs/`):

| Profil | Na čo |
|---|---|
| `golden_binance_btcusdt_3m` | **Referenčný na golden test** — presne nastavenia z grafu TradingView na Binance BTCUSDT.P (RR 1, trailing, 1 BTC). Nie na obchodovanie. |
| `golden_coinbase_btcusd_3m` | Referenčný pre Coinbase BTCUSD — parita jadra s TradingView screenshotmi (MultiCharts a testy). |
| `multicharts_mnq_3m` | MNQ futures pre MultiCharts, 1:1 s Pine jednotkami. |
| `demo_breakout/binance_btcusdt_5m` | Jediný profil ukážkovej stratégie (Pine defaulty, páka 5). |
| ostatné | Skúšané konfigurácie (NY seansa, SL filter, risk sizing, hyperopt…) sú v [docs/profily_archiv/](docs/profily_archiv/ibs/README.md) s tabuľkou odchýlok; načítajú sa cestou (`--profile docs/profily_archiv/ibs/<nazov>.json`). Odporúčaný štart na nasadenie je `btcusdt_3m_binance_ny_sl_risk1` odtiaľ. |

---

## Kde sme s výsledkami (2026-09-05)

Kľúčové číslo je **break-even poplatok** — koľko smie burza brať na stranu, aby stratégia vyšla
na nulu. Binance taker berie 0,05 %. Päť rokov BTC/USDT.P 3m, bez poplatkov, 1 BTC na obchod:

| krok | break-even | obchodov / rok | dokument |
|---|---|---|---|
| pôvodné nastavenie (RR 1, trailing) | 0,0050 % | 166 | [BACKTEST_rok_btcusdt](docs/BACKTEST_rok_btcusdt_2026-09-04.md) |
| RR 5, bez trailingu, `slLookback` 20 | 0,0226 % | 203 | [SWEEP_rr_a_tf](docs/SWEEP_rr_a_tf_2026-09-04.md) |
| + štruktúrny filter (BOS/CHoCH) | 0,0423 % | 96 | [FILTRE_vstupu](docs/FILTRE_vstupu_2026-09-04.md) |
| + len NY seansa | 0,0879 % | 43 | [SEANSY](docs/SEANSY_2026-09-05.md) |
| **+ `minSlDistance` 0,20 % ceny** | **0,1410 %** | **30** | [OPTIMALIZACIA](docs/OPTIMALIZACIA_2026-09-05.md) |

Každý krok zdvojnásobil edge tým, že **odobral** obchody, nie že pridal. Ladenie prahov
hyperoptom overfitovalo; prežili len binárne rozhodnutia s mechanizmom. NY seansa aj filter SL
sa potvrdili **bez ladenia na ETH** (break-even 0,056 → 0,096 %).

S reálnymi poplatkami a risk-based sizingom 1 % účtu (`*_ny_sl_risk1`): BTC **+42,8 %** za päť
rokov (3 z 5 rokov ziskové, max DD 12 %), ETH **+40,5 %** (4 z 5, max DD 8 %). Bez filtra SL
je ten istý sizing +0,2 % — filter a risk sizing patria k sebe.

Čo nefunguje: shorty (PF < 1), londýnska seansa (edge 0), volume filter, trendové HTF filtre,
časový stop, vyšší timeframe grafu, ATR ako jednotka filtra SL, páka (mení len mierku).

---

## Dokumentácia

**Návody a architektúra**

- [RUNNING.md](docs/RUNNING.md) — Docker, venv, dáta, backtest, hyperopt, MultiCharts, riešenie problémov
- [WEBAPP.md](docs/WEBAPP.md) — webová aplikácia pre testerov
- [ARCHITECTURE_port.md](docs/ARCHITECTURE_port.md) — návrh jadra a adaptérov, rozhodnutia, rozšírenia mimo Pine

**Parita s TradingView**

- [GOLDEN_binance_2026-08-24.md](docs/GOLDEN_binance_2026-08-24.md) — golden test: zóny, obchody, kresby, Elliott sedia na cent
- [AUDIT_pine_2026-09-05.md](docs/AUDIT_pine_2026-09-05.md) — systematický prechod Pine skriptu, čo chýbalo
- [OPRAVY_adapter_2026-09-05.md](docs/OPRAVY_adapter_2026-09-05.md) — štyri opravy Freqtrade adaptéra a ich vplyv
- [tv_settings_2026-09-03.md](docs/tv_settings_2026-09-03.md), [chart_reference_BTCUSD_3m.md](docs/chart_reference_BTCUSD_3m.md) — nastavenia grafu a čo stratégia kreslí

**Merania (chronologicky)**

- [BACKTEST_rok_btcusdt_2026-09-04.md](docs/BACKTEST_rok_btcusdt_2026-09-04.md) — rok s reálnymi poplatkami, prečo ich RR 1 neunesie
- [BACKTEST_rok_rr25_all3_2026-09-04.md](docs/BACKTEST_rok_rr25_all3_2026-09-04.md) — RR 2,5, tri entry modely, trailing
- [SWEEP_rr_a_tf_2026-09-04.md](docs/SWEEP_rr_a_tf_2026-09-04.md) — RR pomer a timeframe grafu
- [HYPEROPT_btcusdt_2026-09-04.md](docs/HYPEROPT_btcusdt_2026-09-04.md), [HYPEROPT_uzky_2026-09-04.md](docs/HYPEROPT_uzky_2026-09-04.md) — široký hyperopt overfituje, úzky nenašiel nič
- [HYPOTEZA_koniec_seansy_2026-09-04.md](docs/HYPOTEZA_koniec_seansy_2026-09-04.md) — kde vznikajú straty
- [FILTRE_vstupu_2026-09-04.md](docs/FILTRE_vstupu_2026-09-04.md) — štruktúrny a volume filter
- [SEANSY_2026-09-05.md](docs/SEANSY_2026-09-05.md) — NY má edge, Londýn nie; hodiny neladiť
- [PAKA_2026-09-05.md](docs/PAKA_2026-09-05.md) — páka mení mierku, nie edge
- [EXEKUCIA_maker_taker_2026-09-05.md](docs/EXEKUCIA_maker_taker_2026-09-05.md) — koľko príkazov by ležalo v knihe
- [OPTIMALIZACIA_2026-09-05.md](docs/OPTIMALIZACIA_2026-09-05.md) — filter tesného SL, regime filtre, časový stop, ETH, ATR vs %, risk sizing

---

## Pravidlá práce s repozitárom

- **Dáta** sa sťahujú len v oficiálnych timeframoch búrz a commitujú sa po rokoch do
  `platforms/freqtrade/user_data/data_archive/`; pracovné súbory zloží `python -m tradebot.tools.data_archive merge`.
- **Backtest vždy s `--timeframe-detail 1m` a `--cache none`** — skripty to robia samy.
  Stratégiu nikdy nespúšťať priamo na 1m (limity `*MaxBars` sú v baroch).
- **Parita pred optimalizáciou**: každá zmena jadra musí prejsť golden testom
  (`pytest tradebot/tests/test_golden_tv_binance.py`). Rozšírenia mimo Pine majú default, pri ktorom
  sa správanie rovná Pine, a sú v `PORT_ONLY_FIELDS`.
- **Merania sa zapisujú** ako datované dokumenty v `docs/` s číslami po rokoch, nie len súhrn —
  jeden rok o stratégii nič nepovie.
