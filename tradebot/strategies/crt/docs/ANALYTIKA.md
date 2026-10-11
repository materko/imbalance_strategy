# Základná analytika — CRT + TBS 1.0 (`crt`)

Zmerané 2026-10-11 na `MNQ/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/crt_PRESIEL_SMERNICAMI_CRT_TBS_1_2026-10-11.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy crt \
   --profile .nightsearch/checkup/crt_PRESIEL_SMERNICAMI_CRT_TBS_1_2026-10-11.json \
   --pair MNQ/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 827 obchodov spolu — na štatistiku dosť
- break-even 0.0125 % je nad poplatkom 0.0018 % (rezerva +0.0107 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 4.1 %
- odlíšiteľná od náhody (+5.5 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 40. percentile toho, čo stratégia vyrobí sama od seba)
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 170 | +3.11 | 0.0136 | 2.2 | 55.3 | +9/-7 | `20261011-071923-5cbf08` |
| 20221001-20231001 | 175 | +3.21 | 0.0111 | 1.1 | 55.4 | +6/-5 | `20261011-071926-2ba2db` |
| 20231001-20241001 | 172 | +4.80 | 0.0116 | 0.9 | 58.1 | +6/-5 | `20261011-071929-83afb2` |
| 20240904-20250904 | 150 | +3.53 | 0.0120 | 1.6 | 52.0 | +5/-7 | `20261011-071932-3649d4` |
| 20250904-20260904 | 160 | +4.75 | 0.0148 | 1.6 | 56.2 | +5/-5 | `20261011-071935-2106b5` |

Zisková v **5 z 5** okien, obchodov spolu 827, break-even celkom 0.0125 %.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+0.46 ATR za 5 barov)
- medián držania 11.3 barov grafu
- winrate 55.5 %, payoff 1.065
- 0.46 obchodov za deň
- šikmosť výnosov +0.946

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 55.5 %, `stop_loss` 44.5 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0076 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Vzdialenosť stopu** (riadi `slBufferAtr`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.1048 % | 207 | 25.0 % | 56.0 | 0.0045 | 0.0201 | +0.0076 |
| 0.1048 % – 0.1692 % | 208 | 25.2 % | 52.9 | 0.0055 | 0.0145 | +0.0020 |
| 0.1692 % – 0.2643 % | 206 | 24.9 % | 55.3 | 0.0186 | 0.0114 | -0.0011 |
| nad 0.2643 % | 206 | 24.9 % | 57.8 | 0.0453 | 0.0073 | -0.0052 |

**Volatilita voči normálu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.852 | 207 | 25.0 % | 54.6 | 0.0039 | 0.0178 | +0.0053 |
| 0.852 – 1.168 | 207 | 25.0 % | 51.2 | 0.0044 | 0.0154 | +0.0029 |
| 1.168 – 1.822 | 207 | 25.0 % | 59.9 | 0.0270 | 0.0092 | -0.0033 |
| nad 1.822 | 206 | 24.9 % | 56.3 | 0.0285 | 0.0092 | -0.0033 |

**Hodina vstupu (UTC)** (riadi `tradeStartH`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 10 h | 237 | 28.7 % | 53.6 | 0.0049 | 0.0169 | +0.0044 |
| 10 h – 14 h | 209 | 25.3 % | 55.0 | 0.0111 | 0.0130 | +0.0005 |
| nad 18 h | 181 | 21.9 % | 54.1 | 0.0185 | 0.0110 | -0.0015 |
| 14 h – 18 h | 200 | 24.2 % | 59.5 | 0.0231 | 0.0102 | -0.0023 |

Parametre, ktorými sa dá s tým niečo spraviť: `maxHoldBars`, `slBufferAtr`, `sweepKind`, `tradeDirection`, `tradeStartH`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0185 % | -0.0001 % ± 0.0034 | +5.53 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0185 % | -0.0001 % ± 0.0035 | +5.37 | 100.0 |

Edge je odlisitelny od nahody (5.5 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 201 | 13.6 | 54.2 | 0.0129 | 52 |
| 2022-12 - 2024-03 | 219 | 14.8 | 55.7 | 0.0082 | 26 |
| 2024-03 - 2025-06 | 208 | 14.1 | 57.2 | 0.0180 | 77 |
| 2025-06 - 2026-09 | 199 | 13.5 | 54.8 | 0.0108 | 40 |

Hranice pre úsek veľkosti posledného obdobia: +0.0018 až +0.0235 % (medián 0.0126).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 40. percentile, teda v medziach +0.0018 až +0.0235 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 9** — 2022-03-29T11:46 až 2022-04-21T09:38, spolu +878.41.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-03-29T11:46 | 2022-03-29T11:48 | +61.06 | +0.23 | `take_profit` |
| 2 | 2022-03-29T16:51 | 2022-03-29T17:47 | +121.87 | +0.38 | `take_profit` |
| 3 | 2022-03-29T22:34 | 2022-03-30T01:27 | +80.91 | +0.14 | `take_profit` |
| 4 | 2022-03-31T17:33 | 2022-03-31T19:01 | +76.69 | +0.33 | `take_profit` |
| 5 | 2022-04-01T14:27 | 2022-04-01T14:30 | +158.08 | +0.23 | `take_profit` |
| 6 | 2022-04-07T10:37 | 2022-04-07T11:03 | +74.38 | +0.16 | `take_profit` |
| 7 | 2022-04-08T16:38 | 2022-04-08T17:18 | +108.38 | +0.34 | `take_profit` |
| 8 | 2022-04-11T19:10 | 2022-04-11T19:28 | +124.80 | +0.36 | `take_profit` |
| 9 | 2022-04-21T09:11 | 2022-04-21T09:38 | +72.24 | +0.20 | `take_profit` |

**Straty za sebou: 7** — 2021-11-02T00:15 až 2021-11-19T18:28, spolu -596.26, rovnako dlhých sérií 3.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2021-11-02T00:15 | 2021-11-02T00:33 | -85.02 | -0.03 | `stop_loss` |
| 2 | 2021-11-03T17:27 | 2021-11-03T18:00 | -81.39 | -0.12 | `stop_loss` |
| 3 | 2021-11-08T12:18 | 2021-11-08T12:55 | -81.14 | -0.09 | `stop_loss` |
| 4 | 2021-11-08T21:28 | 2021-11-09T00:27 | -76.81 | -0.21 | `stop_loss` |
| 5 | 2021-11-09T17:18 | 2021-11-09T18:48 | -110.94 | -0.41 | `stop_loss` |
| 6 | 2021-11-10T02:30 | 2021-11-10T02:34 | -103.65 | -0.06 | `stop_loss` |
| 7 | 2021-11-19T18:13 | 2021-11-19T18:28 | -57.30 | -0.15 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0125 %**, medián 0.0126 %, 90 % interval 0.0074–0.0179 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 2.3 %, 95. percentil 4.1 %, najhorší 8.5 %
- najdlhšia séria strát: medián 7, 95. percentil 10 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **941** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=68ee4c4a -->
**Posudok (AI, 11. 10. 2026)** — profil PREŠIEL SMERNICAMI č. 1 z testovania podľa smernice (krok 7).

1. **Na čo sa to hodí a na čo nie.** MNQ 3m, Candle Range Theory s výberom likvidity, WR 55 %, payoff 1,07, drží ~11 barov. Veľmi rovnomerné roky (+3,1 až +4,8 %).
2. **Má to potenciál?** Áno, ale s najmenšou rezervou: +5,5 σ, rovnomerné roky, no break-even len 0,0125 % (~7× poplatok) — najtenšia vrstva z deviatich.
3. **Čo dorobiť.** Žiadna skupina obchodov výsledok nekazí — filtrovať nie je čo; zlepšiť sa dá len vstupom. Analytika ráta obchody z prekrývajúcich sa okien 23/24 a 24/25 (september 2024) dvakrát — najdlhšia séria strát môže byť o 1–2 nadsadená.
4. **Čo otestovať ďalej.** NAS100 z Dukascopy (krok 8) — rovnaký smer výsledku = jav trhu, nie dát; 2× poplatok (`--fee 3.51e-05`) a 1 tick sklzu navyše; forward test 4–8 týždňov na 1 MNQ (krok 9).
5. **Je to použiteľné?** Podmienečne — rozhodne stres 2× poplatok + 1 tick sklzu; pri break-even 0,0125 % je to hranica.
6. **Čo by som pridal.** Cieľ na opačnú stranu rangu namiesto RR — pri stabilnom WR by zvýšil payoff.
<!-- POSUDOK KONIEC -->
