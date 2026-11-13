# Základná analytika — Overnight Bias ORB (BTC) (`onbiasorbbtc`)

Zmerané 2026-11-13 na `BTC/USDT:USDT` 15m, engine `multicharts`, poplatok 0.0200 % na stranu (zadané cez --fee), profil `tradebot/strategies/onbiasorbbtc/configs/btcusdt_binance_15m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy onbiasorbbtc \
   --profile tradebot/strategies/onbiasorbbtc/configs/btcusdt_binance_15m.json \
   --pair BTC/USDT:USDT \
   --timeframe 15m \
   --fee 0.0002 \
   --wallet 60000
```

## V čom je dobrá

- 663 obchodov spolu — na štatistiku dosť
- break-even 0.0422 % je nad poplatkom 0.0200 % (rezerva +0.0222 bodu)
- drawdown drží: 95. percentil 17.7 %
- edge drží aj v poslednom období (2025-06 - 2026-09 na 34. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- zisková v 4 z 5 referenčných okien (20240904-20250904 v strate)
- edge nad poplatkom len v 88 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- proti náhode len +1.7 sigma: náznak, nie dôkaz
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- 65 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 'do 3 R' vlastnosti 'Plánovaný RR': 651 obchodov (98.2 %), bez nej by break-even bol o +0.5937 lepší (riadi `rr`)

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 130 | +1.77 | 0.0405 | 4.7 | 43.1 | +4/-11 | `20261113-171935-f3db5a` |
| 20221001-20231001 | 112 | +6.62 | 0.0720 | 2.1 | 42.9 | +5/-6 | `20261113-171941-c99cc0` |
| 20231001-20241001 | 149 | +8.26 | 0.0773 | 4.9 | 47.0 | +4/-8 | `20261113-171947-f9a984` |
| 20240904-20250904 | 137 | -7.41 | -0.0289 | 8.8 | 41.6 | +3/-8 | `20261113-171953-eae89e` |
| 20250904-20260904 | 147 | +5.12 | 0.0512 | 3.6 | 43.5 | +5/-6 | `20261113-171959-7ac89e` |

Zisková v **4 z 5** okien, obchodov spolu 663, break-even celkom 0.0422 %. Okná sa prekrývajú, 12 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.27 ATR za 5 barov)
- medián držania 15 barov grafu
- winrate 43.89 %, payoff 1.426
- 0.37 obchodov za deň
- šikmosť výnosov +1.055

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `session_end` 65 %, `stop_loss` 29.3 %, `take_profit` 5.7 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'do 3 R' vlastnosti 'Plánovaný RR': 651 obchodov (98.2 %), break-even 0.0329 % oproti 0.0422 % celku. Bez nej by break-even bol 0.6359 % (+0.5937). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: skus preladit `rr`.


**Plánovaný RR** (riadi `rr`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 3 R | 651 | 98.2 % | 43.3 | 0.0329 | 0.6359 | +0.5937 |
| nad 3 R | 12 | 1.8 % | 75.0 | 0.6359 | 0.0329 | -0.0093 |

**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 632 | 95.3 % | 43.4 | 0.0410 | 0.0674 | +0.0252 |
| proti trendu | 31 | 4.7 % | 54.8 | 0.0674 | 0.0410 | -0.0012 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 16 – 23 | 167 | 25.2 % | 38.9 | -0.0340 | 0.0672 | +0.0250 |
| do 8 | 175 | 26.4 % | 40.0 | 0.0144 | 0.0523 | +0.0101 |
| nad 23 | 148 | 22.3 % | 50.7 | 0.0705 | 0.0342 | -0.0080 |
| 8 – 16 | 173 | 26.1 % | 46.8 | 0.1173 | 0.0151 | -0.0271 |

Parametre, ktorými sa dá s tým niečo spraviť: `adxMin`, `exitHHMM`, `minEntryHHMM`, `rr`, `slPct`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0341 % | 0.0000 % ± 0.0204 | +1.67 | 95.1 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0341 % | 0.0000 % ± 0.0212 | +1.61 | 93.9 |

Naznak, ale nie dokaz (1.7 sigma, percentil 95.1). Take rozdiely nahoda robi bezne.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 157 | 10.6 | 41.4 | 0.0341 | 48 |
| 2022-12 - 2024-03 | 145 | 9.8 | 46.9 | 0.1138 | 93 |
| 2024-03 - 2025-06 | 182 | 12.3 | 45.6 | -0.0056 | 10 |
| 2025-06 - 2026-09 | 179 | 12.1 | 41.9 | 0.0266 | 34 |

Hranice pre úsek veľkosti posledného obdobia: -0.0187 až +0.1058 % (medián 0.0413).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 34. percentile, teda v medziach -0.0187 až +0.1058 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 5** — 2023-03-30T15:30 až 2023-04-14T19:15, spolu +758.62, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-03-30T15:30 | 2023-03-30T19:15 | +256.03 | +1.08 | `session_end` |
| 2 | 2023-04-08T18:00 | 2023-04-08T19:15 | +2.64 | +0.01 | `session_end` |
| 3 | 2023-04-11T14:00 | 2023-04-11T19:15 | +146.21 | +0.53 | `session_end` |
| 4 | 2023-04-13T14:30 | 2023-04-13T19:15 | +39.33 | +0.14 | `session_end` |
| 5 | 2023-04-14T14:45 | 2023-04-14T19:15 | +314.41 | +1.07 | `session_end` |

**Straty za sebou: 11** — 2022-05-24T14:00 až 2022-06-17T19:15, spolu -2345.29.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-05-24T14:00 | 2022-05-24T15:47 | -305.52 | -2.05 | `stop_loss` |
| 2 | 2022-05-31T17:00 | 2022-05-31T18:55 | -306.98 | -1.68 | `stop_loss` |
| 3 | 2022-06-03T14:45 | 2022-06-03T19:15 | -99.02 | -0.56 | `session_end` |
| 4 | 2022-06-06T14:15 | 2022-06-06T17:17 | -308.52 | -1.55 | `stop_loss` |
| 5 | 2022-06-10T16:30 | 2022-06-10T19:15 | -57.66 | -0.30 | `session_end` |
| 6 | 2022-06-11T14:30 | 2022-06-11T19:15 | -41.26 | -0.22 | `session_end` |
| 7 | 2022-06-12T14:00 | 2022-06-12T14:51 | -307.38 | -1.68 | `stop_loss` |
| 8 | 2022-06-13T14:45 | 2022-06-13T16:09 | -306.05 | -1.97 | `stop_loss` |
| 9 | 2022-06-15T14:15 | 2022-06-15T14:54 | -305.60 | -2.13 | `stop_loss` |
| 10 | 2022-06-16T14:15 | 2022-06-16T17:18 | -305.60 | -2.22 | `stop_loss` |
| 11 | 2022-06-17T14:45 | 2022-06-17T19:15 | -1.70 | -0.01 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0422 %**, medián 0.0422 %, 90 % interval 0.0104–0.0751 %
- P(edge > poplatok) = **87.5 %**
- max drawdown: medián 8.9 %, 95. percentil 17.7 %, najhorší 41.0 %
- najdlhšia séria strát: medián 10, 95. percentil 14 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **435** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=6e853b84 -->

**1. Na čo sa to hodí.** ORB v smere nočného biasu na BTCUSDT.P 15m, otvorenie NY. Málo obchodov (~140/rok) s WR ~44 %.

**2. Potenciál.** **Áno, slabší.** Zisk v 4 z 5 okien, ale proti náhode len +1,7 sigma — edge je malý a od náhody sa líši len náznakom.

**3. Čo dorobiť.** `slPct` je v percentách rozsahu OR, to je v poriadku; nočný bias BTC (24/7) nemá zatvorenie trhu, takže „noc“ je len okno — overiť, či definícia biasu dáva na BTC zmysel.

**4. Čo otestovať.** Smernica na BTC (od ne 15. 11. 2026 po testoch MYM, do ne 22. 11. 18:00) s poplatkom maker 0,02 %; rozhodne odložený rok 9/2025–9/2026 a stabilita po rokoch.

**5. Použiteľné?** **Zatiaľ nerozhodnuté — rozhodne smernica**; bez zlepšenia ladením je o ničom.

**6. Čo by som pridal.** Bias z ázijskej seansy (0–8 UTC) namiesto nočnej seansy CME.

<!-- POSUDOK KONIEC -->
