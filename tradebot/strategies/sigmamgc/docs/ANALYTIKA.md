# Základná analytika — SIGMA BREAKOUT 1.0 (MGC) (`sigmamgc`)

Zmerané 2026-11-01 na `MGC/USD` 30m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/sigmamgc_PRESIEL_SMERNICAMI_SIGMA_MGC_1_2026-11-01.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy sigmamgc \
   --profile .nightsearch/checkup/sigmamgc_PRESIEL_SMERNICAMI_SIGMA_MGC_1_2026-11-01.json \
   --pair MGC/USD \
   --timeframe 30m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 906 obchodov spolu — na štatistiku dosť
- break-even 0.0287 % je nad poplatkom 0.0018 % (rezerva +0.0269 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 3.3 %
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
| 20211001-20221001 | 184 | +1.54 | 0.0155 | 1.0 | 55.4 | +7/-4 | `20261101-051429-7d29e7` |
| 20221001-20231001 | 185 | +2.56 | 0.0237 | 0.7 | 55.1 | +8/-5 | `20261101-051432-f70b74` |
| 20231001-20241001 | 186 | +1.84 | 0.0150 | 1.8 | 45.2 | +6/-7 | `20261101-051436-e23025` |
| 20240904-20250904 | 193 | +2.05 | 0.0123 | 1.9 | 47.7 | +9/-6 | `20261101-051439-ec1405` |
| 20250904-20260904 | 175 | +13.56 | 0.0542 | 1.5 | 48.0 | +6/-5 | `20261101-051442-119b92` |

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
- max drawdown: medián 2.0 %, 95. percentil 3.3 %, najhorší 8.1 %
- najdlhšia séria strát: medián 8, 95. percentil 10 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

> **Posudok je starší než čísla** (písal sa k vzorke `b3b7d7b2`, tu je `a11b49e1`). Nech ho AI prepíše — čísla nižšie sa medzitým zmenili.

<!-- POSUDOK cisla=b3b7d7b2 -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na MGC, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Intraday momentum na indexoch (rovnaký jav ako NOA — Zarattini a spol.), 9:30–16:00 NY; zlato nemá otvorenie RTH, ktoré by pásmo ukotvilo. Tu na MGC (zlato) — logika robená pre index, čísla to treba brať ako test prenosu.
2. **Má potenciál?** Zisková v 1 z 5 okien, 1819 obchodov (~364 za rok), break-even -0.0031 % (pod poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 44.58 % pri payoffe 1.182. Odložený rok 25/26: -50.89 % PnL, break-even -0.0130 %. Kladné okná sú skôr vlastnosť vzorky ako stabilný jav.
3. **Čo dorobiť.** Stop: predloha bez stopu → 95. percentil DD je obrovský; otestovať `slPct` 0,25–1 % a kontrolu len každých 15–30 min (otočky v šume).
4. **Čo otestovať ďalej.** Smernica (`sigma*`: TF, dni sigma, násobok pásma, VWAP, stop); porovnať s NOA — ak NOA robí to isté lepšie, Sigma je duplicita.
5. **Použiteľné?** **V defaultoch predlohy nie** — edge nad poplatkom nie je stabilný po rokoch; šancu má len s nastavením, ktoré nájde smernica (inak vyradiť).
6. **Čo by som pridal.** Výstup cez VWAP / hranicu pásma (trailing ako NOA) namiesto držania do 16:00; menej otočiek pri širšom pásme.

<!-- POSUDOK KONIEC -->
