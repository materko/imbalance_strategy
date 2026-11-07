# Základná analytika — SPRÁVY 3.0 (`spravy`)

Zmerané 2026-10-30 na `MNQ/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/spravy_PRESIEL_SMERNICAMI_SPR_VY_3_0_MGC_1_2026-10-30.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy spravy \
   --profile .nightsearch/checkup/spravy_PRESIEL_SMERNICAMI_SPR_VY_3_0_MGC_1_2026-10-30.json \
   --pair MNQ/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 273 obchodov spolu — na štatistiku dosť
- break-even 0.0228 % je nad poplatkom 0.0018 % (rezerva +0.0210 bodu)
- drawdown drží: 95. percentil 9.1 %
- edge drží aj v poslednom období (2025-06 - 2026-09 na 85. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- zisková v 4 z 5 referenčných okien (20211001-20221001 v strate)
- edge nad poplatkom len v 85 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- proti náhode len +1.8 sigma: náznak, nie dôkaz
- charakter: protitrendová (mean reversion) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- 61.2 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 'do 10' vlastnosti 'Deň v mesiaci': 73 obchodov (26.7 %), bez nej by break-even bol o +0.0253 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 57 | -3.78 | -0.0698 | 5.5 | 33.3 | +3/-6 | `20261030-051120-37aa42` |
| 20221001-20231001 | 56 | +0.58 | 0.0135 | 1.6 | 37.5 | +3/-9 | `20261030-051123-28b2ea` |
| 20231001-20241001 | 55 | +0.51 | 0.0095 | 1.6 | 40.0 | +3/-5 | `20261030-051126-b757ed` |
| 20240904-20250904 | 57 | +5.76 | 0.0734 | 1.7 | 43.9 | +4/-9 | `20261030-051129-e396ec` |
| 20250904-20260904 | 53 | +5.18 | 0.0565 | 2.1 | 49.1 | +7/-5 | `20261030-051133-7c9c5e` |

Zisková v **4 z 5** okien, obchodov spolu 273, break-even celkom 0.0228 %. Okná sa prekrývajú, 5 obchodov započítaných dvakrát vypadlo.

## Charakter

**Protitrendová (mean reversion)** (istota priemerná)

- vstup proti poslednému pohybu (-0.51 ATR za 5 barov)
- medián držania 11 barov grafu
- winrate 40.29 %, payoff 1.768
- 0.15 obchodov za deň
- šikmosť výnosov +0.363

- **Čo je normálne:** Winrate nad 60 % a payoff pod 1 je pri tomto type v poriadku — zarába sa frekvenciou, nie veľkosťou.
- **Na čo pozor:** Jedna strata môže zmazať mesiac. Stop je tu dôležitejší než vstup a `maxLossDollar` aj drawdown limit majú väčší význam než pri ostatných typoch.
- **Čo ladiť:** Stop a filter režimu (v trende protitrendová stratégia dostáva rany). Ladiť RR nahor väčšinou len zníži winrate a nič nepridá.

Výstupy: `session_end` 61.2 %, `stop_loss` 35.9 %, `take_profit` 2.9 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'do 10' vlastnosti 'Deň v mesiaci': 73 obchodov (26.7 %), break-even -0.05 % oproti 0.0228 % celku. Bez nej by break-even bol 0.0481 % (+0.0253). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 10 | 73 | 26.7 % | 39.7 | -0.0500 | 0.0481 | +0.0253 |
| 10 – 13 | 67 | 24.5 % | 43.3 | 0.0244 | 0.0223 | -0.0005 |
| 13 – 26 | 73 | 26.7 % | 35.6 | 0.0457 | 0.0144 | -0.0084 |
| nad 26 | 60 | 22.0 % | 43.3 | 0.0767 | 0.0070 | -0.0158 |

**Smer**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| short | 153 | 56.0 % | 37.2 | 0.0052 | 0.0468 | +0.0240 |
| long | 120 | 44.0 % | 44.2 | 0.0468 | 0.0052 | -0.0176 |

**Volatilita voči normálu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 1.664 – 2.245 | 68 | 24.9 % | 38.2 | -0.0357 | 0.0424 | +0.0196 |
| 1.306 – 1.664 | 68 | 24.9 % | 32.4 | 0.0080 | 0.0278 | +0.0050 |
| nad 2.245 | 68 | 24.9 % | 44.1 | 0.0371 | 0.0189 | -0.0039 |
| do 1.306 | 69 | 25.3 % | 46.4 | 0.0776 | 0.0016 | -0.0212 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0228 % | -0.0003 % ± 0.0127 | +1.81 | 97.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0228 % | 0.0018 % ± 0.0179 | +1.17 | 88.5 |

Naznak, ale nie dokaz (1.8 sigma, percentil 97.0). Take rozdiely nahoda robi bezne.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 71 | 4.8 | 38.0 | -0.0472 | 3 |
| 2022-12 - 2024-03 | 68 | 4.6 | 32.4 | -0.0040 | 28 |
| 2024-03 - 2025-06 | 67 | 4.5 | 43.3 | 0.0445 | 75 |
| 2025-06 - 2026-09 | 67 | 4.5 | 47.8 | 0.0601 | 85 |

Hranice pre úsek veľkosti posledného obdobia: -0.0421 až +0.0874 % (medián 0.0189).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 85. percentile, teda v medziach -0.0421 až +0.0874 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 7** — 2026-06-17T18:00 až 2026-07-30T17:25, spolu +3716.55.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-06-17T18:00 | 2026-06-17T20:50 | +669.87 | +1.10 | `session_end` |
| 2 | 2026-06-25T13:30 | 2026-06-25T17:25 | +773.40 | +1.28 | `session_end` |
| 3 | 2026-06-30T15:00 | 2026-06-30T15:55 | +307.37 | +0.51 | `session_end` |
| 4 | 2026-07-14T13:30 | 2026-07-14T14:25 | +251.41 | +0.42 | `session_end` |
| 5 | 2026-07-15T12:45 | 2026-07-15T13:46 | +302.40 | +0.50 | `take_profit` |
| 6 | 2026-07-29T18:00 | 2026-07-29T20:50 | +829.57 | +1.50 | `session_end` |
| 7 | 2026-07-30T13:30 | 2026-07-30T17:25 | +582.53 | +1.04 | `session_end` |

**Straty za sebou: 11** — 2023-08-01T15:00 až 2023-10-11T15:40, spolu -923.34.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-08-01T15:00 | 2023-08-01T15:55 | -7.11 | -0.02 | `session_end` |
| 2 | 2023-08-10T13:30 | 2023-08-10T14:25 | -197.08 | -0.64 | `session_end` |
| 3 | 2023-08-11T12:45 | 2023-08-11T12:48 | -54.56 | -0.18 | `stop_loss` |
| 4 | 2023-08-29T15:00 | 2023-08-29T15:55 | -133.08 | -0.43 | `session_end` |
| 5 | 2023-08-31T13:30 | 2023-08-31T13:31 | -67.09 | -0.22 | `stop_loss` |
| 6 | 2023-09-13T13:30 | 2023-09-13T14:25 | -39.09 | -0.13 | `session_end` |
| 7 | 2023-09-14T12:45 | 2023-09-14T13:55 | -88.09 | -0.28 | `stop_loss` |
| 8 | 2023-09-20T18:00 | 2023-09-20T19:12 | -213.08 | -0.69 | `stop_loss` |
| 9 | 2023-09-29T13:30 | 2023-09-29T13:48 | -43.55 | -0.15 | `stop_loss` |
| 10 | 2023-10-03T15:00 | 2023-10-03T15:55 | -38.53 | -0.13 | `session_end` |
| 11 | 2023-10-11T12:45 | 2023-10-11T15:40 | -42.07 | -0.14 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0228 %**, medián 0.0218 %, 90 % interval -0.0103–0.0554 %
- P(edge > poplatok) = **84.8 %**
- max drawdown: medián 4.5 %, 95. percentil 9.1 %, najhorší 19.8 %
- najdlhšia séria strát: medián 10, 95. percentil 15 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

> **Posudok je starší než čísla** (písal sa k vzorke `f83f2c4d`, tu je `7863a9d7`). Nech ho AI prepíše — čísla nižšie sa medzitým zmenili.

<!-- POSUDOK cisla=f83f2c4d -->

**Posudok východiskového profilu SPRÁVY 3.0 (29. 10. 2026, MGC 5m, 1 kontrakt; pravidlá: FOMC PRED do 16:55 NY, CPI a JOLTS proti prvej hodine, PPI proti prvým 15 min so stopom za extrémom a cieľom 1 : 3, PCE v smere nohy 15 → 60; cieľ RRR len pri PPI).**

1. **Na čo sa hodí a na čo nie.** Zlato (MGC / GC, na MT5 XAUUSD) na 5m grafe, len v dni červených správ USA, ~55 obchodov za rok, 0,15 obchodu za deň. Doplnkový modul k iným stratégiám, nie celodenný systém. 72 % obchodov končí na čase — výstup v čase je zámer (pri FOMC a PCE cieľ odrezal veľké pohyby), nie chyba seansy. Na indexy sa pravidlá neprenášajú (MNQ a ES reagujú na CPI / NFP opačne).
2. **Má to potenciál?** Áno. Zisková v 5 z 5 okien, +4,8 sigma proti náhodnému vstupu (1.0 malo +3,6), break-even 0,08 % = 44× poplatok, edge nad poplatkom v 100 % vzoriek, 95. percentil prepadu 1,2 %. Pravidlá majú vysvetlenie (otočenie driftu pred FOMC, návrat výstrelu PPI). Varovanie: výsledok drží hlavne posledné okno (break-even 0,17 % proti 0,008–0,055 % v predošlých) — býčí trh zlata 2025–26; prvé dve obdobia sú na 5. a 10. percentile vlastnej krivky. Pravidlá aj RRR pri PPI sú vybrané z mnohých variantov na tých istých dátach (~45 hypotéz + 25 variantov cieľa), čísla sú preto optimistické.
3. **Čo treba dorobiť.** Kalendár: 2027 doplnený pre FOMC, CPI, NFP, PPI, ISM, CLAIMS; JOLTS, PCE, GDP, RETAIL čakajú na zverejnenie (test `test_kalendar_pokryva_buducnost` pripomenie). Porovnanie s exportom ForexFactory na hube (presunuté správy) a upozornenie na karte Live. Sklz pri vstupe PRED presne v čase FOMC (volatilita 10× bežnej) — v teste je fill na open baru 14:00, naživo môže byť horší.
4. **Čo otestovať ďalej.** `python -m tester.robust` (krok 9: 2× poplatok, vstup o sviečku neskôr — pre PRED rozhodujúce), `cli matrix` na XAU/USD (Dukascopy). Každé pravidlo samostatne po rokoch: CPI slabne (PF 6,4 → 1,0), PCE a JOLTS boli v prvých dvoch oknách pod 1 — ak to tak ostane aj na XAU, vypnúť prepínačom. RRR pri PPI (1 : 3) overiť na XAU, kým sa zapne aj inde.
5. **Použiteľné?** **Áno, ako modul na zlato po správach**, s 1 kontraktom alebo malým rizikom. Pod hranicou smernice (150 obchodov za rok) — výnimka používateľa 29. 10. 2026.
6. **Čo by som pridal.** Pravidlo 2 (tlačovka FOMC) je pripravené: zisk +2 831 $ samostatne, ale s ním padne prvé okno na PF 0,95 — zapnúť až po overení na XAU. Filter „prekvapenie“ (veľkosť nohy voči bežnej reakcii na ten typ správy), aby FADE bral len prehnané reakcie.

<!-- POSUDOK KONIEC -->
