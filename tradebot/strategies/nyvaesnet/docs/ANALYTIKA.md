# Základná analytika — NY VA BREAKOUT ES (C# jadro) (`nyvaesnet`)

Zmerané 2026-10-26 na `ES/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/nyvaesnet/configs/PRESIEL_SMERNICAMI_NY_VA_BREAKOUT_ES_1.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy nyvaesnet \
   --profile tradebot/strategies/nyvaesnet/configs/PRESIEL_SMERNICAMI_NY_VA_BREAKOUT_ES_1.json \
   --pair ES/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 478 obchodov spolu — na štatistiku dosť
- break-even 0.0045 % je nad poplatkom 0.0018 % (rezerva +0.0027 bodu)
- drawdown drží: 95. percentil 12.5 %
- odlíšiteľná od náhody (+4.3 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 54. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- zisková v 4 z 5 referenčných okien (20240904-20250904 v strate)
- edge nad poplatkom len v 94 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'bežný deň' vlastnosti 'Sviatok na burze v USA': 455 obchodov (95.2 %), bez nej by break-even bol o +0.0109 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 117 | +9.14 | 0.0101 | 2.1 | 76.1 | +9/-2 | `20261026-083629-48a721` |
| 20221001-20231001 | 107 | +5.15 | 0.0068 | 2.7 | 73.8 | +10/-3 | `20261026-083635-9ec863` |
| 20231001-20241001 | 70 | +0.36 | 0.0021 | 5.0 | 68.6 | +9/-2 | `20261026-083641-e3b917` |
| 20240904-20250904 | 94 | -6.71 | -0.0036 | 8.0 | 59.6 | +8/-6 | `20261026-083647-dc4ac4` |
| 20250904-20260904 | 97 | +7.87 | 0.0070 | 2.8 | 78.3 | +29/-2 | `20261026-083653-b84343` |

Zisková v **4 z 5** okien, obchodov spolu 478, break-even celkom 0.0045 %. Okná sa prekrývajú, 7 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+0.65 ATR za 5 barov)
- medián držania 1 barov grafu
- winrate 71.97 %, payoff 0.459
- 0.27 obchodov za deň
- šikmosť výnosov -1.088

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 72 %, `stop_loss` 28 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'bežný deň' vlastnosti 'Sviatok na burze v USA': 455 obchodov (95.2 %), break-even 0.004 % oproti 0.0045 % celku. Bez nej by break-even bol 0.0154 % (+0.0109). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bežný deň | 455 | 95.2 % | 71.2 | 0.0040 | 0.0154 | +0.0109 |
| deň po sviatku | 14 | 2.9 % | 85.7 | 0.0162 | 0.0042 | -0.0003 |

**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.0926 % | 120 | 25.1 % | 65.8 | 0.0004 | 0.0076 | +0.0031 |
| 0.0926 % – 0.1247 % | 120 | 25.1 % | 71.7 | 0.0038 | 0.0047 | +0.0002 |
| 0.1247 % – 0.1654 % | 119 | 24.9 % | 74.8 | 0.0080 | 0.0037 | -0.0008 |
| nad 0.1654 % | 119 | 24.9 % | 75.6 | 0.0133 | 0.0030 | -0.0015 |

**Smer**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| short | 230 | 48.1 % | 68.3 | 0.0013 | 0.0075 | +0.0030 |
| long | 248 | 51.9 % | 75.4 | 0.0075 | 0.0013 | -0.0032 |

Parametre, ktorými sa dá s tým niečo spraviť: `entryEndH`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0057 % | -0.0002 % ± 0.0014 | +4.27 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0057 % | -0.0002 % ± 0.0017 | +3.48 | 99.9 |

Edge je odlisitelny od nahody (4.3 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 158 | 10.7 | 75.3 | 0.0088 | 90 |
| 2022-12 - 2024-03 | 90 | 6.1 | 71.1 | 0.0040 | 44 |
| 2024-03 - 2025-06 | 113 | 7.7 | 66.4 | 0.0004 | 12 |
| 2025-06 - 2026-09 | 117 | 7.9 | 73.5 | 0.0048 | 54 |

Hranice pre úsek veľkosti posledného obdobia: -0.0018 až +0.0105 % (medián 0.0044).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 54. percentile, teda v medziach -0.0018 až +0.0105 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 29** — 2026-03-27T14:39 až 2026-07-14T14:34, spolu +5038.86.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-03-27T14:39 | 2026-03-27T14:40 | +151.17 | +0.05 | `take_profit` |
| 2 | 2026-03-27T16:12 | 2026-03-27T16:25 | +151.17 | +0.05 | `take_profit` |
| 3 | 2026-04-01T14:42 | 2026-04-01T14:43 | +250.88 | +0.08 | `take_profit` |
| 4 | 2026-04-01T18:36 | 2026-04-01T18:37 | +113.41 | +0.03 | `take_profit` |
| 5 | 2026-04-08T16:53 | 2026-04-08T17:01 | +225.52 | +0.07 | `take_profit` |
| 6 | 2026-04-13T14:46 | 2026-04-13T14:57 | +187.96 | +0.05 | `take_profit` |
| 7 | 2026-04-15T14:39 | 2026-04-15T14:41 | +187.67 | +0.05 | `take_profit` |
| 8 | 2026-05-04T14:59 | 2026-05-04T15:00 | +112.26 | +0.03 | `take_profit` |
| 9 | 2026-05-08T16:28 | 2026-05-08T18:00 | +211.97 | +0.06 | `take_profit` |
| 10 | 2026-05-11T14:56 | 2026-05-11T15:29 | +224.44 | +0.06 | `take_profit` |
| 11 | 2026-05-12T14:42 | 2026-05-12T14:44 | +124.52 | +0.03 | `take_profit` |
| 12 | 2026-05-12T18:57 | 2026-05-12T19:11 | +211.99 | +0.06 | `take_profit` |
| 13 | 2026-05-13T14:39 | 2026-05-13T14:41 | +149.47 | +0.04 | `take_profit` |
| 14 | 2026-05-21T15:09 | 2026-05-21T15:10 | +173.99 | +0.02 | `take_profit` |
| 15 | 2026-05-26T14:38 | 2026-05-26T14:40 | +173.49 | +0.02 | `take_profit` |
| 16 | 2026-05-27T14:33 | 2026-05-27T14:34 | +174.28 | +0.05 | `take_profit` |
| 17 | 2026-05-27T16:33 | 2026-05-27T17:01 | +174.28 | +0.05 | `take_profit` |
| 18 | 2026-06-04T14:36 | 2026-06-04T14:40 | +224.22 | +0.06 | `take_profit` |
| 19 | 2026-06-05T15:12 | 2026-06-05T15:14 | +174.32 | +0.05 | `take_profit` |
| 20 | 2026-06-08T17:50 | 2026-06-08T17:51 | +149.45 | +0.04 | `take_profit` |
| 21 | 2026-06-17T14:39 | 2026-06-17T14:40 | +211.69 | +0.06 | `take_profit` |
| 22 | 2026-06-17T15:42 | 2026-06-17T17:00 | +211.69 | +0.06 | `take_profit` |
| 23 | 2026-06-24T14:33 | 2026-06-24T14:34 | +161.90 | +0.04 | `take_profit` |
| 24 | 2026-07-06T14:41 | 2026-07-06T14:43 | +198.42 | +0.03 | `take_profit` |
| 25 | 2026-07-08T14:33 | 2026-07-08T14:35 | +124.32 | +0.03 | `take_profit` |
| 26 | 2026-07-08T18:30 | 2026-07-08T18:36 | +149.30 | +0.04 | `take_profit` |
| 27 | 2026-07-09T15:18 | 2026-07-09T15:20 | +136.72 | +0.04 | `take_profit` |
| 28 | 2026-07-13T14:49 | 2026-07-13T14:51 | +161.67 | +0.04 | `take_profit` |
| 29 | 2026-07-14T14:33 | 2026-07-14T14:34 | +136.69 | +0.04 | `take_profit` |

**Straty za sebou: 6** — 2025-05-07T14:33 až 2025-05-22T14:41, spolu -2358.91.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-05-07T14:33 | 2025-05-07T14:49 | -322.42 | -0.11 | `stop_loss` |
| 2 | 2025-05-08T15:07 | 2025-05-08T15:14 | -409.96 | -0.14 | `stop_loss` |
| 3 | 2025-05-12T14:40 | 2025-05-12T14:44 | -397.72 | -0.14 | `stop_loss` |
| 4 | 2025-05-14T15:09 | 2025-05-14T15:20 | -422.86 | -0.14 | `stop_loss` |
| 5 | 2025-05-21T14:49 | 2025-05-21T14:55 | -385.40 | -0.13 | `stop_loss` |
| 6 | 2025-05-22T14:39 | 2025-05-22T14:41 | -420.55 | -0.07 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0045 %**, medián 0.0045 %, 90 % interval 0.0015–0.0074 %
- P(edge > poplatok) = **93.7 %**
- max drawdown: medián 6.4 %, 95. percentil 12.5 %, najhorší 23.6 %
- najdlhšia séria strát: medián 5, 95. percentil 7 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **1 074** na obchod pri účte 60 000

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

<!-- POSUDOK cisla=bbfe2f77 -->

**C# jadro, riziko 500 $ na ES.** Logika je bar po bare zhodná s Python predlohou `nyvaes` na všetkých piatich profiloch (`tester/tests/test_csharp_parity_es.py`). **Pozor na veľkosť:** ES má 50 $ za bod a strop straty (obal `entry_sizing`) vynechá obchod, pri ktorom by 1 kontrakt na stope stratil viac než 500 $ — preto 478 obchodov namiesto 775 a rok 24/25 v strate (−6,7 %); s plným počtom obchodov bolo 5 z 5 rokov v zisku.

**1. Na čo sa to hodí a na čo nie.** Prieraz z value area prvej hodiny NY na S&P 500 futures, 3m, jeden obchod denne, WR 60–78 %. Pri riziku 500 $ patrí na **MES** (5 $ za bod); na ES s 500 $ v tomto tvare nie. Na CFD US500 neprešiel krokom 8.

**2. Má to potenciál?** S plným počtom obchodov áno (`nyvaes`: 5 z 5 rokov, break-even 0,0115 %, +8,0 sigma). S vynechanými ES obchodmi už len 4 z 5 rokov, break-even 0,0045 % (rezerva 0,0027 % nad poplatkom), +4,3 sigma (+3,5 v tých istých hodinách) a edge nad poplatkom v 94 % vzoriek — výber vstupov podľa veľkosti stopu kazí výsledok, lebo vynecháva práve široké, ale ziskové prierazy (skupina so stopom nad 0,165 % má break-even 0,0133 %, najužšia 0,0004 %). Šikmosť výnosov je záporná (−1,1), séria strát do 6 (95. percentil 7), drawdown v 95 % ciest 12,5 %. Posledné obdobie je na 54. percentile, úsek 2024-03 – 2025-06 na 12. — úpadok to nie je, ale rok 24/25 je slabý aj bez stropu (WR 59,6 %).

**3. Čo treba dorobiť.** Nástroj MES (bod 5 $) do zoznamu nástrojov a analytiku na ňom s rizikom 500 $.

**4. Čo otestovať ďalej.** Backtest na MES s 500 $; natívny hyperopt s oknami a plató; forward test na MES.

**5. Je to použiteľné, alebo je to o ničom?** **Použiteľné len na MES** (alebo na ES s vyšším rizikom); **na ES s rizikom 500 $ nie**.

**6. Čo by som pridal.** Cieľ na high / low prvej hodiny, keď je bližšie ako RR — skráti držanie.

<!-- POSUDOK KONIEC -->
