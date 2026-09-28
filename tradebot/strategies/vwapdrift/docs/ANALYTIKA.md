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

- 853 obchodov spolu — na štatistiku dosť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 1 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20231001-20241001, 20240904-20250904 v strate)
- break-even -0.0031 % je pod poplatkom 0.0027 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 3 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 100.0 % (namerané 90.0 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 39.5 % pri riziku, s akým beh bežal
- nie je lepšia než náhodný vstup za tých istých pravidiel (-1.9 sigma) — výber vstupu nepridáva nič
- charakter: protitrendová (mean reversion) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 156 | -11.80 | -0.0037 | 26.1 | 33.3 | +4/-16 | `20260928-071142-28e9af` |
| 20221001-20231001 | 164 | -21.43 | -0.0062 | 22.9 | 31.1 | +3/-10 | `20260928-071145-37907d` |
| 20231001-20241001 | 182 | -13.07 | -0.0008 | 22.6 | 34.1 | +4/-9 | `20260928-071148-d9b646` |
| 20240904-20250904 | 178 | -36.74 | -0.0097 | 45.5 | 33.1 | +4/-8 | `20260928-071151-8ad3d6` |
| 20250904-20260904 | 173 | +3.44 | 0.0039 | 19.9 | 37.0 | +4/-18 | `20260928-071154-60853a` |

Zisková v **1 z 5** okien, obchodov spolu 853, break-even celkom -0.0031 %.

## Charakter

**Protitrendová (mean reversion)** (istota priemerná)

- vstup proti poslednému pohybu (-0.68 ATR za 5 barov)
- medián držania 2.4 barov grafu
- winrate 33.76 %, payoff 1.689
- 0.48 obchodov za deň
- šikmosť výnosov -1.468

- **Čo je normálne:** Winrate nad 60 % a payoff pod 1 je pri tomto type v poriadku — zarába sa frekvenciou, nie veľkosťou.
- **Na čo pozor:** Jedna strata môže zmazať mesiac. Stop je tu dôležitejší než vstup a `maxLossDollar` aj drawdown limit majú väčší význam než pri ostatných typoch.
- **Čo ladiť:** Stop a filter režimu (v trende protitrendová stratégia dostáva rany). Ladiť RR nahor väčšinou len zníži winrate a nič nepridá.

Výstupy: `stop_loss` 65.5 %, `take_profit` 30.6 %, `session_end` 3.9 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0054 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Vzdialenosť stopu** (riadi `slBufferAtr`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 0.2437 % | 213 | 25.0 % | 29.1 | -0.0465 | 0.0023 | +0.0054 |
| 0.0859 % – 0.14 % | 213 | 25.0 % | 28.2 | -0.0092 | -0.0013 | +0.0018 |
| do 0.0859 % | 214 | 25.1 % | 36.5 | 0.0016 | -0.0084 | -0.0053 |
| 0.14 % – 0.2437 % | 213 | 25.0 % | 41.3 | 0.0232 | -0.0073 | -0.0042 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 9 | 239 | 28.0 % | 30.1 | -0.0133 | 0.0005 | +0.0036 |
| 9 – 17 | 221 | 25.9 % | 30.8 | -0.0059 | -0.0022 | +0.0009 |
| nad 23 | 210 | 24.6 % | 36.7 | 0.0009 | -0.0045 | -0.0014 |
| 17 – 23 | 183 | 21.5 % | 38.8 | 0.0066 | -0.0061 | -0.0030 |

**Hodina vstupu (UTC)** (riadi `entryWindowMinutes`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 14 h | 280 | 32.8 % | 31.1 | -0.0127 | 0.0004 | +0.0035 |
| nad 16 h | 147 | 17.2 % | 34.7 | -0.0022 | -0.0033 | -0.0002 |
| 15 h – 16 h | 139 | 16.3 % | 34.5 | 0.0014 | -0.0041 | -0.0010 |
| 14 h – 15 h | 287 | 33.6 % | 35.5 | 0.0016 | -0.0053 | -0.0022 |

Parametre, ktorými sa dá s tým niečo spraviť: `closeAtSessionEnd`, `driftMinAtr`, `entryMode`, `entryWindowMinutes`, `rrRatio`, `slBufferAtr`, `slMode`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0072 % | 0.0000 % ± 0.0037 | -1.94 | 2.5 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0072 % | -0.0001 % ± 0.0041 | -1.74 | 3.9 |

HORSIE nez nahoda (-1.9 sigma). Nahodny vstup za tych istych pravidiel dava lepsi vysledok - vyber vstupu vysledku skodi.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 196 | 13.3 | 32.1 | -0.0068 | 28 |
| 2022-12 - 2024-03 | 209 | 14.2 | 34.0 | -0.0006 | 65 |
| 2024-03 - 2025-06 | 233 | 15.9 | 34.3 | -0.0061 | 28 |
| 2025-06 - 2026-09 | 215 | 14.6 | 34.4 | -0.0001 | 66 |

Hranice pre úsek veľkosti posledného obdobia: -0.0149 až +0.0071 % (medián -0.0028).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 66. percentile, teda v medziach -0.0149 až +0.0071 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 4** — 2021-12-08T17:25 až 2021-12-16T16:01, spolu +597.05, rovnako dlhých sérií 8.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2021-12-08T17:25 | 2021-12-08T17:44 | +139.48 | +0.21 | `take_profit` |
| 2 | 2021-12-13T20:05 | 2021-12-13T20:06 | +166.52 | +0.09 | `take_profit` |
| 3 | 2021-12-14T15:30 | 2021-12-14T15:43 | +129.79 | +0.41 | `take_profit` |
| 4 | 2021-12-16T15:35 | 2021-12-16T16:01 | +161.26 | +0.50 | `take_profit` |

**Straty za sebou: 18** — 2026-06-03T15:00 až 2026-07-14T14:34, spolu -2055.93.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-06-03T15:00 | 2026-06-03T15:22 | -72.80 | -0.12 | `stop_loss` |
| 2 | 2026-06-09T18:35 | 2026-06-09T18:58 | -140.63 | -0.24 | `stop_loss` |
| 3 | 2026-06-11T15:20 | 2026-06-11T15:37 | -170.61 | -0.30 | `stop_loss` |
| 4 | 2026-06-17T15:00 | 2026-06-17T15:18 | -192.28 | -0.32 | `stop_loss` |
| 5 | 2026-06-18T14:30 | 2026-06-18T14:30 | -81.29 | -0.13 | `stop_loss` |
| 6 | 2026-06-19T15:35 | 2026-06-19T15:36 | -112.84 | -0.03 | `stop_loss` |
| 7 | 2026-06-23T14:45 | 2026-06-23T14:46 | -62.72 | -0.10 | `stop_loss` |
| 8 | 2026-06-24T14:20 | 2026-06-24T14:27 | -270.70 | -0.46 | `stop_loss` |
| 9 | 2026-06-25T16:45 | 2026-06-25T16:45 | -73.19 | -0.12 | `stop_loss` |
| 10 | 2026-07-01T14:35 | 2026-07-01T14:36 | -67.26 | -0.11 | `stop_loss` |
| 11 | 2026-07-03T14:20 | 2026-07-05T22:00 | -65.73 | -0.11 | `stop_loss` |
| 12 | 2026-07-06T15:15 | 2026-07-06T15:17 | -78.73 | -0.13 | `stop_loss` |
| 13 | 2026-07-07T18:50 | 2026-07-07T18:51 | -89.17 | -0.15 | `stop_loss` |
| 14 | 2026-07-08T15:00 | 2026-07-08T16:30 | -208.15 | -0.36 | `stop_loss` |
| 15 | 2026-07-09T14:45 | 2026-07-09T14:58 | -112.21 | -0.19 | `stop_loss` |
| 16 | 2026-07-10T15:15 | 2026-07-10T15:15 | -58.72 | -0.10 | `stop_loss` |
| 17 | 2026-07-13T14:45 | 2026-07-13T14:46 | -61.19 | -0.10 | `stop_loss` |
| 18 | 2026-07-14T14:30 | 2026-07-14T14:34 | -137.70 | -0.23 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0031 %**, medián -0.0031 %, 90 % interval -0.0084–0.0020 %
- P(edge > poplatok) = **3.1 %**
- max drawdown: medián 90.0 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 15, 95. percentil 22 obchodov
- pravdepodobnosť ruiny účtu: 39.5 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **13** na obchod pri účte 10 000

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

Chýba. Napíše ho AI: prečíta čísla vyššie a odpovie na týchto šesť otázok. Text patrí **medzi značky** nižšie, aby ho ďalší `cli checkup` preniesol ďalej.

1. **Na čo sa to hodí a na čo nie** — trh, timeframe, režim, veľkosť účtu; kde by to isté číslo znamenalo niečo iné.
2. **Má to potenciál?** Čo z čísel hovorí, že za tým je skutočný jav, a čo hovorí, že je to vlastnosť vzorky.
3. **Čo treba dorobiť** v samotnej stratégii — filtre, výstupy, sizing, sviatky a seansy, chýbajúce parametre.
4. **Čo otestovať ďalej** — konkrétne príkazy (`cli sweep`, `cli matrix`, `cli hyperopt`, druhý engine) a čo by ich výsledok rozhodol.
5. **Je to použiteľné, alebo je to o ničom?** Odpoveď má byť jednoznačná; „ešte uvidíme" je odpoveď len vtedy, keď je za ňou konkrétny test.
6. **Čo by som pridal** — nápad, ktorý v stratégii nie je a z týchto čísel dáva zmysel.
<!-- POSUDOK cisla=e0004e15 -->

**1. Na čo sa to hodí a na čo nie.** Meraná je stratégia z videa IQCapital tak, ako ju autor
povedal: MNQ 5m, VWAP od 9:30 NY z 15m sviečok, prvý pullback v smere driftu. Video
neuvádza stop ani cieľ, takže vstup `close`, stop za pullback a RR 2 sú náš odhad, nie
predloha. V tejto podobe sa nehodí nikam. Zisková je v 1 z 5 rokov (2025/26, +3,4 %),
break-even −0,0031 % je pod poplatkom 0,0027 % a pravdepodobnosť ruiny je 39,5 %.
Stratégia potrebuje skutočný objem burzy. Na CME futures (Databento) VWAP sedí, na
Dukascopy NAS100 je v objeme len aktivita tickov a to isté číslo by znamenalo niečo iné.
Tvrdenie „93,6 % šanca prejsť challenge" z nadpisu videa tieto dáta nepodopierajú.

**2. Má to potenciál?** Skôr nie. Za skutočný jav hovorí len stabilita signálu: 13–16
obchodov za mesiac v každom období, nezávisle od režimu trhu. Proti hovorí všetko
podstatné. Náhodný vstup za tých istých pravidiel je lepší (−1,9 sigma), edge je nad
poplatkom len v 3 % bootstrap vzoriek a „slabne edge" ukazuje DRŽÍ na zápornej úrovni.
Matica šiestich druhov vstupu a štyroch druhov stopu to nezmenila. Na roku 2025/26 bolo
niekoľko verzií výrazne v zisku (`reaction` + `swing` +26,7 %, PF 1,23; `limit` + `vwap`
+22,4 %). Na piatich oknách je však `reaction` + `swing` zisková v 1 z 5 (break-even
−0,0076 %) a `limit` + `vwap` v 2 z 5 (break-even +0,0012 %, stále pod poplatkom). Dobrý
posledný rok je vlastnosť vzorky, nie stratégie.

**3. Čo treba dorobiť.** (a) **Skrátené dni a sviatky:** 3. 7. 2026 (skrátený deň) nebol
po 15:55 žiadny bar a pozícia prežila víkend až do nedeľnej 22:00 UTC. Treba zatvárať aj
na prvom bare nového dňa, prípadne mať kalendár skrátených seáns (týka sa to aj
`breakout` a `orb`). (b) **Stop:** 65 % obchodov končí na stope a medián držania je 2,4 baru.
Stop za pullback je na 5m príliš tesný a najviac škodia obchody s najväčšou vzdialenosťou
stopu (> 0,24 %). (c) **Filter typu dňa:** protitrendový vstup (−0,68 ATR za 5 barov) v silnom
trende dostáva rany. Drift VWAP zatiaľ meria len smer, nie to, či je deň trendový alebo
rotačný.

**4. Čo otestovať ďalej.** `cli sweep --strategy vwapdrift --set entryMode=limit --set
slMode=vwap` cez `rrRatio` 0,75–3 a `awayAtr` 0–3 **len na jednom okne**, potom
víťaza bez zmeny na ostatných štyroch. Rozhodne to, či existuje nastavenie ziskové aspoň
v 4 z 5 rokov. Druhý beh: `--set vwapAnchor=session` (klasický VWAP od 18:00) proti
`ny_open`, lebo tieto dve kotvy dávajú v ten istý deň desiatky bodov rozdiel. Druhý engine
(Freqtrade) tu nemá zmysel, MNQ ide len cez emulátor MultiCharts.

**5. Je to použiteľné, alebo je to o ničom?** V tejto podobe **o ničom**: horšie než
náhoda, pod poplatkom a zisková v jednom roku z piatich. Stratégiu nechávam v registry
ako meranie videa a ako východisko pre test bodu 4. Keď ani ten nenájde nastavenie
ziskové v 4 z 5 okien, treba ju uzavrieť. Použiteľný je samotný VWAP (`tradebot.core.vwap`),
ktorý overene sedí s nezávislým výpočtom na celej histórii MNQ 2019–2026.

**6. Čo by som pridal.** VWAP pásma (±1σ a ±2σ, štandardná odchýlka vážená objemom)
a pullback nie na samotný VWAP, ale do pásma medzi VWAP a −1σ. V trendový deň sa cena
k VWAP často vôbec nevráti a prvý dotyk je potom práve ten deň, keď sa trend láme. Druhý
nápad: obchodovať len dni, keď otvorenie leží mimo rozpätia predošlého dňa (gap/trend
day), a v rotačné dni sa stratégii vyhnúť.

<!-- POSUDOK KONIEC -->
