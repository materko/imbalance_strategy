# Základná analytika — SWEEPING ENGULF 1.0 (BTC) (`sweepengulfbtc`)

Zmerané 2026-11-13 na `BTC/USDT:USDT` 4h, engine `multicharts`, poplatok 0.0200 % na stranu (zadané cez --fee), profil `tradebot/strategies/sweepengulfbtc/configs/btcusdt_binance_4h.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy sweepengulfbtc \
   --profile tradebot/strategies/sweepengulfbtc/configs/btcusdt_binance_4h.json \
   --pair BTC/USDT:USDT \
   --timeframe 4h \
   --fee 0.0002 \
   --wallet 60000
```

## V čom je dobrá

- 207 obchodov spolu — na štatistiku dosť
- break-even 0.0699 % je nad poplatkom 0.0200 % (rezerva +0.0499 bodu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 16. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- zisková v 2 z 5 referenčných okien (20221001-20231001, 20240904-20250904, 20250904-20260904 v strate)
- edge nad poplatkom len v 67 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 79.8 % (namerané 35.9 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 1.5 % pri riziku, s akým beh bežal
- proti náhode len +0.6 sigma: náznak, nie dôkaz
- najhoršia skupina '0.898 – 0.989' vlastnosti 'Volatilita voči normálu': 51 obchodov (24.6 %), bez nej by break-even bol o +0.1127 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 31 | +19.48 | 0.5413 | 8.9 | 38.7 | +4/-8 | `20261113-172329-5195ab` |
| 20221001-20231001 | 43 | -9.03 | -0.2347 | 10.5 | 27.9 | +2/-9 | `20261113-172332-2f87d3` |
| 20231001-20241001 | 43 | +23.94 | 0.3306 | 9.5 | 44.2 | +4/-5 | `20261113-172335-9041ed` |
| 20240904-20250904 | 50 | -22.27 | -0.1251 | 32.8 | 30.0 | +3/-7 | `20261113-172341-8878fa` |
| 20250904-20260904 | 45 | -3.99 | -0.0103 | 30.3 | 31.1 | +4/-10 | `20261113-172344-adb881` |

Zisková v **2 z 5** okien, obchodov spolu 207, break-even celkom 0.0699 %. Okná sa prekrývajú, 5 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+0.85 ATR za 5 barov)
- medián držania 5.1 barov grafu
- winrate 34.78 %, payoff 2.023
- 0.12 obchodov za deň
- šikmosť výnosov +0.761

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 65.2 %, `take_profit` 34.3 %, `force_exit` 0.5 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je '0.898 – 0.989' vlastnosti 'Volatilita voči normálu': 51 obchodov (24.6 %), break-even -0.2745 % oproti 0.0699 % celku. Bez nej by break-even bol 0.1826 % (+0.1127). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Volatilita voči normálu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.898 – 0.989 | 51 | 24.6 % | 29.4 | -0.2745 | 0.1826 | +0.1127 |
| do 0.898 | 53 | 25.6 % | 35.9 | 0.0571 | 0.0740 | +0.0041 |
| 0.989 – 1.095 | 52 | 25.1 % | 30.8 | 0.1031 | 0.0577 | -0.0122 |
| nad 1.095 | 51 | 24.6 % | 43.1 | 0.3947 | -0.0347 | -0.1046 |

**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.1264 – 0.2436 | 52 | 25.1 % | 30.8 | -0.1918 | 0.1661 | +0.0962 |
| nad 0.2436 | 51 | 24.6 % | 37.2 | 0.0114 | 0.0878 | +0.0179 |
| 0.0608 – 0.1264 | 52 | 25.1 % | 30.8 | 0.0174 | 0.0875 | +0.0176 |
| do 0.0608 | 52 | 25.1 % | 40.4 | 0.4648 | -0.0591 | -0.1290 |

**Kalendárny mesiac**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 12 | 20 | 9.7 % | 10.0 | -0.6410 | 0.1427 | +0.0728 |
| 02 | 15 | 7.2 % | 26.7 | -0.4913 | 0.1094 | +0.0395 |
| 09 | 13 | 6.3 % | 15.4 | -0.4840 | 0.1127 | +0.0428 |
| 07 | 22 | 10.6 % | 22.7 | -0.2053 | 0.0962 | +0.0263 |
| … | | | | | | |
| 01 | 15 | 7.2 % | 53.3 | 0.2097 | 0.0603 | -0.0096 |
| 06 | 23 | 11.1 % | 47.8 | 0.2658 | 0.0459 | -0.0240 |
| 03 | 15 | 7.2 % | 33.3 | 0.3539 | 0.0479 | -0.0220 |
| 11 | 15 | 7.2 % | 60.0 | 1.3343 | -0.0524 | -0.1223 |

Parametre, ktorými sa dá s tým niečo spraviť: `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0699 % | 0.0095 % ± 0.1064 | +0.57 | 71.1 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0699 % | 0.0079 % ± 0.1024 | +0.61 | 73.9 |

Neodlisitelne od nahody (+0.6 sigma, percentil 71.1). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2023-01 | 39 | 2.7 | 33.3 | 0.4515 | 90 |
| 2023-01 - 2024-03 | 51 | 3.5 | 37.2 | -0.0430 | 29 |
| 2024-03 - 2025-06 | 59 | 4.0 | 39.0 | 0.2469 | 77 |
| 2025-06 - 2026-09 | 58 | 4.0 | 29.3 | -0.1362 | 16 |

Hranice pre úsek veľkosti posledného obdobia: -0.2777 až +0.4441 % (medián 0.0712).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 16. percentile, teda v medziach -0.2777 až +0.4441 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 4** — 2022-03-22T04:00 až 2022-04-11T20:06, spolu +7401.86, rovnako dlhých sérií 3.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-03-22T04:00 | 2022-03-25T13:48 | +2738.56 | +6.48 | `take_profit` |
| 2 | 2022-03-27T16:00 | 2022-03-27T20:37 | +822.10 | +1.83 | `take_profit` |
| 3 | 2022-04-08T12:00 | 2022-04-10T22:45 | +1339.66 | +3.09 | `take_profit` |
| 4 | 2022-04-11T00:00 | 2022-04-11T20:06 | +2501.55 | +5.94 | `take_profit` |

**Straty za sebou: 10** — 2026-02-07T08:00 až 2026-05-13T12:22, spolu -15338.77.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-02-07T08:00 | 2026-02-08T23:05 | -3667.45 | -5.39 | `stop_loss` |
| 2 | 2026-02-16T16:00 | 2026-03-04T08:46 | -2632.92 | -3.90 | `stop_loss` |
| 3 | 2026-03-08T04:00 | 2026-03-08T08:44 | -510.99 | -0.76 | `stop_loss` |
| 4 | 2026-03-09T00:00 | 2026-03-09T03:15 | -1588.79 | -2.41 | `stop_loss` |
| 5 | 2026-03-24T08:00 | 2026-03-24T13:52 | -1207.97 | -1.70 | `stop_loss` |
| 6 | 2026-04-14T16:00 | 2026-04-14T17:35 | -1064.00 | -1.41 | `stop_loss` |
| 7 | 2026-04-24T12:00 | 2026-04-24T18:17 | -870.21 | -1.11 | `stop_loss` |
| 8 | 2026-05-04T04:00 | 2026-05-04T10:24 | -2075.00 | -2.58 | `stop_loss` |
| 9 | 2026-05-07T08:00 | 2026-05-07T10:27 | -836.63 | -1.03 | `stop_loss` |
| 10 | 2026-05-13T04:00 | 2026-05-13T12:22 | -884.82 | -1.09 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0699 %**, medián 0.0716 %, 90 % interval -0.1190–0.2621 %
- P(edge > poplatok) = **67.3 %**
- max drawdown: medián 35.9 %, 95. percentil 79.8 %, najhorší 100.0 %
- najdlhšia séria strát: medián 11, 95. percentil 15 obchodov
- pravdepodobnosť ruiny účtu: 1.5 %

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
<!-- POSUDOK cisla=403c2a7c -->

**1. Na čo sa to hodí.** Sweep + pohlcujúca sviečka na BTCUSDT.P 4h. ~40 obchodov za rok, veľký pohyb (~2,7 %).

**2. Potenciál.** **Nie z východiska.** Zisk len v 2 z 5 okien, proti náhode +0,6 sigma — od náhody nerozlíšiteľné.

**3. Čo dorobiť.** Na 4h chýba filter režimu; stop a cieľ z MNQ.

**4. Čo otestovať.** Smernica na BTC (od ne 15. 11. 2026 po testoch MYM, do ne 22. 11. 18:00) s poplatkom maker 0,02 %; rozhodne odložený rok 9/2025–9/2026 a stabilita po rokoch. Smernica skúša aj 15m–1h, kde je obchodov viac.

**5. Použiteľné?** **O ničom**, kým ladenie neukáže stabilitu.

**6. Čo by som pridal.** Sweep denného high/low namiesto predošlej sviečky.

<!-- POSUDOK KONIEC -->
