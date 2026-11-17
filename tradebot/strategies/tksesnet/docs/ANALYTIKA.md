# Základná analytika — TKS 1.0 ES (C# jadro) (`tksesnet`)

Zmerané 2026-11-17 na `ES/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/tksesnet/configs/es_databento_3m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy tksesnet \
   --profile tradebot/strategies/tksesnet/configs/es_databento_3m.json \
   --pair ES/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 841 obchodov spolu — na štatistiku dosť
- break-even 0.0157 % je nad poplatkom 0.0018 % (rezerva +0.0139 bodu)
- edge nad poplatkom v 97 % bootstrapových vzoriek
- odlíšiteľná od náhody (+2.5 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 36. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- zisková v 4 z 5 referenčných okien (20231001-20241001 v strate)
- 95. percentil max drawdownu 49.2 % (namerané 23.5 % medián) — na účet to treba mať
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'FOMC' vlastnosti 'Makro udalosť v ten deň': 19 obchodov (2.3 %), bez nej by break-even bol o +0.0207 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 167 | +38.18 | 0.0338 | 14.5 | 71.3 | +11/-4 | `20261117-092601-a3c886` |
| 20221001-20231001 | 164 | +15.46 | 0.0154 | 12.2 | 68.9 | +12/-4 | `20261117-092633-0cff62` |
| 20231001-20241001 | 182 | -1.10 | 0.0010 | 22.7 | 62.6 | +13/-5 | `20261117-093103-26183f` |
| 20240904-20250904 | 168 | +28.58 | 0.0188 | 17.7 | 73.2 | +13/-3 | `20261117-093600-c47e53` |
| 20250904-20260904 | 169 | +19.61 | 0.0117 | 20.8 | 66.3 | +12/-3 | `20261117-093931-bade5f` |

Zisková v **4 z 5** okien, obchodov spolu 841, break-even celkom 0.0157 %. Okná sa prekrývajú, 9 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.39 ATR za 5 barov)
- medián držania 17.7 barov grafu
- winrate 68.61 %, payoff 0.543
- 0.47 obchodov za deň
- šikmosť výnosov -0.754

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 68.6 %, `stop_loss` 31.3 %, `force_exit` 0.1 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'FOMC' vlastnosti 'Makro udalosť v ten deň': 19 obchodov (2.3 %), break-even -0.0189 % oproti 0.0157 % celku. Bez nej by break-even bol 0.0164 % (+0.0207). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| FOMC | 19 | 2.3 % | 57.9 | -0.0189 | 0.0164 | +0.0007 |
| žiadna | 746 | 88.7 % | 68.8 | 0.0131 | 0.0364 | +0.0207 |
| CPI | 35 | 4.2 % | 65.7 | 0.0294 | 0.0151 | -0.0006 |
| NFP | 40 | 4.8 % | 72.5 | 0.0545 | 0.0137 | -0.0020 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| pred vyhlásením | 20 | 2.4 % | 60.0 | 0.0112 | 0.0158 | +0.0001 |
| bez udalosti | 746 | 88.7 % | 68.8 | 0.0131 | 0.0364 | +0.0207 |
| po vyhlásení | 75 | 8.9 % | 69.3 | 0.0429 | 0.0130 | -0.0027 |

**Smer** (riadi `tradeDirection`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| long | 535 | 63.6 % | 66.9 | 0.0099 | 0.0261 | +0.0104 |
| short | 306 | 36.4 % | 71.6 | 0.0261 | 0.0099 | -0.0058 |

Parametre, ktorými sa dá s tým niečo spraviť: `rrRatio`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0157 % | 0.0004 % ± 0.0062 | +2.48 | 99.5 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0157 % | -0.0002 % ± 0.0060 | +2.64 | 99.6 |

Edge je odlisitelny od nahody (2.5 sigma, percentil 99.5).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 205 | 13.9 | 73.2 | 0.0450 | 98 |
| 2022-12 - 2024-03 | 208 | 14.1 | 67.8 | 0.0037 | 24 |
| 2024-03 - 2025-06 | 213 | 14.4 | 64.8 | 0.0098 | 35 |
| 2025-06 - 2026-09 | 215 | 14.6 | 68.8 | 0.0108 | 36 |

Hranice pre úsek veľkosti posledného obdobia: -0.0083 až +0.0405 % (medián 0.0161).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 36. percentile, teda v medziach -0.0083 až +0.0405 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 13** — 2023-10-16T13:51 až 2023-11-08T14:34, spolu +6852.42, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-10-16T13:51 | 2023-10-16T14:13 | +429.80 | +0.20 | `take_profit` |
| 2 | 2023-10-17T14:27 | 2023-10-17T15:15 | +592.29 | +0.27 | `take_profit` |
| 3 | 2023-10-20T14:12 | 2023-10-20T14:57 | +680.01 | +0.32 | `take_profit` |
| 4 | 2023-10-20T17:30 | 2023-10-20T18:15 | +592.50 | +0.28 | `take_profit` |
| 5 | 2023-10-24T14:00 | 2023-10-24T14:39 | +367.49 | +0.17 | `take_profit` |
| 6 | 2023-10-25T14:54 | 2023-10-25T16:07 | +630.07 | +0.30 | `take_profit` |
| 7 | 2023-10-25T17:06 | 2023-10-25T17:44 | +417.61 | +0.20 | `take_profit` |
| 8 | 2023-10-27T13:51 | 2023-10-27T16:50 | +492.71 | +0.24 | `take_profit` |
| 9 | 2023-10-30T17:54 | 2023-10-31T17:30 | +755.14 | +0.36 | `take_profit` |
| 10 | 2023-10-31T17:36 | 2023-10-31T19:00 | +517.62 | +0.25 | `take_profit` |
| 11 | 2023-11-01T13:51 | 2023-11-01T14:20 | +455.07 | +0.22 | `take_profit` |
| 12 | 2023-11-03T14:33 | 2023-11-03T15:44 | +379.83 | +0.17 | `take_profit` |
| 13 | 2023-11-07T15:33 | 2023-11-08T14:34 | +542.28 | +0.25 | `take_profit` |

**Straty za sebou: 5** — 2024-06-24T15:00 až 2024-07-05T14:09, spolu -4161.18, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-06-24T15:00 | 2024-06-24T17:33 | -1147.22 | -0.41 | `stop_loss` |
| 2 | 2024-06-25T15:21 | 2024-06-25T16:23 | -497.20 | -0.18 | `stop_loss` |
| 3 | 2024-06-28T15:39 | 2024-06-28T16:06 | -397.25 | -0.14 | `stop_loss` |
| 4 | 2024-07-01T14:15 | 2024-07-01T19:56 | -1597.19 | -0.58 | `stop_loss` |
| 5 | 2024-07-05T13:57 | 2024-07-05T14:09 | -522.32 | -0.19 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0157 %**, medián 0.0156 %, 90 % interval 0.0033–0.0281 %
- P(edge > poplatok) = **96.8 %**
- max drawdown: medián 23.5 %, 95. percentil 49.2 %, najhorší 100.0 %
- najdlhšia séria strát: medián 5, 95. percentil 7 obchodov
- pravdepodobnosť ruiny účtu: 0.1 %

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
<!-- POSUDOK cisla=4e0e38e7 -->

Pozor: analytika je na **východisku** — nastavenie TKS 1 z MNQ bez zmeny (len seansa trhu); kolo 1 ladenia (17. 11. 2026, hyperopt hraníc Kompasu, potvrdenia a swingu) je v iCloud TKS-TRHY a v histórii hyperoptov. Po smernici sa analytika prepíše na víťaza.

C# kópia — obchody bar po bare zhodné s Python predlohou (parita), posudok platí rovnako.

1. **Na čo sa to hodí:** S&P 500 futures (ES, na menší účet MES — 1 ES má 95. percentil prepadu ~49 % z 60 000 $, MES desatinu), 3m, seansa NY 9:30–16:00, trendové dni. Rovnaký charakter ako TKS na MNQ (prierazy v smere trendu dňa, WR ~69 %, TP 0,5 R).
2. **Potenciál áno.** Bez jediného ladenia 4 z 5 rokov v zisku, break-even 0,0157 % je ~9× poplatok, +2,5 sigma proti náhode aj proti náhode v tých istých hodinách, posledné obdobie na 36. percentile (nič neslabne). Jediný stratový rok (23/24) je tesne pod nulou. Toto je najsilnejší prenos Kompasu mimo Nasdaqu.
3. **Dorobiť:** hranice Kompasu a swing pre ES (kolo 1: lo 25 / hi 70 / 4 sviečky / swing 9 → všetky roky ladenia PF 1,20–1,37, odložený 1,10); okno vstupov a prestávku pre ES (prevzaté z MNQ); FOMC dni (19 obchodov, break-even −0,019 %) — skúsiť filter makra.
4. **Otestovať:** kolo 2 `cli hyperopt --strategy tksesnet --engine multicharts --param entryStartMin=0:90:15 --param entryEndMin=180:330:30 --param lookbackDays=10:25:5 … --windows (4 roky) --aggregate min --select plateau`; `cli plateau <id>`; krok 8 na US500 (Dukascopy); `python -m tester.robust` (2× poplatok, vstup o sviečku neskôr). Rozhodne: odložený rok ≥ 1,2 a plató ≥ 80 %.
5. **Použiteľné — kandidát.** Nie ešte na live, ale jediný z nových trhov, kde edge vidno aj bez ladenia; ide do smernice ako prvý.
6. **Pridal by som** spoločný Kompas NQ + ES (dva indexy v zhode = silnejší trend dňa) a filter dní FOMC.

<!-- POSUDOK KONIEC -->
