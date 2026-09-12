# Ako to celé spustiť — rozcestník

Repozitár má dve platformy a jednu aplikáciu nad nimi. Každá má vlastný dokument, aby sa
nemiešalo, čo platí pre ktorú:

| chcem… | kam ísť |
|---|---|
| **spúšťať backtesty a pozerať históriu** (aj na Dukascopy symboloch) | [WEBAPP.md](WEBAPP.md) — Tester, webová aplikácia |
| **krypto: prostredie, backtest, hyperopt, Docker, server** | [FREQTRADE.md](FREQTRADE.md) |
| **MultiCharts: študia, QuoteManager, emulátor** | [MULTICHARTS.md](MULTICHARTS.md) |
| **dáta: odkiaľ sú, archív, Dukascopy import, nový symbol** | [DATA.md](DATA.md) |
| **testovať z CLI (aj pre AI)** | [../tester/AI_TESTING.md](../tester/AI_TESTING.md) |
| **počítať na viac strojoch** (hub, agenti, `run --remote`, Docker pre hub a agenta) | [HUB.md](HUB.md) |
| **pridať ďalšiu stratégiu** | [STRATEGIE.md](STRATEGIE.md) |
| **zistiť, čo tá stratégia je** (analytika, posudok) | [ANALYTIKA.md](ANALYTIKA.md) |
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
| Databento import (CME futures) | `./bento-import.sh` | `.\bento-import.ps1` |
| Setup (ak `.venv` chýba) | `deploy/freqtrade/scripts/setup.sh` | `deploy\freqtrade\scripts\setup.ps1` |

## Mapa repozitára

```
tradebot/                       PRODUKT - to, co obchoduje
  core/                         Bar, InstrumentSpec, config, kreslenie, hodiny, candles, paths
  strategies/<key>/             jedna strategia = jeden SEBESTACNY balik (STRATEGIE.md):
                                engine, config, meta, configs/ (profily), docs/sources/ (Pine)
  adapters/freqtrade/           genericka IStrategy + EngineRunner
  adapters/multicharts/         TradebotSignal, MCRunner, emulator, kreslenie
  configs/<key>/                referencne profily
  tests/                        testy produktu
deploy/freqtrade/            configy burz, skripty, user_data/ (data, vysledky, shim)
deploy/multicharts/          sablony studii, setup skript, data_archive/tester/<zdroj>/

tester/                         TESTER - cim sa to skusa
  webapp/                       aplikacia pre testerov + CLI (vyber engine)
  engines.py                    freqtrade | multicharts emulator + kde maju data
  AI_TESTING.md                 ako sa testuje z prikazoveho riadku
  compare/                      scan_zones, scan_trades, mc_log_trades, mc_compare
  dukas_import.py               import surovych exportov: cistenie, 1m feather, archiv
  bento_import.py               import Databento (CME futures): kontrakty -> front-month, archiv
  timeframes.py                 dopocet vyssich TF z 1m (tester/timeframes.json)
  quotemanager.py               ASCII export pre QuoteManager (MultiCharts)
  data_archive.py               rocny archiv sviecok
  report.py, fees.py, plot.py   reporty a metriky
  tests/                        testy nastrojov + golden parita s TradingView
  runs/, profiles/              historia behov a configy testerov (v gite)
  scripts/                      spustac webapp

docker/                         Dockerfile.core, Dockerfile.freqtrade, docker-compose.yml
docs/                           navody, architektura, parita; merania v docs/merania/
```
