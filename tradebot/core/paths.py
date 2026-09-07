"""Kde v repozitári čo leží — jediné miesto, kde sú cesty napísané.

```
data_archive/<zdroj>/<trh>/  sviečky po rokoch           — v gite
data/<zdroj>/<trh>/          pracovná podoba tých istých — gitignored
deploy/freqtrade/            čo potrebuje Freqtrade: configy búrz, skripty, user_data
deploy/multicharts/          čo potrebuje MultiCharts: šablóny štúdií, setup
tester/runs/, tester/profiles/   história behov a configy testerov — v gite
```

**Dáta sú jedny, nerozdelené podľa engine.** Sviečka z Binance a sviečka z Dukascopy sa
líšia zdrojom, nie tým, čím ich kto prehrá — tá istá stratégia beží cez Freqtrade aj cez
emulátor MultiCharts na ktoromkoľvek páre (`tester.engines`). Preto je adresárom **zdroj**
(`binance`, `coinbase`, `dukascopy`) a nie platforma. Freqtrade dostane svoj koreň
prepínačom `--datadir`, ktorý mu `tester.engines` poskladá tak, aby jeho vlastná
konvencia (`futures/` a prípona `-futures`) vyšla na tú istú cestu.

`deploy/` je integračná vrstva — to, čo treba na strane cudzej aplikácie, aby v nej adaptér
bežal. Kód tam nie je (ten je v `tradebot/adapters/`) a dáta tiež nie.

Pracovné adresáre (`data/`) sa skladajú z archívu príkazom
``python -m tester.data_archive merge`` a nikdy sa necommitujú — celý súbor by sa pri
každom doťahovaní dát pridal do histórie gitu znova, kým uzavretý rok v archíve sa už
nikdy nezmení.
"""

from __future__ import annotations

from pathlib import Path

__all__ = [
    "REPO",
    "DATA", "DATA_ARCHIVE",
    "DEPLOY_DIR", "FREQTRADE_DIR", "FREQTRADE_USER_DIR", "BACKTEST_RESULTS", "MULTICHARTS_DIR",
    "TESTER_DIR", "RUNS_DIR", "PROFILES_DIR", "TMP_PROFILES",
    "ARCHIVE_ROOTS",
]

#: Koreň repozitára — `tradebot/core/paths.py` → `tradebot/core` → `tradebot` → repo.
REPO = Path(__file__).resolve().parents[2]

# -- Dáta ------------------------------------------------------------------- #

#: Pracovné sviečky, `data/<zdroj>/…` — odvodené z archívu, gitignored.
DATA = REPO / "data"
#: To isté po rokoch, ako je to v gite.
DATA_ARCHIVE = REPO / "data_archive"

# -- Integrácia s platformami ----------------------------------------------- #

DEPLOY_DIR = REPO / "deploy"

FREQTRADE_DIR = DEPLOY_DIR / "freqtrade"
#: `--userdir` Freqtradu: shim stratégie pre resolver, hyperopt loss, výsledky, logy.
#: Sviečky tu **nie sú** — tie idú cez `--datadir`.
FREQTRADE_USER_DIR = FREQTRADE_DIR / "user_data"
BACKTEST_RESULTS = FREQTRADE_USER_DIR / "backtest_results"

MULTICHARTS_DIR = DEPLOY_DIR / "multicharts"

# -- Tester (webapp) -------------------------------------------------------- #

TESTER_DIR = REPO / "tester"
RUNS_DIR = TESTER_DIR / "runs"
PROFILES_DIR = TESTER_DIR / "profiles"
#: Dočasné profily rozbehnutých behov — vedľa histórie, ale gitignored.
TMP_PROFILES = RUNS_DIR / ".profiles"

# -- Archív ----------------------------------------------------------------- #

#: Dvojice (archív v gite, pracovný adresár) pre `data_archive split|merge`.
#: Odkedy sú dáta na jednom mieste, je to jediná dvojica; zoznam ostáva, aby sa testy
#: dali púšťať nad dočasným adresárom a aby sa dal pridať ďalší koreň.
ARCHIVE_ROOTS: tuple[tuple[Path, Path], ...] = ((DATA_ARCHIVE, DATA),)
