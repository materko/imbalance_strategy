# Základná analytika — WILLIAMS %R LONG 1.0 (ES) (`wpres`)

Zmerané 2026-10-31 na `ES/USD` 15m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `/Users/martin/IBS/.nightsearch/base_wpres.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy wpres \
   --profile /Users/martin/IBS/.nightsearch/base_wpres.json \
   --pair ES/USD \
   --timeframe 15m \
   --fee 1.755e-05
```

## V čom je dobrá

- 3647 obchodov spolu — na štatistiku dosť
- charakter: protitrendová (mean reversion) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 2 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20240904-20250904 v strate)
- break-even -0.0001 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 19 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 100.0 % (namerané 100.0 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 93.0 % pri riziku, s akým beh bežal
- nie je lepšia než náhodný vstup za tých istých pravidiel (-1.1 sigma) — výber vstupu nepridáva nič
- 100 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 779 | -234.00 | -0.0053 | 241.6 | 64.2 | +15/-6 | `20261031-085129-355f40` |
| 20221001-20231001 | 733 | -160.62 | -0.0035 | 139.2 | 63.3 | +15/-6 | `20261031-085136-773a41` |
| 20231001-20241001 | 723 | +125.76 | 0.0052 | 50.6 | 67.8 | +16/-5 | `20261031-085139-f4931d` |
| 20240904-20250904 | 735 | -113.28 | -0.0008 | 184.4 | 64.2 | +12/-7 | `20261031-085142-4dc297` |
| 20250904-20260904 | 732 | +53.44 | 0.0028 | 144.4 | 65.2 | +15/-7 | `20261031-085145-471a9c` |

Zisková v **2 z 5** okien, obchodov spolu 3647, break-even celkom -0.0001 %. Okná sa prekrývajú, 55 obchodov započítaných dvakrát vypadlo.

## Charakter

**Protitrendová (mean reversion)** (istota dobrá)

- vstup proti poslednému pohybu (-1.45 ATR za 5 barov)
- medián držania 3 barov grafu
- winrate 64.77 %, payoff 0.519
- 2.03 obchodov za deň
- šikmosť výnosov -3.023

- **Čo je normálne:** Winrate nad 60 % a payoff pod 1 je pri tomto type v poriadku — zarába sa frekvenciou, nie veľkosťou.
- **Na čo pozor:** Jedna strata môže zmazať mesiac. Stop je tu dôležitejší než vstup a `maxLossDollar` aj drawdown limit majú väčší význam než pri ostatných typoch.
- **Čo ladiť:** Stop a filter režimu (v trende protitrendová stratégia dostáva rany). Ladiť RR nahor väčšinou len zníži winrate a nič nepridá.

Výstupy: `session_end` 100 %, `force_exit` 0 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0051 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| sviatok v USA (Deň prezidentov) | 13 | 0.4 % | 53.9 | -0.0785 | 0.0001 | +0.0002 |
| sviatok v USA (Vďakyvzdanie) | 9 | 0.2 % | 77.8 | -0.0322 | -0.0001 | +0.0000 |
| polovičný deň (deň po Vďakyvzdaní) | 8 | 0.2 % | 37.5 | -0.0028 | -0.0001 | +0.0000 |
| bežný deň | 3380 | 92.7 % | 64.7 | -0.0006 | 0.0050 | +0.0051 |
| … | | | | | | |
| sviatok v USA (Juneteenth) | 9 | 0.2 % | 77.8 | 0.0111 | -0.0002 | -0.0001 |
| sviatok v USA (Sviatok práce) | 13 | 0.4 % | 61.5 | 0.0169 | -0.0002 | -0.0001 |
| sviatok v USA (Deň pamiatky) | 15 | 0.4 % | 80.0 | 0.0281 | -0.0003 | -0.0002 |
| sviatok v USA (Deň M. L. Kinga) | 16 | 0.4 % | 75.0 | 0.0419 | -0.0003 | -0.0002 |

**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 15 h | 900 | 24.7 % | 62.9 | -0.0083 | 0.0025 | +0.0026 |
| 6 h – 11 h | 824 | 22.6 % | 65.5 | 0.0017 | -0.0007 | -0.0006 |
| do 6 h | 1106 | 30.3 % | 65.3 | 0.0021 | -0.0011 | -0.0010 |
| 11 h – 15 h | 817 | 22.4 % | 65.4 | 0.0040 | -0.0014 | -0.0013 |

**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 9.998 % | 923 | 25.3 % | 64.0 | -0.0068 | 0.0020 | +0.0021 |
| nad 10.0024 % | 908 | 24.9 % | 62.7 | -0.0037 | 0.0010 | +0.0011 |
| 9.998 % – 10.0004 % | 957 | 26.2 % | 65.2 | 0.0008 | -0.0005 | -0.0004 |
| 10.0004 % – 10.0024 % | 859 | 23.6 % | 67.3 | 0.0088 | -0.0030 | -0.0029 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0001 % | 0.0031 % ± 0.0030 | -1.07 | 14.1 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0001 % | 0.0031 % ± 0.0030 | -1.07 | 14.1 |

HORSIE nez nahoda (-1.1 sigma). Nahodny vstup za tych istych pravidiel dava lepsi vysledok - vyber vstupu vysledku skodi.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 951 | 64.5 | 63.6 | -0.0043 | 15 |
| 2022-12 - 2024-03 | 919 | 62.3 | 66.2 | 0.0024 | 74 |
| 2024-03 - 2025-06 | 879 | 59.6 | 64.2 | -0.0027 | 27 |
| 2025-06 - 2026-09 | 898 | 60.9 | 65.1 | 0.0029 | 76 |

Hranice pre úsek veľkosti posledného obdobia: -0.0073 až +0.0069 % (medián -0.0001).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 76. percentile, teda v medziach -0.0073 až +0.0069 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 16** — 2023-11-14T03:15 až 2023-11-20T13:00, spolu +2711.09.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-11-14T03:15 | 2023-11-14T03:30 | +104.73 | +0.05 | `session_end` |
| 2 | 2023-11-14T11:15 | 2023-11-14T11:45 | +154.73 | +0.07 | `session_end` |
| 3 | 2023-11-14T12:45 | 2023-11-14T12:45 | +129.73 | +0.06 | `session_end` |
| 4 | 2023-11-15T07:15 | 2023-11-15T07:30 | +42.07 | +0.02 | `session_end` |
| 5 | 2023-11-15T09:45 | 2023-11-15T10:00 | +154.57 | +0.07 | `session_end` |
| 6 | 2023-11-15T13:45 | 2023-11-15T15:00 | +254.56 | +0.11 | `session_end` |
| 7 | 2023-11-15T18:15 | 2023-11-15T18:30 | +517.07 | +0.23 | `session_end` |
| 8 | 2023-11-15T21:15 | 2023-11-15T23:45 | +192.08 | +0.09 | `session_end` |
| 9 | 2023-11-16T02:00 | 2023-11-16T03:00 | +67.08 | +0.03 | `session_end` |
| 10 | 2023-11-16T12:30 | 2023-11-16T13:30 | +392.08 | +0.17 | `session_end` |
| 11 | 2023-11-16T16:30 | 2023-11-16T16:45 | +192.09 | +0.09 | `session_end` |
| 12 | 2023-11-17T05:30 | 2023-11-17T05:45 | +29.56 | +0.01 | `session_end` |
| 13 | 2023-11-17T07:15 | 2023-11-17T08:00 | +167.06 | +0.07 | `session_end` |
| 14 | 2023-11-19T23:30 | 2023-11-19T23:45 | +167.06 | +0.07 | `session_end` |
| 15 | 2023-11-20T06:00 | 2023-11-20T07:00 | +79.57 | +0.04 | `session_end` |
| 16 | 2023-11-20T12:45 | 2023-11-20T13:00 | +67.06 | +0.03 | `session_end` |

**Straty za sebou: 7** — 2025-02-21T04:30 až 2025-02-25T08:00, spolu -5499.41, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-02-21T04:30 | 2025-02-21T05:30 | -73.26 | -0.02 | `session_end` |
| 2 | 2025-02-21T14:30 | 2025-02-21T16:00 | -1548.24 | -0.50 | `session_end` |
| 3 | 2025-02-21T17:30 | 2025-02-21T20:15 | -2610.64 | -0.86 | `session_end` |
| 4 | 2025-02-24T07:30 | 2025-02-24T08:30 | -110.62 | -0.04 | `session_end` |
| 5 | 2025-02-24T15:00 | 2025-02-24T16:00 | -160.56 | -0.05 | `session_end` |
| 6 | 2025-02-24T20:30 | 2025-02-25T00:00 | -785.55 | -0.26 | `session_end` |
| 7 | 2025-02-25T06:30 | 2025-02-25T08:00 | -210.54 | -0.07 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0001 %**, medián -0.0002 %, 90 % interval -0.0038–0.0034 %
- P(edge > poplatok) = **19.4 %**
- max drawdown: medián 100.0 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 7, 95. percentil 9 obchodov
- pravdepodobnosť ruiny účtu: 93.0 %

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
<!-- POSUDOK cisla=bd54b519 -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na ES, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Protitrendový long po prepade %R, výstup pri prvom odraze; vysoký WR, nízky payoff — na indexoch citlivý na trend dole (bez stopu). Tu na ES — rovnaká logika ako MNQ, prahy v ATR sa prispôsobia.
2. **Má potenciál?** Zisková v 2 z 5 okien, 3647 obchodov (~729 za rok), break-even -0.0001 % (pod poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 64.77 % pri payoffe 0.519. Odložený rok 25/26: +53.44 % PnL, break-even 0.0028 %. Kladné okná sú skôr vlastnosť vzorky ako stabilný jav.
3. **Čo dorobiť.** Stop: predloha bez stopu, jeden prepad (2022) zmaže roky; povinne `stopPct` alebo ATR stop a filter trendu (len nad EMA 200).
4. **Čo otestovať ďalej.** Smernica (`wpr*`: TF, perióda, prahy vstupu a výstupu, stop, trend); rozhodne, či s filtrom trendu ostane edge nad poplatkom.
5. **Použiteľné?** **V defaultoch predlohy nie** — edge nad poplatkom nie je stabilný po rokoch; šancu má len s nastavením, ktoré nájde smernica (inak vyradiť).
6. **Čo by som pridal.** Len long nad EMA 200 dňa a výstup na %R −50 — klasická Connorsova úprava RSI(2)/%R stratégií.

<!-- POSUDOK KONIEC -->
