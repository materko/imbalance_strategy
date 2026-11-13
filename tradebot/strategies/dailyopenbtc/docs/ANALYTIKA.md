# Základná analytika — DAILY OPEN 1.0 (BTC) (`dailyopenbtc`)

Zmerané 2026-11-13 na `BTC/USDT:USDT` 1h, engine `multicharts`, poplatok 0.0200 % na stranu (zadané cez --fee), profil `tradebot/strategies/dailyopenbtc/configs/btcusdt_binance_1h.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy dailyopenbtc \
   --profile tradebot/strategies/dailyopenbtc/configs/btcusdt_binance_1h.json \
   --pair BTC/USDT:USDT \
   --timeframe 1h \
   --fee 0.0002 \
   --wallet 60000
```

## V čom je dobrá

- 1045 obchodov spolu — na štatistiku dosť
- break-even 0.0452 % je nad poplatkom 0.0200 % (rezerva +0.0252 bodu)
- odlíšiteľná od náhody (+3.2 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 47. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- zisková v 4 z 5 referenčných okien (20211001-20221001 v strate)
- edge nad poplatkom len v 89 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 47.4 % (namerané 22.6 % medián) — na účet to treba mať
- 25.3 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 'do 12 h' vlastnosti 'Hodina vstupu (UTC)': 547 obchodov (52.3 %), bez nej by break-even bol o +0.0546 lepší (riadi `entryStartH`)

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 219 | -11.56 | -0.0217 | 21.4 | 18.7 | +3/-23 | `20261113-172427-0eb9f1` |
| 20221001-20231001 | 202 | +1.55 | 0.0295 | 7.3 | 18.8 | +3/-15 | `20261113-172433-85701d` |
| 20231001-20241001 | 212 | +21.39 | 0.0757 | 15.6 | 24.5 | +6/-14 | `20261113-172436-6757a5` |
| 20240904-20250904 | 219 | +34.12 | 0.0698 | 12.0 | 24.7 | +3/-14 | `20261113-172443-c979dd` |
| 20250904-20260904 | 208 | +7.91 | 0.0338 | 15.8 | 23.1 | +5/-14 | `20261113-172446-18ec9a` |

Zisková v **4 z 5** okien, obchodov spolu 1045, break-even celkom 0.0452 %. Okná sa prekrývajú, 15 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+0.61 ATR za 5 barov)
- medián držania 1.3 barov grafu
- winrate 21.91 %, payoff 4.083
- 0.58 obchodov za deň
- šikmosť výnosov +3.046

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 73.6 %, `session_end` 25.3 %, `take_profit` 1.1 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'do 12 h' vlastnosti 'Hodina vstupu (UTC)': 547 obchodov (52.3 %), break-even -0.0052 % oproti 0.0452 % celku. Bez nej by break-even bol 0.0998 % (+0.0546). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: skus preladit `entryStartH`.


**Hodina vstupu (UTC)** (riadi `entryStartH`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 12 h | 547 | 52.3 % | 22.9 | -0.0052 | 0.0998 | +0.0546 |
| nad 13 h | 161 | 15.4 % | 11.2 | 0.0671 | 0.0411 | -0.0041 |
| 12 h – 13 h | 337 | 32.2 % | 25.5 | 0.1157 | 0.0116 | -0.0336 |

**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.0591 – 0.1274 | 261 | 25.0 % | 16.1 | -0.0492 | 0.0783 | +0.0331 |
| 0.1274 – 0.2171 | 261 | 25.0 % | 22.2 | 0.0375 | 0.0477 | +0.0025 |
| do 0.0591 | 262 | 25.1 % | 23.3 | 0.0708 | 0.0370 | -0.0082 |
| nad 0.2171 | 261 | 25.0 % | 26.1 | 0.1272 | 0.0182 | -0.0270 |

**Deň v týždni**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| štvrtok | 204 | 19.5 % | 18.6 | -0.0418 | 0.0660 | +0.0208 |
| piatok | 206 | 19.7 % | 20.4 | 0.0023 | 0.0554 | +0.0102 |
| utorok | 207 | 19.8 % | 20.3 | 0.0351 | 0.0476 | +0.0024 |
| pondelok | 214 | 20.5 % | 23.8 | 0.0584 | 0.0417 | -0.0035 |
| streda | 214 | 20.5 % | 26.2 | 0.1611 | 0.0144 | -0.0308 |

Parametre, ktorými sa dá s tým niečo spraviť: `entryStartH`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0452 % | -0.0002 % ± 0.0140 | +3.25 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0452 % | 0.0003 % ± 0.0146 | +3.09 | 99.7 |

Edge je odlisitelny od nahody (3.2 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 263 | 17.8 | 20.1 | -0.0112 | 10 |
| 2022-12 - 2024-03 | 257 | 17.4 | 22.6 | 0.1028 | 93 |
| 2024-03 - 2025-06 | 270 | 18.3 | 21.5 | 0.0518 | 62 |
| 2025-06 - 2026-09 | 255 | 17.3 | 23.5 | 0.0400 | 47 |

Hranice pre úsek veľkosti posledného obdobia: -0.0221 až +0.1154 % (medián 0.0434).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 47. percentile, teda v medziach -0.0221 až +0.1154 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 6** — 2024-02-06T13:15 až 2024-02-14T20:00, spolu +4331.17.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-02-06T13:15 | 2024-02-06T20:00 | +219.42 | +0.51 | `session_end` |
| 2 | 2024-02-07T13:00 | 2024-02-07T20:00 | +1039.47 | +2.41 | `session_end` |
| 3 | 2024-02-08T13:00 | 2024-02-08T20:00 | +776.97 | +1.74 | `session_end` |
| 4 | 2024-02-09T13:00 | 2024-02-09T20:00 | +158.84 | +0.34 | `session_end` |
| 5 | 2024-02-12T14:10 | 2024-02-12T20:00 | +2059.94 | +4.28 | `session_end` |
| 6 | 2024-02-14T13:00 | 2024-02-14T20:00 | +76.54 | +0.15 | `session_end` |

**Straty za sebou: 23** — 2022-05-20T12:00 až 2022-06-28T15:22, spolu -5174.47.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-05-20T12:00 | 2022-05-20T12:48 | -271.91 | -0.89 | `stop_loss` |
| 2 | 2022-05-23T12:00 | 2022-05-23T14:02 | -260.61 | -0.86 | `stop_loss` |
| 3 | 2022-05-24T12:04 | 2022-05-24T12:09 | -61.72 | -0.21 | `stop_loss` |
| 4 | 2022-05-27T12:29 | 2022-05-27T12:30 | -61.60 | -0.21 | `stop_loss` |
| 5 | 2022-05-30T12:00 | 2022-05-30T13:19 | -345.60 | -1.13 | `stop_loss` |
| 6 | 2022-05-31T12:19 | 2022-05-31T12:22 | -62.71 | -0.20 | `stop_loss` |
| 7 | 2022-06-01T12:30 | 2022-06-01T12:32 | -62.65 | -0.20 | `stop_loss` |
| 8 | 2022-06-02T12:00 | 2022-06-02T13:15 | -471.37 | -1.56 | `stop_loss` |
| 9 | 2022-06-06T12:00 | 2022-06-06T15:19 | -189.62 | -0.60 | `stop_loss` |
| 10 | 2022-06-07T13:33 | 2022-06-07T14:00 | -61.82 | -0.21 | `stop_loss` |
| 11 | 2022-06-08T12:00 | 2022-06-08T18:35 | -425.28 | -1.40 | `stop_loss` |
| 12 | 2022-06-09T12:01 | 2022-06-09T12:14 | -62.12 | -0.20 | `stop_loss` |
| 13 | 2022-06-10T12:14 | 2022-06-10T12:15 | -62.04 | -0.21 | `stop_loss` |
| 14 | 2022-06-14T12:02 | 2022-06-14T12:04 | -58.84 | -0.27 | `stop_loss` |
| 15 | 2022-06-15T12:15 | 2022-06-15T12:17 | -58.58 | -0.27 | `stop_loss` |
| 16 | 2022-06-17T12:00 | 2022-06-17T19:00 | -465.59 | -2.22 | `session_end` |
| 17 | 2022-06-20T12:00 | 2022-06-20T18:02 | -852.35 | -4.10 | `stop_loss` |
| 18 | 2022-06-21T12:00 | 2022-06-21T19:00 | -82.17 | -0.39 | `session_end` |
| 19 | 2022-06-22T12:00 | 2022-06-22T12:42 | -216.76 | -1.06 | `stop_loss` |
| 20 | 2022-06-23T12:00 | 2022-06-23T17:03 | -454.76 | -2.20 | `stop_loss` |
| 21 | 2022-06-24T12:00 | 2022-06-24T15:10 | -127.14 | -0.60 | `stop_loss` |
| 22 | 2022-06-27T12:00 | 2022-06-27T13:33 | -165.69 | -0.78 | `stop_loss` |
| 23 | 2022-06-28T12:00 | 2022-06-28T15:22 | -293.54 | -1.40 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0452 %**, medián 0.0449 %, 90 % interval 0.0116–0.0793 %
- P(edge > poplatok) = **89.1 %**
- max drawdown: medián 22.6 %, 95. percentil 47.4 %, najhorší 100.0 %
- najdlhšia séria strát: medián 22, 95. percentil 31 obchodov
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
<!-- POSUDOK cisla=8a6e9c8d -->

**1. Na čo sa to hodí.** Prieraz denného otvorenia na BTCUSDT.P 1h, body z MNQ ×7. Hodí sa na trendové mesiace; WR ~20 % chce účet, ktorý znesie dlhé série strát.

**2. Potenciál.** **Áno, stredný.** Proti náhode +3,25 sigma a edge sa v čase zlepšuje (21/22 −12 %, 23/24 +21 %, 24/25 +34 %, 25/26 +8 %); drží (47. percentil). Prvý rok je stratový — treba overiť, že nejde o náhodu posledných dvoch rokov.

**3. Čo dorobiť.** Body (`breakPts`, `slPts`, `tpPts`) sú len prepočet ×7 z MNQ — na BTC by mali byť v percentách alebo ATR, lebo cena BTC sa za 5 rokov zmenila 4×.

**4. Čo otestovať.** Smernica na BTC (od ne 15. 11. 2026 po testoch MYM, do ne 22. 11. 18:00) s poplatkom maker 0,02 %; rozhodne odložený rok 9/2025–9/2026 a stabilita po rokoch.

**5. Použiteľné?** **Áno, s výhradou** stabilných rokov — rozhodne smernica.

**6. Čo by som pridal.** Prah prierazu v % ceny namiesto bodov.

<!-- POSUDOK KONIEC -->
