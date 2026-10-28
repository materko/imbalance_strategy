# Základná analytika — NB 1.0 — prieraz konsolidácie v smere H4 (SMA 10 / 20) (`nb`)

Zmerané 2026-10-28 na `MNQ/USD` 15m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `mnq_databento_15m`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy nb \
   --profile mnq_databento_15m \
   --pair MNQ/USD \
   --timeframe 15m \
   --fee 1.755e-05 \
   --wallet 100000
```

## V čom je dobrá

- break-even 0.0112 % je nad poplatkom 0.0018 % (rezerva +0.0094 bodu)
- drawdown drží: 95. percentil 14.0 %
- edge drží aj v poslednom období (2025-05 - 2026-07 na 62. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- zisková v 3 z 5 referenčných okien (20221001-20231001, 20231001-20241001 v strate)
- edge nad poplatkom len v 70 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- proti náhode len +0.7 sigma: náznak, nie dôkaz
- najhoršia skupina '0.2581 – 0.3767' vlastnosti 'Trend alebo rozsah': 29 obchodov (25.2 %), bez nej by break-even bol o +0.0291 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 19 | +0.66 | 0.0140 | 2.5 | 26.3 | +3/-6 | `20261028-152402-cd30f2` |
| 20221001-20231001 | 17 | -2.25 | -0.0338 | 5.0 | 17.6 | +1/-8 | `20261028-152405-b9d9b5` |
| 20231001-20241001 | 25 | -0.85 | -0.0033 | 4.8 | 24.0 | +2/-9 | `20261028-152408-532f02` |
| 20240904-20250904 | 27 | +5.13 | 0.0483 | 3.6 | 37.0 | +5/-8 | `20261028-152411-6cd238` |
| 20250904-20260904 | 28 | +1.62 | 0.0158 | 3.1 | 28.6 | +2/-7 | `20261028-152414-e8fa73` |

Zisková v **3 z 5** okien, obchodov spolu 115, break-even celkom 0.0112 %. Okná sa prekrývajú, 1 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+1.06 ATR za 5 barov)
- medián držania 20.1 barov grafu
- winrate 27.83 %, payoff 2.929
- 0.07 obchodov za deň
- šikmosť výnosov +1.487

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 72.2 %, `take_profit` 27.8 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je '0.2581 – 0.3767' vlastnosti 'Trend alebo rozsah': 29 obchodov (25.2 %), break-even -0.0714 % oproti 0.0112 % celku. Bez nej by break-even bol 0.0403 % (+0.0291). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.2581 – 0.3767 | 29 | 25.2 % | 6.9 | -0.0714 | 0.0403 | +0.0291 |
| do 0.1667 | 30 | 26.1 % | 26.7 | 0.0052 | 0.0131 | +0.0019 |
| 0.1667 – 0.2581 | 28 | 24.3 % | 35.7 | 0.0391 | 0.0008 | -0.0104 |
| nad 0.3767 | 28 | 24.3 % | 42.9 | 0.0774 | -0.0087 | -0.0199 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 7 – 15 | 28 | 24.3 % | 10.7 | -0.0508 | 0.0351 | +0.0239 |
| do 7 | 31 | 27.0 % | 29.0 | 0.0132 | 0.0106 | -0.0006 |
| nad 24 | 23 | 20.0 % | 34.8 | 0.0363 | 0.0045 | -0.0067 |
| 15 – 24 | 33 | 28.7 % | 36.4 | 0.0527 | -0.0047 | -0.0159 |

**Smer**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| long | 88 | 76.5 % | 27.3 | 0.0080 | 0.0329 | +0.0217 |
| short | 27 | 23.5 % | 29.6 | 0.0329 | 0.0080 | -0.0032 |

Parametre, ktorými sa dá s tým niečo spraviť: `entryEndH`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0263 % | 0.0043 % ± 0.0306 | +0.72 | 76.6 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0263 % | 0.0047 % ± 0.0311 | +0.69 | 75.5 |

Neodlisitelne od nahody (+0.7 sigma, percentil 76.6). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 21 | 1.5 | 28.6 | 0.0283 | 68 |
| 2022-12 - 2024-03 | 26 | 1.8 | 11.5 | -0.0475 | 6 |
| 2024-03 - 2025-05 | 34 | 2.4 | 38.2 | 0.0427 | 84 |
| 2025-05 - 2026-07 | 34 | 2.4 | 29.4 | 0.0193 | 62 |

Hranice pre úsek veľkosti posledného obdobia: -0.0441 až +0.0748 % (medián 0.0076).

**DRZI** — posledné obdobie (2025-05 - 2026-07) je na 62. percentile, teda v medziach -0.0441 až +0.0748 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 5** — 2025-03-28T19:33 až 2025-05-12T07:00, spolu +6079.66.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-03-28T19:33 | 2025-03-31T00:19 | +1089.29 | +1.40 | `take_profit` |
| 2 | 2025-04-03T19:17 | 2025-04-04T10:21 | +985.70 | +2.63 | `take_profit` |
| 3 | 2025-04-16T13:01 | 2025-04-16T17:57 | +1278.41 | +1.72 | `take_profit` |
| 4 | 2025-04-23T10:18 | 2025-04-23T13:37 | +1256.00 | +1.11 | `take_profit` |
| 5 | 2025-05-12T06:24 | 2025-05-12T07:00 | +1470.26 | +0.71 | `take_profit` |

**Straty za sebou: 9** — 2023-10-06T18:03 až 2024-01-24T14:39, spolu -4288.14.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-10-06T18:03 | 2023-10-08T22:00 | -362.11 | -0.60 | `stop_loss` |
| 2 | 2023-10-12T06:01 | 2023-10-12T07:29 | -514.49 | -0.09 | `stop_loss` |
| 3 | 2023-10-26T06:01 | 2023-10-26T08:19 | -499.55 | -0.19 | `stop_loss` |
| 4 | 2023-11-13T09:13 | 2023-11-13T14:31 | -473.99 | -0.14 | `stop_loss` |
| 5 | 2023-11-14T18:30 | 2023-11-14T19:06 | -464.45 | -0.37 | `stop_loss` |
| 6 | 2023-12-12T07:49 | 2023-12-12T09:00 | -497.82 | -0.08 | `stop_loss` |
| 7 | 2023-12-19T19:10 | 2023-12-20T19:40 | -460.96 | -0.27 | `stop_loss` |
| 8 | 2023-12-28T07:23 | 2023-12-28T14:01 | -507.37 | -0.08 | `stop_loss` |
| 9 | 2024-01-24T12:38 | 2024-01-24T14:39 | -507.39 | -0.14 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0112 %**, medián 0.0112 %, 90 % interval -0.0169–0.0426 %
- P(edge > poplatok) = **70.0 %**
- max drawdown: medián 7.1 %, 95. percentil 14.0 %, najhorší 26.5 %
- najdlhšia séria strát: medián 11, 95. percentil 15 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **794** na obchod pri účte 100 000

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
<!-- POSUDOK cisla=feb84784 -->

**Posudok východiska z videa (28. 10. 2026, MNQ 15m, trend H4 SMA 10/20, konsolidácia 8 sviečok, RR 3, miesto do cieľa 2,5 R).**

1. **Na čo sa hodí a na čo nie.** Video (TradeCZ, Nikola) je o CFD indexoch a forexe na M15 / H4. Na MNQ 15m to dáva len ~20–28 obchodov za rok, čo je pre smernicu (150 za rok) málo. Na ES je výsledok horší (zisk len v roku 21/22).
2. **Má potenciál?** Slabý. Zisková v 3 z 5 okien, proti náhode len +0,7 sigma a nad poplatkom v 70 % vzoriek. Výsledok drží hlavne filter „miesto do cieľa 2,5 R“, bez neho je to 99 obchodov s PF 0,79.
3. **Čo dorobiť.** Väčšina obchodov sú longy a najhoršia skupina je stredný „trend alebo rozsah“. Chýba filter, či je trh vôbec v konsolidácii (napr. sklon SMA grafu), a obchod pri silnom trende H4 (SMA 10 ako „stena“) by sa dal podržať dlhšie.
4. **Čo otestovať ďalej.** `cli sweep` na `consBars` / `consMaxWidth` / `roomMinR` na 5 oknách. Rozhodne, či sa dá dostať nad 100 obchodov za rok bez straty PF.
5. **Použiteľné?** V tejto podobe **nie**: málo obchodov a edge sa nedá odlíšiť od náhody.
6. **Čo by som pridal.** Trailing stop podľa SMA 10 (Nikola obchod drží, kým ho SMA 10 drží) namiesto pevného RR 3.

<!-- POSUDOK KONIEC -->
