"""Kde v repozitári čo leží — jediné miesto, kde sú cesty napísané.

Adresáre sú rozdelené podľa toho, **komu patria**, nie podľa toho, kto ich prvý
potreboval:

```
platforms/freqtrade/user_data/       userdir Freqtradu (jeho formát, jeho nástroje)
    data_archive/<burza>/            burzové sviečky po rokoch  — v gite
    data/                            pracovné súbory Freqtradu   — gitignored
    backtest_results/                zipy z backtestu            — gitignored
platforms/multicharts/
    data_archive/                    Dukascopy 1m sviečky po rokoch — v gite
    data/                            pracovné 1m sviečky            — gitignored
tester/
    runs/                            história behov z webapp     — v gite
    profiles/                        vlastné profily testerov    — v gite
```

Dáta testera (`tester/`) sú spoločné pre obe platformy: beh na Binance ide cez
Freqtrade, beh na Dukascopy symbole cez emulátor MultiCharts a v histórii sú vedľa
seba. Preto nesedia pod `user_data` ani jednej z nich.

Pracovné adresáre (`data/`) sa skladajú z archívu príkazom
``python -m tradebot.tools.data_archive merge`` a nikdy sa necommitujú — celý súbor
by sa pri každom doťahovaní dát pridal do histórie gitu znova.
"""

from __future__ import annotations

from pathlib import Path

__all__ = [
    "REPO",
    "FREQTRADE_DIR", "FREQTRADE_USER_DIR", "FREQTRADE_DATA", "FREQTRADE_ARCHIVE",
    "BACKTEST_RESULTS", "DUKASCOPY_FT_DATA",
    "MULTICHARTS_DIR", "MULTICHARTS_DATA", "MULTICHARTS_ARCHIVE",
    "TESTER_DIR", "RUNS_DIR", "PROFILES_DIR", "TMP_PROFILES",
    "ARCHIVE_ROOTS",
]

#: Koreň repozitára — `tradebot/core/paths.py` → `tradebot/core` → `tradebot` → repo.
REPO = Path(__file__).resolve().parents[2]

# -- Freqtrade -------------------------------------------------------------- #

FREQTRADE_DIR = REPO / "platforms" / "freqtrade"
FREQTRADE_USER_DIR = FREQTRADE_DIR / "user_data"
FREQTRADE_DATA = FREQTRADE_USER_DIR / "data"
FREQTRADE_ARCHIVE = FREQTRADE_USER_DIR / "data_archive"
BACKTEST_RESULTS = FREQTRADE_USER_DIR / "backtest_results"
#: Dukascopy sviečky prevedené pre Freqtrade (hyperopt, FreqAI). Odvodené z 1m
#: archívu MultiCharts, preto sa necommitujú a beh ich berie cez `--datadir`.
DUKASCOPY_FT_DATA = FREQTRADE_DATA / "dukascopy"

# -- MultiCharts ------------------------------------------------------------ #

MULTICHARTS_DIR = REPO / "platforms" / "multicharts"
#: 1m sviečky z Dukascopy CSV, pracovná podoba (`data_archive merge`).
MULTICHARTS_DATA = MULTICHARTS_DIR / "data"
#: To isté po rokoch, ako je to v gite (`tradebot.tools.dukas_import`).
MULTICHARTS_ARCHIVE = MULTICHARTS_DIR / "data_archive"

# -- Tester (webapp) -------------------------------------------------------- #

TESTER_DIR = REPO / "tester"
RUNS_DIR = TESTER_DIR / "runs"
PROFILES_DIR = TESTER_DIR / "profiles"
#: Dočasné profily rozbehnutých behov — vedľa histórie, ale gitignored.
TMP_PROFILES = RUNS_DIR / ".profiles"

# -- Archív ----------------------------------------------------------------- #

#: Dvojice (archív v gite, pracovný adresár) pre `data_archive split|merge`.
#: Obe platformy majú rovnaký formát súborov, len iný koreň.
ARCHIVE_ROOTS: tuple[tuple[Path, Path], ...] = (
    (FREQTRADE_ARCHIVE, FREQTRADE_DATA),
    (MULTICHARTS_ARCHIVE, MULTICHARTS_DATA),
)
