# Základná analytika — SWEEPING ENGULF 1.0 (6E) (`sweepengulfeur`)

Zmerané 2026-11-15 na `6E/USD` 4h, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/sweepengulfeur/configs/6e_databento_4h.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy sweepengulfeur \
   --profile tradebot/strategies/sweepengulfeur/configs/6e_databento_4h.json \
   --pair 6E/USD \
   --timeframe 4h \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- break-even 0.0363 % je nad poplatkom 0.0018 % (rezerva +0.0345 bodu)
- drawdown drží: 95. percentil 23.6 %
- edge drží aj v poslednom období (2025-06 - 2026-09 na 25. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- zisková v 3 z 5 referenčných okien (20211001-20221001, 20231001-20241001 v strate)
- edge nad poplatkom len v 92 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- proti náhode len +1.9 sigma: náznak, nie dôkaz
- najhoršia skupina 'NFP' vlastnosti 'Makro udalosť v ten deň': 8 obchodov (4.2 %), bez nej by break-even bol o +0.1068 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 40 | -4.98 | -0.0261 | 9.9 | 27.5 | +5/-9 | `20261115-094800-b79514` |
| 20221001-20231001 | 35 | +23.63 | 0.1522 | 3.3 | 40.0 | +3/-4 | `20261115-094804-0b05cd` |
| 20231001-20241001 | 41 | -0.74 | -0.0022 | 7.3 | 29.3 | +3/-6 | `20261115-094807-68a53b` |
| 20240904-20250904 | 39 | +3.73 | 0.0227 | 6.3 | 35.9 | +4/-4 | `20261115-094810-f9f1b7` |
| 20250904-20260904 | 41 | +6.82 | 0.0359 | 3.6 | 41.5 | +2/-4 | `20261115-094813-3897b1` |

Zisková v **3 z 5** okien, obchodov spolu 192, break-even celkom 0.0363 %. Okná sa prekrývajú, 4 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+0.91 ATR za 5 barov)
- medián držania 4.3 barov grafu
- winrate 35.42 %, payoff 2.394
- 0.11 obchodov za deň
- šikmosť výnosov +1.397

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 64.1 %, `take_profit` 35.4 %, `force_exit` 0.5 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'NFP' vlastnosti 'Makro udalosť v ten deň': 8 obchodov (4.2 %), break-even 0.0029 % oproti 0.0363 % celku. Bez nej by break-even bol 0.0377 % (+0.1068). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| NFP | 8 | 4.2 % | 37.5 | 0.0029 | 0.0377 | +0.0014 |
| žiadna | 164 | 85.4 % | 33.5 | 0.0179 | 0.1431 | +0.1068 |
| CPI | 13 | 6.8 % | 53.9 | 0.2142 | 0.0232 | -0.0131 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| pred vyhlásením | 12 | 6.2 % | 25.0 | -0.0520 | 0.0422 | +0.0059 |
| bez udalosti | 164 | 85.4 % | 33.5 | 0.0179 | 0.1431 | +0.1068 |
| po vyhlásení | 16 | 8.3 % | 62.5 | 0.2914 | 0.0131 | -0.0232 |

**Volatilita voči normálu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.938 | 49 | 25.5 % | 28.6 | -0.0263 | 0.0578 | +0.0215 |
| 1.007 – 1.1 | 47 | 24.5 % | 38.3 | -0.0048 | 0.0497 | +0.0134 |
| 0.938 – 1.007 | 49 | 25.5 % | 30.6 | 0.0531 | 0.0305 | -0.0058 |
| nad 1.1 | 47 | 24.5 % | 44.7 | 0.1261 | 0.0074 | -0.0289 |

Parametre, ktorými sa dá s tým niečo spraviť: `rrRatio`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0363 % | 0.0001 % ± 0.0190 | +1.91 | 96.7 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0363 % | -0.0014 % ± 0.0184 | +2.04 | 97.4 |

Naznak, ale nie dokaz (1.9 sigma, percentil 96.7). Take rozdiely nahoda robi bezne.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 47 | 3.2 | 27.7 | 0.0165 | 34 |
| 2022-12 - 2024-03 | 47 | 3.2 | 42.5 | 0.1004 | 88 |
| 2024-03 - 2025-06 | 48 | 3.3 | 35.4 | 0.0300 | 45 |
| 2025-06 - 2026-09 | 50 | 3.4 | 36.0 | 0.0027 | 25 |

Hranice pre úsek veľkosti posledného obdobia: -0.0396 až +0.1193 % (medián 0.0348).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 25. percentile, teda v medziach -0.0396 až +0.1193 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 5** — 2022-03-18T04:00 až 2022-05-18T19:19, spolu +5095.02.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-03-18T04:00 | 2022-03-18T13:08 | +870.14 | +0.63 | `take_profit` |
| 2 | 2022-03-21T12:00 | 2022-03-28T01:51 | +982.66 | +0.71 | `take_profit` |
| 3 | 2022-04-22T08:00 | 2022-04-25T06:33 | +1089.02 | +0.80 | `take_profit` |
| 4 | 2022-04-25T16:00 | 2022-04-27T07:29 | +1389.07 | +1.04 | `take_profit` |
| 5 | 2022-05-18T04:00 | 2022-05-18T19:19 | +764.14 | +0.58 | `take_profit` |

**Straty za sebou: 9** — 2021-10-04T04:00 až 2022-01-10T14:14, spolu -4788.83.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2021-10-04T04:00 | 2021-10-04T08:03 | -311.35 | -0.21 | `stop_loss` |
| 2 | 2021-10-15T12:00 | 2021-10-18T16:24 | -205.10 | -0.14 | `stop_loss` |
| 3 | 2021-10-20T08:00 | 2021-10-20T16:32 | -348.86 | -0.24 | `stop_loss` |
| 4 | 2021-11-17T04:00 | 2021-11-17T12:01 | -479.96 | -0.34 | `stop_loss` |
| 5 | 2021-11-24T12:00 | 2021-11-26T08:21 | -479.93 | -0.34 | `stop_loss` |
| 6 | 2021-11-30T16:00 | 2021-12-16T13:58 | -1554.97 | -1.10 | `stop_loss` |
| 7 | 2021-12-22T04:00 | 2021-12-22T10:23 | -229.96 | -0.16 | `stop_loss` |
| 8 | 2021-12-28T16:00 | 2021-12-29T14:31 | -479.97 | -0.34 | `stop_loss` |
| 9 | 2022-01-07T16:00 | 2022-01-10T14:14 | -698.72 | -0.49 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0363 %**, medián 0.0358 %, 90 % interval -0.0039–0.0786 %
- P(edge > poplatok) = **92.1 %**
- max drawdown: medián 11.5 %, 95. percentil 23.6 %, najhorší 58.8 %
- najdlhšia séria strát: medián 9, 95. percentil 13 obchodov
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
<!-- POSUDOK cisla=14e9f1fb -->

**1. Na čo sa to hodí.** SWEEPING ENGULF na 6E 4h — sweep predošlej sviečky a pohltenie, filter EMA 200. Čísla sú z **neladeného východiska** (predloha z MNQ, tickové prahy ×0,12); ladenie pôjde len na 2016–2021/9, tieto okná sú preň čisté overenie a nesmú ho ovplyvniť.

**2. Potenciál.** **Stredný.** Break-even 0,036 % (20× poplatok), zisk v 3 z 5 okien, +1,9 sigma — ale len ~40 obchodov za rok.

**3. Čo dorobiť.** Nižší TF (15m–1h), aby bolo ≥ 75 obchodov za rok; smernica skúša `_tf` 15–240.

**4. Čo otestovať.** Smernica EUR (22.–29. 11. 2026); rozhodne, či edge prežije na 15m–1h.

**5. Použiteľné?** **Zatiaľ nie** — pre málo obchodov.

**6. Čo by som pridal.** Sweep len v živých oknách (London, NY ráno).

<!-- POSUDOK KONIEC -->
