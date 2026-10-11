# Základná analytika — DAILY OPEN 1.0 (`dailyopen`)

Zmerané 2026-10-11 na `MNQ/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/dailyopen_PRESIEL_SMERNICAMI_DAILY_OPEN_1_2026-10-11.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy dailyopen \
   --profile .nightsearch/checkup/dailyopen_PRESIEL_SMERNICAMI_DAILY_OPEN_1_2026-10-11.json \
   --pair MNQ/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 767 obchodov spolu — na štatistiku dosť
- break-even 0.0177 % je nad poplatkom 0.0018 % (rezerva +0.0159 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 2.8 %
- odlíšiteľná od náhody (+4.7 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 27. percentile toho, čo stratégia vyrobí sama od seba)
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 152 | +2.56 | 0.0201 | 1.4 | 90.1 | +26/-1 | `20261011-071905-307d8f` |
| 20221001-20231001 | 146 | +0.77 | 0.0078 | 1.7 | 87.7 | +17/-2 | `20261011-071908-98b978` |
| 20231001-20241001 | 158 | +4.84 | 0.0277 | 0.7 | 93.0 | +47/-1 | `20261011-071911-d7e710` |
| 20240904-20250904 | 159 | +4.41 | 0.0213 | 1.0 | 92.5 | +29/-2 | `20261011-071914-2107e4` |
| 20250904-20260904 | 152 | +2.40 | 0.0109 | 1.1 | 90.1 | +28/-1 | `20261011-071917-c241c3` |

Zisková v **5 z 5** okien, obchodov spolu 767, break-even celkom 0.0177 %.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.28 ATR za 5 barov)
- medián držania 2 barov grafu
- winrate 90.74 %, payoff 0.153
- 0.43 obchodov za deň
- šikmosť výnosov -3.066

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 90.7 %, `stop_loss` 9.3 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0095 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 680 | 88.7 % | 90.3 | 0.0163 | 0.0272 | +0.0095 |
| proti trendu | 87 | 11.3 % | 94.2 | 0.0272 | 0.0163 | -0.0014 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.7289 | 192 | 25.0 % | 87.5 | 0.0044 | 0.0228 | +0.0051 |
| 0.8754 – 0.9524 | 192 | 25.0 % | 91.2 | 0.0202 | 0.0169 | -0.0008 |
| 0.7289 – 0.8754 | 192 | 25.0 % | 91.7 | 0.0216 | 0.0164 | -0.0013 |
| nad 0.9524 | 191 | 24.9 % | 92.7 | 0.0265 | 0.0149 | -0.0028 |

**Hodina vstupu (UTC)** (riadi `entryStartH`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 14 h | 441 | 57.5 % | 90.0 | 0.0146 | 0.0220 | +0.0043 |
| 16 h | 31 | 4.0 % | 90.3 | 0.0160 | 0.0178 | +0.0001 |
| 15 h | 291 | 37.9 % | 91.8 | 0.0221 | 0.0151 | -0.0026 |

Parametre, ktorými sa dá s tým niečo spraviť: `entryStartH`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0192 % | 0.0005 % ± 0.0039 | +4.74 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0192 % | 0.0003 % ± 0.0048 | +3.98 | 100.0 |

Edge je odlisitelny od nahody (4.7 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 187 | 12.7 | 88.8 | 0.0135 | 28 |
| 2022-12 - 2024-03 | 189 | 12.8 | 91.0 | 0.0235 | 78 |
| 2024-03 - 2025-06 | 208 | 14.1 | 92.3 | 0.0216 | 71 |
| 2025-06 - 2026-09 | 183 | 12.4 | 90.7 | 0.0129 | 27 |

Hranice pre úsek veľkosti posledného obdobia: +0.0046 až +0.0305 % (medián 0.0175).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 27. percentile, teda v medziach +0.0046 až +0.0305 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 47** — 2023-11-13T16:35 až 2024-02-22T15:29, spolu +1813.84.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-11-13T16:35 | 2023-11-13T16:47 | +39.91 | +0.13 | `take_profit` |
| 2 | 2023-11-16T15:00 | 2023-11-17T08:34 | +38.38 | +0.12 | `take_profit` |
| 3 | 2023-11-20T15:00 | 2023-11-20T16:06 | +39.38 | +0.12 | `take_profit` |
| 4 | 2023-11-20T16:10 | 2023-11-20T18:03 | +38.88 | +0.12 | `take_profit` |
| 5 | 2023-11-22T15:00 | 2023-11-22T15:35 | +34.87 | +0.11 | `take_profit` |
| 6 | 2023-11-22T15:40 | 2023-11-22T17:10 | +37.37 | +0.12 | `take_profit` |
| 7 | 2023-11-27T15:05 | 2023-11-27T15:09 | +38.37 | +0.12 | `take_profit` |
| 8 | 2023-11-28T15:10 | 2023-11-28T15:39 | +38.88 | +0.12 | `take_profit` |
| 9 | 2023-12-05T15:00 | 2023-12-05T15:00 | +38.89 | +0.12 | `take_profit` |
| 10 | 2023-12-05T15:10 | 2023-12-05T15:22 | +38.46 | +0.10 | `take_profit` |
| 11 | 2023-12-07T15:20 | 2023-12-07T15:22 | +39.46 | +0.17 | `take_profit` |
| 12 | 2023-12-08T15:10 | 2023-12-08T15:24 | +39.41 | +0.16 | `take_profit` |
| 13 | 2023-12-11T15:00 | 2023-12-11T15:47 | +38.35 | +0.12 | `take_profit` |
| 14 | 2023-12-11T15:55 | 2023-12-11T18:04 | +38.57 | +0.13 | `take_profit` |
| 15 | 2023-12-12T16:05 | 2023-12-12T18:48 | +37.84 | +0.11 | `take_profit` |
| 16 | 2023-12-13T15:00 | 2023-12-13T15:11 | +38.33 | +0.12 | `take_profit` |
| 17 | 2023-12-13T15:15 | 2023-12-13T15:44 | +38.83 | +0.12 | `take_profit` |
| 18 | 2023-12-15T15:15 | 2023-12-15T15:28 | +38.89 | +0.13 | `take_profit` |
| 19 | 2023-12-18T15:05 | 2023-12-18T17:02 | +37.81 | +0.11 | `take_profit` |
| 20 | 2023-12-20T15:10 | 2023-12-20T15:30 | +39.49 | +0.13 | `take_profit` |
| 21 | 2023-12-21T15:25 | 2023-12-21T20:37 | +38.58 | +0.15 | `take_profit` |
| 22 | 2023-12-27T15:25 | 2023-12-27T16:42 | +39.45 | +0.08 | `take_profit` |
| 23 | 2024-01-05T15:10 | 2024-01-05T16:01 | +39.49 | +0.13 | `take_profit` |
| 24 | 2024-01-08T15:05 | 2024-01-08T15:48 | +38.33 | +0.12 | `take_profit` |
| 25 | 2024-01-09T15:15 | 2024-01-09T16:02 | +39.32 | +0.12 | `take_profit` |
| 26 | 2024-01-09T16:10 | 2024-01-09T16:16 | +37.97 | +0.11 | `take_profit` |
| 27 | 2024-01-10T15:20 | 2024-01-10T15:30 | +39.55 | +0.12 | `take_profit` |
| 28 | 2024-01-16T15:05 | 2024-01-16T15:05 | +38.12 | +0.10 | `take_profit` |
| 29 | 2024-01-16T15:20 | 2024-01-16T15:24 | +39.13 | +0.15 | `take_profit` |
| 30 | 2024-01-18T15:20 | 2024-01-18T15:27 | +36.75 | +0.11 | `take_profit` |
| 31 | 2024-01-19T16:15 | 2024-01-19T17:23 | +40.29 | +0.12 | `take_profit` |
| 32 | 2024-01-24T15:20 | 2024-01-24T15:35 | +38.78 | +0.13 | `take_profit` |
| 33 | 2024-01-25T15:05 | 2024-01-25T15:08 | +38.26 | +0.11 | `take_profit` |
| 34 | 2024-01-26T15:30 | 2024-01-26T15:33 | +38.27 | +0.11 | `take_profit` |
| 35 | 2024-01-26T15:35 | 2024-01-26T15:50 | +38.76 | +0.11 | `take_profit` |
| 36 | 2024-01-29T15:20 | 2024-01-29T17:00 | +37.76 | +0.11 | `take_profit` |
| 37 | 2024-02-01T15:15 | 2024-02-01T15:29 | +38.48 | +0.10 | `take_profit` |
| 38 | 2024-02-01T15:35 | 2024-02-01T17:06 | +37.84 | +0.10 | `take_profit` |
| 39 | 2024-02-02T15:45 | 2024-02-02T16:30 | +38.26 | +0.11 | `take_profit` |
| 40 | 2024-02-02T16:35 | 2024-02-02T16:45 | +38.26 | +0.11 | `take_profit` |
| 41 | 2024-02-07T15:00 | 2024-02-07T15:10 | +39.25 | +0.11 | `take_profit` |
| 42 | 2024-02-07T15:15 | 2024-02-07T15:24 | +38.75 | +0.11 | `take_profit` |
| 43 | 2024-02-08T15:05 | 2024-02-08T15:48 | +39.75 | +0.11 | `take_profit` |
| 44 | 2024-02-09T15:05 | 2024-02-09T15:16 | +38.24 | +0.11 | `take_profit` |
| 45 | 2024-02-12T15:50 | 2024-02-12T16:23 | +38.25 | +0.12 | `take_profit` |
| 46 | 2024-02-14T15:25 | 2024-02-14T20:50 | +38.91 | +0.15 | `take_profit` |
| 47 | 2024-02-22T15:25 | 2024-02-22T15:29 | +38.67 | +0.13 | `take_profit` |

**Straty za sebou: 2** — 2022-11-15T15:05 až 2022-11-22T08:38, spolu -501.44, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-11-15T15:05 | 2022-11-15T18:19 | -250.34 | -1.04 | `stop_loss` |
| 2 | 2022-11-21T15:10 | 2022-11-22T08:38 | -251.10 | -0.80 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0177 %**, medián 0.0178 %, 90 % interval 0.0113–0.0239 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 1.7 %, 95. percentil 2.8 %, najhorší 5.2 %
- najdlhšia séria strát: medián 2, 95. percentil 2 obchodov
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
<!-- POSUDOK cisla=09ce1668 -->
**Posudok (AI, 11. 10. 2026)** — profil PREŠIEL SMERNICAMI č. 1 z testovania podľa smernice (krok 7).

1. **Na čo sa to hodí a na čo nie.** MNQ, prieraz polnočného zavretia, TP malý / SL veľký (payoff 0,15, WR 91 %). Pevný počet kontraktov. Typ 'veľa malých výhier, zriedka veľká strata' — séria výhier až 47.
2. **Má to potenciál?** Áno, štatisticky: +4,7 σ, 5 z 5 rokov. Ale rezerva je len v tom, že veľká strata príde zriedka; break-even 0,018 % a rok 22/23 takmer nulový (+0,8 %).
3. **Čo dorobiť.** Pri payoffe 0,15 zmaže jedna strata ~7 výhier — sklz na stope je kritický. Overiť správanie pri gape cez noc. Analytika ráta obchody z prekrývajúcich sa okien 23/24 a 24/25 (september 2024) dvakrát — najdlhšia séria strát môže byť o 1–2 nadsadená.
4. **Čo otestovať ďalej.** NAS100 z Dukascopy (krok 8) — rovnaký smer výsledku = jav trhu, nie dát; 2× poplatok (`--fee 3.51e-05`) a 1 tick sklzu navyše; forward test 4–8 týždňov na 1 MNQ (krok 9).
5. **Je to použiteľné?** Podmienečne — na ostrý účet len s 2× poplatkom a sklzom v pluse; inak je to pekné WR bez rezervy.
6. **Čo by som pridal.** Stop podľa ATR namiesto pevných bodov, aby sa strata prispôsobila volatilite.
<!-- POSUDOK KONIEC -->
