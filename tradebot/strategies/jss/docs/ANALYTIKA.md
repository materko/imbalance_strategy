# Základná analytika — JSS 1.0 — BOS a SD zóna (`jss`)

Zmerané 2026-10-11 na `MNQ/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/jss_PRESIEL_SMERNICAMI_JSS_1_2026-10-11.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy jss \
   --profile .nightsearch/checkup/jss_PRESIEL_SMERNICAMI_JSS_1_2026-10-11.json \
   --pair MNQ/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 734 obchodov spolu — na štatistiku dosť
- break-even 0.0476 % je nad poplatkom 0.0018 % (rezerva +0.0458 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 7.0 %
- odlíšiteľná od náhody (+4.3 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 40. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- charakter: formácia / štruktúra (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'do 0.2283 %' vlastnosti 'Vzdialenosť stopu': 184 obchodov (25.1 %), bez nej by break-even bol o +0.0224 lepší (riadi `slBufferAtr`)

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 149 | +7.54 | 0.0548 | 2.8 | 38.3 | +4/-11 | `20261011-071816-eb16dd` |
| 20221001-20231001 | 156 | +10.50 | 0.0752 | 2.7 | 44.2 | +5/-7 | `20261011-071819-011da8` |
| 20231001-20241001 | 152 | +5.69 | 0.0309 | 2.0 | 34.9 | +4/-8 | `20261011-071822-5f4ae1` |
| 20240904-20250904 | 148 | +7.21 | 0.0349 | 3.0 | 36.5 | +5/-7 | `20261011-071825-d2d60b` |
| 20250904-20260904 | 129 | +11.67 | 0.0523 | 3.9 | 39.5 | +5/-7 | `20261011-071828-d50c9d` |

Zisková v **5 z 5** okien, obchodov spolu 734, break-even celkom 0.0476 %.

## Charakter

**Formácia / štruktúra** (istota priemerná)

- vstup bez jasného smeru pohybu (+0.11 ATR za 5 barov)
- medián držania 16.4 barov grafu
- winrate 38.69 %, payoff 2.243
- 0.41 obchodov za deň
- šikmosť výnosov +1.212

- **Čo je normálne:** Zmes: časť obchodov sa chová ako prerazenie, časť ako návrat. Priemer preto o jednotlivom obchode nehovorí veľa.
- **Na čo pozor:** Práve pri tomto type sa najviac oplatí rozdeliť obchody na skupiny (`tester.analytics`) — priemer skrýva dve rôzne populácie.
- **Čo ladiť:** Podmienky vstupu (ktoré modely/formácie zapnuté) a potom až výstup.

Výstupy: `stop_loss` 61.3 %, `take_profit` 38.4 %, `force_exit` 0.3 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'do 0.2283 %' vlastnosti 'Vzdialenosť stopu': 184 obchodov (25.1 %), break-even -0.0037 % oproti 0.0476 % celku. Bez nej by break-even bol 0.0701 % (+0.0224). Filter na to postavit ide, ale najprv skus `slBufferAtr` - parameter je lacnejsi a citatelnejsi nez model.


**Vzdialenosť stopu** (riadi `slBufferAtr`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.2283 % | 184 | 25.1 % | 31.0 | -0.0037 | 0.0701 | +0.0224 |
| 0.3247 % – 0.5056 % | 183 | 25.0 % | 36.6 | 0.0206 | 0.0556 | +0.0079 |
| 0.2283 % – 0.3247 % | 183 | 25.0 % | 39.3 | 0.0238 | 0.0557 | +0.0080 |
| nad 0.5056 % | 183 | 25.0 % | 48.1 | 0.1741 | 0.0122 | -0.0355 |

**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.122 – 0.1991 | 183 | 24.9 % | 36.1 | 0.0087 | 0.0609 | +0.0133 |
| 0.0589 – 0.122 | 184 | 25.1 % | 34.2 | 0.0177 | 0.0582 | +0.0106 |
| do 0.0589 | 184 | 25.1 % | 41.3 | 0.0639 | 0.0423 | -0.0053 |
| nad 0.1991 | 183 | 24.9 % | 43.2 | 0.1052 | 0.0296 | -0.0180 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.4216 | 184 | 25.1 % | 37.5 | 0.0165 | 0.0584 | +0.0108 |
| 0.4216 – 0.6381 | 184 | 25.1 % | 37.0 | 0.0319 | 0.0529 | +0.0053 |
| nad 0.8192 | 183 | 24.9 % | 38.2 | 0.0703 | 0.0405 | -0.0071 |
| 0.6381 – 0.8192 | 183 | 24.9 % | 42.1 | 0.0734 | 0.0389 | -0.0087 |

Parametre, ktorými sa dá s tým niečo spraviť: `maxHoldBars`, `rrRatio`, `slBufferAtr`, `tradeDirection`, `tradeStartH`, `triggerMode`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0484 % | 0.0010 % ± 0.0109 | +4.34 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0484 % | 0.0011 % ± 0.0109 | +4.35 | 100.0 |

Edge je odlisitelny od nahody (4.3 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 174 | 11.8 | 39.7 | 0.0714 | 82 |
| 2022-12 - 2024-03 | 191 | 12.9 | 44.0 | 0.0590 | 71 |
| 2024-03 - 2025-06 | 209 | 14.2 | 33.5 | 0.0324 | 23 |
| 2025-06 - 2026-09 | 160 | 10.8 | 38.1 | 0.0418 | 40 |

Hranice pre úsek veľkosti posledného obdobia: +0.0046 až +0.0913 % (medián 0.0481).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 40. percentile, teda v medziach +0.0046 až +0.0913 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 5** — 2023-09-15T13:45 až 2023-09-27T17:41, spolu +1168.22, rovnako dlhých sérií 4.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-09-15T13:45 | 2023-09-19T13:57 | +457.42 | +1.47 | `take_profit` |
| 2 | 2023-09-20T13:50 | 2023-09-20T14:58 | +113.42 | +0.37 | `take_profit` |
| 3 | 2023-09-22T16:35 | 2023-09-22T17:38 | +164.45 | +0.55 | `take_profit` |
| 4 | 2023-09-25T17:30 | 2023-09-26T14:14 | +277.46 | +0.93 | `take_profit` |
| 5 | 2023-09-27T16:50 | 2023-09-27T17:41 | +155.47 | +0.53 | `take_profit` |

**Straty za sebou: 11** — 2021-10-01T13:45 až 2021-10-21T19:05, spolu -1708.96.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2021-10-01T13:45 | 2021-10-01T18:40 | -254.03 | -0.87 | `stop_loss` |
| 2 | 2021-10-04T16:30 | 2021-10-04T22:00 | -194.51 | -0.68 | `stop_loss` |
| 3 | 2021-10-05T13:55 | 2021-10-06T07:48 | -228.52 | -0.78 | `stop_loss` |
| 4 | 2021-10-06T13:40 | 2021-10-06T14:03 | -247.02 | -0.85 | `stop_loss` |
| 5 | 2021-10-08T12:45 | 2021-10-08T13:34 | -145.55 | -0.49 | `stop_loss` |
| 6 | 2021-10-11T13:40 | 2021-10-11T19:59 | -189.54 | -0.64 | `stop_loss` |
| 7 | 2021-10-12T13:15 | 2021-10-12T13:32 | -114.03 | -0.39 | `stop_loss` |
| 8 | 2021-10-13T14:40 | 2021-10-13T17:31 | -113.03 | -0.38 | `stop_loss` |
| 9 | 2021-10-15T13:10 | 2021-10-15T13:31 | -55.06 | -0.18 | `stop_loss` |
| 10 | 2021-10-19T14:05 | 2021-10-19T15:00 | -87.58 | -0.29 | `stop_loss` |
| 11 | 2021-10-21T16:40 | 2021-10-21T19:05 | -80.08 | -0.26 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0476 %**, medián 0.0474 %, 90 % interval 0.0274–0.0674 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 4.1 %, 95. percentil 7.0 %, najhorší 16.1 %
- najdlhšia séria strát: medián 10, 95. percentil 15 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **494** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=83b5996a -->
**Posudok (AI, 11. 10. 2026)** — profil PREŠIEL SMERNICAMI č. 1 z testovania podľa smernice (krok 7).

1. **Na čo sa to hodí a na čo nie.** MNQ 3m, BOS/CHoCH a SD zóna, cieľ ~2,2 R, WR 39 %, drží ~16 barov. Typ s veľa malými stratami a menej veľkými ziskami — psychicky náročnejší (séria strát až 11, MC 95 %: 15).
2. **Má to potenciál?** Áno: 5 z 5 rokov, +4,3 σ, break-even 0,048 % (~26× poplatok), rok 25/26 najlepší (+11,7 %). Rovnomerné roky (+5,7 až +11,7 %) — nie je to jeden šťastný rok.
3. **Čo dorobiť.** Najhoršia štvrtina obchodov má tesný stop (do 0,23 %) — `slBufferAtr` vyššie (+0,022 break-even). Dlhé série strát → sizing nižší (MC odporúča max. ~490 $ riziko pri 60k). Analytika ráta obchody z prekrývajúcich sa okien 23/24 a 24/25 (september 2024) dvakrát — najdlhšia séria strát môže byť o 1–2 nadsadená.
4. **Čo otestovať ďalej.** NAS100 z Dukascopy (krok 8) — rovnaký smer výsledku = jav trhu, nie dát; 2× poplatok (`--fee 3.51e-05`) a 1 tick sklzu navyše; forward test 4–8 týždňov na 1 MNQ (krok 9).
5. **Je to použiteľné?** Áno, solídny kandidát s dobrou rezervou; vhodný pre účet bez denných limitov (prop s denným limitom môže zhodiť séria strát).
6. **Čo by som pridal.** Posun stopu na vstup po 1 R — pri payoffe 2,2 by skrátil straty v sériách; testovať len ako prepínač na forward teste.
<!-- POSUDOK KONIEC -->
