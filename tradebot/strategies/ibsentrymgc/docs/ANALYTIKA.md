# Základná analytika — IBS EZ MGC (`ibsentrymgc`)

Zmerané 2026-10-26 na `MGC/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/ibsentrymgc/configs/mgc_databento_3m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy ibsentrymgc \
   --profile tradebot/strategies/ibsentrymgc/configs/mgc_databento_3m.json \
   --pair MGC/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 813 obchodov spolu — na štatistiku dosť

## Kde má chyby

- zisková v 1 z 5 referenčných okien (20211001-20221001, 20231001-20241001, 20240904-20250904, 20250904-20260904 v strate)
- break-even -0.0015 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 13 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 100.0 % (namerané 55.0 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 6.3 % pri riziku, s akým beh bežal
- nie je lepšia než náhodný vstup za tých istých pravidiel (-2.4 sigma) — výber vstupu nepridáva nič
- POZOR NA TREND: každé z 4 období je horšie než predchádzajúce (sklon -0.0056 na obdobie). Posledné je ešte v medziach (8. percentil), takže test úpadok nepotvrdzuje — ale rad sa sám od seba zoradí zriedka. Zopakuj to, keď pribudnú dáta.
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'deň pred sviatkom' vlastnosti 'Sviatok na burze v USA': 13 obchodov (1.6 %), bez nej by break-even bol o +0.0121 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 130 | -0.57 | 0.0015 | 14.1 | 67.7 | +15/-4 | `20261026-130646-1a5487` |
| 20221001-20231001 | 102 | +28.33 | 0.0183 | 4.5 | 77.5 | +17/-2 | `20261026-130702-b540bf` |
| 20231001-20241001 | 106 | -6.04 | -0.0019 | 12.8 | 64.2 | +9/-4 | `20261026-130720-fc2f46` |
| 20240904-20250904 | 142 | -14.04 | -0.0047 | 21.0 | 62.7 | +12/-6 | `20261026-130738-221cb5` |
| 20250904-20260904 | 333 | -47.19 | -0.0087 | 49.4 | 61.3 | +10/-8 | `20261026-130754-ba3b4c` |

Zisková v **1 z 5** okien, obchodov spolu 813, break-even celkom -0.0015 %.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+0.88 ATR za 5 barov)
- medián držania 4.7 barov grafu
- winrate 64.94 %, payoff 0.493
- 0.45 obchodov za deň
- šikmosť výnosov -1.284

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 65.1 %, `stop_loss` 34.9 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'deň pred sviatkom' vlastnosti 'Sviatok na burze v USA': 13 obchodov (1.6 %), break-even -0.0086 % oproti -0.0015 % celku. Bez nej by break-even bol -0.0014 % (+0.0121). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| deň pred sviatkom | 13 | 1.6 % | 61.5 | -0.0086 | -0.0014 | +0.0001 |
| bežný deň | 772 | 95.0 % | 64.5 | -0.0022 | 0.0106 | +0.0121 |
| deň po sviatku | 19 | 2.3 % | 73.7 | 0.0119 | -0.0018 | -0.0003 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.5537 | 204 | 25.1 % | 59.3 | -0.0089 | 0.0011 | +0.0026 |
| 0.73 – 0.8535 | 203 | 25.0 % | 65.5 | -0.0016 | -0.0015 | +0.0000 |
| 0.5537 – 0.73 | 203 | 25.0 % | 66.0 | 0.0006 | -0.0022 | -0.0007 |
| nad 0.8535 | 203 | 25.0 % | 69.0 | 0.0042 | -0.0035 | -0.0020 |

**Volatilita voči normálu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 1.562 – 2.144 | 203 | 25.0 % | 60.1 | -0.0095 | 0.0010 | +0.0025 |
| 1.158 – 1.562 | 203 | 25.0 % | 63.0 | -0.0044 | -0.0005 | +0.0010 |
| nad 2.144 | 203 | 25.0 % | 67.5 | 0.0037 | -0.0030 | -0.0015 |
| do 1.158 | 204 | 25.1 % | 69.1 | 0.0041 | -0.0037 | -0.0022 |

Parametre, ktorými sa dá s tým niečo spraviť: `closeAtSessionEnd`, `minSlDistance`, `rrRatio`, `sess2TradeStartH`, `state2MaxBars`, `tradeDirection`, `useStructureFilter`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0062 % | 0.0000 % ± 0.0026 | -2.36 | 1.2 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0062 % | -0.0002 % ± 0.0028 | -2.14 | 1.3 |

HORSIE nez nahoda (-2.4 sigma). Nahodny vstup za tych istych pravidiel dava lepsi vysledok - vyber vstupu vysledku skodi.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 156 | 10.6 | 71.8 | 0.0082 | 93 |
| 2022-12 - 2024-03 | 110 | 7.5 | 68.2 | 0.0047 | 79 |
| 2024-03 - 2025-06 | 198 | 13.4 | 63.1 | -0.0038 | 34 |
| 2025-06 - 2026-09 | 349 | 23.7 | 61.9 | -0.0076 | 8 |

Hranice pre úsek veľkosti posledného obdobia: -0.0083 až +0.0056 % (medián -0.0013).

**POZOR NA TREND** — každé z 4 období je horšie než predchádzajúce (sklon -0.0056 na obdobie). Posledné je ešte v medziach (8. percentil), takže test úpadok nepotvrdzuje — ale rad sa sám od seba zoradí zriedka. Zopakuj to, keď pribudnú dáta.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 21** — 2022-09-27T13:44 až 2022-11-07T17:15, spolu +10179.02.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-09-27T13:44 | 2022-09-27T13:48 | +476.91 | +0.07 | `take_profit` |
| 2 | 2022-09-27T15:03 | 2022-09-27T15:16 | +477.56 | +0.09 | `take_profit` |
| 3 | 2022-09-28T16:54 | 2022-09-28T17:00 | +477.27 | +0.09 | `take_profit` |
| 4 | 2022-09-29T14:33 | 2022-09-29T14:43 | +436.73 | +0.07 | `take_profit` |
| 5 | 2022-10-04T16:17 | 2022-10-04T16:37 | +469.54 | +0.10 | `take_profit` |
| 6 | 2022-10-07T14:06 | 2022-10-07T14:18 | +661.27 | +0.10 | `take_profit` |
| 7 | 2022-10-07T16:28 | 2022-10-07T16:32 | +485.00 | +0.11 | `take_profit` |
| 8 | 2022-10-07T18:06 | 2022-10-07T18:11 | +471.23 | +0.07 | `take_profit` |
| 9 | 2022-10-11T14:29 | 2022-10-11T14:34 | +485.30 | +0.12 | `take_profit` |
| 10 | 2022-10-12T06:09 | 2022-10-12T06:17 | +525.16 | +0.10 | `take_profit` |
| 11 | 2022-10-14T15:21 | 2022-10-14T16:00 | +481.33 | +0.14 | `take_profit` |
| 12 | 2022-10-21T14:55 | 2022-10-21T15:23 | +460.91 | +0.20 | `take_profit` |
| 13 | 2022-10-21T15:35 | 2022-10-21T15:44 | +463.82 | +0.19 | `take_profit` |
| 14 | 2022-10-26T14:51 | 2022-10-26T15:09 | +472.81 | +0.11 | `take_profit` |
| 15 | 2022-10-27T14:48 | 2022-10-27T16:35 | +481.23 | +0.14 | `take_profit` |
| 16 | 2022-11-02T22:46 | 2022-11-02T22:51 | +477.03 | +0.07 | `take_profit` |
| 17 | 2022-11-03T13:44 | 2022-11-03T13:49 | +477.91 | +0.10 | `take_profit` |
| 18 | 2022-11-04T06:38 | 2022-11-04T07:05 | +471.98 | +0.08 | `take_profit` |
| 19 | 2022-11-04T16:22 | 2022-11-04T16:27 | +473.54 | +0.10 | `take_profit` |
| 20 | 2022-11-07T15:56 | 2022-11-07T16:17 | +480.92 | +0.12 | `take_profit` |
| 21 | 2022-11-07T16:47 | 2022-11-07T17:15 | +471.59 | +0.07 | `take_profit` |

**Straty za sebou: 8** — 2026-08-12T06:09 až 2026-08-18T14:39, spolu -7856.38.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-08-12T06:09 | 2026-08-12T06:39 | -995.31 | -0.17 | `stop_loss` |
| 2 | 2026-08-13T23:15 | 2026-08-14T00:15 | -1005.48 | -0.23 | `stop_loss` |
| 3 | 2026-08-14T05:45 | 2026-08-14T05:50 | -973.51 | -0.16 | `stop_loss` |
| 4 | 2026-08-14T15:27 | 2026-08-14T15:47 | -927.92 | -0.30 | `stop_loss` |
| 5 | 2026-08-17T04:49 | 2026-08-17T05:14 | -1015.86 | -0.16 | `stop_loss` |
| 6 | 2026-08-17T17:51 | 2026-08-17T18:03 | -990.84 | -0.18 | `stop_loss` |
| 7 | 2026-08-18T06:08 | 2026-08-18T06:24 | -995.30 | -0.17 | `stop_loss` |
| 8 | 2026-08-18T14:33 | 2026-08-18T14:39 | -952.16 | -0.19 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0015 %**, medián -0.0016 %, 90 % interval -0.0063–0.0032 %
- P(edge > poplatok) = **12.7 %**
- max drawdown: medián 55.0 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 7, 95. percentil 9 obchodov
- pravdepodobnosť ruiny účtu: 6.3 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **192** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=563cdbaa -->

_Posudok (Claude, 26. 10. 2026) — nastavenie `mgc_databento_3m`: východiskový profil na zlato, IBS EZ 1 (prešiel smernicou
na MNQ) s bodovými a tickovými prahmi prepočítanými na ATR a s uvoľnenými prahmi FVG/imbalance (~120 obchodov ročne).
Nie je to ladený profil — je to štart hľadania._

1. **Na čo sa to hodí a na čo nie.** V tejto podobe na nič. Na MGC 3m je to 813 obchodov s break-even −0,0015 % (pod
   nulou, nie len pod poplatkom), ziskový je jediný rok z piatich (22/23, +28 %). Ten istý model na MNQ (`ibsentry`,
   `ibsentrynet`) má break-even 0,018 % a 5 z 5 rokov — prenos „ten istý vstup, prahy v ATR“ na zlato nefunguje.
   Veľkosť z rizika (~1 000 $ na obchod) s účtom 60 000 $ dáva medián drawdownu 55 % a 6,3 % ruiny; Monte Carlo pustí
   najviac 192 $ na obchod.
2. **Má to potenciál? Nie v tomto nastavení.** −2,4 σ proti náhodnému vstupu: náhodný vstup s tými istými SL/TP dopadne
   lepšie, takže výber vstupu škodí. Edge navyše rad po rade klesá (0,0082 → 0,0047 → −0,0038 → −0,0076 % po obdobiach)
   a posledný rok je najhorší (−47 %, 333 obchodov — dvakrát viac než predtým, zlato v silnom trende 2025/26).
   Jediný dobrý rok 22/23 (WR 77,5 %, break-even 0,0183 %) je bočný trh zlata — myšlienka (návrat k zóne a scalp na
   0,5 R) možno funguje v rozsahu, ale nie v trende.
3. **Čo treba dorobiť.** (a) Filter režimu je pre zlato povinný: v trendovom roku stratégia obchoduje proti pohybu
   a stráca — skupina „volatilita voči normálu“ 1,16–2,14 má break-even −0,004 až −0,010 %. (b) RR 0,5 pri WR 62–65 %
   je na hrane: pri payoffe 0,49 treba WR ≥ 67 %, ktorú zlato dalo len v 22/23. (c) Sviatky: deň pred sviatkom
   (13 obchodov) je najhorší, ale to je malá vzorka.
4. **Čo otestovať ďalej.** Hľadanie podľa smernice priamo na zlate s oknami kritéria cez všetky roky
   (`cli hyperopt --strategy ibsentrymgc --pair MGC/USD --timeframe 3m --windows ref --aggregate min --select plateau`)
   s priestorom `rrRatio`, `useStructureFilter`, `tradeDirection` a prahmi v ATR. Ak najlepší výsledok so
   `--aggregate min` ostane pod poplatkom, myšlienka na zlate nedrží a stratégiu treba odložiť.
5. **Je to použiteľné? Nie — je to o ničom, kým hľadanie na zlate nenájde nastavenie, ktoré drží vo všetkých piatich
   rokoch.** Na živý účet ani na papier.
6. **Čo by som pridal.** Prepínač „obchoduj len v rozsahu“ (napr. ADX na 60m pod prahom, alebo sklon EMA 50 na 1h blízko
   nuly) — jediný ziskový rok bol rozsahový a stratégia so scalp cieľom 0,5 R patrí do rozsahu, nie do trendu.

<!-- POSUDOK KONIEC -->
