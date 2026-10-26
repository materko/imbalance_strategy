# Základná analytika — FVG POLARITY (MGC) (`fvgpolaritymgc`)

Zmerané 2026-10-26 na `MGC/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/fvgpolaritymgc/configs/WK_fvgpolarity_MGC_161obch_WR61_R1_1.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy fvgpolaritymgc \
   --profile tradebot/strategies/fvgpolaritymgc/configs/WK_fvgpolarity_MGC_161obch_WR61_R1_1.json \
   --pair MGC/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 1483 obchodov spolu — na štatistiku dosť
- break-even 0.0028 % je nad poplatkom 0.0018 % (rezerva +0.0010 bodu)
- drawdown drží: 95. percentil 7.3 %
- odlíšiteľná od náhody (+3.3 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 70. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: protitrendová (mean reversion) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 3 z 5 referenčných okien (20211001-20221001, 20231001-20241001 v strate)
- edge nad poplatkom len v 79 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 409 | -0.66 | 0.0010 | 1.6 | 75.5 | +16/-5 | `20261026-131352-c850d0` |
| 20221001-20231001 | 386 | +1.37 | 0.0034 | 1.6 | 79.0 | +26/-4 | `20261026-131358-91873c` |
| 20231001-20241001 | 363 | -1.61 | -0.0000 | 3.3 | 71.9 | +19/-4 | `20261026-131404-3e4e6c` |
| 20240904-20250904 | 247 | +2.83 | 0.0061 | 2.4 | 64.8 | +11/-6 | `20261026-131410-8a66de` |
| 20250904-20260904 | 107 | +2.02 | 0.0099 | 1.2 | 63.5 | +9/-3 | `20261026-131416-fefafc` |

Zisková v **3 z 5** okien, obchodov spolu 1483, break-even celkom 0.0028 %. Okná sa prekrývajú, 29 obchodov započítaných dvakrát vypadlo.

## Charakter

**Protitrendová (mean reversion)** (istota dobrá)

- vstup proti poslednému pohybu (-0.35 ATR za 5 barov)
- medián držania 5 barov grafu
- winrate 72.96 %, payoff 0.394
- 0.82 obchodov za deň
- šikmosť výnosov +0.701

- **Čo je normálne:** Winrate nad 60 % a payoff pod 1 je pri tomto type v poriadku — zarába sa frekvenciou, nie veľkosťou.
- **Na čo pozor:** Jedna strata môže zmazať mesiac. Stop je tu dôležitejší než vstup a `maxLossDollar` aj drawdown limit majú väčší význam než pri ostatných typoch.
- **Čo ladiť:** Stop a filter režimu (v trende protitrendová stratégia dostáva rany). Ladiť RR nahor väčšinou len zníži winrate a nič nepridá.

Výstupy: `take_profit` 73 %, `stop_loss` 27 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0065 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| žiadna | 1339 | 90.3 % | 73.0 | 0.0022 | 0.0093 | +0.0065 |
| NFP | 43 | 2.9 % | 69.8 | 0.0056 | 0.0028 | +0.0000 |
| CPI | 63 | 4.2 % | 76.2 | 0.0075 | 0.0026 | -0.0002 |
| FOMC | 34 | 2.3 % | 70.6 | 0.0215 | 0.0024 | -0.0004 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bez udalosti | 1339 | 90.3 % | 73.0 | 0.0022 | 0.0093 | +0.0065 |
| pred vyhlásením | 75 | 5.1 % | 80.0 | 0.0085 | 0.0025 | -0.0003 |
| po vyhlásení | 69 | 4.7 % | 63.8 | 0.0103 | 0.0025 | -0.0003 |

**Volatilita voči normálu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.75 – 0.944 | 371 | 25.0 % | 71.2 | -0.0018 | 0.0045 | +0.0017 |
| 0.944 – 1.182 | 370 | 24.9 % | 71.3 | 0.0024 | 0.0030 | +0.0002 |
| nad 1.182 | 370 | 24.9 % | 68.4 | 0.0044 | 0.0024 | -0.0004 |
| do 0.75 | 372 | 25.1 % | 80.9 | 0.0063 | 0.0015 | -0.0013 |

Parametre, ktorými sa dá s tým niečo spraviť: `slPoints`, `tpLevel`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0036 % | -0.0004 % ± 0.0012 | +3.28 | 99.9 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0036 % | -0.0004 % ± 0.0012 | +3.28 | 99.9 |

Edge je odlisitelny od nahody (3.3 sigma, percentil 99.9).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 487 | 33.0 | 76.4 | 0.0018 | 34 |
| 2022-12 - 2024-03 | 484 | 32.8 | 76.0 | 0.0006 | 16 |
| 2024-03 - 2025-06 | 368 | 24.9 | 68.8 | 0.0057 | 87 |
| 2025-06 - 2026-09 | 144 | 9.8 | 61.8 | 0.0050 | 70 |

Hranice pre úsek veľkosti posledného obdobia: -0.0037 až +0.0105 % (medián 0.0026).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 70. percentile, teda v medziach -0.0037 až +0.0105 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je. Signálov pritom ubudlo: z 33.02 na 9.76 obchodov za mesiac. To je úpadok tiež, len v break-evene ho vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 26** — 2022-10-14T18:30 až 2022-11-22T03:49, spolu +715.87.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-10-14T18:30 | 2022-10-14T18:32 | +28.26 | +0.06 | `take_profit` |
| 2 | 2022-10-19T01:48 | 2022-10-19T02:03 | +13.26 | +0.03 | `take_profit` |
| 3 | 2022-10-19T23:12 | 2022-10-20T00:15 | +17.71 | +0.03 | `take_profit` |
| 4 | 2022-10-20T23:00 | 2022-10-20T23:00 | +9.71 | +0.01 | `take_profit` |
| 5 | 2022-10-21T10:42 | 2022-10-21T11:05 | +43.28 | +0.09 | `take_profit` |
| 6 | 2022-10-21T11:15 | 2022-10-21T12:01 | +50.86 | +0.16 | `take_profit` |
| 7 | 2022-10-21T17:12 | 2022-10-21T17:25 | +58.26 | +0.12 | `take_profit` |
| 8 | 2022-10-26T02:09 | 2022-10-26T02:09 | +9.67 | +0.01 | `take_profit` |
| 9 | 2022-10-26T16:15 | 2022-10-26T16:19 | +43.24 | +0.09 | `take_profit` |
| 10 | 2022-10-27T07:39 | 2022-10-27T07:43 | +37.25 | +0.07 | `take_profit` |
| 11 | 2022-10-27T18:23 | 2022-10-27T19:30 | +37.66 | +0.06 | `take_profit` |
| 12 | 2022-10-30T23:26 | 2022-10-30T23:31 | +17.69 | +0.03 | `take_profit` |
| 13 | 2022-10-31T14:48 | 2022-10-31T14:50 | +24.85 | +0.08 | `take_profit` |
| 14 | 2022-10-31T18:13 | 2022-10-31T18:35 | +13.70 | +0.02 | `take_profit` |
| 15 | 2022-10-31T23:09 | 2022-10-31T23:13 | +9.70 | +0.01 | `take_profit` |
| 16 | 2022-11-02T23:31 | 2022-11-02T23:40 | +17.70 | +0.03 | `take_profit` |
| 17 | 2022-11-07T02:57 | 2022-11-07T03:03 | +34.24 | +0.07 | `take_profit` |
| 18 | 2022-11-10T23:31 | 2022-11-10T23:52 | +37.15 | +0.07 | `take_profit` |
| 19 | 2022-11-11T03:25 | 2022-11-11T03:32 | +31.15 | +0.06 | `take_profit` |
| 20 | 2022-11-11T19:39 | 2022-11-11T19:49 | +33.52 | +0.05 | `take_profit` |
| 21 | 2022-11-14T11:07 | 2022-11-14T11:12 | +40.15 | +0.08 | `take_profit` |
| 22 | 2022-11-15T23:45 | 2022-11-16T00:09 | +21.50 | +0.03 | `take_profit` |
| 23 | 2022-11-16T06:39 | 2022-11-16T07:16 | +25.13 | +0.05 | `take_profit` |
| 24 | 2022-11-17T19:58 | 2022-11-17T20:07 | +21.52 | +0.03 | `take_profit` |
| 25 | 2022-11-21T12:02 | 2022-11-21T12:03 | +13.55 | +0.02 | `take_profit` |
| 26 | 2022-11-22T02:00 | 2022-11-22T03:49 | +25.16 | +0.05 | `take_profit` |

**Straty za sebou: 6** — 2025-04-14T13:36 až 2025-05-09T13:00, spolu -526.83.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-04-14T13:36 | 2025-04-14T13:44 | -94.13 | -0.29 | `stop_loss` |
| 2 | 2025-04-16T09:54 | 2025-04-16T10:08 | -76.33 | -0.11 | `stop_loss` |
| 3 | 2025-04-21T09:57 | 2025-04-21T11:11 | -82.39 | -0.12 | `stop_loss` |
| 4 | 2025-04-21T12:21 | 2025-04-21T12:24 | -88.40 | -0.13 | `stop_loss` |
| 5 | 2025-04-21T22:00 | 2025-04-21T22:05 | -96.41 | -0.14 | `stop_loss` |
| 6 | 2025-05-09T11:36 | 2025-05-09T13:00 | -89.17 | -0.27 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0028 %**, medián 0.0028 %, 90 % interval 0.0006–0.0051 %
- P(edge > poplatok) = **78.5 %**
- max drawdown: medián 3.7 %, 95. percentil 7.3 %, najhorší 15.4 %
- najdlhšia séria strát: medián 6, 95. percentil 7 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **331** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=179a0777 -->

_Posudok (Claude, 26. 10. 2026) — nastavenie: `WK_fvgpolarity_MGC_161obch_WR61_R1_1` (MGC 3m), profil vybraný
na poslednom roku („posl. rok 161 obch, PF 1,80“)._

1. **Na čo sa to hodí a na čo nie.** Na zlato (MGC/GC) 3m, protitrendový návrat do FVG (istota dobrá): 1 483 obchodov,
   0,82 za deň, winrate 73 %, payoff 0,39, 73 % výstupov na TP. Nehodí sa tam, kde je sklz väčší než pár tickov:
   pri payoffe 0,39 rozhoduje každý tick na vstupe aj na SL.
2. **Má to potenciál?** Slabý, ale skutočný. Za: +3,3 σ proti náhodnému vstupu, edge drží (70. percentil), drawdown
   malý (95. percentil 7,3 %, ruina 0 %), posledné dva roky najlepšie (break-even 0,0061 a 0,0099 %). Proti: zisková
   len v 3 z 5 okien (2021/22 −0,66 %, 2023/24 −1,61 %), break-even celkom 0,0028 % je len o 0,0010 nad poplatkom
   0,0018 % a nad poplatkom je len 79 % vzoriek. Rast ku koncu je presne to, čo by spravil výber profilu na poslednom
   roku — dva najlepšie roky sú zároveň roky ladenia.
3. **Čo treba dorobiť.** Profil vybraný na poslednom roku treba overiť na odloženom období (smernica: odložený rok
   PF ≥ 1,3). Počet obchodov za rok klesá z 409 na 107 — profil sa na staršie roky správa inak (iná volatilita zlata),
   čo treba v posudku profilu vysvetliť, nie prehliadnuť.
4. **Čo otestovať ďalej.** 2× poplatok (`--fee 3.51e-05`): pri rezerve 0,0010 by mal break-even padnúť na nulu — ak
   padne, je edge len v poplatkoch. A walk-forward na MGC (ladiť 2 roky, merať 6 mesiacov) — rozhodne, či rast
   posledných rokov je trh, alebo výber.
5. **Je to použiteľné?** Zatiaľ nie. Náznak edge na zlate je (3,3 σ), ale rezerva nad poplatkom je taká tenká, že
   reálny sklz MGC (1 tick = 1 $) ju zmaže; na ostrý účet až po walk-forwarde a stres teste poplatku.
6. **Čo by som pridal.** Väčší TP pri rovnakom vstupe (payoff 0,39 → 0,6) s filtrom na seansu Londýn/NY, kde má
   zlato najväčší pohyb — 73 % TP naznačuje, že cena ide ďalej, než TP berie.

<!-- POSUDOK KONIEC -->
