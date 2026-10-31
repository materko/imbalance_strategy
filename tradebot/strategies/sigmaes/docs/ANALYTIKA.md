# Základná analytika — SIGMA BREAKOUT 1.0 (ES) (`sigmaes`)

Zmerané 2026-10-31 na `ES/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `/Users/martin/IBS/.nightsearch/base_sigmaes.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy sigmaes \
   --profile /Users/martin/IBS/.nightsearch/base_sigmaes.json \
   --pair ES/USD \
   --timeframe 5m \
   --fee 1.755e-05
```

## V čom je dobrá

- 1867 obchodov spolu — na štatistiku dosť
- break-even 0.0088 % je nad poplatkom 0.0018 % (rezerva +0.0070 bodu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 36. percentile toho, čo stratégia vyrobí sama od seba)
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 2 z 5 referenčných okien (20211001-20221001, 20231001-20241001, 20250904-20260904 v strate)
- edge nad poplatkom len v 80 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 100.0 % (namerané 100.0 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 74.7 % pri riziku, s akým beh bežal
- proti náhode len +1.4 sigma: náznak, nie dôkaz
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- 100 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 411 | -97.78 | -0.0038 | 333.2 | 46.2 | +6/-7 | `20261031-084859-b55ec8` |
| 20221001-20231001 | 357 | +390.96 | 0.0281 | 56.3 | 52.9 | +8/-7 | `20261031-084902-3d2796` |
| 20231001-20241001 | 383 | -25.72 | 0.0004 | 95.2 | 42.6 | +4/-8 | `20261031-084905-1e8836` |
| 20240904-20250904 | 353 | +469.23 | 0.0241 | 45.4 | 47.9 | +10/-9 | `20261031-084911-989ec0` |
| 20250904-20260904 | 370 | -73.18 | -0.0010 | 113.5 | 46.8 | +6/-7 | `20261031-084917-cd2b14` |

Zisková v **2 z 5** okien, obchodov spolu 1867, break-even celkom 0.0088 %. Okná sa prekrývajú, 7 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.37 ATR za 5 barov)
- medián držania 53 barov grafu
- winrate 47.19 %, payoff 1.197
- 1.05 obchodov za deň
- šikmosť výnosov +2.476

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `session_end` 100 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0084 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Plánovaný RR**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 99.94 R | 262 | 27.7 % | 45.4 | -0.0116 | 0.0203 | +0.0084 |
| 99.94 R – 100 R | 429 | 45.3 % | 51.3 | 0.0163 | 0.0080 | -0.0039 |
| 100 R – 100.04 R | 33 | 3.5 % | 63.6 | 0.0200 | 0.0115 | -0.0004 |
| nad 100.04 R | 222 | 23.5 % | 47.8 | 0.0285 | 0.0070 | -0.0049 |

**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.0758 – 0.1528 | 467 | 25.0 % | 45.6 | -0.0095 | 0.0149 | +0.0061 |
| do 0.0758 | 467 | 25.0 % | 47.8 | 0.0121 | 0.0077 | -0.0011 |
| 0.1528 – 0.2441 | 467 | 25.0 % | 46.9 | 0.0153 | 0.0066 | -0.0022 |
| nad 0.2441 | 466 | 25.0 % | 48.5 | 0.0173 | 0.0060 | -0.0028 |

**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 13 h – 14 h | 519 | 27.8 % | 47.4 | -0.0034 | 0.0135 | +0.0047 |
| nad 17 h | 420 | 22.5 % | 47.6 | 0.0019 | 0.0108 | +0.0020 |
| 14 h – 17 h | 348 | 18.6 % | 49.7 | 0.0145 | 0.0075 | -0.0013 |
| do 13 h | 580 | 31.1 % | 45.2 | 0.0213 | 0.0031 | -0.0057 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0088 % | -0.0000 % ± 0.0061 | +1.45 | 93.6 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0088 % | 0.0000 % ± 0.0070 | +1.26 | 90.2 |

Naznak, ale nie dokaz (1.4 sigma, percentil 93.6). Take rozdiely nahoda robi bezne.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2023-01 | 497 | 34.1 | 47.1 | -0.0006 | 27 |
| 2023-01 - 2024-03 | 454 | 31.1 | 48.9 | 0.0180 | 71 |
| 2024-03 - 2025-06 | 469 | 32.1 | 45.2 | 0.0176 | 76 |
| 2025-06 - 2026-09 | 447 | 30.6 | 47.6 | 0.0017 | 36 |

Hranice pre úsek veľkosti posledného obdobia: -0.0152 až +0.0382 % (medián 0.0073).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 36. percentile, teda v medziach -0.0152 až +0.0382 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 10** — 2025-03-12T13:45 až 2025-03-26T20:00, spolu +12712.64.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-03-12T13:45 | 2025-03-12T20:00 | +927.65 | +0.33 | `session_end` |
| 2 | 2025-03-13T13:45 | 2025-03-13T20:00 | +2240.24 | +0.80 | `session_end` |
| 3 | 2025-03-14T13:40 | 2025-03-14T20:00 | +2115.15 | +0.76 | `session_end` |
| 4 | 2025-03-17T13:35 | 2025-03-17T20:00 | +1114.97 | +0.39 | `session_end` |
| 5 | 2025-03-18T13:40 | 2025-03-18T20:00 | +702.53 | +0.25 | `session_end` |
| 6 | 2025-03-19T14:20 | 2025-03-19T20:00 | +1177.46 | +0.41 | `session_end` |
| 7 | 2025-03-20T13:35 | 2025-03-20T20:00 | +702.48 | +0.25 | `session_end` |
| 8 | 2025-03-21T16:25 | 2025-03-21T20:00 | +902.48 | +0.32 | `session_end` |
| 9 | 2025-03-24T13:40 | 2025-03-24T20:00 | +1089.81 | +0.38 | `session_end` |
| 10 | 2025-03-26T15:45 | 2025-03-26T20:00 | +1739.87 | +0.60 | `session_end` |

**Straty za sebou: 9** — 2025-03-05T21:10 až 2025-03-07T18:35, spolu -10678.53.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-03-05T21:10 | 2025-03-05T21:10 | -135.26 | -0.05 | `session_end` |
| 2 | 2025-03-06T14:40 | 2025-03-06T15:15 | -1560.15 | -0.54 | `session_end` |
| 3 | 2025-03-06T15:25 | 2025-03-06T17:00 | -2397.64 | -0.83 | `session_end` |
| 4 | 2025-03-06T17:10 | 2025-03-06T17:10 | -460.10 | -0.16 | `session_end` |
| 5 | 2025-03-06T17:20 | 2025-03-06T21:00 | -110.10 | -0.04 | `session_end` |
| 6 | 2025-03-06T21:10 | 2025-03-06T21:10 | -10.11 | -0.00 | `session_end` |
| 7 | 2025-03-07T14:35 | 2025-03-07T16:25 | -2597.54 | -0.90 | `session_end` |
| 8 | 2025-03-07T16:35 | 2025-03-07T18:10 | -2960.04 | -1.04 | `session_end` |
| 9 | 2025-03-07T18:20 | 2025-03-07T18:35 | -447.61 | -0.16 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0088 %**, medián 0.0084 %, 90 % interval -0.0043–0.0227 %
- P(edge > poplatok) = **80.2 %**
- max drawdown: medián 100.0 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 9, 95. percentil 12 obchodov
- pravdepodobnosť ruiny účtu: 74.7 %

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
<!-- POSUDOK cisla=26df7336 -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na ES, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Intraday momentum na indexoch (rovnaký jav ako NOA — Zarattini a spol.), 9:30–16:00 NY; zlato nemá otvorenie RTH, ktoré by pásmo ukotvilo. Tu na ES — rovnaká logika ako MNQ, prahy v ATR sa prispôsobia.
2. **Má potenciál?** Zisková v 2 z 5 okien, 1867 obchodov (~373 za rok), break-even 0.0088 % (nad poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 47.19 % pri payoffe 1.197. Odložený rok 25/26: -73.18 % PnL, break-even -0.0010 %. Kladné okná sú skôr vlastnosť vzorky ako stabilný jav.
3. **Čo dorobiť.** Stop: predloha bez stopu → 95. percentil DD je obrovský; otestovať `slPct` 0,25–1 % a kontrolu len každých 15–30 min (otočky v šume).
4. **Čo otestovať ďalej.** Smernica (`sigma*`: TF, dni sigma, násobok pásma, VWAP, stop); porovnať s NOA — ak NOA robí to isté lepšie, Sigma je duplicita.
5. **Použiteľné?** **V defaultoch predlohy nie** — edge nad poplatkom nie je stabilný po rokoch; šancu má len s nastavením, ktoré nájde smernica (inak vyradiť).
6. **Čo by som pridal.** Výstup cez VWAP / hranicu pásma (trailing ako NOA) namiesto držania do 16:00; menej otočiek pri širšom pásme.

<!-- POSUDOK KONIEC -->
