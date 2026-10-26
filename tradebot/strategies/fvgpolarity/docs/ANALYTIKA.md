# Základná analytika — FVG POLARITY (`fvgpolarity`)

Zmerané 2026-10-26 na `MNQ/USD` 15m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/fvgpolarity/configs/mnq_databento_15m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy fvgpolarity \
   --profile tradebot/strategies/fvgpolarity/configs/mnq_databento_15m.json \
   --pair MNQ/USD \
   --timeframe 15m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 19004 obchodov spolu — na štatistiku dosť
- charakter: scalping (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 0 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20231001-20241001, 20240904-20250904, 20250904-20260904 v strate)
- break-even -0.0006 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 0 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 100.0 % (namerané 100.0 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 77.2 % pri riziku, s akým beh bežal
- nie je lepšia než náhodný vstup za tých istých pravidiel (-0.9 sigma) — výber vstupu nepridáva nič

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 4079 | -13.78 | -0.0001 | 17.4 | 57.8 | +19/-13 | `20261026-131214-f3fe18` |
| 20221001-20231001 | 3647 | -18.18 | -0.0011 | 21.9 | 62.9 | +20/-8 | `20261026-131220-f4ed0e` |
| 20231001-20241001 | 3624 | -25.61 | -0.0012 | 27.4 | 60.6 | +14/-10 | `20261026-131226-752950` |
| 20240904-20250904 | 3810 | -32.81 | -0.0013 | 33.1 | 53.6 | +13/-11 | `20261026-131232-4ef0b1` |
| 20250904-20260904 | 4155 | -28.24 | -0.0001 | 31.7 | 49.3 | +15/-14 | `20261026-131238-dbdc76` |

Zisková v **0 z 5** okien, obchodov spolu 19004, break-even celkom -0.0006 %. Okná sa prekrývajú, 311 obchodov započítaných dvakrát vypadlo.

## Charakter

**Scalping** (istota dobrá)

- vstup proti poslednému pohybu (-1.40 ATR za 5 barov)
- medián držania 0.5 barov grafu
- winrate 56.71 %, payoff 0.686
- 10.56 obchodov za deň
- šikmosť výnosov +1.366

- **Čo je normálne:** Edge na obchod je rádovo taký veľký ako poplatok. Break-even poplatok je tu jediné číslo, ktoré niečo znamená.
- **Na čo pozor:** Poplatky a slippage rozhodujú o všetkom. Beh s `--fee 0` je pri tomto type úplne bezcenný.
- **Čo ladiť:** Break-even poplatok, nie PnL. A počet obchodov — menej lepších je zvyčajne viac.

Výstupy: `take_profit` 57.6 %, `stop_loss` 42.4 %, `force_exit` 0 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0006 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Volatilita voči normálu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 1.079 – 1.519 | 4737 | 24.9 % | 52.0 | -0.0026 | 0.0000 | +0.0006 |
| do 0.803 | 4754 | 25.0 % | 66.5 | -0.0007 | -0.0006 | +0.0000 |
| nad 1.519 | 4747 | 25.0 % | 47.0 | -0.0002 | -0.0008 | -0.0002 |
| 0.803 – 1.079 | 4766 | 25.1 % | 61.4 | 0.0010 | -0.0012 | -0.0006 |

**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| sviatok v USA (Vianoce) | 13 | 0.1 % | 30.8 | -0.0195 | -0.0006 | +0.0000 |
| polovičný deň (deň pred Dňom nezávislosti) | 27 | 0.1 % | 55.6 | -0.0105 | -0.0006 | +0.0000 |
| sviatok v USA (Vďakyvzdanie) | 40 | 0.2 % | 70.0 | -0.0041 | -0.0006 | +0.0000 |
| sviatok v USA (Veľký piatok) | 9 | 0.0 % | 77.8 | -0.0037 | -0.0006 | +0.0000 |
| … | | | | | | |
| polovičný deň (deň po Vďakyvzdaní) | 28 | 0.1 % | 67.9 | 0.0020 | -0.0006 | +0.0000 |
| polovičný deň (Štedrý deň) | 19 | 0.1 % | 68.4 | 0.0042 | -0.0006 | +0.0000 |
| sviatok v USA (Deň nezávislosti) | 29 | 0.2 % | 75.9 | 0.0085 | -0.0006 | +0.0000 |
| sviatok v USA (Nový rok) | 22 | 0.1 % | 68.2 | 0.0140 | -0.0006 | +0.0000 |

**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| proti trendu | 12278 | 64.6 % | 54.4 | -0.0009 | -0.0001 | +0.0005 |
| s trendom | 6726 | 35.4 % | 61.0 | -0.0001 | -0.0009 | -0.0003 |

Parametre, ktorými sa dá s tým niečo spraviť: `slPoints`, `tpLevel`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0006 % | -0.0003 % ± 0.0004 | -0.86 | 20.3 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0006 % | -0.0003 % ± 0.0004 | -0.86 | 20.3 |

Neodlisitelne od nahody (-0.9 sigma, percentil 20.3). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 4990 | 338.3 | 58.0 | -0.0002 | 70 |
| 2022-12 - 2024-03 | 4354 | 295.2 | 64.2 | -0.0010 | 32 |
| 2024-03 - 2025-06 | 4667 | 316.4 | 55.1 | -0.0008 | 38 |
| 2025-06 - 2026-09 | 4993 | 338.5 | 50.4 | -0.0005 | 57 |

Hranice pre úsek veľkosti posledného obdobia: -0.0019 až +0.0007 % (medián -0.0006).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 57. percentile, teda v medziach -0.0019 až +0.0007 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 20** — 2023-05-05T19:00 až 2023-05-09T01:33, spolu +523.61, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-05-05T19:00 | 2023-05-05T19:19 | +63.13 | +0.12 | `take_profit` |
| 2 | 2023-05-05T20:15 | 2023-05-07T22:11 | +54.13 | +0.10 | `take_profit` |
| 3 | 2023-05-07T22:30 | 2023-05-07T22:38 | +28.13 | +0.05 | `take_profit` |
| 4 | 2023-05-08T00:00 | 2023-05-08T00:13 | +29.13 | +0.05 | `take_profit` |
| 5 | 2023-05-08T01:45 | 2023-05-08T01:49 | +15.13 | +0.03 | `take_profit` |
| 6 | 2023-05-08T02:45 | 2023-05-08T03:36 | +12.13 | +0.02 | `take_profit` |
| 7 | 2023-05-08T04:00 | 2023-05-08T04:03 | +13.13 | +0.02 | `take_profit` |
| 8 | 2023-05-08T08:00 | 2023-05-08T08:00 | +2.13 | +0.00 | `take_profit` |
| 9 | 2023-05-08T08:30 | 2023-05-08T08:49 | +17.13 | +0.03 | `take_profit` |
| 10 | 2023-05-08T09:15 | 2023-05-08T09:23 | +5.13 | +0.01 | `take_profit` |
| 11 | 2023-05-08T10:00 | 2023-05-08T10:31 | +19.13 | +0.04 | `take_profit` |
| 12 | 2023-05-08T11:30 | 2023-05-08T11:36 | +25.13 | +0.05 | `take_profit` |
| 13 | 2023-05-08T13:00 | 2023-05-08T13:30 | +33.13 | +0.06 | `take_profit` |
| 14 | 2023-05-08T14:00 | 2023-05-08T14:02 | +54.14 | +0.10 | `take_profit` |
| 15 | 2023-05-08T15:15 | 2023-05-08T15:30 | +62.13 | +0.12 | `take_profit` |
| 16 | 2023-05-08T16:15 | 2023-05-08T16:15 | +8.13 | +0.02 | `take_profit` |
| 17 | 2023-05-08T17:30 | 2023-05-08T18:04 | +19.13 | +0.04 | `take_profit` |
| 18 | 2023-05-08T19:00 | 2023-05-08T19:14 | +49.12 | +0.09 | `take_profit` |
| 19 | 2023-05-08T22:15 | 2023-05-08T22:16 | +5.13 | +0.01 | `take_profit` |
| 20 | 2023-05-09T01:30 | 2023-05-09T01:33 | +9.13 | +0.02 | `take_profit` |

**Straty za sebou: 14** — 2025-11-03T08:30 až 2025-11-04T03:00, spolu -1193.32, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-11-03T08:30 | 2025-11-03T08:50 | -83.66 | -0.08 | `stop_loss` |
| 2 | 2025-11-03T09:00 | 2025-11-03T09:05 | -84.66 | -0.08 | `stop_loss` |
| 3 | 2025-11-03T09:15 | 2025-11-03T09:24 | -81.67 | -0.08 | `stop_loss` |
| 4 | 2025-11-03T09:30 | 2025-11-03T11:09 | -82.67 | -0.08 | `stop_loss` |
| 5 | 2025-11-03T14:00 | 2025-11-03T14:00 | -82.68 | -0.08 | `stop_loss` |
| 6 | 2025-11-03T14:15 | 2025-11-03T14:29 | -84.68 | -0.08 | `stop_loss` |
| 7 | 2025-11-03T14:30 | 2025-11-03T14:31 | -82.68 | -0.08 | `stop_loss` |
| 8 | 2025-11-03T15:00 | 2025-11-03T15:00 | -107.67 | -0.10 | `stop_loss` |
| 9 | 2025-11-03T19:15 | 2025-11-03T19:20 | -83.66 | -0.08 | `stop_loss` |
| 10 | 2025-11-03T19:30 | 2025-11-03T19:42 | -79.66 | -0.08 | `stop_loss` |
| 11 | 2025-11-03T23:15 | 2025-11-03T23:52 | -86.66 | -0.08 | `stop_loss` |
| 12 | 2025-11-04T00:00 | 2025-11-04T00:04 | -81.66 | -0.08 | `stop_loss` |
| 13 | 2025-11-04T00:30 | 2025-11-04T02:42 | -86.65 | -0.08 | `stop_loss` |
| 14 | 2025-11-04T02:45 | 2025-11-04T03:00 | -84.64 | -0.08 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0006 %**, medián -0.0006 %, 90 % interval -0.0013–0.0001 %
- P(edge > poplatok) = **0.0 %**
- max drawdown: medián 100.0 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 14, 95. percentil 18 obchodov
- pravdepodobnosť ruiny účtu: 77.2 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **14** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=6f17e76c -->

_Posudok (Claude, 26. 10. 2026) — nastavenie: repo profil `mnq_databento_15m` (MNQ 15m), nie ladený profil
testera; ladené profily `FVP_BTC_*` sú na BTC (WR 97 %, zisk:strata 0,05 R)._

1. **Na čo sa to hodí a na čo nie.** V tomto nastavení na nič. Scalping (istota dobrá) na FVG: 19 004 obchodov,
   10,6 za deň na 15m grafe s mediánom držania 0,5 baru — obchod sa vybaví vnútri sviečky, takže o výsledku rozhoduje
   1m detail fillov, nie logika stratégie. Payoff 0,69 pri winrate 57 % je pod nulou ešte pred poplatkom.
2. **Má to potenciál?** Nie. Strata v 5 z 5 okien (−13,8 až −32,8 %), break-even −0,0006 % pod poplatkom, 0 %
   vzoriek nad poplatkom, −0,9 σ proti náhode. 95. percentil drawdownu 100 % a pravdepodobnosť ruiny 77 % — s rizikom,
   s akým beh bežal, je to istý koniec účtu.
3. **Čo treba dorobiť.** Repo profil s 10 obchodmi za deň je zjavne nastavenie bez filtra — pred akýmkoľvek ďalším
   meraním potrebuje stratégia obmedzenie počtu vstupov. BTC profily `FVP_BTC_*` s WR 97 % a zisk:strata 0,05 R sú
   opačný extrém: jeden zásah SL zmaže 20 ziskov, takže ich „PF 2,26“ visí na tom, že v ladenom roku SL takmer nebol.
4. **Čo otestovať ďalej.** `cli checkup --strategy fvgpolarity --profile tester/profiles/FVP_BTC_179obch_WR97.json
   --pair BTC/USDT:USDT` — či WR 97 % prežije päť rokov; ak niektorý rok padne pod ~94 %, je payoff 0,05 R strata.
5. **Je to použiteľné?** Nie. Repo profil je istá strata; ladené BTC profily sú stavané na jeden rok bez veľkého pohybu.
6. **Čo by som pridal.** Brať len FVG, ktorá vznikla v smere vyššieho TF (1h trend) a obchodovať ju raz — ako
   „polarity“ (zmena úlohy zóny) má zmysel len prvý návrat, nie každý dotyk.

<!-- POSUDOK KONIEC -->
