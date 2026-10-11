# Základná analytika — SPX sila 1.0 (`mag7`)

Zmerané 2026-10-11 na `MNQ/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/mag7_PRESIEL_SMERNICAMI_SPX_sila_1_2026-10-11.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy mag7 \
   --profile .nightsearch/checkup/mag7_PRESIEL_SMERNICAMI_SPX_sila_1_2026-10-11.json \
   --pair MNQ/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 758 obchodov spolu — na štatistiku dosť
- break-even 0.0368 % je nad poplatkom 0.0018 % (rezerva +0.0350 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 4.9 %
- odlíšiteľná od náhody (+3.6 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-08 na 34. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- najhoršia skupina 's trendom' vlastnosti 'S trendom, alebo proti': 697 obchodov (92.0 %), bez nej by break-even bol o +0.0437 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 163 | +6.29 | 0.0446 | 1.6 | 38.0 | +4/-6 | `20261011-071943-6426d5` |
| 20221001-20231001 | 139 | +5.47 | 0.0484 | 1.3 | 38.1 | +5/-7 | `20261011-071946-c90fe6` |
| 20231001-20241001 | 150 | +7.18 | 0.0426 | 2.3 | 39.3 | +3/-8 | `20261011-071949-612596` |
| 20240904-20250904 | 154 | +6.93 | 0.0341 | 2.4 | 39.0 | +4/-11 | `20261011-071952-be409a` |
| 20250904-20260904 | 152 | +5.94 | 0.0252 | 2.8 | 37.5 | +5/-8 | `20261011-071955-6e8991` |

Zisková v **5 z 5** okien, obchodov spolu 758, break-even celkom 0.0368 %.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+1.78 ATR za 5 barov)
- medián držania 9.4 barov grafu
- winrate 38.39 %, payoff 2.153
- 0.42 obchodov za deň
- šikmosť výnosov +0.614

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 61.6 %, `take_profit` 38.4 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 's trendom' vlastnosti 'S trendom, alebo proti': 697 obchodov (92.0 %), break-even 0.0328 % oproti 0.0368 % celku. Bez nej by break-even bol 0.0805 % (+0.0437). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 697 | 92.0 % | 37.6 | 0.0328 | 0.0805 | +0.0437 |
| proti trendu | 61 | 8.0 % | 47.5 | 0.0805 | 0.0328 | -0.0040 |

**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| deň pred sviatkom | 12 | 1.6 % | 33.3 | 0.0083 | 0.0373 | +0.0005 |
| bežný deň | 707 | 93.3 % | 38.0 | 0.0351 | 0.0608 | +0.0240 |
| deň po sviatku | 22 | 2.9 % | 45.5 | 0.0790 | 0.0356 | -0.0012 |

**Hodina vstupu (UTC)** (riadi `waitMin`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 13 h | 413 | 54.5 % | 36.3 | 0.0265 | 0.0497 | +0.0129 |
| 14 h | 298 | 39.3 % | 39.3 | 0.0407 | 0.0343 | -0.0025 |
| 15 h | 47 | 6.2 % | 51.1 | 0.1124 | 0.0323 | -0.0045 |

Parametre, ktorými sa dá s tým niečo spraviť: `allowL`, `rr`, `waitMin`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0372 % | 0.0015 % ± 0.0100 | +3.57 | 99.9 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0372 % | 0.0016 % ± 0.0098 | +3.62 | 100.0 |

Edge je odlisitelny od nahody (3.6 sigma, percentil 99.9).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 203 | 13.8 | 37.4 | 0.0418 | 64 |
| 2022-12 - 2024-03 | 170 | 11.6 | 40.0 | 0.0545 | 74 |
| 2024-03 - 2025-06 | 200 | 13.6 | 38.0 | 0.0320 | 39 |
| 2025-06 - 2026-08 | 185 | 12.6 | 38.4 | 0.0285 | 34 |

Hranice pre úsek veľkosti posledného obdobia: +0.0074 až +0.0687 % (medián 0.0361).

**DRZI** — posledné obdobie (2025-06 - 2026-08) je na 34. percentile, teda v medziach +0.0074 až +0.0687 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 5** — 2023-02-13T14:50 až 2023-02-23T16:41, spolu +1276.95, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-02-13T14:50 | 2023-02-14T09:04 | +254.94 | +1.21 | `take_profit` |
| 2 | 2023-02-14T14:50 | 2023-02-14T15:12 | +255.62 | +1.02 | `take_profit` |
| 3 | 2023-02-15T14:40 | 2023-02-15T19:09 | +255.11 | +1.01 | `take_profit` |
| 4 | 2023-02-20T14:40 | 2023-02-21T08:46 | +255.64 | +1.03 | `take_profit` |
| 5 | 2023-02-23T15:10 | 2023-02-23T16:41 | +255.65 | +1.05 | `take_profit` |

**Straty za sebou: 11** — 2024-12-31T14:45 až 2025-01-28T14:56, spolu -1317.32.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-12-31T14:45 | 2024-12-31T14:47 | -119.22 | -0.19 | `stop_loss` |
| 2 | 2025-01-02T14:40 | 2025-01-02T14:46 | -119.99 | -0.28 | `stop_loss` |
| 3 | 2025-01-03T14:40 | 2025-01-03T14:48 | -119.50 | -0.28 | `stop_loss` |
| 4 | 2025-01-06T14:40 | 2025-01-06T18:45 | -121.03 | -0.28 | `stop_loss` |
| 5 | 2025-01-07T14:40 | 2025-01-07T14:44 | -120.03 | -0.28 | `stop_loss` |
| 6 | 2025-01-15T14:50 | 2025-01-16T21:00 | -119.05 | -0.50 | `stop_loss` |
| 7 | 2025-01-21T14:45 | 2025-01-21T17:28 | -120.85 | -0.36 | `stop_loss` |
| 8 | 2025-01-22T14:55 | 2025-01-23T02:06 | -119.66 | -0.36 | `stop_loss` |
| 9 | 2025-01-24T14:55 | 2025-01-24T15:15 | -119.43 | -0.31 | `stop_loss` |
| 10 | 2025-01-27T15:35 | 2025-01-27T16:00 | -120.07 | -0.45 | `stop_loss` |
| 11 | 2025-01-28T14:40 | 2025-01-28T14:56 | -118.49 | -0.28 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0368 %**, medián 0.0366 %, 90 % interval 0.0226–0.0511 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 2.9 %, 95. percentil 4.9 %, najhorší 9.3 %
- najdlhšia séria strát: medián 10, 95. percentil 15 obchodov
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
<!-- POSUDOK cisla=f07550df -->
**Posudok (AI, 11. 10. 2026)** — profil PREŠIEL SMERNICAMI č. 1 z testovania podľa smernice (krok 7).

1. **Na čo sa to hodí a na čo nie.** MNQ 5m–15m, sila S&P 500 od otvorenia NY, breakout v smere sily, WR 38 %, payoff 2,15. Séria strát až 11 (MC 95 %: 15).
2. **Má to potenciál?** Áno: 5 z 5 rokov rovnomerne (+5,5 až +7,2 %), +3,6 σ, break-even 0,037 % (~20× poplatok). Najistejšie zaradený charakter (breakout, istota dobrá).
3. **Čo dorobiť.** Obchody s trendom tvoria 92 % a sú slabšie než proti trendu — filter trendu (`trendFilter`) stojí za test, ale je to väčšina obchodov. Analytika ráta obchody z prekrývajúcich sa okien 23/24 a 24/25 (september 2024) dvakrát — najdlhšia séria strát môže byť o 1–2 nadsadená.
4. **Čo otestovať ďalej.** NAS100 z Dukascopy (krok 8) — rovnaký smer výsledku = jav trhu, nie dát; 2× poplatok (`--fee 3.51e-05`) a 1 tick sklzu navyše; forward test 4–8 týždňov na 1 MNQ (krok 9).
5. **Je to použiteľné?** Áno, použiteľná — na účte bez denného limitu; dlhé série strát sú pri payoffe 2,15 normálne.
6. **Čo by som pridal.** Kombinácia s VWAP ORB v portfóliu — obe obchodujú NY otvorenie z iného uhla; overiť spoločný drawdown (`cli portfolio`).
<!-- POSUDOK KONIEC -->
