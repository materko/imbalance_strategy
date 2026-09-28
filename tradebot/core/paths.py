"""Kde v repozitári čo leží — jediné miesto, kde sú cesty napísané.

```
data_archive/tester/<zdroj>/<trh>/   sviečky po rokoch — v gite
data/tester/<zdroj>/<trh>/          pracovná podoba tých istých — gitignored
data/quotemanager/<zdroj>/          ASCII exporty na import do QuoteManagera — gitignored
deploy/freqtrade/                 čo potrebuje Freqtrade: configy búrz, skripty, user_data
deploy/multicharts/               čo potrebuje MultiCharts: šablóny štúdií, setup
deploy/ninjatrader/               čo potrebuje NinjaTrader 8: šablóny stratégií, inštalácia
deploy/mt5/                       čo potrebuje MetaTrader 5: šablóny Expert Advisorov nad C# jadrom
csharp/                           jadro a stratégie v C# (NinjaTrader natívne, MT5 cez .NET import, Freqtrade cez most)
tester/runs/, tester/profiles/   história behov a configy testerov — v gite (bez kresieb)
tester/sweeps/                    výsledky mriežok, matíc a overení hyperoptu — v gite
tester/runs/.charts/              kresby behov pre graf, prepočítané na vyžiadanie — gitignored
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

from .env import getenv

__all__ = [
    "REPO",
    "DATA", "DATA_ARCHIVE", "TESTER_ARCHIVE", "TESTER_DATA", "DERIVED_MANIFEST",
    "QUOTEMANAGER_DATA", "NINJATRADER_DATA",
    "DEPLOY_DIR", "FREQTRADE_DIR", "FREQTRADE_USER_DIR", "BACKTEST_RESULTS",
    "MULTICHARTS_DIR", "NINJATRADER_DIR", "MT5_DIR",
    "CSHARP_DIR", "CSHARP_BIN", "CSHARP_DLL", "CSHARP_HOST",
    "TESTER_DIR", "RUNS_DIR", "PROFILES_DIR", "TMP_PROFILES", "ANALYTICS_DIR",
    "SWEEPS_DIR", "CHART_CACHE", "ARCHIVE_DIR",
    "HUB_DIR", "AGENT_CONFIG", "AGENT_STATE",
    "HUB_LIVE_DB", "LIVE_DIR", "LIVE_CURSOR", "LIVE_CURSOR_WEBAPP", "LIVE_MIRROR", "LIVE_MIRROR_CURSOR",
    "LIVE_SECRETS", "LIVE_APPLY_STATE", "LIVE_MT5_DIR",
    "DOCS_DIR", "MERANIA_DIR",
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
#: Textové súbory na import histórie do NinjaTradera (`tester.ninjatrader export`) — výstup zo skladu.
NINJATRADER_DATA = DATA / "ninjatrader"
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
#: Čo potrebuje NinjaTrader 8: šablóny stratégií (NinjaScript) a inštalácia do `bin/Custom`.
NINJATRADER_DIR = DEPLOY_DIR / "ninjatrader"
#: Čo potrebuje MetaTrader 5: šablóny Expert Advisorov (MQL5) — inštalácia do `MQL5/Experts`.
MT5_DIR = DEPLOY_DIR / "mt5"

# -- C# jadro ---------------------------------------------------------------- #

#: Jadro a stratégie v C# (`TradeBot.Core`, `TradeBot.Strategies`) — beží v NinjaTraderi
#: natívne a pod Freqtrade cez most `tradebot/adapters/csharp`.
CSHARP_DIR = REPO / "csharp"
#: Preložené assembly — gitignored, most si ich zostaví sám (`tradebot.adapters.csharp.build`).
CSHARP_BIN = CSHARP_DIR / "bin"
CSHARP_DLL = CSHARP_BIN / "TradeBot.dll"
CSHARP_HOST = CSHARP_BIN / "TradeBot.Host.exe"

# -- Tester (webapp) -------------------------------------------------------- #

TESTER_DIR = REPO / "tester"
RUNS_DIR = TESTER_DIR / "runs"
PROFILES_DIR = TESTER_DIR / "profiles"
#: Dočasné profily rozbehnutých behov — vedľa histórie, ale gitignored.
TMP_PROFILES = RUNS_DIR / ".profiles"
#: História analytiky. Vedľa behov, nie v nich: analytika nie je beh, je to pohľad na
#: viac behov naraz — a rovnako ako behy sa zdieľa cez git (Push ju commituje).
ANALYTICS_DIR = TESTER_DIR / "analytics"
#: Výsledky hromadných behov — mriežka (sweep), matica trhov, overenie víťaza hyperoptu
#: a jeho okolie. Jeden súbor na celok s tabuľkou bodov (parametre + metriky); jednotlivé
#: body do `runs/` nejdú, lebo ich sú tisíce. Bod sa dá kedykoľvek prehrať ako obyčajný
#: beh. Zdieľa sa cez git ako história behov.
SWEEPS_DIR = TESTER_DIR / "sweeps"
#: Archív behov — beh, ktorý sa z histórie odložil (`cli archive`), leží celý (config,
#: výsledok, obchody, log) v gzipovanom JSONL. Tisíce adresárov v `runs/` tým padnú na
#: pár súborov, ale nič sa nestratí: `cli archive --restore` beh vráti presne späť.
#: Ide do gitu ako história behov.
ARCHIVE_DIR = TESTER_DIR / "archive"
#: Kresby enginu pre graf páru (`<run_id>.json.gz`) a výsledok kontroly prehrania.
#: Megabajty na beh a z uloženého configu sa dajú kedykoľvek prepočítať, takže do gitu
#: nejdú — každý klon si ich počíta sám, až keď graf niekto otvorí.
CHART_CACHE = RUNS_DIR / ".charts"

# -- Distribuované počítanie (tester.hub) ----------------------------------- #

#: Stav hubu: zoznam agentov, fronta výpočtov a odovzdané výsledky (`results/<id>.zip`).
#: Gitignored — hub je jeden proces na verejnom stroji, jeho stav nikto nezdieľa.
#: `TRADEBOT_HUB_DATA` ho presunie inam (druhý hub na tom istom stroji, skúška proti
#: dočasnému stavu) — platí pre `serve` aj pre `token add --local` a ďalšie `--local` príkazy.
HUB_DIR = Path(getenv("HUB_DATA") or TESTER_DIR / "hub_data")
#: Konfigurácia agenta v tomto klone: adresa hubu, token, či prijíma a či posiela
#: výpočty. Každý klon má vlastnú, preto gitignored.
AGENT_CONFIG = TESTER_DIR / "agent.json"
#: Stav agenta: čo poslal na hub a ešte sa nevrátilo, čo preň počíta. Prežije reštart.
AGENT_STATE = TESTER_DIR / "agent_state.json"

# -- Live telemetria (tradebot.live, docs/LIVE.md) -------------------------- #

#: Udalosti zo spustených stratégií na hube (`live.sqlite`) — vedľa stavu hubu, gitignored.
HUB_LIVE_DB = HUB_DIR / "live.sqlite"
#: Lokálny stav live telemetrie tohto klonu: kurzory do spoolu platforiem a zrkadlo hubu
#: pre webapp. Každý stroj má vlastný, gitignored. `TRADEBOT_LIVE_DIR` ho presunie inam
#: (druhá webapp na tom istom stroji, testy proti dočasnému zrkadlu).
LIVE_DIR = Path(getenv("LIVE_DIR") or TESTER_DIR / "live")
#: Kurzor agenta do spoolu (súbor → offset); posúva sa až po potvrdení hubom.
LIVE_CURSOR = LIVE_DIR / "cursor.json"
#: Kurzor webapp do lokálneho spoolu (keď webapp beží na obchodnom PC, číta ho priamo).
LIVE_CURSOR_WEBAPP = LIVE_DIR / "cursor_webapp.json"
#: Zrkadlo udalostí hubu pre webapp — hub dole = webapp ukazuje, čo má.
LIVE_MIRROR = LIVE_DIR / "mirror.sqlite"
#: Kurzor zrkadla do hubu (`{"hub_url", "cursor"}` = posledný prevzatý rowid hubu); pri zmene
#: adresy hubu začína od nuly, lebo rowid iného hubu nič neznamená.
LIVE_MIRROR_CURSOR = LIVE_DIR / "mirror_cursor.json"
#: Heslá účtov platforiem z hubu, zašifrované DPAPI na tento stroj a používateľa
#: (`<account>.bin`) — nikdy v gite, nikdy v čitateľnej podobe (docs/LIVE.md, fáza 2b).
LIVE_SECRETS = LIVE_DIR / "secrets"
#: Posledný požadovaný stav z hubu a čo z neho agent aplikoval (`tradebot.live.apply`);
#: po reštarte agent hlási to isté, kým hub nepošle nový.
LIVE_APPLY_STATE = LIVE_DIR / "apply_state.json"
#: Pracovné adresáre MT5 drivera po účtoch: štartovací ini, pid, log, prípadná portable
#: kópia terminálu (`<account>/…`).
LIVE_MT5_DIR = LIVE_DIR / "mt5"

# -- Dokumentácia ----------------------------------------------------------- #

DOCS_DIR = REPO / "docs"
#: Datované merania. Píše sem `tester.paper`, inak sa písali ručne.
MERANIA_DIR = DOCS_DIR / "merania"

# -- Archív ----------------------------------------------------------------- #

#: Dvojica (archív, pracovný strom) pre `data_archive split|merge`. Keďže archív zrkadlí
#: `data/`, stačí jediná — zoznam ostáva, aby sa testy dali púšťať nad dočasným adresárom.
#: Sklad sviečok v archíve — zrkadlo `TESTER_DATA`. Importéry píšu sem, nie o úroveň
#: vyššie: `data_archive/<zdroj>/…` by `merge` do `data/tester/` nepreniesol.
TESTER_ARCHIVE = DATA_ARCHIVE / "tester"

ARCHIVE_ROOTS: tuple[tuple[Path, Path], ...] = ((DATA_ARCHIVE, DATA),)
