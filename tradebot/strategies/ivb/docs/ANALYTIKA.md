# Základná analytika — IVB 1.0 — Initial Volatility Breakout (`ivb`)

Zmerané 2026-10-29 na `MNQ/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `mnq_databento_5m`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy ivb \
   --profile mnq_databento_5m \
   --pair MNQ/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 100000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 548 obchodov spolu — na štatistiku dosť
- break-even 0.0231 % je nad poplatkom 0.0018 % (rezerva +0.0213 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 4.4 %
- odlíšiteľná od náhody (+3.4 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 14. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'do 0.66 R' vlastnosti 'Plánovaný RR': 222 obchodov (40.5 %), bez nej by break-even bol o +0.0106 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 122 | +2.66 | 0.0153 | 1.7 | 63.9 | +5/-3 | `20261029-203404-3b4aa7` |
| 20221001-20231001 | 120 | +9.20 | 0.0413 | 1.4 | 70.8 | +7/-2 | `20261029-203407-e85ca9` |
| 20231001-20241001 | 116 | +2.83 | 0.0106 | 2.2 | 64.7 | +6/-3 | `20261029-203410-841c5f` |
| 20240904-20250904 | 122 | +8.51 | 0.0337 | 1.5 | 70.5 | +11/-3 | `20261029-203413-7ff0e4` |
| 20250904-20260904 | 78 | +1.40 | 0.0103 | 2.0 | 61.5 | +7/-3 | `20261029-203416-0cfa25` |

Zisková v **5 z 5** okien, obchodov spolu 548, break-even celkom 0.0231 %. Okná sa prekrývajú, 10 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.38 ATR za 5 barov)
- medián držania 13.2 barov grafu
- winrate 66.79 %, payoff 0.66
- 0.31 obchodov za deň
- šikmosť výnosov -0.763

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 66.8 %, `stop_loss` 33.2 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'do 0.66 R' vlastnosti 'Plánovaný RR': 222 obchodov (40.5 %), break-even 0.0075 % oproti 0.0231 % celku. Bez nej by break-even bol 0.0337 % (+0.0106). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Plánovaný RR**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.66 R | 222 | 40.5 % | 62.2 | 0.0075 | 0.0337 | +0.0106 |
| nad 0.67 R | 77 | 14.1 % | 70.1 | 0.0266 | 0.0223 | -0.0008 |
| 0.66 R – 0.67 R | 249 | 45.4 % | 69.9 | 0.0371 | 0.0137 | -0.0094 |

**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.3442 % | 138 | 25.2 % | 64.5 | 0.0091 | 0.0336 | +0.0105 |
| nad 0.5983 % | 136 | 24.8 % | 64.0 | 0.0215 | 0.0234 | +0.0003 |
| 0.3442 % – 0.4389 % | 137 | 25.0 % | 66.4 | 0.0218 | 0.0236 | +0.0005 |
| 0.4389 % – 0.5983 % | 137 | 25.0 % | 72.3 | 0.0580 | 0.0151 | -0.0080 |

**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 15 h | 99 | 18.1 % | 58.6 | -0.0044 | 0.0302 | +0.0071 |
| do 14 h | 212 | 38.7 % | 68.4 | 0.0282 | 0.0200 | -0.0031 |
| 14 h – 15 h | 237 | 43.2 % | 68.8 | 0.0320 | 0.0168 | -0.0063 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0239 % | -0.0004 % ± 0.0071 | +3.44 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0239 % | -0.0000 % ± 0.0071 | +3.38 | 100.0 |

Edge je odlisitelny od nahody (3.4 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 148 | 10.1 | 65.5 | 0.0231 | 53 |
| 2022-12 - 2024-03 | 143 | 9.7 | 69.9 | 0.0320 | 79 |
| 2024-03 - 2025-06 | 153 | 10.4 | 68.0 | 0.0237 | 51 |
| 2025-06 - 2026-09 | 104 | 7.1 | 62.5 | 0.0102 | 14 |

Hranice pre úsek veľkosti posledného obdobia: +0.0027 až +0.0454 % (medián 0.0234).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 14. percentile, teda v medziach +0.0027 až +0.0454 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 11** — 2025-03-10T14:05 až 2025-04-08T16:19, spolu +2794.86.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-03-10T14:05 | 2025-03-10T14:46 | +206.12 | +0.52 | `take_profit` |
| 2 | 2025-03-10T14:50 | 2025-03-10T17:02 | +223.63 | +0.57 | `take_profit` |
| 3 | 2025-03-12T14:35 | 2025-03-12T15:06 | +250.13 | +0.64 | `take_profit` |
| 4 | 2025-03-19T15:10 | 2025-03-19T15:52 | +260.21 | +0.33 | `take_profit` |
| 5 | 2025-03-21T15:00 | 2025-03-21T16:57 | +176.11 | +0.44 | `take_profit` |
| 6 | 2025-03-21T17:00 | 2025-03-21T19:59 | +306.20 | +0.38 | `take_profit` |
| 7 | 2025-03-24T15:05 | 2025-03-24T19:54 | +300.21 | +0.25 | `take_profit` |
| 8 | 2025-03-25T15:35 | 2025-03-25T20:18 | +270.19 | +0.22 | `take_profit` |
| 9 | 2025-03-28T14:05 | 2025-03-28T14:08 | +321.22 | +0.40 | `take_profit` |
| 10 | 2025-03-28T14:10 | 2025-03-28T14:25 | +174.62 | +0.44 | `take_profit` |
| 11 | 2025-04-08T15:15 | 2025-04-08T16:19 | +306.24 | +0.85 | `take_profit` |

**Straty za sebou: 3** — 2021-12-28T17:35 až 2021-12-30T20:41, spolu -1388.58, rovnako dlhých sérií 8.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2021-12-28T17:35 | 2021-12-28T23:49 | -457.98 | -0.46 | `stop_loss` |
| 2 | 2021-12-29T15:15 | 2021-12-29T19:55 | -481.97 | -0.49 | `stop_loss` |
| 3 | 2021-12-30T16:00 | 2021-12-30T20:41 | -448.63 | -0.34 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0231 %**, medián 0.0232 %, 90 % interval 0.0143–0.0320 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 2.7 %, 95. percentil 4.4 %, najhorší 8.3 %
- najdlhšia séria strát: medián 4, 95. percentil 5 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **4 264** na obchod pri účte 100 000

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
<!-- POSUDOK cisla=5ca93b6a -->

**Posudok (29. 10. 2026, prepis Rust predlohy 1 : 1, MNQ 5m, defaulty predlohy: IB 9:30–10:00, IB ≤ 0,9 × priemer 10 dní, objem ≥ 1,1×, stop 3 ATR, cieľ 2 ATR).**

1. **Na čo sa hodí a na čo nie.** Na intraday Nasdaq (MNQ) od 10:00 NY. Predloha je stavaná na 5m: na 1m sa šírka IB zapisuje päťkrát za deň a filter objemu (priemer 5 barov vrátane signálneho) je ešte mäkší. Pozície predvolene idú cez noc (`flattenEod` vypnuté), ako prop stratégia s koncom dňa preto bez úpravy nie.
2. **Má potenciál?** Áno, prekvapivo: zisková v 5 z 5 okien, 548 obchodov, +3,4 sigma proti náhodnému vstupu a break-even 0,023 % je trinásťnásobok poplatku. WR 67 % pri payoffe 0,66 sedí s pomerom stop 3 ATR / cieľ 2 ATR. Slabé miesto je posledný rok: PF 1,13, break-even 0,010 % a len 78 obchodov (14. percentil, ešte v medziach). PF 1,13–1,60 po oknách je však na hranici smernice (PF ≥ 1,3).
3. **Čo dorobiť.** Opraviť dve zvláštnosti predlohy ako voliteľné prepínače (počítadlo pokusov len pri prieraze, IB do priemeru raz za deň) a pridať koniec dňa pre prop účty. Obchody po 15 h UTC (popoludnie NY) sú stratové (break-even −0,004 %) — kandidát na skorší koniec okna vstupu.
4. **Čo otestovať ďalej.** Smernicu (krok 4 hľadanie: `maxContractionRatio`, `volSurgeMult`, `slAtrMult`, `tpAtrMult`, `entryWindowEnd`), rozhodne odložený rok; matica `cli matrix --pairs ES/USD --timeframes 5m`, či myšlienka drží aj na S&P 500.
5. **Použiteľné?** Ako porovnanie áno: v predvolenom nastavení je slušná a jednoduchá, ale pod hranicou smernice (PF ~1,3) — samostatne na live zatiaľ nie, najprv smernica.
6. **Čo by som pridal.** Smer dňa (VWAP od 9:30 alebo poloha nad / pod včerajším zavretím) a vynechať popoludňajšie prierazy; cieľ ≥ 1 R namiesto 0,67 R, keď to WR unesie.

<!-- POSUDOK KONIEC -->
