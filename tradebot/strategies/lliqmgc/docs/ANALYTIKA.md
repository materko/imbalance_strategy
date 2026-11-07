# Základná analytika — LONDON LIQUIDITY IFVG 1.0 (MGC) (`lliqmgc`)

Zmerané 2026-11-03 na `MGC/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/lliqmgc_PRESIEL_SMERNICAMI_LONDON_IFVG_MGC_1_2026-11-03.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy lliqmgc \
   --profile .nightsearch/checkup/lliqmgc_PRESIEL_SMERNICAMI_LONDON_IFVG_MGC_1_2026-11-03.json \
   --pair MGC/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 737 obchodov spolu — na štatistiku dosť
- break-even 0.0271 % je nad poplatkom 0.0018 % (rezerva +0.0253 bodu)
- edge nad poplatkom v 99 % bootstrapových vzoriek
- drawdown drží: 95. percentil 5.4 %
- odlíšiteľná od náhody (+5.9 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 90. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- zisková v 3 z 5 referenčných okien (20211001-20221001, 20221001-20231001 v strate)
- najhoršia skupina 'žiadna' vlastnosti 'Makro udalosť v ten deň': 689 obchodov (93.5 %), bez nej by break-even bol o +0.0579 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 157 | -0.24 | -0.0008 | 0.9 | 24.8 | +3/-15 | `20261103-051312-064d05` |
| 20221001-20231001 | 165 | -0.33 | -0.0014 | 0.7 | 23.6 | +3/-16 | `20261103-051315-ca39b0` |
| 20231001-20241001 | 143 | +1.30 | 0.0140 | 0.5 | 30.8 | +5/-13 | `20261103-051318-d50a8a` |
| 20240904-20250904 | 137 | +4.40 | 0.0338 | 0.8 | 33.6 | +4/-9 | `20261103-051321-ad05a1` |
| 20250904-20260904 | 147 | +11.34 | 0.0546 | 3.1 | 29.9 | +6/-12 | `20261103-051324-c66f67` |

Zisková v **3 z 5** okien, obchodov spolu 737, break-even celkom 0.0271 %. Okná sa prekrývajú, 12 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+1.39 ATR za 5 barov)
- medián držania 17.3 barov grafu
- winrate 28.36 %, payoff 3.675
- 0.41 obchodov za deň
- šikmosť výnosov +6.092

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 71.6 %, `take_profit` 28.2 %, `force_exit` 0.1 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'žiadna' vlastnosti 'Makro udalosť v ten deň': 689 obchodov (93.5 %), break-even 0.0231 % oproti 0.0271 % celku. Bez nej by break-even bol 0.085 % (+0.0579). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| žiadna | 689 | 93.5 % | 27.6 | 0.0231 | 0.0850 | +0.0579 |
| FOMC | 12 | 1.6 % | 33.3 | 0.0745 | 0.0264 | -0.0007 |
| CPI | 32 | 4.3 % | 46.9 | 0.1272 | 0.0229 | -0.0042 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bez udalosti | 689 | 93.5 % | 27.6 | 0.0231 | 0.0850 | +0.0579 |
| po vyhlásení | 48 | 6.5 % | 39.6 | 0.0850 | 0.0231 | -0.0040 |

**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| proti trendu | 529 | 71.8 % | 27.6 | 0.0201 | 0.0441 | +0.0170 |
| s trendom | 208 | 28.2 % | 30.3 | 0.0441 | 0.0201 | -0.0070 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0271 % | 0.0003 % ± 0.0046 | +5.87 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0271 % | 0.0015 % ± 0.0046 | +5.62 | 100.0 |

Edge je odlisitelny od nahody (5.9 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 198 | 13.4 | 23.7 | -0.0024 | 7 |
| 2022-12 - 2024-03 | 189 | 12.8 | 25.4 | 0.0012 | 11 |
| 2024-03 - 2025-06 | 170 | 11.5 | 32.9 | 0.0236 | 52 |
| 2025-06 - 2026-09 | 180 | 12.2 | 32.2 | 0.0559 | 90 |

Hranice pre úsek veľkosti posledného obdobia: -0.0070 až +0.0673 % (medián 0.0220).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 90. percentile, teda v medziach -0.0070 až +0.0673 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 6** — 2025-11-06T01:39 až 2025-11-19T05:18, spolu +1105.36.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-11-06T01:39 | 2025-11-06T05:48 | +178.60 | +0.45 | `take_profit` |
| 2 | 2025-11-07T03:03 | 2025-11-07T04:02 | +77.60 | +0.19 | `take_profit` |
| 3 | 2025-11-12T00:24 | 2025-11-12T01:00 | +106.55 | +0.26 | `take_profit` |
| 4 | 2025-11-13T02:03 | 2025-11-13T08:15 | +382.52 | +0.91 | `take_profit` |
| 5 | 2025-11-14T03:39 | 2025-11-14T05:09 | +134.52 | +0.32 | `take_profit` |
| 6 | 2025-11-19T02:06 | 2025-11-19T05:18 | +225.57 | +0.56 | `take_profit` |

**Straty za sebou: 16** — 2023-07-31T00:15 až 2023-08-31T02:18, spolu -164.96.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-07-31T00:15 | 2023-07-31T00:30 | -10.70 | -0.05 | `stop_loss` |
| 2 | 2023-07-31T23:21 | 2023-07-31T23:43 | -12.70 | -0.06 | `stop_loss` |
| 3 | 2023-08-03T03:21 | 2023-08-03T05:00 | -27.69 | -0.14 | `stop_loss` |
| 4 | 2023-08-04T01:54 | 2023-08-04T02:01 | -9.69 | -0.05 | `stop_loss` |
| 5 | 2023-08-10T23:30 | 2023-08-11T00:00 | -7.68 | -0.04 | `stop_loss` |
| 6 | 2023-08-14T02:48 | 2023-08-14T03:04 | -11.68 | -0.06 | `stop_loss` |
| 7 | 2023-08-14T23:51 | 2023-08-15T00:03 | -10.68 | -0.06 | `stop_loss` |
| 8 | 2023-08-15T23:15 | 2023-08-16T01:16 | -11.68 | -0.06 | `stop_loss` |
| 9 | 2023-08-16T23:48 | 2023-08-17T00:03 | -16.67 | -0.09 | `stop_loss` |
| 10 | 2023-08-20T23:33 | 2023-08-20T23:45 | -5.67 | -0.03 | `stop_loss` |
| 11 | 2023-08-21T23:57 | 2023-08-22T00:56 | -9.68 | -0.05 | `stop_loss` |
| 12 | 2023-08-24T03:48 | 2023-08-24T04:13 | -6.68 | -0.03 | `stop_loss` |
| 13 | 2023-08-24T23:45 | 2023-08-24T23:58 | -6.68 | -0.03 | `stop_loss` |
| 14 | 2023-08-28T03:27 | 2023-08-28T03:28 | -2.68 | -0.01 | `stop_loss` |
| 15 | 2023-08-29T00:27 | 2023-08-29T01:04 | -8.68 | -0.04 | `stop_loss` |
| 16 | 2023-08-31T01:57 | 2023-08-31T02:18 | -5.69 | -0.03 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0271 %**, medián 0.0263 %, 90 % interval 0.0087–0.0476 %
- P(edge > poplatok) = **99.2 %**
- max drawdown: medián 2.9 %, 95. percentil 5.4 %, najhorší 13.3 %
- najdlhšia séria strát: medián 18, 95. percentil 26 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

> **Posudok je starší než čísla** (písal sa k vzorke `e2f0df94`, tu je `4e62b00e`). Nech ho AI prepíše — čísla nižšie sa medzitým zmenili.

<!-- POSUDOK cisla=e2f0df94 -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na MGC, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Večerný sweep high / low popoludnia NY (19:15–23:45) a inverzný FVG — málo obchodov (~60 / rok na MNQ), likvidita v Ázii je tenká. Tu na MGC (zlato) — logika robená pre index, čísla to treba brať ako test prenosu.
2. **Má potenciál?** Zisková v 2 z 5 okien, 607 obchodov (~121 za rok), break-even -0.0018 % (pod poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 50.08 % pri payoffe 0.897. Odložený rok 25/26: -12.57 % PnL, break-even -0.0103 %. Kladné okná sú skôr vlastnosť vzorky ako stabilný jav.
3. **Čo dorobiť.** Okno seansy aj sweepu sú pre NQ nevhodné (popoludnie NY → večer); skúsiť Ázia / Londýn ako zdroj likvidity a sweep v NY ráno.
4. **Čo otestovať ďalej.** Smernica (`lliq*`: okná seansy a sweepu, stop / cieľ, vek FVG); pri ~60 obchodoch za rok hranicu 150 z princípu nesplní, kým sa okno nezmení.
5. **Použiteľné?** **V defaultoch predlohy nie** — edge nad poplatkom nie je stabilný po rokoch; šancu má len s nastavením, ktoré nájde smernica (inak vyradiť).
6. **Čo by som pridal.** Likviditu brať z Ázie (20:00–2:00 NY) a sweep v Londýne / NY ráno — klasické ICT poradie, ktoré dá viac obchodov.

<!-- POSUDOK KONIEC -->
