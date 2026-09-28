# Základná analytika — Drift VWAP Pullback — prvý návrat k VWAP v smere driftu (`vwapdrift`)

Zmerané 2026-09-28 na `MNQ/USD` 5m, engine `multicharts`, poplatok 0.0027 % na stranu (1.5 tick na stranu pri cene 13913.8 = 0.00270 %; odhad: polovica spreadu 0,5 ticku + provizia ~0,5 $ na stranu = 1 tick, spolu 1,5 ticku (0,375 bodu); spread z ohlcv dat nevidno), profil `mnq_databento_5m`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy vwapdrift \
   --profile mnq_databento_5m \
   --pair MNQ/USD \
   --timeframe 5m
```

## V čom je dobrá

- 896 obchodov spolu — na štatistiku dosť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 1 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20231001-20241001, 20240904-20250904 v strate)
- break-even -0.0045 % je pod poplatkom 0.0027 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 1 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 100.0 % (namerané 100.0 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 58.6 % pri riziku, s akým beh bežal
- nie je lepšia než náhodný vstup za tých istých pravidiel (-2.8 sigma) — výber vstupu nepridáva nič
- charakter: protitrendová (mean reversion) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 169 | -8.68 | -0.0019 | 23.0 | 33.1 | +4/-18 | `20260928-071634-0056bd` |
| 20221001-20231001 | 176 | -20.23 | -0.0052 | 21.9 | 31.8 | +4/-11 | `20260928-071637-d283fe` |
| 20231001-20241001 | 190 | -37.58 | -0.0075 | 45.7 | 28.9 | +4/-10 | `20260928-071640-821e4a` |
| 20240904-20250904 | 183 | -38.45 | -0.0100 | 48.8 | 32.2 | +7/-9 | `20260928-071644-f0d9ee` |
| 20250904-20260904 | 178 | +3.77 | 0.0040 | 21.5 | 37.6 | +7/-19 | `20260928-071647-e021d0` |

Zisková v **1 z 5** okien, obchodov spolu 896, break-even celkom -0.0045 %.

## Charakter

**Protitrendová (mean reversion)** (istota priemerná)

- vstup proti poslednému pohybu (-0.52 ATR za 5 barov)
- medián držania 2.1 barov grafu
- winrate 32.7 %, payoff 1.708
- 0.5 obchodov za deň
- šikmosť výnosov -1.484

- **Čo je normálne:** Winrate nad 60 % a payoff pod 1 je pri tomto type v poriadku — zarába sa frekvenciou, nie veľkosťou.
- **Na čo pozor:** Jedna strata môže zmazať mesiac. Stop je tu dôležitejší než vstup a `maxLossDollar` aj drawdown limit majú väčší význam než pri ostatných typoch.
- **Čo ladiť:** Stop a filter režimu (v trende protitrendová stratégia dostáva rany). Ladiť RR nahor väčšinou len zníži winrate a nič nepridá.

Výstupy: `stop_loss` 66.7 %, `take_profit` 30.7 %, `session_end` 2.6 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0048 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Vzdialenosť stopu** (riadi `slBufferAtr`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 0.234 % | 223 | 24.9 % | 30.0 | -0.0437 | 0.0003 | +0.0048 |
| 0.089 % – 0.1376 % | 224 | 25.0 % | 26.8 | -0.0120 | -0.0023 | +0.0022 |
| do 0.089 % | 225 | 25.1 % | 35.1 | 0.0012 | -0.0108 | -0.0063 |
| 0.1376 % – 0.234 % | 224 | 25.0 % | 38.8 | 0.0165 | -0.0079 | -0.0034 |

**Hodina vstupu (UTC)** (riadi `entryWindowMinutes`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 14 h | 346 | 38.6 % | 30.1 | -0.0128 | -0.0004 | +0.0041 |
| nad 16 h | 119 | 13.3 % | 32.8 | -0.0056 | -0.0043 | +0.0002 |
| 14 h – 15 h | 305 | 34.0 % | 35.1 | 0.0012 | -0.0073 | -0.0028 |
| 15 h – 16 h | 126 | 14.1 % | 34.1 | 0.0018 | -0.0057 | -0.0012 |

**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| deň po sviatku | 27 | 3.0 % | 33.3 | -0.0135 | -0.0043 | +0.0002 |
| deň pred sviatkom | 9 | 1.0 % | 33.3 | -0.0067 | -0.0045 | +0.0000 |
| bežný deň | 830 | 92.6 % | 32.5 | -0.0050 | -0.0013 | +0.0032 |

Parametre, ktorými sa dá s tým niečo spraviť: `closeAtSessionEnd`, `driftMinAtr`, `entryMode`, `entryWindowMinutes`, `rrRatio`, `slBufferAtr`, `slMode`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0089 % | -0.0000 % ± 0.0032 | -2.75 | 0.3 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0089 % | -0.0001 % ± 0.0037 | -2.37 | 0.9 |

HORSIE nez nahoda (-2.8 sigma). Nahodny vstup za tych istych pravidiel dava lepsi vysledok - vyber vstupu vysledku skodi.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 210 | 14.2 | 32.4 | -0.0049 | 50 |
| 2022-12 - 2024-03 | 222 | 15.1 | 31.5 | -0.0046 | 45 |
| 2024-03 - 2025-06 | 242 | 16.4 | 32.6 | -0.0078 | 32 |
| 2025-06 - 2026-09 | 222 | 15.1 | 34.2 | -0.0006 | 72 |

Hranice pre úsek veľkosti posledného obdobia: -0.0157 až +0.0062 % (medián -0.0045).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 72. percentile, teda v medziach -0.0157 až +0.0062 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 7** — 2025-02-14T15:20 až 2025-02-26T15:33, spolu +1106.84, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-02-14T15:20 | 2025-02-14T15:26 | +186.45 | +0.11 | `take_profit` |
| 2 | 2025-02-17T17:15 | 2025-02-17T17:50 | +153.62 | +0.06 | `take_profit` |
| 3 | 2025-02-18T15:15 | 2025-02-18T15:16 | +160.82 | +0.12 | `take_profit` |
| 4 | 2025-02-19T20:30 | 2025-02-19T20:57 | +145.21 | +0.16 | `take_profit` |
| 5 | 2025-02-21T15:15 | 2025-02-21T15:28 | +162.12 | +0.37 | `take_profit` |
| 6 | 2025-02-25T18:35 | 2025-02-25T18:43 | +125.21 | +0.30 | `take_profit` |
| 7 | 2025-02-26T15:30 | 2025-02-26T15:33 | +173.41 | +0.20 | `take_profit` |

**Straty za sebou: 19** — 2026-06-03T15:00 až 2026-07-14T14:34, spolu -2341.23.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-06-03T15:00 | 2026-06-03T15:22 | -72.80 | -0.12 | `stop_loss` |
| 2 | 2026-06-09T18:35 | 2026-06-09T18:58 | -140.63 | -0.24 | `stop_loss` |
| 3 | 2026-06-11T14:15 | 2026-06-11T14:16 | -77.61 | -0.13 | `stop_loss` |
| 4 | 2026-06-18T14:30 | 2026-06-18T14:30 | -81.29 | -0.13 | `stop_loss` |
| 5 | 2026-06-19T15:35 | 2026-06-19T15:36 | -112.84 | -0.03 | `stop_loss` |
| 6 | 2026-06-22T14:20 | 2026-06-22T14:20 | -88.83 | -0.14 | `stop_loss` |
| 7 | 2026-06-23T14:45 | 2026-06-23T14:46 | -62.72 | -0.10 | `stop_loss` |
| 8 | 2026-06-24T14:20 | 2026-06-24T14:27 | -270.70 | -0.46 | `stop_loss` |
| 9 | 2026-06-25T14:15 | 2026-06-25T14:51 | -346.69 | -0.59 | `stop_loss` |
| 10 | 2026-07-01T14:35 | 2026-07-01T14:36 | -67.26 | -0.11 | `stop_loss` |
| 11 | 2026-07-02T14:15 | 2026-07-02T14:18 | -211.25 | -0.35 | `stop_loss` |
| 12 | 2026-07-03T14:20 | 2026-07-05T22:00 | -65.73 | -0.11 | `stop_loss` |
| 13 | 2026-07-06T15:15 | 2026-07-06T15:17 | -78.73 | -0.13 | `stop_loss` |
| 14 | 2026-07-07T18:50 | 2026-07-07T18:51 | -89.17 | -0.15 | `stop_loss` |
| 15 | 2026-07-08T15:00 | 2026-07-08T16:30 | -208.15 | -0.36 | `stop_loss` |
| 16 | 2026-07-09T14:45 | 2026-07-09T14:58 | -112.21 | -0.19 | `stop_loss` |
| 17 | 2026-07-10T14:20 | 2026-07-10T14:21 | -55.72 | -0.09 | `stop_loss` |
| 18 | 2026-07-13T14:45 | 2026-07-13T14:46 | -61.19 | -0.10 | `stop_loss` |
| 19 | 2026-07-14T14:30 | 2026-07-14T14:34 | -137.70 | -0.23 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0045 %**, medián -0.0045 %, 90 % interval -0.0100–0.0005 %
- P(edge > poplatok) = **0.9 %**
- max drawdown: medián 100.0 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 16, 95. percentil 23 obchodov
- pravdepodobnosť ruiny účtu: 58.6 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **11** na obchod pri účte 10 000

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

<!-- POSUDOK cisla=834cf7e3 -->

**1. Na čo sa to hodí a na čo nie.** Meraná je stratégia z videa IQCapital tak, ako ju autor
povedal: MNQ 5m, VWAP od 9:30 NY z 15m sviečok, prvý pullback v smere driftu. Smer dňa je
posledný jasný drift a odchod od VWAP sa eviduje aj skôr, než má VWAP smer. Video neuvádza
stop ani cieľ, takže vstup `close`, stop za pullback a RR 2 sú náš odhad, nie predloha.
V tejto podobe sa nehodí nikam. Zisková je v 1 z 5 rokov (2025/26, +3,8 %), break-even
−0,0045 % je pod poplatkom 0,0027 % a pravdepodobnosť ruiny je 58,6 %. Stratégia potrebuje
skutočný objem burzy. Na CME futures (Databento) VWAP sedí, na Dukascopy NAS100 je v objeme
len aktivita tickov a to isté číslo by znamenalo niečo iné. Tvrdenie „93,6 % šanca prejsť
challenge" z nadpisu videa tieto dáta nepodopierajú.

**2. Má to potenciál?** V pôvodnej podobe nie. Náhodný vstup za tých istých pravidiel je
lepší (−2,8 sigma) a edge je nad poplatkom len v 0,9 % bootstrap vzoriek. Signál je pritom
stabilný: 35–40 obchodov za štvrťrok v každom roku, takže nejde o náhodne sa zapínajúci filter.
Z matice vstupov a stopov (päť okien) vychádza jediná verzia s náznakom:
**`limit` na VWAP so stopom `vwap`**. Je zisková v 3 z 5 rokov a v troch posledných za sebou
(2023/24 +0,05 %, 2024/25 +11,1 %, 2025/26 +19,5 %), break-even celkom +0,0012 %, stále
pod poplatkom. Rok 2022/23 (−70,8 %, drawdown 76 %) ju však zabíja. Potvrdzovacie vstupy
(`reaction`, `pinbar`, `engulfing`) a stop pod reakčnú sviečku (`candle`) sú na piatich
oknách horšie než náhoda. `reaction` + `candle` dáva 1 z 5 a −4,0 sigma: čakanie na
potvrdenie vstup zhorší a tesný stop pod sviečku vyberie šum.

**3. Čo treba dorobiť.** (a) **Skrátené dni a sviatky:** 3. 7. 2026 (skrátený deň) nebol
po 15:55 žiadny bar a pozícia prežila víkend až do nedeľnej 22:00 UTC. Treba zatvárať aj
na prvom bare nového dňa, prípadne mať kalendár skrátených seáns (týka sa to aj
`breakout` a `orb`). (b) **Stop:** 67 % obchodov končí na stope a medián držania je 2,1 baru.
Na 5m je stop za pullback aj pod sviečku príliš tesný. (c) **Filter typu dňa:** vstup je
protitrendový voči poslednému pohybu (−0,52 ATR za 5 barov) a v silných trendových dňoch
(2022/23) dostáva rany. Drift VWAP meria smer, nie to, či je deň trendový alebo rotačný.

**4. Čo otestovať ďalej.** Verziu `limit` + `vwap`: `cli sweep --strategy vwapdrift --set
entryMode=limit --set slMode=vwap` cez `rrRatio` 0,75–3 a `slBufferAtr` 0–1 **len na okne
20231001-20241001**, potom víťaza bez zmeny na ostatných štyroch. Rozhodne to, či existuje
nastavenie ziskové v 4 z 5 rokov a nad poplatkom. Druhý beh: `--set vwapAnchor=session`
(klasický VWAP od 18:00) proti `ny_open`. Tieto dve kotvy dávajú v ten istý deň desiatky
bodov rozdiel. Freqtrade tu nemá zmysel, MNQ ide len cez emulátor MultiCharts.

**5. Je to použiteľné, alebo je to o ničom?** V podobe z videa **o ničom**: horšie než
náhoda, pod poplatkom a zisková v jednom roku z piatich. Jediná stopa je `limit` + `vwap`
(3 z 5, posledné tri roky v pluse). Stojí za test z bodu 4 a ak ani on nenájde nastavenie
ziskové v 4 z 5 okien nad poplatkom, treba stratégiu uzavrieť. Použiteľný je samotný VWAP
(`tradebot.core.vwap`), ktorý overene sedí s nezávislým výpočtom na celej histórii MNQ
2019–2026.

**6. Čo by som pridal.** VWAP pásma (±1σ a ±2σ, štandardná odchýlka vážená objemom)
a limitku nie na samotný VWAP, ale na hranu pásma −1σ v smere dňa. V trendový deň sa cena
k VWAP často vôbec nevráti a prvý dotyk je potom práve ten deň, keď sa trend láme. Druhý
nápad: filter typu dňa, teda obchodovať len dni, keď otvorenie leží mimo rozpätia
predošlého dňa, a rotačným dňom sa vyhnúť.

<!-- POSUDOK KONIEC -->
