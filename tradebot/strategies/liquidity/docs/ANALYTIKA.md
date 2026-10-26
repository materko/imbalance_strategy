# Základná analytika — Liquidity — likvidita, sweep a cesta k nej (`liquidity`)

Zmerané 2026-10-26 na `MNQ/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/liquidity/configs/mnq_databento_5m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy liquidity \
   --profile tradebot/strategies/liquidity/configs/mnq_databento_5m.json \
   --pair MNQ/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 1398 obchodov spolu — na štatistiku dosť
- drawdown drží: 95. percentil 17.5 %
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 3 z 5 referenčných okien (20231001-20241001, 20240904-20250904 v strate)
- break-even 0.0001 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 18 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- nie je lepšia než náhodný vstup za tých istých pravidiel (-0.1 sigma) — výber vstupu nepridáva nič
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 340 | +0.75 | 0.0031 | 2.0 | 41.8 | +6/-9 | `20261026-131430-19c299` |
| 20221001-20231001 | 321 | +0.75 | 0.0029 | 3.2 | 41.1 | +5/-11 | `20261026-131436-9f37a5` |
| 20231001-20241001 | 301 | -5.65 | -0.0052 | 5.7 | 35.5 | +4/-11 | `20261026-131442-7080ac` |
| 20240904-20250904 | 278 | -3.37 | -0.0026 | 3.7 | 37.4 | +4/-11 | `20261026-131448-354abe` |
| 20250904-20260904 | 182 | +0.31 | 0.0023 | 1.9 | 41.2 | +7/-8 | `20261026-131454-3ffd53` |

Zisková v **3 z 5** okien, obchodov spolu 1398, break-even celkom 0.0001 %. Okná sa prekrývajú, 24 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+2.04 ATR za 5 barov)
- medián držania 5.4 barov grafu
- winrate 39.7 %, payoff 1.446
- 0.78 obchodov za deň
- šikmosť výnosov +0.596

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 60.3 %, `take_profit` 39.7 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0027 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bežný deň | 1288 | 92.1 % | 39.4 | -0.0002 | 0.0028 | +0.0027 |
| deň po sviatku | 46 | 3.3 % | 45.6 | 0.0086 | -0.0002 | -0.0003 |
| deň pred sviatkom | 17 | 1.2 % | 52.9 | 0.0174 | -0.0001 | -0.0002 |

**Smer** (riadi `tradeDirection`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| long | 744 | 53.2 % | 38.8 | -0.0015 | 0.0023 | +0.0022 |
| short | 654 | 46.8 % | 40.7 | 0.0023 | -0.0015 | -0.0016 |

**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.1687 – 0.2563 | 349 | 25.0 % | 36.4 | -0.0062 | 0.0021 | +0.0020 |
| nad 0.2563 | 349 | 25.0 % | 39.0 | -0.0004 | 0.0003 | +0.0002 |
| do 0.1057 | 350 | 25.0 % | 39.7 | 0.0002 | 0.0001 | +0.0000 |
| 0.1057 – 0.1687 | 350 | 25.0 % | 43.7 | 0.0059 | -0.0021 | -0.0022 |

Parametre, ktorými sa dá s tým niečo spraviť: `maxHoldBars`, `rrRatio`, `slBufferAtr`, `tradeDirection`, `tradeMode`, `tradeStartH`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0005 % | -0.0002 % ± 0.0023 | -0.14 | 45.1 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0005 % | -0.0002 % ± 0.0023 | -0.14 | 45.1 |

Neodlisitelne od nahody (-0.1 sigma, percentil 45.1). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 401 | 27.2 | 41.4 | 0.0023 | 75 |
| 2022-12 - 2024-03 | 412 | 28.0 | 40.0 | 0.0013 | 62 |
| 2024-03 - 2025-06 | 329 | 22.4 | 37.4 | -0.0029 | 21 |
| 2025-06 - 2026-09 | 256 | 17.4 | 39.5 | 0.0002 | 52 |

Hranice pre úsek veľkosti posledného obdobia: -0.0068 až +0.0070 % (medián -0.0000).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 52. percentile, teda v medziach -0.0068 až +0.0070 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 7** — 2026-03-11T22:45 až 2026-03-23T07:23, spolu +845.41.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-03-11T22:45 | 2026-03-11T23:09 | +73.26 | +0.15 | `take_profit` |
| 2 | 2026-03-13T06:55 | 2026-03-13T07:15 | +123.28 | +0.25 | `take_profit` |
| 3 | 2026-03-17T05:55 | 2026-03-17T06:00 | +124.52 | +0.13 | `take_profit` |
| 4 | 2026-03-17T12:15 | 2026-03-17T12:32 | +138.50 | +0.14 | `take_profit` |
| 5 | 2026-03-18T12:40 | 2026-03-18T12:44 | +148.25 | +0.30 | `take_profit` |
| 6 | 2026-03-18T19:25 | 2026-03-18T19:55 | +106.27 | +0.21 | `take_profit` |
| 7 | 2026-03-23T06:50 | 2026-03-23T07:23 | +131.33 | +0.27 | `take_profit` |

**Straty za sebou: 11** — 2023-06-28T05:50 až 2023-07-05T18:16, spolu -930.36, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-06-28T05:50 | 2023-06-28T06:43 | -87.17 | -0.10 | `stop_loss` |
| 2 | 2023-06-28T08:40 | 2023-06-28T09:59 | -82.67 | -0.09 | `stop_loss` |
| 3 | 2023-06-28T11:10 | 2023-06-28T11:44 | -77.12 | -0.13 | `stop_loss` |
| 4 | 2023-06-28T20:05 | 2023-06-29T07:03 | -74.06 | -0.24 | `stop_loss` |
| 5 | 2023-06-29T10:25 | 2023-06-29T11:40 | -104.26 | -0.09 | `stop_loss` |
| 6 | 2023-06-29T13:20 | 2023-06-29T13:34 | -56.06 | -0.19 | `stop_loss` |
| 7 | 2023-07-03T05:35 | 2023-07-03T06:00 | -105.47 | -0.06 | `stop_loss` |
| 8 | 2023-07-03T14:40 | 2023-07-03T16:47 | -51.58 | -0.17 | `stop_loss` |
| 9 | 2023-07-04T13:30 | 2023-07-04T14:20 | -102.05 | -0.05 | `stop_loss` |
| 10 | 2023-07-04T23:15 | 2023-07-05T00:00 | -99.85 | -0.03 | `stop_loss` |
| 11 | 2023-07-05T13:50 | 2023-07-05T18:16 | -90.08 | -0.29 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0001 %**, medián 0.0001 %, 90 % interval -0.0028–0.0031 %
- P(edge > poplatok) = **17.6 %**
- max drawdown: medián 9.4 %, 95. percentil 17.5 %, najhorší 27.7 %
- najdlhšia séria strát: medián 12, 95. percentil 17 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **121** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=dd227bfd -->

_Posudok (Claude, 26. 10. 2026) — nastavenie: repo profil `mnq_databento_5m` (MNQ 5m), nie ladený profil
testera; na porovnanie som pustil aj ladený `LQB_1R_RR1_5_477obch_WR50` na tých istých piatich oknách._

1. **Na čo sa to hodí a na čo nie.** Na MNQ 5m ako prerazenie po vybratí likvidity (istota priemerná): 1 398 obchodov,
   0,78 za deň, winrate 40 %, payoff 1,45, výstupy len SL/TP. V repo nastavení sa nehodí na nič — je to nula.
2. **Má to potenciál?** Repo profil nie: break-even 0,0001 % pod poplatkom, 3 z 5 okien (2023/24 −5,65 %, 2024/25
   −3,37 %), −0,1 σ proti náhode. Ladený profil `LQB_1R` je lepší: zisk v 4 z 5 okien (−1,30 / +1,11 / +1,96 / +5,98 /
   +8,92 %), break-even 0,0001 → 0,0027 → 0,0029 → 0,0075 → 0,0140 %. Rast smerom k roku ladenia je ale opäť
   podpis výberu na poslednom roku; prvé tri roky sú pri poplatku 0,0018 % len tesne nad nulou.
3. **Čo treba dorobiť.** Ladený profil udáva „5 rokov ziskové 5/5“, na referenčných oknách MNQ s poplatkom 0,0018 %
   vyšlo 4 z 5 — titul profilu treba zosúladiť s meraním (iný trh, poplatok alebo obdobie). Analytiku stratégie
   je správnejšie spraviť s ladeným profilom, nie s repo defaultmi.
4. **Čo otestovať ďalej.** `cli checkup --strategy liquidity --profile tester/profiles/LQB_1R_RR1_5_477obch_WR50.json
   --pair MNQ/USD --timeframe 5m --fee 1.755e-05 --wallet 60000` — náhoda a slabnutie edge pre ladený profil; ak
   bude pod 2 σ, je zlepšenie len výber.
5. **Je to použiteľné?** Repo profil nie. Ladený je „možno“ — s konkrétnym testom vyššie; dovtedy nie na účet.
6. **Čo by som pridal.** Vstup len po vybratí likvidity z predošlého dňa / overnight high-low (nie z ľubovoľného
   lokálneho swingu) — ten druh likvidity má na indexe známy návratový efekt a ubral by šum z 0,78 obchodu za deň.

<!-- POSUDOK KONIEC -->
