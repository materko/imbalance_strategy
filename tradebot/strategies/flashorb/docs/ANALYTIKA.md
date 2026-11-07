# Základná analytika — FLASH TRIGGER ORB 1.0 (`flashorb`)

Zmerané 2026-11-06 na `MNQ/USD` 1h, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/flashorb_PRESIEL_SMERNICAMI_FLASH_ORB_MNQ_1_2026-11-06.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy flashorb \
   --profile .nightsearch/checkup/flashorb_PRESIEL_SMERNICAMI_FLASH_ORB_MNQ_1_2026-11-06.json \
   --pair MNQ/USD \
   --timeframe 1h \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 795 obchodov spolu — na štatistiku dosť
- break-even 0.0745 % je nad poplatkom 0.0018 % (rezerva +0.0727 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 11.2 %
- odlíšiteľná od náhody (+3.7 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 26. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'žiadna' vlastnosti 'Makro udalosť v ten deň': 674 obchodov (84.8 %), bez nej by break-even bol o +0.0949 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 174 | +7.96 | 0.0510 | 5.3 | 50.6 | +6/-8 | `20261106-051513-38e767` |
| 20221001-20231001 | 157 | +6.56 | 0.0494 | 4.2 | 54.8 | +5/-5 | `20261106-051516-b2550f` |
| 20231001-20241001 | 163 | +20.61 | 0.1071 | 2.5 | 61.4 | +7/-7 | `20261106-051519-9b384d` |
| 20240904-20250904 | 138 | +17.08 | 0.0891 | 5.5 | 55.8 | +6/-5 | `20261106-051522-c1f5e9` |
| 20250904-20260904 | 172 | +18.05 | 0.0609 | 6.9 | 55.8 | +9/-5 | `20261106-051525-c0738e` |

Zisková v **5 z 5** okien, obchodov spolu 795, break-even celkom 0.0745 %. Okná sa prekrývajú, 9 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.43 ATR za 5 barov)
- medián držania 9.7 barov grafu
- winrate 55.85 %, payoff 1.074
- 0.44 obchodov za deň
- šikmosť výnosov +0.562

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 55.6 %, `stop_loss` 43.9 %, `force_exit` 0.5 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'žiadna' vlastnosti 'Makro udalosť v ten deň': 674 obchodov (84.8 %), break-even 0.0575 % oproti 0.0745 % celku. Bez nej by break-even bol 0.1694 % (+0.0949). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| žiadna | 674 | 84.8 % | 54.8 | 0.0575 | 0.1694 | +0.0949 |
| FOMC | 35 | 4.4 % | 60.0 | 0.1106 | 0.0728 | -0.0017 |
| NFP | 39 | 4.9 % | 59.0 | 0.1526 | 0.0705 | -0.0040 |
| CPI | 46 | 5.8 % | 65.2 | 0.2244 | 0.0654 | -0.0091 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| pred vyhlásením | 24 | 3.0 % | 58.3 | 0.0247 | 0.0761 | +0.0016 |
| bez udalosti | 674 | 84.8 % | 54.8 | 0.0575 | 0.1694 | +0.0949 |
| po vyhlásení | 97 | 12.2 % | 62.9 | 0.2069 | 0.0564 | -0.0181 |

**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| proti trendu | 248 | 31.2 % | 51.6 | 0.0150 | 0.1013 | +0.0268 |
| s trendom | 547 | 68.8 % | 57.8 | 0.1013 | 0.0150 | -0.0595 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0745 % | 0.0003 % ± 0.0198 | +3.74 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0745 % | 0.0008 % ± 0.0187 | +3.94 | 100.0 |

Edge je odlisitelny od nahody (3.7 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 213 | 14.4 | 50.7 | 0.0513 | 31 |
| 2022-12 - 2024-03 | 192 | 13.0 | 57.8 | 0.0665 | 44 |
| 2024-03 - 2025-06 | 188 | 12.8 | 60.6 | 0.1365 | 92 |
| 2025-06 - 2026-09 | 202 | 13.7 | 55.0 | 0.0470 | 26 |

Hranice pre úsek veľkosti posledného obdobia: +0.0088 až +0.1394 % (medián 0.0707).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 26. percentile, teda v medziach +0.0088 až +0.1394 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 9** — 2025-09-11T15:00 až 2025-09-29T06:37, spolu +2391.49.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-09-11T15:00 | 2025-09-12T14:51 | +187.81 | +0.39 | `take_profit` |
| 2 | 2025-09-12T15:00 | 2025-09-15T13:32 | +205.80 | +0.43 | `take_profit` |
| 3 | 2025-09-16T16:00 | 2025-09-17T15:05 | +199.28 | +0.41 | `take_profit` |
| 4 | 2025-09-17T16:00 | 2025-09-17T18:45 | +256.29 | +0.53 | `take_profit` |
| 5 | 2025-09-18T15:00 | 2025-09-19T19:50 | +268.26 | +0.54 | `take_profit` |
| 6 | 2025-09-19T20:00 | 2025-09-22T16:35 | +249.75 | +0.50 | `take_profit` |
| 7 | 2025-09-23T17:00 | 2025-09-23T17:36 | +164.25 | +0.33 | `take_profit` |
| 8 | 2025-09-24T16:00 | 2025-09-25T13:40 | +437.28 | +0.89 | `take_profit` |
| 9 | 2025-09-25T15:00 | 2025-09-29T06:37 | +422.76 | +0.86 | `take_profit` |

**Straty za sebou: 8** — 2021-11-17T15:00 až 2021-11-30T15:48, spolu -1046.68.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2021-11-17T15:00 | 2021-11-17T15:11 | -67.64 | -0.21 | `stop_loss` |
| 2 | 2021-11-18T16:00 | 2021-11-18T16:33 | -94.15 | -0.29 | `stop_loss` |
| 3 | 2021-11-19T15:00 | 2021-11-19T18:39 | -143.66 | -0.43 | `stop_loss` |
| 4 | 2021-11-23T15:00 | 2021-11-23T15:06 | -137.65 | -0.42 | `stop_loss` |
| 5 | 2021-11-24T15:00 | 2021-11-24T16:12 | -190.14 | -0.59 | `stop_loss` |
| 6 | 2021-11-25T15:00 | 2021-11-25T23:30 | -65.15 | -0.20 | `stop_loss` |
| 7 | 2021-11-26T15:00 | 2021-11-26T15:03 | -108.64 | -0.33 | `stop_loss` |
| 8 | 2021-11-30T15:00 | 2021-11-30T15:48 | -239.65 | -0.73 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0745 %**, medián 0.0739 %, 90 % interval 0.0415–0.1074 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 6.3 %, 95. percentil 11.2 %, najhorší 25.6 %
- najdlhšia séria strát: medián 7, 95. percentil 10 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

> **Posudok je starší než čísla** (písal sa k vzorke `8a664b9d`, tu je `f31cb059`). Nech ho AI prepíše — čísla nižšie sa medzitým zmenili.

<!-- POSUDOK cisla=8a664b9d -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na MNQ, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Prieraz jednej sviečky (14:30 UTC = otvorenie NY v zime, v lete o hodinu neskôr — predloha posun nerieši); index futures, nie zlato.
2. **Má potenciál?** Zisková v 4 z 5 okien, 798 obchodov (~160 za rok), break-even 0.0428 % (nad poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 29.32 % pri payoffe 2.866. Odložený rok 25/26: +34.41 % PnL, break-even 0.0213 %. Jav je skôr skutočný ako vlastnosť vzorky.
3. **Čo dorobiť.** Čas sviečky v New Yorku namiesto pevného UTC (letný čas posúva sviečku o hodinu), koniec dňa, ktorý na 15m grafe naozaj nastane (predloha 23:59 na 15m nikdy).
4. **Čo otestovať ďalej.** Smernica (`flashorb*`: hodina a minúta sviečky, RR 0,5–3, TF, trend, typ vstupu); rozhodne, či RR 3 s WR ~29 % drží aj s plató.
5. **Použiteľné?** **Áno ako kandidát do smernice** — defaulty predlohy sú ziskové vo väčšine okien a edge je nad poplatkom; rozhodne hľadanie a odložený rok.
6. **Čo by som pridal.** Sviečku vyberať podľa NY času otvorenia (9:30 / 9:45) a cieľ menší ako 3 R — vyšší WR, menej dní bez zisku.

<!-- POSUDOK KONIEC -->
