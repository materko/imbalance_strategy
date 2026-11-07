# Základná analytika — IVB 1.0 (MGC) (`ivbmgc`)

Zmerané 2026-11-02 na `MGC/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/ivbmgc_PRESIEL_SMERNICAMI_IVB_MGC_1_2026-11-02.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy ivbmgc \
   --profile .nightsearch/checkup/ivbmgc_PRESIEL_SMERNICAMI_IVB_MGC_1_2026-11-02.json \
   --pair MGC/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 757 obchodov spolu — na štatistiku dosť
- break-even 0.0114 % je nad poplatkom 0.0018 % (rezerva +0.0096 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 1.8 %
- odlíšiteľná od náhody (+4.2 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 70. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'FOMC' vlastnosti 'Makro udalosť v ten deň': 33 obchodov (4.4 %), bez nej by break-even bol o +0.0110 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 170 | +1.03 | 0.0117 | 0.5 | 76.5 | +16/-3 | `20261102-051243-373b47` |
| 20221001-20231001 | 152 | +0.79 | 0.0100 | 0.4 | 73.0 | +11/-4 | `20261102-051247-b7f110` |
| 20231001-20241001 | 167 | +1.00 | 0.0097 | 0.4 | 73.0 | +10/-4 | `20261102-051250-60da29` |
| 20240904-20250904 | 145 | +1.25 | 0.0103 | 0.5 | 72.4 | +18/-4 | `20261102-051253-bddd1e` |
| 20250904-20260904 | 136 | +2.44 | 0.0141 | 1.6 | 72.8 | +13/-3 | `20261102-051256-448877` |

Zisková v **5 z 5** okien, obchodov spolu 757, break-even celkom 0.0114 %. Okná sa prekrývajú, 13 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.77 ATR za 5 barov)
- medián držania 3.4 barov grafu
- winrate 73.58 %, payoff 0.481
- 0.42 obchodov za deň
- šikmosť výnosov -1.045

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 73.6 %, `stop_loss` 26.4 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'FOMC' vlastnosti 'Makro udalosť v ten deň': 33 obchodov (4.4 %), break-even -0.0005 % oproti 0.0114 % celku. Bez nej by break-even bol 0.012 % (+0.0110). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| FOMC | 33 | 4.4 % | 72.7 | -0.0005 | 0.0120 | +0.0006 |
| žiadna | 661 | 87.3 % | 72.8 | 0.0099 | 0.0224 | +0.0110 |
| CPI | 26 | 3.4 % | 80.8 | 0.0319 | 0.0107 | -0.0007 |
| NFP | 37 | 4.9 % | 83.8 | 0.0418 | 0.0101 | -0.0013 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| pred vyhlásením | 17 | 2.2 % | 76.5 | 0.0010 | 0.0117 | +0.0003 |
| bez udalosti | 661 | 87.3 % | 72.8 | 0.0099 | 0.0224 | +0.0110 |
| po vyhlásení | 79 | 10.4 % | 79.8 | 0.0284 | 0.0096 | -0.0018 |

**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| deň pred sviatkom | 14 | 1.8 % | 64.3 | 0.0034 | 0.0115 | +0.0001 |
| bežný deň | 706 | 93.3 % | 73.5 | 0.0111 | 0.0154 | +0.0040 |
| deň po sviatku | 20 | 2.6 % | 85.0 | 0.0260 | 0.0110 | -0.0004 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0114 % | 0.0001 % ± 0.0027 | +4.24 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0114 % | 0.0007 % ± 0.0027 | +3.98 | 100.0 |

Edge je odlisitelny od nahody (4.2 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 204 | 13.9 | 77.0 | 0.0128 | 63 |
| 2022-12 - 2024-03 | 189 | 12.8 | 73.5 | 0.0105 | 43 |
| 2024-03 - 2025-06 | 193 | 13.1 | 70.0 | 0.0074 | 24 |
| 2025-06 - 2026-09 | 171 | 11.6 | 73.7 | 0.0140 | 70 |

Hranice pre úsek veľkosti posledného obdobia: +0.0011 až +0.0222 % (medián 0.0110).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 70. percentile, teda v medziach +0.0011 až +0.0222 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 18** — 2025-06-25T19:55 až 2025-08-13T14:07, spolu +442.72.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-06-25T19:55 | 2025-06-25T20:03 | +18.82 | +0.06 | `take_profit` |
| 2 | 2025-06-30T16:55 | 2025-06-30T17:00 | +24.84 | +0.08 | `take_profit` |
| 3 | 2025-06-30T19:15 | 2025-06-30T19:18 | +18.84 | +0.06 | `take_profit` |
| 4 | 2025-06-30T19:20 | 2025-06-30T19:57 | +24.83 | +0.07 | `take_profit` |
| 5 | 2025-07-02T18:15 | 2025-07-02T18:57 | +21.82 | +0.06 | `take_profit` |
| 6 | 2025-07-02T19:00 | 2025-07-02T19:06 | +18.82 | +0.06 | `take_profit` |
| 7 | 2025-07-02T20:00 | 2025-07-02T20:07 | +17.82 | +0.05 | `take_profit` |
| 8 | 2025-07-07T16:25 | 2025-07-07T16:25 | +22.83 | +0.07 | `take_profit` |
| 9 | 2025-07-09T16:50 | 2025-07-09T19:04 | +22.83 | +0.07 | `take_profit` |
| 10 | 2025-07-09T19:05 | 2025-07-09T22:16 | +21.83 | +0.07 | `take_profit` |
| 11 | 2025-07-16T15:00 | 2025-07-16T15:01 | +39.83 | +0.12 | `take_profit` |
| 12 | 2025-07-16T15:05 | 2025-07-16T15:05 | +39.82 | +0.12 | `take_profit` |
| 13 | 2025-07-21T19:15 | 2025-07-21T19:23 | +17.80 | +0.05 | `take_profit` |
| 14 | 2025-08-01T19:35 | 2025-08-01T19:38 | +26.80 | +0.08 | `take_profit` |
| 15 | 2025-08-01T19:40 | 2025-08-01T20:32 | +26.80 | +0.08 | `take_profit` |
| 16 | 2025-08-05T16:35 | 2025-08-06T00:20 | +25.79 | +0.08 | `take_profit` |
| 17 | 2025-08-07T19:35 | 2025-08-07T19:38 | +22.78 | +0.07 | `take_profit` |
| 18 | 2025-08-13T14:05 | 2025-08-13T14:07 | +29.80 | +0.09 | `take_profit` |

**Straty za sebou: 4** — 2023-08-29T14:10 až 2023-09-08T14:21, spolu -93.75, rovnako dlhých sérií 3.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-08-29T14:10 | 2023-08-29T14:13 | -26.69 | -0.14 | `stop_loss` |
| 2 | 2023-08-29T20:00 | 2023-08-29T23:16 | -16.69 | -0.08 | `stop_loss` |
| 3 | 2023-08-31T14:05 | 2023-08-31T14:34 | -26.69 | -0.14 | `stop_loss` |
| 4 | 2023-09-08T14:05 | 2023-09-08T14:21 | -23.69 | -0.12 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0114 %**, medián 0.0114 %, 90 % interval 0.0063–0.0165 %
- P(edge > poplatok) = **99.9 %**
- max drawdown: medián 1.0 %, 95. percentil 1.8 %, najhorší 3.7 %
- najdlhšia séria strát: medián 4, 95. percentil 5 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

> **Posudok je starší než čísla** (písal sa k vzorke `ec6563ed`, tu je `dc78bf42`). Nech ho AI prepíše — čísla nižšie sa medzitým zmenili.

<!-- POSUDOK cisla=ec6563ed -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na MGC, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Prieraz stlačeného IB 9:30–10:00 NY pri náraste objemu; index futures 5m. Tu na MGC (zlato) — logika robená pre index, čísla to treba brať ako test prenosu.
2. **Má potenciál?** Zisková v 3 z 5 okien, 550 obchodov (~110 za rok), break-even 0.0041 % (nad poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 62.36 % pri payoffe 0.621. Odložený rok 25/26: -8.32 % PnL, break-even -0.0066 %. Kladné okná sú skôr vlastnosť vzorky ako stabilný jav.
3. **Čo dorobiť.** Dve zvláštnosti predlohy (pokus aj bez prierazu, IB do priemeru na 10:00–10:04) ako prepínače; koniec dňa pre prop.
4. **Čo otestovať ďalej.** Smernica (`ivb*`: pomer IB, objem, stop / cieľ v ATR, okno vstupu, TF).
5. **Použiteľné?** **V defaultoch predlohy nie** — edge nad poplatkom nie je stabilný po rokoch; šancu má len s nastavením, ktoré nájde smernica (inak vyradiť).
6. **Čo by som pridal.** Smer dňa (VWAP od 9:30) a cieľ ≥ 1 R namiesto 0,67 R.

<!-- POSUDOK KONIEC -->
