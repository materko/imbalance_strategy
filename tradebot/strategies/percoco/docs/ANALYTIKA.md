# Základná analytika — Craig Percoco 1.0 (`percoco`)

Zmerané 2026-10-26 na `MNQ/USD` 1m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/percoco/configs/mnq_databento_1m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy percoco \
   --profile tradebot/strategies/percoco/configs/mnq_databento_1m.json \
   --pair MNQ/USD \
   --timeframe 1m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 661 obchodov spolu — na štatistiku dosť
- break-even 0.0023 % je nad poplatkom 0.0018 % (rezerva +0.0005 bodu)
- drawdown drží: 95. percentil 13.6 %
- edge drží aj v poslednom období (2025-06 - 2026-09 na 48. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- zisková v 2 z 5 referenčných okien (20211001-20221001, 20231001-20241001, 20250904-20260904 v strate)
- edge nad poplatkom len v 56 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- proti náhode len +1.1 sigma: náznak, nie dôkaz
- charakter: protitrendová (mean reversion) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'CPI' vlastnosti 'Makro udalosť v ten deň': 32 obchodov (4.8 %), bez nej by break-even bol o +0.0169 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 145 | -0.25 | 0.0009 | 3.3 | 20.7 | +3/-17 | `20261026-131544-bf3d2b` |
| 20221001-20231001 | 156 | +1.33 | 0.0049 | 2.4 | 21.1 | +2/-13 | `20261026-131552-c69d84` |
| 20231001-20241001 | 148 | -1.92 | -0.0018 | 4.5 | 18.9 | +2/-19 | `20261026-131600-e7b85b` |
| 20240904-20250904 | 109 | +1.88 | 0.0070 | 2.0 | 24.8 | +4/-12 | `20261026-131608-8e1d7e` |
| 20250904-20260904 | 115 | -0.21 | 0.0011 | 1.7 | 20.9 | +2/-10 | `20261026-131617-4ff7df` |

Zisková v **2 z 5** okien, obchodov spolu 661, break-even celkom 0.0023 %. Okná sa prekrývajú, 12 obchodov započítaných dvakrát vypadlo.

## Charakter

**Protitrendová (mean reversion)** (istota priemerná)

- vstup proti poslednému pohybu (-0.28 ATR za 5 barov)
- medián držania 11 barov grafu
- winrate 21.18 %, payoff 3.775
- 0.37 obchodov za deň
- šikmosť výnosov +2.183

- **Čo je normálne:** Winrate nad 60 % a payoff pod 1 je pri tomto type v poriadku — zarába sa frekvenciou, nie veľkosťou.
- **Na čo pozor:** Jedna strata môže zmazať mesiac. Stop je tu dôležitejší než vstup a `maxLossDollar` aj drawdown limit majú väčší význam než pri ostatných typoch.
- **Čo ladiť:** Stop a filter režimu (v trende protitrendová stratégia dostáva rany). Ladiť RR nahor väčšinou len zníži winrate a nič nepridá.

Výstupy: `stop_loss` 78.8 %, `take_profit` 21.2 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'CPI' vlastnosti 'Makro udalosť v ten deň': 32 obchodov (4.8 %), break-even -0.0135 % oproti 0.0023 % celku. Bez nej by break-even bol 0.003 % (+0.0169). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| CPI | 32 | 4.8 % | 15.6 | -0.0135 | 0.0030 | +0.0007 |
| žiadna | 572 | 86.5 % | 20.1 | -0.0003 | 0.0192 | +0.0169 |
| FOMC | 22 | 3.3 % | 36.4 | 0.0293 | 0.0010 | -0.0013 |
| NFP | 33 | 5.0 % | 36.4 | 0.0413 | 0.0004 | -0.0019 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bez udalosti | 572 | 86.5 % | 20.1 | -0.0003 | 0.0192 | +0.0169 |
| po vyhlásení | 65 | 9.8 % | 26.1 | 0.0159 | 0.0010 | -0.0013 |
| pred vyhlásením | 24 | 3.6 % | 33.3 | 0.0254 | 0.0012 | -0.0011 |

**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bežný deň | 606 | 91.7 % | 20.8 | 0.0015 | 0.0071 | +0.0048 |
| deň pred sviatkom | 9 | 1.4 % | 22.2 | 0.0055 | 0.0022 | -0.0001 |
| deň po sviatku | 20 | 3.0 % | 25.0 | 0.0073 | 0.0021 | -0.0002 |

Parametre, ktorými sa dá s tým niečo spraviť: `rrRatio`, `slBufferAtr`, `tradeDirection`, `tradeStartH`, `useHtfBias`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0044 % | 0.0001 % ± 0.0038 | +1.13 | 87.1 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0044 % | -0.0000 % ± 0.0048 | +0.93 | 81.9 |

Naznak, ale nie dokaz (1.1 sigma, percentil 87.1). Take rozdiely nahoda robi bezne.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 190 | 12.9 | 20.0 | -0.0018 | 28 |
| 2022-12 - 2024-03 | 180 | 12.2 | 21.7 | 0.0054 | 67 |
| 2024-03 - 2025-06 | 150 | 10.2 | 21.3 | 0.0026 | 55 |
| 2025-06 - 2026-09 | 141 | 9.6 | 22.0 | 0.0018 | 48 |

Hranice pre úsek veľkosti posledného obdobia: -0.0101 až +0.0154 % (medián 0.0021).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 48. percentile, teda v medziach -0.0101 až +0.0154 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 4** — 2025-04-21T13:40 až 2025-05-02T16:05, spolu +1470.12.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-04-21T13:40 | 2025-04-21T14:16 | +372.73 | +1.03 | `take_profit` |
| 2 | 2025-04-21T15:05 | 2025-04-21T15:34 | +357.49 | +0.50 | `take_profit` |
| 3 | 2025-04-24T15:02 | 2025-04-24T15:54 | +361.31 | +0.47 | `take_profit` |
| 4 | 2025-05-02T13:57 | 2025-05-02T16:05 | +378.58 | +0.94 | `take_profit` |

**Straty za sebou: 19** — 2024-05-16T14:34 až 2024-06-17T14:57, spolu -1710.60.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-05-16T14:34 | 2024-05-16T14:43 | -106.51 | -0.04 | `stop_loss` |
| 2 | 2024-05-16T15:38 | 2024-05-16T16:01 | -100.89 | -0.04 | `stop_loss` |
| 3 | 2024-05-21T14:49 | 2024-05-21T14:59 | -113.16 | -0.03 | `stop_loss` |
| 4 | 2024-05-21T15:53 | 2024-05-21T16:08 | -97.90 | -0.04 | `stop_loss` |
| 5 | 2024-05-22T13:43 | 2024-05-22T13:52 | -86.64 | -0.12 | `stop_loss` |
| 6 | 2024-05-22T14:07 | 2024-05-22T17:37 | -76.64 | -0.10 | `stop_loss` |
| 7 | 2024-05-28T14:42 | 2024-05-28T14:44 | -97.96 | -0.04 | `stop_loss` |
| 8 | 2024-05-29T15:32 | 2024-05-29T16:11 | -89.47 | -0.08 | `stop_loss` |
| 9 | 2024-05-31T13:41 | 2024-05-31T13:45 | -101.42 | -0.09 | `stop_loss` |
| 10 | 2024-06-03T14:13 | 2024-06-03T14:13 | -81.93 | -0.07 | `stop_loss` |
| 11 | 2024-06-04T14:05 | 2024-06-04T14:14 | -77.31 | -0.21 | `stop_loss` |
| 12 | 2024-06-04T14:37 | 2024-06-04T15:33 | -65.81 | -0.18 | `stop_loss` |
| 13 | 2024-06-05T13:50 | 2024-06-05T14:00 | -99.11 | -0.05 | `stop_loss` |
| 14 | 2024-06-12T14:50 | 2024-06-12T14:54 | -93.74 | -0.12 | `stop_loss` |
| 15 | 2024-06-12T15:22 | 2024-06-12T16:22 | -56.37 | -0.14 | `stop_loss` |
| 16 | 2024-06-13T13:42 | 2024-06-13T13:58 | -96.76 | -0.12 | `stop_loss` |
| 17 | 2024-06-14T14:29 | 2024-06-14T14:37 | -68.88 | -0.18 | `stop_loss` |
| 18 | 2024-06-17T13:39 | 2024-06-17T14:10 | -92.70 | -0.08 | `stop_loss` |
| 19 | 2024-06-17T14:55 | 2024-06-17T14:57 | -107.41 | -0.04 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0023 %**, medián 0.0022 %, 90 % interval -0.0035–0.0081 %
- P(edge > poplatok) = **55.8 %**
- max drawdown: medián 6.7 %, 95. percentil 13.6 %, najhorší 29.2 %
- najdlhšia séria strát: medián 21, 95. percentil 31 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **164** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=6ec463e2 -->

_Posudok (Claude, 26. 10. 2026) — nastavenie: repo profil `mnq_databento_1m` (MNQ, graf 1m), Pine defaulty;
ladený profil testera pre MNQ neexistuje._

1. **Na čo sa to hodí a na čo nie.** Protitrendová stratégia (istota priemerná) s veľkým TP: 661 obchodov, 0,37 za deň,
   winrate 21 %, payoff 3,8 — tri štvrtiny obchodov končia na SL (79 %). **Pozor na 1m graf:** limity v baroch
   (`*MaxBars`, expirácie, okná) tu znamenajú minúty a 1m detail fillov nič nespresňuje — pri SL aj TP v tej istej
   minúte rozhoduje pravidlo emulátora. Na iný TF sa profil nedá preniesť bez prepočtu týchto limitov.
2. **Má to potenciál?** Skôr nie. Break-even 0,0023 % je nad poplatkom len o 0,0005, nad poplatkom 56 % vzoriek,
   +1,1 σ proti náhode (náznak, nie dôkaz), zisková v 2 z 5 okien (2022/23 +1,33 %, 2024/25 +1,88 %). Série strát
   do 19 za sebou pri winrate 21 % sú normálne, ale treba ich uniesť. Najhoršie sú dni CPI (32 obchodov, bez nich by
   bol break-even o 0,017 lepší) — to je pri 32 obchodoch skôr šum ako filter.
3. **Čo treba dorobiť.** Profil na 5m (alebo aspoň 3m), aby 1m detail fillov mal čo spresniť; dnes sú výsledky
   najviac závislé od pravidla emulátora pre SL+TP v jednej minúte.
4. **Čo otestovať ďalej.** 2× poplatok (`--fee 3.51e-05`) — pri rezerve 0,0005 to break-even takmer iste zhodí pod
   nulu; ak nie, ten istý vstup na 5m grafe s prepočítanými limitmi.
5. **Je to použiteľné?** Nie. Edge je v hranici poplatku a sklzu, odlíšenie od náhody slabé a polovica rokov v strate.
6. **Čo by som pridal.** Vstup len pri extréme dňa (nový high/low dňa po 10:30 NY) — protitrend s payoffom 3,8 dáva
   zmysel tam, kde je návrat najpravdepodobnejší, nie pri každom lokálnom vychýlení.

<!-- POSUDOK KONIEC -->
