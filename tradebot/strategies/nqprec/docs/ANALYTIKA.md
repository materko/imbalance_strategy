# Základná analytika — NQ PRECISION 1.0 (`nqprec`)

Zmerané 2026-10-31 na `MNQ/USD` 1m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `/Users/martin/IBS/.nightsearch/base_nqprec.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy nqprec \
   --profile /Users/martin/IBS/.nightsearch/base_nqprec.json \
   --pair MNQ/USD \
   --timeframe 1m \
   --fee 1.755e-05
```

## V čom je dobrá

- 468 obchodov spolu — na štatistiku dosť
- break-even 0.0038 % je nad poplatkom 0.0018 % (rezerva +0.0020 bodu)
- drawdown drží: 95. percentil 13.4 %
- odlíšiteľná od náhody (+3.3 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-08 na 25. percentile toho, čo stratégia vyrobí sama od seba)
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 3 z 5 referenčných okien (20211001-20221001, 20250904-20260904 v strate)
- edge nad poplatkom len v 83 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 99 | -6.50 | -0.0102 | 7.8 | 82.8 | +16/-2 | `20261031-084939-943ff9` |
| 20221001-20231001 | 84 | +4.66 | 0.0120 | 0.7 | 92.9 | +32/-1 | `20261031-084945-f586db` |
| 20231001-20241001 | 87 | +4.38 | 0.0087 | 1.3 | 94.2 | +27/-1 | `20261031-084954-395590` |
| 20240904-20250904 | 96 | +7.07 | 0.0105 | 1.1 | 92.7 | +20/-1 | `20261031-085006-49924f` |
| 20250904-20260904 | 106 | -1.77 | 0.0002 | 8.1 | 84.0 | +37/-3 | `20261031-085015-cc52df` |

Zisková v **3 z 5** okien, obchodov spolu 468, break-even celkom 0.0038 %. Okná sa prekrývajú, 4 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+0.87 ATR za 5 barov)
- medián držania 0 barov grafu
- winrate 88.89 %, payoff 0.15
- 0.26 obchodov za deň
- šikmosť výnosov -4.089

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 90 %, `stop_loss` 6.2 %, `session_end` 3.8 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0090 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| žiadna | 408 | 87.2 % | 87.8 | 0.0025 | 0.0128 | +0.0090 |
| NFP | 21 | 4.5 % | 95.2 | 0.0074 | 0.0037 | -0.0001 |
| FOMC | 12 | 2.6 % | 91.7 | 0.0077 | 0.0037 | -0.0001 |
| CPI | 26 | 5.6 % | 100.0 | 0.0212 | 0.0029 | -0.0009 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bez udalosti | 408 | 87.2 % | 87.8 | 0.0025 | 0.0128 | +0.0090 |
| pred vyhlásením | 13 | 2.8 % | 92.3 | 0.0077 | 0.0037 | -0.0001 |
| po vyhlásení | 47 | 10.0 % | 97.9 | 0.0144 | 0.0027 | -0.0011 |

**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 14 h | 319 | 68.2 % | 86.2 | 0.0009 | 0.0102 | +0.0064 |
| 15 h | 149 | 31.8 % | 94.6 | 0.0102 | 0.0009 | -0.0029 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0038 % | -0.0002 % ± 0.0012 | +3.27 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0038 % | -0.0005 % ± 0.0018 | +2.44 | 99.3 |

Edge je odlisitelny od nahody (3.3 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 118 | 8.1 | 83.9 | -0.0072 | 1 |
| 2022-12 - 2024-03 | 104 | 7.1 | 95.2 | 0.0115 | 98 |
| 2024-03 - 2025-06 | 116 | 7.9 | 92.2 | 0.0101 | 94 |
| 2025-06 - 2026-08 | 130 | 8.9 | 85.4 | 0.0011 | 25 |

Hranice pre úsek veľkosti posledného obdobia: -0.0037 až +0.0102 % (medián 0.0044).

**DRZI** — posledné obdobie (2025-06 - 2026-08) je na 25. percentile, teda v medziach -0.0037 až +0.0102 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 40** — 2025-08-25T14:00 až 2026-01-22T15:00, spolu +453.81.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-08-25T14:00 | 2025-08-25T14:00 | +9.85 | +0.02 | `take_profit` |
| 2 | 2025-08-28T14:00 | 2025-08-28T14:00 | +15.84 | +0.03 | `take_profit` |
| 3 | 2025-09-01T14:00 | 2025-09-01T14:00 | +2.35 | +0.01 | `take_profit` |
| 4 | 2025-09-15T14:00 | 2025-09-15T14:00 | +5.30 | +0.01 | `take_profit` |
| 5 | 2025-09-16T14:00 | 2025-09-16T14:00 | +5.78 | +0.01 | `take_profit` |
| 6 | 2025-09-19T14:00 | 2025-09-19T14:00 | +6.76 | +0.01 | `take_profit` |
| 7 | 2025-09-22T14:00 | 2025-09-22T14:00 | +4.25 | +0.01 | `take_profit` |
| 8 | 2025-09-23T14:00 | 2025-09-23T14:00 | +6.25 | +0.01 | `take_profit` |
| 9 | 2025-10-03T14:00 | 2025-10-03T14:00 | +7.74 | +0.02 | `take_profit` |
| 10 | 2025-10-08T14:00 | 2025-10-08T14:00 | +5.73 | +0.01 | `take_profit` |
| 11 | 2025-10-13T14:00 | 2025-10-13T14:00 | +15.25 | +0.03 | `take_profit` |
| 12 | 2025-10-15T14:00 | 2025-10-15T14:00 | +14.24 | +0.03 | `take_profit` |
| 13 | 2025-10-17T14:00 | 2025-10-17T14:02 | +17.26 | +0.03 | `take_profit` |
| 14 | 2025-10-23T14:00 | 2025-10-23T14:00 | +8.73 | +0.02 | `take_profit` |
| 15 | 2025-10-29T14:00 | 2025-10-29T14:00 | +6.15 | +0.01 | `take_profit` |
| 16 | 2025-10-31T14:00 | 2025-10-31T14:00 | +9.67 | +0.02 | `take_profit` |
| 17 | 2025-11-04T15:00 | 2025-11-04T15:00 | +11.68 | +0.02 | `take_profit` |
| 18 | 2025-11-05T15:00 | 2025-11-05T15:00 | +12.70 | +0.02 | `take_profit` |
| 19 | 2025-11-06T15:00 | 2025-11-06T15:00 | +13.21 | +0.03 | `take_profit` |
| 20 | 2025-11-12T15:00 | 2025-11-12T15:00 | +13.20 | +0.03 | `take_profit` |
| 21 | 2025-11-14T15:00 | 2025-11-14T15:06 | +19.25 | +0.04 | `take_profit` |
| 22 | 2025-11-17T15:00 | 2025-11-17T15:00 | +14.73 | +0.03 | `take_profit` |
| 23 | 2025-11-18T15:00 | 2025-11-18T15:00 | +21.78 | +0.04 | `take_profit` |
| 24 | 2025-11-19T15:00 | 2025-11-19T15:00 | +15.75 | +0.03 | `take_profit` |
| 25 | 2025-11-26T15:00 | 2025-11-26T15:00 | +13.73 | +0.03 | `take_profit` |
| 26 | 2025-12-01T15:00 | 2025-12-01T15:00 | +5.72 | +0.01 | `take_profit` |
| 27 | 2025-12-08T15:00 | 2025-12-08T15:01 | +10.19 | +0.02 | `take_profit` |
| 28 | 2025-12-11T15:00 | 2025-12-11T15:00 | +15.22 | +0.03 | `take_profit` |
| 29 | 2025-12-15T15:00 | 2025-12-15T15:00 | +13.23 | +0.03 | `take_profit` |
| 30 | 2025-12-16T15:00 | 2025-12-16T15:00 | +18.72 | +0.04 | `take_profit` |
| 31 | 2025-12-19T15:00 | 2025-12-19T15:00 | +11.71 | +0.02 | `take_profit` |
| 32 | 2025-12-30T15:00 | 2025-12-30T15:00 | +9.19 | +0.02 | `take_profit` |
| 33 | 2025-12-31T15:00 | 2025-12-31T15:00 | +9.20 | +0.02 | `take_profit` |
| 34 | 2026-01-06T15:00 | 2026-01-06T15:00 | +9.69 | +0.02 | `take_profit` |
| 35 | 2026-01-08T15:00 | 2026-01-08T15:00 | +12.70 | +0.02 | `take_profit` |
| 36 | 2026-01-14T15:00 | 2026-01-14T15:00 | +16.70 | +0.03 | `take_profit` |
| 37 | 2026-01-16T15:00 | 2026-01-16T15:00 | +9.69 | +0.02 | `take_profit` |
| 38 | 2026-01-19T15:00 | 2026-01-19T15:00 | +5.72 | +0.01 | `take_profit` |
| 39 | 2026-01-21T15:00 | 2026-01-21T15:00 | +15.72 | +0.03 | `take_profit` |
| 40 | 2026-01-22T15:00 | 2026-01-22T15:00 | +13.20 | +0.03 | `take_profit` |

**Straty za sebou: 3** — 2026-04-29T14:00 až 2026-05-01T14:00, spolu -106.78.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-04-29T14:00 | 2026-04-29T14:07 | -63.41 | -0.12 | `session_end` |
| 2 | 2026-04-30T14:00 | 2026-04-30T14:07 | -41.41 | -0.08 | `session_end` |
| 3 | 2026-05-01T14:00 | 2026-05-01T14:00 | -1.96 | -0.00 | `take_profit` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0038 %**, medián 0.0040 %, 90 % interval 0.0001–0.0073 %
- P(edge > poplatok) = **83.4 %**
- max drawdown: medián 6.0 %, 95. percentil 13.4 %, najhorší 28.9 %
- najdlhšia séria strát: medián 3, 95. percentil 3 obchodov
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
<!-- POSUDOK cisla=7ddfe4dd -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na MNQ, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Jedna snímka denne o 10:00 NY, cieľ 0,3 ATR a stop 2,2 ATR — skalp s WR ~85–90 %, ktorý žije z toho, že jedna strata nezožerie 7 výhier.
2. **Má potenciál?** Zisková v 3 z 5 okien, 468 obchodov (~94 za rok), break-even 0.0038 % (nad poplatkom 0,0018 %), +3.3 sigma proti náhodnému vstupu; WR 88.89 % pri payoffe 0.15. Odložený rok 25/26: -1.77 % PnL, break-even 0.0002 %. Kladné okná sú skôr vlastnosť vzorky ako stabilný jav.
3. **Čo dorobiť.** Predloha je tickova (9:59:55); na 1m sa vstupuje o 5 s neskôr — overiť na 1m, či sa to neoplatí posunúť na 9:59. Pomer cieľ / stop 0,14 je na hrane: pri poplatku a sklze rozhoduje každý tick.
4. **Čo otestovať ďalej.** Smernica (`nqprec*`: stop / cieľ v ATR, výstup v čase, čas snímky, filtre); hlavne 2× poplatok a sklz (krok 9) — pri payoffe 0,15 je to rozhodujúce.
5. **Použiteľné?** **V defaultoch predlohy nie** — edge nad poplatkom nie je stabilný po rokoch; šancu má len s nastavením, ktoré nájde smernica (inak vyradiť).
6. **Čo by som pridal.** Cieľ aspoň 0,5 ATR a stop 1 ATR (payoff ~0,5), alebo vstup len v smere včerajška / overnightu.

<!-- POSUDOK KONIEC -->
