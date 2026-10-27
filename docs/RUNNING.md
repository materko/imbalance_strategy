# Ako to celé spustiť — rozcestník

Repozitár má dve platformy a jednu aplikáciu nad nimi. Každá má vlastný dokument, aby sa
nemiešalo, čo platí pre ktorú:

| chcem… | kam ísť |
|---|---|
| **spúšťať backtesty a pozerať históriu** (aj na Dukascopy symboloch) | [WEBAPP.md](WEBAPP.md) — Tester, webová aplikácia |
| **krypto: prostredie, backtest, hyperopt, Docker, server** | [FREQTRADE.md](FREQTRADE.md) |
| **MultiCharts: študia, QuoteManager, emulátor** | [MULTICHARTS.md](MULTICHARTS.md) |
| **NinjaTrader 8 a stratégie s jadrom v C#** | [NINJATRADER.md](NINJATRADER.md) |
| **MetaTrader 5 nad tým istým C# jadrom (Expert Advisor)** | [MT5.md](MT5.md) |
| **stratégia v NinjaTraderi, ordery v MT5** | [ROUTING.md](ROUTING.md) |
| **telemetria bežiacich stratégií (karta Live)** | [LIVE.md](LIVE.md) |
| **zdieľať trhy medzi NinjaTraderom a MT5 (feed pre indikátory, návrh)** | [FEED.md](FEED.md) |
| **dáta: odkiaľ sú, archív, Dukascopy import, nový symbol** | [DATA.md](DATA.md) |
| **testovať z CLI (aj pre AI)** | [../tester/AI_TESTING.md](../tester/AI_TESTING.md) |
| **počítať na viac strojoch** (hub, agenti, `run --remote`, Docker pre hub a agenta) | [HUB.md](HUB.md) |
| **volať webapp zo skriptu alebo z AI** (behy, sweep, hyperopt, natívne behy bez histórie) | [API.md](API.md) |
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
| IBKR import (americké akcie) | `./ibkr-import.sh` | `.\ibkr-import.ps1` |
| Setup (ak `.venv` chýba) | `deploy/freqtrade/scripts/setup.sh` | `deploy\freqtrade\scripts\setup.ps1` |

## Mapa repozitára

Koncept a podrobná mapa sú v [DIRECTORIES.md](DIRECTORIES.md), skratka v [README](../README.md#mapa-repozitára).
