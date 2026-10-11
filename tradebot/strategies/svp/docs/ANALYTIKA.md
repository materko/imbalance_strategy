# Základná analytika — Volume Profile POC 1.0 (`svp`)

Zmerané 2026-10-11 na `MNQ/USD` 15m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/svp_PRESIEL_SMERNICAMI_Volume_Profile_POC_1_2026-10-11.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy svp \
   --profile .nightsearch/checkup/svp_PRESIEL_SMERNICAMI_Volume_Profile_POC_1_2026-10-11.json \
   --pair MNQ/USD \
   --timeframe 15m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 778 obchodov spolu — na štatistiku dosť
- break-even 0.0178 % je nad poplatkom 0.0018 % (rezerva +0.0160 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 2.8 %
- odlíšiteľná od náhody (+8.1 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 54. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- proti náhode v tých istých hodinách je rozdiel podstatne menší (+6.7 vs +8.1 sigma) — veľká časť edge je v tom, KEDY obchoduje, nie v tom, čo si vyberá
- charakter: protitrendová (mean reversion) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'long' vlastnosti 'Smer': 529 obchodov (68.0 %), bez nej by break-even bol o +0.0108 lepší (riadi `tradeDirection`)

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 145 | +3.73 | 0.0183 | 1.1 | 48.3 | +5/-9 | `20261011-071759-5ea121` |
| 20221001-20231001 | 160 | +0.40 | 0.0031 | 2.9 | 42.5 | +5/-12 | `20261011-071802-ac116b` |
| 20231001-20241001 | 186 | +8.45 | 0.0214 | 1.1 | 55.4 | +7/-5 | `20261011-071805-09f2a7` |
| 20240904-20250904 | 155 | +8.13 | 0.0253 | 1.0 | 54.8 | +7/-4 | `20261011-071808-72c01a` |
| 20250904-20260904 | 132 | +5.56 | 0.0183 | 0.9 | 51.5 | +6/-5 | `20261011-071811-4650d5` |

Zisková v **5 z 5** okien, obchodov spolu 778, break-even celkom 0.0178 %.

## Charakter

**Protitrendová (mean reversion)** (istota priemerná)

- vstup proti poslednému pohybu (-0.99 ATR za 5 barov)
- medián držania 0.5 barov grafu
- winrate 50.64 %, payoff 1.461
- 0.43 obchodov za deň
- šikmosť výnosov +1.154

- **Čo je normálne:** Winrate nad 60 % a payoff pod 1 je pri tomto type v poriadku — zarába sa frekvenciou, nie veľkosťou.
- **Na čo pozor:** Jedna strata môže zmazať mesiac. Stop je tu dôležitejší než vstup a `maxLossDollar` aj drawdown limit majú väčší význam než pri ostatných typoch.
- **Čo ladiť:** Stop a filter režimu (v trende protitrendová stratégia dostáva rany). Ladiť RR nahor väčšinou len zníži winrate a nič nepridá.

Výstupy: `take_profit` 50.6 %, `stop_loss` 49.4 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'long' vlastnosti 'Smer': 529 obchodov (68.0 %), break-even 0.0148 % oproti 0.0178 % celku. Bez nej by break-even bol 0.0286 % (+0.0108). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: skus preladit `tradeDirection`.


**Smer** (riadi `tradeDirection`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| long | 529 | 68.0 % | 51.4 | 0.0148 | 0.0286 | +0.0108 |
| short | 249 | 32.0 % | 49.0 | 0.0286 | 0.0148 | -0.0030 |

**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| NFP | 33 | 4.2 % | 42.4 | 0.0080 | 0.0180 | +0.0002 |
| CPI | 30 | 3.9 % | 43.3 | 0.0122 | 0.0179 | +0.0001 |
| žiadna | 669 | 86.0 % | 50.7 | 0.0167 | 0.0259 | +0.0081 |
| FOMC | 46 | 5.9 % | 60.9 | 0.0414 | 0.0163 | -0.0015 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bez udalosti | 669 | 86.0 % | 50.7 | 0.0167 | 0.0259 | +0.0081 |
| po vyhlásení | 85 | 10.9 % | 44.7 | 0.0216 | 0.0174 | -0.0004 |
| pred vyhlásením | 24 | 3.1 % | 70.8 | 0.0345 | 0.0171 | -0.0007 |

Parametre, ktorými sa dá s tým niečo spraviť: `closeAtWindowEnd`, `rrRatio`, `slAtr`, `tradeDirection`, `tradeMode`, `tradeStartH`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0193 % | -0.0000 % ± 0.0024 | +8.12 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0193 % | -0.0001 % ± 0.0029 | +6.67 | 100.0 |

Edge je odlisitelny od nahody (8.1 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 182 | 12.4 | 48.4 | 0.0175 | 48 |
| 2022-12 - 2024-03 | 206 | 14.0 | 47.1 | 0.0101 | 11 |
| 2024-03 - 2025-06 | 215 | 14.6 | 54.4 | 0.0252 | 87 |
| 2025-06 - 2026-09 | 175 | 11.9 | 52.6 | 0.0183 | 54 |

Hranice pre úsek veľkosti posledného obdobia: +0.0071 až +0.0302 % (medián 0.0175).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 54. percentile, teda v medziach +0.0071 až +0.0302 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 8** — 2024-09-13T14:00 až 2024-09-18T14:14, spolu +733.52.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-09-13T14:00 | 2024-09-13T14:01 | +114.27 | +0.15 | `take_profit` |
| 2 | 2024-09-13T14:00 | 2024-09-13T14:01 | +114.27 | +0.15 | `take_profit` |
| 3 | 2024-09-13T14:30 | 2024-09-13T14:39 | +73.63 | +0.19 | `take_profit` |
| 4 | 2024-09-13T14:30 | 2024-09-13T14:39 | +73.63 | +0.19 | `take_profit` |
| 5 | 2024-09-17T16:23 | 2024-09-17T16:29 | +84.62 | +0.22 | `take_profit` |
| 6 | 2024-09-17T16:23 | 2024-09-17T16:29 | +84.62 | +0.22 | `take_profit` |
| 7 | 2024-09-18T14:11 | 2024-09-18T14:14 | +94.24 | +0.12 | `take_profit` |
| 8 | 2024-09-18T14:11 | 2024-09-18T14:14 | +94.24 | +0.12 | `take_profit` |

**Straty za sebou: 12** — 2023-02-28T14:43 až 2023-03-27T19:37, spolu -1014.88.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-02-28T14:43 | 2023-02-28T14:47 | -91.05 | -0.13 | `stop_loss` |
| 2 | 2023-02-28T16:02 | 2023-02-28T16:22 | -84.70 | -0.18 | `stop_loss` |
| 3 | 2023-03-02T18:36 | 2023-03-02T18:37 | -92.68 | -0.19 | `stop_loss` |
| 4 | 2023-03-09T18:23 | 2023-03-09T18:26 | -99.71 | -0.20 | `stop_loss` |
| 5 | 2023-03-17T14:35 | 2023-03-17T14:46 | -54.39 | -0.22 | `stop_loss` |
| 6 | 2023-03-17T18:15 | 2023-03-17T18:39 | -65.89 | -0.26 | `stop_loss` |
| 7 | 2023-03-20T13:28 | 2023-03-20T13:31 | -100.77 | -0.20 | `stop_loss` |
| 8 | 2023-03-20T15:57 | 2023-03-20T16:09 | -63.39 | -0.25 | `stop_loss` |
| 9 | 2023-03-22T19:52 | 2023-03-22T19:55 | -91.90 | -0.36 | `stop_loss` |
| 10 | 2023-03-23T17:11 | 2023-03-23T17:16 | -97.81 | -0.19 | `stop_loss` |
| 11 | 2023-03-27T15:09 | 2023-03-27T15:42 | -80.80 | -0.16 | `stop_loss` |
| 12 | 2023-03-27T19:20 | 2023-03-27T19:37 | -91.80 | -0.18 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0178 %**, medián 0.0178 %, 90 % interval 0.0125–0.0234 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 1.7 %, 95. percentil 2.8 %, najhorší 5.2 %
- najdlhšia séria strát: medián 10, 95. percentil 14 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **1 519** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=66000bb4 -->
**Posudok (AI, 11. 10. 2026)** — profil PREŠIEL SMERNICAMI č. 1 z testovania podľa smernice (krok 7).

1. **Na čo sa to hodí a na čo nie.** MNQ 5m–15m, odraz od POC predošlej seansy (mean reversion), drží veľmi krátko (~0,5 baru). WR 51 %, payoff 1,46. Hodí sa na pokojnejšie dni; v trendových dňoch prichádzajú dlhé série strát.
2. **Má to potenciál?** Áno, ale opatrne: +8,1 σ proti náhode, no v tých istých hodinách už len +6,7 σ — časť edge je v tom, KEDY obchoduje. Rok 22/23 takmer nulový (+0,4 %, break-even 0,003 %), ostatné roky stabilné.
3. **Čo dorobiť.** Longy sú slabšia polovica (68 % obchodov, bez nich +0,011 break-even) — skúsiť `tradeDirection` alebo filter trendu pre longy. Séria strát až 12 (MC 95 %: 14) — vyžaduje trpezlivý účet. Analytika ráta obchody z prekrývajúcich sa okien 23/24 a 24/25 (september 2024) dvakrát — najdlhšia séria strát môže byť o 1–2 nadsadená.
4. **Čo otestovať ďalej.** NAS100 z Dukascopy (krok 8) — rovnaký smer výsledku = jav trhu, nie dát; 2× poplatok (`--fee 3.51e-05`) a 1 tick sklzu navyše; parita s TradingView na 1–2 mesiacoch (krok 9); forward test 4–8 týždňov na 1 MNQ (krok 10).
5. **Je to použiteľné?** Použiteľné ako diverzifikácia (iný typ než breakouty), samostatne slabšia rezerva (break-even 0,018 %). Krok 8 rozhodne.
6. **Čo by som pridal.** Filter dňa podľa trendu (v trendovom dni POC nefunguje ako magnet) a denný limit strát.
<!-- POSUDOK KONIEC -->
