# Základná analytika — Range Breakout (BTC) (`rangebtc`)

Zmerané 2026-11-13 na `BTC/USDT:USDT` 3m, engine `multicharts`, poplatok 0.0200 % na stranu (zadané cez --fee), profil `tradebot/strategies/rangebtc/configs/btcusdt_binance_3m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy rangebtc \
   --profile tradebot/strategies/rangebtc/configs/btcusdt_binance_3m.json \
   --pair BTC/USDT:USDT \
   --timeframe 3m \
   --fee 0.0002 \
   --wallet 60000
```

## V čom je dobrá

- 1278 obchodov spolu — na štatistiku dosť
- drawdown drží: 95. percentil 23.8 %
- odlíšiteľná od náhody (+2.3 sigma proti náhodnému vstupu)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- zisková v 2 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20250904-20260904 v strate)
- break-even 0.0173 % je pod poplatkom 0.0200 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 37 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- najhoršia skupina 'do 2.5 R' vlastnosti 'Plánovaný RR': 1210 obchodov (94.7 %), bez nej by break-even bol o +0.0202 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 260 | -0.35 | 0.0177 | 6.3 | 30.4 | +4/-15 | `20261113-172218-ecc76f` |
| 20221001-20231001 | 259 | -1.56 | 0.0154 | 5.3 | 32.0 | +4/-15 | `20261113-172224-88e1ed` |
| 20231001-20241001 | 259 | +1.47 | 0.0268 | 3.7 | 32.4 | +4/-12 | `20261113-172230-8bcbcc` |
| 20240904-20250904 | 259 | +0.51 | 0.0221 | 4.1 | 32.0 | +5/-16 | `20261113-172236-55315d` |
| 20250904-20260904 | 260 | -2.61 | 0.0090 | 7.0 | 30.0 | +3/-12 | `20261113-172242-eb5dd4` |

Zisková v **2 z 5** okien, obchodov spolu 1278, break-even celkom 0.0173 %. Okná sa prekrývajú, 19 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+1.34 ATR za 5 barov)
- medián držania 49 barov grafu
- winrate 31.3 %, payoff 2.152
- 0.71 obchodov za deň
- šikmosť výnosov +1.549

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 68.7 %, `take_profit` 31.3 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'do 2.5 R' vlastnosti 'Plánovaný RR': 1210 obchodov (94.7 %), break-even 0.0153 % oproti 0.0173 % celku. Bez nej by break-even bol 0.0375 % (+0.0202). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**Plánovaný RR**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 2.5 R | 1210 | 94.7 % | 30.9 | 0.0153 | 0.0375 | +0.0202 |
| nad 2.5 R | 68 | 5.3 % | 38.2 | 0.0375 | 0.0153 | -0.0020 |

**Smer**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| short | 671 | 52.5 % | 29.5 | 0.0059 | 0.0302 | +0.0129 |
| long | 607 | 47.5 % | 33.3 | 0.0302 | 0.0059 | -0.0114 |

**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.0571 – 0.1172 | 320 | 25.0 % | 28.1 | -0.0025 | 0.0251 | +0.0078 |
| do 0.0571 | 320 | 25.0 % | 29.4 | 0.0048 | 0.0219 | +0.0046 |
| 0.1172 – 0.2025 | 319 | 25.0 % | 32.9 | 0.0276 | 0.0139 | -0.0034 |
| nad 0.2025 | 319 | 25.0 % | 34.8 | 0.0496 | 0.0093 | -0.0080 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0253 % | -0.0001 % ± 0.0110 | +2.31 | 98.8 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0253 % | 0.0002 % ± 0.0114 | +2.19 | 98.3 |

Edge je odlisitelny od nahody (2.3 sigma, percentil 98.8).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 320 | 21.7 | 30.6 | 0.0172 | 50 |
| 2022-12 - 2024-03 | 317 | 21.5 | 31.9 | 0.0158 | 50 |
| 2024-03 - 2025-06 | 322 | 21.8 | 31.7 | 0.0226 | 64 |
| 2025-06 - 2026-09 | 319 | 21.6 | 31.0 | 0.0148 | 44 |

Hranice pre úsek veľkosti posledného obdobia: -0.0095 až +0.0458 % (medián 0.0173).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 44. percentile, teda v medziach -0.0095 až +0.0458 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 5** — 2024-12-02T05:51 až 2024-12-06T14:27, spolu +1205.05.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-12-02T05:51 | 2024-12-02T08:19 | +240.67 | +1.12 | `take_profit` |
| 2 | 2024-12-03T06:57 | 2024-12-03T10:56 | +240.06 | +0.99 | `take_profit` |
| 3 | 2024-12-04T05:12 | 2024-12-04T09:15 | +237.54 | +0.81 | `take_profit` |
| 4 | 2024-12-05T05:45 | 2024-12-05T20:18 | +244.62 | +3.92 | `take_profit` |
| 5 | 2024-12-06T05:09 | 2024-12-06T14:27 | +242.15 | +1.47 | `take_profit` |

**Straty za sebou: 16** — 2024-10-14T05:15 až 2024-11-04T13:10, spolu -1774.52.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-10-14T05:15 | 2024-10-14T07:49 | -105.10 | -0.82 | `stop_loss` |
| 2 | 2024-10-15T04:27 | 2024-10-15T07:13 | -114.07 | -0.32 | `stop_loss` |
| 3 | 2024-10-16T04:06 | 2024-10-16T10:09 | -105.80 | -0.70 | `stop_loss` |
| 4 | 2024-10-17T04:51 | 2024-10-17T15:36 | -107.81 | -0.54 | `stop_loss` |
| 5 | 2024-10-18T04:18 | 2024-10-18T06:15 | -105.84 | -0.70 | `stop_loss` |
| 6 | 2024-10-21T04:57 | 2024-10-21T06:58 | -112.99 | -0.34 | `stop_loss` |
| 7 | 2024-10-22T04:21 | 2024-10-22T04:29 | -115.84 | -0.29 | `stop_loss` |
| 8 | 2024-10-23T04:33 | 2024-10-23T04:39 | -117.09 | -0.27 | `stop_loss` |
| 9 | 2024-10-24T04:54 | 2024-10-24T06:54 | -113.85 | -0.33 | `stop_loss` |
| 10 | 2024-10-25T05:45 | 2024-10-25T06:01 | -114.49 | -0.31 | `stop_loss` |
| 11 | 2024-10-28T04:42 | 2024-10-28T05:48 | -115.79 | -0.29 | `stop_loss` |
| 12 | 2024-10-29T04:15 | 2024-10-29T11:32 | -108.49 | -0.49 | `stop_loss` |
| 13 | 2024-10-30T04:15 | 2024-10-30T06:12 | -107.85 | -0.54 | `stop_loss` |
| 14 | 2024-10-31T04:15 | 2024-10-31T10:46 | -111.47 | -0.39 | `stop_loss` |
| 15 | 2024-11-01T04:48 | 2024-11-01T06:58 | -106.61 | -0.62 | `stop_loss` |
| 16 | 2024-11-04T05:30 | 2024-11-04T13:10 | -111.43 | -0.39 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0173 %**, medián 0.0174 %, 90 % interval 0.0036–0.0314 %
- P(edge > poplatok) = **37.2 %**
- max drawdown: medián 12.1 %, 95. percentil 23.8 %, najhorší 39.8 %
- najdlhšia séria strát: medián 18, 95. percentil 25 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **91** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=98347baa -->

**1. Na čo sa to hodí.** Prieraz konsolidácie na BTCUSDT.P 3m. Veľa obchodov (~260/rok) s malým pohybom.

**2. Potenciál.** **Hrubý edge áno, čistý nie.** Proti náhode +2,3 sigma, ale break-even len 0,01–0,03 % — poplatok maker 0,02 % zje skoro všetko (zisk len v 2 z 5 okien).

**3. Čo dorobiť.** Potrebuje menej a väčších obchodov: vyšší TF, širšie rozsahy (`minWidthAtr`), väčší cieľ (`rrRatio`/`measuredMult`).

**4. Čo otestovať.** Smernica na BTC (od ne 15. 11. 2026 po testoch MYM, do ne 22. 11. 18:00) s poplatkom maker 0,02 %; rozhodne odložený rok 9/2025–9/2026 a stabilita po rokoch.

**5. Použiteľné?** **Takto nie**; použiteľné len ak ladenie posunie break-even nad 0,05 %.

**6. Čo by som pridal.** Filter otvorenia NY (`useTradeWindow` 9–12 NY).

<!-- POSUDOK KONIEC -->
