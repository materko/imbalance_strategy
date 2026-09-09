"""Kde v repozitári čo leží — jediné miesto, kde sú cesty napísané.

```
data_archive/tester/<zdroj>/<trh>/   sviečky po rokoch — v gite
data/tester/<zdroj>/<trh>/          pracovná podoba tých istých — gitignored
data/quotemanager/<zdroj>/          ASCII exporty na import do QuoteManagera — gitignored
deploy/freqtrade/                 čo potrebuje Freqtrade: configy búrz, skripty, user_data
deploy/multicharts/               čo potrebuje MultiCharts: šablóny štúdií, setup
tester/runs/, tester/profiles/   história behov a configy testerov — v gite
```

Dáta sa delia podľa toho, **kto ich konzumuje** — nie podľa engine. `tester/` je sklad
sviečok, ktorý číta Tester **oboma enginmi** (Freqtrade aj emulátor MultiCharts čítajú ten
istý súbor, práve preto sa dajú porovnať). `quotemanager/` je z neho odvodený výstup pre
MultiCharts v inom formáte (bar razený zatvorením, objem celé číslo, CSV); späť ho nikto
nečíta, vyrobí sa znova jedným príkazom.

V sklade sa sviečka z Binance a sviečka z Dukascopy líšia zdrojom, nie tým, čím ich kto prehrá — tá istá stratégia beží cez Freqtrade aj cez
emulátor MultiCharts na ktoromkoľvek páre (`tester.engines`). Preto je adresárom **zdroj**
(`binance`, `coinbase`, `dukascopy`) a nie platforma. Freqtrade dostane svoj koreň
prepínačom `--datadir`, ktorý mu `tester.engines` poskladá tak, aby jeho vlastná
konvencia (`futures/` a prípona `-futures`) vyšla na tú istú cestu.

`deploy/` je integračná vrstva — to, čo treba na strane cudzej aplikácie, aby v nej adaptér
bežal. Kód tam nie je (ten je v `tradebot/adapters/`) a dáta tiež nie.

Sklad (`data/tester/`) sa skladá z archívu príkazom
``python -m tester.data_archive merge`` a nikdy sa necommitujú — celý súbor by sa pri
každom doťahovaní dát pridal do histórie gitu znova, kým uzavretý rok v archíve sa už
nikdy nezmení.
"""

from __future__ import annotations

from pathlib import Path

__all__ = [
    "REPO",
    "DATA", "DATA_ARCHIVE", "TESTER_DATA", "DERIVED_MANIFEST", "QUOTEMANAGER_DATA",
    "DEPLOY_DIR", "FREQTRADE_DIR", "FREQTRADE_USER_DIR", "BACKTEST_RESULTS",
    "MULTICHARTS_DIR",
    "TESTER_DIR", "RUNS_DIR", "PROFILES_DIR", "TMP_PROFILES",
    "ARCHIVE_ROOTS",
]

#: Koreň repozitára — `tradebot/core/paths.py` → `tradebot/core` → `tradebot` → repo.
REPO = Path(__file__).resolve().parents[2]

# -- Dáta ------------------------------------------------------------------- #

#: Koreň všetkých dát. Podadresár = konzument, nie platforma.
DATA = REPO / "data"
#: Sklad sviečok, `data/tester/<zdroj>/<trh>/…` — odvodený z archívu, gitignored.
TESTER_DATA = DATA / "tester"
#: Zoznam sviečok, ktoré nevznikli sťahovaním, ale prepočtom z 1m (`tester.timeframes`).
#: Vďaka nemu ich `data_archive split` nepridá do gitu — dopočítať sa dajú kedykoľvek.
DERIVED_MANIFEST = TESTER_DATA / ".derived.json"
#: ASCII exporty pre QuoteManager, `data/quotemanager/<zdroj>/…` — výstup zo skladu.
QUOTEMANAGER_DATA = DATA / "quotemanager"
#: To isté po rokoch a v gite. **Zrkadlí `data/` cestu za cestou**, takže `split`/`merge`
#: je obyčajné kopírovanie koreň na koreň a nikde sa cesty neprekladajú. Uzavretý rok sa
#: už nezmení, takže jeho blob v histórii existuje raz; celý súbor by pribudol pri každom
#: sťahovaní znova.
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

#: Dvojica (archív, pracovný strom) pre `data_archive split|merge`. Keďže archív zrkadlí
#: `data/`, stačí jediná — zoznam ostáva, aby sa testy dali púšťať nad dočasným adresárom.
ARCHIVE_ROOTS: tuple[tuple[Path, Path], ...] = ((DATA_ARCHIVE, DATA),)
