# Základná analytika — WILLIAMS %R LONG 1.0 (MGC) (`wprmgc`)

Zmerané 2026-10-31 na `MGC/USD` 15m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `/Users/martin/IBS/.nightsearch/base_wprmgc.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy wprmgc \
   --profile /Users/martin/IBS/.nightsearch/base_wprmgc.json \
   --pair MGC/USD \
   --timeframe 15m \
   --fee 1.755e-05
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 3633 obchodov spolu — na štatistiku dosť
- break-even 0.0060 % je nad poplatkom 0.0018 % (rezerva +0.0042 bodu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 60. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: protitrendová (mean reversion) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- edge nad poplatkom len v 90 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 74.3 % (namerané 31.1 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 1.3 % pri riziku, s akým beh bežal
- proti náhode len +0.4 sigma: náznak, nie dôkaz
- 100 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 833 | +17.37 | 0.0075 | 5.8 | 67.5 | +12/-5 | `20261031-085129-306009` |
| 20221001-20231001 | 798 | +9.48 | 0.0049 | 5.0 | 64.9 | +12/-5 | `20261031-085133-e35694` |
| 20231001-20241001 | 701 | +8.99 | 0.0046 | 7.7 | 65.6 | +9/-4 | `20261031-085136-dfdc40` |
| 20240904-20250904 | 702 | +21.57 | 0.0069 | 15.3 | 69.4 | +18/-5 | `20261031-085139-e5e996` |
| 20250904-20260904 | 652 | +24.02 | 0.0059 | 37.8 | 65.5 | +20/-5 | `20261031-085142-05410b` |

Zisková v **5 z 5** okien, obchodov spolu 3633, break-even celkom 0.0060 %. Okná sa prekrývajú, 53 obchodov započítaných dvakrát vypadlo.

## Charakter

**Protitrendová (mean reversion)** (istota dobrá)

- vstup proti poslednému pohybu (-1.40 ATR za 5 barov)
- medián držania 3 barov grafu
- winrate 66.47 %, payoff 0.553
- 2.02 obchodov za deň
- šikmosť výnosov -3.665

- **Čo je normálne:** Winrate nad 60 % a payoff pod 1 je pri tomto type v poriadku — zarába sa frekvenciou, nie veľkosťou.
- **Na čo pozor:** Jedna strata môže zmazať mesiac. Stop je tu dôležitejší než vstup a `maxLossDollar` aj drawdown limit majú väčší význam než pri ostatných typoch.
- **Čo ladiť:** Stop a filter režimu (v trende protitrendová stratégia dostáva rany). Ladiť RR nahor väčšinou len zníži winrate a nič nepridá.

Výstupy: `session_end` 100 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0059 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 5 h | 1043 | 28.7 % | 63.2 | -0.0088 | 0.0119 | +0.0059 |
| nad 15 h | 892 | 24.6 % | 67.5 | 0.0090 | 0.0050 | -0.0010 |
| 10 h – 15 h | 849 | 23.4 % | 68.1 | 0.0117 | 0.0042 | -0.0018 |
| 5 h – 10 h | 849 | 23.4 % | 67.8 | 0.0153 | 0.0032 | -0.0028 |

**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| proti trendu | 2320 | 63.9 % | 66.1 | 0.0028 | 0.0115 | +0.0055 |
| s trendom | 1313 | 36.1 % | 67.2 | 0.0115 | 0.0028 | -0.0032 |

**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 10.0037 % | 908 | 25.0 % | 64.1 | -0.0017 | 0.0083 | +0.0023 |
| do 9.9968 % | 909 | 25.0 % | 66.0 | 0.0072 | 0.0056 | -0.0004 |
| 10 % – 10.0037 % | 876 | 24.1 % | 70.8 | 0.0073 | 0.0055 | -0.0005 |
| 9.9968 % – 10 % | 940 | 25.9 % | 65.2 | 0.0103 | 0.0044 | -0.0016 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0060 % | 0.0042 % ± 0.0043 | +0.42 | 67.5 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0060 % | 0.0042 % ± 0.0043 | +0.42 | 67.5 |

Neodlisitelne od nahody (+0.4 sigma, percentil 67.5). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 1024 | 69.4 | 66.6 | 0.0077 | 61 |
| 2022-12 - 2024-03 | 948 | 64.3 | 65.5 | 0.0047 | 38 |
| 2024-03 - 2025-06 | 830 | 56.3 | 68.5 | 0.0027 | 27 |
| 2025-06 - 2026-09 | 831 | 56.3 | 65.3 | 0.0078 | 60 |

Hranice pre úsek veľkosti posledného obdobia: -0.0059 až +0.0159 % (medián 0.0063).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 60. percentile, teda v medziach -0.0059 až +0.0159 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 20** — 2026-01-08T12:15 až 2026-01-22T10:00, spolu +1818.45.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-01-08T12:15 | 2026-01-08T12:30 | +164.45 | +0.37 | `session_end` |
| 2 | 2026-01-08T19:15 | 2026-01-08T19:30 | +39.44 | +0.09 | `session_end` |
| 3 | 2026-01-09T12:30 | 2026-01-09T13:30 | +188.43 | +0.42 | `session_end` |
| 4 | 2026-01-12T20:45 | 2026-01-12T21:45 | +54.38 | +0.12 | `session_end` |
| 5 | 2026-01-13T02:00 | 2026-01-13T02:00 | +87.39 | +0.19 | `session_end` |
| 6 | 2026-01-13T18:00 | 2026-01-13T18:30 | +96.38 | +0.21 | `session_end` |
| 7 | 2026-01-14T23:30 | 2026-01-14T23:45 | +54.38 | +0.12 | `session_end` |
| 8 | 2026-01-15T01:30 | 2026-01-15T02:00 | +129.38 | +0.28 | `session_end` |
| 9 | 2026-01-15T13:45 | 2026-01-15T14:00 | +102.39 | +0.22 | `session_end` |
| 10 | 2026-01-16T00:45 | 2026-01-16T01:00 | +21.38 | +0.05 | `session_end` |
| 11 | 2026-01-16T13:15 | 2026-01-16T13:30 | +17.38 | +0.04 | `session_end` |
| 12 | 2026-01-16T15:30 | 2026-01-16T15:45 | +65.40 | +0.14 | `session_end` |
| 13 | 2026-01-19T10:45 | 2026-01-19T11:15 | +49.36 | +0.11 | `session_end` |
| 14 | 2026-01-19T12:00 | 2026-01-19T12:15 | +98.36 | +0.21 | `session_end` |
| 15 | 2026-01-19T23:30 | 2026-01-20T00:00 | +19.36 | +0.04 | `session_end` |
| 16 | 2026-01-20T01:00 | 2026-01-20T01:00 | +82.36 | +0.18 | `session_end` |
| 17 | 2026-01-21T07:15 | 2026-01-21T07:45 | +172.30 | +0.36 | `session_end` |
| 18 | 2026-01-21T17:15 | 2026-01-21T17:45 | +86.31 | +0.18 | `session_end` |
| 19 | 2026-01-21T19:45 | 2026-01-21T20:00 | +213.32 | +0.45 | `session_end` |
| 20 | 2026-01-22T09:45 | 2026-01-22T10:00 | +76.31 | +0.16 | `session_end` |

**Straty za sebou: 5** — 2022-04-26T18:00 až 2022-04-28T02:45, spolu -121.32, rovnako dlhých sérií 7.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-04-26T18:00 | 2022-04-26T19:15 | -11.67 | -0.06 | `session_end` |
| 2 | 2022-04-27T01:15 | 2022-04-27T04:45 | -37.67 | -0.20 | `session_end` |
| 3 | 2022-04-27T13:30 | 2022-04-27T16:00 | -45.66 | -0.24 | `session_end` |
| 4 | 2022-04-27T19:45 | 2022-04-27T20:30 | -1.66 | -0.01 | `session_end` |
| 5 | 2022-04-27T22:45 | 2022-04-28T02:45 | -24.66 | -0.13 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0060 %**, medián 0.0061 %, 90 % interval 0.0005–0.0112 %
- P(edge > poplatok) = **90.2 %**
- max drawdown: medián 31.1 %, 95. percentil 74.3 %, najhorší 100.0 %
- najdlhšia séria strát: medián 6, 95. percentil 8 obchodov
- pravdepodobnosť ruiny účtu: 1.3 %

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
<!-- POSUDOK cisla=c7396f92 -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na MGC, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Protitrendový long po prepade %R, výstup pri prvom odraze; vysoký WR, nízky payoff — na indexoch citlivý na trend dole (bez stopu). Tu na MGC (zlato) — logika robená pre index, čísla to treba brať ako test prenosu.
2. **Má potenciál?** Zisková v 5 z 5 okien, 3633 obchodov (~727 za rok), break-even 0.0060 % (nad poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 66.47 % pri payoffe 0.553. Odložený rok 25/26: +24.02 % PnL, break-even 0.0059 %. Jav je skôr skutočný ako vlastnosť vzorky.
3. **Čo dorobiť.** Stop: predloha bez stopu, jeden prepad (2022) zmaže roky; povinne `stopPct` alebo ATR stop a filter trendu (len nad EMA 200).
4. **Čo otestovať ďalej.** Smernica (`wpr*`: TF, perióda, prahy vstupu a výstupu, stop, trend); rozhodne, či s filtrom trendu ostane edge nad poplatkom.
5. **Použiteľné?** **Áno ako kandidát do smernice** — defaulty predlohy sú ziskové vo väčšine okien a edge je nad poplatkom; rozhodne hľadanie a odložený rok.
6. **Čo by som pridal.** Len long nad EMA 200 dňa a výstup na %R −50 — klasická Connorsova úprava RSI(2)/%R stratégií.

<!-- POSUDOK KONIEC -->
