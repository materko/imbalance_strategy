# Základná analytika — TKS 1.0 (6E) (`tkseur`)

Zmerané 2026-11-17 na `6E/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/tkseur/configs/6e_databento_3m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy tkseur \
   --profile tradebot/strategies/tkseur/configs/6e_databento_3m.json \
   --pair 6E/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 1381 obchodov spolu — na štatistiku dosť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 1 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20240904-20250904, 20250904-20260904 v strate)
- break-even -0.0004 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 19 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 44.5 % (namerané 23.0 % medián) — na účet to treba mať
- nie je lepšia než náhodný vstup za tých istých pravidiel (-0.0 sigma) — výber vstupu nepridáva nič
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 271 | -0.71 | 0.0012 | 9.8 | 69.4 | +14/-4 | `20261117-114722-17d65e` |
| 20221001-20231001 | 290 | -14.80 | -0.0096 | 15.3 | 62.4 | +10/-5 | `20261117-114725-f1e1c7` |
| 20231001-20241001 | 303 | +8.13 | 0.0077 | 5.7 | 71.0 | +16/-3 | `20261117-114728-cd4e1c` |
| 20240904-20250904 | 276 | -3.84 | -0.0013 | 9.1 | 65.2 | +10/-8 | `20261117-114731-682ada` |
| 20250904-20260904 | 263 | -0.91 | 0.0010 | 6.3 | 66.5 | +13/-4 | `20261117-114734-c10d48` |

Zisková v **1 z 5** okien, obchodov spolu 1381, break-even celkom -0.0004 %. Okná sa prekrývajú, 22 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.62 ATR za 5 barov)
- medián držania 16.3 barov grafu
- winrate 66.76 %, payoff 0.468
- 0.77 obchodov za deň
- šikmosť výnosov -1.28

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 66.8 %, `stop_loss` 33.2 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0053 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| žiadna | 1183 | 85.7 % | 66.6 | -0.0013 | 0.0049 | +0.0053 |
| NFP | 75 | 5.4 % | 65.3 | 0.0037 | -0.0006 | -0.0002 |
| FOMC | 40 | 2.9 % | 70.0 | 0.0051 | -0.0005 | -0.0001 |
| CPI | 83 | 6.0 % | 68.7 | 0.0060 | -0.0008 | -0.0004 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bez udalosti | 1183 | 85.7 % | 66.6 | -0.0013 | 0.0049 | +0.0053 |
| pred vyhlásením | 121 | 8.8 % | 66.9 | -0.0000 | -0.0004 | +0.0000 |
| po vyhlásení | 77 | 5.6 % | 68.8 | 0.0127 | -0.0012 | -0.0008 |

**Plánovaný RR** (riadi `rrRatio`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.5 R – 0.52 R | 215 | 15.6 % | 61.4 | -0.0160 | 0.0025 | +0.0029 |
| 0.48 R – 0.5 R | 488 | 35.3 % | 66.2 | 0.0001 | -0.0006 | -0.0002 |
| nad 0.52 R | 283 | 20.5 % | 64.7 | 0.0003 | -0.0006 | -0.0002 |
| do 0.48 R | 395 | 28.6 % | 71.9 | 0.0070 | -0.0033 | -0.0029 |

Parametre, ktorými sa dá s tým niečo spraviť: `rrRatio`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0004 % | -0.0004 % ± 0.0017 | -0.01 | 51.1 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0004 % | -0.0008 % ± 0.0018 | +0.22 | 58.1 |

Neodlisitelne od nahody (-0.0 sigma, percentil 51.1). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 329 | 22.4 | 66.0 | -0.0079 | 10 |
| 2022-12 - 2024-03 | 371 | 25.2 | 66.6 | 0.0011 | 62 |
| 2024-03 - 2025-06 | 355 | 24.1 | 67.3 | 0.0023 | 70 |
| 2025-06 - 2026-09 | 326 | 22.1 | 67.2 | 0.0023 | 69 |

Hranice pre úsek veľkosti posledného obdobia: -0.0090 až +0.0080 % (medián -0.0002).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 69. percentile, teda v medziach -0.0090 až +0.0080 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 16** — 2023-10-11T13:30 až 2023-10-31T08:22, spolu +2219.28.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-10-11T13:30 | 2023-10-12T06:41 | +232.82 | +0.17 | `take_profit` |
| 2 | 2023-10-12T12:36 | 2023-10-12T13:33 | +239.10 | +0.18 | `take_profit` |
| 3 | 2023-10-16T14:45 | 2023-10-17T11:11 | +151.61 | +0.11 | `take_profit` |
| 4 | 2023-10-17T11:12 | 2023-10-17T11:36 | +120.35 | +0.09 | `take_profit` |
| 5 | 2023-10-17T14:15 | 2023-10-17T14:23 | +164.10 | +0.12 | `take_profit` |
| 6 | 2023-10-19T11:06 | 2023-10-19T11:37 | +101.61 | +0.08 | `take_profit` |
| 7 | 2023-10-20T08:27 | 2023-10-20T08:40 | +95.34 | +0.07 | `take_profit` |
| 8 | 2023-10-20T13:06 | 2023-10-20T14:38 | +157.84 | +0.12 | `take_profit` |
| 9 | 2023-10-23T07:42 | 2023-10-23T07:49 | +70.34 | +0.05 | `take_profit` |
| 10 | 2023-10-23T13:51 | 2023-10-23T13:57 | +32.84 | +0.02 | `take_profit` |
| 11 | 2023-10-25T07:27 | 2023-10-25T09:27 | +151.60 | +0.11 | `take_profit` |
| 12 | 2023-10-25T10:12 | 2023-10-26T02:16 | +195.36 | +0.15 | `take_profit` |
| 13 | 2023-10-27T13:09 | 2023-10-27T13:33 | +214.10 | +0.16 | `take_profit` |
| 14 | 2023-10-27T14:54 | 2023-10-27T14:54 | +7.85 | +0.01 | `take_profit` |
| 15 | 2023-10-30T09:18 | 2023-10-30T11:46 | +170.35 | +0.13 | `take_profit` |
| 16 | 2023-10-31T07:51 | 2023-10-31T08:22 | +114.08 | +0.09 | `take_profit` |

**Straty za sebou: 8** — 2025-04-15T08:51 až 2025-05-02T12:45, spolu -2783.76.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-04-15T08:51 | 2025-04-15T11:23 | -298.74 | -0.21 | `stop_loss` |
| 2 | 2025-04-17T07:57 | 2025-04-17T12:15 | -330.00 | -0.23 | `stop_loss` |
| 3 | 2025-04-21T11:48 | 2025-04-21T13:24 | -380.08 | -0.26 | `stop_loss` |
| 4 | 2025-04-28T12:24 | 2025-04-28T13:17 | -317.50 | -0.22 | `stop_loss` |
| 5 | 2025-04-28T14:42 | 2025-04-30T15:23 | -742.50 | -0.52 | `stop_loss` |
| 6 | 2025-05-01T07:21 | 2025-05-01T08:00 | -298.72 | -0.21 | `stop_loss` |
| 7 | 2025-05-02T09:39 | 2025-05-02T12:30 | -342.48 | -0.24 | `stop_loss` |
| 8 | 2025-05-02T12:45 | 2025-05-02T12:45 | -73.73 | -0.05 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0004 %**, medián -0.0003 %, 90 % interval -0.0045–0.0036 %
- P(edge > poplatok) = **19.2 %**
- max drawdown: medián 23.0 %, 95. percentil 44.5 %, najhorší 74.3 %
- najdlhšia séria strát: medián 7, 95. percentil 9 obchodov
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
<!-- POSUDOK cisla=20c7c431 -->

Pozor: analytika je na **východisku** — nastavenie TKS 1 z MNQ bez zmeny (len seansa trhu); kolo 1 ladenia (17. 11. 2026, hyperopt hraníc Kompasu, potvrdenia a swingu) je v iCloud TKS-TRHY a v histórii hyperoptov. Po smernici sa analytika prepíše na víťaza.

1. **Na čo sa to hodí:** euro (6E), 3m, seansa Londýn 3:00–11:30 NY (`sessOpenMin` 180, noc = Ázia). Euro sa intradenne vracia späť; Kompas meria trend dňa — prirodzene slabšia zhoda.
2. **Potenciál zatiaľ nie.** Na východisku 1 z 5 rokov v zisku, break-even ~0 (−0,0004 %), proti náhode +0,2 sigma = nerozlíšiteľné od náhody. Kolo 1 ladenia (lo 20 / hi 85 / 4 sviečky / swing 8) malo roky ladenia PF 1,08–1,30, ale odložený rok 0,88 → pretrénované.
3. **Dorobiť:** seansu len Londýn 3:00–8:00 NY (bez NY rána), noc kratšiu (len Ázia od 19:00); pre návratový trh skúsiť opačné použitie Kompasu (fade extrémov) — to už je iná stratégia.
4. **Otestovať:** `--set sessCloseMin=480` a hyperopt hraníc; krok 8 na EURUSD CFD. Rozhodne: odložený rok ≥ 1,2.
5. **O ničom v tejto podobe** — euro ako trendový Kompas nefunguje; nechať odložené, kým nepríde nápad na fade.
6. **Pridal by som** Kompas ako filter režimu (trend vs. návrat) pre rangeové stratégie na 6E namiesto samostatného vstupu.

<!-- POSUDOK KONIEC -->
