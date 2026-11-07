# Základná analytika — SIGMA BREAKOUT 1.0 MGC (C# jadro) (`sigmamgcnet`)

Zmerané 2026-11-07 na `MGC/USD` 30m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `PRESIEL_SMERNICAMI_SIGMA_MGC_1`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy sigmamgcnet \
   --profile PRESIEL_SMERNICAMI_SIGMA_MGC_1 \
   --pair MGC/USD \
   --timeframe 30m \
   --fee 1.755e-05
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 906 obchodov spolu — na štatistiku dosť
- break-even 0.0287 % je nad poplatkom 0.0018 % (rezerva +0.0269 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 16.1 %
- odlíšiteľná od náhody (+2.2 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-08 na 83. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- 100 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 'bežný deň' vlastnosti 'Sviatok na burze v USA': 855 obchodov (94.4 %), bez nej by break-even bol o +0.0268 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 184 | +9.23 | 0.0155 | 5.5 | 55.4 | +7/-4 | `20261107-151303-9071df` |
| 20221001-20231001 | 185 | +15.39 | 0.0237 | 4.2 | 55.1 | +8/-5 | `20261107-151306-4d6d7e` |
| 20231001-20241001 | 186 | +11.05 | 0.0150 | 10.5 | 45.2 | +6/-7 | `20261107-151310-958c0f` |
| 20240904-20250904 | 193 | +12.27 | 0.0123 | 9.7 | 47.7 | +9/-6 | `20261107-151313-03a24f` |
| 20250904-20260904 | 175 | +81.39 | 0.0542 | 5.6 | 48.0 | +6/-5 | `20261107-151316-585c54` |

Zisková v **5 z 5** okien, obchodov spolu 906, break-even celkom 0.0287 %. Okná sa prekrývajú, 17 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+0.61 ATR za 5 barov)
- medián držania 4.3 barov grafu
- winrate 50.33 %, payoff 1.516
- 0.5 obchodov za deň
- šikmosť výnosov +1.633

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `session_end` 100 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'bežný deň' vlastnosti 'Sviatok na burze v USA': 855 obchodov (94.4 %), break-even 0.0272 % oproti 0.0287 % celku. Bez nej by break-even bol 0.0555 % (+0.0268). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bežný deň | 855 | 94.4 % | 50.1 | 0.0272 | 0.0555 | +0.0268 |
| deň pred sviatkom | 13 | 1.4 % | 53.9 | 0.0592 | 0.0283 | -0.0004 |
| deň po sviatku | 28 | 3.1 % | 60.7 | 0.0690 | 0.0275 | -0.0012 |

**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 721 | 79.6 % | 50.1 | 0.0234 | 0.0490 | +0.0203 |
| proti trendu | 185 | 20.4 % | 51.4 | 0.0490 | 0.0234 | -0.0053 |

**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 9.912 % | 226 | 24.9 % | 53.5 | 0.0035 | 0.0360 | +0.0073 |
| 9.865 % – 9.912 % | 226 | 24.9 % | 50.4 | 0.0051 | 0.0360 | +0.0073 |
| do 9.7965 % | 227 | 25.1 % | 41.4 | 0.0316 | 0.0275 | -0.0012 |
| 9.7965 % – 9.865 % | 227 | 25.1 % | 56.0 | 0.0697 | 0.0149 | -0.0138 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0287 % | 0.0026 % ± 0.0121 | +2.16 | 98.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0287 % | 0.0036 % ± 0.0119 | +2.12 | 98.3 |

Edge je odlisitelny od nahody (2.2 sigma, percentil 98.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 224 | 15.2 | 54.5 | 0.0136 | 21 |
| 2022-12 - 2024-03 | 227 | 15.4 | 51.1 | 0.0118 | 16 |
| 2024-03 - 2025-06 | 235 | 16.0 | 46.0 | 0.0268 | 48 |
| 2025-06 - 2026-08 | 220 | 14.9 | 50.0 | 0.0448 | 83 |

Hranice pre úsek veľkosti posledného obdobia: +0.0034 až +0.0587 % (medián 0.0261).

**DRZI** — posledné obdobie (2025-06 - 2026-08) je na 83. percentile, teda v medziach +0.0034 až +0.0587 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 9** — 2025-08-21T14:38 až 2025-09-03T20:00, spolu +458.02.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-08-21T14:38 | 2025-08-21T14:30 | +39.81 | +0.12 | `session_end` |
| 2 | 2025-08-21T18:20 | 2025-08-21T20:00 | +5.81 | +0.02 | `session_end` |
| 3 | 2025-08-22T18:22 | 2025-08-22T20:00 | +1.80 | +0.01 | `session_end` |
| 4 | 2025-08-26T17:38 | 2025-08-26T20:00 | +90.79 | +0.26 | `session_end` |
| 5 | 2025-08-27T17:36 | 2025-08-27T20:00 | +29.79 | +0.09 | `session_end` |
| 6 | 2025-08-28T15:17 | 2025-08-28T20:00 | +118.78 | +0.34 | `session_end` |
| 7 | 2025-08-29T17:15 | 2025-08-29T20:00 | +23.77 | +0.07 | `session_end` |
| 8 | 2025-09-02T17:02 | 2025-09-02T20:00 | +116.74 | +0.33 | `session_end` |
| 9 | 2025-09-03T14:53 | 2025-09-03T20:00 | +30.73 | +0.08 | `session_end` |

**Straty za sebou: 7** — 2024-03-22T14:09 až 2024-04-05T20:00, spolu -254.55.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-03-22T14:09 | 2024-03-22T15:00 | -50.76 | -0.23 | `session_end` |
| 2 | 2024-03-22T18:18 | 2024-03-22T20:00 | -36.76 | -0.17 | `session_end` |
| 3 | 2024-03-28T18:33 | 2024-03-28T20:00 | -1.79 | -0.01 | `session_end` |
| 4 | 2024-04-02T14:47 | 2024-04-02T14:30 | -4.80 | -0.02 | `session_end` |
| 5 | 2024-04-04T15:12 | 2024-04-04T16:30 | -51.81 | -0.22 | `session_end` |
| 6 | 2024-04-04T19:02 | 2024-04-04T19:30 | -97.81 | -0.42 | `session_end` |
| 7 | 2024-04-05T17:25 | 2024-04-05T20:00 | -10.82 | -0.05 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0287 %**, medián 0.0281 %, 90 % interval 0.0151–0.0440 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 9.0 %, 95. percentil 16.1 %, najhorší 45.3 %
- najdlhšia séria strát: medián 8, 95. percentil 10 obchodov
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
<!-- POSUDOK cisla=85f2d73b -->

**Posudok (7. 11. 2026, C# jadro Sigma Breakout na zlate, profil PRESIEL_SMERNICAMI_SIGMA_MGC_1, MGC 30m, 1 kontrakt.)**

1. **Na čo sa hodí a na čo nie.** Zlato (MGC / GC) počas RTH 9:30–16:00 NY, výstup každý deň o 16:00 — vhodné aj na prop účty. Nie na nočnú seansu.
2. **Má potenciál?** Áno: zisková v 5 z 5 okien, 906 obchodov, +2,2 sigma proti náhode, break-even 0,029 %, prepad drží (95. percentil 16 %), odložený rok +81 %. Edge v poslednom období na 83. percentile — skôr silnie. Trieda A auditu, Sortino 2,93; s Nasdaq stratégiami takmer nekorelovaná.
3. **Čo dorobiť.** Pravidlo vypnutia naživo z Monte Carlo prepadu; sviatky v USA (bežný deň nesie celý zisk, sviatky sú len šum) zvážiť vynechať.
4. **Čo otestovať ďalej.** Forward test na deme 4–8 týždňov (`sigmamgcnet`, MT5 XAUUSD alebo NT8 MGC); na CFD XAUUSD skontrolovať veľkosť kontraktu.
5. **Použiteľné?** Áno — C# jadro sedí s Pythonom bar po bare na všetkých 7 profiloch, pripravené na demo.
6. **Čo by som pridal.** Kombináciu so SPRÁVAMI (obe zlato, iný čas a iný jav) ako zlatú časť portfólia.

<!-- POSUDOK KONIEC -->
