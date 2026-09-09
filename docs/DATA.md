# Dáta: odkiaľ sú, kde ležia a ako pribudne nový symbol

Dva stromy a jedno pravidlo medzi nimi:

```
data_archive/tester/<zdroj>/<trh>/  po rokoch, LEN z burzy alebo z raw exportu   v gite
data/tester/<zdroj>/<trh>/          sklad sviečok: zložené z archívu + dopočítané  gitignored
data/quotemanager/<zdroj>/          ASCII export na import do QuoteManagera        gitignored
```

**Do `data_archive/` ide výhradne to, čo naozaj prišlo z burzy alebo z raw dát** — píše doň
`split` (a `dukas_import` pri importe surového exportu). Nič dopočítané: vyššie timeframy
poskladané z 1m sú evidované a `split` ich preskočí.

**`data/` do gitu nejde nikdy.** Je celé odvodené: sviečky sa zložia z archívu, chýbajúce
timeframy sa dopočítajú z 1m a `quotemanager/` je ďalší export z toho istého. Preto stačí,
že je `data/` v `.gitignore` — nie je čo strážiť ručne.

**Tester si `data/` pri prvom spustení vyrobí celý sám** (`webapp.cmd` / `./webapp.sh`):
zloží archív a dopočíta timeframy, a čo by aj tak chýbalo, si poskladá stratégia pri behu.
Odmerané na tomto repozitári: z prázdneho `data/` 71 súborov (1,17 GB) za 15 sekúnd.

`tester/` číta Tester **oboma enginmi** (Freqtrade aj emulátor MultiCharts čítajú ten istý
súbor — práve preto sa dajú porovnať). **Archív zrkadlí `data/` cestu za cestou**, len po
rokoch — `split` a `merge` sú preto obyčajné kopírovanie koreň na koreň a niet miesta, kde
by sa cesty mohli rozísť.

Zdroj je `binance`, `coinbase`, `dukascopy`; trh je `spot` alebo `futures`. Z cesty tak
vidno, čo súbor obsahuje, bez otvárania.

| zdroj | čo to je | ako pribudne |
|---|---|---|
| `binance` | futures aj spot, oficiálne TF burzy | `deploy/freqtrade/scripts/download-data.sh` |
| `coinbase` | BTC/USD spot, referenčný | to isté |
| `dukascopy` | CFD (NAS100, forex, komodity) — 1m, UTC, bid strana | `./dukas-import.sh` (§B) |

Ten istý strom čítajú **oba enginy**: Freqtrade dostane koreň cez `--datadir data/<zdroj>`,
emulátor MultiCharts si berie 1m súbor odtiaľ istadiaľ. Preto sa dá krypto prehrať
emulátorom a Dukascopy cez Freqtrade — dáta v tom nebránia
([FREQTRADE.md §G](FREQTRADE.md), [`tester/engines.py`](../tester/engines.py)).

Podadresár `futures/` a príponu `-futures` v mene si Freqtrade drží natvrdo, pre spot
nepridáva nič — preto mu `--datadir` podávame rôzne podľa trhu (pri futures o úroveň
vyššie, pri spote priamo na `spot/`). Na disku je tým rozloženie súmerné. Cesty počíta
jedno miesto —
[`tester/engines.py`](../tester/engines.py); korene sú v
[`tradebot/core/paths.py`](../tradebot/core/paths.py).

```bash
PY -m tester.data_archive status    # čo je kde, koľko barov, aké obdobie
PY -m tester.data_archive merge     # archív -> pracovné súbory (po klonovaní)
PY -m tester.data_archive split     # pracovné súbory -> archív (po stiahnutí)
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
data_archive/tester/binance/futures/
    BTC_USDT_USDT-1m-futures.2019.feather    4.7 MB
    ...
    BTC_USDT_USDT-1m-futures.2026.feather    9.8 MB   <- jediný, ktorý sa mení
```

Delenie je bezstratové — `merge(split(x))` dá presne to isté, čo bolo v `x`
([`test_data_archive.py`](../tester/tests/test_data_archive.py)). `split` navyše
neprepíše rok, ktorého obsah sa nezmenil, aby git nedostal nový blob zadarmo.

---

## A. Burzové dáta (Freqtrade)

```powershell
.\deploy\freqtrade\scripts\download-data.ps1              # Windows
```
```bash
./deploy/freqtrade/scripts/download-data.sh               # macOS / Linux
TIMERANGE=20260801-20260905 ./deploy/freqtrade/scripts/download-data.sh
SKIP_COINBASE=1 DAYS=180 ./deploy/freqtrade/scripts/download-data.sh
```

Skripty volajú `split` samy, takže po stiahnutí stačí commitnúť `data_archive/tester/`.

### Sťahujú sa len oficiálne timeframy búrz

| Burza | Pár | Stiahne sa | Pozn. |
|---|---|---|---|
| Binance | `BTC/USDT:USDT`, `ETH/USDT:USDT` futures | **1m, 3m, 5m** + `mark`, `funding_rate` | vie všetky tri priamo |
| Binance | `BTC/USDT`, `ETH/USDT` spot | **1m, 3m, 5m** | len longy, páka 1 |
| Coinbase | `BTC/USD` spot | **1m, 5m** | **3m neponúka** — ccxt hlási len `1m/5m/15m/30m/1h/2h/6h/1d` |

Z burzy sa sťahuje len to, čo burza naozaj má. Zvyšok si Tester **dopočíta z 1m** —
zoznam je v [`tester/timeframes.json`](../tester/timeframes.json) (dnes 2m, 3m, 4m, 5m,
15m, 30m, 1h, 4h, 1d, 1w) a doplní sa pri štarte webapp alebo príkazom:

```bash
PY -m tester.timeframes            # doplní, čo chýba
PY -m tester.timeframes --status   # čo je z burzy a čo dopočítané
```

Dve pravidlá, aby sa dopočítané a stiahnuté nedalo zameniť:

* **Nič stiahnuté sa neprepisuje.** Doplní sa len súbor, ktorý na disku nie je.
* **Dopočítané sa necommituje.** Vyrobené súbory sú v `data/tester/.derived.json`
  a `data_archive split` ich preskočí — v archíve ostáva len to, čo prišlo z burzy
  alebo z raw exportu. Kedykoľvek sa dajú vyrobiť znova.

Skladá sa tým istým pravidlom ako graf webapp a emulátor (`tradebot/core/candles.py`),
takže bary sú všade rovnaké. Denné začínajú o polnoci UTC, **týždenné v pondelok** (od
epochy by vyšiel štvrtok).

Dopredu to však nemusí byť: **keď súbor pre beh chýba, poskladá si ho samotná stratégia.**
Freqtrade adaptér to robí v `TradebotStrategyBase.ensure_timeframe` — pre základný TF behu
aj pre informatívny (detekčný TF zón) — cez dátový handler Freqtradu, takže pomenovanie aj
formát súboru sú jeho. Deje sa to v `__init__` stratégie, teda **skôr**, než si Freqtrade
načíta dáta backtestu (`bot_start` je už neskoro), a vyrobené súbory sa evidujú rovnako ako
tie z `tester.timeframes`. Jediná podmienka sú 1m sviečky.

V živom a dry-run behu sa **nedopočítava nič** — tam sviečky prichádzajú z burzy a
vymyslený bar by bol chyba, nie pomoc.

> ⚠️ **Freqtrade akceptuje len timeframy, ktoré pozná jeho burza.** Súbor na disku
> nestačí: `2m` a `4m` Binance nepozná, takže beh na nich ide **len cez emulátor
> MultiCharts** — webapp aj CLI to povedia dopredu („burza binance timeframe 2m nepozná")
> a samy prepnú engine. Coinbase nepozná ani `3m`.

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

alebo priamo `PY -m tester.dukas_import <csv> --symbol NAS100`. Import robí vždy to isté
a nič viac: **vyčistí** surový súbor, spraví z neho **feather v timeframe zdroja** (Dukascopy
= 1m), **rozdelí po rokoch** a uloží do `data_archive/`. Tam jeho práca končí.

```
raw  ->  import (čistenie, feather, split po rokoch)  ->  data_archive/  (commituje sa)
```

Všetko ostatné je odvodené a robí si to Tester sám z archívu:

| čo | čím | kedy |
|---|---|---|
| pracovné sviečky `data/tester/` | `tester.data_archive merge` | pri štarte webapp |
| vyššie timeframy | `tester.timeframes` alebo Freqtrade adaptér počas behu | pri štarte webapp / behu |
| ASCII pre QuoteManager | `tester.quotemanager` | pri štarte webapp (Dukascopy symboly) |

Prepínače importu: `--from` / `--to` (orezanie obdobia), `--fix-scale` (oprava dní s cenou
×1000), `--keep-padding` (nevyhadzovať ploché bary), `--archive` (iný archív),
`--no-merge` (nezložiť hneď pracovný súbor).

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
(odtiaľ ho vidí webapp, emulátor aj MultiCharts študia) a vyrobí dáta. Oboje commitni.

**Profil sa k tomu nevyrába.** Prahy v cenových bodoch platia len na podklade s podobnou
mierkou pohybu, takže skopírovať ich z NAS100 na EURUSD (cena 1,08) alebo na kakao je
nezmysel — a profil, ktorý vyzerá hotovo, sa nezmyslu ťažšie všimne než jeho neprítomnosti.
Prvý beh na novom symbole preto choď bez `--profile` (Pine defaulty; inštrument si Tester
nájde podľa páru) a veľkostné polia zadaj v jednotke `atr`
(`--set minImbSizePoints=0.5@atr`), rovnako ako pri ETH. Keď z toho vypadne niečo, čo drží,
ulož si to tlačidlom **Uložiť ako profil**.

Bez `--point-value` príkaz neznámy symbol odmietne a vypíše, čo mu chýba — radšej chyba
než ticho zlý sizing.

### Prečo Dukascopy nejde cez Freqtrade

CFD nie sú burza v ccxt, takže Freqtrade ich nevezme. Webapp má preto vlastnú „burzu"
**MultiCharts**: beh nejde cez Freqtrade, ale cez emulátor MultiCharts — ten istý
`MCRunner`, ktorý beží v študii. Výsledok má rovnaký tvar ako Freqtrade beh a história
ich nerozlišuje (`result.engine` je `multicharts-emulator`). Podrobne:
[MULTICHARTS.md](MULTICHARTS.md).

```bash
PY -m tester.webapp.cli run --profile docs/profily_archiv/ibs/nas100_dukas_3m.json \
   --pair NAS100/USD --timerange 20250106-20250201 --fee 0 --note "NAS100 emulator, januar"
```

Forex a futures z Dukascopy sa na tejto burze nelíšia: všetko sú CFD s longmi, shortmi aj
pákou (typ `futures`); líšia sa len inštrumentom (tick, hodnota bodu, mena) a profilom.
Spread v dátach nie je (bid strana), počíta sa cez poplatok ako percento z nominálu.

---

## B2. ASCII pre QuoteManager (MultiCharts)

MultiCharts si sviečky nesťahuje — nakŕmi sa cez QuoteManager z ASCII súboru. Ten sa robí
**zo skladu sviečok**, nie zo surového exportu, takže v MultiCharts je presne to, na čom
bežali backtesty:

```bash
PY -m tester.quotemanager                     # čo treba a ešte nie je (Dukascopy symboly)
PY -m tester.quotemanager --all               # aj krypto — MultiCharts vie testovať aj to
PY -m tester.quotemanager --symbol NAS100 --force
PY -m tester.quotemanager --status
```

Výstup je `data/quotemanager/<zdroj>/<PÁR>-1m.csv` s hlavičkou
`Date,Time,Open,High,Low,Close,Volume`, časom **zatvorenia** baru (+1 minúta oproti skladu,
konvencia MultiCharts) a objemom ako celé číslo (`round(vol × 100)`; QuoteManager desatiny
neberie). Import v QuoteManageri má časové pásmo súboru **GMT**.

Webapp si pri štarte vyrobí, čo chýba: predvolene len Dukascopy symboly (`TRADEBOT_QUOTEMANAGER=all`
aj krypto, `=off` nič) — celý export BTC 1m má cez 200 MB, preto sa nerobí nasilu.

---

## C. Rýchla kontrola dát bez webapp aj bez MultiCharts

```bash
PY -m tester.compare.scan_zones  --exchange binance          # aké zóny by vznikli
PY -m tester.compare.scan_trades --exchange binance          # celý STATE 0-5 + ordre
PY -m tester.compare.scan_trades --csv C:/dukas/NAS100_M1_10Y.csv \
    --profile docs/profily_archiv/ibs/nas100_dukas_3m.json --from 2025-01-01 --to 2025-01-31
```

`--csv` číta surový Dukascopy export (vypchávku zahodí rovnako ako import), graf aj
detekčný TF skladá z 1m v pamäti a vyplnenie rozhoduje po 1m sviečkach. Fill model je
naivný a poplatky nepočíta — je to na porovnanie zoznamu obchodov so študiou
v MultiCharts, nie na PnL.
