# Základná analytika — FPC 1.0 — férová cena (`fpc`)

Zmerané 2026-10-26 na `MNQ/USD` 1m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/fpc/configs/mnq_databento_1m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy fpc \
   --profile tradebot/strategies/fpc/configs/mnq_databento_1m.json \
   --pair MNQ/USD \
   --timeframe 1m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 6661 obchodov spolu — na štatistiku dosť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 0 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20231001-20241001, 20240904-20250904, 20250904-20260904 v strate)
- break-even -0.0015 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 0 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 81.7 % (namerané 56.3 % medián) — na účet to treba mať
- nie je lepšia než náhodný vstup za tých istých pravidiel (-1.6 sigma) — výber vstupu nepridáva nič
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 1478 | -14.25 | -0.0037 | 15.7 | 38.5 | +8/-12 | `20261026-131113-940f31` |
| 20221001-20231001 | 1126 | -2.35 | 0.0005 | 4.8 | 40.5 | +6/-13 | `20261026-131121-168846` |
| 20231001-20241001 | 1111 | -9.86 | -0.0020 | 13.6 | 39.0 | +6/-16 | `20261026-131129-60bd1c` |
| 20240904-20250904 | 1421 | -5.48 | 0.0003 | 8.7 | 40.0 | +7/-11 | `20261026-131137-427b33` |
| 20250904-20260904 | 1643 | -19.25 | -0.0016 | 25.6 | 38.3 | +8/-12 | `20261026-131145-9b3c00` |

Zisková v **0 z 5** okien, obchodov spolu 6661, break-even celkom -0.0015 %. Okná sa prekrývajú, 118 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+0.55 ATR za 5 barov)
- medián držania 6 barov grafu
- winrate 39.09 %, payoff 1.438
- 3.7 obchodov za deň
- šikmosť výnosov +0.526

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 59.6 %, `take_profit` 37.3 %, `session_end` 3.1 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0054 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| proti trendu | 5528 | 83.0 % | 38.5 | -0.0024 | 0.0039 | +0.0054 |
| s trendom | 1133 | 17.0 % | 42.1 | 0.0039 | -0.0024 | -0.0009 |

**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| žiadna | 5457 | 81.9 % | 38.6 | -0.0023 | 0.0024 | +0.0039 |
| CPI | 464 | 7.0 % | 39.7 | 0.0002 | -0.0016 | -0.0001 |
| NFP | 463 | 7.0 % | 41.5 | 0.0029 | -0.0018 | -0.0003 |
| FOMC | 270 | 4.1 % | 43.0 | 0.0053 | -0.0017 | -0.0002 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| pred vyhlásením | 108 | 1.6 % | 34.3 | -0.0100 | -0.0013 | +0.0002 |
| bez udalosti | 5457 | 81.9 % | 38.6 | -0.0023 | 0.0024 | +0.0039 |
| po vyhlásení | 1096 | 16.5 % | 41.8 | 0.0037 | -0.0024 | -0.0009 |

Parametre, ktorými sa dá s tým niečo spraviť: `revSL`, `revTP`, `s1H`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0013 % | -0.0001 % ± 0.0008 | -1.55 | 6.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0013 % | -0.0003 % ± 0.0010 | -0.99 | 16.1 |

HORSIE nez nahoda (-1.6 sigma). Nahodny vstup za tych istych pravidiel dava lepsi vysledok - vyber vstupu vysledku skodi.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 1805 | 122.4 | 38.6 | -0.0035 | 16 |
| 2022-12 - 2024-03 | 1241 | 84.1 | 40.1 | -0.0005 | 66 |
| 2024-03 - 2025-06 | 1715 | 116.3 | 39.8 | -0.0001 | 76 |
| 2025-06 - 2026-09 | 1900 | 128.8 | 38.3 | -0.0017 | 46 |

Hranice pre úsek veľkosti posledného obdobia: -0.0045 až +0.0016 % (medián -0.0015).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 46. percentile, teda v medziach -0.0045 až +0.0016 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 8** — 2021-12-29T15:32 až 2022-01-03T20:43, spolu +1064.17, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2021-12-29T15:32 | 2021-12-29T16:03 | +148.69 | +0.23 | `take_profit` |
| 2 | 2021-12-30T15:31 | 2021-12-30T16:30 | +18.68 | +0.03 | `session_end` |
| 3 | 2021-12-30T19:01 | 2021-12-30T20:36 | +148.68 | +0.22 | `take_profit` |
| 4 | 2021-12-31T14:31 | 2021-12-31T14:32 | +147.69 | +0.22 | `take_profit` |
| 5 | 2022-01-03T14:31 | 2022-01-03T14:37 | +151.35 | +0.46 | `take_profit` |
| 6 | 2022-01-03T14:46 | 2022-01-03T14:47 | +150.70 | +0.23 | `take_profit` |
| 7 | 2022-01-03T14:57 | 2022-01-03T15:03 | +149.70 | +0.23 | `take_profit` |
| 8 | 2022-01-03T20:17 | 2022-01-03T20:43 | +148.69 | +0.23 | `take_profit` |

**Straty za sebou: 16** — 2024-08-12T14:28 až 2024-08-15T14:13, spolu -1628.76.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-08-12T14:28 | 2024-08-12T14:37 | -102.63 | -0.14 | `stop_loss` |
| 2 | 2024-08-12T14:39 | 2024-08-12T15:02 | -100.63 | -0.13 | `stop_loss` |
| 3 | 2024-08-12T18:04 | 2024-08-12T18:08 | -101.61 | -0.14 | `stop_loss` |
| 4 | 2024-08-13T12:43 | 2024-08-13T13:21 | -102.64 | -0.14 | `stop_loss` |
| 5 | 2024-08-13T13:28 | 2024-08-13T13:32 | -103.65 | -0.14 | `stop_loss` |
| 6 | 2024-08-13T13:39 | 2024-08-13T13:45 | -103.65 | -0.14 | `stop_loss` |
| 7 | 2024-08-13T13:56 | 2024-08-13T13:58 | -99.65 | -0.13 | `stop_loss` |
| 8 | 2024-08-13T18:03 | 2024-08-13T18:35 | -101.68 | -0.13 | `stop_loss` |
| 9 | 2024-08-14T13:46 | 2024-08-14T13:51 | -100.68 | -0.13 | `stop_loss` |
| 10 | 2024-08-14T13:54 | 2024-08-14T13:54 | -100.67 | -0.13 | `stop_loss` |
| 11 | 2024-08-14T14:03 | 2024-08-14T14:06 | -104.67 | -0.14 | `stop_loss` |
| 12 | 2024-08-15T12:44 | 2024-08-15T12:46 | -100.71 | -0.13 | `stop_loss` |
| 13 | 2024-08-15T13:06 | 2024-08-15T13:30 | -99.72 | -0.13 | `stop_loss` |
| 14 | 2024-08-15T13:33 | 2024-08-15T13:34 | -101.72 | -0.13 | `stop_loss` |
| 15 | 2024-08-15T13:41 | 2024-08-15T13:48 | -101.72 | -0.13 | `stop_loss` |
| 16 | 2024-08-15T14:05 | 2024-08-15T14:13 | -102.73 | -0.13 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0015 %**, medián -0.0015 %, 90 % interval -0.0031–0.0002 %
- P(edge > poplatok) = **0.1 %**
- max drawdown: medián 56.3 %, 95. percentil 81.7 %, najhorší 100.0 %
- najdlhšia séria strát: medián 16, 95. percentil 21 obchodov
- pravdepodobnosť ruiny účtu: 0.3 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **25** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=2adc4a35 -->

_Posudok (Claude, 26. 10. 2026) — nastavenie: repo profil `mnq_databento_1m` (MNQ, graf 1m), nie ladený profil
testera; na porovnanie som pustil aj ladený `FPC_MNQ_1m_365obch_WR69_PF1_45` na tých istých piatich oknách._

1. **Na čo sa to hodí a na čo nie.** V tomto nastavení na nič. Prerazenie na 1m grafe s 3,7 obchodu za deň (6 661
   obchodov), medián držania 6 barov = 6 minút, winrate 39 %, payoff 1,44. **Pozor na 1m graf:** limity stratégie
   v baroch (`*MaxBars`, okná a expirácie) tu znamenajú minúty a 1m detail fillov nič nespresňuje — SL aj TP v tej istej
   minúte sa rozhoduje pravidlom, nie poradím cien. Na 1m sú teda fill aj sklz najmenej spoľahlivé práve tam, kde je
   edge najtenší.
2. **Má to potenciál?** Nie. Strata v 5 z 5 okien (−2,4 až −19,3 %), break-even −0,0015 % pod poplatkom, 0 %
   bootstrapových vzoriek nad poplatkom, −1,6 σ proti náhode a 95. percentil drawdownu 81,7 % — pri riziku, s akým
   beh bežal, by účet takmer zanikol. Ladený profil testera nie je lepší: 4 z 5 okien v strate (−1,4 / −3,05 / −1,9 /
   −1,0 %) a jediný ziskový rok 2025/26 (+4,26 %, PF 1,21) je ten, na ktorom bol vybraný — podpis pretrénovania.
3. **Čo treba dorobiť.** Nič, kým stratégia nemá jav, ktorý by sa dal zmerať. Profily „posl. rok PF 1,45“ v
   `tester/profiles` treba čítať ako výber na jednom roku, nie ako výsledok.
4. **Čo otestovať ďalej.** Jediný test, ktorý by mohol zmeniť záver: ten istý vstup na 5m grafe (`--timeframe 5m`,
   limity v baroch prepočítané ×1/5) — ak ani tam nebude break-even nad poplatkom aspoň v 3 z 5 okien, stratégiu odložiť.
5. **Je to použiteľné?** Nie — ani repo, ani ladený profil. Na 1m s 3–4 obchodmi denne by poplatky a sklz zjedli aj
   malý edge, a ten tu nie je.
6. **Čo by som pridal.** Obmedziť sa na prvú hodinu NY seansy, kde má prerazenie na indexe najväčšiu silu, a
   obchodovať len prvý signál dňa — 3,7 obchodu za deň je pri tomto payoffe priveľa.

<!-- POSUDOK KONIEC -->
