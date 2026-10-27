# Repository layout: what goes where

In force since 27 Oct 2026. The name of a directory should tell you whether it holds
**product code**, **Tester code**, **deployment**, **data** or **documentation**, and
everything that belongs to one strategy should live with that strategy.

## Four rules

1. **The repository root has a fixed list of entries** (table below). A new top-level
   directory is added only by changing this document and the README. Working projects,
   experiments and notes never go to the root.
2. **The whole product is in `tradebot/`** — the Python core and the C# core alike. They are
   two implementations of one engine contract, so they sit side by side.
3. **All data is in `data/`.** Git carries only `data/archive/` (downloaded candles) and
   `data/live/` (closed months from live trading); everything else under `data/` is derived
   locally and ignored.
4. **Anything that belongs to a single strategy goes into its package**
   `tradebot/strategies/<key>/`: code, profiles, analytics, brief, Pine source, tuning
   project, notes on settings. `docs/` holds only what applies across strategies.

## Repository root

| entry | what it is | area |
|---|---|---|
| `tradebot/` | the product: Python core, C# core (`tradebot/csharp/`), strategies, platform adapters, live trading | product |
| `tester/` | the Tester: web app, hub, analytics, data importers, plus its committed data (runs, profiles) | Tester |
| `deploy/` | what gets installed into platforms: Freqtrade, MultiCharts, NinjaTrader, MT5, hub agent | deployment |
| `docker/` | images and compose files (tests, Freqtrade, web app, hub, agent) | deployment |
| `data/` | candles and live data; in git only `archive/` and `live/` | data |
| `docs/` | manuals and documents that span strategies | documentation |
| `README.md`, `CLAUDE.md`, `CLAUDE.archive.md` | overview of the repository, instructions for Claude Code | documentation |
| `webapp.*`, `dukas-import.*`, `bento-import.*`, `ibkr-import.*`, `install-macos.sh` | launchers run from the root (testers have them in their guides and on the desktop) | launchers |
| `pyproject.toml`, `.github/`, `.gitignore`, `.gitattributes`, `.dockerignore`, `.env.example` | project settings, lint in CI | configuration |

Local only, ignored by git: `.venv/`, `data/tester/`, `data/quotemanager/`,
`data/ninjatrader/`, `tradebot/csharp/bin/`, `reports/`, `tester/hub_data/`,
`tester/live/`, `tester/agent.json`, `tester/runs/.index/`, `.claude/`, `.ibs-role`.

## Where does a new file go

| I have… | it goes to |
|---|---|
| a new strategy | `tradebot/strategies/<key>/` + a line in the registry ([STRATEGIE.md](STRATEGIE.md)) |
| a brief for a strategy that is yet to be built | `tradebot/strategies/<key>/docs/ZADANIE.md` |
| a tuning project for one strategy (sweeps, candidates, findings) | `tradebot/strategies/<key>/docs/projekt/` |
| Pine source, TradingView settings screenshots | `tradebot/strategies/<key>/docs/sources/`, `…/docs/tradingview/` |
| a C# port of a strategy | `tradebot/csharp/TradeBot.Strategies/<Name>Net/` + wrappers in `deploy/ninjatrader/`, `deploy/mt5/` |
| a profile that belongs to the repository (golden, starting point) | `tradebot/strategies/<key>/configs/` |
| a tester's own profile | `tester/profiles/` (the "Uložiť ako profil" button) |
| candles from a new source | `data/archive/tester/<source>/` via an importer, never by hand |
| a measurement with per-year numbers | `docs/merania/<TOPIC>_<date>.md` (`cli paper`) |
| a code audit, golden test, fixes after an audit | `docs/audity/` |
| market or idea research across strategies | `docs/prieskum/` |
| a manual that will be kept up to date | `docs/<TOPIC>.md` + a line in the README index |
| a new data source importer | `tester/<source>_import.py` + wrappers in the root |
| a hub plugin | `tester/hub/plugins/<name>/` ([HUB.md](HUB.md)) |
| a path the code will read | `tradebot/core/paths.py` — nowhere else |

---

## The whole tree

```
imbalance_strategy/
├── tradebot/        PRODUCT — what trades
│   ├── core/        Python core (engine contract, orders, money, sessions, candles, paths)
│   ├── csharp/      C# core and strategy ports (NinjaTrader 8, MT5, bridge)
│   ├── strategies/  registry + one package per strategy
│   ├── adapters/    Freqtrade, MultiCharts (+ emulator), C# bridge, NinjaTrader, MT5
│   ├── live/        live telemetry, deployment to trading PCs, order routing, Telegram
│   └── tests/
├── tester/          TESTER — how it is tested (web app, hub, analytics, importers) + run history
├── deploy/          what gets installed into Freqtrade, MultiCharts, NinjaTrader, MT5, hub agent
├── docker/          containers
├── data/            ALL DATA — archive/ and live/ in git, the rest derived locally
├── docs/            manuals; merania/, audity/, prieskum/ dated
└── *.sh, *.ps1, …   launchers and project configuration
```

### `tradebot/core/` — the Python core

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
└── paths.py             every path in the repository — the only place paths are written
```

### `tradebot/csharp/` — the C# core

```
csharp/
├── TradeBot.Core/       engine contract, bar history, orders, sessions, VWAP, MAs, warmup, drawing,
│                        EntryLayers, EodClose (15:59 NY close for prop accounts), Bridge (NT → MT5 routing),
│                        Live (telemetry spool), StaticHost (static facade MQL5 can call)
├── TradeBot.Strategies/ ports: IbsNet, OrbNet, IbsEntryNet, VwapOrbNet, VwapAdxNet, NoaNet, TksNet,
│                        FiboNet, NyVaNet, SdEurNet — each tagged [TradeBotEngine("key")]
├── TradeBot.Host/       TradeBot.Host.exe — the bridge without pythonnet
├── TradeBot.Backtest/   native backtest of the C# core over feather candles (MultiCharts emulator)
└── bin/                 build output (TradeBot.dll, TradeBot.Host.exe) — ignored, built on demand
```

C# 5, no NuGet: compiled by `csc.exe` from .NET Framework, by Mono and by NinjaTrader
(`python -m tradebot.adapters.csharp.build`). Every port must match its Python original
bar by bar (`tester/tests/test_csharp_parity*.py`).

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
    ├── freqtrade.py, multicharts.py, hyperopt.py   subclasses for the two engines, hyperopt space
    ├── ta/, htf.py, data.py  strategy-specific indicators, higher-TF feeder, extra symbols (where needed)
    ├── configs/         profiles that belong to the repository (golden, starting points)
    └── docs/
        ├── VYSVETLIVKA.md    what the strategy does, in plain words
        ├── ANALYTIKA.md      baseline analytics and verdict (`cli checkup`)
        ├── ZADANIE.md, PORT.md   brief / what changed in the port (where it applies)
        ├── sources/          Pine source (only on request)
        ├── tradingview/      reference settings and drawings from TradingView
        └── projekt/, <topic>/    tuning project, notes on particular settings (e.g. ibs/docs/rrr05/)
```

C# ports have their own package too (`ibsnet`, `orbnet`, `…net`, `…neteod`): a thin
config + SPEC pointing to the C# engine, plus their own profiles and analytics.

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
├── schema.py, spool.py  telemetry event schema (mirror of csharp/TradeBot.Core/Live.cs), reading the platform spool
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
| `csharp/` | `tradebot/csharp/` |
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
