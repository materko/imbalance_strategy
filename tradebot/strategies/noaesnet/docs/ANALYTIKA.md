# Základná analytika — NOA 1.0 ES (C# jadro) (`noaesnet`)

Zmerané 2026-11-11 na `ES/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee).

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy noaesnet \
   --pair ES/USD \
   --timeframe 5m \
   --fee 1.755e-05
```

## V čom je dobrá

- 1166 obchodov spolu — na štatistiku dosť
- break-even 0.0086 % je nad poplatkom 0.0018 % (rezerva +0.0068 bodu)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- zisková v 4 z 5 referenčných okien (20250904-20260904 v strate)
- edge nad poplatkom len v 88 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 100.0 % (namerané 97.3 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 48.1 % pri riziku, s akým beh bežal
- proti náhode len +1.3 sigma: náznak, nie dôkaz
- SLABNE: posledné obdobie (2025-06 - 2026-09) má break-even -0.0121 %, pod dolnou hranicou -0.0102 % — úsek tejto dĺžky by taký zlý vyšiel len v 3 % prípadov, keby sa edge nemenil. Skôr než to vypneš: pozri `tester.regime`, či to nie je len režimom trhu.
- 99 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 's trendom' vlastnosti 'S trendom, alebo proti': 1129 obchodov (96.8 %), bez nej by break-even bol o +0.0485 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 259 | +141.62 | 0.0146 | 117.4 | 35.9 | +6/-11 | `20261111-175707-4fcb4d` |
| 20221001-20231001 | 214 | +337.70 | 0.0399 | 12.3 | 45.8 | +5/-6 | `20261111-175713-fd685a` |
| 20231001-20241001 | 243 | +86.01 | 0.0088 | 39.3 | 41.6 | +6/-7 | `20261111-175725-137e05` |
| 20240904-20250904 | 226 | +41.47 | 0.0048 | 56.0 | 37.6 | +5/-10 | `20261111-175734-0ffa1b` |
| 20250904-20260904 | 236 | -174.00 | -0.0087 | 175.1 | 39.0 | +5/-11 | `20261111-175740-45b959` |

Zisková v **4 z 5** okien, obchodov spolu 1166, break-even celkom 0.0086 %. Okná sa prekrývajú, 12 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+1.33 ATR za 5 barov)
- medián držania 11 barov grafu
- winrate 39.88 %, payoff 1.67
- 0.65 obchodov za deň
- šikmosť výnosov +1.93

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `session_end` 99 %, `stop_loss` 1 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 's trendom' vlastnosti 'S trendom, alebo proti': 1129 obchodov (96.8 %), break-even 0.007 % oproti 0.0086 % celku. Bez nej by break-even bol 0.0571 % (+0.0485). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 1129 | 96.8 % | 39.5 | 0.0070 | 0.0571 | +0.0485 |
| proti trendu | 37 | 3.2 % | 51.4 | 0.0571 | 0.0070 | -0.0016 |

**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| žiadna | 1008 | 86.4 % | 39.1 | 0.0057 | 0.0276 | +0.0190 |
| NFP | 66 | 5.7 % | 45.5 | 0.0173 | 0.0081 | -0.0005 |
| CPI | 49 | 4.2 % | 42.9 | 0.0302 | 0.0077 | -0.0009 |
| FOMC | 42 | 3.6 % | 45.2 | 0.0410 | 0.0074 | -0.0012 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| pred vyhlásením | 17 | 1.5 % | 35.3 | -0.0102 | 0.0089 | +0.0003 |
| bez udalosti | 1008 | 86.4 % | 39.1 | 0.0057 | 0.0276 | +0.0190 |
| po vyhlásení | 141 | 12.1 % | 46.1 | 0.0321 | 0.0054 | -0.0032 |

Parametre, ktorými sa dá s tým niečo spraviť: `hardStopPct`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0086 % | 0.0009 % ± 0.0061 | +1.26 | 89.7 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0086 % | 0.0017 % ± 0.0070 | +0.98 | 84.1 |

Naznak, ale nie dokaz (1.3 sigma, percentil 89.7). Take rozdiely nahoda robi bezne.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 310 | 21.0 | 37.4 | 0.0224 | 89 |
| 2022-12 - 2024-03 | 288 | 19.5 | 44.8 | 0.0226 | 88 |
| 2024-03 - 2025-06 | 278 | 18.9 | 40.6 | 0.0123 | 64 |
| 2025-06 - 2026-09 | 290 | 19.7 | 36.9 | -0.0121 | 3 |

Hranice pre úsek veľkosti posledného obdobia: -0.0102 až +0.0288 % (medián 0.0086).

**SLABNE** — posledné obdobie (2025-06 - 2026-09) má break-even -0.0121 %, pod dolnou hranicou -0.0102 % — úsek tejto dĺžky by taký zlý vyšiel len v 3 % prípadov, keby sa edge nemenil. Skôr než to vypneš: pozri `tester.regime`, či to nie je len režimom trhu.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 6** — 2022-04-13T14:30 až 2022-04-22T19:55, spolu +11278.65, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-04-13T14:30 | 2022-04-13T19:55 | +2042.24 | +0.93 | `session_end` |
| 2 | 2022-04-14T14:00 | 2022-04-14T15:25 | +42.23 | +0.02 | `session_end` |
| 3 | 2022-04-14T16:00 | 2022-04-14T19:55 | +1429.78 | +0.65 | `session_end` |
| 4 | 2022-04-19T14:00 | 2022-04-19T19:55 | +1817.21 | +0.82 | `session_end` |
| 5 | 2022-04-21T18:00 | 2022-04-21T19:55 | +1854.77 | +0.84 | `session_end` |
| 6 | 2022-04-22T14:00 | 2022-04-22T19:55 | +4092.44 | +1.88 | `session_end` |

**Straty za sebou: 11** — 2022-01-24T15:00 až 2022-01-28T19:25, spolu -10858.51, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-01-24T15:00 | 2022-01-24T18:55 | -1070.06 | -0.50 | `session_end` |
| 2 | 2022-01-24T19:30 | 2022-01-24T19:55 | -907.55 | -0.42 | `session_end` |
| 3 | 2022-01-25T15:00 | 2022-01-25T15:25 | -1695.07 | -0.79 | `session_end` |
| 4 | 2022-01-25T16:00 | 2022-01-25T16:25 | -532.58 | -0.25 | `session_end` |
| 5 | 2022-01-25T17:00 | 2022-01-25T17:25 | -1307.57 | -0.61 | `session_end` |
| 6 | 2022-01-27T15:00 | 2022-01-27T15:25 | -1445.21 | -0.66 | `session_end` |
| 7 | 2022-01-27T18:30 | 2022-01-27T18:55 | -845.08 | -0.39 | `session_end` |
| 8 | 2022-01-27T19:30 | 2022-01-27T19:55 | -132.57 | -0.06 | `session_end` |
| 9 | 2022-01-28T15:00 | 2022-01-28T15:25 | -1132.55 | -0.53 | `session_end` |
| 10 | 2022-01-28T16:30 | 2022-01-28T17:55 | -245.14 | -0.11 | `session_end` |
| 11 | 2022-01-28T18:30 | 2022-01-28T19:25 | -1545.13 | -0.71 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0086 %**, medián 0.0085 %, 90 % interval -0.0011–0.0187 %
- P(edge > poplatok) = **87.9 %**
- max drawdown: medián 97.3 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 12, 95. percentil 17 obchodov
- pravdepodobnosť ruiny účtu: 48.1 %

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
<!-- POSUDOK cisla=26632999 -->

**1. Na čo sa to hodí.** Intraday momentum na ES 5m v seanse NY 9:30–16:00, jeden kontrakt, bez pozície cez noc. Zdrojové nastavenie NOA (pásmo 14 dní × 1, kontrola každých 30 min) je tu na plnom ES kontrakte, preto sú percentá a drawdown (medián 97 %, ruina 48 %) prepočítané na malý účet — pre reálne nasadenie treba MES alebo účet zodpovedajúci plnému ES. Výstupy sú v 99 % na kontrole (`session_end` = výstup cez VWAP / hranicu pásma), to je podstata NOA, nie chyba.

**2. Potenciál.** Myšlienka (Concretum, SPY) je robená práve na S&P 500 a prvé tri roky to potvrdzujú (break-even 0,015 / 0,040 / 0,009 %). Proti tomu: proti náhode len +1,3 sigma, edge od 2024 klesá a posledné obdobie je pod dolnou hranicou (3. percentil) — test „slabne“ hlási skutočný úpadok, nie šum. Bez úpravy je to skôr vlastnosť rokov 2021–2023.

**3. Čo dorobiť.** Nič v logike — zhoda s NOA MNQ a C# (`noaesnet`) je bar po bare. Treba vlastné parametre pre ES: šírku pásma (`volMult`, `lookbackDays`), hustotu kontrol a filter trendu; poistku `hardStopPct` nastaviť podľa volatility ES (je menšia ako na NQ).

**4. Čo otestovať.** Smernica beží na hube (11.–12. 11. 2026, `.nightsearch` noaes): rozhodne, či existuje nastavenie s PF ≥ 1,3 v každom roku a odloženým rokom ≥ 1,2. Ak nie, `cli matrix --strategy noaes --timeframes 3m,5m,15m` povie, či nie je problém v TF.

**5. Použiteľné?** V zdrojovom nastavení **nie** — posledný rok je stratový a edge slabne. Použiteľné len ak smernica nájde nastavenie, ktoré prejde aj odloženým rokom.

**6. Čo by som pridal.** Filter režimu dňa: obchodovať len dni, keď je pásmo šumu široké oproti dlhodobému priemeru (trendové dni), a vynechať dni pred makro správami — skupiny po vyhlásení (CPI, FOMC, NFP) majú break-even 3–5× vyšší než bežné dni.

<!-- POSUDOK KONIEC -->
