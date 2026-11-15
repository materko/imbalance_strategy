# Základná analytika — LONDON LIQUIDITY IFVG 1.0 (6E) (`lliqeur`)

Zmerané 2026-11-15 na `6E/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/lliqeur/configs/6e_databento_5m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy lliqeur \
   --profile tradebot/strategies/lliqeur/configs/6e_databento_5m.json \
   --pair 6E/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 539 obchodov spolu — na štatistiku dosť
- drawdown drží: 95. percentil 8.2 %
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 1 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20231001-20241001, 20250904-20260904 v strate)
- break-even 0.0000 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 2 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- proti náhode len +0.1 sigma: náznak, nie dôkaz
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 104 | -1.76 | -0.0020 | 2.2 | 44.2 | +4/-5 | `20261115-094642-b8cd93` |
| 20221001-20231001 | 117 | -1.17 | -0.0005 | 1.5 | 47.9 | +5/-4 | `20261115-094645-af4d88` |
| 20231001-20241001 | 101 | -1.17 | -0.0008 | 1.5 | 46.5 | +5/-8 | `20261115-094648-55cd07` |
| 20240904-20250904 | 113 | +0.85 | 0.0034 | 1.0 | 57.5 | +8/-6 | `20261115-094651-98104f` |
| 20250904-20260904 | 113 | -1.08 | -0.0002 | 1.3 | 49.6 | +4/-7 | `20261115-094658-d261fc` |

Zisková v **1 z 5** okien, obchodov spolu 539, break-even celkom 0.0000 %. Okná sa prekrývajú, 9 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.46 ATR za 5 barov)
- medián držania 3 barov grafu
- winrate 49.17 %, payoff 0.857
- 0.3 obchodov za deň
- šikmosť výnosov +0.221

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 50.8 %, `take_profit` 49.2 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0008 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 8 – 16 | 136 | 25.2 % | 43.4 | -0.0023 | 0.0008 | +0.0008 |
| 16 – 24 | 142 | 26.3 % | 49.3 | -0.0001 | 0.0001 | +0.0001 |
| do 8 | 145 | 26.9 % | 52.4 | 0.0008 | -0.0003 | -0.0003 |
| nad 24 | 116 | 21.5 % | 51.7 | 0.0020 | -0.0005 | -0.0005 |

**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| deň po sviatku | 12 | 2.2 % | 33.3 | -0.0025 | 0.0001 | +0.0001 |
| deň pred sviatkom | 16 | 3.0 % | 50.0 | -0.0020 | 0.0001 | +0.0001 |
| bežný deň | 490 | 90.9 % | 48.8 | -0.0001 | 0.0008 | +0.0008 |

**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 1 h – 2 h | 135 | 25.0 % | 45.2 | -0.0016 | 0.0006 | +0.0006 |
| nad 2 h | 120 | 22.3 % | 49.2 | 0.0002 | -0.0000 | -0.0000 |
| do 1 h | 284 | 52.7 % | 51.1 | 0.0007 | -0.0007 | -0.0007 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0000 % | -0.0001 % ± 0.0008 | +0.10 | 54.5 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0000 % | -0.0000 % ± 0.0007 | +0.01 | 50.7 |

Neodlisitelne od nahody (+0.1 sigma, percentil 54.5). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 132 | 9.0 | 42.4 | -0.0027 | 5 |
| 2022-12 - 2024-03 | 132 | 9.0 | 45.5 | -0.0007 | 37 |
| 2024-03 - 2025-06 | 132 | 9.0 | 56.8 | 0.0031 | 97 |
| 2025-06 - 2026-09 | 143 | 9.7 | 51.8 | 0.0004 | 59 |

Hranice pre úsek veľkosti posledného obdobia: -0.0028 až +0.0029 % (medián 0.0000).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 59. percentile, teda v medziach -0.0028 až +0.0029 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 8** — 2025-07-29T01:20 až 2025-08-12T04:30, spolu +396.74.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-07-29T01:20 | 2025-07-29T01:40 | +44.90 | +0.03 | `take_profit` |
| 2 | 2025-07-30T03:40 | 2025-07-30T04:03 | +51.16 | +0.04 | `take_profit` |
| 3 | 2025-08-01T03:05 | 2025-08-01T03:06 | +69.98 | +0.05 | `take_profit` |
| 4 | 2025-08-05T00:40 | 2025-08-05T00:50 | +44.91 | +0.03 | `take_profit` |
| 5 | 2025-08-06T02:25 | 2025-08-06T03:06 | +44.91 | +0.03 | `take_profit` |
| 6 | 2025-08-08T00:30 | 2025-08-08T01:06 | +44.87 | +0.03 | `take_profit` |
| 7 | 2025-08-11T01:15 | 2025-08-11T01:33 | +44.88 | +0.03 | `take_profit` |
| 8 | 2025-08-12T03:25 | 2025-08-12T04:30 | +51.14 | +0.04 | `take_profit` |

**Straty za sebou: 8** — 2023-11-28T02:15 až 2023-12-27T02:54, spolu -388.33.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-11-28T02:15 | 2023-11-28T02:26 | -48.56 | -0.04 | `stop_loss` |
| 2 | 2023-11-29T02:50 | 2023-11-29T02:54 | -67.33 | -0.05 | `stop_loss` |
| 3 | 2023-12-04T03:00 | 2023-12-04T04:04 | -61.03 | -0.04 | `stop_loss` |
| 4 | 2023-12-05T01:40 | 2023-12-05T01:45 | -48.51 | -0.04 | `stop_loss` |
| 5 | 2023-12-08T03:10 | 2023-12-08T03:43 | -54.74 | -0.04 | `stop_loss` |
| 6 | 2023-12-13T03:45 | 2023-12-13T03:49 | -29.73 | -0.02 | `stop_loss` |
| 7 | 2023-12-20T02:30 | 2023-12-20T03:53 | -36.08 | -0.03 | `stop_loss` |
| 8 | 2023-12-27T02:35 | 2023-12-27T02:54 | -42.36 | -0.03 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0000 %**, medián 0.0000 %, 90 % interval -0.0014–0.0014 %
- P(edge > poplatok) = **1.9 %**
- max drawdown: medián 5.1 %, 95. percentil 8.2 %, najhorší 13.6 %
- najdlhšia séria strát: medián 8, 95. percentil 11 obchodov
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
<!-- POSUDOK cisla=a0092b3c -->

**1. Na čo sa to hodí.** LONDON IFVG na 6E 5m — sweep rozsahu seansy a vstup na prerazenom FVG. Čísla sú z **neladeného východiska** (predloha z MNQ, tickové prahy ×0,12); ladenie pôjde len na 2016–2021/9, tieto okná sú preň čisté overenie a nesmú ho ovplyvniť.

**2. Potenciál.** **Malý.** Zisk len v 1 z 5 okien, break-even 0,0000 %, +0,1 sigma — v predlohe z MNQ (seansa 13–19 NY, sweep večer) na EUR nič nie je.

**3. Čo dorobiť.** Presunúť seansu na Áziu a sweep do Londýna (smernica skúša `sessionStart`/`lsStart` 0–10 h NY).

**4. Čo otestovať.** Smernica EUR (22.–29. 11. 2026); rozhodne, či londýnske okno dá PF ≥ 1,3 na ladení a ≥ 75 obchodov za rok.

**5. Použiteľné?** **Takto o ničom.** Šancu má len s londýnskym oknom.

**6. Čo by som pridal.** Rozsah Ázie ako seansu (19:00–1:00 NY) — to je pre EUR prirodzená likvidita.

<!-- POSUDOK KONIEC -->
