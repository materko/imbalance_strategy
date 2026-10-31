# Základná analytika — FLASH TRIGGER ORB 1.0 (ES) (`flashorbes`)

Zmerané 2026-10-31 na `ES/USD` 15m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `/Users/martin/IBS/.nightsearch/base_flashorbes.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy flashorbes \
   --profile /Users/martin/IBS/.nightsearch/base_flashorbes.json \
   --pair ES/USD \
   --timeframe 15m \
   --fee 1.755e-05
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 846 obchodov spolu — na štatistiku dosť
- break-even 0.0367 % je nad poplatkom 0.0018 % (rezerva +0.0349 bodu)
- edge nad poplatkom v 98 % bootstrapových vzoriek
- odlíšiteľná od náhody (+2.9 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 46. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- 95. percentil max drawdownu 100.0 % (namerané 100.0 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 53.2 % pri riziku, s akým beh bežal
- najhoršia skupina 'do 3 R' vlastnosti 'Plánovaný RR': 675 obchodov (79.8 %), bez nej by break-even bol o +0.0693 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 203 | +256.67 | 0.0316 | 118.8 | 29.1 | +2/-16 | `20261031-084759-10bda4` |
| 20221001-20231001 | 185 | +104.72 | 0.0153 | 87.0 | 26.5 | +3/-14 | `20261031-084805-162185` |
| 20231001-20241001 | 179 | +241.98 | 0.0281 | 43.3 | 29.6 | +5/-14 | `20261031-084808-768c07` |
| 20240904-20250904 | 136 | +697.81 | 0.0866 | 103.1 | 31.6 | +5/-10 | `20261031-084811-eae5eb` |
| 20250904-20260904 | 156 | +293.52 | 0.0285 | 45.0 | 28.9 | +3/-10 | `20261031-084817-e27eed` |

Zisková v **5 z 5** okien, obchodov spolu 846, break-even celkom 0.0367 %. Okná sa prekrývajú, 13 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+1.26 ATR za 5 barov)
- medián držania 21 barov grafu
- winrate 28.96 %, payoff 2.999
- 0.47 obchodov za deň
- šikmosť výnosov +3.869

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 70.8 %, `take_profit` 28.8 %, `force_exit` 0.4 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'do 3 R' vlastnosti 'Plánovaný RR': 675 obchodov (79.8 %), break-even 0.0185 % oproti 0.0367 % celku. Bez nej by break-even bol 0.106 % (+0.0693). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**Plánovaný RR**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 3 R | 675 | 79.8 % | 27.9 | 0.0185 | 0.1060 | +0.0693 |
| nad 3 R | 171 | 20.2 % | 33.3 | 0.1060 | 0.0185 | -0.0182 |

**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 15 h | 636 | 75.2 % | 29.2 | 0.0228 | 0.0783 | +0.0416 |
| nad 15 h | 210 | 24.8 % | 28.1 | 0.0783 | 0.0228 | -0.0139 |

**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| FOMC | 28 | 3.3 % | 21.4 | -0.0331 | 0.0390 | +0.0023 |
| NFP | 38 | 4.5 % | 31.6 | 0.0140 | 0.0377 | +0.0010 |
| žiadna | 739 | 87.4 % | 28.1 | 0.0308 | 0.0780 | +0.0413 |
| CPI | 40 | 4.7 % | 47.5 | 0.2193 | 0.0276 | -0.0091 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0367 % | 0.0000 % ± 0.0128 | +2.87 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0367 % | 0.0027 % ± 0.0126 | +2.71 | 99.5 |

Edge je odlisitelny od nahody (2.9 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 243 | 16.5 | 29.6 | 0.0416 | 60 |
| 2022-12 - 2024-03 | 220 | 14.9 | 26.4 | 0.0115 | 26 |
| 2024-03 - 2025-06 | 173 | 11.7 | 30.1 | 0.0685 | 81 |
| 2025-06 - 2026-09 | 210 | 14.2 | 30.0 | 0.0288 | 46 |

Hranice pre úsek veľkosti posledného obdobia: -0.0186 až +0.1057 % (medián 0.0326).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 46. percentile, teda v medziach -0.0186 až +0.1057 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 5** — 2023-11-10T17:45 až 2023-12-19T16:04, spolu +20184.28, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-11-10T17:45 | 2023-11-14T20:12 | +5642.16 | +2.56 | `take_profit` |
| 2 | 2023-11-14T20:15 | 2023-12-11T00:00 | +7004.44 | +3.10 | `take_profit` |
| 3 | 2023-12-11T15:00 | 2023-12-12T13:29 | +1329.29 | +0.57 | `take_profit` |
| 4 | 2023-12-12T15:15 | 2023-12-13T19:00 | +1866.76 | +0.80 | `take_profit` |
| 5 | 2023-12-13T19:15 | 2023-12-19T16:04 | +4341.63 | +1.84 | `take_profit` |

**Straty za sebou: 16** — 2021-11-15T15:15 až 2021-12-21T16:40, spolu -23967.63.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2021-11-15T15:15 | 2021-11-16T14:48 | -520.73 | -0.22 | `stop_loss` |
| 2 | 2021-11-16T15:15 | 2021-11-18T15:12 | -908.22 | -0.39 | `stop_loss` |
| 3 | 2021-11-18T15:15 | 2021-11-18T17:02 | -1133.23 | -0.48 | `stop_loss` |
| 4 | 2021-11-19T15:00 | 2021-11-19T18:40 | -745.75 | -0.32 | `stop_loss` |
| 5 | 2021-11-22T15:00 | 2021-11-22T16:53 | -1008.29 | -0.43 | `stop_loss` |
| 6 | 2021-11-23T15:00 | 2021-11-23T15:26 | -1183.21 | -0.50 | `stop_loss` |
| 7 | 2021-11-24T15:30 | 2021-11-26T02:25 | -1008.19 | -0.43 | `stop_loss` |
| 8 | 2021-11-26T15:00 | 2021-11-29T13:47 | -1233.13 | -0.53 | `stop_loss` |
| 9 | 2021-11-29T15:30 | 2021-11-29T17:01 | -1008.14 | -0.44 | `stop_loss` |
| 10 | 2021-11-30T15:15 | 2021-11-30T15:49 | -970.62 | -0.42 | `stop_loss` |
| 11 | 2021-12-01T15:15 | 2021-12-01T18:06 | -1195.60 | -0.52 | `stop_loss` |
| 12 | 2021-12-02T15:00 | 2021-12-03T17:00 | -2782.96 | -1.22 | `stop_loss` |
| 13 | 2021-12-03T17:15 | 2021-12-06T18:26 | -4745.50 | -2.10 | `stop_loss` |
| 14 | 2021-12-06T18:30 | 2021-12-20T07:28 | -3408.03 | -1.48 | `stop_loss` |
| 15 | 2021-12-20T15:15 | 2021-12-20T20:50 | -1057.98 | -0.47 | `stop_loss` |
| 16 | 2021-12-21T15:00 | 2021-12-21T16:40 | -1058.06 | -0.46 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0367 %**, medián 0.0356 %, 90 % interval 0.0079–0.0700 %
- P(edge > poplatok) = **98.1 %**
- max drawdown: medián 100.0 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 16, 95. percentil 23 obchodov
- pravdepodobnosť ruiny účtu: 53.2 %

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
<!-- POSUDOK cisla=6f343ca5 -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na ES, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Prieraz jednej sviečky (14:30 UTC = otvorenie NY v zime, v lete o hodinu neskôr — predloha posun nerieši); index futures, nie zlato. Tu na ES — rovnaká logika ako MNQ, prahy v ATR sa prispôsobia.
2. **Má potenciál?** Zisková v 5 z 5 okien, 846 obchodov (~169 za rok), break-even 0.0367 % (nad poplatkom 0,0018 %), +2.9 sigma proti náhodnému vstupu; WR 28.96 % pri payoffe 2.999. Odložený rok 25/26: +293.52 % PnL, break-even 0.0285 %. Jav je skôr skutočný ako vlastnosť vzorky.
3. **Čo dorobiť.** Čas sviečky v New Yorku namiesto pevného UTC (letný čas posúva sviečku o hodinu), koniec dňa, ktorý na 15m grafe naozaj nastane (predloha 23:59 na 15m nikdy).
4. **Čo otestovať ďalej.** Smernica (`flashorb*`: hodina a minúta sviečky, RR 0,5–3, TF, trend, typ vstupu); rozhodne, či RR 3 s WR ~29 % drží aj s plató.
5. **Použiteľné?** **Áno ako kandidát do smernice** — defaulty predlohy sú ziskové vo väčšine okien a edge je nad poplatkom; rozhodne hľadanie a odložený rok.
6. **Čo by som pridal.** Sviečku vyberať podľa NY času otvorenia (9:30 / 9:45) a cieľ menší ako 3 R — vyšší WR, menej dní bez zisku.

<!-- POSUDOK KONIEC -->
