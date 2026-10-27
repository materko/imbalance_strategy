# Repository layout: what goes where

In force since 27 Oct 2026. The layout follows one concept (below): the name of a directory
tells you **what a thing is**, never which language it is written in, and everything that
belongs to one thing lives in one place.

## The concept

### Vocabulary

| term | what it is | today |
|---|---|---|
| **engine** | an implementation of the strategy logic and its runtime, in one language | Python, C# |
| **platform** | where a strategy runs or trades | Freqtrade, MultiCharts, NinjaTrader 8, MetaTrader 5; TradingView is the origin (Pine) |
| **simulator** | a backtest with a platform's fill model | Freqtrade backtesting, MultiCharts emulator, NinjaTrader Strategy Analyzer, MT5 Strategy Tester |
| **adapter** | the code that connects an engine to a platform | `tradebot/adapters/<platform>/` |
| **strategy key** | the name of one strategy logic (`ibs`, `orb`, …) | see "Known deviations" |

Engine and platform are independent axes. **An engine runs natively in the platform's own
runtime**: Python platforms (Freqtrade — backtest and live crypto —, any future Python
framework, the Tester and its simulators) run the Python engine; .NET platforms (NinjaTrader 8,
MT5 through the DLL, MultiCharts .NET as the target) run the C# engine, because Python hosted
inside a foreign process is held back by its global interpreter lock. Both engines are
production engines. Python is also the reference: golden tests run against TradingView and
every other engine must match Python bar by bar (parity). The Python→C# bridge
(`tradebot/adapters/csharp`) lets C# strategies run on Python platforms for backtests and parity.

### One thing, one directory, languages inside

A thing (the core runtime, one strategy) is one directory. Its implementations in different
languages sit **together** in that directory:

- Python sits directly in the package, because the package *is* a Python package and Python
  is the host language of the repository (registry, StrategySpec, Tester, CLIs).
- Every other language has a subdirectory named after the language: `csharp/` today.

```
tradebot/core/                     the runtime
├── *.py                           contract + Python runtime
└── csharp/                        C# runtime
tradebot/strategies/ibs/           one strategy
├── __init__.py, config.py, params.py, configs/, docs/   description: spec, parameters, profiles, docs
├── engine.py, statemachine.py, ta/ …                     Python implementation
└── csharp/                                               C# implementation (IbsEngine.cs, Ta/ …)
```

A new language (say Rust) means `tradebot/core/rust/`, `tradebot/strategies/<key>/rust/`
and a bridge in `tradebot/adapters/`. Nothing else moves. The build collects the sources
wherever they lie (`tradebot.adapters.csharp.build` takes `core/csharp/` and every
`strategies/*/csharp/`).

### Dependencies point one way

```
adapters/<platform>  ──►  strategies/<key>  ──►  core
```

The core knows no strategy and no platform; a strategy knows no platform; an adapter knows
strategies only through `StrategySpec`, never by name. A new platform is one new directory in
`tradebot/adapters/` and touches no strategy.

### Known deviations (to be removed)

- **Platform glue inside strategies.** Every strategy package still carries `freqtrade.py`,
  `multicharts.py` and `hyperopt.py` (a few lines each, mostly just the key), and `deploy/`
  carries a template per strategy (`deploy/multicharts/*_Signal.py`,
  `deploy/freqtrade/user_data/strategies/*.py`). The adapters should derive them from
  `StrategySpec`.
- **`--engine freqtrade|multicharts`** names a platform, not an engine; it should become
  `--platform`, with the old switch kept as an alias.
- **The key encodes more than the logic.** `ibsnet` is `ibs` on the C# engine, `…eod` adds a
  15:59 NY close for prop accounts, `…es`/`…mgc` a market. The target: key = logic; the spec
  lists the engines a strategy has (`engines=("python", "csharp")`), EOD is a parameter, a
  market is a profile (a separate key only when the market brings its own logic or parameters).
  Old keys stay as aliases (`tradebot.strategies.ALIASES`), so the run history is not rewritten.
  Until then each C# key has a thin package (`ibsnet`, `ibsneteod`, …) whose SPEC points to the
  C# implementation in the package of its Python original (`csharp_dir`).
- **MultiCharts still runs the Python engine** (the first-generation adapter). As a .NET
  platform it belongs on the C# engine, like NinjaTrader and MT5.

## Five rules

1. **The repository root has a fixed list of entries** (table below). A new top-level
   directory is added only by changing this document and the README. Working projects,
   experiments and notes never go to the root.
2. **The whole product is in `tradebot/`**: the runtime in `core/` (Python and `csharp/`),
   strategies in `strategies/`, platforms in `adapters/`, live operations in `live/`.
3. **One thing, one directory, languages inside** — Python directly, other languages in a
   subdirectory named after the language (`csharp/`).
4. **All data is in `data/`.** Git carries only `data/archive/` (downloaded candles) and
   `data/live/` (closed months from live trading); everything else under `data/` is derived
   locally and ignored.
5. **Anything that belongs to a single strategy goes into its package**
   `tradebot/strategies/<key>/`: code in every language, profiles, analytics, brief, Pine
   source, tuning project, notes on settings. `docs/` holds only what applies across strategies.

## Repository root

| entry | what it is | area |
|---|---|---|
| `tradebot/` | the product: runtime (Python and C#), strategies (each with all its implementations), platform adapters, live trading | product |
| `tester/` | the Tester: web app, hub, analytics, data importers, plus its committed data (runs, profiles) | Tester |
| `deploy/` | what gets installed into platforms: Freqtrade, MultiCharts, NinjaTrader, MT5, hub agent | deployment |
| `docker/` | images and compose files (tests, Freqtrade, web app, hub, agent) | deployment |
| `data/` | candles and live data; in git only `archive/` and `live/` | data |
| `docs/` | manuals and documents that span strategies | documentation |
| `README.md`, `CLAUDE.md`, `CLAUDE.archive.md` | overview of the repository, instructions for Claude Code | documentation |
| `webapp.*`, `dukas-import.*`, `bento-import.*`, `ibkr-import.*`, `install-macos.sh` | launchers run from the root (testers have them in their guides and on the desktop) | launchers |
| `pyproject.toml`, `.github/`, `.gitignore`, `.gitattributes`, `.dockerignore`, `.env.example` | project settings, lint in CI | configuration |

Local only, ignored by git: `.venv/`, `data/tester/`, `data/quotemanager/`,
`data/ninjatrader/`, `tradebot/core/csharp/bin/`, `reports/`, `tester/hub_data/`,
`tester/live/`, `tester/agent.json`, `tester/runs/.index/`, `.claude/`, `.ibs-role`.

## Where does a new file go

| I have… | it goes to |
|---|---|
| a new strategy | `tradebot/strategies/<key>/` + a line in the registry ([STRATEGIE.md](STRATEGIE.md)) |
| a brief for a strategy that is yet to be built | `tradebot/strategies/<key>/docs/ZADANIE.md` |
| a tuning project for one strategy (sweeps, candidates, findings) | `tradebot/strategies/<key>/docs/projekt/` |
| Pine source, TradingView settings screenshots | `tradebot/strategies/<key>/docs/sources/`, `…/docs/tradingview/` |
| a C# implementation of a strategy | `tradebot/strategies/<original key>/csharp/` + for now a thin `<key>net` package and wrappers in `deploy/ninjatrader/`, `deploy/mt5/` |
| a profile that belongs to the repository (golden, starting point) | `tradebot/strategies/<key>/configs/` |
| a tester's own profile | `tester/profiles/` (the "Uložiť ako profil" button) |
| candles from a new source | `data/archive/tester/<source>/` via an importer, never by hand |
| a measurement with per-year numbers | `docs/merania/<TOPIC>_<date>.md` (`cli paper`) |
| a code audit, golden test, fixes after an audit | `docs/audity/` |
| market or idea research across strategies | `docs/prieskum/` |
| a manual that will be kept up to date | `docs/<TOPIC>.md` + a line in the README index |
| a new data source importer | `tester/<source>_import.py` + wrappers in the root |
| a hub plugin | `tester/hub/plugins/<name>/` ([HUB.md](HUB.md)) |
| an implementation in a new language | `tradebot/core/<language>/`, `tradebot/strategies/<key>/<language>/`, a bridge in `tradebot/adapters/` |
| a new platform | `tradebot/adapters/<platform>/` (+ `deploy/<platform>/` for what is installed into it) |
| a path the code will read | `tradebot/core/paths.py` — nowhere else |

---

## The whole tree

```
imbalance_strategy/
├── tradebot/        PRODUCT — what trades
│   ├── core/        runtime: engine contract + Python runtime; csharp/ = C# runtime
│   ├── strategies/  registry + one package per strategy (Python implementation, csharp/ where it exists)
│   ├── adapters/    one directory per platform: Freqtrade, MultiCharts (+ emulator), NinjaTrader, MT5;
│   │                plus the Python→C# bridge
│   ├── live/        live telemetry, deployment to trading PCs, order routing, Telegram
│   └── tests/
├── tester/          TESTER — how it is tested (web app, hub, analytics, importers) + run history
├── deploy/          what gets installed into Freqtrade, MultiCharts, NinjaTrader, MT5, hub agent
├── docker/          containers
├── data/            ALL DATA — archive/ and live/ in git, the rest derived locally
├── docs/            manuals; merania/, audity/, prieskum/ dated
└── *.sh, *.ps1, …   launchers and project configuration
```

### `tradebot/core/` — the runtime

```
core/
├── engine.py            strategy engine contract: one call per closed chart bar
├── types.py             basic data types (Bar, InstrumentSpec, …)
├── config.py            base StrategyConfig and profile loading
├── orders.py            what the engine tells the adapter: order intents, state events, market context
├── money.py             money of one trade and of a whole run — the single definition for both engines and analytics
├── risk.py              stop loss, take profit, position size, trailing (Pine lines 1944–2016)
├── history.py           ring buffer of bars with Pine indexing semantics
├── clock.py             sessions and time windows (exact replica of the Pine code)
├── candles.py           building higher timeframes from 1m — the one rule for every path
├── derived.py           registry of candles computed from 1m rather than downloaded
├── warmup.py            pre-history for the chart and for higher-TF indicators
├── ma.py, vwap.py       moving averages (SMA, EMA, RMA) and session VWAP, bar by bar
├── entry_*.py           shared entry layers: confirmation candle, order type, trend/volatility filter, sizing, drawing
├── drawing.py           platform-neutral drawing commands and palette
├── dukascopy.py         reading a raw Dukascopy 1m export and its padding rule
├── clr.py               pythonnet (CLR inside Python) housekeeping
├── env.py               TRADEBOT_* environment variables (old IBS_* still accepted)
├── version.py           short HEAD commit of the code
├── paths.py             every path in the repository — the only place paths are written
└── csharp/              the C# runtime:
    ├── TradeBot.Core/       engine contract, bar history, orders, sessions, VWAP, MAs, warmup, drawing,
    │                        EntryLayers, EodClose (15:59 NY close for prop accounts), Bridge (NT → MT5 routing),
    │                        Live (telemetry spool), StaticHost (static facade MQL5 can call)
    ├── TradeBot.Backtest/   native backtest over feather candles (MultiCharts emulator in C#)
    ├── TradeBot.Host/       TradeBot.Host.exe — the bridge without pythonnet
    └── bin/                 build output (TradeBot.dll, TradeBot.Host.exe) — ignored, built on demand
```

C# 5, no NuGet: compiled by `csc.exe` from .NET Framework, by Mono and by NinjaTrader
(`python -m tradebot.adapters.csharp.build`, which takes `core/csharp/` and every
`strategies/*/csharp/`). NinjaTrader gets the core and the strategies as sources
(`TradeBot.Strategies/<key>/` in its AddOn folder); MT5 gets the DLL.

### `tradebot/strategies/` — registry and strategy packages

```
strategies/
├── __init__.py          STRATEGIES (61 keys) and ALIASES (ibsninja, orbninja, trendline)
├── base.py              StrategySpec — how a strategy describes itself to the core and adapters
├── hyperopt.py          shared hyperopt helpers
└── <key>/               one package per strategy:
    ├── __init__.py      exports the SPEC for the registry
    ├── config.py        the strategy config (Pine defaults; PORT_ONLY_FIELDS for extensions outside Pine)
    ├── engine.py        the engine: one call per closed bar, returns order intents and drawings
    ├── params.py        parameter descriptions for the web app form
    ├── meta.py, drawing.py   metadata for the web app; what the strategy draws
    ├── freqtrade.py, multicharts.py, hyperopt.py   platform glue and hyperopt space (to move to adapters/)
    ├── ta/, htf.py, data.py  strategy-specific indicators, higher-TF feeder, extra symbols (where needed)
    ├── csharp/          the C# implementation, where it exists: <Name>Engine.cs, <Name>Config.cs, …,
    │                    each engine class tagged [TradeBotEngine("key")]; must match Python bar by bar
    ├── configs/         profiles that belong to the repository (golden, starting points)
    └── docs/
        ├── VYSVETLIVKA.md    what the strategy does, in plain words
        ├── ANALYTIKA.md      baseline analytics and verdict (`cli checkup`)
        ├── ZADANIE.md, PORT.md   brief / what changed in the port (where it applies)
        ├── sources/          Pine source (only on request)
        ├── tradingview/      reference settings and drawings from TradingView
        └── projekt/, <topic>/    tuning project, notes on particular settings (e.g. ibs/docs/rrr05/)
```

C# implementations live in the package of their Python original: `ibs/csharp`, `orb/csharp`,
`ibsentry/csharp`, `vwaporb/csharp`, `vwapadx/csharp`, `noa/csharp`, `tks/csharp`,
`fibo/csharp`, `nyva/csharp`, `sdeur/csharp`. For now every C# key also has a thin package
(`ibsnet`, `orbnet`, `…net`, `…neteod`) with its SPEC (`csharp_dir` points to the original's
`csharp/`), profiles and analytics — see "Known deviations".

### `tradebot/adapters/` and `tradebot/live/`

```
adapters/
├── freqtrade/           generic Freqtrade strategy (TradebotStrategyBase), EngineRunner over DataFrames,
│                        per-trade SL/TP/size callbacks, hyperopt plans, FreqAI filter, dry/live run
├── multicharts/         MultiCharts study (the only file touching PowerLanguage .NET), MCRunner,
│                        drawing, Data2 from CSV, and the MultiCharts emulator that runs anywhere
├── csharp/              bridge to the C# core (pythonnet or TradeBot.Host.exe) and its build
├── ninjatrader/         NinjaScript strategy + live add-on and feed, installer and compile check
└── mt5/                 MQL5 Expert Advisor, drawing, order executor, .set presets, installer
live/
├── schema.py, spool.py  telemetry event schema (mirror of core/csharp/TradeBot.Core/Live.cs), reading the platform spool
├── shipper.py, transport.py   sending the spool from the agent to the hub
├── store.py             sqlite store of live events (shared by the hub and the web app mirror)
├── deploy.py, apply.py  desired state on the hub (accounts, deployments) and reconciling a machine to it
├── drivers/             per-platform drivers on the agent (MT5, NinjaTrader 8, DPAPI secrets)
├── routes.py, bridge.py routing orders to the MT5 executor; manual master for testing it
├── journal.py, perf.py, reports.py, telegram.py   trade journal, performance, Telegram messages and commands
├── symbols.py, update.py, vault.py   symbol/TF from a profile, code updates on the trading PC, password encryption
└── __main__.py          manual check of the telemetry on a trading PC
```

### `tester/` — the Tester

Modules in the root of `tester/` are code; subdirectories are either code packages or data.

```
tester/
├── webapp/                  the web app (FastAPI + Plotly)
│   ├── app.py, __main__.py  application and server start (assembles data from the archive if missing)
│   ├── api/                 REST routers: runs, chart, profiles, sweeps, hyperopt, matrix, analytics,
│   │                        diversify, prop/paper, native C# runs, hub, live, git
│   ├── cli/                 `python -m tester.webapp.cli` — run, sweep, hyperopt, matrix, analysis, history, remote
│   ├── static/              the page: index.html, styles, js/
│   ├── runner.py, command.py, results.py, mc_worker.py   queue, Freqtrade command, results, emulator worker
│   ├── store.py, index.py   one directory per run; sqlite index of the history
│   ├── archive.py, prune.py archiving old runs (`cli archive`), trimming runs to what belongs in git
│   ├── gitsync.py           pull/push of the testers' data (runs, sweeps, profiles, analytics)
│   ├── chart.py, replay.py  chart data; drawings recomputed on demand from the stored config
│   ├── profiles.py, repo_profiles.py, param_meta.py, market.py   profiles, form metadata, markets and pairs
│   └── batches.py, hyperopt_job.py, anstore.py   batch results, hyperopt jobs, analytics history
├── hub/                     distributed computing
│   ├── server.py, state.py, plans.py, stats.py, events.py   hub, queue, plans, agent stats, event log
│   ├── agent.py, client.py, config.py   agent, submitter side, agent config (tester/agent.json)
│   ├── protocol.py, tokens.py, transfer.py, gitcode.py   job kinds, tokens, moving runs as zips, code version
│   ├── sparse.py, update.py, delivered.py, live.py   lean clone rules, hub self-update, delivered runs, live API
│   └── plugins/             code running inside the hub: livedata (live candles/trades → data/live/),
│                            watchdog (machines → Telegram), ff_calendar (ForexFactory news → Telegram)
├── compare/                 cross-platform checks: C# vs Python parity, native C# backtest, replay on Mono,
│                            MultiCharts log vs simulator, zone and trade scans
├── dashboard/               static results dashboard + its live section
├── tests/                   Tester tests, golden tests against TradingView (golden/), C# parity, MT5 facade, index
├── scripts/                 the web app launcher (wrapped by webapp.* in the root)
│
├── engines.py               the two engines (Freqtrade, MultiCharts emulator) and where each has data
├── ftexchange.py, ftrun.py  the fictitious "tester" exchange for Freqtrade and the wrapper that registers it
├── native.py, native_hyperopt.py   native runs and hyperopt of C# strategies on the emulator
├── ninjatrader.py           NinjaTrader 8: data in, signals out
├── dukas_import.py, bento_import.py, ibkr_import.py   importers: Dukascopy CFD, Databento CME futures, IBKR stocks
├── data_archive.py, timeframes.py, quotemanager.py   archive split/merge, deriving TFs from 1m, ASCII for QuoteManager
├── livedata.py, livesim.py  live candles and trades; joining them with downloaded data
├── checkup.py, analytics.py, character.py   baseline analytics and verdict, trade group analysis, strategy character
├── nulltest.py, decay.py, montecarlo.py, plateau.py, regime.py   vs. random, fading edge, Monte Carlo, plateau, market regime
├── trade_metrics.py, trade_features.py, trade_splits.py   basic numbers, trade features, splitting into groups
├── sweep.py, hyperopt.py, matrix.py   parameter grids, hyperopt, markets × timeframes matrix
├── portfolio.py, prop.py    portfolio of several runs, prop challenge simulation
├── paper.py, report.py, plot.py, fees.py   measurement document, Strategy-Tester-style report, plots, maker/taker
├── calendar.py, calendar_us.json   exchange holidays and macro events
├── synthetic.py, recompute.py, atomic.py   synthetic market, recomputing money of stored runs, atomic writes
├── timeframes.json          which timeframes the Tester keeps on disk
├── AI_TESTING.md            how to test from the command line (also for AI)
│
├── runs/                    DATA: run history — never bulk-delete; old runs go via `cli archive`
├── archive/                 DATA: archived runs (reversible with `--restore`)
├── sweeps/, analytics/      DATA: grid / hyperopt results and analytics
└── profiles/                DATA: testers' own profiles (incl. PRESIEL_SMERNICAMI_*)
```

### `deploy/` and `docker/` — deployment

```
deploy/
├── freqtrade/               exchange configs (binance, coinbase, dukascopy, tester…), scripts (setup, download,
│                            backtest, hyperopt for .ps1 and .sh), user_data/ (strategy shim, hyperopt loss)
├── multicharts/             study templates <Name>_Signal.py for each strategy, setup script
├── ninjatrader/             NinjaScript wrappers <Name>Net.cs (and …Eod.cs) for the C# strategies
├── mt5/                     Expert Advisors <Name>Net.mq5, TradeBotExecutor.mq5, ini/ for the Strategy Tester
└── agent/                   install / run / uninstall a hub agent on Windows
docker/                      Dockerfile.core, .freqtrade, .hub, .agent; compose files; hub entrypoint
```

### `data/` — all data

```
data/
├── archive/tester/          IN GIT — downloaded candles split by year, official timeframes only
│   ├── binance/futures, spot    BTC, ETH (Freqtrade downloads)
│   ├── coinbase/spot            BTC/USD
│   ├── databento/futures        CME MNQ, MGC, ES, 6E — front month by volume
│   ├── dukascopy/futures        CFD: NAS100, US500, DJ30, DAX, JP225, forex, XAU, oil, gas, softs
│   └── ibkr/futures             Mag7 stocks, 1m RTH
├── live/                    IN GIT — closed months from live trading, pushed by the hub
│   ├── candles/                 live candles (incl. 1m)
│   └── instances/               trades per live instance
├── tester/                  local — working copy of the archive + timeframes derived from 1m
├── quotemanager/            local — ASCII export for MultiCharts QuoteManager
└── ninjatrader/             local — history export for NinjaTrader
```

`data/archive/tester/` mirrors `data/tester/` path for path (`python -m tester.data_archive
merge|split`). Derived timeframes never go to the archive and live data never mixes with
downloaded data — they are joined only when read (`tester.livesim`). Details: [DATA.md](DATA.md).

### `docs/` — documentation

```
docs/
├── *.md                     living manuals (kept up to date): WEBAPP, API, DATA, STRATEGIE, ANALYTIKA,
│                            TYPY_STRATEGII, SMERNICA_TESTOVANIA, HYPEROPT, FREQTRADE, MULTICHARTS,
│                            NINJATRADER, MT5, ROUTING, LIVE, FEED, HUB, ARCHITEKTURA, ARCHITECTURE_port,
│                            RUNNING, DIRECTORIES (this file)
├── merania/                 dated measurements with per-year numbers on five reference windows
├── audity/                  dated audits, the golden test against TradingView, fixes after audits
├── prieskum/                market and idea research (gold, S&P 500, videos)
└── profily_archiv/ibs/      archive of tried IBS profiles
```

- Living manuals sit in the root of `docs/` in upper case; each has a line in the README index.
- Dated documents sit in subdirectories and are not changed after writing (except links).
- `profily_archiv/` stays in `docs/` even though it is IBS-only: thousands of runs in the
  history and the testers' guides refer to `--profile docs/profily_archiv/ibs/…`.

---

## Cleanup of 27 Oct 2026

What moved. Run history in `tester/runs/` is not rewritten, so old paths may remain there.

| was | is |
|---|---|
| `csharp/TradeBot.Core`, `TradeBot.Backtest`, `TradeBot.Host` | `tradebot/core/csharp/` |
| `csharp/TradeBot.Strategies/<Name>Net/` | `tradebot/strategies/<original key>/csharp/` (e.g. `IbsNet` → `ibs/csharp`) |
| `data_archive/` | `data/archive/` |
| `data_live/` | `data/live/` |
| `projekty/ORB/` | `tradebot/strategies/orb/docs/projekt/` |
| `docs/zadania/STRUKTURA_strategia.md` | `tradebot/strategies/structure/docs/ZADANIE.md` |
| `docs/0.5_*.md` (IBS at RRR 0.5) | `tradebot/strategies/ibs/docs/rrr05/` |
| `docs/cely_kod_original.rtf` | `tradebot/strategies/ibs/docs/sources/` |
| `docs/tv_settings_2026-09-03.md`, `docs/chart_reference_BTCUSD_3m.md` | `tradebot/strategies/ibs/docs/tradingview/` |
| `docs/AUDIT_*.md`, `docs/GOLDEN_binance_2026-08-24.md`, `docs/OPRAVY_adapter_2026-09-05.md` | `docs/audity/` |

Existing clones: lean clones of hub agents switch their sparse-checkout rules to the new
paths on agent start (`tester.hub.sparse.migrate_legacy`). The hub reads its rules from its
own clone since the same day, so its image has to be rebuilt once.
