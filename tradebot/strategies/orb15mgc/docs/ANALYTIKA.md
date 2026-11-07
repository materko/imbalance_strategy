# Základná analytika — ORB 15/5 1.0 (MGC) (`orb15mgc`)

Zmerané 2026-11-03 na `MGC/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/orb15mgc_PRESIEL_SMERNICAMI_ORB_15_5_MGC_1_2026-11-03.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy orb15mgc \
   --profile .nightsearch/checkup/orb15mgc_PRESIEL_SMERNICAMI_ORB_15_5_MGC_1_2026-11-03.json \
   --pair MGC/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 897 obchodov spolu — na štatistiku dosť
- break-even 0.0489 % je nad poplatkom 0.0018 % (rezerva +0.0471 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 6.7 %
- odlíšiteľná od náhody (+3.5 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 84. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- najhoršia skupina 'do 14 h' vlastnosti 'Hodina vstupu (UTC)': 493 obchodov (55.0 %), bez nej by break-even bol o +0.0358 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 136 | +0.99 | 0.0136 | 2.4 | 34.6 | +4/-12 | `20261103-051333-5bdcf5` |
| 20221001-20231001 | 153 | +2.46 | 0.0273 | 1.7 | 35.3 | +5/-11 | `20261103-051336-81e0da` |
| 20231001-20241001 | 212 | +5.71 | 0.0374 | 1.4 | 36.8 | +5/-10 | `20261103-051339-e7b20d` |
| 20240904-20250904 | 217 | +6.88 | 0.0335 | 2.4 | 40.1 | +6/-7 | `20261103-051342-33b44f` |
| 20250904-20260904 | 205 | +23.52 | 0.0791 | 5.2 | 40.0 | +5/-7 | `20261103-051346-c9ee8c` |

Zisková v **5 z 5** okien, obchodov spolu 897, break-even celkom 0.0489 %. Okná sa prekrývajú, 26 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+1.50 ATR za 5 barov)
- medián držania 26 barov grafu
- winrate 37.79 %, payoff 2.361
- 0.5 obchodov za deň
- šikmosť výnosov +1.525

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 62.2 %, `take_profit` 37.7 %, `force_exit` 0.1 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'do 14 h' vlastnosti 'Hodina vstupu (UTC)': 493 obchodov (55.0 %), break-even 0.0192 % oproti 0.0489 % celku. Bez nej by break-even bol 0.0847 % (+0.0358). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 14 h | 493 | 55.0 % | 35.9 | 0.0192 | 0.0847 | +0.0358 |
| 14 h – 16 h | 247 | 27.5 % | 38.9 | 0.0543 | 0.0468 | -0.0021 |
| nad 16 h | 157 | 17.5 % | 42.0 | 0.1344 | 0.0311 | -0.0178 |

**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.1858 % – 0.2618 % | 224 | 25.0 % | 31.7 | -0.0002 | 0.0641 | +0.0152 |
| do 0.1858 % | 225 | 25.1 % | 37.3 | 0.0106 | 0.0598 | +0.0109 |
| 0.2618 % – 0.4157 % | 224 | 25.0 % | 40.6 | 0.0322 | 0.0548 | +0.0059 |
| nad 0.4157 % | 224 | 25.0 % | 41.5 | 0.1365 | 0.0150 | -0.0339 |

**Deň v týždni**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| streda | 196 | 21.9 % | 31.1 | -0.0020 | 0.0633 | +0.0144 |
| pondelok | 166 | 18.5 % | 34.9 | 0.0107 | 0.0579 | +0.0090 |
| piatok | 198 | 22.1 % | 38.9 | 0.0630 | 0.0451 | -0.0038 |
| utorok | 166 | 18.5 % | 44.6 | 0.0844 | 0.0408 | -0.0081 |
| štvrtok | 170 | 19.0 % | 40.6 | 0.0964 | 0.0378 | -0.0111 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0489 % | 0.0124 % ± 0.0104 | +3.52 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0489 % | 0.0176 % ± 0.0105 | +2.99 | 99.9 |

Edge je odlisitelny od nahody (3.5 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 183 | 12.4 | 35.0 | 0.0216 | 20 |
| 2022-12 - 2024-03 | 193 | 13.1 | 34.2 | 0.0280 | 23 |
| 2024-03 - 2025-06 | 276 | 18.7 | 40.6 | 0.0371 | 31 |
| 2025-06 - 2026-09 | 245 | 16.6 | 39.6 | 0.0737 | 84 |

Hranice pre úsek veľkosti posledného obdobia: +0.0062 až +0.0926 % (medián 0.0482).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 84. percentile, teda v medziach +0.0062 až +0.0926 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 6** — 2025-08-26T14:50 až 2025-09-03T23:55, spolu +2059.60.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-08-26T14:50 | 2025-08-26T19:49 | +125.80 | +0.37 | `take_profit` |
| 2 | 2025-08-26T19:50 | 2025-08-28T16:34 | +374.79 | +1.09 | `take_profit` |
| 3 | 2025-08-28T16:35 | 2025-08-29T15:15 | +299.77 | +0.86 | `take_profit` |
| 4 | 2025-08-29T15:20 | 2025-09-02T01:46 | +658.76 | +1.88 | `take_profit` |
| 5 | 2025-09-02T13:45 | 2025-09-02T14:44 | +218.75 | +0.62 | `take_profit` |
| 6 | 2025-09-02T14:45 | 2025-09-03T23:55 | +381.74 | +1.07 | `force_exit` |

**Straty za sebou: 12** — 2022-03-08T14:50 až 2022-04-05T14:08, spolu -975.29.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-03-08T14:50 | 2022-03-09T09:53 | -233.71 | -1.14 | `stop_loss` |
| 2 | 2022-03-09T15:20 | 2022-03-09T17:33 | -76.70 | -0.38 | `stop_loss` |
| 3 | 2022-03-10T14:40 | 2022-03-10T14:43 | -53.71 | -0.27 | `stop_loss` |
| 4 | 2022-03-10T14:50 | 2022-03-10T14:55 | -52.71 | -0.26 | `stop_loss` |
| 5 | 2022-03-11T14:40 | 2022-03-14T09:03 | -115.69 | -0.58 | `stop_loss` |
| 6 | 2022-03-24T14:20 | 2022-03-25T10:37 | -68.69 | -0.35 | `stop_loss` |
| 7 | 2022-03-25T14:10 | 2022-03-28T03:51 | -60.68 | -0.31 | `stop_loss` |
| 8 | 2022-03-30T13:40 | 2022-03-31T02:15 | -67.68 | -0.35 | `stop_loss` |
| 9 | 2022-03-31T13:50 | 2022-03-31T19:48 | -53.68 | -0.28 | `stop_loss` |
| 10 | 2022-04-01T13:50 | 2022-04-01T14:30 | -90.68 | -0.47 | `stop_loss` |
| 11 | 2022-04-04T14:50 | 2022-04-04T15:31 | -47.68 | -0.25 | `stop_loss` |
| 12 | 2022-04-05T13:45 | 2022-04-05T14:08 | -53.68 | -0.28 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0489 %**, medián 0.0485 %, 90 % interval 0.0266–0.0719 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 3.9 %, 95. percentil 6.7 %, najhorší 12.3 %
- najdlhšia séria strát: medián 13, 95. percentil 18 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

> **Posudok je starší než čísla** (písal sa k vzorke `49442113`, tu je `c5a1a2a9`). Nech ho AI prepíše — čísla nižšie sa medzitým zmenili.

<!-- POSUDOK cisla=49442113 -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na MGC, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Intraday index futures od 9:45 NY, jeden obchod denne; na zlate OR 9:30–9:45 nemá zmysel otvorenia akciovej burzy, čísla tam ukazujú skôr šum. Tu na MGC (zlato) — logika robená pre index, čísla to treba brať ako test prenosu.
2. **Má potenciál?** Zisková v 3 z 5 okien, 1134 obchodov (~227 za rok), break-even 0.0089 % (nad poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 43.56 % pri payoffe 1.401. Odložený rok 25/26: +30.61 % PnL, break-even 0.0169 %. Kladné okná sú skôr vlastnosť vzorky ako stabilný jav.
3. **Čo dorobiť.** Skúsiť OR 5 / 30 / 60 min a cieľ RR 0,75–1,5; filter predošlého dňa a knôtu majú byť v mriežke oboma smermi; pre prop koniec dňa.
4. **Čo otestovať ďalej.** Smernica (mriežka glsearch `orb15*`: dĺžka OR, RR, filtre, trend EMA, limit / IBS / pin bar); rozhodne odložený rok 25/26, ktorý je pri MNQ v defaultoch stratový.
5. **Použiteľné?** **V defaultoch predlohy nie** — edge nad poplatkom nie je stabilný po rokoch; šancu má len s nastavením, ktoré nájde smernica (inak vyradiť).
6. **Čo by som pridal.** Smer dňa z VWAP od 9:30 alebo z polohy voči včerajšiemu zavretiu — ORB bez kontextu chytá aj falošné prierazy rána.

<!-- POSUDOK KONIEC -->
