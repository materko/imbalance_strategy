# Základná analytika — TKS 1.0 (MYM) (`tksmym`)

Zmerané 2026-11-17 na `MYM/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/tksmym/configs/mym_databento_3m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy tksmym \
   --profile tradebot/strategies/tksmym/configs/mym_databento_3m.json \
   --pair MYM/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 773 obchodov spolu — na štatistiku dosť
- drawdown drží: 95. percentil 12.1 %

## Kde má chyby

- zisková v 2 z 5 referenčných okien (20211001-20221001, 20240904-20250904, 20250904-20260904 v strate)
- break-even -0.0069 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 12 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- nie je lepšia než náhodný vstup za tých istých pravidiel (-1.1 sigma) — výber vstupu nepridáva nič
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 's trendom' vlastnosti 'S trendom, alebo proti': 726 obchodov (93.9 %), bez nej by break-even bol o +0.0403 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 161 | -3.97 | -0.0422 | 4.6 | 64.6 | +8/-4 | `20261117-113243-cd09bf` |
| 20221001-20231001 | 150 | +1.99 | 0.0255 | 0.6 | 74.0 | +12/-3 | `20261117-113246-f06855` |
| 20231001-20241001 | 160 | +0.62 | 0.0079 | 0.8 | 66.2 | +8/-4 | `20261117-113252-b38b4e` |
| 20240904-20250904 | 137 | -1.35 | -0.0119 | 1.9 | 64.2 | +5/-4 | `20261117-113255-09960c` |
| 20250904-20260904 | 176 | -2.00 | -0.0120 | 2.9 | 64.2 | +9/-5 | `20261117-113258-b4b93c` |

Zisková v **2 z 5** okien, obchodov spolu 773, break-even celkom -0.0069 %. Okná sa prekrývajú, 11 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.38 ATR za 5 barov)
- medián držania 19.7 barov grafu
- winrate 66.75 %, payoff 0.451
- 0.43 obchodov za deň
- šikmosť výnosov -1.211

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 66.8 %, `stop_loss` 33.2 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 's trendom' vlastnosti 'S trendom, alebo proti': 726 obchodov (93.9 %), break-even -0.0096 % oproti -0.0069 % celku. Bez nej by break-even bol 0.0334 % (+0.0403). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 726 | 93.9 % | 66.1 | -0.0096 | 0.0334 | +0.0403 |
| proti trendu | 47 | 6.1 % | 76.6 | 0.0334 | -0.0096 | -0.0027 |

**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| FOMC | 18 | 2.3 % | 55.6 | -0.0402 | -0.0061 | +0.0008 |
| NFP | 34 | 4.4 % | 64.7 | -0.0120 | -0.0067 | +0.0002 |
| žiadna | 680 | 88.0 % | 66.2 | -0.0115 | 0.0269 | +0.0338 |
| CPI | 41 | 5.3 % | 82.9 | 0.0918 | -0.0123 | -0.0054 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| pred vyhlásením | 18 | 2.3 % | 55.6 | -0.0402 | -0.0061 | +0.0008 |
| bez udalosti | 680 | 88.0 % | 66.2 | -0.0115 | 0.0269 | +0.0338 |
| po vyhlásení | 75 | 9.7 % | 74.7 | 0.0435 | -0.0123 | -0.0054 |

Parametre, ktorými sa dá s tým niečo spraviť: `rrRatio`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0069 % | 0.0007 % ± 0.0067 | -1.15 | 13.4 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0069 % | -0.0005 % ± 0.0065 | -0.98 | 16.7 |

HORSIE nez nahoda (-1.1 sigma). Nahodny vstup za tych istych pravidiel dava lepsi vysledok - vyber vstupu vysledku skodi.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 194 | 13.2 | 66.5 | -0.0288 | 7 |
| 2022-12 - 2024-03 | 198 | 13.4 | 72.7 | 0.0223 | 99 |
| 2024-03 - 2025-06 | 172 | 11.7 | 62.8 | -0.0095 | 42 |
| 2025-06 - 2026-09 | 209 | 14.2 | 64.6 | -0.0110 | 38 |

Hranice pre úsek veľkosti posledného obdobia: -0.0319 až +0.0162 % (medián -0.0067).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 38. percentile, teda v medziach -0.0319 až +0.0162 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 12** — 2023-01-05T15:21 až 2023-01-24T15:55, spolu +566.89.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-01-05T15:21 | 2023-01-05T15:53 | +35.42 | +0.21 | `take_profit` |
| 2 | 2023-01-05T15:54 | 2023-01-05T16:21 | +39.92 | +0.24 | `take_profit` |
| 3 | 2023-01-06T15:36 | 2023-01-06T16:51 | +88.41 | +0.53 | `take_profit` |
| 4 | 2023-01-09T14:48 | 2023-01-09T14:48 | +12.90 | +0.08 | `take_profit` |
| 5 | 2023-01-09T15:39 | 2023-01-09T16:15 | +41.40 | +0.24 | `take_profit` |
| 6 | 2023-01-10T15:57 | 2023-01-10T20:50 | +51.41 | +0.30 | `take_profit` |
| 7 | 2023-01-12T18:42 | 2023-01-12T18:54 | +38.90 | +0.23 | `take_profit` |
| 8 | 2023-01-13T14:48 | 2023-01-13T15:13 | +48.90 | +0.29 | `take_profit` |
| 9 | 2023-01-17T15:57 | 2023-01-17T20:50 | +53.40 | +0.31 | `take_profit` |
| 10 | 2023-01-18T15:48 | 2023-01-18T16:06 | +57.91 | +0.34 | `take_profit` |
| 11 | 2023-01-23T15:18 | 2023-01-23T15:58 | +55.41 | +0.33 | `take_profit` |
| 12 | 2023-01-24T15:33 | 2023-01-24T15:55 | +42.91 | +0.26 | `take_profit` |

**Straty za sebou: 5** — 2026-04-21T13:51 až 2026-04-27T15:03, spolu -531.35.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-04-21T13:51 | 2026-04-21T14:34 | -96.38 | -0.39 | `stop_loss` |
| 2 | 2026-04-22T14:00 | 2026-04-22T16:29 | -90.87 | -0.37 | `stop_loss` |
| 3 | 2026-04-23T14:15 | 2026-04-23T17:10 | -119.87 | -0.48 | `stop_loss` |
| 4 | 2026-04-24T14:30 | 2026-04-27T13:33 | -110.37 | -0.45 | `stop_loss` |
| 5 | 2026-04-27T13:54 | 2026-04-27T15:03 | -113.87 | -0.46 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0069 %**, medián -0.0067 %, 90 % interval -0.0194–0.0056 %
- P(edge > poplatok) = **12.1 %**
- max drawdown: medián 6.6 %, 95. percentil 12.1 %, najhorší 21.6 %
- najdlhšia séria strát: medián 5, 95. percentil 7 obchodov
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
<!-- POSUDOK cisla=8e4a0eb5 -->

Pozor: analytika je na **východisku** — nastavenie TKS 1 z MNQ bez zmeny (len seansa trhu); kolo 1 ladenia (17. 11. 2026, hyperopt hraníc Kompasu, potvrdenia a swingu) je v iCloud TKS-TRHY a v histórii hyperoptov. Po smernici sa analytika prepíše na víťaza.

1. **Na čo sa to hodí:** Micro Dow (MYM), 3m, seansa NY. Prepad je malý (95. percentil 12 %), ale aj zisk; Dow je pomalší a menej trendový než Nasdaq.
2. **Potenciál slabý.** Na východisku 2 z 5 rokov v zisku, break-even −0,0069 % (pod nulou), proti náhode −1,0 sigma — s nastavením z MNQ tu edge nie je. Kolo 1 ladenia našlo lo 30 / hi 70 / 1 sviečka / swing 12: všetky roky tesne v pluse (PF 1,04–1,19), odložený rok 1,20 — chytilo sa to, ale tenko.
3. **Dorobiť:** hranice a potvrdenie pre Dow (Kompas sa na MYM hýbe inak), okno vstupov; zvážiť filter trendu (skupina „s trendom“ je 94 % obchodov a ťahá dole — trendový filter z MNQ tu skôr škodí).
4. **Otestovať:** kolo 2 na víťazovi kola 1 (`--set loLevel=30 --set hiLevel=70 --set nConf=1 --set pivLen=12`), parametre `trendFilter=with,off`, `entryStartMin`, `entryEndMin`, `lookbackDays`; plató; robustnosť. Rozhodne: PF ladenia ≥ 1,3 bez roka pod 0,9.
5. **Zatiaľ o ničom** na východisku; po kole 1 hraničné — rozhodne kolo 2. Ak PF ladenia neprekročí ~1,2, nechať tak.
6. **Pridal by som** Kompas z ES alebo NQ ako filter pre MYM (Dow ide za širokým trhom, vlastný Kompas je slabší signál).

<!-- POSUDOK KONIEC -->
