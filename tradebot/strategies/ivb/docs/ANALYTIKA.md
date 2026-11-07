# Základná analytika — IVB 1.0 — Initial Volatility Breakout (`ivb`)

Zmerané 2026-11-03 na `MNQ/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/ivb_PRESIEL_SMERNICAMI_IVB_MNQ_1_2026-11-03.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy ivb \
   --profile .nightsearch/checkup/ivb_PRESIEL_SMERNICAMI_IVB_MNQ_1_2026-11-03.json \
   --pair MNQ/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 1001 obchodov spolu — na štatistiku dosť
- break-even 0.0140 % je nad poplatkom 0.0018 % (rezerva +0.0122 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 2.8 %
- odlíšiteľná od náhody (+7.0 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 46. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- proti náhode v tých istých hodinách je rozdiel podstatne menší (+5.2 vs +7.0 sigma) — veľká časť edge je v tom, KEDY obchoduje, nie v tom, čo si vyberá
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'NFP' vlastnosti 'Makro udalosť v ten deň': 52 obchodov (5.2 %), bez nej by break-even bol o +0.0110 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 204 | +1.75 | 0.0109 | 1.5 | 92.2 | +25/-1 | `20261103-051253-4901e9` |
| 20221001-20231001 | 228 | +3.35 | 0.0184 | 0.5 | 93.0 | +30/-1 | `20261103-051256-b15532` |
| 20231001-20241001 | 183 | +1.76 | 0.0097 | 0.7 | 91.3 | +32/-1 | `20261103-051300-a44c90` |
| 20240904-20250904 | 206 | +4.32 | 0.0164 | 1.0 | 93.2 | +34/-2 | `20261103-051303-5edd96` |
| 20250904-20260904 | 188 | +4.35 | 0.0147 | 1.9 | 93.1 | +47/-2 | `20261103-051306-b95087` |

Zisková v **5 z 5** okien, obchodov spolu 1001, break-even celkom 0.0140 %. Okná sa prekrývajú, 8 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.58 ATR za 5 barov)
- medián držania 0.4 barov grafu
- winrate 92.51 %, payoff 0.125
- 0.56 obchodov za deň
- šikmosť výnosov -3.93

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 92.7 %, `stop_loss` 7.3 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'NFP' vlastnosti 'Makro udalosť v ten deň': 52 obchodov (5.2 %), break-even 0.0095 % oproti 0.014 % celku. Bez nej by break-even bol 0.0142 % (+0.0110). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| NFP | 52 | 5.2 % | 94.2 | 0.0095 | 0.0142 | +0.0002 |
| žiadna | 879 | 87.8 % | 92.0 | 0.0125 | 0.0250 | +0.0110 |
| FOMC | 33 | 3.3 % | 93.9 | 0.0238 | 0.0137 | -0.0003 |
| CPI | 34 | 3.4 % | 100.0 | 0.0525 | 0.0128 | -0.0012 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bez udalosti | 879 | 87.8 % | 92.0 | 0.0125 | 0.0250 | +0.0110 |
| pred vyhlásením | 36 | 3.6 % | 94.4 | 0.0244 | 0.0136 | -0.0004 |
| po vyhlásení | 86 | 8.6 % | 96.5 | 0.0253 | 0.0129 | -0.0011 |

**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 880 | 87.9 % | 92.3 | 0.0130 | 0.0207 | +0.0067 |
| proti trendu | 121 | 12.1 % | 94.2 | 0.0207 | 0.0130 | -0.0010 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0140 % | 0.0000 % ± 0.0020 | +7.03 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0140 % | 0.0001 % ± 0.0026 | +5.25 | 100.0 |

Edge je odlisitelny od nahody (7.0 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 258 | 17.5 | 93.4 | 0.0181 | 76 |
| 2022-12 - 2024-03 | 234 | 15.9 | 91.9 | 0.0114 | 33 |
| 2024-03 - 2025-06 | 261 | 17.7 | 92.0 | 0.0133 | 44 |
| 2025-06 - 2026-09 | 248 | 16.8 | 92.7 | 0.0136 | 46 |

Hranice pre úsek veľkosti posledného obdobia: +0.0047 až +0.0232 % (medián 0.0141).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 46. percentile, teda v medziach +0.0047 až +0.0232 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 47** — 2026-03-20T13:55 až 2026-06-16T13:55, spolu +1742.76.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-03-20T13:55 | 2026-03-20T13:55 | +40.29 | +0.08 | `take_profit` |
| 2 | 2026-03-20T14:00 | 2026-03-20T14:01 | +44.80 | +0.09 | `take_profit` |
| 3 | 2026-03-25T13:50 | 2026-03-25T13:50 | +41.29 | +0.08 | `take_profit` |
| 4 | 2026-03-25T13:55 | 2026-03-25T14:00 | +42.29 | +0.09 | `take_profit` |
| 5 | 2026-03-25T14:05 | 2026-03-25T15:16 | +45.29 | +0.09 | `take_profit` |
| 6 | 2026-03-27T13:55 | 2026-03-27T13:55 | +43.85 | +0.09 | `take_profit` |
| 7 | 2026-03-27T14:00 | 2026-03-27T14:00 | +51.85 | +0.11 | `take_profit` |
| 8 | 2026-03-30T13:50 | 2026-03-30T13:55 | +31.86 | +0.07 | `take_profit` |
| 9 | 2026-03-30T14:00 | 2026-03-30T14:41 | +32.36 | +0.07 | `take_profit` |
| 10 | 2026-03-30T14:45 | 2026-03-30T17:13 | +40.87 | +0.09 | `take_profit` |
| 11 | 2026-04-06T13:55 | 2026-04-06T13:57 | +38.29 | +0.08 | `take_profit` |
| 12 | 2026-04-06T14:00 | 2026-04-06T14:00 | +40.29 | +0.08 | `take_profit` |
| 13 | 2026-04-13T13:50 | 2026-04-13T13:50 | +27.73 | +0.05 | `take_profit` |
| 14 | 2026-04-13T13:55 | 2026-04-13T13:58 | +30.73 | +0.06 | `take_profit` |
| 15 | 2026-04-13T14:00 | 2026-04-13T14:00 | +34.22 | +0.07 | `take_profit` |
| 16 | 2026-04-15T14:05 | 2026-04-15T14:14 | +27.17 | +0.05 | `take_profit` |
| 17 | 2026-04-17T14:00 | 2026-04-17T14:04 | +42.62 | +0.08 | `take_profit` |
| 18 | 2026-04-21T14:00 | 2026-04-21T14:07 | +30.12 | +0.06 | `take_profit` |
| 19 | 2026-04-23T13:50 | 2026-04-23T14:57 | +29.10 | +0.05 | `take_profit` |
| 20 | 2026-04-23T15:00 | 2026-04-23T15:00 | +36.10 | +0.07 | `take_profit` |
| 21 | 2026-04-29T13:55 | 2026-04-29T14:24 | +28.09 | +0.05 | `take_profit` |
| 22 | 2026-04-29T14:30 | 2026-04-29T14:34 | +31.59 | +0.06 | `take_profit` |
| 23 | 2026-05-01T14:00 | 2026-05-01T14:02 | +12.04 | +0.02 | `take_profit` |
| 24 | 2026-05-04T14:00 | 2026-05-04T14:39 | +37.04 | +0.07 | `take_profit` |
| 25 | 2026-05-05T14:05 | 2026-05-05T14:24 | +24.03 | +0.04 | `take_profit` |
| 26 | 2026-05-06T13:55 | 2026-05-06T14:40 | +46.00 | +0.08 | `take_profit` |
| 27 | 2026-05-06T14:45 | 2026-05-06T14:53 | +48.00 | +0.08 | `take_profit` |
| 28 | 2026-05-07T13:55 | 2026-05-07T13:55 | +23.48 | +0.04 | `take_profit` |
| 29 | 2026-05-08T13:50 | 2026-05-08T13:53 | +33.46 | +0.06 | `take_profit` |
| 30 | 2026-05-08T14:05 | 2026-05-08T14:22 | +37.96 | +0.07 | `take_profit` |
| 31 | 2026-05-14T13:50 | 2026-05-14T13:50 | +33.92 | +0.06 | `take_profit` |
| 32 | 2026-05-21T13:55 | 2026-05-21T14:01 | +49.94 | +0.09 | `take_profit` |
| 33 | 2026-05-21T14:05 | 2026-05-21T17:10 | +51.94 | +0.09 | `take_profit` |
| 34 | 2026-05-26T13:50 | 2026-05-26T13:57 | +28.90 | +0.05 | `take_profit` |
| 35 | 2026-05-26T14:00 | 2026-05-26T14:14 | +33.89 | +0.06 | `take_profit` |
| 36 | 2026-05-26T14:15 | 2026-05-26T14:19 | +33.89 | +0.06 | `take_profit` |
| 37 | 2026-05-29T13:50 | 2026-05-29T13:53 | +25.86 | +0.04 | `take_profit` |
| 38 | 2026-05-29T13:55 | 2026-05-29T13:56 | +27.36 | +0.04 | `take_profit` |
| 39 | 2026-05-29T14:00 | 2026-05-29T14:00 | +26.86 | +0.04 | `take_profit` |
| 40 | 2026-06-02T14:00 | 2026-06-02T14:07 | +37.35 | +0.06 | `take_profit` |
| 41 | 2026-06-05T13:50 | 2026-06-05T13:57 | +44.40 | +0.07 | `take_profit` |
| 42 | 2026-06-05T14:00 | 2026-06-05T15:13 | +51.41 | +0.09 | `take_profit` |
| 43 | 2026-06-12T14:10 | 2026-06-12T14:17 | +83.42 | +0.14 | `take_profit` |
| 44 | 2026-06-15T13:50 | 2026-06-15T13:53 | +33.84 | +0.06 | `take_profit` |
| 45 | 2026-06-15T13:55 | 2026-06-15T13:55 | +35.84 | +0.06 | `take_profit` |
| 46 | 2026-06-16T13:50 | 2026-06-16T13:50 | +35.83 | +0.06 | `take_profit` |
| 47 | 2026-06-16T13:55 | 2026-06-16T13:55 | +35.33 | +0.06 | `take_profit` |

**Straty za sebou: 2** — 2025-01-24T14:55 až 2025-01-30T15:02, spolu -434.07, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-01-24T14:55 | 2025-01-24T15:16 | -154.05 | -0.35 | `stop_loss` |
| 2 | 2025-01-30T14:50 | 2025-01-30T15:02 | -280.02 | -0.64 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0140 %**, medián 0.0140 %, 90 % interval 0.0092–0.0187 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 1.7 %, 95. percentil 2.8 %, najhorší 6.0 %
- najdlhšia séria strát: medián 2, 95. percentil 2 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

> **Posudok je starší než čísla** (písal sa k vzorke `5ca93b6a`, tu je `f84ee5fd`). Nech ho AI prepíše — čísla nižšie sa medzitým zmenili.

<!-- POSUDOK cisla=5ca93b6a -->

**Posudok (29. 10. 2026, prepis Rust predlohy 1 : 1, MNQ 5m, defaulty predlohy: IB 9:30–10:00, IB ≤ 0,9 × priemer 10 dní, objem ≥ 1,1×, stop 3 ATR, cieľ 2 ATR).**

1. **Na čo sa hodí a na čo nie.** Na intraday Nasdaq (MNQ) od 10:00 NY. Predloha je stavaná na 5m: na 1m sa šírka IB zapisuje päťkrát za deň a filter objemu (priemer 5 barov vrátane signálneho) je ešte mäkší. Pozície predvolene idú cez noc (`flattenEod` vypnuté), ako prop stratégia s koncom dňa preto bez úpravy nie.
2. **Má potenciál?** Áno, prekvapivo: zisková v 5 z 5 okien, 548 obchodov, +3,4 sigma proti náhodnému vstupu a break-even 0,023 % je trinásťnásobok poplatku. WR 67 % pri payoffe 0,66 sedí s pomerom stop 3 ATR / cieľ 2 ATR. Slabé miesto je posledný rok: PF 1,13, break-even 0,010 % a len 78 obchodov (14. percentil, ešte v medziach). PF 1,13–1,60 po oknách je však na hranici smernice (PF ≥ 1,3).
3. **Čo dorobiť.** Opraviť dve zvláštnosti predlohy ako voliteľné prepínače (počítadlo pokusov len pri prieraze, IB do priemeru raz za deň) a pridať koniec dňa pre prop účty. Obchody po 15 h UTC (popoludnie NY) sú stratové (break-even −0,004 %) — kandidát na skorší koniec okna vstupu.
4. **Čo otestovať ďalej.** Smernicu (krok 4 hľadanie: `maxContractionRatio`, `volSurgeMult`, `slAtrMult`, `tpAtrMult`, `entryWindowEnd`), rozhodne odložený rok; matica `cli matrix --pairs ES/USD --timeframes 5m`, či myšlienka drží aj na S&P 500.
5. **Použiteľné?** Ako porovnanie áno: v predvolenom nastavení je slušná a jednoduchá, ale pod hranicou smernice (PF ~1,3) — samostatne na live zatiaľ nie, najprv smernica.
6. **Čo by som pridal.** Smer dňa (VWAP od 9:30 alebo poloha nad / pod včerajším zavretím) a vynechať popoludňajšie prierazy; cieľ ≥ 1 R namiesto 0,67 R, keď to WR unesie.

<!-- POSUDOK KONIEC -->
