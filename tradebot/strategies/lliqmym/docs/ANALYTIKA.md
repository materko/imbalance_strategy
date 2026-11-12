# Základná analytika — LONDON LIQUIDITY IFVG 1.0 (MYM) (`lliqmym`)

Zmerané 2026-11-12 na `MYM/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `mym_databento_5m`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy lliqmym \
   --profile mym_databento_5m \
   --pair MYM/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 292 obchodov spolu — na štatistiku dosť
- drawdown drží: 95. percentil 1.8 %
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 1 z 5 referenčných okien (20221001-20231001, 20231001-20241001, 20240904-20250904, 20250904-20260904 v strate)
- break-even -0.0027 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 3 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- nie je lepšia než náhodný vstup za tých istých pravidiel (-1.2 sigma) — výber vstupu nepridáva nič
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 70 | +0.08 | 0.0037 | 0.2 | 55.7 | +9/-4 | `20261112-111922-86e635` |
| 20221001-20231001 | 53 | -0.35 | -0.0101 | 0.4 | 52.8 | +7/-5 | `20261112-111925-e18a6d` |
| 20231001-20241001 | 38 | -0.04 | 0.0003 | 0.1 | 47.4 | +4/-4 | `20261112-111929-e864fd` |
| 20240904-20250904 | 63 | -0.47 | -0.0086 | 0.6 | 42.9 | +4/-6 | `20261112-111935-7fbfab` |
| 20250904-20260904 | 72 | -0.10 | 0.0000 | 0.3 | 51.4 | +5/-4 | `20261112-111942-36304e` |

Zisková v **1 z 5** okien, obchodov spolu 292, break-even celkom -0.0027 %. Okná sa prekrývajú, 4 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.27 ATR za 5 barov)
- medián držania 5.3 barov grafu
- winrate 50.34 %, payoff 0.758
- 0.16 obchodov za deň
- šikmosť výnosov -2.824

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 50.3 %, `stop_loss` 49.7 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0097 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bežný deň | 259 | 88.7 % | 49.4 | -0.0038 | 0.0070 | +0.0097 |
| deň pred sviatkom | 8 | 2.7 % | 50.0 | -0.0005 | -0.0027 | +0.0000 |

**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| proti trendu | 231 | 79.1 % | 50.2 | -0.0048 | 0.0054 | +0.0081 |
| s trendom | 61 | 20.9 % | 50.8 | 0.0054 | -0.0048 | -0.0021 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 7 – 14 | 73 | 25.0 % | 35.6 | -0.0175 | 0.0023 | +0.0050 |
| nad 22 | 72 | 24.7 % | 50.0 | -0.0014 | -0.0031 | -0.0004 |
| 14 – 22 | 72 | 24.7 % | 54.2 | 0.0015 | -0.0040 | -0.0013 |
| do 7 | 75 | 25.7 % | 61.3 | 0.0066 | -0.0059 | -0.0032 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0027 % | -0.0002 % ± 0.0020 | -1.21 | 10.8 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0027 % | -0.0000 % ± 0.0016 | -1.62 | 5.2 |

HORSIE nez nahoda (-1.2 sigma). Nahodny vstup za tych istych pravidiel dava lepsi vysledok - vyber vstupu vysledku skodi.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 85 | 5.8 | 51.8 | 0.0009 | 77 |
| 2022-12 - 2024-03 | 57 | 3.9 | 56.1 | -0.0055 | 25 |
| 2024-03 - 2025-06 | 62 | 4.2 | 43.5 | -0.0067 | 20 |
| 2025-06 - 2026-09 | 88 | 6.0 | 50.0 | -0.0013 | 60 |

Hranice pre úsek veľkosti posledného obdobia: -0.0101 až +0.0045 % (medián -0.0023).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 60. percentile, teda v medziach -0.0101 až +0.0045 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 10** — 2023-08-17T02:05 až 2023-10-30T04:30, spolu +71.99.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-08-17T02:05 | 2023-08-17T03:07 | +10.39 | +0.06 | `take_profit` |
| 2 | 2023-08-20T23:55 | 2023-08-21T00:25 | +8.39 | +0.05 | `take_profit` |
| 3 | 2023-08-31T02:50 | 2023-08-31T03:02 | +4.39 | +0.03 | `take_profit` |
| 4 | 2023-09-05T00:15 | 2023-09-05T00:24 | +3.89 | +0.02 | `take_profit` |
| 5 | 2023-09-12T02:20 | 2023-09-12T03:34 | +5.39 | +0.03 | `take_profit` |
| 6 | 2023-09-18T01:20 | 2023-09-18T01:32 | +4.89 | +0.03 | `take_profit` |
| 7 | 2023-10-16T01:20 | 2023-10-16T02:03 | +10.91 | +0.06 | `take_profit` |
| 8 | 2023-10-20T02:05 | 2023-10-20T02:42 | +10.41 | +0.06 | `take_profit` |
| 9 | 2023-10-23T02:10 | 2023-10-23T02:25 | +5.42 | +0.03 | `take_profit` |
| 10 | 2023-10-30T02:10 | 2023-10-30T04:30 | +7.93 | +0.05 | `take_profit` |

**Straty za sebou: 6** — 2025-05-19T00:30 až 2025-06-17T02:02, spolu -99.98.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-05-19T00:30 | 2025-05-19T01:02 | -22.25 | -0.10 | `stop_loss` |
| 2 | 2025-05-27T00:50 | 2025-05-27T01:04 | -11.74 | -0.06 | `stop_loss` |
| 3 | 2025-06-02T00:45 | 2025-06-02T01:43 | -17.74 | -0.08 | `stop_loss` |
| 4 | 2025-06-10T02:05 | 2025-06-10T02:50 | -13.25 | -0.06 | `stop_loss` |
| 5 | 2025-06-12T03:25 | 2025-06-12T04:38 | -13.75 | -0.06 | `stop_loss` |
| 6 | 2025-06-17T01:55 | 2025-06-17T02:02 | -21.25 | -0.10 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0027 %**, medián -0.0027 %, 90 % interval -0.0068–0.0013 %
- P(edge > poplatok) = **3.1 %**
- max drawdown: medián 1.0 %, 95. percentil 1.8 %, najhorší 3.0 %
- najdlhšia séria strát: medián 6, 95. percentil 8 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %

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
<!-- POSUDOK cisla=daef384b -->

**1. Na čo sa to hodí.** Likvidita z Londýna a inverzný FVG na MYM 5m, ~60 obchodov za rok.

**2. Potenciál.** Žiadny: proti náhode −1,2 sigma (horšie než náhodný vstup), zisk len v 1 z 5 okien, break-even okolo nuly. Nočná časť seansy na MYM má malý objem, takže londýnska likvidita tu má menšiu váhu ako na NQ.

**3. Čo dorobiť.** V logike nič. Na MYM by dávala zmysel len časť v seanse NY.

**4. Čo otestovať.** Smernica od 12. 11. 19:00 (okná seansy, typ stopu a cieľa). Ak zostane pod náhodou, vyradiť.

**5. Použiteľné?** **Nie.**

**6. Čo by som pridal.** Likviditu z overnight high/low (Globex) namiesto Londýna a vstup len 9:30–11:00 NY, keď má MYM objem.

<!-- POSUDOK KONIEC -->
