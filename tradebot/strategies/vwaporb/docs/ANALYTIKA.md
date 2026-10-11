# Základná analytika — VWAP ORB 1.5 (`vwaporb`)

Zmerané 2026-10-11 na `MNQ/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/vwaporb_PRESIEL_SMERNICAMI_VWAP_ORB_1_2026-10-11.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy vwaporb \
   --profile .nightsearch/checkup/vwaporb_PRESIEL_SMERNICAMI_VWAP_ORB_1_2026-10-11.json \
   --pair MNQ/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 788 obchodov spolu — na štatistiku dosť
- break-even 0.0727 % je nad poplatkom 0.0018 % (rezerva +0.0709 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 7.8 %
- odlíšiteľná od náhody (+5.4 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-08 na 21. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'do 0.6343 %' vlastnosti 'Vzdialenosť stopu': 198 obchodov (25.1 %), bez nej by break-even bol o +0.0290 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 174 | +18.14 | 0.1140 | 3.2 | 76.4 | +11/-4 | `20261011-071720-7523f8` |
| 20221001-20231001 | 167 | +10.67 | 0.0744 | 2.1 | 73.7 | +15/-3 | `20261011-071723-457b20` |
| 20231001-20241001 | 172 | +16.50 | 0.0815 | 1.8 | 77.3 | +9/-4 | `20261011-071726-8a283a` |
| 20240904-20250904 | 148 | +6.62 | 0.0333 | 4.8 | 66.9 | +14/-5 | `20261011-071729-489fa5` |
| 20250904-20260904 | 127 | +15.58 | 0.0706 | 6.3 | 71.7 | +12/-3 | `20261011-071732-36ff93` |

Zisková v **5 z 5** okien, obchodov spolu 788, break-even celkom 0.0727 %.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.44 ATR za 5 barov)
- medián držania 41.8 barov grafu
- winrate 73.48 %, payoff 0.562
- 0.44 obchodov za deň
- šikmosť výnosov -0.594

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 73.5 %, `stop_loss` 26.5 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'do 0.6343 %' vlastnosti 'Vzdialenosť stopu': 198 obchodov (25.1 %), break-even -0.0048 % oproti 0.0727 % celku. Bez nej by break-even bol 0.1017 % (+0.0290). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.6343 % | 198 | 25.1 % | 66.2 | -0.0048 | 0.1017 | +0.0290 |
| 0.9262 % – 1.3538 % | 197 | 25.0 % | 73.6 | 0.0564 | 0.0780 | +0.0053 |
| 0.6343 % – 0.9262 % | 197 | 25.0 % | 78.7 | 0.0729 | 0.0727 | +0.0000 |
| nad 1.3538 % | 196 | 24.9 % | 75.5 | 0.1818 | 0.0402 | -0.0325 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 16 – 23 | 187 | 23.7 % | 70.0 | 0.0210 | 0.0888 | +0.0161 |
| nad 23 | 187 | 23.7 % | 71.7 | 0.0540 | 0.0785 | +0.0058 |
| 8 – 16 | 213 | 27.0 % | 74.2 | 0.0890 | 0.0665 | -0.0062 |
| do 8 | 201 | 25.5 % | 77.6 | 0.1215 | 0.0565 | -0.0162 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.8147 – 0.9191 | 197 | 25.0 % | 73.1 | 0.0334 | 0.0855 | +0.0128 |
| do 0.8147 | 198 | 25.1 % | 72.2 | 0.0390 | 0.0838 | +0.0111 |
| 0.9191 – 0.9704 | 197 | 25.0 % | 72.1 | 0.0810 | 0.0699 | -0.0028 |
| nad 0.9704 | 196 | 24.9 % | 76.5 | 0.1359 | 0.0515 | -0.0212 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0727 % | -0.0019 % ± 0.0139 | +5.37 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0727 % | -0.0029 % ± 0.0144 | +5.24 | 100.0 |

Edge je odlisitelny od nahody (5.4 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 206 | 14.0 | 75.7 | 0.1123 | 88 |
| 2022-12 - 2024-03 | 204 | 13.9 | 76.0 | 0.0729 | 53 |
| 2024-03 - 2025-06 | 210 | 14.3 | 73.3 | 0.0750 | 54 |
| 2025-06 - 2026-08 | 168 | 11.4 | 67.9 | 0.0449 | 21 |

Hranice pre úsek veľkosti posledného obdobia: +0.0168 až +0.1348 % (medián 0.0728).

**DRZI** — posledné obdobie (2025-06 - 2026-08) je na 21. percentile, teda v medziach +0.0168 až +0.1348 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 15** — 2023-06-01T15:03 až 2023-06-21T14:50, spolu +2075.41.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-06-01T15:03 | 2023-06-01T15:36 | +102.99 | +0.36 | `take_profit` |
| 2 | 2023-06-01T15:39 | 2023-06-01T16:20 | +138.49 | +0.48 | `take_profit` |
| 3 | 2023-06-01T16:21 | 2023-06-02T13:30 | +209.48 | +0.72 | `take_profit` |
| 4 | 2023-06-06T14:30 | 2023-06-06T14:49 | +61.48 | +0.21 | `take_profit` |
| 5 | 2023-06-06T14:51 | 2023-06-07T13:32 | +91.47 | +0.31 | `take_profit` |
| 6 | 2023-06-07T14:48 | 2023-06-07T16:22 | +183.99 | +0.63 | `take_profit` |
| 7 | 2023-06-07T16:24 | 2023-06-08T06:13 | +279.99 | +0.97 | `take_profit` |
| 8 | 2023-06-08T16:00 | 2023-06-09T13:30 | +168.48 | +0.58 | `take_profit` |
| 9 | 2023-06-12T19:21 | 2023-06-13T03:34 | +171.95 | +0.57 | `take_profit` |
| 10 | 2023-06-14T13:48 | 2023-06-14T14:05 | +43.44 | +0.14 | `take_profit` |
| 11 | 2023-06-14T14:06 | 2023-06-14T14:21 | +68.44 | +0.23 | `take_profit` |
| 12 | 2023-06-14T14:24 | 2023-06-14T15:23 | +88.43 | +0.29 | `take_profit` |
| 13 | 2023-06-15T14:09 | 2023-06-15T15:38 | +135.93 | +0.45 | `take_profit` |
| 14 | 2023-06-15T15:39 | 2023-06-15T18:55 | +208.42 | +0.68 | `take_profit` |
| 15 | 2023-06-21T14:33 | 2023-06-21T14:50 | +122.44 | +0.41 | `take_profit` |

**Straty za sebou: 5** — 2025-01-29T19:06 až 2025-02-03T15:24, spolu -1423.07.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-01-29T19:06 | 2025-01-30T01:14 | -376.51 | -0.88 | `stop_loss` |
| 2 | 2025-01-30T17:18 | 2025-01-30T20:02 | -261.52 | -0.61 | `stop_loss` |
| 3 | 2025-01-30T20:45 | 2025-01-30T21:30 | -268.52 | -0.62 | `stop_loss` |
| 4 | 2025-01-31T17:12 | 2025-01-31T18:34 | -277.03 | -0.63 | `stop_loss` |
| 5 | 2025-02-03T15:12 | 2025-02-03T15:24 | -239.49 | -0.57 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0727 %**, medián 0.0727 %, 90 % interval 0.0461–0.1009 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 4.6 %, 95. percentil 7.8 %, najhorší 19.1 %
- najdlhšia séria strát: medián 5, 95. percentil 6 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **463** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=955e7a36 -->
**Posudok (AI, 11. 10. 2026)** — profil PREŠIEL SMERNICAMI č. 1 z testovania podľa smernice (krok 7).

1. **Na čo sa to hodí a na čo nie.** MNQ 3m–5m, NY otvorenie (range po 9:30 a prieraz s VWAP). Scalp s cieľom ~0,55 R a winrate 73 %, drží ~40 barov. Hodí sa na futures s dobrým plnením; na CFD so širším spreadom bude horšia, ale break-even 0,073 % na stranu (~40× poplatok) dáva najväčšiu rezervu zo všetkých.
2. **Má to potenciál?** Áno. 5 z 5 rokov v zisku, +5,4 σ proti náhode (aj v tých istých hodinách +5,2 σ — edge je vo výbere, nie len v čase), break-even suverénne najvyšší. Proti: rok 24/25 slabší (+6,6 %, WR 67 %) a posledné obdobie na 21. percentile — zatiaľ v norme, ale sledovať.
3. **Čo dorobiť.** Najhoršia štvrtina obchodov má veľmi tesný stop (do 0,63 %) — minimálna vzdialenosť stopu (`minSlDistance` / `slBufferAtr`) by ich odfiltrovala (+0,029 break-even). Analytika ráta obchody z prekrývajúcich sa okien 23/24 a 24/25 (september 2024) dvakrát — najdlhšia séria strát môže byť o 1–2 nadsadená.
4. **Čo otestovať ďalej.** NAS100 z Dukascopy (krok 8) — rovnaký smer výsledku = jav trhu, nie dát; 2× poplatok (`--fee 3.51e-05`) a 1 tick sklzu navyše; forward test 4–8 týždňov na 1 MNQ (krok 9).
5. **Je to použiteľné?** Áno — najsilnejší kandidát podľa rezervy na náklady. Ďalej krok 8 a 10.
6. **Čo by som pridal.** Filter na tesný stop (min. vzdialenosť v ATR) a denný limit 2 strát (séria strát 4–5 prichádza v zhlukoch).
<!-- POSUDOK KONIEC -->
