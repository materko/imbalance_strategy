# Základná analytika — NQ PRECISION 1.0 (`nqprec`)

Zmerané 2026-11-05 na `MNQ/USD` 2m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/nqprec_PRESIEL_SMERNICAMI_NQ_PRECISION_MNQ_1_2026-11-05.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy nqprec \
   --profile .nightsearch/checkup/nqprec_PRESIEL_SMERNICAMI_NQ_PRECISION_MNQ_1_2026-11-05.json \
   --pair MNQ/USD \
   --timeframe 2m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 923 obchodov spolu — na štatistiku dosť
- break-even 0.0082 % je nad poplatkom 0.0018 % (rezerva +0.0064 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 2.3 %
- odlíšiteľná od náhody (+8.3 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 64. percentile toho, čo stratégia vyrobí sama od seba)
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- proti náhode v tých istých hodinách je rozdiel podstatne menší (+5.7 vs +8.3 sigma) — veľká časť edge je v tom, KEDY obchoduje, nie v tom, čo si vyberá
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 184 | +0.94 | 0.0073 | 1.0 | 91.8 | +52/-1 | `20261105-051423-703fcc` |
| 20221001-20231001 | 184 | +0.19 | 0.0030 | 0.9 | 90.8 | +53/-3 | `20261105-051426-5e2c19` |
| 20231001-20241001 | 189 | +0.76 | 0.0051 | 0.9 | 92.1 | +32/-2 | `20261105-051429-452475` |
| 20240904-20250904 | 201 | +3.36 | 0.0136 | 0.7 | 95.5 | +47/-2 | `20261105-051432-9eb5e6` |
| 20250904-20260904 | 182 | +2.50 | 0.0095 | 0.9 | 93.4 | +47/-1 | `20261105-051436-5ff2f3` |

Zisková v **5 z 5** okien, obchodov spolu 923, break-even celkom 0.0082 %. Okná sa prekrývajú, 17 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+0.61 ATR za 5 barov)
- medián držania 0.5 barov grafu
- winrate 92.63 %, payoff 0.119
- 0.51 obchodov za deň
- šikmosť výnosov -3.898

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 92.6 %, `stop_loss` 7.4 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0068 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 868 | 94.0 % | 92.5 | 0.0077 | 0.0150 | +0.0068 |
| proti trendu | 55 | 6.0 % | 94.5 | 0.0150 | 0.0077 | -0.0005 |

**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bežný deň | 858 | 93.0 % | 92.5 | 0.0079 | 0.0114 | +0.0032 |
| deň po sviatku | 21 | 2.3 % | 90.5 | 0.0138 | 0.0080 | -0.0002 |
| deň pred sviatkom | 14 | 1.5 % | 100.0 | 0.0193 | 0.0080 | -0.0002 |

**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| FOMC | 25 | 2.7 % | 92.0 | -0.0004 | 0.0084 | +0.0002 |
| žiadna | 824 | 89.3 % | 92.5 | 0.0078 | 0.0110 | +0.0028 |
| NFP | 41 | 4.4 % | 92.7 | 0.0098 | 0.0081 | -0.0001 |
| CPI | 32 | 3.5 % | 96.9 | 0.0206 | 0.0077 | -0.0005 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0082 % | -0.0001 % ± 0.0010 | +8.28 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0082 % | -0.0001 % ± 0.0015 | +5.65 | 100.0 |

Edge je odlisitelny od nahody (8.3 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 227 | 15.4 | 92.1 | 0.0072 | 40 |
| 2022-12 - 2024-03 | 224 | 15.2 | 91.5 | 0.0042 | 18 |
| 2024-03 - 2025-06 | 242 | 16.4 | 93.0 | 0.0096 | 65 |
| 2025-06 - 2026-09 | 230 | 15.6 | 93.9 | 0.0097 | 64 |

Hranice pre úsek veľkosti posledného obdobia: +0.0011 až +0.0148 % (medián 0.0084).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 64. percentile, teda v medziach +0.0011 až +0.0148 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 53** — 2022-11-07T14:58 až 2023-02-15T15:11, spolu +757.14.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-11-07T14:58 | 2022-11-07T14:59 | +48.24 | +0.22 | `take_profit` |
| 2 | 2022-11-08T15:26 | 2022-11-08T15:27 | +10.72 | +0.05 | `take_profit` |
| 3 | 2022-11-10T14:56 | 2022-11-10T14:57 | +17.20 | +0.08 | `take_profit` |
| 4 | 2022-11-11T15:26 | 2022-11-11T15:27 | +32.18 | +0.14 | `take_profit` |
| 5 | 2022-11-14T15:24 | 2022-11-14T15:34 | +11.17 | +0.05 | `take_profit` |
| 6 | 2022-11-16T14:58 | 2022-11-16T14:59 | +10.67 | +0.05 | `take_profit` |
| 7 | 2022-11-17T14:52 | 2022-11-17T15:15 | +9.18 | +0.04 | `take_profit` |
| 8 | 2022-11-18T14:50 | 2022-11-18T15:00 | +7.68 | +0.03 | `take_profit` |
| 9 | 2022-11-21T15:14 | 2022-11-21T15:15 | +17.18 | +0.07 | `take_profit` |
| 10 | 2022-11-22T14:54 | 2022-11-22T14:55 | +7.19 | +0.03 | `take_profit` |
| 11 | 2022-11-23T15:14 | 2022-11-23T15:15 | +9.17 | +0.04 | `take_profit` |
| 12 | 2022-11-28T15:54 | 2022-11-28T15:58 | +6.18 | +0.03 | `take_profit` |
| 13 | 2022-11-29T14:57 | 2022-11-29T15:13 | +7.69 | +0.03 | `take_profit` |
| 14 | 2022-12-01T14:50 | 2022-12-01T14:51 | +19.65 | +0.08 | `take_profit` |
| 15 | 2022-12-02T15:17 | 2022-12-02T15:34 | +11.66 | +0.05 | `take_profit` |
| 16 | 2022-12-05T15:04 | 2022-12-05T15:05 | +3.66 | +0.02 | `take_profit` |
| 17 | 2022-12-06T15:16 | 2022-12-06T15:38 | +8.68 | +0.04 | `take_profit` |
| 18 | 2022-12-07T15:02 | 2022-12-07T15:10 | +11.19 | +0.05 | `take_profit` |
| 19 | 2022-12-08T15:16 | 2022-12-08T15:25 | +9.68 | +0.04 | `take_profit` |
| 20 | 2022-12-12T15:19 | 2022-12-12T15:20 | +16.68 | +0.07 | `take_profit` |
| 21 | 2022-12-16T15:08 | 2022-12-16T15:09 | +11.20 | +0.05 | `take_profit` |
| 22 | 2022-12-19T15:04 | 2022-12-19T15:05 | +7.21 | +0.03 | `take_profit` |
| 23 | 2022-12-20T15:16 | 2022-12-20T15:18 | +12.21 | +0.05 | `take_profit` |
| 24 | 2022-12-21T15:16 | 2022-12-21T15:19 | +9.21 | +0.04 | `take_profit` |
| 25 | 2022-12-22T14:46 | 2022-12-22T15:01 | +7.72 | +0.03 | `take_profit` |
| 26 | 2022-12-23T14:52 | 2022-12-23T14:55 | +14.73 | +0.07 | `take_profit` |
| 27 | 2022-12-27T15:12 | 2022-12-27T15:13 | +23.23 | +0.11 | `take_profit` |
| 28 | 2022-12-28T15:56 | 2022-12-28T15:57 | +9.24 | +0.04 | `take_profit` |
| 29 | 2022-12-30T15:51 | 2022-12-30T15:52 | +7.23 | +0.03 | `take_profit` |
| 30 | 2023-01-04T15:24 | 2023-01-04T15:25 | +14.24 | +0.07 | `take_profit` |
| 31 | 2023-01-05T14:48 | 2023-01-05T14:49 | +9.24 | +0.04 | `take_profit` |
| 32 | 2023-01-06T14:50 | 2023-01-06T14:51 | +17.24 | +0.08 | `take_profit` |
| 33 | 2023-01-09T15:08 | 2023-01-09T15:09 | +9.21 | +0.04 | `take_profit` |
| 34 | 2023-01-10T15:15 | 2023-01-10T15:16 | +16.71 | +0.07 | `take_profit` |
| 35 | 2023-01-11T15:11 | 2023-01-11T15:12 | +9.70 | +0.04 | `take_profit` |
| 36 | 2023-01-13T14:53 | 2023-01-13T14:54 | +8.70 | +0.04 | `take_profit` |
| 37 | 2023-01-18T15:02 | 2023-01-18T15:03 | +9.18 | +0.04 | `take_profit` |
| 38 | 2023-01-19T14:56 | 2023-01-19T14:57 | +10.70 | +0.05 | `take_profit` |
| 39 | 2023-01-20T15:17 | 2023-01-20T15:19 | +8.70 | +0.04 | `take_profit` |
| 40 | 2023-01-24T15:32 | 2023-01-24T15:33 | +11.66 | +0.05 | `take_profit` |
| 41 | 2023-01-25T15:16 | 2023-01-25T15:24 | +9.18 | +0.04 | `take_profit` |
| 42 | 2023-01-27T14:56 | 2023-01-27T15:01 | +8.15 | +0.03 | `take_profit` |
| 43 | 2023-01-30T15:25 | 2023-01-30T15:26 | +20.65 | +0.09 | `take_profit` |
| 44 | 2023-01-31T15:20 | 2023-01-31T15:22 | +14.15 | +0.06 | `take_profit` |
| 45 | 2023-02-01T15:58 | 2023-02-01T15:59 | +7.65 | +0.03 | `take_profit` |
| 46 | 2023-02-02T15:26 | 2023-02-02T15:27 | +14.61 | +0.06 | `take_profit` |
| 47 | 2023-02-03T14:50 | 2023-02-03T14:51 | +77.11 | +0.30 | `take_profit` |
| 48 | 2023-02-06T15:22 | 2023-02-06T15:23 | +13.12 | +0.05 | `take_profit` |
| 49 | 2023-02-07T15:47 | 2023-02-07T15:48 | +11.12 | +0.04 | `take_profit` |
| 50 | 2023-02-08T15:26 | 2023-02-08T15:27 | +19.11 | +0.08 | `take_profit` |
| 51 | 2023-02-13T15:18 | 2023-02-13T15:19 | +29.63 | +0.12 | `take_profit` |
| 52 | 2023-02-14T14:52 | 2023-02-14T14:54 | +18.62 | +0.07 | `take_profit` |
| 53 | 2023-02-15T15:10 | 2023-02-15T15:11 | +11.12 | +0.04 | `take_profit` |

**Straty za sebou: 3** — 2023-07-21T14:40 až 2023-07-27T14:07, spolu -283.31.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-07-21T14:40 | 2023-07-21T15:09 | -127.09 | -0.41 | `stop_loss` |
| 2 | 2023-07-25T14:25 | 2023-07-25T14:31 | -82.60 | -0.26 | `stop_loss` |
| 3 | 2023-07-27T13:54 | 2023-07-27T14:07 | -73.61 | -0.23 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0082 %**, medián 0.0082 %, 90 % interval 0.0048–0.0115 %
- P(edge > poplatok) = **99.9 %**
- max drawdown: medián 1.3 %, 95. percentil 2.3 %, najhorší 5.3 %
- najdlhšia séria strát: medián 3, 95. percentil 3 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

> **Posudok je starší než čísla** (písal sa k vzorke `7ddfe4dd`, tu je `234ae0a7`). Nech ho AI prepíše — čísla nižšie sa medzitým zmenili.

<!-- POSUDOK cisla=7ddfe4dd -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na MNQ, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Jedna snímka denne o 10:00 NY, cieľ 0,3 ATR a stop 2,2 ATR — skalp s WR ~85–90 %, ktorý žije z toho, že jedna strata nezožerie 7 výhier.
2. **Má potenciál?** Zisková v 3 z 5 okien, 468 obchodov (~94 za rok), break-even 0.0038 % (nad poplatkom 0,0018 %), +3.3 sigma proti náhodnému vstupu; WR 88.89 % pri payoffe 0.15. Odložený rok 25/26: -1.77 % PnL, break-even 0.0002 %. Kladné okná sú skôr vlastnosť vzorky ako stabilný jav.
3. **Čo dorobiť.** Predloha je tickova (9:59:55); na 1m sa vstupuje o 5 s neskôr — overiť na 1m, či sa to neoplatí posunúť na 9:59. Pomer cieľ / stop 0,14 je na hrane: pri poplatku a sklze rozhoduje každý tick.
4. **Čo otestovať ďalej.** Smernica (`nqprec*`: stop / cieľ v ATR, výstup v čase, čas snímky, filtre); hlavne 2× poplatok a sklz (krok 9) — pri payoffe 0,15 je to rozhodujúce.
5. **Použiteľné?** **V defaultoch predlohy nie** — edge nad poplatkom nie je stabilný po rokoch; šancu má len s nastavením, ktoré nájde smernica (inak vyradiť).
6. **Čo by som pridal.** Cieľ aspoň 0,5 ATR a stop 1 ATR (payoff ~0,5), alebo vstup len v smere včerajška / overnightu.

<!-- POSUDOK KONIEC -->
