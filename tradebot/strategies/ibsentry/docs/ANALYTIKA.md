# Základná analytika — IBS Entry Zone (`ibsentry`)

Zmerané 2026-10-11 na `MNQ/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/ibsentry_presiel1_2026-10-11.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy ibsentry \
   --profile .nightsearch/checkup/ibsentry_presiel1_2026-10-11.json \
   --pair MNQ/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 817 obchodov spolu — na štatistiku dosť
- break-even 0.0181 % je nad poplatkom 0.0018 % (rezerva +0.0163 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 13.5 %
- odlíšiteľná od náhody (+8.3 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 82. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'bežný deň' vlastnosti 'Sviatok na burze v USA': 786 obchodov (96.2 %), bez nej by break-even bol o +0.0101 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 222 | +50.98 | 0.0230 | 8.3 | 76.1 | +13/-3 | `20261011-071201-cbd665` |
| 20221001-20231001 | 124 | +12.62 | 0.0098 | 9.1 | 71.8 | +8/-3 | `20261011-071215-a25342` |
| 20231001-20241001 | 98 | +9.88 | 0.0089 | 6.1 | 72.5 | +8/-3 | `20261011-071227-e2e095` |
| 20240904-20250904 | 161 | +34.78 | 0.0190 | 6.7 | 75.8 | +13/-3 | `20261011-071240-2dfee3` |
| 20250904-20260904 | 212 | +58.13 | 0.0222 | 6.7 | 78.3 | +18/-4 | `20261011-071253-682ea1` |

Zisková v **5 z 5** okien, obchodov spolu 817, break-even celkom 0.0181 %.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+0.71 ATR za 5 barov)
- medián držania 2.3 barov grafu
- winrate 75.52 %, payoff 0.497
- 0.45 obchodov za deň
- šikmosť výnosov -1.443

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 75.8 %, `stop_loss` 24.2 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'bežný deň' vlastnosti 'Sviatok na burze v USA': 786 obchodov (96.2 %), break-even 0.0176 % oproti 0.0181 % celku. Bez nej by break-even bol 0.0282 % (+0.0101). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bežný deň | 786 | 96.2 % | 75.3 | 0.0176 | 0.0282 | +0.0101 |
| deň po sviatku | 17 | 2.1 % | 82.3 | 0.0258 | 0.0179 | -0.0002 |
| deň pred sviatkom | 11 | 1.3 % | 81.8 | 0.0418 | 0.0177 | -0.0004 |

**S trendom, alebo proti** (riadi `useStructureFilter`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 575 | 70.4 % | 73.7 | 0.0144 | 0.0263 | +0.0082 |
| proti trendu | 242 | 29.6 % | 79.8 | 0.0263 | 0.0144 | -0.0037 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 7 – 14 | 205 | 25.1 % | 70.7 | 0.0092 | 0.0209 | +0.0028 |
| do 7 | 211 | 25.8 % | 74.9 | 0.0167 | 0.0185 | +0.0004 |
| 14 – 23 | 203 | 24.8 % | 76.8 | 0.0196 | 0.0175 | -0.0006 |
| nad 23 | 198 | 24.2 % | 79.8 | 0.0268 | 0.0153 | -0.0028 |

Parametre, ktorými sa dá s tým niečo spraviť: `closeAtSessionEnd`, `minSlDistance`, `rrRatio`, `sess2TradeStartH`, `state2MaxBars`, `tradeDirection`, `useStructureFilter`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0211 % | -0.0000 % ± 0.0026 | +8.27 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0211 % | -0.0001 % ± 0.0026 | +8.04 | 100.0 |

Edge je odlisitelny od nahody (8.3 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 267 | 18.1 | 74.2 | 0.0179 | 48 |
| 2022-12 - 2024-03 | 112 | 7.6 | 75.9 | 0.0159 | 41 |
| 2024-03 - 2025-06 | 209 | 14.2 | 73.2 | 0.0135 | 23 |
| 2025-06 - 2026-09 | 229 | 15.5 | 79.0 | 0.0232 | 82 |

Hranice pre úsek veľkosti posledného obdobia: +0.0089 až +0.0267 % (medián 0.0182).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 82. percentile, teda v medziach +0.0089 až +0.0267 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 18** — 2026-01-29T18:09 až 2026-02-12T15:54, spolu +9058.81.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-01-29T18:09 | 2026-01-29T18:10 | +439.50 | +0.11 | `take_profit` |
| 2 | 2026-01-30T07:27 | 2026-01-30T07:37 | +449.30 | +0.07 | `take_profit` |
| 3 | 2026-01-30T17:54 | 2026-01-30T18:00 | +467.68 | +0.15 | `take_profit` |
| 4 | 2026-01-30T20:01 | 2026-01-30T20:05 | +455.59 | +0.11 | `take_profit` |
| 5 | 2026-01-30T21:11 | 2026-02-01T23:00 | +1417.22 | +0.46 | `take_profit` |
| 6 | 2026-02-04T15:33 | 2026-02-04T15:34 | +458.66 | +0.18 | `take_profit` |
| 7 | 2026-02-04T15:54 | 2026-02-04T16:01 | +442.35 | +0.09 | `take_profit` |
| 8 | 2026-02-04T18:32 | 2026-02-04T18:42 | +442.76 | +0.13 | `take_profit` |
| 9 | 2026-02-04T18:45 | 2026-02-04T18:50 | +443.28 | +0.10 | `take_profit` |
| 10 | 2026-02-05T00:24 | 2026-02-05T00:38 | +471.90 | +0.12 | `take_profit` |
| 11 | 2026-02-05T15:51 | 2026-02-05T15:52 | +444.65 | +0.13 | `take_profit` |
| 12 | 2026-02-05T18:00 | 2026-02-05T18:10 | +452.55 | +0.18 | `take_profit` |
| 13 | 2026-02-05T19:33 | 2026-02-05T20:25 | +390.05 | +0.26 | `take_profit` |
| 14 | 2026-02-05T21:09 | 2026-02-05T21:19 | +423.10 | +0.21 | `take_profit` |
| 15 | 2026-02-09T14:39 | 2026-02-09T14:40 | +457.95 | +0.23 | `take_profit` |
| 16 | 2026-02-10T15:18 | 2026-02-10T15:24 | +472.64 | +0.08 | `take_profit` |
| 17 | 2026-02-11T18:19 | 2026-02-11T18:27 | +461.73 | +0.08 | `take_profit` |
| 18 | 2026-02-12T15:54 | 2026-02-12T15:54 | +467.88 | +0.08 | `take_profit` |

**Straty za sebou: 5** — 2024-09-18T19:18 až 2024-10-03T15:40, spolu -4713.40.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-09-18T19:18 | 2024-09-18T19:20 | -953.97 | -0.19 | `stop_loss` |
| 2 | 2024-09-18T19:18 | 2024-09-18T19:20 | -953.97 | -0.19 | `stop_loss` |
| 3 | 2024-09-27T17:30 | 2024-09-27T18:00 | -979.22 | -0.24 | `stop_loss` |
| 4 | 2024-09-27T17:30 | 2024-09-27T18:00 | -979.22 | -0.24 | `stop_loss` |
| 5 | 2024-10-03T15:00 | 2024-10-03T15:40 | -847.02 | -0.42 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0181 %**, medián 0.0181 %, 90 % interval 0.0133–0.0228 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 7.6 %, 95. percentil 13.5 %, najhorší 33.7 %
- najdlhšia séria strát: medián 4, 95. percentil 5 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **2 494** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=2b15ffbe -->
**Posudok (AI, 11. 10. 2026)** — profil PREŠIEL SMERNICAMI č. 1 z testovania podľa smernice (krok 7).

1. **Na čo sa to hodí a na čo nie.** Na MNQ / NQ futures na 3m grafe s 1m detailom, intraday cez viac seáns (Ázia 0–3 NY,
   NY, popoludnie do 19:45). Je to scalp s malým cieľom: TP 0,5 R, medián držania 2,3 baru (~7 minút), winrate 75 %,
   payoff 0,5. Hodí sa na účet, ktorý znesie 3–5 strát po sebe (≈ 1 000 $ každá pri 1 MNQ s rizikom ~950 $).
   Nehodí sa tam, kde je plnenie horšie než na CME futures (široký spread CFD, oneskorenie platformy) —
   pri cieli 0,5 R rozhodne o výsledku každý tick. Na NAS100 CFD by to isté číslo znamenalo menej.
2. **Má to potenciál? Áno.** Za skutočným javom hovorí: 5 z 5 rokov v zisku, odložený rok 2025/26 najlepší (PF 1,81,
   optimalizátor ho nevidel), +8,3 σ proti náhodnému vstupu s tým istým SL/TP, edge neslabne (posledné obdobie
   82. percentil), break-even 0,0181 % na stranu je ~10× nad poplatkom (≈ 3,6 bodu MNQ na stranu, ~14 tickov —
   rezerva aj na sklz). Proti: roky 22/23 a 23/24 sú slabé (+12 % a +10 %, 98–124 obchodov), takže výsledok
   stojí najmä na volatilnejších rokoch; parametre vybralo hľadanie z ~16 000 kombinácií, čo samo vyberá šťastné nastavenia
   (preto platí prísnejšia hranica a odložený rok — ten prešiel).
3. **Čo dorobiť.** (a) Analytika ráta obchody z prekrývajúcich sa okien 23/24 a 24/25 dvakrát (séria strát 5 má
   dvojice rovnakých obchodov; skutočne najviac 3–4 straty po sebe) — opraviť deduplikáciu v sériách. (b) Obchody,
   ktoré vstúpia a vystúpia v tej istej minúte, závisia od poradia SL/TP vnútri 1m sviečky — overiť na tick dátach
   alebo forward testom. (c) Filter na slabé, pokojné roky: v rokoch s nízkou volatilitou ubudne obchodov aj zisku —
   filter volatility (`volFilter`) skúsiť ako ochranu, nie na ladenie výsledku.
4. **Čo otestovať ďalej.** Krok 8: ten istý profil na NAS100 (Dukascopy) — `cli run --strategy ibsentry --profile … --pair NAS100/USD
   --engine multicharts` — rovnaký smer výsledku = jav trhu, nie dát. Doplnky: 2× poplatok (`--fee 3.51e-05`) a
   1 tick sklzu navyše — pri TP 0,5 R je to najdôležitejší stres. Krok 9: parita s TradingView na 1–2 mesiacoch.
   Krok 10: forward test 4–8 týždňov na 1 MNQ, obchod po obchode proti webapp.
5. **Je to použiteľné? Áno, ako kandidát na forward test** — zatiaľ najlepšia stratégia z testovania podľa smernice.
   Na ostrý účet až po kroku 8 a 10; kým nie je overený sklz na krátkych obchodoch, nie je to hotové.
6. **Čo by som pridal.** Denný limit straty (napr. 2 stopy) — séria strát prichádza v zhlukoch v jednom-dvoch dňoch
   (2024-09-18, 2024-09-27) a pre prop účty (denný limit FTMO/Tradeify) je to rozhodujúce. A čiastočný posun stopu na
   vstup po 0,3 R, otestovaný len ako prepínač na kroku 10, nie hľadaním.
<!-- POSUDOK KONIEC -->
