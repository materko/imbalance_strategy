# Základná analytika — IBS Entry Zone (C# jadro EOD) (`ibsentryneteod`)

Zmerané 2026-10-26 na `MNQ/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tester/profiles/SMERNICE_CS_EOD_IBS_Entry_Zone_1.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy ibsentryneteod \
   --profile tester/profiles/SMERNICE_CS_EOD_IBS_Entry_Zone_1.json \
   --pair MNQ/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 788 obchodov spolu — na štatistiku dosť
- break-even 0.0171 % je nad poplatkom 0.0018 % (rezerva +0.0153 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 14.3 %
- odlíšiteľná od náhody (+8.2 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 79. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'bežný deň' vlastnosti 'Sviatok na burze v USA': 758 obchodov (96.2 %), bez nej by break-even bol o +0.0124 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 213 | +51.01 | 0.0240 | 8.3 | 76.1 | +14/-3 | `20261026-130541-694c7f` |
| 20221001-20231001 | 124 | +7.81 | 0.0067 | 11.7 | 68.5 | +8/-3 | `20261026-130553-deb0ee` |
| 20231001-20241001 | 91 | +12.19 | 0.0110 | 4.5 | 72.5 | +9/-3 | `20261026-130605-1334a7` |
| 20240904-20250904 | 157 | +27.74 | 0.0159 | 6.8 | 73.2 | +13/-3 | `20261026-130617-ad4457` |
| 20250904-20260904 | 203 | +52.55 | 0.0210 | 6.8 | 77.8 | +16/-4 | `20261026-130629-4f90c0` |

Zisková v **5 z 5** okien, obchodov spolu 788, break-even celkom 0.0171 %.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+0.71 ATR za 5 barov)
- medián držania 2 barov grafu
- winrate 74.37 %, payoff 0.52
- 0.44 obchodov za deň
- šikmosť výnosov -1.477

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 74 %, `stop_loss` 23.5 %, `session_end` 2.5 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'bežný deň' vlastnosti 'Sviatok na burze v USA': 758 obchodov (96.2 %), break-even 0.0165 % oproti 0.0171 % celku. Bez nej by break-even bol 0.0295 % (+0.0124). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bežný deň | 758 | 96.2 % | 74.1 | 0.0165 | 0.0295 | +0.0124 |
| deň po sviatku | 17 | 2.2 % | 82.3 | 0.0235 | 0.0169 | -0.0002 |
| deň pred sviatkom | 10 | 1.3 % | 80.0 | 0.0537 | 0.0167 | -0.0004 |

**S trendom, alebo proti** (riadi `useStructureFilter`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 559 | 70.9 % | 72.8 | 0.0139 | 0.0246 | +0.0075 |
| proti trendu | 229 | 29.1 % | 78.2 | 0.0246 | 0.0139 | -0.0032 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 7 – 14 | 199 | 25.3 % | 68.3 | 0.0063 | 0.0206 | +0.0035 |
| do 7 | 204 | 25.9 % | 73.5 | 0.0158 | 0.0175 | +0.0004 |
| 14 – 23 | 195 | 24.7 % | 75.9 | 0.0176 | 0.0169 | -0.0002 |
| nad 23 | 190 | 24.1 % | 80.0 | 0.0290 | 0.0133 | -0.0038 |

Parametre, ktorými sa dá s tým niečo spraviť: `closeAtSessionEnd`, `minSlDistance`, `rrRatio`, `sess2TradeStartH`, `state2MaxBars`, `tradeDirection`, `useStructureFilter`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0193 % | -0.0002 % ± 0.0024 | +8.19 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0193 % | -0.0001 % ± 0.0026 | +7.38 | 100.0 |

Edge je odlisitelny od nahody (8.2 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 258 | 17.5 | 73.3 | 0.0175 | 55 |
| 2022-12 - 2024-03 | 110 | 7.5 | 73.6 | 0.0152 | 42 |
| 2024-03 - 2025-06 | 200 | 13.6 | 72.0 | 0.0125 | 22 |
| 2025-06 - 2026-09 | 220 | 14.9 | 78.2 | 0.0216 | 79 |

Hranice pre úsek veľkosti posledného obdobia: +0.0080 až +0.0261 % (medián 0.0172).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 79. percentile, teda v medziach +0.0080 až +0.0261 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 16** — 2026-01-29T18:09 až 2026-02-12T15:54, spolu +7218.49.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-01-29T18:09 | 2026-01-29T18:10 | +439.50 | +0.11 | `take_profit` |
| 2 | 2026-01-30T07:27 | 2026-01-30T07:37 | +449.30 | +0.07 | `take_profit` |
| 3 | 2026-01-30T17:54 | 2026-01-30T18:00 | +467.68 | +0.15 | `take_profit` |
| 4 | 2026-01-30T20:01 | 2026-01-30T20:05 | +455.59 | +0.11 | `take_profit` |
| 5 | 2026-02-04T15:33 | 2026-02-04T15:34 | +458.66 | +0.18 | `take_profit` |
| 6 | 2026-02-04T15:54 | 2026-02-04T16:01 | +442.35 | +0.09 | `take_profit` |
| 7 | 2026-02-04T18:32 | 2026-02-04T18:42 | +442.76 | +0.13 | `take_profit` |
| 8 | 2026-02-04T18:45 | 2026-02-04T18:50 | +443.28 | +0.10 | `take_profit` |
| 9 | 2026-02-05T00:24 | 2026-02-05T00:38 | +471.90 | +0.12 | `take_profit` |
| 10 | 2026-02-05T15:51 | 2026-02-05T15:52 | +444.65 | +0.13 | `take_profit` |
| 11 | 2026-02-05T18:00 | 2026-02-05T18:10 | +452.55 | +0.18 | `take_profit` |
| 12 | 2026-02-05T19:33 | 2026-02-05T20:25 | +390.05 | +0.26 | `take_profit` |
| 13 | 2026-02-09T14:39 | 2026-02-09T14:40 | +457.95 | +0.23 | `take_profit` |
| 14 | 2026-02-10T15:18 | 2026-02-10T15:24 | +472.64 | +0.08 | `take_profit` |
| 15 | 2026-02-11T18:19 | 2026-02-11T18:27 | +461.73 | +0.08 | `take_profit` |
| 16 | 2026-02-12T15:54 | 2026-02-12T15:54 | +467.88 | +0.08 | `take_profit` |

**Straty za sebou: 5** — 2024-09-18T19:18 až 2024-10-03T15:40, spolu -4713.40.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-09-18T19:18 | 2024-09-18T19:20 | -953.97 | -0.19 | `stop_loss` |
| 2 | 2024-09-18T19:18 | 2024-09-18T19:20 | -953.97 | -0.19 | `stop_loss` |
| 3 | 2024-09-27T17:30 | 2024-09-27T18:00 | -979.22 | -0.24 | `stop_loss` |
| 4 | 2024-09-27T17:30 | 2024-09-27T18:00 | -979.22 | -0.24 | `stop_loss` |
| 5 | 2024-10-03T15:00 | 2024-10-03T15:40 | -847.02 | -0.42 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0171 %**, medián 0.0172 %, 90 % interval 0.0122–0.0219 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 8.0 %, 95. percentil 14.3 %, najhorší 43.3 %
- najdlhšia séria strát: medián 4, 95. percentil 6 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **2 317** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=f7bfdd79 -->

_Posudok (Claude, 26. 10. 2026) — nastavenie „IBS EZ 1 C# EOD“ (`SMERNICE_CS_EOD_IBS_Entry_Zone_1`, parametre zhodné
s `ibsentrynet`): navyše o 15:59 NY zatvorí všetko, zruší čakajúce príkazy a do 18:00 NY nevstúpi._

1. **Na čo sa to hodí a na čo nie.** Na prop účty s MNQ / NQ, kde pozícia nesmie prežiť koniec dňa — inak to isté čo
   `ibsentrynet`: graf 3m s 1m detailom, scalp s TP 0,5 R, winrate 74 %, medián držania 2 bary. Veľkosť je z rizika
   (~950 $ na obchod, nie 1 kontrakt): 95. percentil drawdownu 14,3 % z 60 000 $ = ~8 600 $, to je viac než
   celkový limit bežnej 50k výzvy (2 000–2 500 $). Na prop účet teda s rizikom okolo 200–250 $ na obchod (1 MNQ pri
   typickom stope), nie s 950 $.
2. **Má to potenciál? Áno.** EOD zoberie len málo: 817 → 788 obchodov (−29), break-even 0,0179 → 0,0171 % (−4 %),
   +8,2 σ, 5 z 5 okien v zisku, posledné obdobie na 79. percentile. `session_end` je len 2,5 % výstupov — stratégia
   väčšinu obchodov dokončí za pár minút. Najviac to zasiahne rok 22/23 (break-even 0,0098 → 0,0067 %, max DD 9,1 →
   11,7 %): presne tam boli zisky z pozícií cez noc. Rok 23/24 sa naopak zlepší (0,0089 → 0,0110 %, DD 6,1 → 4,5 %).
3. **Čo treba dorobiť.** (a) Analytika ráta prekrytie okien 2023/24 a 2024/25 dvakrát — séria 5 strát je v skutočnosti 3.
   (b) Posledný vstup by mal mať odstup od 15:59: obchod otvorený o 15:50 s cieľom 0,5 R často nestihne ani TP, ani SL a
   zatvorí sa na čase — parameter „najneskorší vstup“ pred EOD dnes chýba (riadi sa len koncom seansy `sess2TradeEnd`).
   (c) Sviatky so skráteným obchodovaním (13:00 NY) EOD nepozná — zatvorí až o 15:59, keď trh dávno stojí.
4. **Čo otestovať ďalej.** `cli checkup --strategy ibsentryneteod --profile tester/profiles/SMERNICE_CS_EOD_IBS_Entry_Zone_1.json
   --pair MNQ/USD --timeframe 3m --fee 1.755e-05 --set maxLossDollar=250 --no-write` — drawdown v dolároch pri riziku, aké
   prop účet unesie; rozhodne, či 95. percentil ostane pod limitom výzvy. Potom `cli prop` nad behmi tohto dokumentu
   s pravidlami konkrétnej výzvy (denná strata, trailing drawdown).
5. **Je to použiteľné? Áno, na prop účty** — edge je takmer celý zachovaný, len s menším rizikom na obchod, než má
   profil. Pred ostrým účtom forward test (rovnako ako `ibsentrynet`).
6. **Čo by som pridal.** Denný stop po 2 stratách a stop vstupov 15 minút pred EOD; obe priamo mieria na pravidlá prop
   výziev, kde jeden zlý deň ukončí účet skôr než zlý mesiac.

<!-- POSUDOK KONIEC -->
