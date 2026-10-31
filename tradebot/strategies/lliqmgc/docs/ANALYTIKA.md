# Základná analytika — LONDON LIQUIDITY IFVG 1.0 (MGC) (`lliqmgc`)

Zmerané 2026-10-31 na `MGC/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `/Users/martin/IBS/.nightsearch/base_lliqmgc.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy lliqmgc \
   --profile /Users/martin/IBS/.nightsearch/base_lliqmgc.json \
   --pair MGC/USD \
   --timeframe 5m \
   --fee 1.755e-05
```

## V čom je dobrá

- 607 obchodov spolu — na štatistiku dosť

## Kde má chyby

- zisková v 2 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20250904-20260904 v strate)
- break-even -0.0018 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 27 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 47.7 % (namerané 21.2 % medián) — na účet to treba mať
- nie je lepšia než náhodný vstup za tých istých pravidiel (-0.8 sigma) — výber vstupu nepridáva nič
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'proti trendu' vlastnosti 'S trendom, alebo proti': 434 obchodov (71.5 %), bez nej by break-even bol o +0.0131 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 133 | -2.81 | -0.0041 | 3.2 | 43.6 | +5/-4 | `20261031-085039-649888` |
| 20221001-20231001 | 127 | -1.78 | -0.0020 | 2.2 | 46.5 | +6/-5 | `20261031-085042-852018` |
| 20231001-20241001 | 114 | +3.35 | 0.0083 | 1.5 | 57.9 | +11/-7 | `20261031-085048-1494fd` |
| 20240904-20250904 | 126 | +2.62 | 0.0052 | 2.8 | 53.2 | +6/-7 | `20261031-085051-b47449` |
| 20250904-20260904 | 120 | -12.57 | -0.0103 | 24.3 | 50.8 | +8/-12 | `20261031-085057-bf2a9c` |

Zisková v **2 z 5** okien, obchodov spolu 607, break-even celkom -0.0018 %. Okná sa prekrývajú, 13 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.45 ATR za 5 barov)
- medián držania 3.2 barov grafu
- winrate 50.08 %, payoff 0.897
- 0.34 obchodov za deň
- šikmosť výnosov +0.333

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 50.1 %, `stop_loss` 49.9 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'proti trendu' vlastnosti 'S trendom, alebo proti': 434 obchodov (71.5 %), break-even -0.007 % oproti -0.0018 % celku. Bez nej by break-even bol 0.0113 % (+0.0131). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| proti trendu | 434 | 71.5 % | 49.1 | -0.0070 | 0.0113 | +0.0131 |
| s trendom | 173 | 28.5 % | 52.6 | 0.0113 | -0.0070 | -0.0052 |

**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| žiadna | 569 | 93.7 % | 49.7 | -0.0022 | 0.0046 | +0.0064 |
| FOMC | 9 | 1.5 % | 44.4 | 0.0135 | -0.0020 | -0.0002 |
| CPI | 27 | 4.4 % | 63.0 | 0.0161 | -0.0025 | -0.0007 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bez udalosti | 569 | 93.7 % | 49.7 | -0.0022 | 0.0046 | +0.0064 |
| po vyhlásení | 38 | 6.3 % | 55.3 | 0.0046 | -0.0022 | -0.0004 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0018 % | -0.0001 % ± 0.0023 | -0.75 | 22.2 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0018 % | -0.0000 % ± 0.0023 | -0.78 | 20.5 |

Neodlisitelne od nahody (-0.8 sigma, percentil 22.2). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 167 | 11.3 | 45.5 | -0.0031 | 36 |
| 2022-12 - 2024-03 | 140 | 9.5 | 46.4 | -0.0020 | 38 |
| 2024-03 - 2025-06 | 150 | 10.2 | 56.7 | 0.0084 | 87 |
| 2025-06 - 2026-09 | 150 | 10.2 | 52.0 | -0.0076 | 22 |

Hranice pre úsek veľkosti posledného obdobia: -0.0220 až +0.0126 % (medián 0.0002).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 22. percentile, teda v medziach -0.0220 až +0.0126 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 11** — 2024-05-06T01:05 až 2024-06-07T01:28, spolu +244.94.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-05-06T01:05 | 2024-05-06T02:01 | +36.19 | +0.16 | `take_profit` |
| 2 | 2024-05-07T01:25 | 2024-05-07T01:52 | +21.18 | +0.09 | `take_profit` |
| 3 | 2024-05-08T02:55 | 2024-05-08T04:13 | +25.18 | +0.11 | `take_profit` |
| 4 | 2024-05-09T01:25 | 2024-05-09T01:35 | +13.19 | +0.06 | `take_profit` |
| 5 | 2024-05-14T00:40 | 2024-05-14T00:44 | +10.18 | +0.04 | `take_profit` |
| 6 | 2024-05-16T01:55 | 2024-05-16T02:06 | +29.16 | +0.12 | `take_profit` |
| 7 | 2024-05-24T02:50 | 2024-05-24T04:52 | +35.18 | +0.15 | `take_profit` |
| 8 | 2024-05-28T01:35 | 2024-05-28T01:46 | +20.17 | +0.09 | `take_profit` |
| 9 | 2024-06-03T02:25 | 2024-06-03T02:39 | +17.18 | +0.07 | `take_profit` |
| 10 | 2024-06-04T01:55 | 2024-06-04T02:10 | +19.17 | +0.08 | `take_profit` |
| 11 | 2024-06-07T01:15 | 2024-06-07T01:28 | +18.16 | +0.08 | `take_profit` |

**Straty za sebou: 12** — 2026-02-03T02:45 až 2026-03-24T05:05, spolu -2512.58.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-02-03T02:45 | 2026-02-03T03:04 | -371.68 | -0.78 | `stop_loss` |
| 2 | 2026-02-06T00:40 | 2026-02-06T01:02 | -342.66 | -0.72 | `stop_loss` |
| 3 | 2026-02-12T02:05 | 2026-02-12T02:46 | -128.78 | -0.25 | `stop_loss` |
| 4 | 2026-02-20T01:40 | 2026-02-20T02:05 | -96.76 | -0.19 | `stop_loss` |
| 5 | 2026-02-23T03:15 | 2026-02-23T03:37 | -126.82 | -0.24 | `stop_loss` |
| 6 | 2026-03-04T03:35 | 2026-03-04T03:57 | -168.82 | -0.33 | `stop_loss` |
| 7 | 2026-03-09T23:45 | 2026-03-10T01:05 | -139.81 | -0.27 | `stop_loss` |
| 8 | 2026-03-16T00:05 | 2026-03-16T01:13 | -190.76 | -0.38 | `stop_loss` |
| 9 | 2026-03-18T00:30 | 2026-03-18T01:04 | -54.76 | -0.11 | `stop_loss` |
| 10 | 2026-03-20T02:30 | 2026-03-20T02:49 | -150.65 | -0.32 | `stop_loss` |
| 11 | 2026-03-23T01:20 | 2026-03-23T01:59 | -438.55 | -0.99 | `stop_loss` |
| 12 | 2026-03-24T02:30 | 2026-03-24T05:05 | -302.52 | -0.70 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0018 %**, medián -0.0014 %, 90 % interval -0.0110–0.0063 %
- P(edge > poplatok) = **27.0 %**
- max drawdown: medián 21.2 %, 95. percentil 47.7 %, najhorší 88.5 %
- najdlhšia séria strát: medián 9, 95. percentil 14 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %

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
<!-- POSUDOK cisla=e2f0df94 -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na MGC, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Večerný sweep high / low popoludnia NY (19:15–23:45) a inverzný FVG — málo obchodov (~60 / rok na MNQ), likvidita v Ázii je tenká. Tu na MGC (zlato) — logika robená pre index, čísla to treba brať ako test prenosu.
2. **Má potenciál?** Zisková v 2 z 5 okien, 607 obchodov (~121 za rok), break-even -0.0018 % (pod poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 50.08 % pri payoffe 0.897. Odložený rok 25/26: -12.57 % PnL, break-even -0.0103 %. Kladné okná sú skôr vlastnosť vzorky ako stabilný jav.
3. **Čo dorobiť.** Okno seansy aj sweepu sú pre NQ nevhodné (popoludnie NY → večer); skúsiť Ázia / Londýn ako zdroj likvidity a sweep v NY ráno.
4. **Čo otestovať ďalej.** Smernica (`lliq*`: okná seansy a sweepu, stop / cieľ, vek FVG); pri ~60 obchodoch za rok hranicu 150 z princípu nesplní, kým sa okno nezmení.
5. **Použiteľné?** **V defaultoch predlohy nie** — edge nad poplatkom nie je stabilný po rokoch; šancu má len s nastavením, ktoré nájde smernica (inak vyradiť).
6. **Čo by som pridal.** Likviditu brať z Ázie (20:00–2:00 NY) a sweep v Londýne / NY ráno — klasické ICT poradie, ktoré dá viac obchodov.

<!-- POSUDOK KONIEC -->
