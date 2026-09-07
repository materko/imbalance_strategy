# Ako to celé spustiť — rozcestník

Repozitár má dve platformy a jednu aplikáciu nad nimi. Každá má vlastný dokument, aby sa
nemiešalo, čo platí pre ktorú:

| chcem… | kam ísť |
|---|---|
| **spúšťať backtesty a pozerať históriu** (aj na Dukascopy symboloch) | [WEBAPP.md](WEBAPP.md) — Tester, webová aplikácia |
| **krypto: prostredie, backtest, hyperopt, Docker, server** | [FREQTRADE.md](FREQTRADE.md) |
| **MultiCharts: študia, QuoteManager, emulátor** | [MULTICHARTS.md](MULTICHARTS.md) |
| **dáta: odkiaľ sú, archív, Dukascopy import, nový symbol** | [DATA.md](DATA.md) |
| **pridať ďalšiu stratégiu** | [STRATEGIE.md](STRATEGIE.md) |
| **ako je to postavené a prečo** | [ARCHITECTURE_port.md](ARCHITECTURE_port.md) |

## Kde čo beží

| Prostredie | Na čo | Platformy |
|---|---|---|
| **Natívny venv** | Tester, Freqtrade vetva, testy, nástroje | Windows / macOS / Linux |
| **Docker** | server, CI, „nech to proste beží" | Windows / macOS / Linux |
| **Globálny Python** | MultiCharts študia | **len Windows** |

> **MultiCharts na macOS nebeží** a **nedá sa kontajnerizovať** — je to Windows desktop
> aplikácia s GUI a licenciou viazanou na stroj. Na Macu aj v Dockeri sa dá robiť jadro
> (`tradebot/`), testy, celá Freqtrade vetva aj emulátor MultiCharts vo webapp; samotná
> študia potrebuje Windows.

Všetko sa spúšťa **z koreňa repozitára**. `PY` = Python z `.venv`:

| | macOS / Linux | Windows |
|---|---|---|
| Python | `.venv/bin/python` | `.venv\Scripts\python.exe` |
| Tester (webapp) | `./webapp.sh` | `.\webapp.ps1` alebo `webapp.cmd` |
| Dukascopy import | `./dukas-import.sh` | `.\dukas-import.ps1` |
| Setup (ak `.venv` chýba) | `platforms/freqtrade/scripts/setup.sh` | `platforms\freqtrade\scripts\setup.ps1` |

## Mapa repozitára

```
tradebot/                       spoločné jadro a všetko, čo nie je viazané na platformu
  core/                         Bar, InstrumentSpec, SizeSpec, config, kreslenie, hodiny, paths
  strategies/<key>/             jedna stratégia = jeden balík (STRATEGIE.md)
  adapters/freqtrade/           generická IStrategy + EngineRunner
  adapters/multicharts/         TradebotSignal, MCRunner, emulátor, kreslenie
  configs/<key>/                referenčné profily
  webapp/                       Tester (FastAPI + Plotly)
  tools/                        data_archive, dukas_import, report, fees, scan_*, mc_*
  tests/                        pytest vrátane golden testov proti TradingView
platforms/freqtrade/            configy búrz, skripty, user_data/ (dáta, výsledky, shim)
platforms/multicharts/          šablóny študií, setup skript, Dukascopy dáta
tester/                         runs/ (história behov) + profiles/ (profily testerov), oboje v gite
docker/                         Dockerfile.core, Dockerfile.freqtrade, docker-compose.yml
pine/                           Pine zdroje stratégií — zdroj pravdy pre parametre
docs/                           návody, architektúra, parita; merania v docs/merania/
```
