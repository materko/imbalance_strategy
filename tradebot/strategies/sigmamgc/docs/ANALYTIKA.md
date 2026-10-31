# Základná analytika — SIGMA BREAKOUT 1.0 (MGC) (`sigmamgc`)

Zmerané 2026-10-31 na `MGC/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `/Users/martin/IBS/.nightsearch/base_sigmamgc.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy sigmamgc \
   --profile /Users/martin/IBS/.nightsearch/base_sigmamgc.json \
   --pair MGC/USD \
   --timeframe 5m \
   --fee 1.755e-05
```

## V čom je dobrá

- 1819 obchodov spolu — na štatistiku dosť

## Kde má chyby

- zisková v 1 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20231001-20241001, 20250904-20260904 v strate)
- break-even -0.0031 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 27 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 100.0 % (namerané 85.9 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 39.1 % pri riziku, s akým beh bežal
- nie je lepšia než náhodný vstup za tých istých pravidiel (-0.3 sigma) — výber vstupu nepridáva nič
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- 100 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 'streda' vlastnosti 'Deň v týždni': 421 obchodov (23.1 %), bez nej by break-even bol o +0.0103 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 367 | -5.02 | -0.0020 | 15.5 | 43.6 | +4/-7 | `20261031-084904-e18573` |
| 20221001-20231001 | 359 | -1.90 | 0.0004 | 12.1 | 44.3 | +6/-8 | `20261031-084907-595e1f` |
| 20231001-20241001 | 372 | -3.97 | -0.0006 | 15.9 | 45.2 | +7/-10 | `20261031-084913-e72932` |
| 20240904-20250904 | 343 | +14.65 | 0.0088 | 15.3 | 49.6 | +6/-8 | `20261031-084919-134857` |
| 20250904-20260904 | 388 | -50.89 | -0.0130 | 70.7 | 41.0 | +10/-8 | `20261031-084925-a16f75` |

Zisková v **1 z 5** okien, obchodov spolu 1819, break-even celkom -0.0031 %. Okná sa prekrývajú, 10 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.20 ATR za 5 barov)
- medián držania 62 barov grafu
- winrate 44.58 %, payoff 1.182
- 1.02 obchodov za deň
- šikmosť výnosov +1.075

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `session_end` 100 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'streda' vlastnosti 'Deň v týždni': 421 obchodov (23.1 %), break-even -0.0369 % oproti -0.0031 % celku. Bez nej by break-even bol 0.0072 % (+0.0103). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Deň v týždni**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| streda | 421 | 23.1 % | 40.6 | -0.0369 | 0.0072 | +0.0103 |
| pondelok | 311 | 17.1 % | 46.6 | -0.0244 | 0.0014 | +0.0045 |
| utorok | 355 | 19.5 % | 45.9 | 0.0015 | -0.0043 | -0.0012 |
| piatok | 369 | 20.3 % | 43.6 | 0.0185 | -0.0085 | -0.0054 |
| štvrtok | 363 | 20.0 % | 47.1 | 0.0296 | -0.0112 | -0.0081 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 8 | 481 | 26.4 % | 41.2 | -0.0257 | 0.0050 | +0.0081 |
| 16 – 23 | 426 | 23.4 % | 47.4 | -0.0126 | -0.0001 | +0.0030 |
| 8 – 16 | 476 | 26.2 % | 43.5 | -0.0012 | -0.0038 | -0.0007 |
| nad 23 | 436 | 24.0 % | 46.8 | 0.0297 | -0.0133 | -0.0102 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| pred vyhlásením | 42 | 2.3 % | 30.9 | -0.0607 | -0.0017 | +0.0014 |
| po vyhlásení | 251 | 13.8 % | 37.0 | -0.0427 | 0.0029 | +0.0060 |
| bez udalosti | 1526 | 83.9 % | 46.2 | 0.0047 | -0.0455 | -0.0424 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0031 % | -0.0002 % ± 0.0093 | -0.31 | 37.5 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0031 % | -0.0005 % ± 0.0098 | -0.27 | 41.3 |

Neodlisitelne od nahody (-0.3 sigma, percentil 37.5). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2023-01 | 466 | 31.9 | 43.6 | -0.0063 | 44 |
| 2023-01 - 2024-03 | 432 | 29.6 | 44.2 | 0.0030 | 66 |
| 2024-03 - 2025-06 | 450 | 30.9 | 47.3 | 0.0079 | 75 |
| 2025-06 - 2026-09 | 471 | 32.3 | 43.3 | -0.0111 | 32 |

Hranice pre úsek veľkosti posledného obdobia: -0.0279 až +0.0230 % (medián -0.0040).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 32. percentile, teda v medziach -0.0279 až +0.0230 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 10** — 2026-03-23T20:10 až 2026-04-02T20:00, spolu +3905.08.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-03-23T20:10 | 2026-03-23T20:10 | +43.45 | +0.10 | `session_end` |
| 2 | 2026-03-23T20:20 | 2026-03-23T20:20 | +21.45 | +0.05 | `session_end` |
| 3 | 2026-03-24T14:00 | 2026-03-24T20:00 | +196.46 | +0.45 | `session_end` |
| 4 | 2026-03-25T13:40 | 2026-03-25T20:00 | +243.40 | +0.53 | `session_end` |
| 5 | 2026-03-26T13:40 | 2026-03-26T20:00 | +803.46 | +1.81 | `session_end` |
| 6 | 2026-03-27T14:05 | 2026-03-27T20:00 | +556.42 | +1.24 | `session_end` |
| 7 | 2026-03-30T13:35 | 2026-03-30T20:00 | +479.40 | +1.04 | `session_end` |
| 8 | 2026-03-31T13:40 | 2026-03-31T20:00 | +976.36 | +2.12 | `session_end` |
| 9 | 2026-04-01T13:40 | 2026-04-01T20:00 | +178.32 | +0.37 | `session_end` |
| 10 | 2026-04-02T13:50 | 2026-04-02T20:00 | +406.36 | +0.87 | `session_end` |

**Straty za sebou: 10** — 2023-12-29T14:50 až 2024-01-04T15:10, spolu -555.22.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-12-29T14:50 | 2023-12-29T21:00 | -13.73 | -0.07 | `session_end` |
| 2 | 2024-01-02T14:35 | 2024-01-02T15:35 | -117.73 | -0.57 | `session_end` |
| 3 | 2024-01-02T15:45 | 2024-01-02T21:00 | -3.73 | -0.02 | `session_end` |
| 4 | 2024-01-02T21:10 | 2024-01-02T21:10 | -5.73 | -0.03 | `session_end` |
| 5 | 2024-01-03T14:40 | 2024-01-03T15:00 | -125.72 | -0.62 | `session_end` |
| 6 | 2024-01-03T15:10 | 2024-01-03T15:35 | -115.72 | -0.56 | `session_end` |
| 7 | 2024-01-03T15:45 | 2024-01-03T15:45 | -8.72 | -0.04 | `session_end` |
| 8 | 2024-01-03T15:55 | 2024-01-03T21:00 | -75.72 | -0.37 | `session_end` |
| 9 | 2024-01-03T21:10 | 2024-01-03T21:10 | -0.72 | -0.00 | `session_end` |
| 10 | 2024-01-04T14:50 | 2024-01-04T15:10 | -87.72 | -0.43 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0031 %**, medián -0.0032 %, 90 % interval -0.0161–0.0101 %
- P(edge > poplatok) = **26.9 %**
- max drawdown: medián 85.9 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 11, 95. percentil 14 obchodov
- pravdepodobnosť ruiny účtu: 39.1 %

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
<!-- POSUDOK cisla=b3b7d7b2 -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na MGC, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Intraday momentum na indexoch (rovnaký jav ako NOA — Zarattini a spol.), 9:30–16:00 NY; zlato nemá otvorenie RTH, ktoré by pásmo ukotvilo. Tu na MGC (zlato) — logika robená pre index, čísla to treba brať ako test prenosu.
2. **Má potenciál?** Zisková v 1 z 5 okien, 1819 obchodov (~364 za rok), break-even -0.0031 % (pod poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 44.58 % pri payoffe 1.182. Odložený rok 25/26: -50.89 % PnL, break-even -0.0130 %. Kladné okná sú skôr vlastnosť vzorky ako stabilný jav.
3. **Čo dorobiť.** Stop: predloha bez stopu → 95. percentil DD je obrovský; otestovať `slPct` 0,25–1 % a kontrolu len každých 15–30 min (otočky v šume).
4. **Čo otestovať ďalej.** Smernica (`sigma*`: TF, dni sigma, násobok pásma, VWAP, stop); porovnať s NOA — ak NOA robí to isté lepšie, Sigma je duplicita.
5. **Použiteľné?** **V defaultoch predlohy nie** — edge nad poplatkom nie je stabilný po rokoch; šancu má len s nastavením, ktoré nájde smernica (inak vyradiť).
6. **Čo by som pridal.** Výstup cez VWAP / hranicu pásma (trailing ako NOA) namiesto držania do 16:00; menej otočiek pri širšom pásme.

<!-- POSUDOK KONIEC -->
