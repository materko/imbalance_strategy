# TradeBot — stratégie z TradingView a videí do Pythonu a C#, backtest aj obchod naživo

Repozitár sú **dva celky**:

| | čo to je | kde |
|---|---|---|
| **TradeBot** | produkt, ktorý obchoduje: generické jadro, registry stratégií a tenké adaptéry — **Freqtrade** (krypto), **MultiCharts** (Python študia), **NinjaTrader 8** a **MetaTrader 5** (stratégie s jadrom v C#). Jadro ani adaptéry nepoznajú stratégiu menom — všetko ide cez `StrategySpec`. | [`tradebot/`](tradebot), [`csharp/`](csharp) |
| **TradeBot Tester** | čím sa to skúša: dáta, backtesty do zdieľanej histórie, webová aplikácia, analytika a smernica testovania, porovnania platforiem, **hub** na počítanie na viac strojoch a **Live** karta s telemetriou bežiacich stratégií. | [`tester/`](tester) |

Závislosť ide jedným smerom — Tester importuje `tradebot`, produkt o Testeri nevie.

```
TradingView / video / zadanie ──► tradebot/strategies/<key>  (Python predloha, oba enginy)
                                         │  parita bar po bare
                                         ▼
                                  csharp/…/<Meno>Net  (C# 5 jadro)
                                         │
              ┌──────────────────────────┼───────────────────────────┐
         NinjaTrader 8             MetaTrader 5 (EA)          Freqtrade / webapp (most)
              └──────── telemetria (spool) ──► hub ──► webapp, karta Live ───┘
```

---

## Stratégie

V registry je **61 stratégií** (vrátane C# prepisov a ich EOD kópií pre prop účty). Úplný
zoznam s popisom a počtom parametrov: [docs/STRATEGIE.md](docs/STRATEGIE.md); ako sa
pridáva ďalšia, kontrakt enginu a definícia hotového tamtiež. Webapp ich triedi podľa trhu
a typu (`STRATEGIA_TRH_TYP` v [`settings.js`](tester/webapp/static/js/settings.js)):

| trh | trendové | skalpovacie | rangeové | **LIVE** (C# jadro → NT8, MT5) |
|---|---|---|---|---|
| **NASDAQ** (MNQ, NAS100) | `structure` `orb` `range` `breakout` `trendlines` `vwapadx` `voltbreak` `onbiasorb` `vwapop` `vwaporb` `jss` `fibo` `mag7` `dailyopen` `noa` `tks` `nocpon` | `ibs` `ibszones` `ibsentry` `ibsfvg` `scalp3ma` `fvgpolarity` `silverbullet` | `gap` `sdzone` `divergence` `liquidity` `vwapdrift` `crt` `svp` `percoco` `fpc` `sweepfvg` `sweepengulf` `varev` | `ibsnet` `orbnet` `ibsentrynet` `vwaporbnet` `vwapadxnet` `noanet` `tksnet` (päť z nich aj ako `…eod`) |
| **ZLATO** (MGC) | `fibomgc` | `ibsentrymgc` `fvgpolaritymgc` `scalp3mamgc` | | `fibomgcnet` |
| **S&P 500** (ES) | `nyvaes` | `ibsentryes` | | `ibsentryesnet` `nyvaesnet` |
| **EURUSD** (6E) | | | `sdeur` `asiasweep` | `sdeurnet` |

Mimo trhov je len ukážková `demo_breakout`. Staré kľúče `ibsninja`, `orbninja` a
`trendline` sú aliasy (`tradebot.strategies.ALIASES`), história sa neprepisuje.

Každá stratégia sa píše **pre oba Python enginy** (Freqtrade aj emulátor MultiCharts) a má
vlastnú základnú analytiku s posudkom (`tradebot/strategies/<key>/docs/ANALYTIKA.md`,
[docs/ANALYTIKA.md](docs/ANALYTIKA.md)). Do **LIVE** ide stratégia prepisom do C# jadra,
ktorý musí s Python predlohou sedieť bar po bare ([docs/NINJATRADER.md](docs/NINJATRADER.md)).

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

Vo webapp vyberieš stratégiu (podľa trhu a typu), nastavíš parametre, pár a obdobie,
spustíš backtest a vidíš výsledky, graf výnosnosti, graf páru so všetkým, čo engine
nakreslil, a zoznam obchodov. Ďalej sweep, hyperopt, analytika, diverzifikácia (aj živých behov),
karta **Hub** (výpočty na iných strojoch) a **Live** (bežiace stratégie v NT8 / MT5).
História behov sa zdieľa cez git a hľadá sa v nej podľa parametrov.
Podrobne: [docs/WEBAPP.md](docs/WEBAPP.md), z príkazového riadku [tester/AI_TESTING.md](tester/AI_TESTING.md).

### Vývojár — venv, testy, backtest z príkazového riadku

```powershell
.\deploy\freqtrade\scripts\setup.ps1             # .venv + freqtrade + tradebot (Windows)
.venv\Scripts\python.exe -m tester.webapp.cli run --strategy ibs --note "čo testujem"
```
```bash
./deploy/freqtrade/scripts/setup.sh              # macOS / Linux
.venv/bin/python -m pytest -q                    # ~4000 testov vrátane golden a C# parity
python -m tradebot.adapters.csharp.build --force # preklad C# jadra (csc.exe / Mono)
```

Pred pushom musí prejsť lint z [`.github/workflows/lint.yml`](.github/workflows/lint.yml):
`ruff check .`, ESLint skriptov webapp a preklad C# jadra.

### Dáta

Archív sviečok je po rokoch v [`data_archive/tester/`](data_archive/tester), len oficiálne
timeframy zdrojov; vyššie TF si Tester dopočíta z 1m sám
([`tester/timeframes.json`](tester/timeframes.json)):

| zdroj | čo | importér |
|---|---|---|
| Binance, Coinbase | BTC, ETH — futures perpetuály aj spot | sťahuje Freqtrade |
| Databento | CME futures `MNQ`, `MGC`, `ES`, `6E` — front-month podľa objemu | `./bento-import.sh` · `.\bento-import.ps1` |
| Dukascopy | CFD: indexy (NAS100, US500, DJ30, DAX, JP225), forex, zlato, komodity | `./dukas-import.sh` · `.\dukas-import.ps1` |
| IBKR | americké akcie Mag7, 1m RTH | `./ibkr-import.sh` · `.\ibkr-import.ps1` |

Sviečky a obchody stratégií naživo drží hub a uzavreté mesiace pushne do `data_live/`.
Celá cesta dát: [docs/DATA.md](docs/DATA.md), [docs/ARCHITEKTURA.md](docs/ARCHITEKTURA.md).

---

## Rozcestník dokumentácie

| chcem… | kam |
|---|---|
| spúšťať backtesty, pozerať a zdieľať históriu | [docs/WEBAPP.md](docs/WEBAPP.md) |
| testovať z CLI (aj pre AI) | [tester/AI_TESTING.md](tester/AI_TESTING.md) |
| volať webapp zo skriptu alebo z AI | [docs/API.md](docs/API.md) |
| pridať ďalšiu stratégiu, zoznam stratégií | [docs/STRATEGIE.md](docs/STRATEGIE.md) |
| vedieť, kedy stratégia prešla (smernica testovania) | [docs/SMERNICA_TESTOVANIA.md](docs/SMERNICA_TESTOVANIA.md) |
| čo tá stratégia je, v čom je dobrá, kde má chyby | [docs/ANALYTIKA.md](docs/ANALYTIKA.md), [docs/TYPY_STRATEGII.md](docs/TYPY_STRATEGII.md) |
| hľadať parametre (sweep, hyperopt, FreqAI) | [docs/HYPEROPT.md](docs/HYPEROPT.md) |
| krypto: prostredie, backtest, Docker, server | [docs/FREQTRADE.md](docs/FREQTRADE.md) |
| MultiCharts: študia, QuoteManager, emulátor | [docs/MULTICHARTS.md](docs/MULTICHARTS.md) |
| NinjaTrader 8 a C# jadro | [docs/NINJATRADER.md](docs/NINJATRADER.md) |
| MetaTrader 5 nad tým istým C# jadrom | [docs/MT5.md](docs/MT5.md) |
| stratégia v NinjaTraderi, ordery v MT5 | [docs/ROUTING.md](docs/ROUTING.md) |
| telemetria bežiacich stratégií (karta Live) | [docs/LIVE.md](docs/LIVE.md) |
| zdieľať trhy medzi NT8 a MT5 (návrh) | [docs/FEED.md](docs/FEED.md) |
| počítať na viac strojoch (hub, agenti, pluginy) | [docs/HUB.md](docs/HUB.md), [deploy/agent/](deploy/agent/README.md) |
| dáta: archív, importy, nový symbol | [docs/DATA.md](docs/DATA.md) |
| prehľad architektúry a cesty dát | [docs/ARCHITEKTURA.md](docs/ARCHITEKTURA.md), návrh portu [docs/ARCHITECTURE_port.md](docs/ARCHITECTURE_port.md) |
| kde čo beží (venv, Docker, Windows) | [docs/RUNNING.md](docs/RUNNING.md) |
| čísla z meraní | [docs/merania/](docs/merania/README.md) |
| prieskum trhov a stratégií (zlato, S&P 500, videá) | [docs/prieskum/](docs/prieskum/README.md) |

Audity: [architektúra 2026-10-25](docs/AUDIT_architektura_2026-10-25.md),
[smerovanie NT → MT5 2026-10-26](docs/AUDIT_routing_2026-10-26.md),
[main 2026-09-17](docs/AUDIT_main_2026-09-17.md), [Pine 2026-09-05](docs/AUDIT_pine_2026-09-05.md).

---

## Mapa repozitára

| Cesta | Čo tam je |
|---|---|
| **TradeBot — produkt** | |
| [`tradebot/core/`](tradebot/core) | Generické jadro: `StrategyConfig`, `Engine`/`EngineOutput`, `OrderIntent`/`TradePlan`, `BarHistory`, hodiny seáns, kreslenie, inštrumenty, VWAP, skladanie TF z 1m (`candles`), obaly vstupov (`entry_*.py`), `paths.py` so všetkými cestami repozitára. |
| [`tradebot/strategies/`](tradebot/strategies) | Registry `STRATEGIES` + aliasy; jedna stratégia = jeden sebestačný balík (engine, config, `params.py`, meta, `configs/` s profilmi, `docs/`). |
| [`tradebot/adapters/freqtrade/`](tradebot/adapters/freqtrade) | Generická `TradebotStrategyBase` + `EngineRunner` (engine nad DataFrame, fill model). |
| [`tradebot/adapters/multicharts/`](tradebot/adapters/multicharts) | Študia `TradebotSignal`, `MCRunner`, kreslenie (Windows) a **emulátor** MultiCharts (beží všade). |
| [`csharp/`](csharp) | `TradeBot.Core` (jadro, `EntryLayers`, `EodCloseEngine`, `Bridge` pre smerovanie) a `TradeBot.Strategies` (`IbsNet`, `OrbNet`, `IbsEntryNet`, `VwapOrbNet`, `VwapAdxNet`, `NoaNet`, `TksNet`, `FiboNet`, `NyVaNet`, `SdEurNet`) — C# 5 bez NuGet. |
| [`tradebot/adapters/csharp/`](tradebot/adapters/csharp) | Most: C# engine sa javí ako Python engine (pythonnet alebo `TradeBot.Host.exe`) — beží pod Freqtrade, v emulátore aj vo webapp; preklad (`build`). |
| [`tradebot/adapters/ninjatrader/`](tradebot/adapters/ninjatrader), [`deploy/ninjatrader/`](deploy/ninjatrader) | Generická NinjaScript stratégia + inštalácia; tenké obaly stratégií pre NT8. |
| [`tradebot/adapters/mt5/`](tradebot/adapters/mt5), [`deploy/mt5/`](deploy/mt5) | Expert Advisor v MQL5 nad fasádou `StaticHost`, kreslenie, exekútor `TradeBotExecutor`; obaly EA a `.ini` pre Strategy Tester. |
| [`tradebot/live/`](tradebot/live) | Live telemetria (spool platformy → agent → hub → sqlite), nasadenie profilov a účtov na stroje (`apply`, `deploy`, ovládače platforiem), ručný master smerovania (`bridge`), Telegram. |
| [`tradebot/tests/`](tradebot/tests) | Testy produktu. |
| **TradeBot Tester** | |
| [`tester/webapp/`](tester/webapp) | Webová aplikácia (FastAPI + Plotly), jej CLI a sqlite index histórie. |
| [`tester/hub/`](tester/hub) | Hub a agenti (distribuované behy, aktualizácie, pluginy `livedata`, `watchdog`, `ff_calendar`). |
| `tester/livedata.py`, `tester/livesim.py`, [`tester/dashboard/`](tester/dashboard) | Živé sviečky a obchody z hubu, spojenie so stiahnutými dátami, dashboard. |
| `tester/*_import.py`, `tester/data_archive.py`, `tester/timeframes.py`, `tester/quotemanager.py` | Importy (Dukascopy, Databento, IBKR), ročný archív, dopočet TF, ASCII pre QuoteManager. |
| `tester/analytics*`, `checkup.py`, `character.py`, `nulltest.py`, `decay.py`, `montecarlo.py`, `paper.py` | Základná analytika a posudok stratégie, test proti náhode, slabnúci edge, Monte Carlo, dokument merania. |
| `tester/sweep.py`, `hyperopt.py`, `native_hyperopt.py`, `matrix.py`, `plateau.py`, `portfolio.py`, `prop.py` | Hľadanie parametrov, matica behov, plató, diverzifikácia, prop pravidlá. |
| [`tester/compare/`](tester/compare) | Porovnania platforiem a parita C# ↔ Python (`csharp_parity`). |
| [`tester/tests/`](tester/tests) | Testy Testera, **golden testy** proti TradingView, parita C#, MT5 fasáda, index. |
| `tester/runs/`, `tester/profiles/`, `tester/archive/` | História behov, vlastné profily (vrátane `PRESIEL_SMERNICAMI_*`) a odložené staré behy. |
| **Ostatné** | |
| [`deploy/freqtrade/`](deploy/freqtrade), [`deploy/multicharts/`](deploy/multicharts), [`deploy/agent/`](deploy/agent) | Configy búrz a skripty Freqtrade, šablóny študií MultiCharts, inštalácia agenta hubu. |
| [`docker/`](docker) | Obrazy a compose pre testy, Freqtrade, webapp, hub a agenta. |
| `data_archive/tester/`, `data_live/` | Stiahnuté sviečky po rokoch; uzavreté mesiace z naživo. |
| `webapp.*`, `dukas-import.*`, `bento-import.*`, `ibkr-import.*`, `install-macos.sh` | Spúšťače z koreňa repozitára. |
| [`CLAUDE.md`](CLAUDE.md) | Pokyny pre Claude Code v režime **tester** / **developer** (`.ibs-role`). |
| [`docs/`](docs) | Návody, architektúra, audity; merania v [`docs/merania/`](docs/merania/README.md), archív profilov v [`docs/profily_archiv/`](docs/profily_archiv/ibs/README.md). |

---

## Kde sme (2026-10-27)

- **Výber stratégií** ide cez [smernicu testovania](docs/SMERNICA_TESTOVANIA.md) — séria
  skúšok, ktoré môžu stratégiu „zabiť" (päť okien, náhoda, Monte Carlo, náklady, …).
  Nastavenia, ktoré prešli, sú profily `PRESIEL_SMERNICAMI_*` a webapp ich označí
  „✓ smernica" (VWAP ORB, VWAP ADX, Volt Break, Volume Profile POC, Fibo MGC, NY VA ES, IBS EZ ES, …).
- **Naživo**: stratégie s C# jadrom bežia v NinjaTraderi 8 a MetaTraderi 5 a hlásia sa na
  kartu Live cez hub ([docs/LIVE.md](docs/LIVE.md)). Smerovanie „stratégia v NT, ordery v MT5"
  má hotovú fázu 1, exekútor a AddOn sú napísané, ale **na MT5 účte ešte neoverené**
  ([docs/ROUTING.md](docs/ROUTING.md), audit [2026-10-26](docs/AUDIT_routing_2026-10-26.md)).
- **Parita**: Python port sedí s TradingView na cent (golden test,
  [GOLDEN_binance_2026-08-24](docs/GOLDEN_binance_2026-08-24.md)); C# jadro sedí s Python
  predlohou bar po bare (`tester/tests/test_csharp_parity*.py`).
- **Pôvodná IBS na krypte** (BTC/ETH, september 2026): filtre NY seansy a tesného SL
  zdvihli break-even poplatok z 0,005 % na 0,141 %; s risk sizingom 1 % BTC +42,8 % a ETH
  +40,5 % za päť rokov. Celý príbeh po rokoch: [docs/merania/](docs/merania/README.md),
  posledný prepočet po audite [PREPOCET_po_audite_2026-10-26](docs/merania/PREPOCET_po_audite_2026-10-26.md).

---

## Pravidlá práce s repozitárom

- **Backtest vždy s `--timeframe-detail 1m` a `--cache none`** (skripty to robia samy);
  stratégiu nikdy nespúšťať priamo na 1m grafe (limity `*MaxBars` sú v baroch).
- **Parita pred optimalizáciou**: zmena jadra musí prejsť golden testom
  (`pytest tester/tests/test_golden_tv_binance.py`), zmena logiky stratégie s C# prepisom
  tú istú zmenu v C# a paritu bar po bare. Rozšírenia mimo Pine majú default zhodný s Pine
  (`PORT_ONLY_FIELDS`).
- **Dáta** sa sťahujú len v oficiálnych timeframoch a commitujú sa po rokoch; dopočítané
  do archívu nejdú ([docs/DATA.md](docs/DATA.md)).
- **Merania** sú datované dokumenty v `docs/merania/` s číslami po rokoch na piatich
  referenčných oknách — jeden rok o stratégii nič nepovie.
- **História behov** sa nemaže hromadne; staré behy sa odkladajú `cli archive` (vratné).
- **README sa aktualizuje pri každej významnej zmene** — nová stratégia, platforma,
  adaptér, služba, zdroj dát alebo dokument v rozcestníku; spolu s tým zmeniť aj
  dátum v „Kde sme".
