# Základná analytika — IVB 1.0 (ES) (`ivbes`)

Zmerané 2026-11-07 na `ES/USD` 15m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/ivbes_PRESIEL_SMERNICAMI_IVB_ES_1_2026-11-07.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy ivbes \
   --profile .nightsearch/checkup/ivbes_PRESIEL_SMERNICAMI_IVB_ES_1_2026-11-07.json \
   --pair ES/USD \
   --timeframe 15m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 799 obchodov spolu — na štatistiku dosť
- break-even 0.0165 % je nad poplatkom 0.0018 % (rezerva +0.0147 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 15.6 %
- odlíšiteľná od náhody (+6.7 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 34. percentile toho, čo stratégia vyrobí sama od seba)
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- proti náhode v tých istých hodinách je rozdiel podstatne menší (+5.4 vs +6.7 sigma) — veľká časť edge je v tom, KEDY obchoduje, nie v tom, čo si vyberá
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 147 | +40.35 | 0.0404 | 2.9 | 97.3 | +93/-1 | `20261107-051933-5b4483` |
| 20221001-20231001 | 174 | +9.38 | 0.0096 | 4.7 | 90.8 | +23/-1 | `20261107-051936-d710c5` |
| 20231001-20241001 | 169 | +14.08 | 0.0116 | 8.1 | 91.1 | +26/-2 | `20261107-051940-9a7955` |
| 20240904-20250904 | 170 | +19.15 | 0.0131 | 11.6 | 90.6 | +30/-1 | `20261107-051943-a20919` |
| 20250904-20260904 | 152 | +24.31 | 0.0153 | 6.8 | 93.4 | +36/-1 | `20261107-051946-4b5e4f` |

Zisková v **5 z 5** okien, obchodov spolu 799, break-even celkom 0.0165 %. Okná sa prekrývajú, 13 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.66 ATR za 5 barov)
- medián držania 0.7 barov grafu
- winrate 92.62 %, payoff 0.137
- 0.44 obchodov za deň
- šikmosť výnosov -3.018

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 92.6 %, `stop_loss` 7.4 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0058 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.416 % | 200 | 25.0 % | 90.0 | 0.0009 | 0.0223 | +0.0058 |
| 0.416 % – 0.5453 % | 200 | 25.0 % | 92.5 | 0.0101 | 0.0188 | +0.0023 |
| 0.5453 % – 0.7895 % | 200 | 25.0 % | 91.5 | 0.0117 | 0.0181 | +0.0016 |
| nad 0.7895 % | 199 | 24.9 % | 96.5 | 0.0484 | 0.0074 | -0.0091 |

**Plánovaný RR**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.12 R | 473 | 59.2 % | 92.4 | 0.0135 | 0.0208 | +0.0043 |
| nad 0.13 R | 65 | 8.1 % | 95.4 | 0.0205 | 0.0162 | -0.0003 |
| 0.12 R – 0.13 R | 261 | 32.7 % | 92.3 | 0.0209 | 0.0143 | -0.0022 |

**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.2095 – 0.3016 | 200 | 25.0 % | 91.0 | 0.0046 | 0.0205 | +0.0040 |
| do 0.1247 | 200 | 25.0 % | 90.5 | 0.0148 | 0.0171 | +0.0006 |
| nad 0.3016 | 199 | 24.9 % | 95.5 | 0.0218 | 0.0147 | -0.0018 |
| 0.1247 – 0.2095 | 200 | 25.0 % | 93.5 | 0.0247 | 0.0138 | -0.0027 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0165 % | -0.0003 % ± 0.0025 | +6.69 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0165 % | -0.0003 % ± 0.0031 | +5.39 | 100.0 |

Edge je odlisitelny od nahody (6.7 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 188 | 12.8 | 96.3 | 0.0373 | 100 |
| 2022-12 - 2024-03 | 206 | 14.0 | 89.3 | 0.0020 | 3 |
| 2024-03 - 2025-06 | 215 | 14.6 | 92.6 | 0.0170 | 51 |
| 2025-06 - 2026-09 | 190 | 12.9 | 92.6 | 0.0136 | 34 |

Hranice pre úsek veľkosti posledného obdobia: +0.0044 až +0.0288 % (medián 0.0166).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 34. percentile, teda v medziach +0.0044 až +0.0288 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 93** — 2021-10-01T18:00 až 2022-05-31T16:02, spolu +21543.83.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2021-10-01T18:00 | 2021-10-01T18:05 | +242.38 | +0.11 | `take_profit` |
| 2 | 2021-10-04T14:45 | 2021-10-04T14:46 | +204.96 | +0.10 | `take_profit` |
| 3 | 2021-10-04T15:00 | 2021-10-04T15:01 | +217.48 | +0.10 | `take_profit` |
| 4 | 2021-10-06T17:45 | 2021-10-06T18:05 | +267.40 | +0.12 | `take_profit` |
| 5 | 2021-10-18T15:30 | 2021-10-18T15:35 | +117.15 | +0.05 | `take_profit` |
| 6 | 2021-10-22T15:45 | 2021-10-22T15:47 | +117.07 | +0.05 | `take_profit` |
| 7 | 2021-10-25T15:30 | 2021-10-25T15:53 | +79.51 | +0.03 | `take_profit` |
| 8 | 2021-10-25T16:15 | 2021-10-25T16:28 | +92.00 | +0.04 | `take_profit` |
| 9 | 2021-10-28T15:00 | 2021-10-28T15:07 | +91.96 | +0.04 | `take_profit` |
| 10 | 2021-10-29T18:00 | 2021-10-29T19:47 | +104.44 | +0.05 | `take_profit` |
| 11 | 2021-11-10T18:30 | 2021-11-10T18:39 | +104.33 | +0.04 | `take_profit` |
| 12 | 2021-11-12T16:15 | 2021-11-12T16:15 | +66.81 | +0.03 | `take_profit` |
| 13 | 2021-11-12T16:30 | 2021-11-12T16:30 | +79.30 | +0.03 | `take_profit` |
| 14 | 2021-11-15T17:00 | 2021-11-15T17:00 | +54.30 | +0.02 | `take_profit` |
| 15 | 2021-11-16T16:30 | 2021-11-16T16:35 | +79.25 | +0.03 | `take_profit` |
| 16 | 2021-11-16T18:00 | 2021-11-16T18:04 | +91.74 | +0.04 | `take_profit` |
| 17 | 2021-11-19T17:30 | 2021-11-19T17:36 | +116.73 | +0.05 | `take_profit` |
| 18 | 2021-11-24T18:15 | 2021-11-24T20:09 | +154.26 | +0.07 | `take_profit` |
| 19 | 2021-11-26T16:30 | 2021-11-26T16:54 | +254.44 | +0.11 | `take_profit` |
| 20 | 2021-11-30T16:15 | 2021-11-30T16:21 | +279.44 | +0.12 | `take_profit` |
| 21 | 2021-12-01T18:15 | 2021-12-01T18:17 | +216.93 | +0.09 | `take_profit` |
| 22 | 2021-12-02T18:15 | 2021-12-02T19:29 | +341.95 | +0.15 | `take_profit` |
| 23 | 2021-12-03T16:00 | 2021-12-03T16:05 | +267.07 | +0.12 | `take_profit` |
| 24 | 2021-12-06T18:15 | 2021-12-06T18:25 | +229.43 | +0.10 | `take_profit` |
| 25 | 2021-12-06T18:45 | 2021-12-06T19:03 | +254.41 | +0.11 | `take_profit` |
| 26 | 2021-12-16T19:30 | 2021-12-16T19:45 | +291.82 | +0.13 | `take_profit` |
| 27 | 2021-12-21T17:00 | 2021-12-21T17:03 | +166.91 | +0.07 | `take_profit` |
| 28 | 2021-12-21T17:30 | 2021-12-21T17:48 | +216.89 | +0.09 | `take_profit` |
| 29 | 2021-12-21T19:00 | 2021-12-21T19:03 | +166.87 | +0.07 | `take_profit` |
| 30 | 2021-12-22T19:15 | 2021-12-22T19:41 | +141.81 | +0.06 | `take_profit` |
| 31 | 2021-12-27T18:45 | 2021-12-27T18:56 | +91.63 | +0.04 | `take_profit` |
| 32 | 2022-01-04T16:15 | 2022-01-04T16:15 | +104.11 | +0.04 | `take_profit` |
| 33 | 2022-01-07T16:00 | 2022-01-07T16:17 | +179.32 | +0.08 | `take_profit` |
| 34 | 2022-01-11T18:45 | 2022-01-11T19:42 | +229.27 | +0.10 | `take_profit` |
| 35 | 2022-01-13T17:30 | 2022-01-13T17:30 | +154.28 | +0.07 | `take_profit` |
| 36 | 2022-01-13T17:45 | 2022-01-13T17:47 | +154.28 | +0.07 | `take_profit` |
| 37 | 2022-01-14T18:15 | 2022-01-14T18:20 | +229.40 | +0.10 | `take_profit` |
| 38 | 2022-01-18T19:15 | 2022-01-18T20:16 | +229.47 | +0.10 | `take_profit` |
| 39 | 2022-01-27T17:30 | 2022-01-27T17:31 | +429.86 | +0.20 | `take_profit` |
| 40 | 2022-01-27T17:45 | 2022-01-27T17:46 | +442.39 | +0.20 | `take_profit` |
| 41 | 2022-02-04T19:00 | 2022-02-04T20:00 | +292.08 | +0.13 | `take_profit` |
| 42 | 2022-02-07T17:00 | 2022-02-07T17:00 | +167.13 | +0.07 | `take_profit` |
| 43 | 2022-02-08T18:00 | 2022-02-08T20:34 | +154.58 | +0.07 | `take_profit` |
| 44 | 2022-02-11T18:45 | 2022-02-11T18:46 | +542.23 | +0.24 | `take_profit` |
| 45 | 2022-02-18T18:00 | 2022-02-18T18:18 | +292.41 | +0.14 | `take_profit` |
| 46 | 2022-02-22T17:45 | 2022-02-22T17:48 | +292.45 | +0.14 | `take_profit` |
| 47 | 2022-02-23T18:15 | 2022-02-23T18:30 | +255.02 | +0.12 | `take_profit` |
| 48 | 2022-02-28T16:00 | 2022-02-28T16:18 | +379.84 | +0.17 | `take_profit` |
| 49 | 2022-03-01T17:00 | 2022-03-01T17:08 | +317.46 | +0.15 | `take_profit` |
| 50 | 2022-03-01T18:30 | 2022-03-01T20:49 | +354.98 | +0.17 | `take_profit` |
| 51 | 2022-03-02T16:30 | 2022-03-02T16:31 | +342.32 | +0.16 | `take_profit` |
| 52 | 2022-03-07T18:00 | 2022-03-07T18:16 | +342.58 | +0.16 | `take_profit` |
| 53 | 2022-03-08T17:30 | 2022-03-08T17:38 | +467.55 | +0.22 | `take_profit` |
| 54 | 2022-03-08T18:00 | 2022-03-08T18:02 | +455.02 | +0.21 | `take_profit` |
| 55 | 2022-03-11T17:00 | 2022-03-11T17:03 | +317.57 | +0.15 | `take_profit` |
| 56 | 2022-03-11T19:15 | 2022-03-11T19:45 | +267.58 | +0.13 | `take_profit` |
| 57 | 2022-03-14T16:30 | 2022-03-14T16:35 | +242.65 | +0.12 | `take_profit` |
| 58 | 2022-03-15T16:45 | 2022-03-15T18:50 | +305.07 | +0.14 | `take_profit` |
| 59 | 2022-03-17T16:45 | 2022-03-17T17:22 | +242.33 | +0.11 | `take_profit` |
| 60 | 2022-03-17T17:45 | 2022-03-17T17:52 | +242.30 | +0.11 | `take_profit` |
| 61 | 2022-03-18T18:15 | 2022-03-18T18:18 | +217.22 | +0.10 | `take_profit` |
| 62 | 2022-03-23T17:45 | 2022-03-23T19:41 | +154.68 | +0.07 | `take_profit` |
| 63 | 2022-03-24T15:30 | 2022-03-24T15:41 | +229.61 | +0.10 | `take_profit` |
| 64 | 2022-03-28T16:00 | 2022-03-28T16:17 | +167.08 | +0.07 | `take_profit` |
| 65 | 2022-04-05T18:00 | 2022-04-05T18:04 | +167.04 | +0.07 | `take_profit` |
| 66 | 2022-04-08T15:15 | 2022-04-08T16:21 | +167.08 | +0.07 | `take_profit` |
| 67 | 2022-04-12T16:45 | 2022-04-12T17:40 | +217.24 | +0.10 | `take_profit` |
| 68 | 2022-04-12T18:00 | 2022-04-12T18:15 | +292.27 | +0.13 | `take_profit` |
| 69 | 2022-04-13T16:45 | 2022-04-13T18:50 | +267.21 | +0.12 | `take_profit` |
| 70 | 2022-04-19T18:30 | 2022-04-19T18:39 | +142.21 | +0.06 | `take_profit` |
| 71 | 2022-04-21T16:15 | 2022-04-21T16:23 | +167.19 | +0.08 | `take_profit` |
| 72 | 2022-04-21T17:15 | 2022-04-21T17:17 | +204.73 | +0.09 | `take_profit` |
| 73 | 2022-04-22T16:15 | 2022-04-22T17:02 | +229.94 | +0.11 | `take_profit` |
| 74 | 2022-04-22T18:15 | 2022-04-22T18:49 | +317.47 | +0.15 | `take_profit` |
| 75 | 2022-04-26T14:45 | 2022-04-26T15:05 | +205.11 | +0.10 | `take_profit` |
| 76 | 2022-04-28T16:30 | 2022-04-28T16:35 | +267.56 | +0.13 | `take_profit` |
| 77 | 2022-04-28T16:45 | 2022-04-28T16:46 | +255.03 | +0.12 | `take_profit` |
| 78 | 2022-04-28T17:00 | 2022-04-28T17:07 | +267.51 | +0.13 | `take_profit` |
| 79 | 2022-04-29T17:00 | 2022-04-29T18:01 | +280.16 | +0.13 | `take_profit` |
| 80 | 2022-05-02T17:15 | 2022-05-02T17:17 | +317.80 | +0.15 | `take_profit` |
| 81 | 2022-05-03T15:30 | 2022-05-03T15:33 | +267.65 | +0.13 | `take_profit` |
| 82 | 2022-05-05T15:00 | 2022-05-05T15:02 | +267.68 | +0.13 | `take_profit` |
| 83 | 2022-05-10T15:00 | 2022-05-10T15:03 | +293.00 | +0.15 | `take_profit` |
| 84 | 2022-05-10T15:30 | 2022-05-10T15:30 | +255.52 | +0.13 | `take_profit` |
| 85 | 2022-05-16T17:45 | 2022-05-16T18:25 | +305.42 | +0.15 | `take_profit` |
| 86 | 2022-05-18T15:30 | 2022-05-18T15:30 | +193.03 | +0.10 | `take_profit` |
| 87 | 2022-05-18T15:45 | 2022-05-18T15:45 | +218.01 | +0.11 | `take_profit` |
| 88 | 2022-05-18T17:30 | 2022-05-18T17:43 | +255.58 | +0.13 | `take_profit` |
| 89 | 2022-05-20T15:15 | 2022-05-20T15:16 | +243.22 | +0.13 | `take_profit` |
| 90 | 2022-05-20T15:30 | 2022-05-20T15:38 | +243.22 | +0.13 | `take_profit` |
| 91 | 2022-05-23T18:00 | 2022-05-23T18:44 | +355.53 | +0.18 | `take_profit` |
| 92 | 2022-05-26T15:30 | 2022-05-26T15:31 | +217.90 | +0.11 | `take_profit` |
| 93 | 2022-05-31T16:00 | 2022-05-31T16:02 | +267.71 | +0.13 | `take_profit` |

**Straty za sebou: 2** — 2024-01-17T19:15 až 2024-01-18T19:15, spolu -2354.26.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-01-17T19:15 | 2024-01-18T09:40 | -1220.86 | -0.51 | `stop_loss` |
| 2 | 2024-01-18T18:30 | 2024-01-18T19:15 | -1133.40 | -0.47 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0165 %**, medián 0.0166 %, 90 % interval 0.0106–0.0223 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 8.4 %, 95. percentil 15.6 %, najhorší 34.1 %
- najdlhšia séria strát: medián 2, 95. percentil 2 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

> **Posudok je starší než čísla** (písal sa k vzorke `4444a3c3`, tu je `a0b9fb16`). Nech ho AI prepíše — čísla nižšie sa medzitým zmenili.

<!-- POSUDOK cisla=4444a3c3 -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na ES, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Prieraz stlačeného IB 9:30–10:00 NY pri náraste objemu; index futures 5m. Tu na ES — rovnaká logika ako MNQ, prahy v ATR sa prispôsobia.
2. **Má potenciál?** Zisková v 5 z 5 okien, 559 obchodov (~112 za rok), break-even 0.0137 % (nad poplatkom 0,0018 %), +3.3 sigma proti náhodnému vstupu; WR 64.76 % pri payoffe 0.665. Odložený rok 25/26: +44.67 % PnL, break-even 0.0077 %. Jav je skôr skutočný ako vlastnosť vzorky.
3. **Čo dorobiť.** Dve zvláštnosti predlohy (pokus aj bez prierazu, IB do priemeru na 10:00–10:04) ako prepínače; koniec dňa pre prop.
4. **Čo otestovať ďalej.** Smernica (`ivb*`: pomer IB, objem, stop / cieľ v ATR, okno vstupu, TF).
5. **Použiteľné?** **Áno ako kandidát do smernice** — defaulty predlohy sú ziskové vo väčšine okien a edge je nad poplatkom; rozhodne hľadanie a odložený rok.
6. **Čo by som pridal.** Smer dňa (VWAP od 9:30) a cieľ ≥ 1 R namiesto 0,67 R.

<!-- POSUDOK KONIEC -->
