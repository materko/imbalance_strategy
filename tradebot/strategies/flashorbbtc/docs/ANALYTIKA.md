# Základná analytika — FLASH TRIGGER ORB 1.0 (BTC) (`flashorbbtc`)

Zmerané 2026-11-13 na `BTC/USDT:USDT` 15m, engine `multicharts`, poplatok 0.0200 % na stranu (zadané cez --fee), profil `tradebot/strategies/flashorbbtc/configs/btcusdt_binance_15m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy flashorbbtc \
   --profile tradebot/strategies/flashorbbtc/configs/btcusdt_binance_15m.json \
   --pair BTC/USDT:USDT \
   --timeframe 15m \
   --fee 0.0002 \
   --wallet 60000
```

## V čom je dobrá

- 1296 obchodov spolu — na štatistiku dosť
- break-even 0.0329 % je nad poplatkom 0.0200 % (rezerva +0.0129 bodu)
- drawdown drží: 95. percentil 14.8 %
- odlíšiteľná od náhody (+2.1 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 32. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- zisková v 4 z 5 referenčných okien (20240904-20250904 v strate)
- edge nad poplatkom len v 85 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- najhoršia skupina 'žiadna' vlastnosti 'Makro udalosť v ten deň': 1171 obchodov (90.4 %), bez nej by break-even bol o +0.1046 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 305 | +6.50 | 0.0651 | 4.1 | 29.8 | +5/-11 | `20261113-172007-46ca6d` |
| 20221001-20231001 | 272 | +1.13 | 0.0252 | 5.5 | 27.9 | +5/-17 | `20261113-172011-8603bb` |
| 20231001-20241001 | 261 | +3.54 | 0.0420 | 4.0 | 29.1 | +4/-11 | `20261113-172017-833cd1` |
| 20240904-20250904 | 215 | -0.38 | 0.0170 | 5.5 | 26.5 | +4/-12 | `20261113-172023-c6e1f3` |
| 20250904-20260904 | 264 | +2.03 | 0.0314 | 3.4 | 28.4 | +3/-11 | `20261113-172029-77ee52` |

Zisková v **4 z 5** okien, obchodov spolu 1296, break-even celkom 0.0329 %. Okná sa prekrývajú, 21 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+1.03 ATR za 5 barov)
- medián držania 14.7 barov grafu
- winrate 28.24 %, payoff 2.702
- 0.72 obchodov za deň
- šikmosť výnosov +2.179

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 71.7 %, `take_profit` 28 %, `force_exit` 0.3 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'žiadna' vlastnosti 'Makro udalosť v ten deň': 1171 obchodov (90.4 %), break-even 0.0251 % oproti 0.0329 % celku. Bez nej by break-even bol 0.1375 % (+0.1046). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| žiadna | 1171 | 90.4 % | 27.6 | 0.0251 | 0.1375 | +0.1046 |
| FOMC | 32 | 2.5 % | 28.1 | 0.0366 | 0.0328 | -0.0001 |
| CPI | 44 | 3.4 % | 34.1 | 0.1583 | 0.0303 | -0.0026 |
| NFP | 48 | 3.7 % | 37.5 | 0.1862 | 0.0288 | -0.0041 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bez udalosti | 1171 | 90.4 % | 27.6 | 0.0251 | 0.1375 | +0.1046 |
| pred vyhlásením | 31 | 2.4 % | 29.0 | 0.0460 | 0.0326 | -0.0003 |
| po vyhlásení | 94 | 7.3 % | 36.2 | 0.1805 | 0.0256 | -0.0073 |

**Volatilita voči normálu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.937 | 325 | 25.1 % | 25.2 | 0.0013 | 0.0588 | +0.0259 |
| 1.235 – 1.504 | 324 | 25.0 % | 26.5 | 0.0163 | 0.0367 | +0.0038 |
| 0.937 – 1.235 | 324 | 25.0 % | 29.0 | 0.0481 | 0.0286 | -0.0043 |
| nad 1.504 | 323 | 24.9 % | 32.2 | 0.1314 | 0.0166 | -0.0163 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0522 % | 0.0021 % ± 0.0237 | +2.12 | 97.7 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0522 % | 0.0023 % ± 0.0232 | +2.15 | 98.0 |

Edge je odlisitelny od nahody (2.1 sigma, percentil 97.7).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 366 | 24.8 | 29.8 | 0.0606 | 84 |
| 2022-12 - 2024-03 | 345 | 23.4 | 26.7 | 0.0150 | 23 |
| 2024-03 - 2025-06 | 249 | 16.9 | 29.3 | 0.0512 | 72 |
| 2025-06 - 2026-09 | 336 | 22.8 | 27.4 | 0.0211 | 32 |

Hranice pre úsek veľkosti posledného obdobia: -0.0070 až +0.0784 % (medián 0.0323).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 32. percentile, teda v medziach -0.0070 až +0.0784 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 5** — 2022-06-01T15:30 až 2022-06-07T19:39, spolu +1477.11, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-06-01T15:30 | 2022-06-01T20:31 | +296.59 | +4.73 | `take_profit` |
| 2 | 2022-06-02T15:00 | 2022-06-02T22:07 | +294.77 | +2.24 | `take_profit` |
| 3 | 2022-06-03T20:45 | 2022-06-06T01:26 | +296.02 | +3.25 | `take_profit` |
| 4 | 2022-06-06T15:00 | 2022-06-07T00:24 | +294.66 | +2.42 | `take_profit` |
| 5 | 2022-06-07T15:15 | 2022-06-07T19:39 | +295.07 | +2.84 | `take_profit` |

**Straty za sebou: 17** — 2022-10-31T15:30 až 2022-11-20T17:53, spolu -1785.79.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-10-31T15:30 | 2022-11-02T18:00 | -105.41 | -0.76 | `stop_loss` |
| 2 | 2022-11-02T18:15 | 2022-11-02T18:38 | -103.86 | -1.19 | `stop_loss` |
| 3 | 2022-11-03T17:45 | 2022-11-04T04:29 | -108.38 | -0.51 | `stop_loss` |
| 4 | 2022-11-04T15:30 | 2022-11-05T00:40 | -104.06 | -1.00 | `stop_loss` |
| 5 | 2022-11-05T15:30 | 2022-11-06T01:59 | -107.95 | -0.53 | `stop_loss` |
| 6 | 2022-11-06T15:15 | 2022-11-06T16:02 | -111.96 | -0.37 | `stop_loss` |
| 7 | 2022-11-07T16:00 | 2022-11-07T21:40 | -106.37 | -0.67 | `stop_loss` |
| 8 | 2022-11-08T15:30 | 2022-11-08T16:03 | -102.50 | -1.59 | `stop_loss` |
| 9 | 2022-11-09T15:15 | 2022-11-09T15:36 | -101.63 | -2.08 | `stop_loss` |
| 10 | 2022-11-10T16:30 | 2022-11-10T17:37 | -101.41 | -2.81 | `stop_loss` |
| 11 | 2022-11-11T15:00 | 2022-11-13T21:02 | -101.06 | -3.36 | `stop_loss` |
| 12 | 2022-11-13T21:15 | 2022-11-14T06:59 | -101.82 | -2.14 | `stop_loss` |
| 13 | 2022-11-14T20:00 | 2022-11-14T23:18 | -101.51 | -2.58 | `stop_loss` |
| 14 | 2022-11-15T15:45 | 2022-11-15T18:27 | -102.95 | -1.31 | `stop_loss` |
| 15 | 2022-11-16T16:00 | 2022-11-16T17:37 | -104.18 | -0.93 | `stop_loss` |
| 16 | 2022-11-17T15:30 | 2022-11-20T11:33 | -102.93 | -1.21 | `stop_loss` |
| 17 | 2022-11-20T15:15 | 2022-11-20T17:53 | -117.81 | -0.27 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0329 %**, medián 0.0327 %, 90 % interval 0.0123–0.0544 %
- P(edge > poplatok) = **85.0 %**
- max drawdown: medián 7.6 %, 95. percentil 14.8 %, najhorší 30.8 %
- najdlhšia séria strát: medián 17, 95. percentil 24 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **169** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=304af40c -->

**1. Na čo sa to hodí.** Rozsah otvorenia v zvolenej hodine na BTCUSDT.P 15m. Najrovnomernejší výsledok z ôsmich, ale tenký.

**2. Potenciál.** **Áno, tenký edge.** Zisk v 4 z 5 okien, +2,1 sigma, break-even 0,02–0,07 % — pri poplatku maker 0,02 % to stačí len tesne.

**3. Čo dorobiť.** Cieľ (`riskReward`) a hodina rozsahu sú z MNQ; na BTC je najsilnejšia hodina 14–15 UTC (otvorenie NY), smernica skúša 13–16 aj ranné hodiny.

**4. Čo otestovať.** Smernica na BTC (od ne 15. 11. 2026 po testoch MYM, do ne 22. 11. 18:00) s poplatkom maker 0,02 %; rozhodne odložený rok 9/2025–9/2026 a stabilita po rokoch.

**5. Použiteľné?** **S výhradou** — použiteľné len ak ladenie zdvihne break-even nad 0,05 %.

**6. Čo by som pridal.** Druhé okno v Ázii (0–2 UTC), kde má BTC tiež zvýšenú volatilitu.

<!-- POSUDOK KONIEC -->
