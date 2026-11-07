# Základná analytika — ORB 15/5 1.0 (ES) (`orb15es`)

Zmerané 2026-11-04 na `ES/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/orb15es_PRESIEL_SMERNICAMI_ORB_15_5_ES_1_2026-11-04.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy orb15es \
   --profile .nightsearch/checkup/orb15es_PRESIEL_SMERNICAMI_ORB_15_5_ES_1_2026-11-04.json \
   --pair ES/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 864 obchodov spolu — na štatistiku dosť
- break-even 0.0375 % je nad poplatkom 0.0018 % (rezerva +0.0357 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- odlíšiteľná od náhody (+3.8 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 26. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- 95. percentil max drawdownu 31.2 % (namerané 16.6 % medián) — na účet to treba mať
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'do 0.3818 %' vlastnosti 'Vzdialenosť stopu': 217 obchodov (25.1 %), bez nej by break-even bol o +0.0102 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 176 | +51.86 | 0.0427 | 18.5 | 74.4 | +15/-3 | `20261104-051232-9314e1` |
| 20221001-20231001 | 164 | +37.59 | 0.0348 | 16.8 | 73.2 | +13/-4 | `20261104-051235-2a5f46` |
| 20231001-20241001 | 197 | +88.28 | 0.0543 | 6.3 | 78.2 | +19/-4 | `20261104-051238-70045f` |
| 20240904-20250904 | 174 | +35.50 | 0.0221 | 17.3 | 65.5 | +12/-4 | `20261104-051242-934612` |
| 20250904-20260904 | 166 | +59.69 | 0.0321 | 15.7 | 72.9 | +11/-6 | `20261104-051245-777f83` |

Zisková v **5 z 5** okien, obchodov spolu 864, break-even celkom 0.0375 %. Okná sa prekrývajú, 13 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.61 ATR za 5 barov)
- medián držania 45.7 barov grafu
- winrate 73.26 %, payoff 0.516
- 0.48 obchodov za deň
- šikmosť výnosov -0.671

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 73.1 %, `stop_loss` 26.7 %, `force_exit` 0.1 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'do 0.3818 %' vlastnosti 'Vzdialenosť stopu': 217 obchodov (25.1 %), break-even 0.0096 % oproti 0.0375 % celku. Bez nej by break-even bol 0.0477 % (+0.0102). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.3818 % | 217 | 25.1 % | 71.9 | 0.0096 | 0.0477 | +0.0102 |
| 0.5676 % – 0.8493 % | 216 | 25.0 % | 71.3 | 0.0266 | 0.0412 | +0.0037 |
| 0.3818 % – 0.5676 % | 216 | 25.0 % | 75.9 | 0.0365 | 0.0378 | +0.0003 |
| nad 0.8493 % | 215 | 24.9 % | 74.0 | 0.0845 | 0.0240 | -0.0135 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 15 – 23 | 225 | 26.0 % | 69.8 | 0.0127 | 0.0461 | +0.0086 |
| do 8 | 220 | 25.5 % | 69.5 | 0.0215 | 0.0430 | +0.0055 |
| nad 23 | 205 | 23.7 % | 76.6 | 0.0511 | 0.0333 | -0.0042 |
| 8 – 15 | 214 | 24.8 % | 77.6 | 0.0668 | 0.0278 | -0.0097 |

**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 15 h | 266 | 30.8 % | 72.2 | 0.0194 | 0.0459 | +0.0084 |
| 15 h – 16 h | 192 | 22.2 % | 71.9 | 0.0241 | 0.0413 | +0.0038 |
| nad 18 h | 183 | 21.2 % | 73.8 | 0.0514 | 0.0339 | -0.0036 |
| 16 h – 18 h | 223 | 25.8 % | 75.3 | 0.0604 | 0.0296 | -0.0079 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0375 % | 0.0034 % ± 0.0090 | +3.80 | 99.9 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0375 % | 0.0016 % ± 0.0089 | +4.03 | 100.0 |

Edge je odlisitelny od nahody (3.8 sigma, percentil 99.9).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 209 | 14.2 | 72.7 | 0.0330 | 39 |
| 2022-12 - 2024-03 | 231 | 15.7 | 78.3 | 0.0556 | 85 |
| 2024-03 - 2025-06 | 211 | 14.3 | 69.2 | 0.0380 | 51 |
| 2025-06 - 2026-09 | 213 | 14.5 | 72.3 | 0.0271 | 26 |

Hranice pre úsek veľkosti posledného obdobia: +0.0107 až +0.0654 % (medián 0.0377).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 26. percentile, teda v medziach +0.0107 až +0.0654 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 19** — 2023-12-21T20:55 až 2024-01-29T20:25, spolu +10113.48.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-12-21T20:55 | 2023-12-22T13:44 | +529.08 | +0.22 | `take_profit` |
| 2 | 2023-12-26T17:50 | 2023-12-26T20:04 | +254.03 | +0.11 | `take_profit` |
| 3 | 2023-12-26T20:10 | 2023-12-26T20:25 | +329.02 | +0.14 | `take_profit` |
| 4 | 2023-12-26T20:30 | 2023-12-28T01:37 | +454.01 | +0.19 | `take_profit` |
| 5 | 2024-01-08T15:50 | 2024-01-08T18:47 | +516.63 | +0.22 | `take_profit` |
| 6 | 2024-01-08T18:50 | 2024-01-08T19:32 | +791.61 | +0.33 | `take_profit` |
| 7 | 2024-01-08T19:35 | 2024-01-10T18:04 | +1154.08 | +0.48 | `take_profit` |
| 8 | 2024-01-10T18:10 | 2024-01-10T19:12 | +366.56 | +0.15 | `take_profit` |
| 9 | 2024-01-10T19:15 | 2024-01-11T03:54 | +604.03 | +0.25 | `take_profit` |
| 10 | 2024-01-18T19:25 | 2024-01-18T20:30 | +529.07 | +0.22 | `take_profit` |
| 11 | 2024-01-18T20:40 | 2024-01-19T07:19 | +679.05 | +0.28 | `take_profit` |
| 12 | 2024-01-19T16:10 | 2024-01-19T17:27 | +416.51 | +0.17 | `take_profit` |
| 13 | 2024-01-19T17:30 | 2024-01-19T18:15 | +616.49 | +0.25 | `take_profit` |
| 14 | 2024-01-19T18:20 | 2024-01-19T19:14 | +891.47 | +0.37 | `take_profit` |
| 15 | 2024-01-23T20:00 | 2024-01-23T20:12 | +241.42 | +0.10 | `take_profit` |
| 16 | 2024-01-23T20:15 | 2024-01-23T21:45 | +366.40 | +0.15 | `take_profit` |
| 17 | 2024-01-29T17:35 | 2024-01-29T19:34 | +291.35 | +0.12 | `take_profit` |
| 18 | 2024-01-29T19:50 | 2024-01-29T20:00 | +403.84 | +0.16 | `take_profit` |
| 19 | 2024-01-29T20:05 | 2024-01-29T20:25 | +678.82 | +0.27 | `take_profit` |

**Straty za sebou: 6** — 2026-06-15T15:50 až 2026-06-26T19:59, spolu -14429.02.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-06-15T15:50 | 2026-06-16T14:31 | -1813.38 | -0.47 | `stop_loss` |
| 2 | 2026-06-18T14:50 | 2026-06-19T04:02 | -1663.25 | -0.44 | `stop_loss` |
| 3 | 2026-06-19T14:55 | 2026-06-21T22:00 | -1088.26 | -0.29 | `stop_loss` |
| 4 | 2026-06-24T14:50 | 2026-06-24T17:16 | -2175.59 | -0.58 | `stop_loss` |
| 5 | 2026-06-25T14:55 | 2026-06-26T02:24 | -4213.04 | -1.13 | `stop_loss` |
| 6 | 2026-06-26T15:30 | 2026-06-26T19:59 | -3475.50 | -0.93 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0375 %**, medián 0.0375 %, 90 % interval 0.0239–0.0514 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 16.6 %, 95. percentil 31.2 %, najhorší 75.7 %
- najdlhšia séria strát: medián 5, 95. percentil 7 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

> **Posudok je starší než čísla** (písal sa k vzorke `85348268`, tu je `4d9a0b32`). Nech ho AI prepíše — čísla nižšie sa medzitým zmenili.

<!-- POSUDOK cisla=85348268 -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na ES, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Intraday index futures od 9:45 NY, jeden obchod denne; na zlate OR 9:30–9:45 nemá zmysel otvorenia akciovej burzy, čísla tam ukazujú skôr šum. Tu na ES — rovnaká logika ako MNQ, prahy v ATR sa prispôsobia.
2. **Má potenciál?** Zisková v 3 z 5 okien, 1161 obchodov (~232 za rok), break-even 0.0075 % (nad poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 42.46 % pri payoffe 1.434. Odložený rok 25/26: +26.17 % PnL, break-even 0.0033 %. Kladné okná sú skôr vlastnosť vzorky ako stabilný jav.
3. **Čo dorobiť.** Skúsiť OR 5 / 30 / 60 min a cieľ RR 0,75–1,5; filter predošlého dňa a knôtu majú byť v mriežke oboma smermi; pre prop koniec dňa.
4. **Čo otestovať ďalej.** Smernica (mriežka glsearch `orb15*`: dĺžka OR, RR, filtre, trend EMA, limit / IBS / pin bar); rozhodne odložený rok 25/26, ktorý je pri MNQ v defaultoch stratový.
5. **Použiteľné?** **V defaultoch predlohy nie** — edge nad poplatkom nie je stabilný po rokoch; šancu má len s nastavením, ktoré nájde smernica (inak vyradiť).
6. **Čo by som pridal.** Smer dňa z VWAP od 9:30 alebo z polohy voči včerajšiemu zavretiu — ORB bez kontextu chytá aj falošné prierazy rána.

<!-- POSUDOK KONIEC -->
