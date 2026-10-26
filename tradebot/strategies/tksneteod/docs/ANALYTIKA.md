# Základná analytika — TKS 1.0 (C# jadro EOD) (`tksneteod`)

Zmerané 2026-10-26 na `MNQ/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tester/profiles/SMERNICE_CS_EOD_TKS_1.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy tksneteod \
   --profile tester/profiles/SMERNICE_CS_EOD_TKS_1.json \
   --pair MNQ/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 872 obchodov spolu — na štatistiku dosť
- break-even 0.0328 % je nad poplatkom 0.0018 % (rezerva +0.0310 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 5.4 %
- odlíšiteľná od náhody (+5.3 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 64. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'long' vlastnosti 'Smer': 546 obchodov (62.6 %), bez nej by break-even bol o +0.0233 lepší (riadi `tradeDirection`)

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 163 | +7.33 | 0.0505 | 1.9 | 70.5 | +9/-4 | `20261026-125837-f31ec5` |
| 20221001-20231001 | 175 | +3.94 | 0.0274 | 1.4 | 66.3 | +11/-4 | `20261026-125845-cee15d` |
| 20231001-20241001 | 191 | +2.53 | 0.0128 | 1.6 | 63.9 | +10/-4 | `20261026-125851-cd1024` |
| 20240904-20250904 | 181 | +6.84 | 0.0285 | 3.1 | 69.1 | +10/-5 | `20261026-125857-1dc7fb` |
| 20250904-20260904 | 176 | +11.72 | 0.0393 | 2.0 | 69.9 | +10/-3 | `20261026-125903-0f51a1` |

Zisková v **5 z 5** okien, obchodov spolu 872, break-even celkom 0.0328 %. Okná sa prekrývajú, 14 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.36 ATR za 5 barov)
- medián držania 16.7 barov grafu
- winrate 68.23 %, payoff 0.65
- 0.48 obchodov za deň
- šikmosť výnosov -0.919

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 61.1 %, `stop_loss` 21 %, `session_end` 17.9 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'long' vlastnosti 'Smer': 546 obchodov (62.6 %), break-even 0.0194 % oproti 0.0328 % celku. Bez nej by break-even bol 0.0561 % (+0.0233). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: skus preladit `tradeDirection`.


**Smer** (riadi `tradeDirection`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| long | 546 | 62.6 % | 67.6 | 0.0194 | 0.0561 | +0.0233 |
| short | 326 | 37.4 % | 69.3 | 0.0561 | 0.0194 | -0.0134 |

**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.4112 % – 0.642 % | 218 | 25.0 % | 64.7 | -0.0005 | 0.0442 | +0.0114 |
| do 0.4112 % | 219 | 25.1 % | 72.2 | 0.0158 | 0.0391 | +0.0063 |
| 0.642 % – 0.964 % | 218 | 25.0 % | 71.1 | 0.0577 | 0.0245 | -0.0083 |
| nad 0.964 % | 217 | 24.9 % | 65.0 | 0.0635 | 0.0238 | -0.0090 |

**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.0965 | 219 | 25.1 % | 67.6 | 0.0064 | 0.0419 | +0.0091 |
| 0.1786 – 0.2699 | 218 | 25.0 % | 66.1 | 0.0249 | 0.0353 | +0.0025 |
| 0.0965 – 0.1786 | 218 | 25.0 % | 72.0 | 0.0326 | 0.0328 | +0.0000 |
| nad 0.2699 | 217 | 24.9 % | 67.3 | 0.0677 | 0.0211 | -0.0117 |

Parametre, ktorými sa dá s tým niečo spraviť: `rrRatio`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0328 % | -0.0002 % ± 0.0062 | +5.30 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0328 % | -0.0004 % ± 0.0072 | +4.63 | 100.0 |

Edge je odlisitelny od nahody (5.3 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 202 | 13.7 | 70.8 | 0.0546 | 92 |
| 2022-12 - 2024-03 | 218 | 14.8 | 64.2 | 0.0145 | 13 |
| 2024-03 - 2025-06 | 233 | 15.8 | 67.4 | 0.0258 | 33 |
| 2025-06 - 2026-09 | 219 | 14.8 | 70.8 | 0.0384 | 64 |

Hranice pre úsek veľkosti posledného obdobia: +0.0082 až +0.0579 % (medián 0.0329).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 64. percentile, teda v medziach +0.0082 až +0.0579 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 11** — 2023-08-07T13:48 až 2023-08-31T17:22, spolu +879.71.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-08-07T13:48 | 2023-08-07T13:49 | +28.92 | +0.09 | `take_profit` |
| 2 | 2023-08-08T13:48 | 2023-08-08T14:01 | +78.93 | +0.26 | `take_profit` |
| 3 | 2023-08-15T14:18 | 2023-08-15T19:54 | +53.94 | +0.18 | `session_end` |
| 4 | 2023-08-17T14:12 | 2023-08-17T14:34 | +95.45 | +0.32 | `take_profit` |
| 5 | 2023-08-17T15:00 | 2023-08-17T18:36 | +116.46 | +0.39 | `take_profit` |
| 6 | 2023-08-23T14:00 | 2023-08-23T14:43 | +134.44 | +0.45 | `take_profit` |
| 7 | 2023-08-29T13:45 | 2023-08-29T13:46 | +66.94 | +0.22 | `take_profit` |
| 8 | 2023-08-30T14:00 | 2023-08-30T14:12 | +78.41 | +0.25 | `take_profit` |
| 9 | 2023-08-30T15:00 | 2023-08-30T16:46 | +97.41 | +0.31 | `take_profit` |
| 10 | 2023-08-31T14:03 | 2023-08-31T14:29 | +73.91 | +0.24 | `take_profit` |
| 11 | 2023-08-31T17:09 | 2023-08-31T17:22 | +54.91 | +0.18 | `take_profit` |

**Straty za sebou: 5** — 2024-09-25T17:21 až 2024-10-03T17:00, spolu -779.56, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-09-25T17:21 | 2024-09-25T17:21 | -9.92 | -0.02 | `stop_loss` |
| 2 | 2024-09-25T18:00 | 2024-09-25T19:54 | -31.92 | -0.08 | `session_end` |
| 3 | 2024-09-26T15:15 | 2024-09-26T19:54 | -148.92 | -0.37 | `session_end` |
| 4 | 2024-10-02T13:45 | 2024-10-02T14:20 | -349.40 | -0.88 | `stop_loss` |
| 5 | 2024-10-03T14:36 | 2024-10-03T17:00 | -239.40 | -0.60 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0328 %**, medián 0.0328 %, 90 % interval 0.0207–0.0450 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 3.2 %, 95. percentil 5.4 %, najhorší 12.8 %
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
<!-- POSUDOK cisla=bedfc252 -->

_Posudok (Claude, 26. 10. 2026) — nastavenie „TKS 1 C# EOD“ (`SMERNICE_CS_EOD_TKS_1`, parametre ako TKS 1), kópia
`tksnet` so zatvorením o 15:59 NY pre prop účty (`EodCloseEngine`)._

1. **Na čo sa to hodí a na čo nie.** MNQ / NQ 3m na prop účtoch, ktoré vyžadujú flat na konci dňa. Na rozdiel od NOA
   tu zatvorenie o 15:59 mení veľa, lebo TKS inak drží cez noc: 17,9 % obchodov zavrie čas, break-even klesne
   z 0,0511 na 0,0328 % (−36 %), winrate zo 73,7 na 68,2 %, posledný rok z +18,7 na +11,7 %. Zato je pokojnejší
   rok 2021/22 (+7,3 vs +5,1 %, drawdown 1,9 vs 4,2 %) a najdlhšia séria strát je 5 (95. percentil 7). 95. percentil
   drawdownu 5,4 % (~3 240 $ zo 60 000 $), najhorší 12,8 % — na 50k prop účte treba riziko na obchod znížiť.
2. **Má to potenciál?** Áno: 5 z 5 okien (+2,5 až +11,7 %), +5,3 sigma, break-even 18× nad poplatkom (interval
   0,0207–0,0450 %), posledné obdobie na 64. percentile. Najtenší je rok 2023/24 (0,0128 %, len 7× poplatok) —
   s reálnym sklzom na MNQ by tam bola nula.
3. **Čo treba dorobiť.** Posledný vstup je 270 min po otvorení (14:00 NY): obchody otvorené neskoro nestihnú TP
   a skončia na 15:59 — v EOD variante by mal byť posledný vstup skôr. Overiť naživo hodinové zatvorenie od
   15:58:30 bez nového baru a skrátené seansy (13:00), ktoré 15:59 nepokryje.
4. **Čo otestovať ďalej.** `cli sweep --strategy tksneteod --profile tester/profiles/SMERNICE_CS_EOD_TKS_1.json
   --space "entryEndMin=150:270:30"` — rozhodne, koľko z poklesu break-evenu vracia skorší posledný vstup.
   `cli prop` s pravidlami výzvy na týchto behoch a týždeň na Sim101 s
   `python -m tester.ninjatrader compare --strategy tksneteod --profile tester/profiles/SMERNICE_CS_EOD_TKS_1.json`.
5. **Je to použiteľné?** Áno, ale slabšie než `tksnet` — edge drží (5/5, +5,3 sigma), rezerva nad poplatkom je však
   o tretinu menšia. Na prop účty po forward teste a so skorším posledným vstupom.
6. **Čo by som pridal.** TP, ktorý sa pred koncom dňa zmenší na dosiahnuteľnú vzdialenosť (napr. polovicu) alebo
   presun SL na vstup od 15:30 — obchody, ktoré by inak išli cez noc do TP, by aspoň neskončili na 15:59 v strate.

<!-- POSUDOK KONIEC -->
