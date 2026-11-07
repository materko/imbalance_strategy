# Základná analytika — WILLIAMS %R LONG 1.0 (MGC) (`wprmgc`)

Zmerané 2026-11-07 na `MGC/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/wprmgc_PRESIEL_SMERNICAMI_WILLIAMS_R_MGC_1_2026-11-07.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy wprmgc \
   --profile .nightsearch/checkup/wprmgc_PRESIEL_SMERNICAMI_WILLIAMS_R_MGC_1_2026-11-07.json \
   --pair MGC/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 776 obchodov spolu — na štatistiku dosť
- break-even 0.0204 % je nad poplatkom 0.0018 % (rezerva +0.0186 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 2.3 %
- edge drží aj v poslednom období (2025-06 - 2026-09 na 91. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: protitrendová (mean reversion) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- proti náhode len +1.2 sigma: náznak, nie dôkaz
- 100 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 'do 100 R' vlastnosti 'Plánovaný RR': 756 obchodov (97.4 %), bez nej by break-even bol o +0.0118 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 191 | +0.96 | 0.0100 | 0.4 | 68.1 | +9/-3 | `20261107-051952-c02584` |
| 20221001-20231001 | 203 | +1.08 | 0.0102 | 0.4 | 65.0 | +8/-4 | `20261107-051955-cfa4ba` |
| 20231001-20241001 | 173 | +1.78 | 0.0158 | 0.5 | 72.8 | +10/-4 | `20261107-051959-045451` |
| 20240904-20250904 | 126 | +2.74 | 0.0236 | 1.0 | 75.4 | +15/-3 | `20261107-052002-89d5e4` |
| 20250904-20260904 | 96 | +5.42 | 0.0405 | 1.7 | 68.8 | +8/-5 | `20261107-052005-4f12c2` |

Zisková v **5 z 5** okien, obchodov spolu 776, break-even celkom 0.0204 %. Okná sa prekrývajú, 13 obchodov započítaných dvakrát vypadlo.

## Charakter

**Protitrendová (mean reversion)** (istota dobrá)

- vstup proti poslednému pohybu (-1.98 ATR za 5 barov)
- medián držania 27 barov grafu
- winrate 69.33 %, payoff 0.732
- 0.43 obchodov za deň
- šikmosť výnosov -1.358

- **Čo je normálne:** Winrate nad 60 % a payoff pod 1 je pri tomto type v poriadku — zarába sa frekvenciou, nie veľkosťou.
- **Na čo pozor:** Jedna strata môže zmazať mesiac. Stop je tu dôležitejší než vstup a `maxLossDollar` aj drawdown limit majú väčší význam než pri ostatných typoch.
- **Čo ladiť:** Stop a filter režimu (v trende protitrendová stratégia dostáva rany). Ladiť RR nahor väčšinou len zníži winrate a nič nepridá.

Výstupy: `session_end` 100 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'do 100 R' vlastnosti 'Plánovaný RR': 756 obchodov (97.4 %), break-even 0.0201 % oproti 0.0204 % celku. Bez nej by break-even bol 0.0322 % (+0.0118). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**Plánovaný RR**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 100 R | 756 | 97.4 % | 69.0 | 0.0201 | 0.0322 | +0.0118 |
| nad 100 R | 20 | 2.6 % | 80.0 | 0.0322 | 0.0201 | -0.0003 |

**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 5 h | 240 | 30.9 % | 68.3 | 0.0073 | 0.0261 | +0.0057 |
| 11 h – 18 h | 191 | 24.6 % | 66.5 | 0.0156 | 0.0220 | +0.0016 |
| 5 h – 11 h | 178 | 22.9 % | 70.2 | 0.0280 | 0.0180 | -0.0024 |
| nad 18 h | 167 | 21.5 % | 73.0 | 0.0368 | 0.0161 | -0.0043 |

**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| proti trendu | 195 | 25.1 % | 64.1 | 0.0046 | 0.0257 | +0.0053 |
| s trendom | 581 | 74.9 % | 71.1 | 0.0257 | 0.0046 | -0.0158 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0204 % | 0.0068 % ± 0.0115 | +1.18 | 88.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0204 % | 0.0068 % ± 0.0115 | +1.18 | 88.0 |

Naznak, ale nie dokaz (1.2 sigma, percentil 88.0). Take rozdiely nahoda robi bezne.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 241 | 16.3 | 66.8 | 0.0110 | 16 |
| 2022-12 - 2024-03 | 246 | 16.7 | 67.5 | 0.0061 | 6 |
| 2024-03 - 2025-06 | 167 | 11.3 | 73.7 | 0.0222 | 66 |
| 2025-06 - 2026-09 | 122 | 8.3 | 72.1 | 0.0404 | 91 |

Hranice pre úsek veľkosti posledného obdobia: -0.0006 až +0.0480 % (medián 0.0179).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 91. percentile, teda v medziach -0.0006 až +0.0480 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 15** — 2025-07-29T15:44 až 2025-09-03T00:15, spolu +526.88.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-07-29T15:44 | 2025-07-29T16:51 | +8.81 | +0.03 | `session_end` |
| 2 | 2025-07-31T10:18 | 2025-07-31T11:30 | +6.82 | +0.02 | `session_end` |
| 3 | 2025-08-01T16:21 | 2025-08-01T17:33 | +78.81 | +0.23 | `session_end` |
| 4 | 2025-08-07T02:28 | 2025-08-07T03:54 | +23.79 | +0.07 | `session_end` |
| 5 | 2025-08-13T11:24 | 2025-08-13T13:42 | +13.80 | +0.04 | `session_end` |
| 6 | 2025-08-20T08:35 | 2025-08-20T09:06 | +53.82 | +0.16 | `session_end` |
| 7 | 2025-08-20T15:54 | 2025-08-20T16:15 | +65.81 | +0.19 | `session_end` |
| 8 | 2025-08-22T19:15 | 2025-08-24T23:51 | +4.80 | +0.01 | `session_end` |
| 9 | 2025-08-26T18:04 | 2025-08-26T18:36 | +31.80 | +0.09 | `session_end` |
| 10 | 2025-08-28T10:03 | 2025-08-28T10:30 | +30.79 | +0.09 | `session_end` |
| 11 | 2025-08-28T12:48 | 2025-08-28T13:48 | +57.79 | +0.17 | `session_end` |
| 12 | 2025-08-28T15:21 | 2025-08-28T16:06 | +51.78 | +0.15 | `session_end` |
| 13 | 2025-08-29T19:00 | 2025-08-29T19:21 | +30.77 | +0.09 | `session_end` |
| 14 | 2025-09-01T07:05 | 2025-09-01T08:03 | +11.76 | +0.03 | `session_end` |
| 15 | 2025-09-02T23:30 | 2025-09-03T00:15 | +55.74 | +0.15 | `session_end` |

**Straty za sebou: 5** — 2026-03-16T14:30 až 2026-03-27T09:30, spolu -785.24.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-03-16T14:30 | 2026-03-16T17:03 | -171.76 | -0.34 | `session_end` |
| 2 | 2026-03-17T05:54 | 2026-03-17T07:24 | -99.76 | -0.20 | `session_end` |
| 3 | 2026-03-23T15:18 | 2026-03-23T17:06 | -330.55 | -0.75 | `session_end` |
| 4 | 2026-03-25T03:45 | 2026-03-25T07:12 | -120.60 | -0.26 | `session_end` |
| 5 | 2026-03-27T07:54 | 2026-03-27T09:30 | -62.57 | -0.14 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0204 %**, medián 0.0199 %, 90 % interval 0.0116–0.0299 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 1.3 %, 95. percentil 2.3 %, najhorší 4.9 %
- najdlhšia séria strát: medián 5, 95. percentil 6 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

> **Posudok je starší než čísla** (písal sa k vzorke `c7396f92`, tu je `14fd4fff`). Nech ho AI prepíše — čísla nižšie sa medzitým zmenili.

<!-- POSUDOK cisla=c7396f92 -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na MGC, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Protitrendový long po prepade %R, výstup pri prvom odraze; vysoký WR, nízky payoff — na indexoch citlivý na trend dole (bez stopu). Tu na MGC (zlato) — logika robená pre index, čísla to treba brať ako test prenosu.
2. **Má potenciál?** Zisková v 5 z 5 okien, 3633 obchodov (~727 za rok), break-even 0.0060 % (nad poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 66.47 % pri payoffe 0.553. Odložený rok 25/26: +24.02 % PnL, break-even 0.0059 %. Jav je skôr skutočný ako vlastnosť vzorky.
3. **Čo dorobiť.** Stop: predloha bez stopu, jeden prepad (2022) zmaže roky; povinne `stopPct` alebo ATR stop a filter trendu (len nad EMA 200).
4. **Čo otestovať ďalej.** Smernica (`wpr*`: TF, perióda, prahy vstupu a výstupu, stop, trend); rozhodne, či s filtrom trendu ostane edge nad poplatkom.
5. **Použiteľné?** **Áno ako kandidát do smernice** — defaulty predlohy sú ziskové vo väčšine okien a edge je nad poplatkom; rozhodne hľadanie a odložený rok.
6. **Čo by som pridal.** Len long nad EMA 200 dňa a výstup na %R −50 — klasická Connorsova úprava RSI(2)/%R stratégií.

<!-- POSUDOK KONIEC -->
