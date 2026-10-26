# Základná analytika — Trendlines — prerazenie trendovky (`trendlines`)

Zmerané 2026-10-26 na `MNQ/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/trendlines/configs/mnq_databento_5m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy trendlines \
   --profile tradebot/strategies/trendlines/configs/mnq_databento_5m.json \
   --pair MNQ/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 2564 obchodov spolu — na štatistiku dosť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 0 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20231001-20241001, 20240904-20250904, 20250904-20260904 v strate)
- break-even -0.0002 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 0 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 57.0 % (namerané 42.8 % medián) — na účet to treba mať
- proti náhode len +1.1 sigma: náznak, nie dôkaz
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 555 | -12.08 | -0.0020 | 13.8 | 36.9 | +5/-14 | `20261026-132117-7cf896` |
| 20221001-20231001 | 511 | -6.13 | 0.0003 | 8.5 | 40.7 | +10/-8 | `20261026-132123-86be08` |
| 20231001-20241001 | 528 | -11.79 | -0.0002 | 13.5 | 39.2 | +5/-9 | `20261026-132129-2db25d` |
| 20240904-20250904 | 510 | -4.26 | 0.0008 | 6.8 | 42.4 | +7/-10 | `20261026-132135-fcdc81` |
| 20250904-20260904 | 496 | -6.62 | 0.0000 | 8.3 | 39.9 | +6/-10 | `20261026-132141-2adc70` |

Zisková v **0 z 5** okien, obchodov spolu 2564, break-even celkom -0.0002 %. Okná sa prekrývajú, 36 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.52 ATR za 5 barov)
- medián držania 0.8 barov grafu
- winrate 39.66 %, payoff 1.271
- 1.43 obchodov za deň
- šikmosť výnosov +0.648

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 60.3 %, `take_profit` 39.7 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0005 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.6667 | 642 | 25.0 % | 36.6 | -0.0010 | 0.0003 | +0.0005 |
| 0.8566 – 0.944 | 642 | 25.0 % | 39.4 | -0.0006 | -0.0000 | +0.0002 |
| 0.6667 – 0.8566 | 641 | 25.0 % | 39.5 | -0.0001 | -0.0002 | +0.0000 |
| nad 0.944 | 639 | 24.9 % | 43.2 | 0.0021 | -0.0006 | -0.0004 |

**S trendom, alebo proti** (riadi `entryMode`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| proti trendu | 656 | 25.6 % | 36.1 | -0.0013 | 0.0003 | +0.0005 |
| s trendom | 1908 | 74.4 % | 40.9 | 0.0003 | -0.0013 | -0.0011 |

**Trend alebo rozsah** (riadi `lineSlope`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.0928 – 0.1564 | 641 | 25.0 % | 37.9 | -0.0012 | 0.0002 | +0.0004 |
| 0.0441 – 0.0928 | 641 | 25.0 % | 38.2 | -0.0006 | -0.0000 | +0.0002 |
| do 0.0441 | 642 | 25.0 % | 40.5 | 0.0003 | -0.0004 | -0.0002 |
| nad 0.1564 | 640 | 25.0 % | 42.0 | 0.0008 | -0.0005 | -0.0003 |

Parametre, ktorými sa dá s tým niečo spraviť: `entryMode`, `lineSlope`, `maxHoldBars`, `rrRatio`, `slBufferAtr`, `tradeDirection`, `tradeStartH`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0005 % | -0.0004 % ± 0.0008 | +1.12 | 86.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0005 % | -0.0004 % ± 0.0008 | +1.12 | 86.0 |

Naznak, ale nie dokaz (1.1 sigma, percentil 86.0). Take rozdiely nahoda robi bezne.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 671 | 45.5 | 36.8 | -0.0022 | 1 |
| 2022-12 - 2024-03 | 641 | 43.5 | 42.0 | 0.0008 | 87 |
| 2024-03 - 2025-06 | 633 | 42.9 | 39.0 | -0.0005 | 36 |
| 2025-06 - 2026-09 | 619 | 42.0 | 41.0 | 0.0005 | 80 |

Hranice pre úsek veľkosti posledného obdobia: -0.0016 až +0.0013 % (medián -0.0002).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 80. percentile, teda v medziach -0.0016 až +0.0013 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 10** — 2023-07-11T11:25 až 2023-07-14T18:32, spolu +1282.18.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-07-11T11:25 | 2023-07-11T11:35 | +125.38 | +0.05 | `take_profit` |
| 2 | 2023-07-11T13:15 | 2023-07-11T13:18 | +138.89 | +0.05 | `take_profit` |
| 3 | 2023-07-12T05:55 | 2023-07-12T05:56 | +108.32 | +0.01 | `take_profit` |
| 4 | 2023-07-12T07:35 | 2023-07-12T07:36 | +142.68 | +0.03 | `take_profit` |
| 5 | 2023-07-12T22:05 | 2023-07-13T02:29 | +137.74 | +0.15 | `take_profit` |
| 6 | 2023-07-13T05:00 | 2023-07-13T05:08 | +128.86 | +0.03 | `take_profit` |
| 7 | 2023-07-14T01:50 | 2023-07-14T02:17 | +138.57 | +0.05 | `take_profit` |
| 8 | 2023-07-14T09:40 | 2023-07-14T09:48 | +124.16 | +0.02 | `take_profit` |
| 9 | 2023-07-14T13:35 | 2023-07-14T14:03 | +122.39 | +0.39 | `take_profit` |
| 10 | 2023-07-14T18:25 | 2023-07-14T18:32 | +115.19 | +0.12 | `take_profit` |

**Straty za sebou: 14** — 2022-01-26T15:40 až 2022-02-02T19:38, spolu -1166.48.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-01-26T15:40 | 2022-01-26T15:40 | -94.53 | -0.11 | `stop_loss` |
| 2 | 2022-01-27T12:00 | 2022-01-27T12:22 | -70.50 | -0.25 | `stop_loss` |
| 3 | 2022-01-27T18:25 | 2022-01-27T18:35 | -78.48 | -0.28 | `stop_loss` |
| 4 | 2022-01-28T01:05 | 2022-01-28T01:15 | -64.49 | -0.23 | `stop_loss` |
| 5 | 2022-01-28T08:15 | 2022-01-28T09:15 | -89.99 | -0.32 | `stop_loss` |
| 6 | 2022-01-28T10:40 | 2022-01-28T10:42 | -54.98 | -0.20 | `stop_loss` |
| 7 | 2022-01-28T16:00 | 2022-01-28T16:00 | -85.98 | -0.15 | `stop_loss` |
| 8 | 2022-01-31T12:25 | 2022-01-31T12:34 | -102.04 | -0.12 | `stop_loss` |
| 9 | 2022-02-01T03:25 | 2022-02-01T03:28 | -97.72 | -0.07 | `stop_loss` |
| 10 | 2022-02-01T09:30 | 2022-02-01T10:07 | -67.05 | -0.23 | `stop_loss` |
| 11 | 2022-02-01T14:40 | 2022-02-01T14:40 | -100.17 | -0.08 | `stop_loss` |
| 12 | 2022-02-01T20:35 | 2022-02-01T20:38 | -77.10 | -0.13 | `stop_loss` |
| 13 | 2022-02-02T13:25 | 2022-02-02T13:36 | -90.27 | -0.07 | `stop_loss` |
| 14 | 2022-02-02T19:35 | 2022-02-02T19:38 | -93.18 | -0.10 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0002 %**, medián -0.0002 %, 90 % interval -0.0009–0.0005 %
- P(edge > poplatok) = **0.0 %**
- max drawdown: medián 42.8 %, 95. percentil 57.0 %, najhorší 81.7 %
- najdlhšia séria strát: medián 13, 95. percentil 18 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **35** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=3576e711 -->

_Posudok (Claude, 26. 10. 2026) — repo profil „mnq_databento_5m“, MNQ 5m. Na porovnanie som na tých istých piatich
oknách pustil dva ladené profily testera: `R1_trendlines_MNQ_182obch_WR67` (behy `20261026-132612-243ded` až
`-132639-d81e3f`) a `TL_1R_RR2_5_303obch_WR38` (`20261026-132646-988bd9` až `-132712-f433d4`)._

1. **Na čo sa to hodí a na čo nie.** MNQ 5m, 1,43 obchodu denne, medián držania 0,8 baru — o výsledku rozhoduje prvá
   sviečka po prerazení, teda exekúcia a sklz. Nehodí sa nikam, kde je sklz väčší než nula: break-even je okolo nuly
   už bez neho.
2. **Má to potenciál?** Nie. Repo profil: 0 z 5 okien, break-even −0,0002 % pri poplatku 0,0018 %, 0 % bootstrapu nad
   poplatkom, 95. percentil drawdownu 57 %. Ladené profily nie sú lepšie mimo roka, na ktorom vznikli:
   R1_MNQ_182 má PF po oknách 1,02 / 0,80 / 0,90 / 0,64 / 1,51 (zisk len v 2025/26, titulok sľubuje PF 2,18);
   TL_1R_RR2_5 („ziskové 5/5“) dáva dnes 2 z 5 (PF 1,30 / 0,76 / 0,90 / 0,86 / 1,25). Edge z ladenia je vlastnosť
   vybraného roka.
3. **Čo treba dorobiť.** Vstup na prerazenie čiary bez potvrdenia a stop tesne za ňou (`slBufferAtr`) robí obchody,
   ktoré skončia do jedného baru (SL/TP 60/40 %, payoff 1,27). Chýba minimálna vzdialenosť stopu a kvalita čiary
   (počet dotykov, dĺžka).
4. **Čo otestovať ďalej.** `cli sweep --strategy trendlines --profile mnq_databento_5m --pair MNQ/USD --timeframe 5m --space slBufferAtr=0.5:2:0.25 --space maxHoldBars=6:48:6`
   na piatich oknách s cieľom break_even — ak žiadny bod nedá 4 z 5, stratégiu odložiť.
5. **Je to použiteľné?** Nie — ani repo, ani ladené profily nedržia mimo roka, na ktorom vznikli.
6. **Čo by som pridal.** Vstup limitkou na retest prerazenej čiary namiesto trhu po prerazení: obchod dostane
   štruktúrny stop a nebude to súboj o jednu sviečku, v ktorom náklad zje všetko.

<!-- POSUDOK KONIEC -->
