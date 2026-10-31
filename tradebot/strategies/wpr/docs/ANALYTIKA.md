# Základná analytika — WILLIAMS %R LONG 1.0 (`wpr`)

Zmerané 2026-10-31 na `MNQ/USD` 15m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `/Users/martin/IBS/.nightsearch/base_wpr.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy wpr \
   --profile /Users/martin/IBS/.nightsearch/base_wpr.json \
   --pair MNQ/USD \
   --timeframe 15m \
   --fee 1.755e-05
```

## V čom je dobrá

- 3545 obchodov spolu — na štatistiku dosť
- charakter: protitrendová (mean reversion) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 3 z 5 referenčných okien (20211001-20221001, 20250904-20260904 v strate)
- break-even -0.0005 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 25 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 100.0 % (namerané 92.1 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 44.1 % pri riziku, s akým beh bežal
- nie je lepšia než náhodný vstup za tých istých pravidiel (-1.0 sigma) — výber vstupu nepridáva nič
- 100 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 756 | -83.23 | -0.0182 | 88.1 | 62.4 | +9/-6 | `20261031-085119-20d1ee` |
| 20221001-20231001 | 755 | +19.34 | 0.0066 | 12.9 | 65.8 | +17/-11 | `20261031-085122-973226` |
| 20231001-20241001 | 698 | +21.47 | 0.0061 | 20.3 | 66.2 | +14/-7 | `20261031-085126-aff8c0` |
| 20240904-20250904 | 686 | +14.21 | 0.0042 | 46.5 | 68.1 | +12/-3 | `20261031-085129-2da202` |
| 20250904-20260904 | 702 | -18.07 | -0.0007 | 48.4 | 62.1 | +13/-5 | `20261031-085132-478b62` |

Zisková v **3 z 5** okien, obchodov spolu 3545, break-even celkom -0.0005 %. Okná sa prekrývajú, 52 obchodov započítaných dvakrát vypadlo.

## Charakter

**Protitrendová (mean reversion)** (istota dobrá)

- vstup proti poslednému pohybu (-1.45 ATR za 5 barov)
- medián držania 3 barov grafu
- winrate 64.65 %, payoff 0.525
- 1.97 obchodov za deň
- šikmosť výnosov -3.057

- **Čo je normálne:** Winrate nad 60 % a payoff pod 1 je pri tomto type v poriadku — zarába sa frekvenciou, nie veľkosťou.
- **Na čo pozor:** Jedna strata môže zmazať mesiac. Stop je tu dôležitejší než vstup a `maxLossDollar` aj drawdown limit majú väčší význam než pri ostatných typoch.
- **Čo ladiť:** Stop a filter režimu (v trende protitrendová stratégia dostáva rany). Ladiť RR nahor väčšinou len zníži winrate a nič nepridá.

Výstupy: `session_end` 100 %, `force_exit` 0 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0025 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Volatilita voči normálu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.766 | 890 | 25.1 % | 65.6 | -0.0080 | 0.0020 | +0.0025 |
| 1.011 – 1.461 | 885 | 25.0 % | 61.7 | -0.0048 | 0.0010 | +0.0015 |
| 0.766 – 1.011 | 884 | 24.9 % | 66.7 | -0.0020 | -0.0000 | +0.0005 |
| nad 1.461 | 886 | 25.0 % | 64.6 | 0.0132 | -0.0050 | -0.0045 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.1877 – 0.5025 | 885 | 25.0 % | 66.3 | -0.0078 | 0.0020 | +0.0025 |
| do 0.0441 | 889 | 25.1 % | 61.2 | -0.0070 | 0.0016 | +0.0021 |
| nad 0.5025 | 886 | 25.0 % | 67.7 | 0.0061 | -0.0027 | -0.0022 |
| 0.0441 – 0.1877 | 885 | 25.0 % | 63.4 | 0.0070 | -0.0029 | -0.0024 |

**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 11 h – 15 h | 810 | 22.8 % | 65.2 | -0.0083 | 0.0018 | +0.0023 |
| nad 15 h | 880 | 24.8 % | 63.2 | -0.0004 | -0.0005 | +0.0000 |
| do 6 h | 1044 | 29.4 % | 65.7 | 0.0022 | -0.0016 | -0.0011 |
| 6 h – 11 h | 811 | 22.9 % | 64.4 | 0.0036 | -0.0017 | -0.0012 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0005 % | 0.0034 % ± 0.0039 | -1.00 | 15.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0005 % | 0.0034 % ± 0.0039 | -1.00 | 15.0 |

HORSIE nez nahoda (-1.0 sigma). Nahodny vstup za tych istych pravidiel dava lepsi vysledok - vyber vstupu vysledku skodi.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 939 | 63.7 | 62.3 | -0.0136 | 3 |
| 2022-12 - 2024-03 | 913 | 61.9 | 66.7 | 0.0066 | 88 |
| 2024-03 - 2025-06 | 828 | 56.1 | 66.7 | 0.0009 | 53 |
| 2025-06 - 2026-09 | 865 | 58.6 | 63.1 | 0.0015 | 60 |

Hranice pre úsek veľkosti posledného obdobia: -0.0116 až +0.0098 % (medián -0.0002).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 60. percentile, teda v medziach -0.0116 až +0.0098 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 17** — 2023-05-12T18:00 až 2023-05-22T11:30, spolu +609.20.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-05-12T18:00 | 2023-05-12T18:45 | +45.06 | +0.17 | `session_end` |
| 2 | 2023-05-15T14:00 | 2023-05-15T14:30 | +34.06 | +0.13 | `session_end` |
| 3 | 2023-05-16T13:00 | 2023-05-16T13:30 | +132.55 | +0.49 | `session_end` |
| 4 | 2023-05-16T20:00 | 2023-05-16T20:15 | +41.55 | +0.15 | `session_end` |
| 5 | 2023-05-17T05:30 | 2023-05-17T05:45 | +5.55 | +0.02 | `session_end` |
| 6 | 2023-05-17T07:30 | 2023-05-17T08:00 | +40.05 | +0.15 | `session_end` |
| 7 | 2023-05-17T14:00 | 2023-05-17T14:15 | +70.05 | +0.26 | `session_end` |
| 8 | 2023-05-18T01:00 | 2023-05-18T02:00 | +11.54 | +0.04 | `session_end` |
| 9 | 2023-05-18T07:00 | 2023-05-18T07:00 | +36.54 | +0.13 | `session_end` |
| 10 | 2023-05-18T13:00 | 2023-05-18T13:15 | +28.04 | +0.10 | `session_end` |
| 11 | 2023-05-19T06:00 | 2023-05-19T06:15 | +24.52 | +0.09 | `session_end` |
| 12 | 2023-05-19T07:00 | 2023-05-19T07:45 | +13.02 | +0.05 | `session_end` |
| 13 | 2023-05-19T11:00 | 2023-05-19T11:00 | +26.52 | +0.10 | `session_end` |
| 14 | 2023-05-19T12:15 | 2023-05-19T12:30 | +30.02 | +0.11 | `session_end` |
| 15 | 2023-05-19T15:30 | 2023-05-19T15:45 | +15.03 | +0.05 | `session_end` |
| 16 | 2023-05-19T18:15 | 2023-05-19T18:45 | +43.53 | +0.16 | `session_end` |
| 17 | 2023-05-22T10:00 | 2023-05-22T11:30 | +11.53 | +0.04 | `session_end` |

**Straty za sebou: 11** — 2022-12-15T01:45 až 2022-12-20T05:00, spolu -917.31.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-12-15T01:45 | 2022-12-15T03:15 | -18.33 | -0.08 | `session_end` |
| 2 | 2022-12-15T07:30 | 2022-12-15T10:30 | -214.33 | -0.91 | `session_end` |
| 3 | 2022-12-15T15:00 | 2022-12-15T19:30 | -204.81 | -0.88 | `session_end` |
| 4 | 2022-12-16T05:00 | 2022-12-16T05:30 | -1.30 | -0.01 | `session_end` |
| 5 | 2022-12-16T08:00 | 2022-12-16T09:45 | -124.80 | -0.55 | `session_end` |
| 6 | 2022-12-16T15:15 | 2022-12-16T17:15 | -97.30 | -0.43 | `session_end` |
| 7 | 2022-12-19T05:00 | 2022-12-19T06:00 | -24.80 | -0.11 | `session_end` |
| 8 | 2022-12-19T13:15 | 2022-12-19T15:15 | -146.30 | -0.64 | `session_end` |
| 9 | 2022-12-19T16:00 | 2022-12-19T17:00 | -4.29 | -0.02 | `session_end` |
| 10 | 2022-12-19T19:00 | 2022-12-19T20:45 | -8.79 | -0.04 | `session_end` |
| 11 | 2022-12-20T03:15 | 2022-12-20T05:00 | -72.28 | -0.33 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0005 %**, medián -0.0004 %, 90 % interval -0.0059–0.0047 %
- P(edge > poplatok) = **24.5 %**
- max drawdown: medián 92.1 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 8, 95. percentil 12 obchodov
- pravdepodobnosť ruiny účtu: 44.1 %

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
<!-- POSUDOK cisla=2f0c9eff -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na MNQ, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Protitrendový long po prepade %R, výstup pri prvom odraze; vysoký WR, nízky payoff — na indexoch citlivý na trend dole (bez stopu).
2. **Má potenciál?** Zisková v 3 z 5 okien, 3545 obchodov (~709 za rok), break-even -0.0005 % (pod poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 64.65 % pri payoffe 0.525. Odložený rok 25/26: -18.07 % PnL, break-even -0.0007 %. Kladné okná sú skôr vlastnosť vzorky ako stabilný jav.
3. **Čo dorobiť.** Stop: predloha bez stopu, jeden prepad (2022) zmaže roky; povinne `stopPct` alebo ATR stop a filter trendu (len nad EMA 200).
4. **Čo otestovať ďalej.** Smernica (`wpr*`: TF, perióda, prahy vstupu a výstupu, stop, trend); rozhodne, či s filtrom trendu ostane edge nad poplatkom.
5. **Použiteľné?** **V defaultoch predlohy nie** — edge nad poplatkom nie je stabilný po rokoch; šancu má len s nastavením, ktoré nájde smernica (inak vyradiť).
6. **Čo by som pridal.** Len long nad EMA 200 dňa a výstup na %R −50 — klasická Connorsova úprava RSI(2)/%R stratégií.

<!-- POSUDOK KONIEC -->
