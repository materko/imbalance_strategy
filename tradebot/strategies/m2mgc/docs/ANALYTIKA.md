# Základná analytika — M2 (MGC) (`m2mgc`)

Zmerané 2026-10-28 na `MGC/USD` 1m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `mgc_databento_1m`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy m2mgc \
   --profile mgc_databento_1m \
   --pair MGC/USD \
   --timeframe 1m \
   --fee 1.755e-05 \
   --wallet 100000
```

## V čom je dobrá

- 42956 obchodov spolu — na štatistiku dosť
- odlíšiteľná od náhody (+3.4 sigma proti náhodnému vstupu)
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 0 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20231001-20241001, 20240904-20250904, 20250904-20260904 v strate)
- break-even -0.0001 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 0 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 100.0 % (namerané 100.0 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 100.0 % pri riziku, s akým beh bežal
- charakter: formácia / štruktúra (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 8993 | -897.04 | -0.0003 | 899.6 | 30.7 | +8/-21 | `20261028-152638-343eeb` |
| 20221001-20231001 | 8439 | -807.79 | -0.0001 | 812.1 | 31.8 | +6/-27 | `20261028-152642-922d19` |
| 20231001-20241001 | 8729 | -869.07 | -0.0003 | 819.4 | 31.5 | +9/-23 | `20261028-152648-ea43b1` |
| 20240904-20250904 | 8743 | -598.50 | 0.0000 | 596.9 | 33.0 | +8/-22 | `20261028-152655-cf83d4` |
| 20250904-20260904 | 8698 | -274.10 | 0.0005 | 291.6 | 33.7 | +8/-19 | `20261028-152702-be9a2e` |

Zisková v **0 z 5** okien, obchodov spolu 42956, break-even celkom -0.0001 %. Okná sa prekrývajú, 646 obchodov započítaných dvakrát vypadlo.

## Charakter

**Formácia / štruktúra** (istota priemerná)

- vstup bez jasného smeru pohybu (+0.00 ATR za 5 barov)
- medián držania 2 barov grafu
- winrate 32.13 %, payoff 1.676
- 23.88 obchodov za deň
- šikmosť výnosov +2.476

- **Čo je normálne:** Zmes: časť obchodov sa chová ako prerazenie, časť ako návrat. Priemer preto o jednotlivom obchode nehovorí veľa.
- **Na čo pozor:** Práve pri tomto type sa najviac oplatí rozdeliť obchody na skupiny (`tester.analytics`) — priemer skrýva dve rôzne populácie.
- **Čo ladiť:** Podmienky vstupu (ktoré modely/formácie zapnuté) a potom až výstup.

Výstupy: `stop_loss` 67.9 %, `take_profit` 32.1 %, `force_exit` 0 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0002 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Plánovaný RR**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 2 R | 40124 | 93.9 % | 32.9 | -0.0001 | 0.0001 | +0.0002 |
| nad 2 R | 2589 | 6.1 % | 23.3 | 0.0001 | -0.0001 | +0.0000 |

**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 6 h – 11 h | 9401 | 21.9 % | 31.4 | -0.0004 | -0.0000 | +0.0001 |
| do 6 h | 12313 | 28.7 % | 31.6 | -0.0002 | -0.0001 | +0.0000 |
| 11 h – 17 h | 12022 | 28.0 % | 32.9 | -0.0000 | -0.0001 | +0.0000 |
| nad 17 h | 9220 | 21.5 % | 32.6 | 0.0002 | -0.0002 | -0.0001 |

**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 0.1963 | 10731 | 25.0 % | 32.1 | -0.0003 | -0.0000 | +0.0001 |
| 0.1167 – 0.1963 | 10731 | 25.0 % | 31.9 | -0.0002 | -0.0001 | +0.0000 |
| 0.0545 – 0.1167 | 10727 | 25.0 % | 31.9 | -0.0001 | -0.0001 | +0.0000 |
| do 0.0545 | 10767 | 25.1 % | 32.6 | 0.0001 | -0.0002 | -0.0001 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0003 % | -0.0001 % ± 0.0001 | +3.42 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0003 % | -0.0001 % ± 0.0001 | +3.42 | 100.0 |

Edge je odlisitelny od nahody (3.4 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 11002 | 745.9 | 31.2 | -0.0002 | 25 |
| 2022-12 - 2024-03 | 10352 | 701.8 | 31.2 | -0.0003 | 12 |
| 2024-03 - 2025-06 | 10846 | 735.3 | 32.3 | -0.0001 | 48 |
| 2025-06 - 2026-09 | 10756 | 729.2 | 33.8 | 0.0005 | 100 |

Hranice pre úsek veľkosti posledného obdobia: -0.0004 až +0.0002 % (medián -0.0001).

**ZLEPSUJE SA** — posledné obdobie (2025-06 - 2026-09) je nad hornou hranicou +0.0002 %. Pozor na opačnú chybu — dôvod zvyšovať riziko to nie je, rovnako dobre to môže byť priaznivý režim.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 9** — 2024-05-10T04:55 až 2024-05-10T08:26, spolu +8185.71.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-05-10T04:55 | 2024-05-10T04:56 | +792.87 | +0.01 | `take_profit` |
| 2 | 2024-05-10T05:13 | 2024-05-10T05:17 | +896.38 | +0.03 | `take_profit` |
| 3 | 2024-05-10T05:20 | 2024-05-10T05:22 | +896.36 | +0.03 | `take_profit` |
| 4 | 2024-05-10T06:00 | 2024-05-10T06:11 | +949.97 | +0.10 | `take_profit` |
| 5 | 2024-05-10T06:14 | 2024-05-10T06:16 | +935.01 | +0.06 | `take_profit` |
| 6 | 2024-05-10T06:19 | 2024-05-10T06:42 | +950.89 | +0.11 | `take_profit` |
| 7 | 2024-05-10T07:17 | 2024-05-10T07:27 | +944.16 | +0.07 | `take_profit` |
| 8 | 2024-05-10T07:45 | 2024-05-10T08:18 | +962.50 | +0.12 | `take_profit` |
| 9 | 2024-05-10T08:25 | 2024-05-10T08:26 | +857.58 | +0.02 | `take_profit` |

**Straty za sebou: 27** — 2023-05-23T18:39 až 2023-05-24T11:17, spolu -15421.13.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-05-23T18:39 | 2023-05-23T18:39 | -555.65 | -0.03 | `stop_loss` |
| 2 | 2023-05-23T18:50 | 2023-05-23T18:53 | -539.05 | -0.04 | `stop_loss` |
| 3 | 2023-05-23T18:56 | 2023-05-23T19:00 | -613.25 | -0.02 | `stop_loss` |
| 4 | 2023-05-23T19:32 | 2023-05-23T19:35 | -586.73 | -0.02 | `stop_loss` |
| 5 | 2023-05-23T19:56 | 2023-05-23T19:59 | -613.19 | -0.02 | `stop_loss` |
| 6 | 2023-05-23T20:27 | 2023-05-23T20:34 | -447.19 | -0.01 | `stop_loss` |
| 7 | 2023-05-23T20:58 | 2023-05-23T22:00 | -613.19 | -0.02 | `stop_loss` |
| 8 | 2023-05-23T22:13 | 2023-05-23T22:17 | -613.23 | -0.02 | `stop_loss` |
| 9 | 2023-05-23T22:25 | 2023-05-23T22:34 | -613.22 | -0.02 | `stop_loss` |
| 10 | 2023-05-23T22:59 | 2023-05-23T22:59 | -281.27 | -0.01 | `stop_loss` |
| 11 | 2023-05-23T23:07 | 2023-05-23T23:19 | -613.26 | -0.02 | `stop_loss` |
| 12 | 2023-05-23T23:42 | 2023-05-23T23:51 | -613.20 | -0.02 | `stop_loss` |
| 13 | 2023-05-24T00:37 | 2023-05-24T00:42 | -673.57 | -0.01 | `stop_loss` |
| 14 | 2023-05-24T04:09 | 2023-05-24T04:09 | -673.60 | -0.01 | `stop_loss` |
| 15 | 2023-05-24T04:46 | 2023-05-24T04:46 | -423.71 | -0.01 | `stop_loss` |
| 16 | 2023-05-24T04:53 | 2023-05-24T05:00 | -613.33 | -0.02 | `stop_loss` |
| 17 | 2023-05-24T05:16 | 2023-05-24T05:17 | -613.36 | -0.02 | `stop_loss` |
| 18 | 2023-05-24T05:26 | 2023-05-24T05:26 | -423.70 | -0.01 | `stop_loss` |
| 19 | 2023-05-24T05:39 | 2023-05-24T05:40 | -613.37 | -0.02 | `stop_loss` |
| 20 | 2023-05-24T05:44 | 2023-05-24T05:47 | -569.50 | -0.03 | `stop_loss` |
| 21 | 2023-05-24T06:02 | 2023-05-24T06:03 | -673.76 | -0.01 | `stop_loss` |
| 22 | 2023-05-24T06:16 | 2023-05-24T06:19 | -546.30 | -0.04 | `stop_loss` |
| 23 | 2023-05-24T10:12 | 2023-05-24T10:16 | -569.40 | -0.03 | `stop_loss` |
| 24 | 2023-05-24T10:32 | 2023-05-24T10:33 | -555.58 | -0.03 | `stop_loss` |
| 25 | 2023-05-24T10:45 | 2023-05-24T10:47 | -569.41 | -0.03 | `stop_loss` |
| 26 | 2023-05-24T11:07 | 2023-05-24T11:08 | -613.29 | -0.02 | `stop_loss` |
| 27 | 2023-05-24T11:16 | 2023-05-24T11:17 | -586.82 | -0.02 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0001 %**, medián -0.0001 %, 90 % interval -0.0002–0.0000 %
- P(edge > poplatok) = **0.0 %**
- max drawdown: medián 100.0 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 25, 95. percentil 32 obchodov
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
<!-- POSUDOK cisla=94bb3521 -->

**Posudok (28. 10. 2026, pravidlá presne podľa podkladov METODA_2 / advanced, MGC 1m, RR 2, EMA 20–1200).**

1. **Na čo sa hodí a na čo nie.** Podklad je ES 1m. Na 1m je M2 prakticky každých pár minút (~8 000 obchodov za rok) so stopom na pár tickov, takže poplatok je väčšia časť rizika než edge. Na takýto skalp so stopmi pod 1 bod sa pravidlá nehodia.
2. **Má potenciál?** Ako mechanické pravidlo nie. Zisková je v 0 z 5 okien a break-even je hlboko pod poplatkom. Proti náhodným vstupom je to síce odlíšiteľné (+3,4 sigma), ale edge je rádovo 0,0003 % na obchod a poplatok ho zje desaťnásobne. WR 34 % pri RR 2 zodpovedá náhode, sľubovaných 60 % sa nepotvrdilo.
3. **Čo dorobiť.** Kontext, ktorý autor používa a v texte nie je mechanicky popísaný: M2 len na začiatku impulzu, ktorý zlomil štruktúru, cieľ na likviditu či gap a order flow (absorpcia, delta, VPOC). Order flow sa z OHLCV 1m urobiť nedá.
4. **Čo otestovať ďalej.** Vyšší TF (15m–1h) s cieľom na likviditu, a M2 len po zlome swingu (ako `jss`). Rozhodne PF na 5 oknách po poplatkoch.
5. **Použiteľné?** V tejto podobe **nie**: pravidlá samy o sebe edge po nákladoch nemajú.
6. **Čo by som pridal.** Filter veľkosti M2 (minimálny rozsah v ATR), aby stop nebol v šume, a jedna M2 na impulz namiesto každej opačnej sviečky.

<!-- POSUDOK KONIEC -->
