# Základná analytika — NQ PRECISION 1.0 (ES) (`nqpreces`)

Zmerané 2026-10-31 na `ES/USD` 1m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `/Users/martin/IBS/.nightsearch/base_nqpreces.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy nqpreces \
   --profile /Users/martin/IBS/.nightsearch/base_nqpreces.json \
   --pair ES/USD \
   --timeframe 1m \
   --fee 1.755e-05
```

## V čom je dobrá

- 488 obchodov spolu — na štatistiku dosť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 1 z 5 referenčných okien (20211001-20221001, 20231001-20241001, 20240904-20250904, 20250904-20260904 v strate)
- break-even -0.0007 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 4 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 100.0 % (namerané 73.8 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 22.0 % pri riziku, s akým beh bežal
- nie je lepšia než náhodný vstup za tých istých pravidiel (-0.5 sigma) — výber vstupu nepridáva nič
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 108 | -30.24 | -0.0048 | 41.2 | 84.3 | +17/-2 | `20261031-084939-c47b2e` |
| 20221001-20231001 | 79 | +9.15 | 0.0046 | 4.6 | 91.1 | +18/-1 | `20261031-084948-84f9fd` |
| 20231001-20241001 | 79 | -3.39 | 0.0009 | 14.0 | 86.1 | +18/-3 | `20261031-084957-7038e2` |
| 20240904-20250904 | 112 | -34.11 | -0.0034 | 44.5 | 83.9 | +24/-2 | `20261031-085009-89fc9c` |
| 20250904-20260904 | 118 | -7.25 | 0.0009 | 27.8 | 87.3 | +39/-2 | `20261031-085021-fb4811` |

Zisková v **1 z 5** okien, obchodov spolu 488, break-even celkom -0.0007 %. Okná sa prekrývajú, 8 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+0.65 ATR za 5 barov)
- medián držania 0 barov grafu
- winrate 86.27 %, payoff 0.12
- 0.27 obchodov za deň
- šikmosť výnosov -3.392

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 86.5 %, `stop_loss` 10.7 %, `session_end` 2.9 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0067 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| žiadna | 421 | 86.3 % | 85.0 | -0.0017 | 0.0060 | +0.0067 |
| CPI | 25 | 5.1 % | 92.0 | 0.0034 | -0.0009 | -0.0002 |
| FOMC | 19 | 3.9 % | 94.7 | 0.0055 | -0.0010 | -0.0003 |
| NFP | 23 | 4.7 % | 95.7 | 0.0090 | -0.0012 | -0.0005 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bez udalosti | 421 | 86.3 % | 85.0 | -0.0017 | 0.0060 | +0.0067 |
| pred vyhlásením | 19 | 3.9 % | 94.7 | 0.0055 | -0.0010 | -0.0003 |
| po vyhlásení | 48 | 9.8 % | 93.8 | 0.0062 | -0.0014 | -0.0007 |

**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bežný deň | 458 | 93.9 % | 86.2 | -0.0011 | 0.0055 | +0.0062 |
| deň po sviatku | 13 | 2.7 % | 92.3 | 0.0077 | -0.0009 | -0.0002 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0007 % | -0.0003 % ± 0.0008 | -0.48 | 30.7 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0007 % | -0.0006 % ± 0.0011 | -0.10 | 44.0 |

Neodlisitelne od nahody (-0.5 sigma, percentil 30.7). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 131 | 8.9 | 85.5 | -0.0031 | 21 |
| 2022-12 - 2024-03 | 89 | 6.0 | 87.6 | 0.0022 | 78 |
| 2024-03 - 2025-06 | 125 | 8.5 | 83.2 | -0.0036 | 16 |
| 2025-06 - 2026-09 | 143 | 9.7 | 88.8 | 0.0015 | 79 |

Hranice pre úsek veľkosti posledného obdobia: -0.0049 až +0.0037 % (medián -0.0005).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 79. percentile, teda v medziach -0.0049 až +0.0037 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 43** — 2025-06-16T14:00 až 2025-11-06T15:00, spolu +1683.99.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-06-16T14:00 | 2025-06-16T14:00 | +51.80 | +0.02 | `take_profit` |
| 2 | 2025-06-18T14:00 | 2025-06-18T14:00 | +39.38 | +0.01 | `take_profit` |
| 3 | 2025-06-19T14:00 | 2025-06-19T14:01 | +39.51 | +0.01 | `take_profit` |
| 4 | 2025-06-23T14:00 | 2025-06-23T14:00 | +39.40 | +0.01 | `take_profit` |
| 5 | 2025-06-27T14:00 | 2025-06-27T14:00 | +1.59 | +0.00 | `take_profit` |
| 6 | 2025-07-01T14:00 | 2025-07-01T14:00 | +26.54 | +0.01 | `take_profit` |
| 7 | 2025-07-03T14:00 | 2025-07-03T14:00 | +13.93 | +0.00 | `take_profit` |
| 8 | 2025-07-09T14:00 | 2025-07-09T14:00 | +26.43 | +0.01 | `take_profit` |
| 9 | 2025-07-15T14:00 | 2025-07-15T14:00 | +51.41 | +0.02 | `take_profit` |
| 10 | 2025-07-16T14:00 | 2025-07-16T14:06 | +51.48 | +0.02 | `take_profit` |
| 11 | 2025-07-17T14:00 | 2025-07-17T14:00 | +38.91 | +0.01 | `take_profit` |
| 12 | 2025-07-21T14:00 | 2025-07-21T14:00 | +26.33 | +0.01 | `take_profit` |
| 13 | 2025-07-22T14:00 | 2025-07-22T14:00 | +51.40 | +0.02 | `take_profit` |
| 14 | 2025-08-01T14:00 | 2025-08-01T14:00 | +64.01 | +0.02 | `take_profit` |
| 15 | 2025-08-04T14:00 | 2025-08-04T14:00 | +26.38 | +0.01 | `take_profit` |
| 16 | 2025-08-08T14:00 | 2025-08-08T14:00 | +26.27 | +0.01 | `take_profit` |
| 17 | 2025-08-12T14:00 | 2025-08-12T14:00 | +76.24 | +0.02 | `take_profit` |
| 18 | 2025-08-13T14:00 | 2025-08-13T14:06 | +26.10 | +0.01 | `take_profit` |
| 19 | 2025-08-14T14:00 | 2025-08-14T14:03 | +38.63 | +0.01 | `take_profit` |
| 20 | 2025-08-20T14:00 | 2025-08-20T14:05 | +51.29 | +0.02 | `take_profit` |
| 21 | 2025-08-28T14:00 | 2025-08-28T14:00 | +38.62 | +0.01 | `take_profit` |
| 22 | 2025-09-01T14:00 | 2025-09-01T14:00 | +1.13 | +0.00 | `take_profit` |
| 23 | 2025-09-02T14:00 | 2025-09-02T14:00 | +88.74 | +0.03 | `take_profit` |
| 24 | 2025-09-03T14:00 | 2025-09-03T14:00 | +51.20 | +0.02 | `take_profit` |
| 25 | 2025-09-05T14:00 | 2025-09-05T14:00 | +51.04 | +0.02 | `take_profit` |
| 26 | 2025-09-11T14:00 | 2025-09-11T14:00 | +38.47 | +0.01 | `take_profit` |
| 27 | 2025-09-15T14:00 | 2025-09-15T14:00 | +13.28 | +0.00 | `take_profit` |
| 28 | 2025-09-16T14:00 | 2025-09-16T14:00 | +25.79 | +0.01 | `take_profit` |
| 29 | 2025-09-22T14:00 | 2025-09-22T14:00 | +0.71 | +0.00 | `take_profit` |
| 30 | 2025-09-24T14:00 | 2025-09-24T14:00 | +25.72 | +0.01 | `take_profit` |
| 31 | 2025-09-26T14:00 | 2025-09-26T14:00 | +38.25 | +0.01 | `take_profit` |
| 32 | 2025-10-06T14:00 | 2025-10-06T14:00 | +13.12 | +0.00 | `take_profit` |
| 33 | 2025-10-09T14:00 | 2025-10-09T14:00 | +25.59 | +0.01 | `take_profit` |
| 34 | 2025-10-13T14:00 | 2025-10-13T14:00 | +63.25 | +0.02 | `take_profit` |
| 35 | 2025-10-15T14:00 | 2025-10-15T14:00 | +63.16 | +0.02 | `take_profit` |
| 36 | 2025-10-21T14:00 | 2025-10-21T14:00 | +38.13 | +0.01 | `take_profit` |
| 37 | 2025-10-23T14:00 | 2025-10-23T14:00 | +25.64 | +0.01 | `take_profit` |
| 38 | 2025-10-28T14:00 | 2025-10-28T14:00 | +37.87 | +0.01 | `take_profit` |
| 39 | 2025-10-29T14:00 | 2025-10-29T14:00 | +25.30 | +0.01 | `take_profit` |
| 40 | 2025-10-30T14:00 | 2025-10-30T14:00 | +75.38 | +0.02 | `take_profit` |
| 41 | 2025-11-04T15:00 | 2025-11-04T15:00 | +63.00 | +0.02 | `take_profit` |
| 42 | 2025-11-05T15:00 | 2025-11-05T15:05 | +63.03 | +0.02 | `take_profit` |
| 43 | 2025-11-06T15:00 | 2025-11-06T15:00 | +50.59 | +0.01 | `take_profit` |

**Straty za sebou: 3** — 2023-12-07T15:00 až 2024-01-03T15:00, spolu -699.82.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-12-07T15:00 | 2023-12-07T15:06 | -258.03 | -0.11 | `stop_loss` |
| 2 | 2023-12-19T15:00 | 2023-12-19T15:01 | -195.93 | -0.08 | `stop_loss` |
| 3 | 2024-01-03T15:00 | 2024-01-03T15:00 | -245.86 | -0.10 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0007 %**, medián -0.0007 %, 90 % interval -0.0031–0.0016 %
- P(edge > poplatok) = **3.9 %**
- max drawdown: medián 73.8 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 3, 95. percentil 3 obchodov
- pravdepodobnosť ruiny účtu: 22.0 %

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
<!-- POSUDOK cisla=aa06ffe7 -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na ES, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Jedna snímka denne o 10:00 NY, cieľ 0,3 ATR a stop 2,2 ATR — skalp s WR ~85–90 %, ktorý žije z toho, že jedna strata nezožerie 7 výhier. Tu na ES — rovnaká logika ako MNQ, prahy v ATR sa prispôsobia.
2. **Má potenciál?** Zisková v 1 z 5 okien, 488 obchodov (~98 za rok), break-even -0.0007 % (pod poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 86.27 % pri payoffe 0.12. Odložený rok 25/26: -7.25 % PnL, break-even 0.0009 %. Kladné okná sú skôr vlastnosť vzorky ako stabilný jav.
3. **Čo dorobiť.** Predloha je tickova (9:59:55); na 1m sa vstupuje o 5 s neskôr — overiť na 1m, či sa to neoplatí posunúť na 9:59. Pomer cieľ / stop 0,14 je na hrane: pri poplatku a sklze rozhoduje každý tick.
4. **Čo otestovať ďalej.** Smernica (`nqprec*`: stop / cieľ v ATR, výstup v čase, čas snímky, filtre); hlavne 2× poplatok a sklz (krok 9) — pri payoffe 0,15 je to rozhodujúce.
5. **Použiteľné?** **V defaultoch predlohy nie** — edge nad poplatkom nie je stabilný po rokoch; šancu má len s nastavením, ktoré nájde smernica (inak vyradiť).
6. **Čo by som pridal.** Cieľ aspoň 0,5 ATR a stop 1 ATR (payoff ~0,5), alebo vstup len v smere včerajška / overnightu.

<!-- POSUDOK KONIEC -->
