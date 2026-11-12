# Základná analytika — MTK ORB (MGC) (`mtkorb`)

Zmerané 2026-11-12 na `MGC/USD` 1m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/mtkorb_PRESIEL_SMERNICAMI_MTK_ORB_MGC_1_2026-11-12.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy mtkorb \
   --profile .nightsearch/checkup/mtkorb_PRESIEL_SMERNICAMI_MTK_ORB_MGC_1_2026-11-12.json \
   --pair MGC/USD \
   --timeframe 1m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 202 obchodov spolu — na štatistiku dosť
- break-even 0.0340 % je nad poplatkom 0.0018 % (rezerva +0.0322 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 1.4 %
- odlíšiteľná od náhody (+3.8 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 93. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'piatok' vlastnosti 'Deň v týždni': 52 obchodov (25.7 %), bez nej by break-even bol o +0.0137 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 46 | +0.59 | 0.0230 | 0.3 | 60.9 | +4/-5 | `20261112-174452-b9ba3a` |
| 20221001-20231001 | 42 | +0.51 | 0.0209 | 0.3 | 66.7 | +6/-3 | `20261112-174458-b09bd1` |
| 20231001-20241001 | 48 | +0.66 | 0.0207 | 0.6 | 62.5 | +17/-6 | `20261112-174504-88d615` |
| 20240904-20250904 | 40 | +0.13 | 0.0050 | 0.8 | 60.0 | +7/-3 | `20261112-174510-c13aa9` |
| 20250904-20260904 | 28 | +3.39 | 0.0862 | 0.5 | 75.0 | +7/-2 | `20261112-174516-2c5112` |

Zisková v **5 z 5** okien, obchodov spolu 202, break-even celkom 0.0340 %. Okná sa prekrývajú, 2 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+2.00 ATR za 5 barov)
- medián držania 39 barov grafu
- winrate 64.36 %, payoff 0.921
- 0.11 obchodov za deň
- šikmosť výnosov -0.39

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 64.4 %, `stop_loss` 35.6 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'piatok' vlastnosti 'Deň v týždni': 52 obchodov (25.7 %), break-even -0.0044 % oproti 0.034 % celku. Bez nej by break-even bol 0.0477 % (+0.0137). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Deň v týždni**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| piatok | 52 | 25.7 % | 55.8 | -0.0044 | 0.0477 | +0.0137 |
| štvrtok | 49 | 24.3 % | 67.3 | 0.0234 | 0.0370 | +0.0030 |
| pondelok | 27 | 13.4 % | 55.6 | 0.0255 | 0.0353 | +0.0013 |
| streda | 40 | 19.8 % | 67.5 | 0.0606 | 0.0273 | -0.0067 |
| utorok | 34 | 16.8 % | 76.5 | 0.0802 | 0.0239 | -0.0101 |

**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.2116 % | 51 | 25.2 % | 54.9 | -0.0046 | 0.0458 | +0.0118 |
| 0.2116 % – 0.274 % | 51 | 25.2 % | 54.9 | -0.0018 | 0.0454 | +0.0114 |
| 0.274 % – 0.3583 % | 50 | 24.8 % | 80.0 | 0.0622 | 0.0249 | -0.0091 |
| nad 0.3583 % | 50 | 24.8 % | 68.0 | 0.0724 | 0.0190 | -0.0150 |

**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 14 h – 15 h | 37 | 18.3 % | 56.8 | -0.0039 | 0.0430 | +0.0090 |
| do 14 h | 135 | 66.8 % | 64.4 | 0.0313 | 0.0389 | +0.0049 |
| nad 15 h | 30 | 14.9 % | 73.3 | 0.0894 | 0.0232 | -0.0108 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0340 % | -0.0000 % ± 0.0089 | +3.84 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0340 % | 0.0002 % ± 0.0089 | +3.79 | 100.0 |

Edge je odlisitelny od nahody (3.8 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 57 | 3.9 | 61.4 | 0.0194 | 28 |
| 2022-12 - 2024-03 | 59 | 4.0 | 57.6 | 0.0100 | 15 |
| 2024-03 - 2025-06 | 49 | 3.3 | 69.4 | 0.0231 | 33 |
| 2025-06 - 2026-09 | 37 | 2.5 | 73.0 | 0.0719 | 93 |

Hranice pre úsek veľkosti posledného obdobia: -0.0104 až +0.0767 % (medián 0.0316).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 93. percentile, teda v medziach -0.0104 až +0.0767 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 17** — 2024-03-13T15:07 až 2024-07-25T13:54, spolu +842.08.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-03-13T15:07 | 2024-03-13T17:10 | +58.23 | +0.27 | `take_profit` |
| 2 | 2024-03-14T14:22 | 2024-03-14T15:41 | +46.24 | +0.21 | `take_profit` |
| 3 | 2024-03-28T14:42 | 2024-03-28T16:23 | +48.22 | +0.22 | `take_profit` |
| 4 | 2024-04-05T13:48 | 2024-04-05T14:14 | +53.19 | +0.23 | `take_profit` |
| 5 | 2024-04-22T16:22 | 2024-04-22T18:29 | +60.18 | +0.26 | `take_profit` |
| 6 | 2024-05-09T13:55 | 2024-05-09T14:01 | +31.18 | +0.13 | `take_profit` |
| 7 | 2024-05-14T13:49 | 2024-05-14T13:58 | +40.17 | +0.17 | `take_profit` |
| 8 | 2024-05-14T14:00 | 2024-05-15T03:47 | +69.17 | +0.29 | `take_profit` |
| 9 | 2024-05-15T14:57 | 2024-05-15T15:01 | +42.16 | +0.18 | `take_profit` |
| 10 | 2024-05-20T13:58 | 2024-05-20T16:32 | +76.15 | +0.31 | `take_profit` |
| 11 | 2024-06-06T15:10 | 2024-06-06T15:27 | +63.16 | +0.26 | `take_profit` |
| 12 | 2024-06-07T13:43 | 2024-06-07T13:48 | +59.18 | +0.25 | `take_profit` |
| 13 | 2024-06-13T13:47 | 2024-06-13T13:54 | +47.18 | +0.20 | `take_profit` |
| 14 | 2024-07-03T13:41 | 2024-07-03T13:50 | +36.17 | +0.15 | `take_profit` |
| 15 | 2024-07-04T13:49 | 2024-07-04T13:55 | +10.17 | +0.04 | `take_profit` |
| 16 | 2024-07-11T14:10 | 2024-07-11T14:57 | +58.15 | +0.24 | `take_profit` |
| 17 | 2024-07-25T13:49 | 2024-07-25T13:54 | +43.17 | +0.18 | `take_profit` |

**Straty za sebou: 6** — 2024-02-05T15:41 až 2024-02-29T16:14, spolu -191.29.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-02-05T15:41 | 2024-02-05T16:06 | -24.71 | -0.12 | `stop_loss` |
| 2 | 2024-02-08T15:00 | 2024-02-08T18:01 | -56.72 | -0.28 | `stop_loss` |
| 3 | 2024-02-12T15:54 | 2024-02-12T17:26 | -46.71 | -0.23 | `stop_loss` |
| 4 | 2024-02-19T14:55 | 2024-02-19T15:17 | -14.71 | -0.07 | `stop_loss` |
| 5 | 2024-02-19T15:22 | 2024-02-19T15:41 | -12.71 | -0.06 | `stop_loss` |
| 6 | 2024-02-29T14:44 | 2024-02-29T16:14 | -35.72 | -0.17 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0340 %**, medián 0.0332 %, 90 % interval 0.0136–0.0536 %
- P(edge > poplatok) = **99.8 %**
- max drawdown: medián 0.8 %, 95. percentil 1.4 %, najhorší 2.6 %
- najdlhšia séria strát: medián 6, 95. percentil 8 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

> **Posudok je starší než čísla** (písal sa k vzorke `98689f09`, tu je `74eccf76`). Nech ho AI prepíše — čísla nižšie sa medzitým zmenili.

<!-- POSUDOK cisla=98689f09 -->

**1. Na čo sa to hodí.** Zlato (MGC / GC), 1m graf: jeden prieraz denne po otvorení New Yorku, stop order na hranici rozsahu 9:30–9:45 v smere gapu, stop na druhej strane OR a cieľ RR 0,75 (profil PREŠIEL SMERNICAMI č. 1). Ladené na všetkých dátach 2010–2024, odložené 2 roky 9/2024 – 9/2026.

**2. Potenciál.** Najsilnejší výsledok z rozboru NY open: zisk v **5 z 5** okien, proti náhode **+3,8 sigma**, edge nad poplatkom v 100 % bootstrapových vzoriek. Posledné obdobie je na 93. percentile a posledný rok je najlepší (+3,4 %, WR 75 %). Slabší je rok 2024/25 (break-even len 0,005 %). Obchodov je málo, 28–48 za rok v referenčných oknách, a 75/rok splnila len na celej histórii 2010–2024.

**3. Čo dorobiť.** C# `mtkorbnet` sedí s Pythonom bar po bare (6/6, aj predloha ORB 15 bez rozšírení). Na 1m grafe nie sú limity v baroch, takže 1m je tu v poriadku. Najhoršia skupina je piatok (26 % obchodov), bez nej by bol break-even o 0,014 lepší.

**4. Čo otestovať.** Forward test na C# jadre (1 MGC). Paralelne `cli sweep` s vypnutým piatkom: ak výsledok drží vo všetkých oknách, piatok vyradiť.

**5. Použiteľné?** **Áno, ako doplnok.** Edge je štatisticky najčistejší, ale obchodov je málo, preto len popri iných stratégiách na zlate.

**6. Čo by som pridal.** Druhú vrstvu: rovnaký vzor na otvorení COMEX 8:20 NY (rozbor ho ukázal tiež). Zdvojnásobila by počet obchodov bez zmeny logiky.

<!-- POSUDOK KONIEC -->
