# Základná analytika — VWAP OP (`vwapop`)

Zmerané 2026-10-26 na `MNQ/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/vwapop/configs/mnq_databento_5m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy vwapop \
   --profile tradebot/strategies/vwapop/configs/mnq_databento_5m.json \
   --pair MNQ/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 855 obchodov spolu — na štatistiku dosť
- drawdown drží: 95. percentil 18.3 %
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 2 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20231001-20241001 v strate)
- break-even -0.0024 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 8 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- nie je lepšia než náhodný vstup za tých istých pravidiel (-1.2 sigma) — výber vstupu nepridáva nič
- charakter: protitrendová (mean reversion) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 165 | -2.07 | -0.0068 | 4.2 | 31.5 | +4/-9 | `20261026-132225-077ec3` |
| 20221001-20231001 | 202 | -4.29 | -0.0087 | 5.0 | 28.7 | +6/-12 | `20261026-132231-3a87bf` |
| 20231001-20241001 | 207 | -2.36 | -0.0025 | 3.9 | 31.9 | +4/-11 | `20261026-132237-8b233b` |
| 20240904-20250904 | 156 | +0.03 | 0.0018 | 3.1 | 31.4 | +3/-11 | `20261026-132243-a43c8d` |
| 20250904-20260904 | 138 | +1.16 | 0.0052 | 1.8 | 36.2 | +8/-10 | `20261026-132249-c981d7` |

Zisková v **2 z 5** okien, obchodov spolu 855, break-even celkom -0.0024 %. Okná sa prekrývajú, 13 obchodov započítaných dvakrát vypadlo.

## Charakter

**Protitrendová (mean reversion)** (istota priemerná)

- vstup proti poslednému pohybu (-0.51 ATR za 5 barov)
- medián držania 2.2 barov grafu
- winrate 31.58 %, payoff 1.949
- 0.48 obchodov za deň
- šikmosť výnosov +0.95

- **Čo je normálne:** Winrate nad 60 % a payoff pod 1 je pri tomto type v poriadku — zarába sa frekvenciou, nie veľkosťou.
- **Na čo pozor:** Jedna strata môže zmazať mesiac. Stop je tu dôležitejší než vstup a `maxLossDollar` aj drawdown limit majú väčší význam než pri ostatných typoch.
- **Čo ladiť:** Stop a filter režimu (v trende protitrendová stratégia dostáva rany). Ladiť RR nahor väčšinou len zníži winrate a nič nepridá.

Výstupy: `stop_loss` 68.4 %, `take_profit` 31.6 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0091 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| deň po sviatku | 23 | 2.7 % | 26.1 | -0.0187 | -0.0020 | +0.0004 |
| bežný deň | 796 | 93.1 % | 31.0 | -0.0038 | 0.0067 | +0.0091 |
| deň pred sviatkom | 8 | 0.9 % | 50.0 | 0.0436 | -0.0027 | -0.0003 |

**Smer** (riadi `allowLong`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| short | 411 | 48.1 % | 27.2 | -0.0102 | 0.0055 | +0.0079 |
| long | 444 | 51.9 % | 35.6 | 0.0055 | -0.0102 | -0.0078 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.5261 | 214 | 25.0 % | 23.8 | -0.0142 | 0.0023 | +0.0047 |
| nad 0.7247 | 213 | 24.9 % | 32.4 | -0.0029 | -0.0022 | +0.0002 |
| 0.6331 – 0.7247 | 214 | 25.0 % | 34.1 | 0.0035 | -0.0044 | -0.0020 |
| 0.5261 – 0.6331 | 214 | 25.0 % | 36.0 | 0.0057 | -0.0050 | -0.0026 |

Parametre, ktorými sa dá s tým niečo spraviť: `allowLong`, `closeEOD`, `driftAtr`, `rr`, `slAtr`, `tradeWin`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0032 % | -0.0000 % ± 0.0027 | -1.18 | 12.3 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0032 % | -0.0003 % ± 0.0034 | -0.86 | 18.4 |

HORSIE nez nahoda (-1.2 sigma). Nahodny vstup za tych istych pravidiel dava lepsi vysledok - vyber vstupu vysledku skodi.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 201 | 13.6 | 32.3 | -0.0037 | 40 |
| 2022-12 - 2024-03 | 270 | 18.3 | 27.8 | -0.0094 | 9 |
| 2024-03 - 2025-06 | 203 | 13.8 | 34.5 | 0.0039 | 85 |
| 2025-06 - 2026-09 | 181 | 12.3 | 33.1 | 0.0014 | 73 |

Hranice pre úsek veľkosti posledného obdobia: -0.0128 až +0.0078 % (medián -0.0023).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 73. percentile, teda v medziach -0.0128 až +0.0078 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 8** — 2026-01-19T15:25 až 2026-02-23T15:44, spolu +1279.41.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-01-19T15:25 | 2026-01-19T16:03 | +156.45 | +0.15 | `take_profit` |
| 2 | 2026-01-20T15:55 | 2026-01-20T16:02 | +138.72 | +0.27 | `take_profit` |
| 3 | 2026-01-26T15:15 | 2026-01-26T16:32 | +176.68 | +0.34 | `take_profit` |
| 4 | 2026-01-28T15:20 | 2026-01-28T15:57 | +143.16 | +0.27 | `take_profit` |
| 5 | 2026-01-30T16:45 | 2026-01-30T16:58 | +165.19 | +0.32 | `take_profit` |
| 6 | 2026-02-03T16:00 | 2026-02-03T16:22 | +181.70 | +0.35 | `take_profit` |
| 7 | 2026-02-19T15:15 | 2026-02-19T16:23 | +166.25 | +0.33 | `take_profit` |
| 8 | 2026-02-23T15:25 | 2026-02-23T15:44 | +151.25 | +0.30 | `take_profit` |

**Straty za sebou: 12** — 2023-01-10T15:55 až 2023-01-30T15:15, spolu -957.37.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-01-10T15:55 | 2023-01-10T15:57 | -63.29 | -0.28 | `stop_loss` |
| 2 | 2023-01-11T15:35 | 2023-01-11T15:36 | -81.59 | -0.18 | `stop_loss` |
| 3 | 2023-01-12T15:45 | 2023-01-12T16:01 | -74.30 | -0.32 | `stop_loss` |
| 4 | 2023-01-13T16:15 | 2023-01-13T16:17 | -80.61 | -0.18 | `stop_loss` |
| 5 | 2023-01-17T16:40 | 2023-01-17T16:57 | -74.45 | -0.11 | `stop_loss` |
| 6 | 2023-01-18T15:25 | 2023-01-18T15:31 | -86.46 | -0.12 | `stop_loss` |
| 7 | 2023-01-19T15:15 | 2023-01-19T15:17 | -63.30 | -0.28 | `stop_loss` |
| 8 | 2023-01-23T19:50 | 2023-01-23T19:54 | -101.33 | -0.11 | `stop_loss` |
| 9 | 2023-01-24T15:15 | 2023-01-24T15:24 | -59.83 | -0.25 | `stop_loss` |
| 10 | 2023-01-25T15:35 | 2023-01-25T15:58 | -95.82 | -0.41 | `stop_loss` |
| 11 | 2023-01-26T15:15 | 2023-01-26T15:16 | -98.69 | -0.21 | `stop_loss` |
| 12 | 2023-01-30T15:15 | 2023-01-30T15:15 | -77.70 | -0.16 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0024 %**, medián -0.0024 %, 90 % interval -0.0071–0.0023 %
- P(edge > poplatok) = **7.6 %**
- max drawdown: medián 10.6 %, 95. percentil 18.3 %, najhorší 25.8 %
- najdlhšia séria strát: medián 14, 95. percentil 19 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **114** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=efcbc473 -->

_Posudok (Claude, 26. 10. 2026) — repo profil „mnq_databento_5m“, MNQ 5m. Ladený profil testera existuje len pre zlato
(`R1_vwapop_MGC_243obch_WR63`, MGC 3m); pustil som ho na piatich oknách (behy `20261026-132907-09cce1` až
`-132934-ea0e1f`)._

1. **Na čo sa to hodí a na čo nie.** Protitrendová (vstup −0,51 ATR proti pohybu), MNQ 5m, 0,48 obchodu denne, držanie
   2,2 baru, winrate 32 % pri payoffe 1,95. Na MNQ sa v tejto podobe nehodí na nič.
2. **Má to potenciál?** Nie. 2 z 5 okien a aj tie okolo poplatku (2024/25 0,0018 %, 2025/26 0,0052 %), break-even
   −0,0024 %, −1,2 σ — horšie než náhodný vstup —, nad poplatkom 8 % bootstrapu. Ladený MGC profil má PF po oknách
   0,95 / 0,89 / 1,12 / 1,00 / 1,48: zisk len v roku, na ktorom bol nájdený (titulok PF 1,85).
3. **Čo treba dorobiť.** Reverzia k VWAP s RR ~2 a držaním 2 bary si protirečí: reverzný obchod zarába vysokým
   winrate s cieľom na VWAP, nie vzdialeným TP. Cieľ priamo na VWAP a väčšia minimálna vzdialenosť od neho (`driftAtr`).
4. **Čo otestovať ďalej.** `cli sweep --strategy vwapop --profile mnq_databento_5m --pair MNQ/USD --timeframe 5m --space rr=0.5:1.5:0.25 --space driftAtr=1:3:0.5`
   na piatich oknách s cieľom break_even a min. 4 z 5 — ak nič, stratégiu odložiť.
5. **Je to použiteľné?** Nie — na MNQ ani na MGC (ladený profil drží len rok, z ktorého vzišiel).
6. **Čo by som pridal.** Obchodovať len v dňoch bez trendu (cena od otvorenia aspoň dvakrát prekrížila VWAP alebo nízke
   ADX). Reverzia k VWAP v trendovom dni je presne ten obchod, ktorý končí na stope.

<!-- POSUDOK KONIEC -->
