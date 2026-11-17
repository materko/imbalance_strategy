# Základná analytika — TKS 1.0 MGC (C# jadro) (`tksmgcnet`)

Zmerané 2026-11-17 na `MGC/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/tksmgcnet/configs/mgc_databento_3m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy tksmgcnet \
   --profile tradebot/strategies/tksmgcnet/configs/mgc_databento_3m.json \
   --pair MGC/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 992 obchodov spolu — na štatistiku dosť

## Kde má chyby

- zisková v 0 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20231001-20241001, 20240904-20250904, 20250904-20260904 v strate)
- break-even -0.0106 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 8 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 26.4 % (namerané 14.8 % medián) — na účet to treba mať
- nie je lepšia než náhodný vstup za tých istých pravidiel (-1.5 sigma) — výber vstupu nepridáva nič
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'bežný deň' vlastnosti 'Sviatok na burze v USA': 936 obchodov (94.4 %), bez nej by break-even bol o +0.0566 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 198 | -2.74 | -0.0210 | 3.7 | 62.6 | +7/-4 | `20261117-113312-9cc7eb` |
| 20221001-20231001 | 188 | -2.15 | -0.0163 | 3.2 | 61.7 | +13/-4 | `20261117-113640-0a7b76` |
| 20231001-20241001 | 203 | -2.57 | -0.0151 | 4.7 | 66.5 | +14/-5 | `20261117-113646-4b5691` |
| 20240904-20250904 | 212 | -3.08 | -0.0127 | 5.1 | 65.6 | +9/-5 | `20261117-114557-c422f1` |
| 20250904-20260904 | 205 | -1.10 | -0.0019 | 6.9 | 68.3 | +9/-4 | `20261117-114603-c3b988` |

Zisková v **0 z 5** okien, obchodov spolu 992, break-even celkom -0.0106 %. Okná sa prekrývajú, 14 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.50 ATR za 5 barov)
- medián držania 16.7 barov grafu
- winrate 65.12 %, payoff 0.474
- 0.55 obchodov za deň
- šikmosť výnosov -1.374

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 65.1 %, `stop_loss` 34.9 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'bežný deň' vlastnosti 'Sviatok na burze v USA': 936 obchodov (94.4 %), break-even -0.014 % oproti -0.0106 % celku. Bez nej by break-even bol 0.046 % (+0.0566). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bežný deň | 936 | 94.4 % | 64.8 | -0.0140 | 0.0460 | +0.0566 |
| deň po sviatku | 27 | 2.7 % | 77.8 | 0.0598 | -0.0125 | -0.0019 |

**Plánovaný RR** (riadi `rrRatio`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.49 R – 0.5 R | 256 | 25.8 % | 62.5 | -0.0411 | 0.0013 | +0.0119 |
| nad 0.51 R | 183 | 18.4 % | 55.7 | -0.0244 | -0.0079 | +0.0027 |
| 0.5 R – 0.51 R | 148 | 14.9 % | 69.6 | 0.0061 | -0.0140 | -0.0034 |
| do 0.49 R | 405 | 40.8 % | 69.4 | 0.0099 | -0.0236 | -0.0130 |

**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 0.6821 % | 247 | 24.9 % | 62.4 | -0.0402 | 0.0012 | +0.0118 |
| 0.4785 % – 0.6821 % | 248 | 25.0 % | 66.5 | -0.0013 | -0.0134 | -0.0028 |
| 0.3197 % – 0.4785 % | 248 | 25.0 % | 64.5 | -0.0009 | -0.0137 | -0.0031 |
| do 0.3197 % | 249 | 25.1 % | 67.1 | 0.0058 | -0.0157 | -0.0051 |

Parametre, ktorými sa dá s tým niečo spraviť: `rrRatio`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0106 % | 0.0003 % ± 0.0073 | -1.49 | 7.1 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0106 % | -0.0006 % ± 0.0071 | -1.41 | 8.8 |

HORSIE nez nahoda (-1.5 sigma). Nahodny vstup za tych istych pravidiel dava lepsi vysledok - vyber vstupu vysledku skodi.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 241 | 16.3 | 61.8 | -0.0200 | 31 |
| 2022-12 - 2024-03 | 227 | 15.4 | 67.0 | 0.0027 | 77 |
| 2024-03 - 2025-06 | 266 | 18.0 | 63.9 | -0.0245 | 22 |
| 2025-06 - 2026-09 | 258 | 17.5 | 67.8 | -0.0031 | 66 |

Hranice pre úsek veľkosti posledného obdobia: -0.0419 až +0.0182 % (medián -0.0105).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 66. percentile, teda v medziach -0.0419 až +0.0182 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 15** — 2023-09-15T13:15 až 2023-10-05T12:38, spolu +563.93.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-09-15T13:15 | 2023-09-15T13:25 | +31.32 | +0.16 | `take_profit` |
| 2 | 2023-09-18T16:48 | 2023-09-18T17:15 | +15.31 | +0.08 | `take_profit` |
| 3 | 2023-09-20T13:39 | 2023-09-20T13:43 | +28.31 | +0.14 | `take_profit` |
| 4 | 2023-09-22T12:57 | 2023-09-22T13:14 | +11.32 | +0.06 | `take_profit` |
| 5 | 2023-09-22T13:18 | 2023-09-22T14:39 | +16.32 | +0.08 | `take_profit` |
| 6 | 2023-09-25T12:42 | 2023-09-25T12:42 | +8.32 | +0.04 | `take_profit` |
| 7 | 2023-09-25T14:24 | 2023-09-26T00:57 | +42.32 | +0.22 | `take_profit` |
| 8 | 2023-09-26T12:42 | 2023-09-26T15:06 | +30.32 | +0.16 | `take_profit` |
| 9 | 2023-09-26T15:51 | 2023-09-26T18:26 | +34.33 | +0.18 | `take_profit` |
| 10 | 2023-09-27T13:54 | 2023-09-27T15:20 | +38.33 | +0.20 | `take_profit` |
| 11 | 2023-09-28T13:00 | 2023-09-28T14:31 | +35.34 | +0.19 | `take_profit` |
| 12 | 2023-09-28T15:03 | 2023-09-28T15:17 | +61.34 | +0.33 | `take_profit` |
| 13 | 2023-09-29T14:39 | 2023-09-29T17:29 | +102.34 | +0.55 | `take_profit` |
| 14 | 2023-10-02T14:48 | 2023-10-02T23:14 | +51.35 | +0.28 | `take_profit` |
| 15 | 2023-10-04T14:27 | 2023-10-05T12:38 | +57.36 | +0.31 | `take_profit` |

**Straty za sebou: 5** — 2024-07-22T12:39 až 2024-07-29T14:38, spolu -533.23, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-07-22T12:39 | 2024-07-23T11:16 | -173.84 | -0.73 | `stop_loss` |
| 2 | 2024-07-24T13:00 | 2024-07-24T13:17 | -53.85 | -0.22 | `stop_loss` |
| 3 | 2024-07-24T13:42 | 2024-07-24T13:45 | -74.85 | -0.31 | `stop_loss` |
| 4 | 2024-07-24T14:06 | 2024-07-24T17:37 | -135.85 | -0.56 | `stop_loss` |
| 5 | 2024-07-29T13:39 | 2024-07-29T14:38 | -94.84 | -0.40 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0106 %**, medián -0.0105 %, 90 % interval -0.0254–0.0038 %
- P(edge > poplatok) = **8.1 %**
- max drawdown: medián 14.8 %, 95. percentil 26.4 %, najhorší 51.9 %
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
<!-- POSUDOK cisla=d6bb4e71 -->

Pozor: analytika je na **východisku** — nastavenie TKS 1 z MNQ bez zmeny (len seansa trhu); kolo 1 ladenia (17. 11. 2026, hyperopt hraníc Kompasu, potvrdenia a swingu) je v iCloud TKS-TRHY a v histórii hyperoptov. Po smernici sa analytika prepíše na víťaza.

C# kópia — obchody bar po bare zhodné s Python predlohou (parita), posudok platí rovnako.

1. **Na čo sa to hodí:** zlato (MGC), 3m, seansa od otvorenia COMEX 8:20–13:30 NY (`sessOpenMin` 500). Zlato reaguje na správy o 8:30 a má iný denný rytmus než indexy.
2. **Potenciál neistý.** Na východisku (TKS 1 z MNQ so seansou 8:20) 0 z 5 rokov v zisku, break-even −0,0106 %, proti náhode −1,4 sigma — hranice z MNQ na zlato nesedia. Kolo 1 ladenia so seansou 8:20 (lo 25 / hi 90 / 1 sviečka / swing 3): roky ladenia PF 1,01–1,22, odložený rok **1,40** (zisk 5 490 $, DD 1 142 $); so seansou 9:30 odložený rok padol (0,90). Seansa trhu teda hrá rolu, edge v rokoch ladenia je ale tenký.
3. **Dorobiť:** okno vstupov od 8:20 (správy o 8:30 — vstup pred / po), hranice a potvrdenie; zvážiť koniec seansy (13:30 vs. neskôr).
4. **Otestovať:** kolo 2 na víťazovi (`--set loLevel=25 --set hiLevel=90 --set nConf=1 --set pivLen=3`) s `entryStartMin`, `entryEndMin`, `sessCloseMin=780:900:30`, `lookbackDays`; krok 8 na XAU/USD; robustnosť. Rozhodne: roky ladenia ≥ 1,2 a XAU/USD v pluse.
5. **Na východisku o ničom, po kole 1 kandidát druhého radu** — hodnota je hlavne v zistení, že Kompas na zlate chce vlastnú seansu.
6. **Pridal by som** Kompas so seansou viazanou na čas správ (8:30) a filter dní bez správ.

<!-- POSUDOK KONIEC -->
