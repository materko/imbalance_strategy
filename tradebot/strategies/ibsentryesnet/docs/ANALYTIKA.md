# Základná analytika — IBS EZ ES (C# jadro) (`ibsentryesnet`)

Zmerané 2026-10-26 na `ES/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/ibsentryesnet/configs/PRESIEL_SMERNICAMI_IBS_EZ_ES_1.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy ibsentryesnet \
   --profile tradebot/strategies/ibsentryesnet/configs/PRESIEL_SMERNICAMI_IBS_EZ_ES_1.json \
   --pair ES/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 588 obchodov spolu — na štatistiku dosť
- break-even 0.0070 % je nad poplatkom 0.0018 % (rezerva +0.0052 bodu)
- edge nad poplatkom v 99 % bootstrapových vzoriek
- drawdown drží: 95. percentil 11.0 %
- odlíšiteľná od náhody (+4.4 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-08 na 49. percentile toho, čo stratégia vyrobí sama od seba)
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 174 | +9.02 | 0.0077 | 4.0 | 73.6 | +16/-5 | `20261026-083503-6308f3` |
| 20221001-20231001 | 141 | +5.55 | 0.0061 | 5.1 | 71.6 | +12/-4 | `20261026-083518-d7cc4e` |
| 20231001-20241001 | 102 | +0.63 | 0.0024 | 3.9 | 71.6 | +15/-3 | `20261026-083533-da5176` |
| 20240904-20250904 | 108 | +10.37 | 0.0116 | 3.5 | 75.9 | +10/-3 | `20261026-083548-f178e5` |
| 20250904-20260904 | 63 | +3.22 | 0.0061 | 2.9 | 73.0 | +9/-3 | `20261026-083603-44e9d7` |

Zisková v **5 z 5** okien, obchodov spolu 588, break-even celkom 0.0070 %.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+0.53 ATR za 5 barov)
- medián držania 1.3 barov grafu
- winrate 73.13 %, payoff 0.468
- 0.33 obchodov za deň
- šikmosť výnosov -0.502

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 73.1 %, `stop_loss` 26.9 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0097 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Plánovaný RR** (riadi `rrRatio`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.5 R | 527 | 89.6 % | 72.7 | 0.0057 | 0.0167 | +0.0097 |
| nad 0.5 R | 61 | 10.4 % | 77.0 | 0.0167 | 0.0057 | -0.0013 |

**Hodina vstupu (UTC)** (riadi `sess2TradeStartH`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 16 h | 198 | 33.7 % | 69.2 | 0.0027 | 0.0092 | +0.0022 |
| 16 h – 18 h | 196 | 33.3 % | 74.0 | 0.0073 | 0.0068 | -0.0002 |
| 18 h – 19 h | 113 | 19.2 % | 77.0 | 0.0109 | 0.0061 | -0.0009 |
| nad 19 h | 81 | 13.8 % | 75.3 | 0.0116 | 0.0062 | -0.0008 |

**Smer** (riadi `tradeDirection`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| long | 329 | 56.0 % | 72.0 | 0.0058 | 0.0086 | +0.0016 |
| short | 259 | 44.0 % | 74.5 | 0.0086 | 0.0058 | -0.0012 |

Parametre, ktorými sa dá s tým niečo spraviť: `closeAtSessionEnd`, `minSlDistance`, `rrRatio`, `sess2TradeStartH`, `state2MaxBars`, `tradeDirection`, `useStructureFilter`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0070 % | 0.0000 % ± 0.0016 | +4.42 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0070 % | -0.0001 % ± 0.0017 | +4.28 | 100.0 |

Edge je odlisitelny od nahody (4.4 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 225 | 15.3 | 72.0 | 0.0064 | 46 |
| 2022-12 - 2024-03 | 133 | 9.1 | 72.2 | 0.0043 | 27 |
| 2024-03 - 2025-06 | 151 | 10.3 | 75.5 | 0.0101 | 78 |
| 2025-06 - 2026-08 | 79 | 5.4 | 73.4 | 0.0069 | 49 |

Hranice pre úsek veľkosti posledného obdobia: -0.0028 až +0.0163 % (medián 0.0070).

**DRZI** — posledné obdobie (2025-06 - 2026-08) je na 49. percentile, teda v medziach -0.0028 až +0.0163 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je. Signálov pritom ubudlo: z 15.32 na 5.38 obchodov za mesiac. To je úpadok tiež, len v break-evene ho vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 20** — 2024-07-26T18:04 až 2024-09-06T16:19, spolu +3350.82.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-07-26T18:04 | 2024-07-26T18:11 | +190.33 | +0.07 | `take_profit` |
| 2 | 2024-07-26T19:41 | 2024-07-26T19:42 | +215.36 | +0.08 | `take_profit` |
| 3 | 2024-07-26T19:57 | 2024-07-26T19:57 | +177.86 | +0.06 | `take_profit` |
| 4 | 2024-07-30T22:09 | 2024-07-30T22:09 | +121.65 | +0.04 | `take_profit` |
| 5 | 2024-08-01T19:15 | 2024-08-01T19:15 | +115.43 | +0.04 | `take_profit` |
| 6 | 2024-08-08T17:09 | 2024-08-08T17:09 | +171.92 | +0.06 | `take_profit` |
| 7 | 2024-08-12T17:27 | 2024-08-12T17:44 | +209.33 | +0.08 | `take_profit` |
| 8 | 2024-08-23T19:48 | 2024-08-23T19:48 | +127.59 | +0.05 | `take_profit` |
| 9 | 2024-08-28T19:35 | 2024-08-28T19:45 | +196.40 | +0.07 | `take_profit` |
| 10 | 2024-09-03T17:38 | 2024-09-03T17:43 | +171.47 | +0.06 | `take_profit` |
| 11 | 2024-09-04T18:36 | 2024-09-04T18:37 | +184.05 | +0.07 | `take_profit` |
| 12 | 2024-09-04T18:36 | 2024-09-04T18:37 | +184.05 | +0.07 | `take_profit` |
| 13 | 2024-09-04T19:54 | 2024-09-04T19:54 | +165.29 | +0.06 | `take_profit` |
| 14 | 2024-09-04T19:54 | 2024-09-04T19:54 | +165.29 | +0.06 | `take_profit` |
| 15 | 2024-09-05T17:00 | 2024-09-05T17:05 | +134.09 | +0.05 | `take_profit` |
| 16 | 2024-09-05T17:00 | 2024-09-05T17:05 | +134.09 | +0.05 | `take_profit` |
| 17 | 2024-09-05T20:18 | 2024-09-05T20:24 | +196.58 | +0.07 | `take_profit` |
| 18 | 2024-09-05T20:18 | 2024-09-05T20:24 | +196.58 | +0.07 | `take_profit` |
| 19 | 2024-09-06T16:09 | 2024-09-06T16:19 | +146.74 | +0.05 | `take_profit` |
| 20 | 2024-09-06T16:09 | 2024-09-06T16:19 | +146.74 | +0.05 | `take_profit` |

**Straty za sebou: 5** — 2021-10-01T15:12 až 2021-10-04T19:51, spolu -2125.08.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2021-10-01T15:12 | 2021-10-01T15:13 | -495.04 | -0.23 | `stop_loss` |
| 2 | 2021-10-04T15:27 | 2021-10-04T15:32 | -432.51 | -0.20 | `stop_loss` |
| 3 | 2021-10-04T16:59 | 2021-10-04T17:03 | -345.00 | -0.16 | `stop_loss` |
| 4 | 2021-10-04T17:30 | 2021-10-04T18:00 | -382.51 | -0.18 | `stop_loss` |
| 5 | 2021-10-04T19:50 | 2021-10-04T19:51 | -470.02 | -0.22 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0070 %**, medián 0.0070 %, 90 % interval 0.0036–0.0103 %
- P(edge > poplatok) = **99.4 %**
- max drawdown: medián 6.0 %, 95. percentil 11.0 %, najhorší 23.1 %
- najdlhšia séria strát: medián 6, 95. percentil 8 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **1 461** na obchod pri účte 60 000

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

> **Posudok je starší než čísla** (písal sa k vzorke `8afca62b`, tu je `71738d76`). Nech ho AI prepíše — čísla nižšie sa medzitým zmenili.

<!-- POSUDOK cisla=8afca62b -->

**C# jadro, riziko 500 $ na ES.** Logika je bar po bare zhodná s Python predlohou `ibsentryes` (`tester/tests/test_csharp_parity_es.py`). **Pozor na veľkosť:** ES má 50 $ za bod a strop straty (obal `entry_sizing`, od 26. 10. platí vždy pri počte z rizika) vynechá obchod, pri ktorom by aj 1 kontrakt na stope stratil viac než 500 $ — preto je tu 588 obchodov namiesto 824 pri riziku 1000 $ (posledný rok 63 namiesto 126).

**1. Na čo sa to hodí a na čo nie.** Na S&P 500 futures, 3m, skalp s cieľom ~0,5 R, WR 72–76 %. Pri riziku 500 $ patrí na **MES** (5 $ za bod), kde sa vstúpi takmer vždy; na ES s 500 $ prídeš o tretinu obchodov a o väčšinu zisku (rok 23/24 len +0,6 %).

**2. Má to potenciál?** Áno: zisk v 5 z 5 okien aj s vynechanými obchodmi, +4,4 sigma proti náhode, edge nad poplatkom v 99 % vzoriek, posledné obdobie na 49. percentile. Pri riziku 1000 $ (všetky obchody) bolo 5 z 5 rokov s PnL +14 až +33 % a +7,5 sigma.

**3. Čo treba dorobiť.** Nástroj MES do zoznamu nástrojov (ten istý cenový rad ako ES, bod 5 $), aby sa backtest dal počítať presne tak, ako sa bude obchodovať pri 500 $.

**4. Čo otestovať ďalej.** Backtest na MES s rizikom 500 $ (po pridaní nástroja); natívny hyperopt s oknami a plató; forward test na MES.

**5. Je to použiteľné, alebo je to o ničom?** **Použiteľné** — na MES s rizikom 500 $ alebo na ES s rizikom aspoň ~1000 $. Na ES s 500 $ nie, lebo vynechá najlepšie obchody s dlhším stopom.

**6. Čo by som pridal.** Potvrdenie smeru z NQ (prieraz ES len keď NQ ide tým istým smerom).

<!-- POSUDOK KONIEC -->
