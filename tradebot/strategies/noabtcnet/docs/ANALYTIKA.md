# Základná analytika — NOA 1.0 BTC (C# jadro) (`noabtcnet`)

Zmerané 2026-11-13 na `BTC/USDT:USDT` 5m, engine `multicharts`, poplatok 0.0200 % na stranu (zadané cez --fee), profil `tradebot/strategies/noabtcnet/configs/btcusdt_binance_5m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy noabtcnet \
   --profile tradebot/strategies/noabtcnet/configs/btcusdt_binance_5m.json \
   --pair BTC/USDT:USDT \
   --timeframe 5m \
   --fee 0.0002 \
   --wallet 60000
```

## V čom je dobrá

- 1132 obchodov spolu — na štatistiku dosť
- break-even 0.0460 % je nad poplatkom 0.0200 % (rezerva +0.0260 bodu)
- odlíšiteľná od náhody (+3.3 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 28. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- zisková v 4 z 5 referenčných okien (20240904-20250904 v strate)
- edge nad poplatkom len v 95 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 36.0 % (namerané 17.3 % medián) — na účet to treba mať
- 87.6 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 's trendom' vlastnosti 'S trendom, alebo proti': 1080 obchodov (95.4 %), bez nej by break-even bol o +0.0185 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 244 | +14.41 | 0.0693 | 7.0 | 33.2 | +7/-17 | `20261113-172510-562735` |
| 20221001-20231001 | 193 | +20.32 | 0.1518 | 1.9 | 36.8 | +5/-10 | `20261113-172529-f08f1a` |
| 20231001-20241001 | 223 | +21.64 | 0.0736 | 5.5 | 33.6 | +4/-11 | `20261113-172547-bb6cc5` |
| 20240904-20250904 | 247 | -19.24 | -0.0052 | 35.1 | 34.4 | +5/-14 | `20261113-172602-90a551` |
| 20250904-20260904 | 236 | +21.74 | 0.0529 | 16.0 | 36.4 | +8/-20 | `20261113-172618-b5980c` |

Zisková v **4 z 5** okien, obchodov spolu 1132, break-even celkom 0.0460 %. Okná sa prekrývajú, 11 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+1.20 ATR za 5 barov)
- medián držania 11 barov grafu
- winrate 34.72 %, payoff 2.206
- 0.63 obchodov za deň
- šikmosť výnosov +2.482

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `session_end` 87.6 %, `stop_loss` 12.4 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 's trendom' vlastnosti 'S trendom, alebo proti': 1080 obchodov (95.4 %), break-even 0.0452 % oproti 0.046 % celku. Bez nej by break-even bol 0.0645 % (+0.0185). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 1080 | 95.4 % | 34.8 | 0.0452 | 0.0645 | +0.0185 |
| proti trendu | 52 | 4.6 % | 32.7 | 0.0645 | 0.0452 | -0.0008 |

**Smer** (riadi `tradeDirection`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| long | 529 | 46.7 % | 36.1 | 0.0286 | 0.0625 | +0.0165 |
| short | 603 | 53.3 % | 33.5 | 0.0625 | 0.0286 | -0.0174 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.8664 – 0.9352 | 283 | 25.0 % | 28.6 | -0.0027 | 0.0620 | +0.0160 |
| do 0.7492 | 284 | 25.1 % | 35.2 | 0.0425 | 0.0470 | +0.0010 |
| nad 0.9352 | 282 | 24.9 % | 34.8 | 0.0486 | 0.0449 | -0.0011 |
| 0.7492 – 0.8664 | 283 | 25.0 % | 40.3 | 0.0969 | 0.0301 | -0.0159 |

Parametre, ktorými sa dá s tým niečo spraviť: `hardStopPct`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0460 % | -0.0022 % ± 0.0145 | +3.32 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0460 % | -0.0018 % ± 0.0156 | +3.07 | 99.7 |

Edge je odlisitelny od nahody (3.3 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 281 | 19.1 | 32.0 | 0.0669 | 74 |
| 2022-12 - 2024-03 | 261 | 17.7 | 36.8 | 0.1354 | 99 |
| 2024-03 - 2025-06 | 295 | 20.0 | 35.9 | 0.0249 | 27 |
| 2025-06 - 2026-09 | 295 | 20.0 | 34.2 | 0.0278 | 28 |

Hranice pre úsek veľkosti posledného obdobia: -0.0042 až +0.1013 % (medián 0.0461).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 28. percentile, teda v medziach -0.0042 až +0.1013 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 8** — 2025-11-06T19:30 až 2025-11-18T17:25, spolu +5812.28.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-11-06T19:30 | 2025-11-06T20:55 | +837.47 | +0.82 | `session_end` |
| 2 | 2025-11-07T17:30 | 2025-11-07T20:55 | +1377.30 | +1.35 | `session_end` |
| 3 | 2025-11-11T15:30 | 2025-11-11T18:55 | +270.00 | +0.26 | `session_end` |
| 4 | 2025-11-11T20:00 | 2025-11-11T20:55 | +257.63 | +0.25 | `session_end` |
| 5 | 2025-11-12T16:30 | 2025-11-12T20:25 | +37.62 | +0.04 | `session_end` |
| 6 | 2025-11-13T17:30 | 2025-11-13T20:55 | +2096.12 | +2.09 | `session_end` |
| 7 | 2025-11-17T18:00 | 2025-11-17T20:55 | +806.58 | +0.87 | `session_end` |
| 8 | 2025-11-18T15:30 | 2025-11-18T17:25 | +129.57 | +0.14 | `session_end` |

**Straty za sebou: 20** — 2026-04-06T16:00 až 2026-05-04T15:20, spolu -5794.96.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-04-06T16:00 | 2026-04-06T16:25 | -86.56 | -0.12 | `session_end` |
| 2 | 2026-04-07T15:00 | 2026-04-07T15:25 | -355.80 | -0.52 | `session_end` |
| 3 | 2026-04-09T16:00 | 2026-04-09T18:25 | -267.30 | -0.37 | `session_end` |
| 4 | 2026-04-10T14:30 | 2026-04-10T15:55 | -541.07 | -0.74 | `session_end` |
| 5 | 2026-04-10T17:00 | 2026-04-10T17:25 | -54.48 | -0.07 | `session_end` |
| 6 | 2026-04-10T18:00 | 2026-04-10T18:25 | -169.10 | -0.23 | `session_end` |
| 7 | 2026-04-10T19:00 | 2026-04-10T19:25 | -133.00 | -0.18 | `session_end` |
| 8 | 2026-04-14T14:00 | 2026-04-14T14:55 | -534.89 | -0.71 | `session_end` |
| 9 | 2026-04-14T16:00 | 2026-04-14T16:25 | -98.09 | -0.13 | `session_end` |
| 10 | 2026-04-16T14:00 | 2026-04-16T14:55 | -210.54 | -0.29 | `session_end` |
| 11 | 2026-04-16T15:30 | 2026-04-16T15:55 | -537.96 | -0.73 | `session_end` |
| 12 | 2026-04-16T17:00 | 2026-04-16T17:25 | -70.16 | -0.09 | `session_end` |
| 13 | 2026-04-17T14:00 | 2026-04-17T17:25 | -135.20 | -0.17 | `session_end` |
| 14 | 2026-04-17T18:00 | 2026-04-17T18:25 | -346.72 | -0.45 | `session_end` |
| 15 | 2026-04-21T17:30 | 2026-04-21T17:55 | -254.86 | -0.34 | `session_end` |
| 16 | 2026-04-22T15:30 | 2026-04-22T16:25 | -171.68 | -0.22 | `session_end` |
| 17 | 2026-04-27T15:30 | 2026-04-27T19:55 | -52.13 | -0.07 | `session_end` |
| 18 | 2026-04-29T18:30 | 2026-04-29T19:55 | -441.03 | -0.59 | `session_end` |
| 19 | 2026-05-01T14:00 | 2026-05-01T14:25 | -495.78 | -0.63 | `session_end` |
| 20 | 2026-05-04T15:00 | 2026-05-04T15:20 | -838.60 | -1.05 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0460 %**, medián 0.0458 %, 90 % interval 0.0194–0.0733 %
- P(edge > poplatok) = **94.6 %**
- max drawdown: medián 17.3 %, 95. percentil 36.0 %, najhorší 89.5 %
- najdlhšia séria strát: medián 16, 95. percentil 24 obchodov
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
<!-- POSUDOK cisla=19d62a57 -->

_C# prepis `noabtc` (parita bar po bare) — čísla aj posudok sú tie isté._

**1. Na čo sa to hodí.** Únik z pásma šumu od otvorenia New Yorku na BTCUSDT.P 5m. Pásmo je v percentách, takže sa na BTC prenáša bez prepočtu; hodí sa na pracovné dni, víkend BTC (polovičná volatilita) logika nemá.

**2. Potenciál.** **Áno, najväčší z ôsmich BTC kópií.** Východisko z MNQ bez ladenia: zisk v 4 z 5 okien (break-even 0,05–0,15 %), proti náhode **+3,3 sigma**, edge v poslednom období drží (28. percentil). Slabé je len okno 24/25 (−19 %), kde BTC po halvingu chodil v širokom pásme.

**3. Čo dorobiť.** Hard stop je z MNQ (0,41 %) — na BTC je pohyb dňa 2,3× väčší, smernica skúša 0,5–3 %. Shorty sú výrazne lepšie ako longy (break-even 0,063 vs. 0,029 %).

**4. Čo otestovať.** Smernica na BTC (od ne 15. 11. 2026 po testoch MYM, do ne 22. 11. 18:00) s poplatkom maker 0,02 %; rozhodne odložený rok 9/2025–9/2026 a stabilita po rokoch. Ak prejde, krok 9 (robustnosť) a porovnanie s C# `noabtcnet` naživo.

**5. Použiteľné?** **Áno, kandidát č. 1 na BTC** — za týmto číslom je skutočný jav (otvorenie NY), nie vzorka.

**6. Čo by som pridal.** Filter režimu: vynechať dni, keď je denný rozsah BTC za posledné 2 týždne pod mediánom (okno 24/25).

<!-- POSUDOK KONIEC -->
