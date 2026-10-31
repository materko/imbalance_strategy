# Základná analytika — NQ PRECISION 1.0 (MGC) (`nqprecmgc`)

Zmerané 2026-10-31 na `MGC/USD` 1m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `/Users/martin/IBS/.nightsearch/base_nqprecmgc.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy nqprecmgc \
   --profile /Users/martin/IBS/.nightsearch/base_nqprecmgc.json \
   --pair MGC/USD \
   --timeframe 1m \
   --fee 1.755e-05
```

## V čom je dobrá

- 291 obchodov spolu — na štatistiku dosť
- break-even 0.0025 % je nad poplatkom 0.0018 % (rezerva +0.0007 bodu)
- drawdown drží: 95. percentil 6.2 %
- odlíšiteľná od náhody (+2.3 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 78. percentile toho, čo stratégia vyrobí sama od seba)
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 2 z 5 referenčných okien (20221001-20231001, 20231001-20241001, 20240904-20250904 v strate)
- edge nad poplatkom len v 64 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 50 | +0.78 | 0.0061 | 0.2 | 84.0 | +20/-2 | `20261031-084944-5a9107` |
| 20221001-20231001 | 62 | -1.74 | -0.0056 | 1.8 | 75.8 | +10/-2 | `20261031-084950-e843c0` |
| 20231001-20241001 | 49 | -1.28 | -0.0042 | 1.4 | 69.4 | +10/-2 | `20261031-085002-ecf54e` |
| 20240904-20250904 | 54 | -1.24 | -0.0019 | 2.2 | 85.2 | +13/-1 | `20261031-085014-1d0923` |
| 20250904-20260904 | 78 | +4.54 | 0.0083 | 1.7 | 89.7 | +19/-2 | `20261031-085023-02ee10` |

Zisková v **2 z 5** okien, obchodov spolu 291, break-even celkom 0.0025 %. Okná sa prekrývajú, 2 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+0.55 ATR za 5 barov)
- medián držania 0 barov grafu
- winrate 81.79 %, payoff 0.244
- 0.16 obchodov za deň
- šikmosť výnosov -2.614

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 86.6 %, `stop_loss` 10.7 %, `session_end` 2.7 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0070 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 264 | 90.7 % | 81.8 | 0.0019 | 0.0095 | +0.0070 |
| proti trendu | 27 | 9.3 % | 81.5 | 0.0095 | 0.0019 | -0.0006 |

**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bežný deň | 264 | 90.7 % | 81.8 | 0.0018 | 0.0094 | +0.0069 |
| deň po sviatku | 12 | 4.1 % | 83.3 | 0.0106 | 0.0022 | -0.0003 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 8 – 16 | 72 | 24.7 % | 73.6 | -0.0085 | 0.0061 | +0.0036 |
| do 8 | 77 | 26.5 % | 79.2 | 0.0032 | 0.0023 | -0.0002 |
| nad 24 | 59 | 20.3 % | 84.8 | 0.0045 | 0.0020 | -0.0005 |
| 16 – 24 | 83 | 28.5 % | 89.2 | 0.0100 | -0.0004 | -0.0029 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0025 % | -0.0008 % ± 0.0014 | +2.33 | 99.5 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0025 % | -0.0012 % ± 0.0018 | +2.09 | 98.8 |

Edge je odlisitelny od nahody (2.3 sigma, percentil 99.5).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 62 | 4.2 | 82.3 | 0.0028 | 51 |
| 2022-12 - 2024-03 | 74 | 5.0 | 73.0 | -0.0027 | 11 |
| 2024-03 - 2025-06 | 59 | 4.0 | 81.4 | 0.0001 | 32 |
| 2025-06 - 2026-09 | 96 | 6.5 | 88.5 | 0.0053 | 78 |

Hranice pre úsek veľkosti posledného obdobia: -0.0036 až +0.0082 % (medián 0.0026).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 78. percentile, teda v medziach -0.0036 až +0.0082 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 26** — 2025-08-06T14:00 až 2025-12-05T15:00, spolu +217.62.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-08-06T14:00 | 2025-08-06T14:00 | +1.80 | +0.01 | `take_profit` |
| 2 | 2025-08-07T14:00 | 2025-08-07T14:00 | +3.79 | +0.01 | `take_profit` |
| 3 | 2025-08-14T14:00 | 2025-08-14T14:00 | +1.81 | +0.01 | `take_profit` |
| 4 | 2025-08-18T14:00 | 2025-08-18T14:00 | +2.81 | +0.01 | `take_profit` |
| 5 | 2025-08-28T14:00 | 2025-08-28T14:00 | +2.78 | +0.01 | `take_profit` |
| 6 | 2025-08-29T14:00 | 2025-08-29T14:00 | +0.78 | +0.00 | `take_profit` |
| 7 | 2025-09-01T14:00 | 2025-09-01T14:00 | +2.76 | +0.01 | `take_profit` |
| 8 | 2025-09-08T14:00 | 2025-09-08T14:01 | +6.71 | +0.02 | `take_profit` |
| 9 | 2025-09-19T14:00 | 2025-09-19T14:00 | +3.70 | +0.01 | `take_profit` |
| 10 | 2025-09-26T14:00 | 2025-09-26T14:00 | +8.67 | +0.02 | `take_profit` |
| 11 | 2025-10-09T14:00 | 2025-10-09T14:00 | +14.58 | +0.04 | `take_profit` |
| 12 | 2025-10-10T14:00 | 2025-10-10T14:00 | +9.60 | +0.02 | `take_profit` |
| 13 | 2025-10-13T14:00 | 2025-10-13T14:00 | +9.56 | +0.02 | `take_profit` |
| 14 | 2025-10-20T14:00 | 2025-10-20T14:00 | +9.48 | +0.02 | `take_profit` |
| 15 | 2025-10-21T14:00 | 2025-10-21T14:00 | +28.53 | +0.07 | `take_profit` |
| 16 | 2025-10-28T14:00 | 2025-10-28T14:00 | +19.61 | +0.05 | `take_profit` |
| 17 | 2025-10-30T14:00 | 2025-10-30T14:00 | +10.59 | +0.03 | `take_profit` |
| 18 | 2025-11-03T15:00 | 2025-11-03T15:00 | +1.58 | +0.00 | `take_profit` |
| 19 | 2025-11-04T15:00 | 2025-11-04T15:00 | +13.61 | +0.03 | `take_profit` |
| 20 | 2025-11-05T15:00 | 2025-11-05T15:00 | +1.60 | +0.00 | `take_profit` |
| 21 | 2025-11-18T15:00 | 2025-11-18T15:00 | +16.57 | +0.04 | `take_profit` |
| 22 | 2025-11-19T15:00 | 2025-11-19T15:00 | +10.55 | +0.03 | `take_profit` |
| 23 | 2025-11-20T15:00 | 2025-11-20T15:00 | +15.56 | +0.04 | `take_profit` |
| 24 | 2025-11-24T15:00 | 2025-11-24T15:00 | +8.57 | +0.02 | `take_profit` |
| 25 | 2025-12-03T15:00 | 2025-12-03T15:00 | +4.51 | +0.01 | `take_profit` |
| 26 | 2025-12-05T15:00 | 2025-12-05T15:00 | +7.50 | +0.02 | `take_profit` |

**Straty za sebou: 2** — 2022-07-29T14:00 až 2022-08-04T14:00, spolu -1.25, rovnako dlhých sérií 7.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-07-29T14:00 | 2022-07-29T14:00 | -0.62 | -0.00 | `take_profit` |
| 2 | 2022-08-04T14:00 | 2022-08-04T14:00 | -0.63 | -0.00 | `take_profit` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0025 %**, medián 0.0025 %, 90 % interval -0.0009–0.0058 %
- P(edge > poplatok) = **64.0 %**
- max drawdown: medián 3.1 %, 95. percentil 6.2 %, najhorší 12.9 %
- najdlhšia séria strát: medián 2, 95. percentil 3 obchodov
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
<!-- POSUDOK cisla=f449f889 -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na MGC, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Jedna snímka denne o 10:00 NY, cieľ 0,3 ATR a stop 2,2 ATR — skalp s WR ~85–90 %, ktorý žije z toho, že jedna strata nezožerie 7 výhier. Tu na MGC (zlato) — logika robená pre index, čísla to treba brať ako test prenosu.
2. **Má potenciál?** Zisková v 2 z 5 okien, 291 obchodov (~58 za rok), break-even 0.0025 % (nad poplatkom 0,0018 %), +2.3 sigma proti náhodnému vstupu; WR 81.79 % pri payoffe 0.244. Odložený rok 25/26: +4.54 % PnL, break-even 0.0083 %. Kladné okná sú skôr vlastnosť vzorky ako stabilný jav.
3. **Čo dorobiť.** Predloha je tickova (9:59:55); na 1m sa vstupuje o 5 s neskôr — overiť na 1m, či sa to neoplatí posunúť na 9:59. Pomer cieľ / stop 0,14 je na hrane: pri poplatku a sklze rozhoduje každý tick.
4. **Čo otestovať ďalej.** Smernica (`nqprec*`: stop / cieľ v ATR, výstup v čase, čas snímky, filtre); hlavne 2× poplatok a sklz (krok 9) — pri payoffe 0,15 je to rozhodujúce.
5. **Použiteľné?** **V defaultoch predlohy nie** — edge nad poplatkom nie je stabilný po rokoch; šancu má len s nastavením, ktoré nájde smernica (inak vyradiť).
6. **Čo by som pridal.** Cieľ aspoň 0,5 ATR a stop 1 ATR (payoff ~0,5), alebo vstup len v smere včerajška / overnightu.

<!-- POSUDOK KONIEC -->
