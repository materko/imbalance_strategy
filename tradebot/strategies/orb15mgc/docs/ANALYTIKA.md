# Základná analytika — ORB 15/5 1.0 (MGC) (`orb15mgc`)

Zmerané 2026-10-31 na `MGC/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `/Users/martin/IBS/.nightsearch/base_orb15mgc.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy orb15mgc \
   --profile /Users/martin/IBS/.nightsearch/base_orb15mgc.json \
   --pair MGC/USD \
   --timeframe 5m \
   --fee 1.755e-05
```

## V čom je dobrá

- 1134 obchodov spolu — na štatistiku dosť
- break-even 0.0089 % je nad poplatkom 0.0018 % (rezerva +0.0071 bodu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 75. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- zisková v 3 z 5 referenčných okien (20211001-20221001, 20231001-20241001 v strate)
- edge nad poplatkom len v 80 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 66.6 % (namerané 29.9 % medián) — na účet to treba mať
- proti náhode len +1.1 sigma: náznak, nie dôkaz
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- 42.5 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 'bežný deň' vlastnosti 'Sviatok na burze v USA': 1046 obchodov (92.2 %), bez nej by break-even bol o +0.0201 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 233 | -7.38 | -0.0069 | 10.8 | 41.2 | +6/-8 | `20261031-084724-d71217` |
| 20221001-20231001 | 234 | +10.38 | 0.0135 | 7.3 | 45.3 | +4/-7 | `20261031-084730-40ff3b` |
| 20231001-20241001 | 227 | -14.21 | -0.0122 | 15.7 | 37.0 | +4/-7 | `20261031-084736-740855` |
| 20240904-20250904 | 231 | +17.69 | 0.0145 | 14.0 | 47.2 | +5/-10 | `20261031-084742-174f93` |
| 20250904-20260904 | 228 | +30.61 | 0.0169 | 24.9 | 45.6 | +7/-14 | `20261031-084745-b97cf2` |

Zisková v **3 z 5** okien, obchodov spolu 1134, break-even celkom 0.0089 %. Okná sa prekrývajú, 19 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.44 ATR za 5 barov)
- medián držania 37.4 barov grafu
- winrate 43.56 %, payoff 1.401
- 0.63 obchodov za deň
- šikmosť výnosov +0.753

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `session_end` 42.5 %, `stop_loss` 41.3 %, `take_profit` 16.2 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'bežný deň' vlastnosti 'Sviatok na burze v USA': 1046 obchodov (92.2 %), break-even 0.0072 % oproti 0.0089 % celku. Bez nej by break-even bol 0.029 % (+0.0201). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bežný deň | 1046 | 92.2 % | 43.0 | 0.0072 | 0.0290 | +0.0201 |
| deň po sviatku | 32 | 2.8 % | 68.8 | 0.0441 | 0.0079 | -0.0010 |
| deň pred sviatkom | 16 | 1.4 % | 75.0 | 0.1129 | 0.0073 | -0.0016 |

**Deň v týždni**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| streda | 231 | 20.4 % | 38.1 | -0.0320 | 0.0193 | +0.0104 |
| pondelok | 231 | 20.4 % | 41.6 | 0.0020 | 0.0107 | +0.0018 |
| utorok | 226 | 19.9 % | 50.0 | 0.0128 | 0.0079 | -0.0010 |
| piatok | 219 | 19.3 % | 43.4 | 0.0309 | 0.0036 | -0.0053 |
| štvrtok | 227 | 20.0 % | 44.9 | 0.0325 | 0.0031 | -0.0058 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 8 | 298 | 26.3 % | 38.9 | -0.0160 | 0.0176 | +0.0087 |
| 8 – 16 | 300 | 26.5 % | 41.7 | -0.0068 | 0.0146 | +0.0057 |
| 16 – 23 | 264 | 23.3 % | 45.1 | 0.0257 | 0.0037 | -0.0052 |
| nad 23 | 272 | 24.0 % | 49.3 | 0.0366 | 0.0001 | -0.0088 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0089 % | 0.0014 % ± 0.0067 | +1.13 | 87.3 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0089 % | 0.0022 % ± 0.0066 | +1.01 | 83.5 |

Naznak, ale nie dokaz (1.1 sigma, percentil 87.3). Take rozdiely nahoda robi bezne.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 290 | 19.7 | 43.5 | -0.0011 | 28 |
| 2022-12 - 2024-03 | 279 | 18.9 | 40.1 | 0.0001 | 30 |
| 2024-03 - 2025-06 | 286 | 19.4 | 44.4 | 0.0069 | 46 |
| 2025-06 - 2026-09 | 279 | 18.9 | 46.2 | 0.0186 | 75 |

Hranice pre úsek veľkosti posledného obdobia: -0.0180 až +0.0372 % (medián 0.0076).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 75. percentile, teda v medziach -0.0180 až +0.0372 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 7** — 2026-08-13T14:00 až 2026-08-21T20:00, spolu +1812.94.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-08-13T14:00 | 2026-08-13T20:00 | +250.45 | +0.57 | `session_end` |
| 2 | 2026-08-14T14:50 | 2026-08-14T20:00 | +77.44 | +0.17 | `session_end` |
| 3 | 2026-08-17T13:50 | 2026-08-17T13:57 | +206.43 | +0.46 | `take_profit` |
| 4 | 2026-08-18T15:00 | 2026-08-18T20:00 | +238.45 | +0.54 | `session_end` |
| 5 | 2026-08-19T14:10 | 2026-08-19T20:00 | +366.40 | +0.81 | `session_end` |
| 6 | 2026-08-20T14:25 | 2026-08-20T15:14 | +467.40 | +1.03 | `take_profit` |
| 7 | 2026-08-21T14:25 | 2026-08-21T20:00 | +206.36 | +0.44 | `session_end` |

**Straty za sebou: 14** — 2026-04-28T14:05 až 2026-05-20T14:16, spolu -2423.81.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-04-28T14:05 | 2026-04-28T16:52 | -259.61 | -0.57 | `stop_loss` |
| 2 | 2026-05-01T13:55 | 2026-05-01T20:00 | -72.62 | -0.16 | `session_end` |
| 3 | 2026-05-04T14:10 | 2026-05-04T14:18 | -155.61 | -0.34 | `stop_loss` |
| 4 | 2026-05-05T14:10 | 2026-05-05T14:14 | -124.61 | -0.27 | `stop_loss` |
| 5 | 2026-05-06T13:50 | 2026-05-06T16:58 | -214.65 | -0.46 | `stop_loss` |
| 6 | 2026-05-07T14:50 | 2026-05-07T15:26 | -160.67 | -0.34 | `stop_loss` |
| 7 | 2026-05-08T14:00 | 2026-05-08T14:09 | -219.67 | -0.46 | `stop_loss` |
| 8 | 2026-05-11T14:10 | 2026-05-11T20:00 | -129.66 | -0.27 | `session_end` |
| 9 | 2026-05-12T14:00 | 2026-05-12T19:12 | -229.65 | -0.49 | `stop_loss` |
| 10 | 2026-05-13T15:30 | 2026-05-13T20:00 | -38.65 | -0.08 | `session_end` |
| 11 | 2026-05-14T14:20 | 2026-05-14T19:19 | -295.64 | -0.63 | `stop_loss` |
| 12 | 2026-05-18T13:55 | 2026-05-18T14:04 | -191.61 | -0.42 | `stop_loss` |
| 13 | 2026-05-19T13:55 | 2026-05-19T20:00 | -209.58 | -0.46 | `session_end` |
| 14 | 2026-05-20T14:05 | 2026-05-20T14:16 | -121.58 | -0.27 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0089 %**, medián 0.0088 %, 90 % interval -0.0050–0.0225 %
- P(edge > poplatok) = **80.2 %**
- max drawdown: medián 29.9 %, 95. percentil 66.6 %, najhorší 100.0 %
- najdlhšia séria strát: medián 11, 95. percentil 16 obchodov
- pravdepodobnosť ruiny účtu: 0.5 %

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
<!-- POSUDOK cisla=49442113 -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na MGC, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Intraday index futures od 9:45 NY, jeden obchod denne; na zlate OR 9:30–9:45 nemá zmysel otvorenia akciovej burzy, čísla tam ukazujú skôr šum. Tu na MGC (zlato) — logika robená pre index, čísla to treba brať ako test prenosu.
2. **Má potenciál?** Zisková v 3 z 5 okien, 1134 obchodov (~227 za rok), break-even 0.0089 % (nad poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 43.56 % pri payoffe 1.401. Odložený rok 25/26: +30.61 % PnL, break-even 0.0169 %. Kladné okná sú skôr vlastnosť vzorky ako stabilný jav.
3. **Čo dorobiť.** Skúsiť OR 5 / 30 / 60 min a cieľ RR 0,75–1,5; filter predošlého dňa a knôtu majú byť v mriežke oboma smermi; pre prop koniec dňa.
4. **Čo otestovať ďalej.** Smernica (mriežka glsearch `orb15*`: dĺžka OR, RR, filtre, trend EMA, limit / IBS / pin bar); rozhodne odložený rok 25/26, ktorý je pri MNQ v defaultoch stratový.
5. **Použiteľné?** **V defaultoch predlohy nie** — edge nad poplatkom nie je stabilný po rokoch; šancu má len s nastavením, ktoré nájde smernica (inak vyradiť).
6. **Čo by som pridal.** Smer dňa z VWAP od 9:30 alebo z polohy voči včerajšiemu zavretiu — ORB bez kontextu chytá aj falošné prierazy rána.

<!-- POSUDOK KONIEC -->
