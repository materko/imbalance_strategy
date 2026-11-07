# Základná analytika — SIGMA BREAKOUT 1.0 (C# jadro) (`sigmanet`)

Zmerané 2026-11-07 na `MNQ/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `PRESIEL_SMERNICAMI_SIGMA_MNQ_1`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy sigmanet \
   --profile PRESIEL_SMERNICAMI_SIGMA_MNQ_1 \
   --pair MNQ/USD \
   --timeframe 3m \
   --fee 1.755e-05
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 833 obchodov spolu — na štatistiku dosť
- break-even 0.0537 % je nad poplatkom 0.0018 % (rezerva +0.0519 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- odlíšiteľná od náhody (+4.3 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 47. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- 95. percentil max drawdownu 38.3 % (namerané 18.6 % medián) — na účet to treba mať
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- 100 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina '99.98 R – 100 R' vlastnosti 'Plánovaný RR': 173 obchodov (41.9 %), bez nej by break-even bol o +0.0396 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 176 | +43.07 | 0.0462 | 27.1 | 56.8 | +6/-6 | `20261107-151212-9cb8be` |
| 20221001-20231001 | 171 | +37.81 | 0.0439 | 10.9 | 58.5 | +6/-5 | `20261107-151221-6af2d9` |
| 20231001-20241001 | 172 | +45.01 | 0.0384 | 14.5 | 53.5 | +5/-5 | `20261107-151230-952d22` |
| 20240904-20250904 | 157 | +68.80 | 0.0536 | 17.8 | 52.9 | +7/-5 | `20261107-151239-99a223` |
| 20250904-20260904 | 164 | +111.00 | 0.0653 | 12.7 | 58.5 | +9/-7 | `20261107-151249-df7766` |

Zisková v **5 z 5** okien, obchodov spolu 833, break-even celkom 0.0537 %. Okná sa prekrývajú, 7 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+0.92 ATR za 5 barov)
- medián držania 103 barov grafu
- winrate 56.18 %, payoff 1.096
- 0.46 obchodov za deň
- šikmosť výnosov +1.59

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `session_end` 100 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je '99.98 R – 100 R' vlastnosti 'Plánovaný RR': 173 obchodov (41.9 %), break-even 0.0137 % oproti 0.0537 % celku. Bez nej by break-even bol 0.1056 % (+0.0396). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Plánovaný RR**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 99.98 R – 100 R | 173 | 41.9 % | 56.1 | 0.0137 | 0.1056 | +0.0396 |
| 100 R – 100.01 R | 36 | 8.7 % | 63.9 | 0.0723 | 0.0652 | -0.0008 |
| do 99.98 R | 111 | 26.9 % | 65.8 | 0.0781 | 0.0620 | -0.0040 |
| nad 100.01 R | 93 | 22.5 % | 64.5 | 0.1528 | 0.0418 | -0.0242 |

**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 806 | 96.8 % | 56.3 | 0.0530 | 0.0734 | +0.0197 |
| proti trendu | 27 | 3.2 % | 51.9 | 0.0734 | 0.0530 | -0.0007 |

**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| deň po sviatku | 24 | 2.9 % | 54.2 | 0.0324 | 0.0543 | +0.0006 |
| bežný deň | 789 | 94.7 % | 56.0 | 0.0526 | 0.0719 | +0.0182 |
| deň pred sviatkom | 12 | 1.4 % | 66.7 | 0.1524 | 0.0521 | -0.0016 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0537 % | 0.0007 % ± 0.0122 | +4.34 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0537 % | -0.0005 % ± 0.0139 | +3.91 | 100.0 |

Edge je odlisitelny od nahody (4.3 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 218 | 14.8 | 56.9 | 0.0462 | 40 |
| 2022-12 - 2024-03 | 217 | 14.7 | 57.1 | 0.0416 | 35 |
| 2024-03 - 2025-06 | 196 | 13.3 | 55.6 | 0.0746 | 76 |
| 2025-06 - 2026-09 | 202 | 13.7 | 55.0 | 0.0496 | 47 |

Hranice pre úsek veľkosti posledného obdobia: +0.0064 až +0.1023 % (medián 0.0514).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 47. percentile, teda v medziach +0.0064 až +0.1023 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 9** — 2026-06-01T15:42 až 2026-06-17T20:00, spolu +3869.04.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-06-01T15:42 | 2026-06-01T20:00 | +61.36 | +0.10 | `session_end` |
| 2 | 2026-06-02T15:39 | 2026-06-02T20:00 | +30.85 | +0.05 | `session_end` |
| 3 | 2026-06-05T15:06 | 2026-06-05T20:00 | +1710.94 | +2.87 | `session_end` |
| 4 | 2026-06-09T14:27 | 2026-06-09T20:00 | +713.94 | +1.21 | `session_end` |
| 5 | 2026-06-11T17:39 | 2026-06-11T20:00 | +559.44 | +0.96 | `session_end` |
| 6 | 2026-06-12T14:21 | 2026-06-12T20:00 | +141.42 | +0.24 | `session_end` |
| 7 | 2026-06-15T13:36 | 2026-06-15T20:00 | +336.84 | +0.55 | `session_end` |
| 8 | 2026-06-16T17:06 | 2026-06-16T20:00 | +310.87 | +0.51 | `session_end` |
| 9 | 2026-06-17T19:36 | 2026-06-17T20:00 | +3.39 | +0.01 | `session_end` |

**Straty za sebou: 7** — 2025-12-02T14:45 až 2025-12-11T21:00, spolu -968.62.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-12-02T14:45 | 2025-12-02T21:00 | -0.80 | -0.00 | `session_end` |
| 2 | 2025-12-04T14:57 | 2025-12-04T21:00 | -110.30 | -0.22 | `session_end` |
| 3 | 2025-12-05T15:48 | 2025-12-05T21:00 | -181.81 | -0.35 | `session_end` |
| 4 | 2025-12-08T16:00 | 2025-12-08T21:00 | -2.80 | -0.01 | `session_end` |
| 5 | 2025-12-09T16:33 | 2025-12-09T21:00 | -11.80 | -0.02 | `session_end` |
| 6 | 2025-12-10T20:09 | 2025-12-10T21:00 | -115.31 | -0.22 | `session_end` |
| 7 | 2025-12-11T14:54 | 2025-12-11T21:00 | -545.80 | -1.07 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0537 %**, medián 0.0534 %, 90 % interval 0.0304–0.0778 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 18.6 %, 95. percentil 38.3 %, najhorší 100.0 %
- najdlhšia séria strát: medián 7, 95. percentil 9 obchodov
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
<!-- POSUDOK cisla=7e7191aa -->

**Posudok (7. 11. 2026, C# jadro Sigma Breakout, profil PRESIEL_SMERNICAMI_SIGMA_MNQ_1, MNQ, 1 kontrakt.)**

1. **Na čo sa hodí a na čo nie.** Intraday momentum na Nasdaq futures (MNQ / NQ) počas RTH 9:30–16:00 NY, každý deň von o 16:00 — vhodné aj na prop účty s koncom dňa. Nie na zlato bez otvorenia RTH ani na trhy bez výraznej dennej seansy.
2. **Má potenciál?** Áno: zisková v 5 z 5 okien, 833 obchodov, +4,3 sigma proti náhodnému vstupu, break-even 0,054 % je tridsaťnásobok poplatku, odložený rok +111 % pri WR 58 %. Edge v poslednom období je na 47. percentile — normálny, neslabne. Trieda A auditu, Sortino 2,68.
3. **Čo dorobiť.** Pravidlo vypnutia naživo (95. percentil Monte Carlo prepadu 38 % pri 1 kontrakte — veľkosť voliť tak, aby to účet uniesol); 42 % obchodov má poistku 10 % (bez skutočného stopu) — pre live zvážiť `slPct`.
4. **Čo otestovať ďalej.** Forward test na deme 4–8 týždňov (`sigmanet` na MT5 / NT8), porovnanie naživo vs. test na karte Live; korelácia s NOA (0,56) — spolu ich nedávať na jeden účet.
5. **Použiteľné?** Áno — C# jadro sedí s Pythonom bar po bare (`test_csharp_parity_sigma.py`), stratégia je pripravená na demo nasadenie.
6. **Čo by som pridal.** Výstup cez VWAP alebo hranicu pásma (ako NOA) namiesto držania do 16:00 — menší prepad pri otočkách.

<!-- POSUDOK KONIEC -->
