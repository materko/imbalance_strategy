# Základná analytika — TKS 1.0 BTC (C# jadro) (`tksbtcnet`)

Zmerané 2026-11-17 na `BTC/USDT:USDT` 3m, engine `multicharts`, poplatok 0.0200 % na stranu (zadané cez --fee), profil `tradebot/strategies/tksbtcnet/configs/btcusdt_binance_3m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy tksbtcnet \
   --profile tradebot/strategies/tksbtcnet/configs/btcusdt_binance_3m.json \
   --pair BTC/USDT:USDT \
   --timeframe 3m \
   --fee 0.0002 \
   --wallet 60000
```

## V čom je dobrá

- 790 obchodov spolu — na štatistiku dosť

## Kde má chyby

- zisková v 1 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20231001-20241001, 20250904-20260904 v strate)
- break-even 0.0092 % je pod poplatkom 0.0200 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 31 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 85.7 % (namerané 40.5 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 1.6 % pri riziku, s akým beh bežal
- proti náhode len +0.5 sigma: náznak, nie dôkaz
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 's trendom' vlastnosti 'S trendom, alebo proti': 724 obchodov (91.6 %), bez nej by break-even bol o +0.0564 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 139 | -2.25 | 0.0074 | 11.9 | 65.5 | +8/-5 | `20261117-114744-5e679d` |
| 20221001-20231001 | 144 | -4.32 | -0.0175 | 6.9 | 68.1 | +11/-4 | `20261117-114753-d3a01e` |
| 20231001-20241001 | 160 | -7.63 | -0.0054 | 12.4 | 66.2 | +11/-3 | `20261117-114759-9c35ee` |
| 20240904-20250904 | 176 | +4.21 | 0.0277 | 15.5 | 69.3 | +19/-4 | `20261117-114808-a22269` |
| 20250904-20260904 | 183 | -12.02 | -0.0036 | 29.7 | 67.8 | +12/-4 | `20261117-114817-55ba7b` |

Zisková v **1 z 5** okien, obchodov spolu 790, break-even celkom 0.0092 %. Okná sa prekrývajú, 12 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.57 ATR za 5 barov)
- medián držania 16.5 barov grafu
- winrate 67.72 %, payoff 0.453
- 0.44 obchodov za deň
- šikmosť výnosov -1.4

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 68.1 %, `stop_loss` 31.8 %, `force_exit` 0.1 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 's trendom' vlastnosti 'S trendom, alebo proti': 724 obchodov (91.6 %), break-even 0.0049 % oproti 0.0092 % celku. Bez nej by break-even bol 0.0656 % (+0.0564). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 724 | 91.6 % | 67.8 | 0.0049 | 0.0656 | +0.0564 |
| proti trendu | 66 | 8.4 % | 66.7 | 0.0656 | 0.0049 | -0.0043 |

**Smer** (riadi `tradeDirection`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| long | 504 | 63.8 % | 66.9 | -0.0022 | 0.0280 | +0.0188 |
| short | 286 | 36.2 % | 69.2 | 0.0280 | -0.0022 | -0.0114 |

**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.1041 – 0.1884 | 198 | 25.1 % | 61.6 | -0.0410 | 0.0271 | +0.0179 |
| nad 0.2702 | 196 | 24.8 % | 69.9 | 0.0219 | 0.0050 | -0.0042 |
| do 0.1041 | 198 | 25.1 % | 68.2 | 0.0294 | 0.0027 | -0.0065 |
| 0.1884 – 0.2702 | 198 | 25.1 % | 71.2 | 0.0302 | 0.0024 | -0.0068 |

Parametre, ktorými sa dá s tým niečo spraviť: `rrRatio`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0092 % | -0.0002 % ± 0.0183 | +0.52 | 69.5 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0092 % | 0.0006 % ± 0.0179 | +0.48 | 68.6 |

Neodlisitelne od nahody (+0.5 sigma, percentil 69.5). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 169 | 11.5 | 63.9 | -0.0077 | 35 |
| 2022-12 - 2024-03 | 174 | 11.9 | 69.5 | 0.0167 | 57 |
| 2024-03 - 2025-06 | 219 | 14.9 | 70.8 | 0.0425 | 76 |
| 2025-06 - 2026-08 | 228 | 15.6 | 66.2 | -0.0158 | 27 |

Hranice pre úsek veľkosti posledného obdobia: -0.0585 až +0.0730 % (medián 0.0095).

**DRZI** — posledné obdobie (2025-06 - 2026-08) je na 27. percentile, teda v medziach -0.0585 až +0.0730 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 19** — 2024-10-30T15:00 až 2024-12-09T14:47, spolu +9994.27.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-10-30T15:00 | 2024-10-30T21:04 | +457.04 | +0.63 | `take_profit` |
| 2 | 2024-10-31T14:06 | 2024-10-31T18:33 | +648.67 | +0.91 | `take_profit` |
| 3 | 2024-11-04T16:54 | 2024-11-04T17:20 | +488.89 | +0.72 | `take_profit` |
| 4 | 2024-11-06T15:51 | 2024-11-06T18:09 | +418.15 | +0.56 | `take_profit` |
| 5 | 2024-11-07T15:18 | 2024-11-07T15:48 | +425.44 | +0.56 | `take_profit` |
| 6 | 2024-11-08T18:21 | 2024-11-08T18:37 | +320.72 | +0.42 | `take_profit` |
| 7 | 2024-11-11T14:54 | 2024-11-11T15:06 | +417.86 | +0.51 | `take_profit` |
| 8 | 2024-11-12T14:48 | 2024-11-12T14:52 | +568.73 | +0.66 | `take_profit` |
| 9 | 2024-11-12T16:45 | 2024-11-12T17:18 | +622.13 | +0.71 | `take_profit` |
| 10 | 2024-11-12T18:06 | 2024-11-12T18:18 | +658.19 | +0.76 | `take_profit` |
| 11 | 2024-11-18T15:42 | 2024-11-19T13:09 | +973.71 | +1.06 | `take_profit` |
| 12 | 2024-11-19T16:30 | 2024-11-19T17:34 | +508.84 | +0.55 | `take_profit` |
| 13 | 2024-11-21T18:24 | 2024-11-21T19:14 | +621.56 | +0.63 | `take_profit` |
| 14 | 2024-11-22T15:27 | 2024-11-22T16:55 | +560.52 | +0.57 | `take_profit` |
| 15 | 2024-11-25T14:48 | 2024-11-25T14:59 | +765.94 | +0.80 | `take_profit` |
| 16 | 2024-11-25T18:24 | 2024-11-25T18:35 | +349.56 | +0.36 | `take_profit` |
| 17 | 2024-11-29T14:48 | 2024-11-29T14:59 | +324.85 | +0.33 | `take_profit` |
| 18 | 2024-12-02T15:18 | 2024-12-02T15:44 | +527.61 | +0.55 | `take_profit` |
| 19 | 2024-12-09T14:45 | 2024-12-09T14:47 | +335.86 | +0.34 | `take_profit` |

**Straty za sebou: 5** — 2022-05-31T15:57 až 2022-06-16T17:18, spolu -3094.34.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-05-31T15:57 | 2022-06-01T04:07 | -624.64 | -1.94 | `stop_loss` |
| 2 | 2022-06-06T14:30 | 2022-06-06T15:19 | -459.79 | -1.45 | `stop_loss` |
| 3 | 2022-06-13T14:48 | 2022-06-13T16:11 | -1054.98 | -4.60 | `stop_loss` |
| 4 | 2022-06-14T13:45 | 2022-06-14T14:00 | -419.50 | -1.90 | `stop_loss` |
| 5 | 2022-06-16T14:09 | 2022-06-16T17:18 | -535.43 | -2.57 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0092 %**, medián 0.0095 %, 90 % interval -0.0270–0.0449 %
- P(edge > poplatok) = **31.4 %**
- max drawdown: medián 40.5 %, 95. percentil 85.7 %, najhorší 100.0 %
- najdlhšia séria strát: medián 5, 95. percentil 7 obchodov
- pravdepodobnosť ruiny účtu: 1.6 %

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
<!-- POSUDOK cisla=b089f67e -->

Pozor: analytika je na **východisku** — nastavenie TKS 1 z MNQ bez zmeny (len seansa trhu); kolo 1 ladenia (17. 11. 2026, hyperopt hraníc Kompasu, potvrdenia a swingu) je v iCloud TKS-TRHY a v histórii hyperoptov. Po smernici sa analytika prepíše na víťaza.

C# kópia — obchody bar po bare zhodné s Python predlohou (parita), posudok platí rovnako.

1. **Na čo sa to hodí:** BTCUSDT.P, 3m, seansa NY 9:30–16:00 v pracovné dni (najživšie hodiny BTC). Poplatok maker 0,02 % na stranu je ~10× MNQ; cieľ 0,5 R je na BTC krátky na taký poplatok.
2. **Potenciál zatiaľ nie.** Na východisku 1 z 5 rokov v zisku, break-even 0,0092 % je pod poplatkom 0,02 %, proti náhode +0,5 sigma, prepad 95. percentil 86 %. Kolo 1 ladenia (lo 35 / hi 70 / 4 sviečky / swing 7) roky ladenia PF 1,07–1,26, odložený rok 0,86 → pretrénované.
3. **Dorobiť:** väčší cieľ (RR 1–2) alebo limitný vstup, aby poplatok nezjedol edge; začiatok seansy 8:00 NY.
4. **Otestovať:** `--set sessOpenMin=480`, `--param rrRatio=0.5:2:0.25` s hranicami; `--goal break_even` s poplatkom 0,0002. Rozhodne: break-even ≥ 2× poplatok na rokoch ladenia aj v odloženom roku.
5. **O ničom v tejto podobe** — BTC je na minútach návratový a TKS s cieľom 0,5 R nepokryje poplatok.
6. **Pridal by som** Kompas z NQ ako filter pre BTC v NY seanse (BTC ide s Nasdaqom) namiesto vlastného Kompasu BTC.

<!-- POSUDOK KONIEC -->
