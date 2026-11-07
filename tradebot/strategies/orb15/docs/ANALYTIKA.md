# Základná analytika — ORB 15/5 1.0 (`orb15`)

Zmerané 2026-11-06 na `MNQ/USD` 15m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/orb15_PRESIEL_SMERNICAMI_ORB_15_5_MNQ_1_2026-11-06.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy orb15 \
   --profile .nightsearch/checkup/orb15_PRESIEL_SMERNICAMI_ORB_15_5_MNQ_1_2026-11-06.json \
   --pair MNQ/USD \
   --timeframe 15m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 729 obchodov spolu — na štatistiku dosť
- break-even 0.0643 % je nad poplatkom 0.0018 % (rezerva +0.0625 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 8.8 %
- odlíšiteľná od náhody (+4.4 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 64. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'deň po sviatku' vlastnosti 'Sviatok na burze v USA': 20 obchodov (2.7 %), bez nej by break-even bol o +0.0272 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 160 | +10.33 | 0.0711 | 3.8 | 65.6 | +10/-4 | `20261106-051602-437354` |
| 20221001-20231001 | 152 | +2.52 | 0.0204 | 2.7 | 63.2 | +10/-5 | `20261106-051606-a62fc5` |
| 20231001-20241001 | 151 | +11.35 | 0.0655 | 4.3 | 64.2 | +14/-4 | `20261106-051609-1f780d` |
| 20240904-20250904 | 137 | +11.41 | 0.0602 | 3.6 | 63.5 | +13/-4 | `20261106-051612-005d5c` |
| 20250904-20260904 | 138 | +21.63 | 0.0902 | 3.8 | 62.3 | +13/-5 | `20261106-051615-94ba8c` |

Zisková v **5 z 5** okien, obchodov spolu 729, break-even celkom 0.0643 %. Okná sa prekrývajú, 9 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.62 ATR za 5 barov)
- medián držania 13.5 barov grafu
- winrate 63.79 %, payoff 0.822
- 0.41 obchodov za deň
- šikmosť výnosov -0.321

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 63.8 %, `stop_loss` 36.1 %, `force_exit` 0.1 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'deň po sviatku' vlastnosti 'Sviatok na burze v USA': 20 obchodov (2.7 %), break-even 0.0074 % oproti 0.0643 % celku. Bez nej by break-even bol 0.0661 % (+0.0272). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| deň po sviatku | 20 | 2.7 % | 55.0 | 0.0074 | 0.0661 | +0.0018 |
| bežný deň | 692 | 94.9 % | 64.0 | 0.0626 | 0.0915 | +0.0272 |
| deň pred sviatkom | 9 | 1.2 % | 77.8 | 0.3626 | 0.0594 | -0.0049 |

**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.4824 % | 183 | 25.1 % | 61.2 | 0.0039 | 0.0871 | +0.0228 |
| 0.4824 % – 0.735 % | 182 | 25.0 % | 64.3 | 0.0335 | 0.0744 | +0.0101 |
| 0.735 % – 1.0624 % | 182 | 25.0 % | 63.7 | 0.0492 | 0.0693 | +0.0050 |
| nad 1.0624 % | 182 | 25.0 % | 65.9 | 0.1853 | 0.0281 | -0.0362 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.931 – 0.9702 | 182 | 25.0 % | 56.6 | 0.0023 | 0.0849 | +0.0206 |
| do 0.851 | 183 | 25.1 % | 65.0 | 0.0673 | 0.0633 | -0.0010 |
| 0.851 – 0.931 | 182 | 25.0 % | 66.5 | 0.0741 | 0.0611 | -0.0032 |
| nad 0.9702 | 182 | 25.0 % | 67.0 | 0.1140 | 0.0480 | -0.0163 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0643 % | 0.0000 % ± 0.0146 | +4.40 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0643 % | -0.0005 % ± 0.0142 | +4.57 | 100.0 |

Edge je odlisitelny od nahody (4.4 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 192 | 13.0 | 65.1 | 0.0642 | 54 |
| 2022-12 - 2024-03 | 199 | 13.5 | 61.8 | 0.0148 | 7 |
| 2024-03 - 2025-06 | 167 | 11.3 | 67.7 | 0.0941 | 79 |
| 2025-06 - 2026-09 | 171 | 11.6 | 60.8 | 0.0749 | 64 |

Hranice pre úsek veľkosti posledného obdobia: +0.0026 až +0.1247 % (medián 0.0613).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 64. percentile, teda v medziach +0.0026 až +0.1247 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 14** — 2024-08-01T15:00 až 2024-09-06T20:35, spolu +3760.31.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-08-01T15:00 | 2024-08-01T16:39 | +486.15 | +1.26 | `take_profit` |
| 2 | 2024-08-07T16:00 | 2024-08-07T16:04 | +234.21 | +0.64 | `take_profit` |
| 3 | 2024-08-08T14:30 | 2024-08-08T17:46 | +285.20 | +0.78 | `take_profit` |
| 4 | 2024-08-09T17:15 | 2024-08-12T14:26 | +274.19 | +0.74 | `take_profit` |
| 5 | 2024-08-12T14:30 | 2024-08-13T12:30 | +248.18 | +0.66 | `take_profit` |
| 6 | 2024-08-13T15:15 | 2024-08-13T16:20 | +111.67 | +0.29 | `take_profit` |
| 7 | 2024-08-13T17:15 | 2024-08-15T12:30 | +306.15 | +0.80 | `take_profit` |
| 8 | 2024-08-16T14:30 | 2024-08-16T16:33 | +114.12 | +0.29 | `take_profit` |
| 9 | 2024-08-19T15:15 | 2024-08-19T17:59 | +138.12 | +0.35 | `take_profit` |
| 10 | 2024-08-22T15:45 | 2024-08-27T13:45 | +458.63 | +1.17 | `take_profit` |
| 11 | 2024-08-28T15:00 | 2024-08-28T15:12 | +156.14 | +0.40 | `take_profit` |
| 12 | 2024-09-03T15:00 | 2024-09-03T19:38 | +333.66 | +0.87 | `take_profit` |
| 13 | 2024-09-05T15:15 | 2024-09-06T01:01 | +262.17 | +0.69 | `take_profit` |
| 14 | 2024-09-06T14:45 | 2024-09-06T20:35 | +351.70 | +0.95 | `take_profit` |

**Straty za sebou: 5** — 2023-06-28T14:45 až 2023-07-07T15:59, spolu -677.86, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-06-28T14:45 | 2023-06-29T14:10 | -280.56 | -0.92 | `stop_loss` |
| 2 | 2023-06-30T14:30 | 2023-06-30T15:30 | -86.58 | -0.28 | `stop_loss` |
| 3 | 2023-06-30T17:00 | 2023-06-30T20:00 | -92.08 | -0.30 | `stop_loss` |
| 4 | 2023-07-05T14:45 | 2023-07-05T15:20 | -84.08 | -0.27 | `stop_loss` |
| 5 | 2023-07-07T14:45 | 2023-07-07T15:59 | -134.57 | -0.44 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0643 %**, medián 0.0643 %, 90 % interval 0.0352–0.0935 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 4.9 %, 95. percentil 8.8 %, najhorší 18.8 %
- najdlhšia séria strát: medián 5, 95. percentil 7 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

> **Posudok je starší než čísla** (písal sa k vzorke `e3619529`, tu je `a2374023`). Nech ho AI prepíše — čísla nižšie sa medzitým zmenili.

<!-- POSUDOK cisla=e3619529 -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na MNQ, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Intraday index futures od 9:45 NY, jeden obchod denne; na zlate OR 9:30–9:45 nemá zmysel otvorenia akciovej burzy, čísla tam ukazujú skôr šum.
2. **Má potenciál?** Zisková v 4 z 5 okien, 1167 obchodov (~233 za rok), break-even 0.0146 % (nad poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 44.99 % pri payoffe 1.338. Odložený rok 25/26: -38.18 % PnL, break-even -0.0133 %. Kladné okná sú skôr vlastnosť vzorky ako stabilný jav.
3. **Čo dorobiť.** Skúsiť OR 5 / 30 / 60 min a cieľ RR 0,75–1,5; filter predošlého dňa a knôtu majú byť v mriežke oboma smermi; pre prop koniec dňa.
4. **Čo otestovať ďalej.** Smernica (mriežka glsearch `orb15*`: dĺžka OR, RR, filtre, trend EMA, limit / IBS / pin bar); rozhodne odložený rok 25/26, ktorý je pri MNQ v defaultoch stratový.
5. **Použiteľné?** **V defaultoch predlohy nie** — edge nad poplatkom nie je stabilný po rokoch; šancu má len s nastavením, ktoré nájde smernica (inak vyradiť).
6. **Čo by som pridal.** Smer dňa z VWAP od 9:30 alebo z polohy voči včerajšiemu zavretiu — ORB bez kontextu chytá aj falošné prierazy rána.

<!-- POSUDOK KONIEC -->
