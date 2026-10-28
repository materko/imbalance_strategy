# Základná analytika — M2 (`m2`)

Zmerané 2026-10-28 na `ES/USD` 1m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `es_databento_1m`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy m2 \
   --profile es_databento_1m \
   --pair ES/USD \
   --timeframe 1m \
   --fee 1.755e-05 \
   --wallet 100000
```

## V čom je dobrá

- 37864 obchodov spolu — na štatistiku dosť
- odlíšiteľná od náhody (+6.9 sigma proti náhodnému vstupu)
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 0 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20231001-20241001, 20240904-20250904, 20250904-20260904 v strate)
- break-even 0.0006 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 0 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 100.0 % (namerané 100.0 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 100.0 % pri riziku, s akým beh bežal
- SLABNE: posledné obdobie (2025-06 - 2026-09) má break-even +0.0003 %, pod dolnou hranicou +0.0003 % — úsek tejto dĺžky by taký zlý vyšiel len v 4 % prípadov, keby sa edge nemenil. Skôr než to vypneš: pozri `tester.regime`, či to nie je len režimom trhu.
- charakter: formácia / štruktúra (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 7948 | -262.91 | 0.0007 | 274.3 | 34.9 | +10/-19 | `20261028-152420-19c2be` |
| 20221001-20231001 | 7523 | -297.98 | 0.0007 | 284.1 | 35.1 | +8/-19 | `20261028-152424-271552` |
| 20231001-20241001 | 7312 | -298.49 | 0.0010 | 317.0 | 36.4 | +13/-19 | `20261028-152431-0087ca` |
| 20240904-20250904 | 7563 | -440.90 | 0.0006 | 358.6 | 34.3 | +8/-17 | `20261028-152434-4fd9f3` |
| 20250904-20260904 | 8030 | -596.29 | 0.0002 | 595.5 | 33.9 | +7/-23 | `20261028-152441-8436d5` |

Zisková v **0 z 5** okien, obchodov spolu 37864, break-even celkom 0.0006 %. Okná sa prekrývajú, 512 obchodov započítaných dvakrát vypadlo.

## Charakter

**Formácia / štruktúra** (istota priemerná)

- vstup bez jasného smeru pohybu (+0.23 ATR za 5 barov)
- medián držania 3 barov grafu
- winrate 34.85 %, payoff 1.604
- 21.05 obchodov za deň
- šikmosť výnosov +1.008

- **Čo je normálne:** Zmes: časť obchodov sa chová ako prerazenie, časť ako návrat. Priemer preto o jednotlivom obchode nehovorí veľa.
- **Na čo pozor:** Práve pri tomto type sa najviac oplatí rozdeliť obchody na skupiny (`tester.analytics`) — priemer skrýva dve rôzne populácie.
- **Čo ladiť:** Podmienky vstupu (ktoré modely/formácie zapnuté) a potom až výstup.

Výstupy: `stop_loss` 65.2 %, `take_profit` 34.8 %, `force_exit` 0 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0003 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| FOMC+CPI | 35 | 0.1 % | 31.4 | -0.0004 | 0.0006 | +0.0000 |
| žiadna | 33620 | 88.8 % | 34.8 | 0.0006 | 0.0009 | +0.0003 |
| FOMC | 1161 | 3.1 % | 35.4 | 0.0007 | 0.0006 | +0.0000 |
| CPI | 1672 | 4.4 % | 35.9 | 0.0009 | 0.0006 | +0.0000 |
| NFP | 1376 | 3.6 % | 34.2 | 0.0012 | 0.0006 | +0.0000 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| pred vyhlásením | 1808 | 4.8 % | 33.2 | 0.0000 | 0.0006 | +0.0000 |
| bez udalosti | 33620 | 88.8 % | 34.8 | 0.0006 | 0.0009 | +0.0003 |
| po vyhlásení | 2436 | 6.4 % | 36.6 | 0.0019 | 0.0005 | -0.0001 |

**Smer**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| short | 16201 | 42.8 % | 33.8 | 0.0003 | 0.0007 | +0.0001 |
| long | 21663 | 57.2 % | 35.6 | 0.0007 | 0.0003 | -0.0003 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0006 % | -0.0001 % ± 0.0001 | +6.90 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0006 % | -0.0001 % ± 0.0001 | +6.90 | 100.0 |

Edge je odlisitelny od nahody (6.9 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 9707 | 658.1 | 34.9 | 0.0007 | 77 |
| 2022-12 - 2024-03 | 9082 | 615.7 | 35.8 | 0.0009 | 96 |
| 2024-03 - 2025-06 | 9270 | 628.5 | 34.8 | 0.0006 | 54 |
| 2025-06 - 2026-09 | 9805 | 664.7 | 34.1 | 0.0003 | 4 |

Hranice pre úsek veľkosti posledného obdobia: +0.0003 až +0.0009 % (medián 0.0006).

**SLABNE** — posledné obdobie (2025-06 - 2026-09) má break-even +0.0003 %, pod dolnou hranicou +0.0003 % — úsek tejto dĺžky by taký zlý vyšiel len v 4 % prípadov, keby sa edge nemenil. Skôr než to vypneš: pozri `tester.regime`, či to nie je len režimom trhu.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 13** — 2024-04-18T22:11 až 2024-04-19T01:44, spolu +11439.82.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-04-18T22:11 | 2024-04-18T22:17 | +822.72 | +0.02 | `take_profit` |
| 2 | 2024-04-18T22:20 | 2024-04-18T22:25 | +822.74 | +0.02 | `take_profit` |
| 3 | 2024-04-18T22:26 | 2024-04-18T22:48 | +859.80 | +0.03 | `take_profit` |
| 4 | 2024-04-18T23:26 | 2024-04-18T23:52 | +911.47 | +0.04 | `take_profit` |
| 5 | 2024-04-18T23:55 | 2024-04-18T23:56 | +822.97 | +0.02 | `take_profit` |
| 6 | 2024-04-19T00:01 | 2024-04-19T00:07 | +846.93 | +0.06 | `take_profit` |
| 7 | 2024-04-19T00:08 | 2024-04-19T00:12 | +846.95 | +0.06 | `take_profit` |
| 8 | 2024-04-19T00:15 | 2024-04-19T00:17 | +964.66 | +0.10 | `take_profit` |
| 9 | 2024-04-19T00:23 | 2024-04-19T00:52 | +830.87 | +0.07 | `take_profit` |
| 10 | 2024-04-19T01:01 | 2024-04-19T01:04 | +955.91 | +0.08 | `take_profit` |
| 11 | 2024-04-19T01:20 | 2024-04-19T01:22 | +873.63 | +0.12 | `take_profit` |
| 12 | 2024-04-19T01:23 | 2024-04-19T01:27 | +948.65 | +0.13 | `take_profit` |
| 13 | 2024-04-19T01:41 | 2024-04-19T01:44 | +932.52 | +0.19 | `take_profit` |

**Straty za sebou: 23** — 2026-01-23T14:40 až 2026-01-26T16:45, spolu -11381.24.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-01-23T14:40 | 2026-01-23T14:42 | -312.17 | -0.09 | `stop_loss` |
| 2 | 2026-01-23T14:53 | 2026-01-23T14:56 | -299.67 | -0.09 | `stop_loss` |
| 3 | 2026-01-23T17:05 | 2026-01-23T17:42 | -499.39 | -0.07 | `stop_loss` |
| 4 | 2026-01-23T19:10 | 2026-01-23T19:11 | -560.98 | -0.03 | `stop_loss` |
| 5 | 2026-01-23T19:28 | 2026-01-23T19:29 | -523.20 | -0.03 | `stop_loss` |
| 6 | 2026-01-23T19:48 | 2026-01-23T20:08 | -399.38 | -0.06 | `stop_loss` |
| 7 | 2026-01-25T23:45 | 2026-01-25T23:46 | -498.46 | -0.04 | `stop_loss` |
| 8 | 2026-01-25T23:55 | 2026-01-25T23:57 | -548.51 | -0.04 | `stop_loss` |
| 9 | 2026-01-26T00:20 | 2026-01-26T00:26 | -486.44 | -0.05 | `stop_loss` |
| 10 | 2026-01-26T00:47 | 2026-01-26T00:55 | -498.21 | -0.03 | `stop_loss` |
| 11 | 2026-01-26T00:59 | 2026-01-26T01:02 | -448.94 | -0.04 | `stop_loss` |
| 12 | 2026-01-26T02:49 | 2026-01-26T03:00 | -560.76 | -0.03 | `stop_loss` |
| 13 | 2026-01-26T04:14 | 2026-01-26T04:17 | -621.55 | -0.02 | `stop_loss` |
| 14 | 2026-01-26T05:01 | 2026-01-26T05:18 | -621.58 | -0.02 | `stop_loss` |
| 15 | 2026-01-26T13:17 | 2026-01-26T13:25 | -498.44 | -0.03 | `stop_loss` |
| 16 | 2026-01-26T14:04 | 2026-01-26T14:20 | -498.50 | -0.03 | `stop_loss` |
| 17 | 2026-01-26T14:30 | 2026-01-26T14:30 | -498.53 | -0.03 | `stop_loss` |
| 18 | 2026-01-26T14:53 | 2026-01-26T15:01 | -548.97 | -0.04 | `stop_loss` |
| 19 | 2026-01-26T15:26 | 2026-01-26T15:27 | -561.27 | -0.03 | `stop_loss` |
| 20 | 2026-01-26T15:40 | 2026-01-26T15:42 | -449.24 | -0.04 | `stop_loss` |
| 21 | 2026-01-26T15:57 | 2026-01-26T15:59 | -498.78 | -0.03 | `stop_loss` |
| 22 | 2026-01-26T16:10 | 2026-01-26T16:17 | -499.01 | -0.04 | `stop_loss` |
| 23 | 2026-01-26T16:29 | 2026-01-26T16:45 | -449.27 | -0.04 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0006 %**, medián 0.0006 %, 90 % interval 0.0005–0.0007 %
- P(edge > poplatok) = **0.0 %**
- max drawdown: medián 100.0 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 23, 95. percentil 29 obchodov
- pravdepodobnosť ruiny účtu: 100.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **5** na obchod pri účte 100 000

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
<!-- POSUDOK cisla=29d118fb -->

**Posudok (28. 10. 2026, pravidlá presne podľa podkladov METODA_2 / advanced, ES 1m, RR 2, EMA 20–1200).**

1. **Na čo sa hodí a na čo nie.** Podklad je ES 1m. Na 1m je M2 prakticky každých pár minút (~8 000 obchodov za rok) so stopom na pár tickov, takže poplatok je väčšia časť rizika než edge. Na takýto skalp so stopmi pod 1 bod sa pravidlá nehodia.
2. **Má potenciál?** Ako mechanické pravidlo nie. Zisková je v 0 z 5 okien a break-even je hlboko pod poplatkom. Proti náhodným vstupom je to síce odlíšiteľné (+6,9 sigma), ale edge je rádovo 0,0003 % na obchod a poplatok ho zje desaťnásobne. WR 34 % pri RR 2 zodpovedá náhode, sľubovaných 60 % sa nepotvrdilo.
3. **Čo dorobiť.** Kontext, ktorý autor používa a v texte nie je mechanicky popísaný: M2 len na začiatku impulzu, ktorý zlomil štruktúru, cieľ na likviditu či gap a order flow (absorpcia, delta, VPOC). Order flow sa z OHLCV 1m urobiť nedá.
4. **Čo otestovať ďalej.** Vyšší TF (15m–1h) s cieľom na likviditu, a M2 len po zlome swingu (ako `jss`). Rozhodne PF na 5 oknách po poplatkoch.
5. **Použiteľné?** V tejto podobe **nie**: pravidlá samy o sebe edge po nákladoch nemajú.
6. **Čo by som pridal.** Filter veľkosti M2 (minimálny rozsah v ATR), aby stop nebol v šume, a jedna M2 na impulz namiesto každej opačnej sviečky.

<!-- POSUDOK KONIEC -->
