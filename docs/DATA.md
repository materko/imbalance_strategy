# Dáta: odkiaľ sú, kde ležia a ako pribudne nový symbol

Dáta majú v repozitári dva pôvody a každý má vlastný adresár. Spoločné je pravidlo:
**na disku sú výhradne skutočné sviečky** — žiadny timeframe sa nedopočítava a neukladá.
Vyššie TF skladajú z 1m až za behu v pamäti naše vlastné nástroje (webapp graf, offline
simulátor, emulátor MultiCharts). Freqtrade to nerobí: pre svoj `--timeframe` potrebuje
súbor na disku (viď upozornenie v §A).

| pôvod | čo to je | archív (v gite) | pracovné (gitignored) |
|---|---|---|---|
| **burza cez ccxt** | Binance futures a spot, Coinbase spot — oficiálne TF burzy | `platforms/freqtrade/user_data/data_archive/<burza>/` | `platforms/freqtrade/user_data/data/` |
| **Dukascopy export** | CFD (NAS100, forex, komodity) — 1m, UTC, bid strana | `platforms/multicharts/data_archive/` | `platforms/multicharts/data/` |

Cesty sú na jednom mieste v [`tradebot/core/paths.py`](../tradebot/core/paths.py); nikde
inde v kóde sa nepíšu.

```bash
PY -m tradebot.tools.data_archive status    # čo je kde, koľko barov, aké obdobie
PY -m tradebot.tools.data_archive merge     # archív -> pracovné súbory (po klonovaní)
PY -m tradebot.tools.data_archive split     # pracovné súbory -> archív (po stiahnutí)
```

`PY` = Python z `.venv` (`\.venv\Scripts\python.exe` na Windows, `.venv/bin/python` inde).
**Po čerstvom klone treba `merge`**, inak backtest ani testy nemajú z čoho čítať; webapp
si ho pri štarte spustí sama.

---

## Prečo archív po rokoch

Freqtrade drží celý pár+TF v **jednom** súbore, ktorý sa pri každom sťahovaní prepíše
celý. Git si pamätá každú verziu — 86 MB `1m` súbor by tak pri každom doťahovaní pridal
do histórie ďalších 86 MB, ktoré sa už nedajú odstrániť bez prepísania histórie.

Rok, ktorý sa skončil, sa už nikdy nezmení, takže jeho blob v histórii existuje raz:

```
platforms/freqtrade/user_data/data_archive/binance/futures/
    BTC_USDT_USDT-1m-futures.2019.feather    4.7 MB
    ...
    BTC_USDT_USDT-1m-futures.2026.feather    9.8 MB   <- jediný, ktorý sa mení
```

Delenie je bezstratové — `merge(split(x))` dá presne to isté, čo bolo v `x`
([`test_data_archive.py`](../tradebot/tests/test_data_archive.py)). `split` navyše
neprepíše rok, ktorého obsah sa nezmenil, aby git nedostal nový blob zadarmo.

---

## A. Burzové dáta (Freqtrade)

```powershell
.\platforms\freqtrade\scripts\download-data.ps1              # Windows
```
```bash
./platforms/freqtrade/scripts/download-data.sh               # macOS / Linux
TIMERANGE=20260801-20260905 ./platforms/freqtrade/scripts/download-data.sh
SKIP_COINBASE=1 DAYS=180 ./platforms/freqtrade/scripts/download-data.sh
```

Skripty volajú `split` samy, takže po stiahnutí stačí commitnúť `data_archive/`.

### Sťahujú sa len oficiálne timeframy búrz

| Burza | Pár | Stiahne sa | Pozn. |
|---|---|---|---|
| Binance | `BTC/USDT:USDT`, `ETH/USDT:USDT` futures | **1m, 3m, 5m** + `mark`, `funding_rate` | vie všetky tri priamo |
| Binance | `BTC/USDT`, `ETH/USDT` spot | **1m, 3m, 5m** | len longy, páka 1 |
| Coinbase | `BTC/USD` spot | **1m, 5m** | **3m neponúka** — ccxt hlási len `1m/5m/15m/30m/1h/2h/6h/1d` |

**Coinbase 3m sa nikde neukladá ako súbor** — na disku sú len skutočné burzové sviečky,
žiadne umelo dorobené timeframy, ktoré by sa dali omylom zameniť za reálne dáta.

> ⚠️ **Freqtrade si vyšší timeframe z 1m nedopočíta.** Ak súbor pre `--timeframe` nie je na
> disku, backtest skončí na `No history for <pár>, <typ>, <TF> found` — overené na páre,
> ktorý má 1m/3m/5m/15m/30m a spustí sa s `--timeframe 1h`. Jediné, čo Freqtrade naozaj
> resampluje, sú **obchody** (`trades-to-ohlcv`, dáta z `download-data --dl-trades`);
> `--timeframe-detail 1m` používa 1m len na rozlíšenie SL/TP **vnútri** sviečky základného
> TF, ktorý musí existovať. Z 1m skladajú vyšší TF **naše vlastné nástroje** v pamäti —
> webapp graf, offline simulátor (`scan_zones`, `scan_trades --csv`), emulátor MultiCharts
> a HTF feeder študie —, nie Freqtrade.

Coinbase preto cez Freqtrade zabacktestuješ len na 1m alebo 5m; jej profil
`golden_coinbase_btcusd_3m` slúži na golden testy jadra proti TradingView, ktoré bežia nad
uloženými referenčnými dátami, nie cez Freqtrade.

### Načo sú tie tri timeframy

| TF | Úloha | Kde je to rozhodnuté |
|---|---|---|
| **3m** | timeframe stratégie — signály; všetky `*MaxBars` limity sa počítajú v **baroch** | [ARCHITECTURE_port.md §7](ARCHITECTURE_port.md) |
| **5m** | `zoneDetectionTF` — detekcia SD zón, ťahá sa ako informative pair | §3 |
| **1m** | `--timeframe-detail` — rozlíšenie SL/TP vnútri 3m sviečky v backteste | §7 |

> ⚠️ **Stratégiu nikdy nespúšťaj priamo na 1m.** `state2MaxBars=15` je na 3m grafe
> 45 minút, na 1m by to bolo 15 minút — iná stratégia.

---

## B. Dukascopy: jeden príkaz do Testera aj do MultiCharts

Surový export z Dukascopy (napr. `NAS100_M1_10Y.csv`) vyzerá takto — 1m, **UTC**, čas
**otvorenia** baru, len **bid** strana bez spreadu, objem v lotoch s desatinami:

```
dt,o,h,l,c,vol
2025-01-05 23:00:00,21339.209,21345.543,21324.419,21333.753,0.03
```

Priamo použiteľný nie je. Všetko potrebné spraví jeden príkaz:

```powershell
.\dukas-import.ps1 C:\dukas\NAS100_M1_10Y.csv --symbol NAS100
```
```bash
./dukas-import.sh ~/dukas/NAS100_M1_10Y.csv --symbol NAS100
```

alebo priamo `PY -m tradebot.tools.dukas_import <csv> --symbol NAS100`. Vyrobí obe veci:

| `--target` | čo vznikne | pre koho |
|---|---|---|
| `tester` | `platforms/multicharts/data_archive/<STEM>-1m.<rok>.feather` (commitni ich) a hneď z nich pracovný súbor v `platforms/multicharts/data/` | webapp Tester — pár je po reštarte v ponuke Nový beh |
| `multicharts` | `<zdroj>_mc.csv` — ASCII pre QuoteManager, hlavička `Date,Time,Open,High,Low,Close,Volume` | MultiCharts študia (import do QuoteManagera) |
| `both` (predvolené) | obe | |

Užitočné prepínače: `--from 2021-01-01 --to 2026-09-05` (orezanie obdobia), `--fix-scale`
(oprava dní s cenou ×1000), `--mc-out <cesta>` (kam ASCII súbor), `--no-merge` (nezložiť
pracovný súbor), `--stamp open` (ak import v QuoteManageri berie čas otvorenia baru).
Celý zoznam: `./dukas-import.sh` bez parametrov.

### Čo sa v exporte opravuje a prečo

Obe cesty čistia dáta **rovnakým pravidlom**, takže webapp, MultiCharts aj offline
simulátor (`scan_trades --csv`) vidia tie isté bary:

| chyba v exporte | čo s tým | prečo |
|---|---|---|
| **vypchávka**: riadok pre každú minútu vrátane víkendov a prestávok — plochý bar `o=h=l=c` s cenou posledného uzavretia, ~40 % súboru | zahodí sa každý plochý bar, ktorého cena sa rovná predchádzajúcemu uzavretiu; skutočná plochá minúta (cena sa pohla a stála) ostáva | limity `*MaxBars` sú v baroch, ATR a SMA objemu by sa skreslili |
| **čas otvorenia** baru | pre MultiCharts +1 minúta (razí bar časom zatvorenia), pre Tester ostáva | inak by seansy sedeli o bar vedľa |
| **cena ×1000** na niektorých dňoch (US500 2015–2019) | `--fix-scale`; nástroj to nahlási vždy, aj keď neopravuje | jeden zlý deň zhodí ATR aj zóny |
| **objem v lotoch** (0.01) | `round(vol × --volume-scale)`, predvolene ×100 | QuoteManager berie len celé číslo a väčšina barov by sa zaokrúhlila na nulu |

Objem Dukascopy je len tickový (loty klientov), nie burzový obrat — inštrument má
`has_real_volume=False` a `useVolumeFilter` treba nechať vypnutý.

### Nový symbol

Stačí ho pomenovať a povedať hodnotu bodu — **Big Point Value**, ako ju má symbol
v QuoteManageri (inak by sizing v Testeri a v MultiCharts nebol ten istý):

```bash
./dukas-import.sh ~/dukas/EURUSD_M1.csv --symbol EURUSD --point-value 100000 --tick 0.00001
```

Príkaz dopíše riadok do [`tradebot/core/instruments_dukascopy.json`](../tradebot/core/instruments_dukascopy.json)
(odtiaľ ho vidí webapp, emulátor aj MultiCharts študia), vyrobí dáta a k tomu **kostru
profilu** `docs/profily_archiv/ibs/<symbol>_dukas_3m.json`. Oboje commitni.

Kostra je kópia NAS100 profilu, takže **prahy v bodoch sú prevzaté z MNQ** — sedia len na
podklade s podobnou mierkou pohybu (NAS100, US500). Na forexe alebo komoditách ich prepni
na jednotku `atr` (`--set minImbSizePoints=0.5@atr`), rovnako ako pri ETH. Píše to aj
`_comment` vo vygenerovanom profile.

Bez `--point-value` príkaz neznámy symbol odmietne a vypíše, čo mu chýba — radšej chyba
než ticho zlý sizing.

### Prečo Dukascopy nejde cez Freqtrade

CFD nie sú burza v ccxt, takže Freqtrade ich nevezme. Webapp má preto vlastnú „burzu"
**MultiCharts**: beh nejde cez Freqtrade, ale cez emulátor MultiCharts — ten istý
`MCRunner`, ktorý beží v študii. Výsledok má rovnaký tvar ako Freqtrade beh a história
ich nerozlišuje (`result.engine` je `multicharts-emulator`). Podrobne:
[MULTICHARTS.md](MULTICHARTS.md).

```bash
PY -m tradebot.webapp.cli run --profile docs/profily_archiv/ibs/nas100_dukas_3m.json \
   --pair NAS100/USD --timerange 20250106-20250201 --fee 0 --note "NAS100 emulator, januar"
```

Forex a futures z Dukascopy sa na tejto burze nelíšia: všetko sú CFD s longmi, shortmi aj
pákou (typ `futures`); líšia sa len inštrumentom (tick, hodnota bodu, mena) a profilom.
Spread v dátach nie je (bid strana), počíta sa cez poplatok ako percento z nominálu.

---

## C. Rýchla kontrola dát bez webapp aj bez MultiCharts

```bash
PY -m tradebot.tools.scan_zones  --exchange binance          # aké zóny by vznikli
PY -m tradebot.tools.scan_trades --exchange binance          # celý STATE 0-5 + ordre
PY -m tradebot.tools.scan_trades --csv C:/dukas/NAS100_M1_10Y.csv \
    --profile docs/profily_archiv/ibs/nas100_dukas_3m.json --from 2025-01-01 --to 2025-01-31
```

`--csv` číta surový Dukascopy export (vypchávku zahodí rovnako ako import), graf aj
detekčný TF skladá z 1m v pamäti a vyplnenie rozhoduje po 1m sviečkach. Fill model je
naivný a poplatky nepočíta — je to na porovnanie zoznamu obchodov so študiou
v MultiCharts, nie na PnL.
