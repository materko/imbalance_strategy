# Základná analytika — M2 (MNQ) (`m2mnq`)

Zmerané 2026-10-28 na `MNQ/USD` 1m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `mnq_databento_1m`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy m2mnq \
   --profile mnq_databento_1m \
   --pair MNQ/USD \
   --timeframe 1m \
   --fee 1.755e-05 \
   --wallet 100000
```

## V čom je dobrá

- 43088 obchodov spolu — na štatistiku dosť
- odlíšiteľná od náhody (+5.3 sigma proti náhodnému vstupu)
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 0 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20231001-20241001, 20240904-20250904, 20250904-20260904 v strate)
- break-even 0.0002 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 0 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 100.0 % (namerané 100.0 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 100.0 % pri riziku, s akým beh bežal
- charakter: formácia / štruktúra (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 8994 | -441.92 | 0.0002 | 446.2 | 33.5 | +9/-25 | `20261028-152525-38b311` |
| 20221001-20231001 | 8529 | -543.46 | 0.0002 | 497.3 | 33.6 | +7/-16 | `20261028-152529-7c9b1f` |
| 20231001-20241001 | 8749 | -658.55 | 0.0004 | 649.0 | 34.3 | +8/-21 | `20261028-152535-969640` |
| 20240904-20250904 | 8533 | -680.37 | -0.0001 | 664.8 | 32.8 | +7/-23 | `20261028-152542-9ae433` |
| 20250904-20260904 | 8852 | -532.43 | 0.0002 | 523.1 | 33.5 | +6/-23 | `20261028-152549-a0feff` |

Zisková v **0 z 5** okien, obchodov spolu 43088, break-even celkom 0.0002 %. Okná sa prekrývajú, 569 obchodov započítaných dvakrát vypadlo.

## Charakter

**Formácia / štruktúra** (istota priemerná)

- vstup bez jasného smeru pohybu (+0.21 ATR za 5 barov)
- medián držania 3 barov grafu
- winrate 33.55 %, payoff 1.637
- 23.95 obchodov za deň
- šikmosť výnosov +2.295

- **Čo je normálne:** Zmes: časť obchodov sa chová ako prerazenie, časť ako návrat. Priemer preto o jednotlivom obchode nehovorí veľa.
- **Na čo pozor:** Práve pri tomto type sa najviac oplatí rozdeliť obchody na skupiny (`tester.analytics`) — priemer skrýva dve rôzne populácie.
- **Čo ladiť:** Podmienky vstupu (ktoré modely/formácie zapnuté) a potom až výstup.

Výstupy: `stop_loss` 66.5 %, `take_profit` 33.5 %, `force_exit` 0 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0006 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Plánovaný RR**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 2 R | 42571 | 98.9 % | 33.6 | 0.0002 | 0.0008 | +0.0006 |
| nad 2 R | 483 | 1.1 % | 32.3 | 0.0008 | 0.0002 | +0.0000 |

**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| žiadna | 38256 | 88.8 % | 33.5 | 0.0002 | 0.0005 | +0.0003 |
| FOMC | 1337 | 3.1 % | 33.6 | 0.0003 | 0.0002 | +0.0000 |
| CPI | 1881 | 4.4 % | 34.3 | 0.0005 | 0.0002 | +0.0000 |
| NFP | 1556 | 3.6 % | 34.1 | 0.0006 | 0.0002 | +0.0000 |
| FOMC+CPI | 58 | 0.1 % | 36.2 | 0.0006 | 0.0002 | +0.0000 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| pred vyhlásením | 2091 | 4.9 % | 33.3 | 0.0001 | 0.0002 | +0.0000 |
| bez udalosti | 38256 | 88.8 % | 33.5 | 0.0002 | 0.0005 | +0.0003 |
| po vyhlásení | 2741 | 6.4 % | 34.6 | 0.0009 | 0.0002 | +0.0000 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0003 % | -0.0004 % ± 0.0001 | +5.27 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0003 % | -0.0004 % ± 0.0001 | +5.27 | 100.0 |

Edge je odlisitelny od nahody (5.3 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 10900 | 739.0 | 33.5 | 0.0002 | 47 |
| 2022-12 - 2024-03 | 10734 | 727.7 | 33.8 | 0.0003 | 72 |
| 2024-03 - 2025-06 | 10611 | 719.4 | 33.4 | 0.0001 | 29 |
| 2025-06 - 2026-09 | 10843 | 735.1 | 33.4 | 0.0002 | 49 |

Hranice pre úsek veľkosti posledného obdobia: -0.0001 až +0.0005 % (medián 0.0002).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 49. percentile, teda v medziach -0.0001 až +0.0005 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 9** — 2022-06-24T00:39 až 2022-06-24T04:23, spolu +8485.50.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-06-24T00:39 | 2022-06-24T00:44 | +935.72 | +0.06 | `take_profit` |
| 2 | 2022-06-24T00:59 | 2022-06-24T01:14 | +944.70 | +0.07 | `take_profit` |
| 3 | 2022-06-24T01:18 | 2022-06-24T01:21 | +944.70 | +0.07 | `take_profit` |
| 4 | 2022-06-24T01:30 | 2022-06-24T01:36 | +954.38 | +0.16 | `take_profit` |
| 5 | 2022-06-24T02:05 | 2022-06-24T02:09 | +953.44 | +0.09 | `take_profit` |
| 6 | 2022-06-24T02:18 | 2022-06-24T03:04 | +938.21 | +0.31 | `take_profit` |
| 7 | 2022-06-24T03:36 | 2022-06-24T03:41 | +935.08 | +0.06 | `take_profit` |
| 8 | 2022-06-24T03:55 | 2022-06-24T04:04 | +944.37 | +0.07 | `take_profit` |
| 9 | 2022-06-24T04:22 | 2022-06-24T04:23 | +934.90 | +0.06 | `take_profit` |

**Straty za sebou: 25** — 2022-07-26T15:58 až 2022-07-27T13:28, spolu -13457.37.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-07-26T15:58 | 2022-07-26T16:30 | -492.33 | -0.11 | `stop_loss` |
| 2 | 2022-07-26T16:47 | 2022-07-26T16:48 | -548.78 | -0.04 | `stop_loss` |
| 3 | 2022-07-26T17:02 | 2022-07-26T17:02 | -533.35 | -0.05 | `stop_loss` |
| 4 | 2022-07-26T17:08 | 2022-07-26T17:08 | -533.39 | -0.05 | `stop_loss` |
| 5 | 2022-07-26T17:21 | 2022-07-26T17:22 | -533.57 | -0.05 | `stop_loss` |
| 6 | 2022-07-26T17:27 | 2022-07-26T17:29 | -500.71 | -0.11 | `stop_loss` |
| 7 | 2022-07-26T17:41 | 2022-07-26T18:03 | -522.41 | -0.07 | `stop_loss` |
| 8 | 2022-07-26T18:38 | 2022-07-26T18:46 | -521.87 | -0.06 | `stop_loss` |
| 9 | 2022-07-26T18:50 | 2022-07-26T18:51 | -538.15 | -0.04 | `stop_loss` |
| 10 | 2022-07-26T19:09 | 2022-07-26T19:11 | -526.78 | -0.05 | `stop_loss` |
| 11 | 2022-07-26T19:28 | 2022-07-26T19:30 | -519.72 | -0.06 | `stop_loss` |
| 12 | 2022-07-26T19:49 | 2022-07-26T19:50 | -520.48 | -0.07 | `stop_loss` |
| 13 | 2022-07-27T05:19 | 2022-07-27T05:25 | -558.25 | -0.03 | `stop_loss` |
| 14 | 2022-07-27T05:37 | 2022-07-27T05:37 | -572.68 | -0.03 | `stop_loss` |
| 15 | 2022-07-27T05:46 | 2022-07-27T05:48 | -549.49 | -0.04 | `stop_loss` |
| 16 | 2022-07-27T05:59 | 2022-07-27T06:00 | -572.63 | -0.03 | `stop_loss` |
| 17 | 2022-07-27T06:23 | 2022-07-27T06:25 | -586.24 | -0.02 | `stop_loss` |
| 18 | 2022-07-27T06:29 | 2022-07-27T06:30 | -559.54 | -0.03 | `stop_loss` |
| 19 | 2022-07-27T06:34 | 2022-07-27T06:42 | -534.03 | -0.05 | `stop_loss` |
| 20 | 2022-07-27T07:41 | 2022-07-27T07:43 | -549.52 | -0.04 | `stop_loss` |
| 21 | 2022-07-27T07:51 | 2022-07-27T07:53 | -549.52 | -0.04 | `stop_loss` |
| 22 | 2022-07-27T08:34 | 2022-07-27T08:41 | -549.58 | -0.04 | `stop_loss` |
| 23 | 2022-07-27T08:47 | 2022-07-27T09:02 | -533.89 | -0.05 | `stop_loss` |
| 24 | 2022-07-27T09:07 | 2022-07-27T09:11 | -523.65 | -0.07 | `stop_loss` |
| 25 | 2022-07-27T13:26 | 2022-07-27T13:28 | -526.81 | -0.06 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0002 %**, medián 0.0002 %, 90 % interval 0.0001–0.0004 %
- P(edge > poplatok) = **0.0 %**
- max drawdown: medián 100.0 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 24, 95. percentil 31 obchodov
- pravdepodobnosť ruiny účtu: 100.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **3** na obchod pri účte 100 000

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
<!-- POSUDOK cisla=84f632a9 -->

**Posudok (28. 10. 2026, pravidlá presne podľa podkladov METODA_2 / advanced, MNQ 1m, RR 2, EMA 20–1200).**

1. **Na čo sa hodí a na čo nie.** Podklad je ES 1m. Na 1m je M2 prakticky každých pár minút (~8 000 obchodov za rok) so stopom na pár tickov, takže poplatok je väčšia časť rizika než edge. Na takýto skalp so stopmi pod 1 bod sa pravidlá nehodia.
2. **Má potenciál?** Ako mechanické pravidlo nie. Zisková je v 0 z 5 okien a break-even je hlboko pod poplatkom. Proti náhodným vstupom je to síce odlíšiteľné (+5,3 sigma), ale edge je rádovo 0,0003 % na obchod a poplatok ho zje desaťnásobne. WR 34 % pri RR 2 zodpovedá náhode, sľubovaných 60 % sa nepotvrdilo.
3. **Čo dorobiť.** Kontext, ktorý autor používa a v texte nie je mechanicky popísaný: M2 len na začiatku impulzu, ktorý zlomil štruktúru, cieľ na likviditu či gap a order flow (absorpcia, delta, VPOC). Order flow sa z OHLCV 1m urobiť nedá.
4. **Čo otestovať ďalej.** Vyšší TF (15m–1h) s cieľom na likviditu, a M2 len po zlome swingu (ako `jss`). Rozhodne PF na 5 oknách po poplatkoch.
5. **Použiteľné?** V tejto podobe **nie**: pravidlá samy o sebe edge po nákladoch nemajú.
6. **Čo by som pridal.** Filter veľkosti M2 (minimálny rozsah v ATR), aby stop nebol v šume, a jedna M2 na impulz namiesto každej opačnej sviečky.

<!-- POSUDOK KONIEC -->
