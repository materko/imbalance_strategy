# Základná analytika — VWAP ADX Pullback (`vwapadx`)

Zmerané 2026-10-11 na `MNQ/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/vwapadx_PRESIEL_SMERNICAMI_VWAP_ADX_Pullback_1_2026-10-11.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy vwapadx \
   --profile .nightsearch/checkup/vwapadx_PRESIEL_SMERNICAMI_VWAP_ADX_Pullback_1_2026-10-11.json \
   --pair MNQ/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 857 obchodov spolu — na štatistiku dosť
- break-even 0.0194 % je nad poplatkom 0.0018 % (rezerva +0.0176 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 4.9 %
- odlíšiteľná od náhody (+4.3 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 38. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- charakter: formácia / štruktúra (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina '0.2242 % – 0.3958 %' vlastnosti 'Vzdialenosť stopu': 214 obchodov (25.0 %), bez nej by break-even bol o +0.0127 lepší (riadi `slBars`)

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 156 | +8.28 | 0.0424 | 0.7 | 73.1 | +10/-3 | `20261011-071844-a70293` |
| 20221001-20231001 | 183 | +2.83 | 0.0135 | 1.7 | 68.3 | +8/-5 | `20261011-071847-bc0eb0` |
| 20231001-20241001 | 181 | +2.87 | 0.0099 | 1.5 | 65.8 | +11/-6 | `20261011-071850-d57df1` |
| 20240904-20250904 | 179 | +7.81 | 0.0252 | 3.6 | 63.1 | +10/-5 | `20261011-071853-21be97` |
| 20250904-20260904 | 158 | +4.79 | 0.0146 | 2.5 | 67.1 | +13/-5 | `20261011-071857-aa820a` |

Zisková v **5 z 5** okien, obchodov spolu 857, break-even celkom 0.0194 %.

## Charakter

**Formácia / štruktúra** (istota priemerná)

- vstup bez jasného smeru pohybu (-0.22 ATR za 5 barov)
- medián držania 8.7 barov grafu
- winrate 67.33 %, payoff 0.692
- 0.48 obchodov za deň
- šikmosť výnosov +2.996

- **Čo je normálne:** Zmes: časť obchodov sa chová ako prerazenie, časť ako návrat. Priemer preto o jednotlivom obchode nehovorí veľa.
- **Na čo pozor:** Práve pri tomto type sa najviac oplatí rozdeliť obchody na skupiny (`tester.analytics`) — priemer skrýva dve rôzne populácie.
- **Čo ladiť:** Podmienky vstupu (ktoré modely/formácie zapnuté) a potom až výstup.

Výstupy: `take_profit` 67.6 %, `stop_loss` 32.3 %, `force_exit` 0.1 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je '0.2242 % – 0.3958 %' vlastnosti 'Vzdialenosť stopu': 214 obchodov (25.0 %), break-even 0.0011 % oproti 0.0194 % celku. Bez nej by break-even bol 0.0236 % (+0.0127). Filter na to postavit ide, ale najprv skus `slBars` - parameter je lacnejsi a citatelnejsi nez model.


**Vzdialenosť stopu** (riadi `slBars`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.2242 % – 0.3958 % | 214 | 25.0 % | 66.4 | 0.0011 | 0.0236 | +0.0042 |
| do 0.2242 % | 215 | 25.1 % | 42.3 | 0.0061 | 0.0321 | +0.0127 |
| 0.3958 % – 0.5963 % | 214 | 25.0 % | 79.0 | 0.0272 | 0.0179 | -0.0015 |
| nad 0.5963 % | 214 | 25.0 % | 81.8 | 0.0737 | 0.0093 | -0.0101 |

**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| žiadna | 739 | 86.2 % | 66.8 | 0.0179 | 0.0307 | +0.0113 |
| CPI | 33 | 3.9 % | 60.6 | 0.0259 | 0.0192 | -0.0002 |
| NFP | 33 | 3.9 % | 75.8 | 0.0342 | 0.0189 | -0.0005 |
| FOMC | 48 | 5.6 % | 72.9 | 0.0344 | 0.0188 | -0.0006 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bez udalosti | 739 | 86.2 % | 66.8 | 0.0179 | 0.0307 | +0.0113 |
| pred vyhlásením | 21 | 2.5 % | 71.4 | 0.0213 | 0.0194 | +0.0000 |
| po vyhlásení | 97 | 11.3 % | 70.1 | 0.0329 | 0.0180 | -0.0014 |

Parametre, ktorými sa dá s tým niečo spraviť: `adxMin`, `exitHHMM`, `orEndHHMM`, `slBars`, `tpBars`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0237 % | 0.0012 % ± 0.0052 | +4.31 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0237 % | 0.0019 % ± 0.0056 | +3.90 | 100.0 |

Edge je odlisitelny od nahody (4.3 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 193 | 13.1 | 74.1 | 0.0414 | 97 |
| 2022-12 - 2024-03 | 215 | 14.6 | 67.0 | 0.0137 | 30 |
| 2024-03 - 2025-06 | 248 | 16.9 | 62.9 | 0.0165 | 40 |
| 2025-06 - 2026-09 | 201 | 13.7 | 66.7 | 0.0156 | 38 |

Hranice pre úsek veľkosti posledného obdobia: +0.0015 až +0.0374 % (medián 0.0189).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 38. percentile, teda v medziach +0.0015 až +0.0374 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 13** — 2025-10-17T16:42 až 2025-11-10T15:25, spolu +711.86.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-10-17T16:42 | 2025-10-17T16:50 | +112.25 | +0.23 | `take_profit` |
| 2 | 2025-10-17T18:42 | 2025-10-17T19:11 | +85.24 | +0.17 | `take_profit` |
| 3 | 2025-10-20T14:00 | 2025-10-20T14:04 | +32.73 | +0.06 | `take_profit` |
| 4 | 2025-10-22T05:00 | 2025-10-22T06:42 | +29.22 | +0.06 | `take_profit` |
| 5 | 2025-10-23T14:12 | 2025-10-23T14:36 | +124.73 | +0.25 | `take_profit` |
| 6 | 2025-10-23T14:45 | 2025-10-23T14:47 | +50.73 | +0.10 | `take_profit` |
| 7 | 2025-10-27T18:36 | 2025-10-27T18:43 | +30.36 | +0.03 | `take_profit` |
| 8 | 2025-10-30T20:27 | 2025-10-30T20:28 | +7.17 | +0.01 | `take_profit` |
| 9 | 2025-10-30T20:30 | 2025-10-30T20:30 | +4.17 | +0.01 | `take_profit` |
| 10 | 2025-10-30T20:33 | 2025-10-30T20:33 | +37.17 | +0.07 | `take_profit` |
| 11 | 2025-10-30T20:36 | 2025-10-30T20:37 | +22.67 | +0.04 | `take_profit` |
| 12 | 2025-11-05T15:15 | 2025-11-05T15:28 | +134.70 | +0.26 | `take_profit` |
| 13 | 2025-11-10T15:21 | 2025-11-10T15:25 | +40.70 | +0.08 | `take_profit` |

**Straty za sebou: 10** — 2024-09-13T20:27 až 2024-09-25T17:00, spolu -1364.27.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-09-13T20:27 | 2024-09-13T20:55 | -94.74 | -0.12 | `stop_loss` |
| 2 | 2024-09-13T20:27 | 2024-09-13T20:55 | -94.74 | -0.12 | `stop_loss` |
| 3 | 2024-09-18T18:15 | 2024-09-18T19:05 | -214.38 | -0.54 | `stop_loss` |
| 4 | 2024-09-18T18:15 | 2024-09-18T19:05 | -214.38 | -0.54 | `stop_loss` |
| 5 | 2024-09-19T05:00 | 2024-09-19T05:46 | -103.18 | -0.09 | `stop_loss` |
| 6 | 2024-09-19T05:00 | 2024-09-19T05:46 | -103.18 | -0.09 | `stop_loss` |
| 7 | 2024-09-19T19:00 | 2024-09-19T19:14 | -86.41 | -0.21 | `stop_loss` |
| 8 | 2024-09-19T19:00 | 2024-09-19T19:14 | -86.41 | -0.21 | `stop_loss` |
| 9 | 2024-09-25T14:33 | 2024-09-25T17:00 | -183.42 | -0.45 | `stop_loss` |
| 10 | 2024-09-25T14:33 | 2024-09-25T17:00 | -183.42 | -0.45 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0194 %**, medián 0.0193 %, 90 % interval 0.0108–0.0287 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 2.8 %, 95. percentil 4.9 %, najhorší 11.7 %
- najdlhšia séria strát: medián 6, 95. percentil 8 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **723** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=79fa1d08 -->
**Posudok (AI, 11. 10. 2026)** — profil PREŠIEL SMERNICAMI č. 1 z testovania podľa smernice (krok 7).

1. **Na čo sa to hodí a na čo nie.** MNQ 1m, pullback k VWAP s ADX, cieľ ~0,7 R, WR 67 %, drží ~9 barov. Na 1m je výsledok citlivý na plnenie a sklz.
2. **Má to potenciál?** Áno, ale najtesnejšie: +4,3 σ, break-even 0,019 % (~11× poplatok). Roky 22/23 a 23/24 slabé (+2,8 %, break-even ~0,01 %) — rezerva v pokojných rokoch je malá.
3. **Čo dorobiť.** Štvrtina obchodov so stopom 0,22–0,40 % je najslabšia (`slBars`). 1m graf → overiť sklz 1 tick, pri tak malej rezerve rozhodne. Analytika ráta obchody z prekrývajúcich sa okien 23/24 a 24/25 (september 2024) dvakrát — najdlhšia séria strát môže byť o 1–2 nadsadená.
4. **Čo otestovať ďalej.** NAS100 z Dukascopy (krok 8) — rovnaký smer výsledku = jav trhu, nie dát; 2× poplatok (`--fee 3.51e-05`) a 1 tick sklzu navyše; forward test 4–8 týždňov na 1 MNQ (krok 9).
5. **Je to použiteľné?** Podmienečne — len ak prejde stresom 1 tick sklzu. Inak o ničom.
6. **Čo by som pridal.** Filter volatility (pokojné dni vynechať) — slabé roky boli pokojné.
<!-- POSUDOK KONIEC -->
