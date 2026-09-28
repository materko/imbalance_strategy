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

- 970 obchodov spolu — na štatistiku dosť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 1 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20231001-20241001, 20240904-20250904 v strate)
- break-even -0.0013 % je pod poplatkom 0.0027 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 8 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 100.0 % (namerané 77.2 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 27.0 % pri riziku, s akým beh bežal
- nie je lepšia než náhodný vstup za tých istých pravidiel (-0.3 sigma) — výber vstupu nepridáva nič
- charakter: protitrendová (mean reversion) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 192 | -4.25 | 0.0007 | 20.9 | 33.9 | +5/-12 | `20260928-073355-81eb19` |
| 20221001-20231001 | 188 | -7.03 | 0.0004 | 13.4 | 34.6 | +3/-10 | `20260928-073358-95f08a` |
| 20231001-20241001 | 203 | -26.15 | -0.0037 | 34.7 | 31.5 | +4/-16 | `20260928-073401-a24250` |
| 20240904-20250904 | 194 | -34.46 | -0.0081 | 45.1 | 32.5 | +5/-9 | `20260928-073405-de61a2` |
| 20250904-20260904 | 193 | +9.96 | 0.0060 | 22.3 | 39.4 | +7/-11 | `20260928-073408-295dca` |

Zisková v **1 z 5** okien, obchodov spolu 970, break-even celkom -0.0013 %.

## Charakter

**Protitrendová (mean reversion)** (istota priemerná)

- vstup proti poslednému pohybu (-0.76 ATR za 5 barov)
- medián držania 2 barov grafu
- winrate 34.33 %, payoff 1.713
- 0.54 obchodov za deň
- šikmosť výnosov -2.276

- **Čo je normálne:** Winrate nad 60 % a payoff pod 1 je pri tomto type v poriadku — zarába sa frekvenciou, nie veľkosťou.
- **Na čo pozor:** Jedna strata môže zmazať mesiac. Stop je tu dôležitejší než vstup a `maxLossDollar` aj drawdown limit majú väčší význam než pri ostatných typoch.
- **Čo ladiť:** Stop a filter režimu (v trende protitrendová stratégia dostáva rany). Ladiť RR nahor väčšinou len zníži winrate a nič nepridá.

Výstupy: `stop_loss` 64.9 %, `take_profit` 32.5 %, `session_end` 2.6 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0037 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 8 – 16 | 245 | 25.3 % | 26.1 | -0.0144 | 0.0024 | +0.0037 |
| do 8 | 246 | 25.4 % | 34.5 | -0.0064 | 0.0004 | +0.0017 |
| 16 – 23 | 237 | 24.4 % | 38.0 | 0.0050 | -0.0036 | -0.0023 |
| nad 23 | 242 | 24.9 % | 38.8 | 0.0081 | -0.0047 | -0.0034 |

**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| deň po sviatku | 27 | 2.8 % | 37.0 | -0.0078 | -0.0012 | +0.0001 |
| bežný deň | 899 | 92.7 % | 33.8 | -0.0019 | 0.0019 | +0.0032 |
| deň pred sviatkom | 13 | 1.3 % | 46.1 | 0.0053 | -0.0014 | -0.0001 |

**Hodina vstupu (UTC)** (riadi `entryWindowMinutes`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 14 h | 324 | 33.4 % | 32.1 | -0.0088 | 0.0018 | +0.0031 |
| nad 16 h | 136 | 14.0 % | 35.3 | -0.0023 | -0.0011 | +0.0002 |
| 15 h – 16 h | 169 | 17.4 % | 33.1 | -0.0011 | -0.0014 | -0.0001 |
| 14 h – 15 h | 341 | 35.2 % | 36.7 | 0.0054 | -0.0049 | -0.0036 |

Parametre, ktorými sa dá s tým niečo spraviť: `closeAtSessionEnd`, `driftMinAtr`, `entryMode`, `entryWindowMinutes`, `rrRatio`, `slBufferAtr`, `slMode`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0012 % | -0.0002 % ± 0.0027 | -0.35 | 36.5 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0012 % | -0.0003 % ± 0.0033 | -0.29 | 39.2 |

Neodlisitelne od nahody (-0.3 sigma, percentil 36.5). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 238 | 16.1 | 34.0 | -0.0003 | 54 |
| 2022-12 - 2024-03 | 235 | 15.9 | 32.8 | -0.0020 | 43 |
| 2024-03 - 2025-06 | 257 | 17.4 | 34.2 | -0.0038 | 31 |
| 2025-06 - 2026-09 | 240 | 16.3 | 36.2 | 0.0014 | 67 |

Hranice pre úsek veľkosti posledného obdobia: -0.0119 až +0.0084 % (medián -0.0011).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 67. percentile, teda v medziach -0.0119 až +0.0084 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

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

**Straty za sebou: 18** — 2024-08-29T15:25 až 2024-09-18T14:42, spolu -1375.20.

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
| 9 | 2024-09-11T15:35 | 2024-09-11T15:38 | -68.02 | -0.18 | `stop_loss` |
| 10 | 2024-09-11T15:35 | 2024-09-11T15:38 | -68.02 | -0.18 | `stop_loss` |
| 11 | 2024-09-12T14:40 | 2024-09-12T15:46 | -102.08 | -0.26 | `stop_loss` |
| 12 | 2024-09-12T14:40 | 2024-09-12T15:46 | -102.08 | -0.26 | `stop_loss` |
| 13 | 2024-09-13T14:15 | 2024-09-13T14:29 | -53.60 | -0.14 | `stop_loss` |
| 14 | 2024-09-13T14:15 | 2024-09-13T14:29 | -53.60 | -0.14 | `stop_loss` |
| 15 | 2024-09-16T15:30 | 2024-09-16T17:39 | -77.12 | -0.20 | `stop_loss` |
| 16 | 2024-09-16T15:30 | 2024-09-16T17:39 | -77.12 | -0.20 | `stop_loss` |
| 17 | 2024-09-18T14:35 | 2024-09-18T14:42 | -63.12 | -0.16 | `stop_loss` |
| 18 | 2024-09-18T14:35 | 2024-09-18T14:42 | -63.12 | -0.16 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0013 %**, medián -0.0013 %, 90 % interval -0.0065–0.0034 %
- P(edge > poplatok) = **8.3 %**
- max drawdown: medián 77.2 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 15, 95. percentil 22 obchodov
- pravdepodobnosť ruiny účtu: 27.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **14** na obchod pri účte 10 000

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

<!-- POSUDOK cisla=8e607315 -->

**1. Na čo sa to hodí a na čo nie.** Meraná je stratégia z videa IQCapital tak, ako ju autor
povedal: MNQ 5m, VWAP od 9:30 NY z 15m sviečok, prvý pullback v smere dňa (posledný jasný
drift). Video neuvádza stop ani cieľ, takže vstup `close`, stop za pullback a RR 2 sú náš
odhad, nie predloha. V tejto podobe sa nehodí nikam. Zisková je v 1 z 5 rokov (2025/26,
+10,0 %), break-even −0,0013 % je pod poplatkom 0,0027 % a pravdepodobnosť ruiny je 27 %.
Stratégia potrebuje skutočný objem burzy. Na CME futures (Databento) VWAP sedí, na Dukascopy
NAS100 je v objeme len aktivita tickov. Tvrdenie „93,6 % šanca prejsť challenge" z nadpisu
videa tieto dáta nepodopierajú.

**2. Má to potenciál?** V pôvodnej podobe nie. Od náhodného vstupu sa nelíši (−0,3 sigma)
a edge je nad poplatkom len v 8,3 % bootstrap vzoriek. Signál je stabilný (188–203 obchodov
za rok), nejde teda o náhodne sa zapínajúci filter, ale výber vstupu nič nepridáva. Z matice
na piatich oknách: **`limit` na VWAP so stopom `vwap`** je zisková v 2 z 5 rokov (2024/25
+15,8 %, 2025/26 +12,9 %), break-even +0,0012 % pod poplatkom, a 2022/23 −62,6 %.
Prepínače `everyBounce` a `tradeBreakout` výsledok nezlepšili: každý odraz dáva 0 z 5
(s `limit` 1 z 5 a trikrát zničený účet), prerazenie v oboch smeroch 1 z 5 (2024/25 −92 %),
len v smere dňa 1 z 5, obe spolu 0 z 5. Viac obchodov z toho istého signálu tu znamená
viac poplatkov, nie viac edge. Dobrý rok 2025/26 sa opakuje takmer v každej verzii a je
vlastnosťou toho roka, nie stratégie.

**3. Čo treba dorobiť.** (a) **Skrátené dni a sviatky:** 3. 7. 2026 (skrátený deň) nebol
po 15:55 žiadny bar a pozícia prežila víkend až do nedeľnej 22:00 UTC. Treba zatvárať aj
na prvom bare nového dňa, prípadne mať kalendár skrátených seáns (týka sa to aj
`breakout` a `orb`). (b) **Stop:** 65 % obchodov končí na stope a medián držania sú 2 bary;
stop za pullback aj pod sviečku sú na 5m príliš tesné. (c) **Filter typu dňa:** vstup je
protitrendový voči poslednému pohybu (−0,76 ATR za 5 barov) a v silných trendových dňoch
(2022/23, 2024/25) dostáva rany. Drift VWAP meria smer, nie to, či je deň trendový alebo
rotačný.

**4. Čo otestovať ďalej.** Verziu `limit` + `vwap`: `cli sweep --strategy vwapdrift --set
entryMode=limit --set slMode=vwap` cez `rrRatio` 0,75–3 a `slBufferAtr` 0–1 **len na okne
20231001-20241001**, potom víťaza bez zmeny na ostatných štyroch. Rozhodne to, či existuje
nastavenie ziskové v 4 z 5 rokov a nad poplatkom. Druhý beh: `--set vwapAnchor=session`
(klasický VWAP od 18:00) proti `ny_open`. Freqtrade tu nemá zmysel, MNQ ide len cez emulátor
MultiCharts.

**5. Je to použiteľné, alebo je to o ničom?** V podobe z videa aj so všetkými variantmi
vstupu, stopu, každého odrazu a prerazenia **o ničom**: žiadna verzia nie je zisková
v 3 z 5 rokov nad poplatkom a žiadna nie je lepšia než náhoda. Jediná stopa je `limit` +
`vwap` (dva posledné roky v pluse), ktorá stojí za test z bodu 4. Ak ani on nenájde
nastavenie ziskové v 4 z 5 okien nad poplatkom, treba stratégiu uzavrieť. Použiteľný je
samotný VWAP (`tradebot.core.vwap`), ktorý overene sedí s nezávislým výpočtom na celej
histórii MNQ 2019–2026.

**6. Čo by som pridal.** VWAP pásma (±1σ a ±2σ, štandardná odchýlka vážená objemom)
a limitku nie na samotný VWAP, ale na hranu pásma −1σ v smere dňa. V trendový deň sa cena
k VWAP často vôbec nevráti a prvý dotyk je potom práve ten deň, keď sa trend láme. Druhý
nápad: filter typu dňa, teda obchodovať len dni, keď otvorenie leží mimo rozpätia
predošlého dňa, a rotačným dňom sa vyhnúť.

<!-- POSUDOK KONIEC -->
