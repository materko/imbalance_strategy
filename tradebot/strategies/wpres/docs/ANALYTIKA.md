# Základná analytika — WILLIAMS %R LONG 1.0 (ES) (`wpres`)

Zmerané 2026-11-04 na `ES/USD` 1m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/wpres_PRESIEL_SMERNICAMI_WILLIAMS_R_ES_1_2026-11-04.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy wpres \
   --profile .nightsearch/checkup/wpres_PRESIEL_SMERNICAMI_WILLIAMS_R_ES_1_2026-11-04.json \
   --pair ES/USD \
   --timeframe 1m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 761 obchodov spolu — na štatistiku dosť
- break-even 0.0094 % je nad poplatkom 0.0018 % (rezerva +0.0076 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 6.1 %
- edge drží aj v poslednom období (2025-06 - 2026-09 na 38. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: protitrendová (mean reversion) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- proti náhode len +1.7 sigma: náznak, nie dôkaz
- 100 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 160 | +14.21 | 0.0141 | 2.0 | 75.6 | +11/-4 | `20261104-051317-ab72c8` |
| 20221001-20231001 | 141 | +11.22 | 0.0132 | 2.2 | 61.0 | +6/-8 | `20261104-051324-e91e51` |
| 20231001-20241001 | 172 | +4.75 | 0.0050 | 3.6 | 73.8 | +14/-2 | `20261104-051330-bac970` |
| 20240904-20250904 | 152 | +6.86 | 0.0063 | 2.3 | 74.3 | +8/-3 | `20261104-051336-91e039` |
| 20250904-20260904 | 145 | +14.03 | 0.0099 | 2.4 | 74.5 | +14/-4 | `20261104-051343-0bfb9d` |

Zisková v **5 z 5** okien, obchodov spolu 761, break-even celkom 0.0094 %. Okná sa prekrývajú, 9 obchodov započítaných dvakrát vypadlo.

## Charakter

**Protitrendová (mean reversion)** (istota dobrá)

- vstup proti poslednému pohybu (-1.14 ATR za 5 barov)
- medián držania 23 barov grafu
- winrate 72.27 %, payoff 0.657
- 0.42 obchodov za deň
- šikmosť výnosov +1.719

- **Čo je normálne:** Winrate nad 60 % a payoff pod 1 je pri tomto type v poriadku — zarába sa frekvenciou, nie veľkosťou.
- **Na čo pozor:** Jedna strata môže zmazať mesiac. Stop je tu dôležitejší než vstup a `maxLossDollar` aj drawdown limit majú väčší význam než pri ostatných typoch.
- **Čo ladiť:** Stop a filter režimu (v trende protitrendová stratégia dostáva rany). Ladiť RR nahor väčšinou len zníži winrate a nič nepridá.

Výstupy: `session_end` 100 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0053 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| žiadna | 677 | 89.0 % | 71.6 | 0.0087 | 0.0147 | +0.0053 |
| FOMC | 28 | 3.7 % | 75.0 | 0.0087 | 0.0094 | +0.0000 |
| CPI | 32 | 4.2 % | 71.9 | 0.0161 | 0.0091 | -0.0003 |
| NFP | 23 | 3.0 % | 87.0 | 0.0207 | 0.0090 | -0.0004 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bez udalosti | 677 | 89.0 % | 71.6 | 0.0087 | 0.0147 | +0.0053 |
| pred vyhlásením | 30 | 3.9 % | 73.3 | 0.0102 | 0.0093 | -0.0001 |
| po vyhlásení | 54 | 7.1 % | 79.6 | 0.0172 | 0.0088 | -0.0006 |

**Volatilita voči normálu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.541 | 192 | 25.2 % | 69.3 | 0.0019 | 0.0119 | +0.0025 |
| 0.541 – 0.753 | 189 | 24.8 % | 70.4 | 0.0083 | 0.0097 | +0.0003 |
| 0.753 – 1.14 | 190 | 25.0 % | 70.5 | 0.0087 | 0.0096 | +0.0002 |
| nad 1.14 | 190 | 25.0 % | 79.0 | 0.0186 | 0.0063 | -0.0031 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0094 % | 0.0018 % ± 0.0045 | +1.68 | 95.7 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0094 % | 0.0018 % ± 0.0045 | +1.68 | 95.7 |

Naznak, ale nie dokaz (1.7 sigma, percentil 95.7). Take rozdiely nahoda robi bezne.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 195 | 13.2 | 73.8 | 0.0145 | 93 |
| 2022-12 - 2024-03 | 185 | 12.6 | 68.1 | 0.0124 | 83 |
| 2024-03 - 2025-06 | 197 | 13.4 | 73.1 | 0.0046 | 6 |
| 2025-06 - 2026-09 | 184 | 12.5 | 73.9 | 0.0082 | 38 |

Hranice pre úsek veľkosti posledného obdobia: +0.0038 až +0.0152 % (medián 0.0092).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 38. percentile, teda v medziach +0.0038 až +0.0152 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 14** — 2023-12-22T09:54 až 2024-01-19T01:01, spolu +569.52, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-12-22T09:54 | 2023-12-22T10:13 | +16.59 | +0.01 | `session_end` |
| 2 | 2023-12-27T21:25 | 2023-12-27T21:38 | +41.52 | +0.02 | `session_end` |
| 3 | 2023-12-28T12:46 | 2023-12-28T13:04 | +29.02 | +0.01 | `session_end` |
| 4 | 2024-01-01T23:47 | 2024-01-02T00:03 | +41.54 | +0.02 | `session_end` |
| 5 | 2024-01-04T01:11 | 2024-01-04T01:52 | +16.66 | +0.01 | `session_end` |
| 6 | 2024-01-05T21:39 | 2024-01-05T21:56 | +54.19 | +0.02 | `session_end` |
| 7 | 2024-01-08T21:19 | 2024-01-08T21:22 | +66.58 | +0.03 | `session_end` |
| 8 | 2024-01-10T21:40 | 2024-01-10T23:23 | +104.04 | +0.04 | `session_end` |
| 9 | 2024-01-10T23:50 | 2024-01-11T00:26 | +29.04 | +0.01 | `session_end` |
| 10 | 2024-01-15T03:20 | 2024-01-15T03:34 | +41.55 | +0.02 | `session_end` |
| 11 | 2024-01-16T21:41 | 2024-01-16T23:50 | +41.58 | +0.02 | `session_end` |
| 12 | 2024-01-17T21:25 | 2024-01-17T21:36 | +16.63 | +0.01 | `session_end` |
| 13 | 2024-01-18T21:44 | 2024-01-18T23:52 | +16.56 | +0.01 | `session_end` |
| 14 | 2024-01-19T00:46 | 2024-01-19T01:01 | +54.05 | +0.02 | `session_end` |

**Straty za sebou: 8** — 2023-07-10T04:56 až 2023-07-26T17:08, spolu -1076.16.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-07-10T04:56 | 2023-07-10T06:19 | -582.76 | -0.26 | `session_end` |
| 2 | 2023-07-10T20:57 | 2023-07-10T22:29 | -70.30 | -0.03 | `session_end` |
| 3 | 2023-07-12T22:52 | 2023-07-12T23:41 | -20.42 | -0.01 | `session_end` |
| 4 | 2023-07-20T20:47 | 2023-07-20T23:05 | -70.51 | -0.03 | `session_end` |
| 5 | 2023-07-21T04:54 | 2023-07-21T05:56 | -8.02 | -0.00 | `session_end` |
| 6 | 2023-07-21T15:41 | 2023-07-21T16:22 | -70.54 | -0.03 | `session_end` |
| 7 | 2023-07-25T09:07 | 2023-07-25T09:50 | -33.06 | -0.01 | `session_end` |
| 8 | 2023-07-26T16:24 | 2023-07-26T17:08 | -220.55 | -0.10 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0094 %**, medián 0.0094 %, 90 % interval 0.0066–0.0122 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 3.5 %, 95. percentil 6.1 %, najhorší 12.7 %
- najdlhšia séria strát: medián 6, 95. percentil 9 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

> **Posudok je starší než čísla** (písal sa k vzorke `bd54b519`, tu je `fc3bc792`). Nech ho AI prepíše — čísla nižšie sa medzitým zmenili.

<!-- POSUDOK cisla=bd54b519 -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na ES, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Protitrendový long po prepade %R, výstup pri prvom odraze; vysoký WR, nízky payoff — na indexoch citlivý na trend dole (bez stopu). Tu na ES — rovnaká logika ako MNQ, prahy v ATR sa prispôsobia.
2. **Má potenciál?** Zisková v 2 z 5 okien, 3647 obchodov (~729 za rok), break-even -0.0001 % (pod poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 64.77 % pri payoffe 0.519. Odložený rok 25/26: +53.44 % PnL, break-even 0.0028 %. Kladné okná sú skôr vlastnosť vzorky ako stabilný jav.
3. **Čo dorobiť.** Stop: predloha bez stopu, jeden prepad (2022) zmaže roky; povinne `stopPct` alebo ATR stop a filter trendu (len nad EMA 200).
4. **Čo otestovať ďalej.** Smernica (`wpr*`: TF, perióda, prahy vstupu a výstupu, stop, trend); rozhodne, či s filtrom trendu ostane edge nad poplatkom.
5. **Použiteľné?** **V defaultoch predlohy nie** — edge nad poplatkom nie je stabilný po rokoch; šancu má len s nastavením, ktoré nájde smernica (inak vyradiť).
6. **Čo by som pridal.** Len long nad EMA 200 dňa a výstup na %R −50 — klasická Connorsova úprava RSI(2)/%R stratégií.

<!-- POSUDOK KONIEC -->
