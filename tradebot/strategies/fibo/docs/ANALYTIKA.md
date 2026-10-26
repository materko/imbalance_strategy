# Základná analytika — Fibo 1.0 (`fibo`)

Zmerané 2026-10-26 na `MNQ/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/fibo/configs/mnq_databento_5m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy fibo \
   --profile tradebot/strategies/fibo/configs/mnq_databento_5m.json \
   --pair MNQ/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 580 obchodov spolu — na štatistiku dosť
- drawdown drží: 95. percentil 9.9 %
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 1 z 5 referenčných okien (20221001-20231001, 20231001-20241001, 20240904-20250904, 20250904-20260904 v strate)
- break-even -0.0010 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 28 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- nie je lepšia než náhodný vstup za tých istých pravidiel (-0.2 sigma) — výber vstupu nepridáva nič
- charakter: protitrendová (mean reversion) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 112 | +0.27 | 0.0039 | 1.1 | 42.9 | +5/-6 | `20261026-131034-7fc335` |
| 20221001-20231001 | 165 | -0.39 | -0.0004 | 2.5 | 43.0 | +5/-10 | `20261026-131040-9e781c` |
| 20231001-20241001 | 153 | -2.08 | -0.0074 | 2.4 | 41.2 | +5/-11 | `20261026-131046-95704e` |
| 20240904-20250904 | 101 | -0.21 | 0.0005 | 2.3 | 41.6 | +4/-7 | `20261026-131052-f99e6c` |
| 20250904-20260904 | 54 | -0.12 | 0.0005 | 1.0 | 37.0 | +3/-6 | `20261026-131058-f51760` |

Zisková v **1 z 5** okien, obchodov spolu 580, break-even celkom -0.0010 %. Okná sa prekrývajú, 5 obchodov započítaných dvakrát vypadlo.

## Charakter

**Protitrendová (mean reversion)** (istota priemerná)

- vstup proti poslednému pohybu (-0.30 ATR za 5 barov)
- medián držania 25 barov grafu
- winrate 41.9 %, payoff 1.32
- 0.34 obchodov za deň
- šikmosť výnosov +0.66

- **Čo je normálne:** Winrate nad 60 % a payoff pod 1 je pri tomto type v poriadku — zarába sa frekvenciou, nie veľkosťou.
- **Na čo pozor:** Jedna strata môže zmazať mesiac. Stop je tu dôležitejší než vstup a `maxLossDollar` aj drawdown limit majú väčší význam než pri ostatných typoch.
- **Čo ladiť:** Stop a filter režimu (v trende protitrendová stratégia dostáva rany). Ladiť RR nahor väčšinou len zníži winrate a nič nepridá.

Výstupy: `stop_loss` 58.1 %, `take_profit` 41.9 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0070 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**S trendom, alebo proti** (riadi `requireBreak`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 432 | 74.5 % | 44.0 | -0.0036 | 0.0060 | +0.0070 |
| proti trendu | 148 | 25.5 % | 35.8 | 0.0060 | -0.0036 | -0.0026 |

**Smer** (riadi `tradeDirection`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| short | 293 | 50.5 % | 38.6 | -0.0071 | 0.0053 | +0.0063 |
| long | 287 | 49.5 % | 45.3 | 0.0053 | -0.0071 | -0.0061 |

**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.0886 – 0.1472 | 146 | 25.2 % | 37.7 | -0.0195 | 0.0052 | +0.0062 |
| do 0.0429 | 146 | 25.2 % | 36.3 | -0.0016 | -0.0007 | +0.0003 |
| 0.0429 – 0.0886 | 145 | 25.0 % | 41.4 | 0.0044 | -0.0028 | -0.0018 |
| nad 0.1472 | 143 | 24.7 % | 52.5 | 0.0137 | -0.0054 | -0.0044 |

Parametre, ktorými sa dá s tým niečo spraviť: `maxHoldBars`, `requireBreak`, `rrRatio`, `slBufferAtr`, `tradeDirection`, `tradeStartH`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0006 % | 0.0003 % ± 0.0055 | -0.17 | 43.7 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0006 % | 0.0003 % ± 0.0055 | -0.17 | 43.7 |

Neodlisitelne od nahody (-0.2 sigma, percentil 43.7). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-11 | 128 | 9.2 | 44.5 | 0.0080 | 82 |
| 2022-11 - 2024-01 | 205 | 14.7 | 39.5 | -0.0115 | 8 |
| 2024-01 - 2025-03 | 155 | 11.1 | 43.9 | 0.0001 | 53 |
| 2025-03 - 2026-05 | 92 | 6.6 | 40.2 | 0.0057 | 71 |

Hranice pre úsek veľkosti posledného obdobia: -0.0206 až +0.0192 % (medián -0.0010).

**DRZI** — posledné obdobie (2025-03 - 2026-05) je na 71. percentile, teda v medziach -0.0206 až +0.0192 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 5** — 2022-07-20T07:00 až 2022-07-27T08:07, spolu +345.66, rovnako dlhých sérií 5.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-07-20T07:00 | 2022-07-20T07:35 | +62.14 | +0.25 | `take_profit` |
| 2 | 2022-07-20T08:55 | 2022-07-20T10:40 | +74.14 | +0.30 | `take_profit` |
| 3 | 2022-07-22T10:20 | 2022-07-22T11:47 | +70.62 | +0.28 | `take_profit` |
| 4 | 2022-07-26T12:05 | 2022-07-26T13:00 | +71.14 | +0.29 | `take_profit` |
| 5 | 2022-07-27T07:10 | 2022-07-27T08:07 | +67.64 | +0.28 | `take_profit` |

**Straty za sebou: 11** — 2023-10-20T09:50 až 2023-11-14T13:30, spolu -926.56.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-10-20T09:50 | 2023-10-20T14:11 | -76.04 | -0.26 | `stop_loss` |
| 2 | 2023-10-24T09:45 | 2023-10-24T13:40 | -100.08 | -0.17 | `stop_loss` |
| 3 | 2023-10-25T13:20 | 2023-10-25T13:30 | -86.07 | -0.15 | `stop_loss` |
| 4 | 2023-11-03T10:05 | 2023-11-03T11:50 | -83.10 | -0.14 | `stop_loss` |
| 5 | 2023-11-06T20:15 | 2023-11-07T13:56 | -87.57 | -0.29 | `stop_loss` |
| 6 | 2023-11-08T04:10 | 2023-11-08T17:00 | -100.15 | -0.16 | `stop_loss` |
| 7 | 2023-11-09T00:15 | 2023-11-09T08:44 | -82.58 | -0.27 | `stop_loss` |
| 8 | 2023-11-13T11:55 | 2023-11-13T14:30 | -73.09 | -0.23 | `stop_loss` |
| 9 | 2023-11-13T15:50 | 2023-11-13T16:42 | -96.59 | -0.31 | `stop_loss` |
| 10 | 2023-11-14T10:25 | 2023-11-14T10:50 | -90.19 | -0.14 | `stop_loss` |
| 11 | 2023-11-14T12:05 | 2023-11-14T13:30 | -51.09 | -0.16 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0010 %**, medián -0.0009 %, 90 % interval -0.0087–0.0070 %
- P(edge > poplatok) = **28.3 %**
- max drawdown: medián 5.1 %, 95. percentil 9.9 %, najhorší 16.0 %
- najdlhšia séria strát: medián 10, 95. percentil 15 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **219** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=ef58e852 -->

_Posudok (Claude, 26. 10. 2026) — nastavenie: repo profil `mnq_databento_5m` (Pine defaulty prenesené na MNQ 5m),
nie ladený profil testera; ladené profily `WK_fibo_*` sú na BTC, nie na MNQ._

1. **Na čo sa to hodí a na čo nie.** V tomto nastavení na nič. Návrat k Fibonacciho úrovni (protitrendová, istota
   priemerná) na MNQ 5m dáva 580 obchodov za 5 rokov (0,34 za deň), winrate 41,9 %, payoff 1,32 — to je presne
   hranica nuly. Výstupy sú len SL (58 %) a TP (42 %), čiže výsledok je čisto otázka pomeru zásahov.
2. **Má to potenciál?** Nie v tejto podobe. Zisková len v 1 z 5 okien (2021/22 +0,27 %), break-even −0,0010 % pod
   poplatkom 0,0018 %, nad poplatkom len 28 % bootstrapových vzoriek a −0,2 σ proti náhodnému vstupu — výber vstupu
   nepridáva nič. Edge „drží“ (71. percentil) len v tom zmysle, že nulový bol vždy. Za stratégiou nie je jav, ktorý by
   sa dal vidieť na MNQ.
3. **Čo treba dorobiť.** Repo profil je na MNQ len prenesený — kto chce o fibo povedať niečo na MNQ, musí mať
   ladený profil pre MNQ (dnes sú ladené len BTC `WK_fibo_BTC_*` s „posl. rok PF 1,6“, čiže laďované na jeden rok).
   Dokument tak hovorí o Pine defaultoch na MNQ, nie o stratégii v najlepšom nastavení.
4. **Čo otestovať ďalej.** `cli checkup --strategy fibo --profile tester/profiles/WK_fibo_BTC_152obch_WR56_R1_3.json
   --pair BTC/USDT:USDT` — či BTC nastavenie drží aj mimo roka, na ktorom bolo vybrané; rozhodne, či sa fibo vôbec
   oplatí ďalej ladiť. Ak tam bude ziskový len posledný rok, stratégiu odložiť.
5. **Je to použiteľné?** Nie. Na MNQ s týmto profilom je to náhoda pod poplatkom; nič na ostrý účet ani do portfólia.
6. **Čo by som pridal.** Vstup len pri súbehu Fibo úrovne so štruktúrou dňa (VWAP, high/low predošlého dňa) —
   samotná úroveň 61,8 % je na indexe zjavne bez informácie; súbeh je jediný spôsob, ako jej dať obsah.

<!-- POSUDOK KONIEC -->
