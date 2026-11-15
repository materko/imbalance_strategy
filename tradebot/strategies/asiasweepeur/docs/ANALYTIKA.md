# Základná analytika — ASIA SWEEP 1.0 (6E) (`asiasweepeur`)

Zmerané 2026-11-15 na `6E/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/asiasweepeur/configs/6e_databento_5m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy asiasweepeur \
   --profile tradebot/strategies/asiasweepeur/configs/6e_databento_5m.json \
   --pair 6E/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 820 obchodov spolu — na štatistiku dosť
- break-even 0.0058 % je nad poplatkom 0.0018 % (rezerva +0.0040 bodu)
- drawdown drží: 95. percentil 12.0 %
- odlíšiteľná od náhody (+3.3 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 17. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- zisková v 4 z 5 referenčných okien (20250904-20260904 v strate)
- edge nad poplatkom len v 93 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- najhoršia skupina 'proti trendu' vlastnosti 'S trendom, alebo proti': 668 obchodov (81.5 %), bez nej by break-even bol o +0.0113 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 169 | +1.65 | 0.0039 | 5.2 | 34.3 | +4/-8 | `20261115-094733-84137d` |
| 20221001-20231001 | 182 | +4.95 | 0.0078 | 3.9 | 35.2 | +4/-11 | `20261115-094739-1d7800` |
| 20231001-20241001 | 169 | +5.04 | 0.0083 | 1.5 | 40.2 | +5/-7 | `20261115-094742-72e2d1` |
| 20240904-20250904 | 148 | +4.02 | 0.0077 | 3.9 | 35.8 | +3/-9 | `20261115-094745-cc1784` |
| 20250904-20260904 | 165 | -1.54 | -0.0002 | 5.6 | 31.5 | +4/-16 | `20261115-094748-c2846c` |

Zisková v **4 z 5** okien, obchodov spolu 820, break-even celkom 0.0058 %. Okná sa prekrývajú, 13 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+0.83 ATR za 5 barov)
- medián držania 8.7 barov grafu
- winrate 35.61 %, payoff 2.069
- 0.46 obchodov za deň
- šikmosť výnosov +1.313

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 64.4 %, `take_profit` 35.6 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'proti trendu' vlastnosti 'S trendom, alebo proti': 668 obchodov (81.5 %), break-even 0.0032 % oproti 0.0058 % celku. Bez nej by break-even bol 0.0171 % (+0.0113). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| proti trendu | 668 | 81.5 % | 34.9 | 0.0032 | 0.0171 | +0.0113 |
| s trendom | 152 | 18.5 % | 38.8 | 0.0171 | 0.0032 | -0.0026 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.2708 – 0.425 | 205 | 25.0 % | 31.2 | -0.0024 | 0.0085 | +0.0027 |
| do 0.2708 | 206 | 25.1 % | 34.0 | 0.0001 | 0.0077 | +0.0019 |
| 0.425 – 0.6154 | 205 | 25.0 % | 36.1 | 0.0044 | 0.0062 | +0.0004 |
| nad 0.6154 | 204 | 24.9 % | 41.2 | 0.0212 | 0.0007 | -0.0051 |

**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 0.1408 | 204 | 24.9 % | 30.9 | -0.0009 | 0.0080 | +0.0022 |
| 0.0811 – 0.1408 | 203 | 24.8 % | 35.0 | 0.0044 | 0.0062 | +0.0004 |
| 0.0359 – 0.0811 | 207 | 25.2 % | 38.2 | 0.0053 | 0.0059 | +0.0001 |
| do 0.0359 | 206 | 25.1 % | 38.4 | 0.0142 | 0.0029 | -0.0029 |

Parametre, ktorými sa dá s tým niečo spraviť: `rrRatio`, `sweepStartH`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0058 % | -0.0001 % ± 0.0018 | +3.31 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0058 % | -0.0000 % ± 0.0021 | +2.79 | 99.5 |

Edge je odlisitelny od nahody (3.3 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 209 | 14.2 | 34.9 | 0.0051 | 46 |
| 2022-12 - 2024-03 | 218 | 14.8 | 37.2 | 0.0080 | 68 |
| 2024-03 - 2025-06 | 194 | 13.2 | 38.1 | 0.0099 | 78 |
| 2025-06 - 2026-09 | 199 | 13.5 | 32.2 | 0.0003 | 17 |

Hranice pre úsek veľkosti posledného obdobia: -0.0027 až +0.0146 % (medián 0.0056).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 17. percentile, teda v medziach -0.0027 až +0.0146 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 5** — 2023-09-26T07:25 až 2023-10-03T07:01, spolu +951.78, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-09-26T07:25 | 2023-09-26T08:27 | +245.34 | +0.18 | `take_profit` |
| 2 | 2023-09-28T07:10 | 2023-09-28T09:52 | +426.62 | +0.32 | `take_profit` |
| 3 | 2023-09-29T06:45 | 2023-09-29T06:45 | +82.84 | +0.06 | `take_profit` |
| 4 | 2023-10-02T06:10 | 2023-10-02T06:33 | +89.10 | +0.07 | `take_profit` |
| 5 | 2023-10-03T06:05 | 2023-10-03T07:01 | +107.89 | +0.08 | `take_profit` |

**Straty za sebou: 16** — 2026-05-12T07:25 až 2026-06-11T10:03, spolu -1562.94.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-05-12T07:25 | 2026-05-12T07:45 | -98.91 | -0.07 | `stop_loss` |
| 2 | 2026-05-13T06:05 | 2026-05-13T06:08 | -48.91 | -0.03 | `stop_loss` |
| 3 | 2026-05-14T06:30 | 2026-05-14T07:59 | -92.64 | -0.06 | `stop_loss` |
| 4 | 2026-05-19T06:25 | 2026-05-19T06:46 | -73.86 | -0.05 | `stop_loss` |
| 5 | 2026-05-20T07:50 | 2026-05-20T07:53 | -30.09 | -0.02 | `stop_loss` |
| 6 | 2026-05-21T08:15 | 2026-05-21T12:27 | -417.60 | -0.29 | `stop_loss` |
| 7 | 2026-05-22T06:20 | 2026-05-22T06:39 | -73.85 | -0.05 | `stop_loss` |
| 8 | 2026-05-25T08:15 | 2026-05-26T01:41 | -130.11 | -0.09 | `stop_loss` |
| 9 | 2026-05-26T06:30 | 2026-05-26T07:05 | -86.36 | -0.06 | `stop_loss` |
| 10 | 2026-05-29T08:25 | 2026-05-29T08:47 | -48.86 | -0.03 | `stop_loss` |
| 11 | 2026-06-01T06:30 | 2026-06-01T06:51 | -73.87 | -0.05 | `stop_loss` |
| 12 | 2026-06-03T06:15 | 2026-06-03T06:23 | -48.85 | -0.03 | `stop_loss` |
| 13 | 2026-06-04T06:25 | 2026-06-04T06:35 | -73.85 | -0.05 | `stop_loss` |
| 14 | 2026-06-08T08:45 | 2026-06-08T08:52 | -73.80 | -0.05 | `stop_loss` |
| 15 | 2026-06-10T06:55 | 2026-06-10T07:22 | -98.82 | -0.07 | `stop_loss` |
| 16 | 2026-06-11T09:20 | 2026-06-11T10:03 | -92.56 | -0.06 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0058 %**, medián 0.0058 %, 90 % interval 0.0013–0.0103 %
- P(edge > poplatok) = **93.3 %**
- max drawdown: medián 6.2 %, 95. percentil 12.0 %, najhorší 32.0 %
- najdlhšia séria strát: medián 13, 95. percentil 19 obchodov
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
<!-- POSUDOK cisla=68529957 -->

**1. Na čo sa to hodí.** Asia Sweep na 6E 5m — London vybije ázijský rozsah a vstupuje sa späť do neho. Na EUR je to typický vzorec. Čísla sú z **neladeného východiska** (predloha z MNQ, tickové prahy ×0,12); ladenie pôjde len na 2016–2021/9, tieto okná sú preň čisté overenie a nesmú ho ovplyvniť.

**2. Potenciál.** **Veľký.** Už neladená: zisk v 4 z 5 okien, +3,3 sigma, break-even 0,0058 % (3× poplatok), ~165 obchodov za rok. Najlepšie východisko z EUR kópií.

**3. Čo dorobiť.** 81 % obchodov ide proti trendu a tie kazia výsledok (bez nich break-even o +0,011 lepší) — skúsiť filter trendu.

**4. Čo otestovať.** Smernica EUR (22.–29. 11. 2026) s filtrom trendu (`trendFilter` with), cieľom do stredu / opačnej strany rangu; posledné okno 25/26 je v strate — sledovať.

**5. Použiteľné?** **Sľubné** — prvý kandidát na EUR, rozhodne smernica.

**6. Čo by som pridal.** Filter šírky ázijského rozsahu (úzky rozsah = čistejší sweep).

<!-- POSUDOK KONIEC -->
