# Základná analytika — LONDON LIQUIDITY IFVG 1.0 (ES) (`lliqes`)

Zmerané 2026-11-05 na `ES/USD` 1m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/lliqes_PRESIEL_SMERNICAMI_LONDON_IFVG_ES_1_2026-11-05.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy lliqes \
   --profile .nightsearch/checkup/lliqes_PRESIEL_SMERNICAMI_LONDON_IFVG_ES_1_2026-11-05.json \
   --pair ES/USD \
   --timeframe 1m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 929 obchodov spolu — na štatistiku dosť
- break-even 0.0059 % je nad poplatkom 0.0018 % (rezerva +0.0041 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 10.1 %
- odlíšiteľná od náhody (+7.1 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 68. percentile toho, čo stratégia vyrobí sama od seba)
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 3 z 5 referenčných okien (20221001-20231001, 20231001-20241001 v strate)
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 186 | +8.26 | 0.0080 | 6.2 | 91.4 | +30/-2 | `20261105-051346-bf5df0` |
| 20221001-20231001 | 172 | -0.13 | 0.0016 | 4.2 | 83.1 | +20/-2 | `20261105-051352-890f17` |
| 20231001-20241001 | 192 | -1.35 | 0.0009 | 4.5 | 83.8 | +23/-3 | `20261105-051358-34a8c6` |
| 20240904-20250904 | 202 | +15.29 | 0.0094 | 3.7 | 92.6 | +25/-1 | `20261105-051405-20398c` |
| 20250904-20260904 | 194 | +11.57 | 0.0068 | 2.4 | 90.7 | +26/-2 | `20261105-051411-0c7588` |

Zisková v **3 z 5** okien, obchodov spolu 929, break-even celkom 0.0059 %. Okná sa prekrývajú, 17 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.25 ATR za 5 barov)
- medián držania 1 barov grafu
- winrate 88.48 %, payoff 0.191
- 0.52 obchodov za deň
- šikmosť výnosov -4.662

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 89.3 %, `stop_loss` 10.7 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0021 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bežný deň | 862 | 92.8 % | 88.6 | 0.0057 | 0.0080 | +0.0021 |
| deň po sviatku | 29 | 3.1 % | 93.1 | 0.0103 | 0.0057 | -0.0002 |
| deň pred sviatkom | 14 | 1.5 % | 100.0 | 0.0138 | 0.0057 | -0.0002 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 0.8105 | 232 | 25.0 % | 87.1 | 0.0004 | 0.0077 | +0.0018 |
| 0.4375 – 0.6204 | 232 | 25.0 % | 87.9 | 0.0057 | 0.0059 | +0.0000 |
| do 0.4375 | 233 | 25.1 % | 84.5 | 0.0060 | 0.0058 | -0.0001 |
| 0.6204 – 0.8105 | 232 | 25.0 % | 94.4 | 0.0114 | 0.0041 | -0.0018 |

**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.0326 | 234 | 25.2 % | 89.3 | 0.0029 | 0.0069 | +0.0010 |
| 0.0798 – 0.1461 | 233 | 25.1 % | 87.5 | 0.0056 | 0.0060 | +0.0001 |
| nad 0.1461 | 231 | 24.9 % | 84.0 | 0.0057 | 0.0059 | +0.0000 |
| 0.0326 – 0.0798 | 231 | 24.9 % | 93.1 | 0.0092 | 0.0048 | -0.0011 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0059 % | -0.0004 % ± 0.0009 | +7.06 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0059 % | -0.0004 % ± 0.0010 | +6.53 | 100.0 |

Edge je odlisitelny od nahody (7.1 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 221 | 15.0 | 91.9 | 0.0092 | 87 |
| 2022-12 - 2024-03 | 227 | 15.4 | 81.1 | 0.0002 | 3 |
| 2024-03 - 2025-06 | 244 | 16.5 | 89.8 | 0.0064 | 59 |
| 2025-06 - 2026-09 | 237 | 16.1 | 91.1 | 0.0071 | 68 |

Hranice pre úsek veľkosti posledného obdobia: +0.0014 až +0.0105 % (medián 0.0060).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 68. percentile, teda v medziach +0.0014 až +0.0105 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 41** — 2022-08-11T14:42 až 2022-10-24T13:52, spolu +3968.66.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-08-11T14:42 | 2022-08-11T14:42 | +67.55 | +0.03 | `take_profit` |
| 2 | 2022-08-12T13:49 | 2022-08-12T14:00 | +55.08 | +0.03 | `take_profit` |
| 3 | 2022-08-15T14:49 | 2022-08-15T14:49 | +67.50 | +0.03 | `take_profit` |
| 4 | 2022-08-16T14:48 | 2022-08-16T14:51 | +67.47 | +0.03 | `take_profit` |
| 5 | 2022-08-17T15:02 | 2022-08-17T15:12 | +55.01 | +0.03 | `take_profit` |
| 6 | 2022-08-19T14:02 | 2022-08-19T14:04 | +80.05 | +0.04 | `take_profit` |
| 7 | 2022-08-23T14:36 | 2022-08-23T14:36 | +92.72 | +0.04 | `take_profit` |
| 8 | 2022-08-24T14:39 | 2022-08-24T14:40 | +80.24 | +0.04 | `take_profit` |
| 9 | 2022-08-25T13:53 | 2022-08-25T13:53 | +67.70 | +0.03 | `take_profit` |
| 10 | 2022-08-26T14:10 | 2022-08-26T14:10 | +180.12 | +0.09 | `take_profit` |
| 11 | 2022-08-29T13:44 | 2022-08-29T13:45 | +80.42 | +0.04 | `take_profit` |
| 12 | 2022-08-31T15:20 | 2022-08-31T15:21 | +105.51 | +0.05 | `take_profit` |
| 13 | 2022-09-01T15:36 | 2022-09-01T15:36 | +105.61 | +0.05 | `take_profit` |
| 14 | 2022-09-02T14:57 | 2022-09-02T16:20 | +80.48 | +0.04 | `take_profit` |
| 15 | 2022-09-05T23:23 | 2022-09-05T23:26 | +5.59 | +0.00 | `take_profit` |
| 16 | 2022-09-06T15:07 | 2022-09-06T15:08 | +105.59 | +0.05 | `take_profit` |
| 17 | 2022-09-07T14:07 | 2022-09-07T14:09 | +105.62 | +0.05 | `take_profit` |
| 18 | 2022-09-08T13:42 | 2022-09-08T13:42 | +118.05 | +0.06 | `take_profit` |
| 19 | 2022-09-13T13:40 | 2022-09-13T13:41 | +105.42 | +0.05 | `take_profit` |
| 20 | 2022-09-14T14:39 | 2022-09-14T14:42 | +130.55 | +0.07 | `take_profit` |
| 21 | 2022-09-15T13:35 | 2022-09-15T13:37 | +80.57 | +0.04 | `take_profit` |
| 22 | 2022-09-16T14:06 | 2022-09-16T14:06 | +105.71 | +0.05 | `take_profit` |
| 23 | 2022-09-19T15:32 | 2022-09-19T15:35 | +68.19 | +0.04 | `take_profit` |
| 24 | 2022-09-21T13:33 | 2022-09-21T13:33 | +43.17 | +0.02 | `take_profit` |
| 25 | 2022-09-22T14:30 | 2022-09-22T14:32 | +105.85 | +0.06 | `take_profit` |
| 26 | 2022-09-23T15:22 | 2022-09-23T15:24 | +93.48 | +0.05 | `take_profit` |
| 27 | 2022-09-26T14:46 | 2022-09-26T14:47 | +105.98 | +0.06 | `take_profit` |
| 28 | 2022-09-27T13:46 | 2022-09-27T13:49 | +80.97 | +0.04 | `take_profit` |
| 29 | 2022-09-28T14:03 | 2022-09-28T14:05 | +168.56 | +0.09 | `take_profit` |
| 30 | 2022-09-30T13:43 | 2022-09-30T13:43 | +156.10 | +0.09 | `take_profit` |
| 31 | 2022-10-05T20:01 | 2022-10-05T20:02 | +93.33 | +0.05 | `take_profit` |
| 32 | 2022-10-06T14:50 | 2022-10-06T14:52 | +105.86 | +0.06 | `take_profit` |
| 33 | 2022-10-10T15:13 | 2022-10-10T15:14 | +93.64 | +0.05 | `take_profit` |
| 34 | 2022-10-11T14:26 | 2022-10-11T14:26 | +93.69 | +0.05 | `take_profit` |
| 35 | 2022-10-12T13:36 | 2022-10-12T13:36 | +106.18 | +0.06 | `take_profit` |
| 36 | 2022-10-13T13:34 | 2022-10-13T13:34 | +143.83 | +0.08 | `take_profit` |
| 37 | 2022-10-18T20:12 | 2022-10-18T20:16 | +93.42 | +0.05 | `take_profit` |
| 38 | 2022-10-19T20:19 | 2022-10-19T20:30 | +93.49 | +0.05 | `take_profit` |
| 39 | 2022-10-20T15:46 | 2022-10-20T15:46 | +55.95 | +0.03 | `take_profit` |
| 40 | 2022-10-21T15:14 | 2022-10-21T15:20 | +143.53 | +0.08 | `take_profit` |
| 41 | 2022-10-24T13:50 | 2022-10-24T13:52 | +180.85 | +0.10 | `take_profit` |

**Straty za sebou: 3** — 2023-12-19T14:47 až 2023-12-21T23:32, spolu -287.81.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-12-19T14:47 | 2023-12-19T14:48 | -145.93 | -0.06 | `stop_loss` |
| 2 | 2023-12-20T15:28 | 2023-12-20T15:30 | -95.96 | -0.04 | `stop_loss` |
| 3 | 2023-12-21T23:29 | 2023-12-21T23:32 | -45.91 | -0.02 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0059 %**, medián 0.0059 %, 90 % interval 0.0035–0.0082 %
- P(edge > poplatok) = **99.8 %**
- max drawdown: medián 5.4 %, 95. percentil 10.1 %, najhorší 23.8 %
- najdlhšia séria strát: medián 3, 95. percentil 3 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

> **Posudok je starší než čísla** (písal sa k vzorke `4d47f85b`, tu je `fb1d35e5`). Nech ho AI prepíše — čísla nižšie sa medzitým zmenili.

<!-- POSUDOK cisla=4d47f85b -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na ES, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Večerný sweep high / low popoludnia NY (19:15–23:45) a inverzný FVG — málo obchodov (~60 / rok na MNQ), likvidita v Ázii je tenká. Tu na ES — rovnaká logika ako MNQ, prahy v ATR sa prispôsobia.
2. **Má potenciál?** Zisková v 2 z 5 okien, 306 obchodov (~61 za rok), break-even 0.0018 % (pod poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 51.31 % pri payoffe 0.952. Odložený rok 25/26: +11.79 % PnL, break-even 0.0040 %. Kladné okná sú skôr vlastnosť vzorky ako stabilný jav.
3. **Čo dorobiť.** Okno seansy aj sweepu sú pre NQ nevhodné (popoludnie NY → večer); skúsiť Ázia / Londýn ako zdroj likvidity a sweep v NY ráno.
4. **Čo otestovať ďalej.** Smernica (`lliq*`: okná seansy a sweepu, stop / cieľ, vek FVG); pri ~60 obchodoch za rok hranicu 150 z princípu nesplní, kým sa okno nezmení.
5. **Použiteľné?** **V defaultoch predlohy nie** — edge nad poplatkom nie je stabilný po rokoch; šancu má len s nastavením, ktoré nájde smernica (inak vyradiť).
6. **Čo by som pridal.** Likviditu brať z Ázie (20:00–2:00 NY) a sweep v Londýne / NY ráno — klasické ICT poradie, ktoré dá viac obchodov.

<!-- POSUDOK KONIEC -->
