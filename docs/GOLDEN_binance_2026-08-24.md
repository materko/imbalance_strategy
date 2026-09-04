# Golden test: TradingView vs port — BINANCE:BTCUSDT.P, 3m

Referencia odčítaná priamo z TradingView Strategy Testera (2026-09-04), uložená v
[`ibs/tests/golden/tv_btcusdt_binance_3m.json`](../ibs/tests/golden/tv_btcusdt_binance_3m.json).

Nastavenia: čerstvo vložený `imbalance_strategy_FULL.pine` + 5 odchýlok od Pine defaultov
(`enablePinBarEntry`, `enableTrailing`, `tradeDirection="Long only"`, `sess2ZoneStartH=8`,
`showElliott=false`). Profil na našej strane: `btcusdt_3m_binance_tv`.

Časy TradingView sú v zóne grafu **UTC+2**, nižšie prepočítané na UTC.

```bash
python -m ibs.tools.scan_trades --exchange binance --profile btcusdt_3m_binance_tv \
    --from 2026-08-24 --to 2026-09-04 --limit 0
```

## Zhoda: 3 z 5 obchodov sedia na cent

| TradingView | Port | |
|---|---|---|
| #1 vstup **14:54** @ **79 419.5**, výstup 15:03 @ **79 607.3**, WIN | `LONG_10` vyplnený **14:54** @ **79 419.50**, TP **79 607.30**, WIN | ✅ |
| #2 vstup **17:15** @ **79 022.0**, výstup 17:21 @ **78 541.2**, LOSS | `LONG_9` vyplnený **17:15** @ **79 022.00**, SL **78 541.20**, LOSS | ✅ |
| #3 vstup **07:42** @ **80 516.0**, výstup 07:45 @ **80 458.9**, LOSS | `LONG_12` vyplnený **07:42** @ **80 516.10**, SL **80 458.90**, LOSS | ✅ (vstup o 1 tick) |

Sedí vstupná cena, SL aj TP úroveň **a minúta vyplnenia**. To znamená, že detekcia zóny,
hľadanie gapu, `state2ConfirmTicks`, swing SL, `rrRatio` aj `snapMode` fungujú presne ako Pine.

Sedí aj **veľkosť pozície**: TV obchod #4 mal `size = 2`. Pri tick 0.1 a `tickDollarValue = 0.5`
vychádza `floor(350 / (SL_vzdialenosť × 5))`; pri SL ≈ 31.4 bodu to dá presne 2. To potvrdzuje,
že `legacyPineSizing` reprodukuje Pine vzorec vrátane jeho zaokrúhľovania.

## Rozdiel: dva obchody TradingView nemáme, päť máme navyše

TradingView má a my nie:

| | čas UTC | cena | pozn. |
|---|---|---|---|
| #4 | 08-27 07:09 | 78 765.1 | = **close** baru 07:06 |
| #5 | 08-28 14:51 | 79 250.0 | = **close** baru 14:48 |

Overené, že **nejde o rozdiel v dátach**: naše 3m sviečky majú na tých časoch presne
`O = 78 765.1` a `O = 79 250.0`, oba dni sú kompletné (480 barov).

Príčina je v **zónach, nie vo vstupnom modeli**. Diagnostika 08-28 14:48 ukazuje:

```
08-28 14:48  O=79255.5 C=79250.0 pinLONG=True | LONG zon zivych=1 dotyk=0
```

Pin bar **detegujeme správne** (a jeho close je presne TV vstupná cena), ale jediná živá LONG
zóna je 78 662.7–78 993.7, zatiaľ čo bar má low 79 048.9 — zónu sa teda nedotýka. TradingView
musel mať v tom mieste ďalšiu LONG zónu, ktorú my nemáme. Rovnaký obraz je aj 08-27 07:06.

Päť obchodov navyše na našej strane (08-25 16:30, 08-26 07:09, 08-31, 09-01, 09-02) je
druhá strana tej istej mince — máme inú množinu zón.

Orezanie vstupu na rovnaké okno ako má TradingView (`--from`) trade set **nezmenilo**, takže
to nie je hĺbkou histórie.

## Pine logs — priama stopa TradingView automatu

Pine kód loguje každý prechod cez `log.info`. TradingView to zobrazuje v paneli **Pine logs**
(kontextové menu stratégie). Odtiaľ je celá stopa jeho vlastného automatu v tom istom okne:

**Zadané ordre (`STATE4->5`)** — 6:

| čas (graf) | uid | entry | SL | TP | máme? |
|---|---|---|---|---|---|
| 08-24 16:51 | **10** | 79 419.5 | 79 231.7 | 79 607.3 | ✅ `LONG_10`, identické |
| 08-24 19:06 | **9** | 79 022 | 78 541.2 | 79 502.8 | ✅ `LONG_9`, identické |
| 08-25 09:39 | **12** | 80 516.1 | 80 458.9 | 80 573.3 | ✅ `LONG_12`, identické |
| 08-27 09:06 | 31 | 78 765.1 | 78 733.7 | 78 796.5 | ❌ |
| 08-28 16:48 | 44 | 79 250 | 79 048.7 | 79 451.3 | ❌ |
| 09-02 17:15 | **64** | 76 830.9 | 76 702.4 | 76 959.4 | ✅ `LONG_91`, ceny identické (iné uid) |

Tri ordre sedia **vrátane uid** — zóny teda vznikajú v rovnakom poradí. Štvrtý (09-02) má
identické ceny aj čas, ale iné poradové číslo, takže sa medzitým počty zón rozišli.

**`STATE4 SKIP`** — TradingView má v celom okne **5** (všetky `SMER VYPNUTY`).
**`STATE3->4`** — TradingView má **5**. Spolu s 6 ordermi to dáva 11 príchodov do STATE 4,
z toho **6 cez Pin Bar**.

## Nájdená chyba: zónam nevypršala platnosť

Pôvodne sme mali **42** Pin Bar vstupov a **31** SKIP-ov proti TradingView 6 a 5.

Príčina je v Pine na riadkoch **665–681** — samostatný prechod **pred** hlavným cyklom zón:

```pine
if not array.get(zUsedA, i) and time >= array.get(zExpA, i)
    ...
    array.set(zUsedA, i, true)
```

Zóna, ktorej vypršala platnosť (`zoneValidHours = 6`) a ešte nebola použitá, sa označí ako
`used`. Tým vypadne z aktívnej množiny, lebo `active` púšťa ďalej `used` zóny len v stavoch 2–5.

Nám tento prechod chýbal — zóny v STATE 0 žili donekonečna (až po strop 200 zón) a hromadili sa.
Preto sa ich pin bar chytal mnohonásobne častejšie.

Po doplnení (`StateMachine._expire`):

| | pred | po | TradingView |
|---|---|---|---|
| SKIP: SMER VYPNUTY | 31 | **7** | 5 |
| zadaných orderov | 8 | **7** | 6 |

## Nájdená chyba: zle počítané HTF okno (104 zón namiesto 77)

Po oprave expirácie sme mali stále **104** zón proti 77 v TradingView. Hranice (`top`/`bot`)
sedeli 37 z 39, ale bar vzniku len 21 z 39 — chyba teda nebola v detekcii patternu,
ale v tom, **z ktorých štyroch 5m barov** sa pattern počítal.

Pine riadok 338:

```pine
[o5_0, ..., t5_3, v5Sma] = request.security(syminfo.tickerid, zoneDetectionTF,
    [open[1], ..., time[4], ta.sma(volume, volSmaLen)[1]],
    barmerge.gaps_off, barmerge.lookahead_off)
```

Brali sme okno z **otváracieho** času baru grafu (`bar.time // htf_ms`). Pine ale vyhodnocuje
bar pri jeho **uzavretí** a s `lookahead_off` je vtedy „aktuálnym" barom v security ten, ktorý
sa naposledy uzavrel. Výraz má navyše offset `[1]`, takže `bars[0]` je ešte o jeden bar dozadu:

```python
close_ms = ts_ms + chart_tf_ms
newest   = (close_ms // htf_ms) * htf_ms - 2 * htf_ms
```

Pri 3m grafe a 5m detekcii sa mriežky neprekrývajú, takže tento posun **nie je konštantný** —
v 15-minútovom cykle sa strieda −2 a −1 HTF bar. Preto to nešlo opraviť žiadnym pevným
posunom (skúšané `delay` 0–3 × `lag` 1–3, žiadna kombinácia nesedela).

Vedľajší dôsledok, ktorý Pine naozaj má: každý HTF bar zarovnaný na 15 minút sa nikdy
nestane `bars[0]`. Postupnosť okien je `−5, +5, +5, +10, +20, +20, …` — bary 0, 15, 30 sa
preskočia. Je to artefakt neprekrývajúcich sa mriežok, nie chyba portu.

Súčasne bolo treba zrušiť `.shift(1)` pri `vol_sma`: `ta.sma(volume, n)[1]` vo výraze security
je SMA **na bare `bars[0]` vrátane**, nie na bare pred ním.

## Výsledok: plná parita

Po oprave (`htf_window_opens()` v `ibs/core/types.py`):

| | pred | po | TradingView |
|---|---|---|---|
| zón v okne | 104 | **76** | 77 (uid 76 je za koncom stiahnutých dát) |
| zadaných orderov | 7 | **6** | 6 |
| vyplnených obchodov | — | **5** | 5 |
| winrate | — | **60 %** (3W/2L) | 60 % (3W/2L) |

Všetkých **77 zón sedí na uid, hranice aj bar vzniku** (uid 76 je za koncom stiahnutých dát). Všetkých **5 obchodov
sedí na minútu vyplnenia, vstupnú cenu, veľkosť aj výstupnú cenu**:

| # | vstup UTC | entry | qty | výstup | naše |
|---|---|---|---|---|---|
| 1 | 08-24 14:54 | 79 419,5 | 1 | 79 607,3 | `LONG_10` ✅ |
| 2 | 08-24 17:15 | 79 022,0 | 1 | 78 541,2 | `LONG_9` ✅ |
| 3 | 08-25 07:42 | 80 516,0 | 1 | 80 458,9 | `LONG_12` ✅ |
| 4 | 08-27 07:09 | 78 765,1 | 2 | 78 796,5 | `LONG_31` ✅ |
| 5 | 08-28 14:51 | 79 250,0 | 1 | 79 451,3 | `LONG_44` ✅ |

Šiesty order (`LONG_64`, 09-02 15:15) sa nikdy nevyplnil a expiroval — TradingView ho
v Pine logoch tiež má v STATE 4 a v List of Trades tiež nie je.

Regresný test: `ibs/tests/test_golden_tv_binance.py`.

## Overenie cez Freqtrade

Backtest musí bežať s profilom, ktorý zodpovedá nastaveniam v TradingView:

```bash
IBS_PROFILE=btcusdt_3m_binance_tv ./platforms/freqtrade/scripts/backtest.sh --timerange 20260824-20260905
```

S ním dá Freqtrade **5 obchodov, uid zón 10, 9, 12, 31, 44 a vstupné ceny na cent
zhodné s TradingView**. Šiesty signál (uid 64, 09-02 15:15) sa ako v TradingView
nikdy nevyplní.

S predvoleným profilom `btcusdt_3m_binance` vyjdú **iné obchody** — a je to tak správne.
Ten profil má prahy prepnuté na jednotku `atr`, takže filtruje inak než Pine defaulty
v absolútnych bodoch. Na porovnanie s TradingView treba `_tv` profil.

> **Chyba nájdená pri tomto porovnaní:** ATR sa nikdy nepočítalo. `detect_sd_pattern()`
> aj `IBSEngine.on_bar()` mali `atr: float = 0.0` a nikto ho neposielal, takže každý
> parameter v jednotke `atr` vychádzal **nula** a príslušný filter bol fakticky vypnutý.
> Prejavilo sa to zónou navyše (uid 54, 09-01 12:12 `shortV3`), ktorá posunula všetky
> ďalšie uid o +1. Opravené: `BarHistory.atr` (Wilderov RMA) + nový vstup `atrLen`.
> Po oprave má exekučný profil 66 zón namiesto 77. Na `_tv` profil to nemá vplyv —
> ten má všetko v `abs`/`ticks`.

### Výstupy: TP musí ísť cez ROI, nie cez exit-signál

Pôvodne bol TP v `custom_exit`. To je **exit-signál**, a ten sa v backteste vyhodnocuje
aj plní **otváracou cenou sviečky** (`row[OPEN_IDX]`) — knôt cez TP teda neurobí nič
a keď sa napokon spustí, cena je už za TP:

| # | TV výstup | `custom_exit` | `custom_roi` |
|---|---|---|---|
| 1 | 79 607,3 | 79 618,1 (o 10 min neskôr) | **79 607,3** ✅ |
| 2 | 78 541,2 (SL) | 78 541,2 | 78 541,2 ✅ |
| 3 | 80 458,9 (SL) | 80 459,0 | 80 459,0 (0,1 = 1 tick) |
| 4 | 78 796,5 | 78 803,4 | **78 796,5** ✅ |
| 5 | 79 451,3 | 79 460,4 | **79 451,3** ✅ |

Riešenie je `use_custom_roi = True` + `custom_roi()`, ktorý vráti
`trade.calc_profit_ratio(take_profit)`. ROI sa vyhodnocuje proti **`high`** sviečky
(pre long) a plní sa cenou z `calc_close_rate_for_roi()` orezanou do rozsahu sviečky —
teda intrabar a presne na TP, rovnako ako Pine `strategy.exit(limit=…)`. A keďže
`calc_profit_ratio()` je presná inverzia, poplatky ani páku netreba riešiť ručne.

Zvyšný rozdiel 0,1 pri obchode 3 je zaokrúhlenie SL na cenovú presnosť páru — jeden tick.

`open_date` vo výpise Freqtradu je sviečka, na ktorej sa **zadal order**, nie minúta
vyplnenia — preto pri obchode 2 ukazuje 17:09, hoci sa vyplnil o 17:15 ako v TradingView.

## Parita kreslenia

Obchody a zóny sedia, ale to nehovorí nič o tom, čo je na grafe **vidieť**. Preto
druhý golden fixture: `tv_draw_btcusdt_binance_3m.json` — súradnice objektov, ktoré
TradingView naozaj nakreslil.

Získané rovnakým trikom ako zoznam zón: do skriptu na grafe pribudlo šesť `log.info`
volaní hneď za príslušné `array.push(...)`:

| Pine riadok | objekt | čo sa loguje |
|---|---|---|
| 751 / 763 | HH/HL/LH/LL štítok | `time[structureSwingLen]`, cena pivota, text |
| 789 / 814 | BOS/CHoCH čiara | čas vzniku swingu, úroveň, čas prerazenia, text |
| 1188 / 1233 | likviditný sweep | čas swingu, úroveň, čas prepichnutia, smer |

Odčítalo sa cez filter `DRAW|` v paneli Pine logs. Log volania boli potom zo skriptu
odstránené (cez Version history späť na predošlú verziu).

Okno **2026-09-03 09:06 – 09-04 04:42 UTC** je súvislé, takže obsahuje všetky objekty,
ktoré tam TradingView nakreslil. Vďaka tomu test kontroluje aj to, že nekreslíme nič navyše.

**Výsledok: 76 z 76 objektov sedí presne** — bar vzniku, obe x súradnice, cenová úroveň
aj text:

| druh | počet | zhoda |
|---|---|---|
| HH/HL/LH/LL štítky | 50 | 50 |
| BOS/CHoCH čiary | 23 | 23 |
| likviditné sweepy | 3 | 3 |

Rozdiel v y súradnici štítkov je zámerný a test s ním počíta: Pine loguje surovú cenu
pivota, ale štítok kreslí o 25 tickov vedľa (`syminfo.mintick * 25`).

Regresný test: `ibs/tests/test_golden_tv_draw.py`.

### Čo tento fixture nepokrýva

- **SD zóny a TP/SL boxy** — tie stráži `test_golden_tv_binance.py` cez `tv_zones_*`.
- **S/R a Elliott kreslenie** — kreslia sa až na `barstate.islast`, takže sa v logu
  objavia raz a nedá sa z nich postaviť zmysluplné okno. Elliott zigzag je overený
  samostatne, viď nižšie.
- **Pozadie seáns a dashboard** — `bgcolor()` a `table.cell()` sa nedajú logovať zmysluplne.

## Obchodovanie z S/R a likvidity (overené 2026-09-04)

`enableSrTrading` a `enableLqTrading` dlho neboli overené — golden fixture vznikol
s nimi vypnutými, lebo taký bol referenčný beh.

Zmerané priamo v TradingView na tom istom grafe a rozsahu, zapnutím oboch prepínačov
v nastaveniach stratégie:

| | TradingView | engine |
|---|---|---|
| vypnuté | 5 obchodov (3W/2L) | 5 obchodov (3W/2L) |
| **zapnuté** | **6 obchodov (4W/2L)** | **6 obchodov (4W/2L)** |

Engine pritom pridá 21 S/R zón a 12 likviditných k pôvodným 76 SD zónam, a z nich
vznikne presne jeden obchod navyše — ten istý, čo v TradingView, a v oboch je ziskový.

Regresný test: `test_sr_a_likviditne_zony_sedia_s_tradingview`.

> **Pozor pri písaní ďalších testov:** `ibs.tools.scan_trades` si stavia `ZoneBook`
> a `StateMachine` sám a **nikdy nezavolá `IBSEngine`**, takže spawnovanie zón z S/R
> ani zo sweepu cez neho neprejde. Prvý pokus o toto meranie preto ukázal „SR/LQ
> nemá žiadny efekt" — test musí ísť cez `IBSEngine`.

## Elliott zigzag (overené 2026-09-04)

Elliott sa nedal overiť cez finálne vykreslenie: na BTC dá platný počet vĺn len pri
`ewSwingLen 30 / ewMinWavePoints 600`, a aj tak len na ~13 % možných posledných barov.
Overuje sa preto vrstva pod ním — **zigzag**, z ktorého sa vlny skladajú.

Postup: do `ewAddPoint` v Pine sa dočasne pridal `log.info("EW|...")`, na grafe sa
zapol Elliott (`ewSwingLen 25`, `ewMinWavePoints 600`) a z panelu logov sa odčítalo
43 bodov do `golden/tv_elliott_btcusdt_binance_3m.json`.

Výsledok: **41 z 41 bodov v súvislom úseku sedí, žiadny nechýba a žiadny nie je navyše.**

Cestou k tomu boli dve zistenia:

**Skutočná chyba v porte — pivot a zhodné hodnoty.** Pine `ta.pivothigh` pripúšťa
zhodnú hodnotu na **ľavej** (staršej) strane, ale na pravej je prísny. Náš `pivot()`
bol prísny na oboch stranách, takže zahadzoval pivoty na plochých vrcholoch.
Opravené v `ibs/core/ta/structure.py`.

**Chyba merania — log vzniká len pri pushi.** Pine loguje len pridanie bodu; keď
neskôr posunie posledný bod na extrémnejšiu hodnotu, log nevznikne. Prvé porovnanie
(TV pushe proti našim finálnym bodom) dalo 32 zo 41 a vyzeralo to ako ďalšia chyba
v porte. Test preto porovnáva **push udalosti**, nie finálny zoznam bodov.

Regresný test: `ibs/tests/test_golden_tv_elliott.py`.

## Celý Freqtrade backtest vs TradingView (2026-09-04)

Doteraz sa parita merala nad `IBSEngine` v teste. Toto je porovnanie **celého
Freqtrade backtestu** proti Strategy Testeru — teda vrátane adaptéra, limitných
príkazov, `custom_roi`, `custom_stoploss` aj peňaženky.

Nastavenia grafu: `btcusdt_3m_binance_tv` + zapnuté `enableSrTrading`
a `enableLqTrading` (RR 1, Long only, IMB + Pin Bar, Engulfing vypnutý,
trailing zapnutý). Rozsah Aug 24 – Sep 4 2026.

| # | TradingView | Freqtrade | |
|---|---|---|---|
| 1 | 79 419,5 → 79 607,3 | rovnaké | +187,8 |
| 2 | 79 022,0 → 78 541,2 | rovnaké | −480,8 |
| 3 | 80 516,0 → 80 458,9 | 80 516,1 → 80 459,0 | −57,1 |
| 4 | 78 110,3 → 78 620,8 | rovnaké | +510,5 / +504,97 |
| 5 | 78 765,1 → 78 796,5 (qty 2) | rovnaké | +62,8 |
| 6 | 79 250,0 → 79 451,3 | rovnaké | +201,3 |

**6 obchodov, 4W/2L v oboch.** Zhodujú sa smery, časy aj ceny.

### Tri rozdiely, ktoré nie sú chybou

**Zaokrúhlenie o jeden tick (obchod 3).** Známy rozdiel v zaokrúhľovaní vstupnej
ceny; posunie sa aj SL, takže PnL vyjde rovnako.

**Funding (obchod 4).** Freqtrade dá +504,97 namiesto +510,5. Rozdiel −5,53 je
presne `funding_fees` z exportu — obchod bežal 2 h 42 min a prešiel cez funding.
TradingView funding nemodeluje vôbec.

**Poplatky a peňaženka.** Pine `strategy()` nemá `commission_value`, takže
TradingView počíta bez poplatkov, a `default_qty_value=1` obchoduje 1 BTC bez
ohľadu na to, že účet má 10 000 USDT. Freqtrade s reálnym poplatkom (0,05 %/stranu)
a peňaženkou 10 000 USDT dá 6 obchodov, ale 3W/3L a −10,78 USDT — obchod 5
(+31,4 bodu, teda +0,04 %) sa na poplatkoch prevráti do straty. Nie je to iný
obchod, je to ten istý obchod s inou ekonomikou.

Preto sa porovnáva takto:

```bash
IBS_PROFILE=btcusdt_3m_binance_tv .venv/bin/python -m freqtrade backtesting   --config platforms/freqtrade/config.binance.json   --userdir platforms/freqtrade/user_data --strategy IBSImbalanceStrategy   --timeframe-detail 1m --timerange 20260824-20260905 --fee 0 --dry-run-wallet 400000
```

`--fee 0` vypne poplatky ako v Pine, `--dry-run-wallet 400000` zabezpečí, že sa
1–2 BTC pozícia vôbec zmestí (inak Freqtrade stake oreže na veľkosť peňaženky).

### Čo hlási Freqtrade inak

`open_date` je čas **vloženia** limitného príkazu, nie jeho vyplnenia. Obchod 2
tak má v exporte 17:09 UTC, hoci sa vyplnil 17:15 UTC (TradingView hlási 19:15
miestneho, teda vyplnenie). Rovnako `close_date` je presná minúta z 1m detailu,
zatiaľ čo TradingView hlási otvárací čas 3m sviečky, v ktorej výstup nastal.

