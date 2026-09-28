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

- 1005 obchodov spolu — na štatistiku dosť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 1 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20231001-20241001, 20240904-20250904 v strate)
- break-even -0.0024 % je pod poplatkom 0.0027 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 5 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 100.0 % (namerané 90.1 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 40.6 % pri riziku, s akým beh bežal
- nie je lepšia než náhodný vstup za tých istých pravidiel (-1.3 sigma) — výber vstupu nepridáva nič
- charakter: protitrendová (mean reversion) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 198 | -8.65 | -0.0015 | 28.7 | 33.3 | +6/-13 | `20260928-072338-65af60` |
| 20221001-20231001 | 195 | -12.68 | -0.0018 | 19.1 | 34.4 | +3/-11 | `20260928-072341-060259` |
| 20231001-20241001 | 209 | -27.97 | -0.0047 | 36.2 | 31.6 | +4/-15 | `20260928-072344-6f4b53` |
| 20240904-20250904 | 202 | -43.59 | -0.0112 | 53.9 | 32.2 | +5/-10 | `20260928-072347-637f04` |
| 20250904-20260904 | 201 | +16.27 | 0.0079 | 20.9 | 39.3 | +7/-11 | `20260928-072350-842376` |

Zisková v **1 z 5** okien, obchodov spolu 1005, break-even celkom -0.0024 %.

## Charakter

**Protitrendová (mean reversion)** (istota priemerná)

- vstup proti poslednému pohybu (-0.54 ATR za 5 barov)
- medián držania 2.4 barov grafu
- winrate 34.13 %, payoff 1.703
- 0.56 obchodov za deň
- šikmosť výnosov -1.135

- **Čo je normálne:** Winrate nad 60 % a payoff pod 1 je pri tomto type v poriadku — zarába sa frekvenciou, nie veľkosťou.
- **Na čo pozor:** Jedna strata môže zmazať mesiac. Stop je tu dôležitejší než vstup a `maxLossDollar` aj drawdown limit majú väčší význam než pri ostatných typoch.
- **Čo ladiť:** Stop a filter režimu (v trende protitrendová stratégia dostáva rany). Ladiť RR nahor väčšinou len zníži winrate a nič nepridá.

Výstupy: `stop_loss` 65 %, `take_profit` 31.3 %, `session_end` 3.7 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0045 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Hodina vstupu (UTC)** (riadi `entryWindowMinutes`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 14 h | 385 | 38.3 % | 31.4 | -0.0115 | 0.0021 | +0.0045 |
| nad 16 h | 125 | 12.4 % | 36.0 | -0.0020 | -0.0025 | -0.0001 |
| 14 h – 15 h | 353 | 35.1 % | 35.7 | 0.0032 | -0.0054 | -0.0030 |
| 15 h – 16 h | 142 | 14.1 % | 35.9 | 0.0037 | -0.0036 | -0.0012 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 8 – 16 | 255 | 25.4 % | 25.1 | -0.0181 | 0.0021 | +0.0045 |
| do 8 | 255 | 25.4 % | 33.7 | -0.0094 | -0.0002 | +0.0022 |
| 16 – 23 | 248 | 24.7 % | 37.9 | 0.0066 | -0.0058 | -0.0034 |
| nad 23 | 247 | 24.6 % | 40.1 | 0.0083 | -0.0062 | -0.0038 |

**Vzdialenosť stopu** (riadi `slBufferAtr`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 0.2456 % | 250 | 24.9 % | 31.2 | -0.0361 | 0.0020 | +0.0044 |
| 0.094 % – 0.1503 % | 251 | 25.0 % | 27.9 | -0.0120 | 0.0002 | +0.0026 |
| do 0.094 % | 252 | 25.1 % | 35.7 | 0.0018 | -0.0073 | -0.0049 |
| 0.1503 % – 0.2456 % | 252 | 25.1 % | 41.7 | 0.0238 | -0.0067 | -0.0043 |

Parametre, ktorými sa dá s tým niečo spraviť: `closeAtSessionEnd`, `driftMinAtr`, `entryMode`, `entryWindowMinutes`, `rrRatio`, `slBufferAtr`, `slMode`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0046 % | -0.0000 % ± 0.0034 | -1.33 | 9.1 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0046 % | -0.0000 % ± 0.0037 | -1.23 | 9.9 |

HORSIE nez nahoda (-1.3 sigma). Nahodny vstup za tych istych pravidiel dava lepsi vysledok - vyber vstupu vysledku skodi.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 245 | 16.6 | 33.1 | -0.0038 | 44 |
| 2022-12 - 2024-03 | 245 | 16.6 | 33.5 | -0.0026 | 49 |
| 2024-03 - 2025-06 | 266 | 18.0 | 33.5 | -0.0076 | 20 |
| 2025-06 - 2026-09 | 249 | 16.9 | 36.5 | 0.0038 | 83 |

Hranice pre úsek veľkosti posledného obdobia: -0.0140 až +0.0081 % (medián -0.0024).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 83. percentile, teda v medziach -0.0140 až +0.0081 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 7** — 2026-02-19T15:15 až 2026-03-02T15:47, spolu +1086.72.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-02-19T15:15 | 2026-02-19T15:34 | +118.81 | +0.24 | `take_profit` |
| 2 | 2026-02-20T15:35 | 2026-02-20T15:43 | +195.31 | +0.39 | `take_profit` |
| 3 | 2026-02-23T15:25 | 2026-02-23T15:52 | +169.32 | +0.34 | `take_profit` |
| 4 | 2026-02-25T15:20 | 2026-02-25T15:28 | +152.54 | +0.15 | `take_profit` |
| 5 | 2026-02-26T16:30 | 2026-02-26T16:46 | +154.80 | +0.31 | `take_profit` |
| 6 | 2026-02-27T16:45 | 2026-02-27T16:51 | +141.62 | +0.14 | `take_profit` |
| 7 | 2026-03-02T15:35 | 2026-03-02T15:47 | +154.31 | +0.31 | `take_profit` |

**Straty za sebou: 20** — 2024-08-29T15:25 až 2024-09-18T14:30, spolu -1788.24.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-08-29T15:25 | 2024-08-29T17:48 | -88.61 | -0.23 | `stop_loss` |
| 2 | 2024-08-30T14:15 | 2024-08-30T14:15 | -99.33 | -0.08 | `stop_loss` |
| 3 | 2024-09-04T15:35 | 2024-09-04T18:37 | -92.05 | -0.24 | `stop_loss` |
| 4 | 2024-09-04T15:35 | 2024-09-04T18:37 | -92.05 | -0.24 | `stop_loss` |
| 5 | 2024-09-05T17:45 | 2024-09-05T17:46 | -84.14 | -0.07 | `stop_loss` |
| 6 | 2024-09-05T17:45 | 2024-09-05T17:46 | -84.14 | -0.07 | `stop_loss` |
| 7 | 2024-09-09T15:45 | 2024-09-09T15:50 | -53.51 | -0.14 | `stop_loss` |
| 8 | 2024-09-09T15:45 | 2024-09-09T15:50 | -53.51 | -0.14 | `stop_loss` |
| 9 | 2024-09-10T14:15 | 2024-09-10T18:01 | -195.02 | -0.52 | `stop_loss` |
| 10 | 2024-09-10T14:15 | 2024-09-10T18:01 | -195.02 | -0.52 | `stop_loss` |
| 11 | 2024-09-11T15:35 | 2024-09-11T15:38 | -68.02 | -0.18 | `stop_loss` |
| 12 | 2024-09-11T15:35 | 2024-09-11T15:38 | -68.02 | -0.18 | `stop_loss` |
| 13 | 2024-09-12T14:40 | 2024-09-12T15:46 | -102.08 | -0.26 | `stop_loss` |
| 14 | 2024-09-12T14:40 | 2024-09-12T15:46 | -102.08 | -0.26 | `stop_loss` |
| 15 | 2024-09-13T14:15 | 2024-09-13T14:29 | -53.60 | -0.14 | `stop_loss` |
| 16 | 2024-09-13T14:15 | 2024-09-13T14:29 | -53.60 | -0.14 | `stop_loss` |
| 17 | 2024-09-16T15:30 | 2024-09-16T17:39 | -77.12 | -0.20 | `stop_loss` |
| 18 | 2024-09-16T15:30 | 2024-09-16T17:39 | -77.12 | -0.20 | `stop_loss` |
| 19 | 2024-09-18T14:20 | 2024-09-18T14:30 | -74.62 | -0.19 | `stop_loss` |
| 20 | 2024-09-18T14:20 | 2024-09-18T14:30 | -74.62 | -0.19 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0024 %**, medián -0.0025 %, 90 % interval -0.0082–0.0028 %
- P(edge > poplatok) = **5.3 %**
- max drawdown: medián 90.1 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 16, 95. percentil 22 obchodov
- pravdepodobnosť ruiny účtu: 40.6 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **12** na obchod pri účte 10 000

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

<!-- POSUDOK cisla=7477586c -->

**1. Na čo sa to hodí a na čo nie.** Meraná je stratégia z videa IQCapital tak, ako ju autor
povedal: MNQ 5m, VWAP od 9:30 NY z 15m sviečok, prvý pullback v smere dňa (posledný jasný
drift). Dotyk, ktorý zavrie kúsok za VWAP, je stále pullback; prerazený je až pri zavretí
o viac než 0,5 ATR. Video neuvádza stop ani cieľ, takže vstup `close`, stop za pullback
a RR 2 sú náš odhad, nie predloha. V tejto podobe sa nehodí nikam. Zisková je v 1 z 5 rokov
(2025/26, +16,3 %), break-even −0,0024 % je pod poplatkom 0,0027 % a pravdepodobnosť ruiny
je 40,6 %. Stratégia potrebuje skutočný objem burzy. Na CME futures (Databento) VWAP sedí,
na Dukascopy NAS100 je v objeme len aktivita tickov. Tvrdenie „93,6 % šanca prejsť
challenge" z nadpisu videa tieto dáta nepodopierajú.

**2. Má to potenciál?** V pôvodnej podobe nie. Náhodný vstup za tých istých pravidiel je
lepší (−1,3 sigma) a edge je nad poplatkom len v 5,3 % bootstrap vzoriek. Signál je stabilný
(195–209 obchodov za rok v každom okne), takže nejde o náhodne sa zapínajúci filter. Z matice
vstupov a stopov (päť okien) jediná verzia s náznakom zostáva **`limit` na VWAP so stopom
`vwap`**. Je zisková v 3 z 5 rokov, v troch posledných za sebou (+0,05 %, +11,1 %, +19,5 %),
break-even +0,0012 %, stále pod poplatkom, a 2022/23 −70,8 % ju zabíja. `reaction` + `swing`
dáva 2 z 5 (−0,6 sigma). `reaction` + `candle` (stop pod reakčnú sviečku) dáva pri RR 1
winrate 46–52 %, ale 0 z 5 ziskových rokov a pri RR 2 1 z 5. Stop pod reakčnú sviečku je
na 5m príliš tesný. Dobrý rok 2025/26 sa opakuje takmer v každej verzii, preto ho treba
brať ako vlastnosť toho roka, nie stratégie.

**3. Čo treba dorobiť.** (a) **Skrátené dni a sviatky:** 3. 7. 2026 (skrátený deň) nebol
po 15:55 žiadny bar a pozícia prežila víkend až do nedeľnej 22:00 UTC. Treba zatvárať aj
na prvom bare nového dňa, prípadne mať kalendár skrátených seáns (týka sa to aj
`breakout` a `orb`). (b) **Stop:** 65 % obchodov končí na stope a medián držania je 2,4 baru;
stop za pullback aj pod sviečku sú na 5m príliš tesné. (c) **Filter typu dňa:** vstup je
protitrendový voči poslednému pohybu (−0,54 ATR za 5 barov) a v silných trendových dňoch
(2022/23) dostáva rany. Drift VWAP meria smer, nie to, či je deň trendový alebo rotačný.

**4. Čo otestovať ďalej.** Verziu `limit` + `vwap`: `cli sweep --strategy vwapdrift --set
entryMode=limit --set slMode=vwap` cez `rrRatio` 0,75–3 a `slBufferAtr` 0–1 **len na okne
20231001-20241001**, potom víťaza bez zmeny na ostatných štyroch. Rozhodne to, či existuje
nastavenie ziskové v 4 z 5 rokov a nad poplatkom. Druhý beh: `--set vwapAnchor=session`
(klasický VWAP od 18:00) proti `ny_open`. Freqtrade tu nemá zmysel, MNQ ide len cez emulátor
MultiCharts.

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
