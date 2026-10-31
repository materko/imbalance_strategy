# Základná analytika — T-MEAN REVERSION 1.0 (MGC) (`tmrmgc`)

Zmerané 2026-10-31 na `MGC/USD` 15m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `/Users/martin/IBS/.nightsearch/base_tmrmgc.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy tmrmgc \
   --profile /Users/martin/IBS/.nightsearch/base_tmrmgc.json \
   --pair MGC/USD \
   --timeframe 15m \
   --fee 1.755e-05
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- break-even 0.1369 % je nad poplatkom 0.0018 % (rezerva +0.1351 bodu)
- edge drží aj v poslednom období (2025-06 - 2026-08 na 29. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- edge nad poplatkom len v 93 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 63.4 % (namerané 32.8 % medián) — na účet to treba mať
- proti náhode len +0.5 sigma: náznak, nie dôkaz
- charakter: formácia / štruktúra (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- 99.1 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina '1.054 – 1.233' vlastnosti 'Volatilita voči normálu': 29 obchodov (24.8 %), bez nej by break-even bol o +0.1663 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 24 | +2.62 | 0.0316 | 5.4 | 54.2 | +3/-3 | `20261031-085109-91eef9` |
| 20221001-20231001 | 26 | +20.12 | 0.2059 | 5.3 | 65.4 | +10/-3 | `20261031-085112-41bdfd` |
| 20231001-20241001 | 23 | +19.18 | 0.1872 | 3.4 | 69.6 | +6/-2 | `20261031-085116-a738fd` |
| 20240904-20250904 | 25 | +36.75 | 0.2497 | 14.5 | 68.0 | +4/-3 | `20261031-085119-8f982a` |
| 20250904-20260904 | 20 | +4.44 | 0.0271 | 40.6 | 55.0 | +6/-4 | `20261031-085122-f19404` |

Zisková v **5 z 5** okien, obchodov spolu 117, break-even celkom 0.1369 %. Okná sa prekrývajú, 1 obchodov započítaných dvakrát vypadlo.

## Charakter

**Formácia / štruktúra** (istota priemerná)

- vstup bez jasného smeru pohybu (-0.02 ATR za 5 barov)
- medián držania 203 barov grafu
- winrate 62.39 %, payoff 0.867
- 0.07 obchodov za deň
- šikmosť výnosov -0.521

- **Čo je normálne:** Zmes: časť obchodov sa chová ako prerazenie, časť ako návrat. Priemer preto o jednotlivom obchode nehovorí veľa.
- **Na čo pozor:** Práve pri tomto type sa najviac oplatí rozdeliť obchody na skupiny (`tester.analytics`) — priemer skrýva dve rôzne populácie.
- **Čo ladiť:** Podmienky vstupu (ktoré modely/formácie zapnuté) a potom až výstup.

Výstupy: `session_end` 99.1 %, `force_exit` 0.9 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je '1.054 – 1.233' vlastnosti 'Volatilita voči normálu': 29 obchodov (24.8 %), break-even -0.3763 % oproti 0.1369 % celku. Bez nej by break-even bol 0.3032 % (+0.1663). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Volatilita voči normálu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 1.054 – 1.233 | 29 | 24.8 % | 58.6 | -0.3763 | 0.3032 | +0.1663 |
| 1.233 – 1.459 | 29 | 24.8 % | 62.1 | 0.0407 | 0.1658 | +0.0289 |
| do 1.054 | 30 | 25.6 % | 56.7 | 0.1644 | 0.1252 | -0.0117 |
| nad 1.459 | 29 | 24.8 % | 72.4 | 0.7519 | -0.0439 | -0.1808 |

**Plánovaný RR**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 99.95 R | 32 | 27.4 % | 53.1 | -0.2564 | 0.2548 | +0.1179 |
| nad 100.03 R | 28 | 23.9 % | 57.1 | -0.0403 | 0.1835 | +0.0466 |
| 99.95 R – 100 R | 47 | 40.2 % | 66.0 | 0.2576 | 0.0441 | -0.0928 |
| 100 R – 100.03 R | 10 | 8.5 % | 90.0 | 0.7314 | 0.0508 | -0.0861 |

**Kalendárny mesiac**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 10 | 9 | 7.7 % | 33.3 | -0.7892 | 0.2062 | +0.0693 |
| 06 | 13 | 11.1 % | 46.1 | -0.6628 | 0.2458 | +0.1089 |
| 11 | 13 | 11.1 % | 53.9 | 0.0750 | 0.1444 | +0.0075 |
| 03 | 11 | 9.4 % | 72.7 | 0.1536 | 0.1350 | -0.0019 |
| … | | | | | | |
| 12 | 9 | 7.7 % | 77.8 | 0.4498 | 0.1128 | -0.0241 |
| 04 | 11 | 9.4 % | 54.5 | 0.4810 | 0.1024 | -0.0345 |
| 01 | 9 | 7.7 % | 88.9 | 0.5109 | 0.1058 | -0.0311 |
| 02 | 10 | 8.5 % | 80.0 | 0.6387 | 0.0915 | -0.0454 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.1369 % | 0.0824 % ± 0.1097 | +0.50 | 69.1 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.1369 % | 0.0819 % ± 0.1121 | +0.49 | 68.4 |

Neodlisitelne od nahody (+0.5 sigma, percentil 69.1). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2023-01 | 31 | 2.1 | 58.1 | 0.0907 | 39 |
| 2023-01 - 2024-03 | 28 | 1.9 | 67.9 | 0.1909 | 58 |
| 2024-03 - 2025-06 | 34 | 2.3 | 64.7 | 0.2423 | 73 |
| 2025-06 - 2026-08 | 24 | 1.6 | 58.3 | 0.0371 | 29 |

Hranice pre úsek veľkosti posledného obdobia: -0.3039 až +0.4680 % (medián 0.1764).

**DRZI** — posledné obdobie (2025-06 - 2026-08) je na 29. percentile, teda v medziach -0.3039 až +0.4680 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 10** — 2022-11-21T17:15 až 2023-04-12T20:00, spolu +2170.37.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-11-21T17:15 | 2022-11-23T20:00 | +153.39 | +0.88 | `session_end` |
| 2 | 2022-11-28T17:15 | 2022-11-30T20:00 | +402.38 | +2.31 | `session_end` |
| 3 | 2022-12-05T17:15 | 2022-12-07T20:00 | +198.37 | +1.11 | `session_end` |
| 4 | 2023-01-23T17:15 | 2023-01-25T20:00 | +233.32 | +1.21 | `session_end` |
| 5 | 2023-01-30T17:15 | 2023-02-01T20:00 | +180.32 | +0.93 | `session_end` |
| 6 | 2023-02-06T17:15 | 2023-02-08T20:00 | +93.34 | +0.50 | `session_end` |
| 7 | 2023-02-27T17:15 | 2023-03-01T20:00 | +209.36 | +1.15 | `session_end` |
| 8 | 2023-03-27T17:15 | 2023-03-29T20:00 | +107.31 | +0.55 | `session_end` |
| 9 | 2023-04-03T17:15 | 2023-04-05T20:00 | +363.29 | +1.82 | `session_end` |
| 10 | 2023-04-10T17:15 | 2023-04-12T20:00 | +229.29 | +1.14 | `session_end` |

**Straty za sebou: 4** — 2026-05-18T17:15 až 2026-06-24T20:00, spolu -5584.12.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-05-18T17:15 | 2026-05-20T20:00 | -80.60 | -0.18 | `session_end` |
| 2 | 2026-05-25T17:15 | 2026-05-27T20:00 | -895.59 | -1.96 | `session_end` |
| 3 | 2026-06-08T17:15 | 2026-06-10T20:00 | -2684.48 | -6.15 | `session_end` |
| 4 | 2026-06-22T17:15 | 2026-06-24T20:00 | -1923.44 | -4.57 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.1369 %**, medián 0.1357 %, 90 % interval -0.0092–0.2924 %
- P(edge > poplatok) = **93.4 %**
- max drawdown: medián 32.8 %, 95. percentil 63.4 %, najhorší 100.0 %
- najdlhšia séria strát: medián 4, 95. percentil 6 obchodov
- pravdepodobnosť ruiny účtu: 0.3 %

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
<!-- POSUDOK cisla=4859da67 -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na MGC, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Kalendárny jav (pondelok po červenom piatku → streda), ~25 obchodov za rok — pre smernicu (150 / rok) z princípu nevhodný, skôr doplnok portfólia. Tu na MGC (zlato) — logika robená pre index, čísla to treba brať ako test prenosu.
2. **Má potenciál?** Zisková v 5 z 5 okien, 117 obchodov (~23 za rok), break-even 0.1369 % (nad poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 62.39 % pri payoffe 0.867. Odložený rok 25/26: +4.44 % PnL, break-even 0.0271 %. Jav je skôr skutočný ako vlastnosť vzorky.
3. **Čo dorobiť.** Bez stopu: poistka 10 % je len technická; pre live treba stop v % alebo ATR. Sviatky (pondelok zatvorené) predloha nerieši.
4. **Čo otestovať ďalej.** Smernica ho pre počet obchodov nepustí; ako doplnok portfólia `cli portfolio` s inými stratégiami a test proti náhode na dňoch v týždni.
5. **Použiteľné?** **Pre smernicu nie** (≈25 obchodov za rok, hranica 150); ako kalendárny doplnok portfólia áno — zisková vo väčšine okien a break-even vysoko nad poplatkom.
6. **Čo by som pridal.** Rovnaký jav aj pre pozitívny piatok (short alebo bez obchodu) a výstup už v utorok — overiť, kde je drift najsilnejší.

<!-- POSUDOK KONIEC -->
