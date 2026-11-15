# Základná analytika — MTK ZONE (6E) (`mtkzoneeur`)

Zmerané 2026-11-15 na `6E/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/mtkzoneeur/configs/6e_databento_3m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy mtkzoneeur \
   --profile tradebot/strategies/mtkzoneeur/configs/6e_databento_3m.json \
   --pair 6E/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 6510 obchodov spolu — na štatistiku dosť
- odlíšiteľná od náhody (+2.9 sigma proti náhodnému vstupu)
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 0 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20231001-20241001, 20240904-20250904, 20250904-20260904 v strate)
- break-even 0.0005 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 0 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 54.3 % (namerané 39.8 % medián) — na účet to treba mať
- charakter: protitrendová (mean reversion) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 1339 | -7.93 | 0.0004 | 11.6 | 48.7 | +8/-12 | `20261115-094839-ba0ba6` |
| 20221001-20231001 | 1381 | -7.78 | 0.0005 | 10.4 | 50.2 | +9/-7 | `20261115-094845-a081e3` |
| 20231001-20241001 | 1197 | -8.21 | 0.0002 | 9.3 | 49.8 | +8/-9 | `20261115-094851-decc17` |
| 20240904-20250904 | 1372 | -6.91 | 0.0007 | 8.5 | 51.0 | +14/-9 | `20261115-094857-3252e0` |
| 20250904-20260904 | 1325 | -7.89 | 0.0005 | 9.0 | 52.5 | +15/-8 | `20261115-094903-c4d8b0` |

Zisková v **0 z 5** okien, obchodov spolu 6510, break-even celkom 0.0005 %. Okná sa prekrývajú, 104 obchodov započítaných dvakrát vypadlo.

## Charakter

**Protitrendová (mean reversion)** (istota priemerná)

- vstup proti poslednému pohybu (-1.46 ATR za 5 barov)
- medián držania 1.3 barov grafu
- winrate 50.43 %, payoff 0.864
- 3.62 obchodov za deň
- šikmosť výnosov +0.347

- **Čo je normálne:** Winrate nad 60 % a payoff pod 1 je pri tomto type v poriadku — zarába sa frekvenciou, nie veľkosťou.
- **Na čo pozor:** Jedna strata môže zmazať mesiac. Stop je tu dôležitejší než vstup a `maxLossDollar` aj drawdown limit majú väčší význam než pri ostatných typoch.
- **Čo ladiť:** Stop a filter režimu (v trende protitrendová stratégia dostáva rany). Ladiť RR nahor väčšinou len zníži winrate a nič nepridá.

Výstupy: `take_profit` 50.4 %, `stop_loss` 49.6 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0011 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| CPI | 285 | 4.4 % | 48.8 | -0.0018 | 0.0006 | +0.0001 |
| žiadna | 5730 | 88.0 % | 50.2 | 0.0003 | 0.0016 | +0.0011 |
| NFP | 293 | 4.5 % | 52.6 | 0.0034 | 0.0003 | -0.0002 |
| FOMC | 198 | 3.0 % | 57.1 | 0.0038 | 0.0004 | -0.0001 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| po vyhlásení | 183 | 2.8 % | 38.2 | -0.0012 | 0.0005 | +0.0000 |
| bez udalosti | 5730 | 88.0 % | 50.2 | 0.0003 | 0.0016 | +0.0011 |
| pred vyhlásením | 597 | 9.2 % | 56.8 | 0.0024 | 0.0003 | -0.0002 |

**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 10 h – 13 h | 1915 | 29.4 % | 47.7 | -0.0009 | 0.0011 | +0.0006 |
| do 7 h | 1836 | 28.2 % | 50.3 | 0.0000 | 0.0007 | +0.0002 |
| nad 13 h | 1213 | 18.6 % | 51.9 | 0.0016 | 0.0002 | -0.0003 |
| 7 h – 10 h | 1546 | 23.7 % | 52.8 | 0.0019 | 0.0000 | -0.0005 |

Parametre, ktorými sa dá s tým niečo spraviť: `rrRatio`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0005 % | -0.0000 % ± 0.0002 | +2.86 | 99.9 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0005 % | -0.0001 % ± 0.0002 | +2.71 | 99.4 |

Edge je odlisitelny od nahody (2.9 sigma, percentil 99.9).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 1668 | 113.1 | 49.0 | 0.0007 | 61 |
| 2022-12 - 2024-03 | 1641 | 111.2 | 49.7 | 0.0002 | 34 |
| 2024-03 - 2025-06 | 1561 | 105.8 | 51.0 | 0.0005 | 53 |
| 2025-06 - 2026-09 | 1640 | 111.2 | 52.0 | 0.0005 | 50 |

Hranice pre úsek veľkosti posledného obdobia: -0.0006 až +0.0015 % (medián 0.0005).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 50. percentile, teda v medziach -0.0006 až +0.0015 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 15** — 2025-10-29T15:14 až 2025-11-03T07:58, spolu +617.31.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-10-29T15:14 | 2025-10-29T15:15 | +26.13 | +0.02 | `take_profit` |
| 2 | 2025-10-29T15:52 | 2025-10-29T15:54 | +26.12 | +0.02 | `take_profit` |
| 3 | 2025-10-30T06:49 | 2025-10-30T06:55 | +63.64 | +0.04 | `take_profit` |
| 4 | 2025-10-30T07:05 | 2025-10-30T07:06 | +19.89 | +0.01 | `take_profit` |
| 5 | 2025-10-30T10:02 | 2025-10-30T10:30 | +88.64 | +0.06 | `take_profit` |
| 6 | 2025-10-30T11:00 | 2025-10-30T11:02 | +13.65 | +0.01 | `take_profit` |
| 7 | 2025-10-30T13:32 | 2025-10-30T13:33 | +44.91 | +0.03 | `take_profit` |
| 8 | 2025-10-30T13:59 | 2025-10-30T14:00 | +38.66 | +0.03 | `take_profit` |
| 9 | 2025-10-31T07:07 | 2025-10-31T07:57 | +101.17 | +0.07 | `take_profit` |
| 10 | 2025-10-31T08:03 | 2025-10-31T08:22 | +32.41 | +0.02 | `take_profit` |
| 11 | 2025-10-31T08:28 | 2025-10-31T08:31 | +32.41 | +0.02 | `take_profit` |
| 12 | 2025-10-31T10:34 | 2025-10-31T10:38 | +19.91 | +0.01 | `take_profit` |
| 13 | 2025-10-31T13:10 | 2025-10-31T13:16 | +19.92 | +0.01 | `take_profit` |
| 14 | 2025-10-31T14:55 | 2025-10-31T15:03 | +69.93 | +0.05 | `take_profit` |
| 15 | 2025-11-03T07:56 | 2025-11-03T07:58 | +19.93 | +0.01 | `take_profit` |

**Straty za sebou: 12** — 2022-03-10T08:03 až 2022-03-14T12:25, spolu -1070.48, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-03-10T08:03 | 2022-03-10T08:10 | -42.35 | -0.03 | `stop_loss` |
| 2 | 2022-03-10T09:00 | 2022-03-10T09:00 | -54.85 | -0.04 | `stop_loss` |
| 3 | 2022-03-10T12:45 | 2022-03-10T12:45 | -142.35 | -0.10 | `stop_loss` |
| 4 | 2022-03-10T14:20 | 2022-03-10T14:20 | -54.84 | -0.04 | `stop_loss` |
| 5 | 2022-03-10T15:34 | 2022-03-10T15:34 | -98.57 | -0.07 | `stop_loss` |
| 6 | 2022-03-11T08:48 | 2022-03-11T09:23 | -123.58 | -0.09 | `stop_loss` |
| 7 | 2022-03-11T09:41 | 2022-03-11T11:05 | -223.58 | -0.16 | `stop_loss` |
| 8 | 2022-03-11T12:55 | 2022-03-11T12:55 | -73.59 | -0.05 | `stop_loss` |
| 9 | 2022-03-14T06:14 | 2022-03-14T06:24 | -36.06 | -0.03 | `stop_loss` |
| 10 | 2022-03-14T07:00 | 2022-03-14T07:01 | -29.80 | -0.02 | `stop_loss` |
| 11 | 2022-03-14T09:54 | 2022-03-14T09:56 | -54.84 | -0.04 | `stop_loss` |
| 12 | 2022-03-14T12:01 | 2022-03-14T12:25 | -136.07 | -0.10 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0005 %**, medián 0.0005 %, 90 % interval -0.0000–0.0010 %
- P(edge > poplatok) = **0.0 %**
- max drawdown: medián 39.8 %, 95. percentil 54.3 %, najhorší 76.7 %
- najdlhšia séria strát: medián 12, 95. percentil 16 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %

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
<!-- POSUDOK cisla=24cccb19 -->

**1. Na čo sa to hodí.** MTK ZONE na 6E 3m — SD zóny z objemu (6E má burzový objem), seansa rozšírená na 2:00–12:00 NY. Čísla sú z **neladeného východiska** (predloha z MNQ, tickové prahy ×0,12); ladenie pôjde len na 2016–2021/9, tieto okná sú preň čisté overenie a nesmú ho ovplyvniť.

**2. Potenciál.** **Neistý.** +2,9 sigma proti náhode (zóny niečo vedia), ale ~1 300 obchodov za rok s break-even 0,0005 % — poplatok zje všetko, 0 z 5 okien v pluse.

**3. Čo dorobiť.** Oveľa prísnejší výber zón (`minConf` 3, `minScore`, menej zón) a väčší cieľ, aby obchodov bolo stovky, nie tisíce.

**4. Čo otestovať.** Smernica EUR (22.–29. 11. 2026); rozhodne, či pri ~100–300 obchodoch za rok vyjde break-even ≥ 2× poplatok.

**5. Použiteľné?** **Takto nie**; signál v zónach je, treba ho prefiltrovať.

**6. Čo by som pridal.** Zóny len z vyššieho TF (15m) a vstup len v Londýne / NY ráno.

<!-- POSUDOK KONIEC -->
