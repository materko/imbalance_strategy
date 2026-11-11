# Základná analytika — MTK ORB (MGC) (`mtkorb`)

Zmerané 2026-11-11 na `MGC/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `mgc_databento_5m`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy mtkorb \
   --profile mgc_databento_5m \
   --pair MGC/USD \
   --timeframe 5m \
   --fee 1.755e-05
```

## V čom je dobrá

- 474 obchodov spolu — na štatistiku dosť
- break-even 0.0107 % je nad poplatkom 0.0018 % (rezerva +0.0089 bodu)
- edge nad poplatkom v 97 % bootstrapových vzoriek
- odlíšiteľná od náhody (+2.3 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-08 na 85. percentile toho, čo stratégia vyrobí sama od seba)
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 4 z 5 referenčných okien (20231001-20241001 v strate)
- 95. percentil max drawdownu 83.0 % (namerané 35.4 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 2.2 % pri riziku, s akým beh bežal
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 102 | +38.18 | 0.0101 | 23.1 | 54.9 | +5/-8 | `20261111-185036-f209b5` |
| 20221001-20231001 | 99 | +60.42 | 0.0144 | 25.8 | 56.6 | +7/-6 | `20261111-185042-7c4d8a` |
| 20231001-20241001 | 96 | -53.87 | -0.0087 | 73.4 | 44.8 | +5/-6 | `20261111-185048-aac086` |
| 20240904-20250904 | 89 | +85.84 | 0.0218 | 19.8 | 59.5 | +5/-4 | `20261111-185051-4d9008` |
| 20250904-20260904 | 92 | +50.92 | 0.0211 | 33.4 | 55.4 | +12/-6 | `20261111-185055-d98a0c` |

Zisková v **4 z 5** okien, obchodov spolu 474, break-even celkom 0.0107 %. Okná sa prekrývajú, 4 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.01 ATR za 5 barov)
- medián držania 4 barov grafu
- winrate 54.43 %, payoff 0.999
- 0.26 obchodov za deň
- šikmosť výnosov -0.174

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 52.5 %, `stop_loss` 42.8 %, `session_end` 4.6 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0065 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 14 h | 180 | 38.0 % | 49.4 | 0.0013 | 0.0172 | +0.0065 |
| 13 h | 273 | 57.6 % | 57.1 | 0.0168 | 0.0033 | -0.0074 |
| 15 h | 21 | 4.4 % | 61.9 | 0.0220 | 0.0102 | -0.0005 |

**Volatilita voči normálu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 1.41 – 1.699 | 117 | 24.7 % | 47.0 | -0.0032 | 0.0155 | +0.0048 |
| nad 2.039 | 117 | 24.7 % | 51.3 | 0.0023 | 0.0131 | +0.0024 |
| 1.699 – 2.039 | 119 | 25.1 % | 57.1 | 0.0182 | 0.0084 | -0.0023 |
| do 1.41 | 121 | 25.5 % | 62.0 | 0.0236 | 0.0056 | -0.0051 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.4962 | 119 | 25.1 % | 48.7 | -0.0007 | 0.0153 | +0.0046 |
| nad 0.8929 | 118 | 24.9 % | 50.9 | 0.0054 | 0.0122 | +0.0015 |
| 0.7326 – 0.8929 | 118 | 24.9 % | 52.5 | 0.0071 | 0.0119 | +0.0012 |
| 0.4962 – 0.7326 | 119 | 25.1 % | 65.5 | 0.0317 | 0.0036 | -0.0071 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0118 % | 0.0000 % ± 0.0051 | +2.29 | 98.8 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0118 % | -0.0002 % ± 0.0058 | +2.07 | 97.9 |

Edge je odlisitelny od nahody (2.3 sigma, percentil 98.8).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 130 | 8.8 | 56.9 | 0.0148 | 69 |
| 2022-12 - 2024-03 | 122 | 8.3 | 49.2 | -0.0011 | 13 |
| 2024-03 - 2025-06 | 110 | 7.5 | 55.5 | 0.0139 | 61 |
| 2025-06 - 2026-08 | 112 | 7.6 | 56.2 | 0.0210 | 85 |

Hranice pre úsek veľkosti posledného obdobia: -0.0057 až +0.0269 % (medián 0.0104).

**DRZI** — posledné obdobie (2025-06 - 2026-08) je na 85. percentile, teda v medziach -0.0057 až +0.0269 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 12** — 2026-06-17T13:45 až 2026-07-23T13:59, spolu +5235.81.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-06-17T13:45 | 2026-06-17T14:23 | +467.34 | +0.21 | `take_profit` |
| 2 | 2026-06-19T13:45 | 2026-06-19T14:16 | +418.14 | +0.25 | `take_profit` |
| 3 | 2026-06-22T13:46 | 2026-06-22T14:07 | +470.08 | +0.28 | `take_profit` |
| 4 | 2026-06-26T13:45 | 2026-06-26T14:04 | +347.13 | +0.43 | `take_profit` |
| 5 | 2026-06-29T13:48 | 2026-06-29T14:03 | +426.32 | +0.26 | `take_profit` |
| 6 | 2026-06-30T13:46 | 2026-06-30T14:09 | +433.74 | +0.36 | `take_profit` |
| 7 | 2026-07-06T13:46 | 2026-07-06T14:24 | +452.72 | +0.22 | `take_profit` |
| 8 | 2026-07-08T14:00 | 2026-07-08T14:16 | +412.71 | +0.34 | `take_profit` |
| 9 | 2026-07-13T13:49 | 2026-07-13T14:03 | +382.73 | +0.31 | `take_profit` |
| 10 | 2026-07-20T13:50 | 2026-07-20T14:10 | +472.97 | +0.24 | `take_profit` |
| 11 | 2026-07-22T13:46 | 2026-07-22T14:02 | +457.62 | +0.37 | `take_profit` |
| 12 | 2026-07-23T13:45 | 2026-07-23T13:59 | +494.31 | +0.30 | `take_profit` |

**Straty za sebou: 8** — 2022-07-07T13:48 až 2022-08-01T14:02, spolu -3476.00.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-07-07T13:48 | 2022-07-07T14:59 | -496.12 | -0.28 | `stop_loss` |
| 2 | 2022-07-12T13:45 | 2022-07-12T15:07 | -487.28 | -0.24 | `stop_loss` |
| 3 | 2022-07-15T13:47 | 2022-07-15T14:00 | -505.98 | -0.30 | `stop_loss` |
| 4 | 2022-07-19T14:13 | 2022-07-19T14:22 | -479.60 | -0.25 | `stop_loss` |
| 5 | 2022-07-25T14:04 | 2022-07-25T20:00 | -77.42 | -0.05 | `session_end` |
| 6 | 2022-07-26T13:50 | 2022-07-26T14:00 | -489.65 | -0.18 | `stop_loss` |
| 7 | 2022-07-27T13:49 | 2022-07-27T15:19 | -464.42 | -0.30 | `stop_loss` |
| 8 | 2022-08-01T13:45 | 2022-08-01T14:02 | -475.53 | -0.22 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0107 %**, medián 0.0107 %, 90 % interval 0.0029–0.0187 %
- P(edge > poplatok) = **96.9 %**
- max drawdown: medián 35.4 %, 95. percentil 83.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 7, 95. percentil 10 obchodov
- pravdepodobnosť ruiny účtu: 2.2 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **127** na obchod pri účte 10 000

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
<!-- POSUDOK cisla=98689f09 -->

**1. Na čo sa to hodí.** Zlato (MGC / GC) na 5m, jeden prieraz denne po otvorení New Yorku, držanie zvyčajne do cieľa alebo stopu v ten istý deň. Riziko je šírka OR (pri MGC typicky desiatky dolárov na kontrakt), takže sa hodí aj na malý účet s mikro kontraktom; vysoké percentá drawdownu sú z behu na malej peňaženke s veľkosťou z rizika, nie na 1 kontrakt.

**2. Potenciál.** Áno — je to jediná stratégia z rozboru NY open, ktorá je odlíšiteľná od náhody (+2,3 sigma proti náhodnému vstupu), edge nad poplatkom v 97 % bootstrapových vzoriek a posledné obdobie drží (85. percentil). Rozbor na 1m dátach 2010–2026 ukázal ten istý jav v 15 zo 16 rokov. Proti: rok 2023/24 je v strate a samotný prieraz OR na zlate (bez gap filtra) od 2023 slabne — edge stojí na filtri smeru gapu.

**3. Čo dorobiť.** Logika je hotová (stop order na hranici OR, len prvý prieraz, smer gapu, šírka OR). Chýba C# prepis pre NinjaTrader / MT5 — až keď smernica potvrdí nastavenie. Zvážiť seansu COMEX (OR od 8:20), ktorú smernica skúša cez `orStart`.

**4. Čo otestovať.** Smernica beží (11.–12. 11. 2026) na všetkých dátach MGC 2010-11 – 2024-09 s 2 odloženými rokmi 2024-09 – 2026-09; rozhodne, či sa dá nájsť nastavenie s PF ≥ 1,3 bez roka pod 0,9 na 14 rokoch. Potom `cli matrix --strategy mtkorb --timeframes 1m,3m,5m` a druhý trh (XAU CFD).

**5. Použiteľné?** **Áno ako kandidát** — z toho, čo sme na otvorení NY našli, má najlepšie podložený edge. Na nasadenie čaká na smernicu a odložené 2 roky.

**6. Čo by som pridal.** Filter na makro dni (CPI, FOMC, NFP o 8:30 menia gap aj OR) a čiastočný výber na 1R s posunom stopu na vstup — prieraz OR v smere gapu zvykne buď hneď ísť, alebo sa vrátiť.

<!-- POSUDOK KONIEC -->
