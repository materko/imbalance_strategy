# Základná analytika — ORB 15/5 1.0 (`orb15`)

Zmerané 2026-10-31 na `MNQ/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `/Users/martin/IBS/.nightsearch/base_orb15.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy orb15 \
   --profile /Users/martin/IBS/.nightsearch/base_orb15.json \
   --pair MNQ/USD \
   --timeframe 5m \
   --fee 1.755e-05
```

## V čom je dobrá

- 1167 obchodov spolu — na štatistiku dosť
- break-even 0.0146 % je nad poplatkom 0.0018 % (rezerva +0.0128 bodu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 6. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- zisková v 4 z 5 referenčných okien (20250904-20260904 v strate)
- edge nad poplatkom len v 90 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 89.1 % (namerané 38.2 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 2.9 % pri riziku, s akým beh bežal
- proti náhode len +1.8 sigma: náznak, nie dôkaz
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- 40.4 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina '1.99 R – 2 R' vlastnosti 'Plánovaný RR': 396 obchodov (33.9 %), bez nej by break-even bol o +0.0179 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 252 | +37.95 | 0.0288 | 14.9 | 47.2 | +7/-5 | `20261031-084724-5844df` |
| 20221001-20231001 | 232 | +27.78 | 0.0243 | 13.1 | 44.0 | +7/-6 | `20261031-084727-e2a2b3` |
| 20231001-20241001 | 233 | +33.88 | 0.0220 | 10.7 | 45.5 | +8/-7 | `20261031-084733-8008e8` |
| 20240904-20250904 | 231 | +43.76 | 0.0241 | 20.1 | 42.9 | +4/-6 | `20261031-084736-9b0cef` |
| 20250904-20260904 | 237 | -38.18 | -0.0133 | 60.0 | 44.3 | +7/-6 | `20261031-084742-c7a5fa` |

Zisková v **4 z 5** okien, obchodov spolu 1167, break-even celkom 0.0146 %. Okná sa prekrývajú, 18 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.41 ATR za 5 barov)
- medián držania 47 barov grafu
- winrate 44.99 %, payoff 1.338
- 0.65 obchodov za deň
- šikmosť výnosov +0.87

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 43.1 %, `session_end` 40.4 %, `take_profit` 16.5 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je '1.99 R – 2 R' vlastnosti 'Plánovaný RR': 396 obchodov (33.9 %), break-even -0.0184 % oproti 0.0146 % celku. Bez nej by break-even bol 0.0325 % (+0.0179). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Plánovaný RR**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 1.99 R – 2 R | 396 | 33.9 % | 42.9 | -0.0184 | 0.0325 | +0.0179 |
| nad 2.01 R | 151 | 12.9 % | 45.0 | 0.0091 | 0.0154 | +0.0008 |
| 2 R – 2.01 R | 259 | 22.2 % | 44.4 | 0.0192 | 0.0133 | -0.0013 |
| do 1.99 R | 361 | 30.9 % | 47.6 | 0.0521 | -0.0014 | -0.0160 |

**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.086 – 0.161 | 292 | 25.0 % | 38.7 | -0.0334 | 0.0305 | +0.0159 |
| do 0.086 | 292 | 25.0 % | 42.8 | -0.0020 | 0.0202 | +0.0056 |
| 0.161 – 0.2717 | 292 | 25.0 % | 47.6 | 0.0239 | 0.0115 | -0.0031 |
| nad 0.2717 | 291 | 24.9 % | 50.9 | 0.0698 | -0.0037 | -0.0183 |

**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.5562 % – 0.7757 % | 291 | 24.9 % | 41.9 | -0.0248 | 0.0276 | +0.0130 |
| do 0.3949 % | 292 | 25.0 % | 41.8 | 0.0181 | 0.0134 | -0.0012 |
| nad 0.7757 % | 291 | 24.9 % | 48.5 | 0.0325 | 0.0096 | -0.0050 |
| 0.3949 % – 0.5562 % | 293 | 25.1 % | 47.8 | 0.0332 | 0.0080 | -0.0066 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0146 % | 0.0009 % ± 0.0076 | +1.81 | 96.1 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0146 % | 0.0020 % ± 0.0082 | +1.53 | 93.8 |

Naznak, ale nie dokaz (1.8 sigma, percentil 96.1). Take rozdiely nahoda robi bezne.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 302 | 20.5 | 47.7 | 0.0396 | 89 |
| 2022-12 - 2024-03 | 292 | 19.8 | 43.8 | 0.0145 | 50 |
| 2024-03 - 2025-06 | 282 | 19.1 | 45.7 | 0.0361 | 85 |
| 2025-06 - 2026-09 | 291 | 19.7 | 42.6 | -0.0146 | 6 |

Hranice pre úsek veľkosti posledného obdobia: -0.0162 až +0.0498 % (medián 0.0148).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 6. percentile, teda v medziach -0.0162 až +0.0498 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 8** — 2023-12-04T15:15 až 2023-12-13T19:55, spolu +1341.42.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-12-04T15:15 | 2023-12-04T15:32 | +178.39 | +0.56 | `take_profit` |
| 2 | 2023-12-05T14:55 | 2023-12-05T21:00 | +131.88 | +0.42 | `session_end` |
| 3 | 2023-12-06T15:05 | 2023-12-06T21:00 | +203.89 | +0.64 | `session_end` |
| 4 | 2023-12-07T15:25 | 2023-12-07T21:00 | +64.38 | +0.20 | `session_end` |
| 5 | 2023-12-08T15:05 | 2023-12-08T21:00 | +93.87 | +0.29 | `session_end` |
| 6 | 2023-12-11T14:55 | 2023-12-11T21:00 | +170.85 | +0.52 | `session_end` |
| 7 | 2023-12-12T15:00 | 2023-12-12T21:00 | +252.84 | +0.77 | `session_end` |
| 8 | 2023-12-13T19:05 | 2023-12-13T19:55 | +245.33 | +0.74 | `take_profit` |

**Straty za sebou: 7** — 2023-11-21T15:25 až 2023-12-01T15:26, spolu -624.36.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-11-21T15:25 | 2023-11-21T21:00 | -72.62 | -0.23 | `session_end` |
| 2 | 2023-11-23T15:05 | 2023-11-23T15:50 | -32.13 | -0.10 | `stop_loss` |
| 3 | 2023-11-24T15:25 | 2023-11-27T16:53 | -106.13 | -0.33 | `stop_loss` |
| 4 | 2023-11-27T16:55 | 2023-11-27T21:00 | -96.13 | -0.30 | `session_end` |
| 5 | 2023-11-28T14:55 | 2023-11-28T15:39 | -95.12 | -0.30 | `stop_loss` |
| 6 | 2023-11-30T15:05 | 2023-11-30T21:00 | -97.12 | -0.30 | `session_end` |
| 7 | 2023-12-01T15:05 | 2023-12-01T15:26 | -125.12 | -0.39 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0146 %**, medián 0.0147 %, 90 % interval -0.0020–0.0314 %
- P(edge > poplatok) = **90.2 %**
- max drawdown: medián 38.2 %, 95. percentil 89.1 %, najhorší 100.0 %
- najdlhšia séria strát: medián 8, 95. percentil 11 obchodov
- pravdepodobnosť ruiny účtu: 2.9 %

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
<!-- POSUDOK cisla=e3619529 -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na MNQ, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Intraday index futures od 9:45 NY, jeden obchod denne; na zlate OR 9:30–9:45 nemá zmysel otvorenia akciovej burzy, čísla tam ukazujú skôr šum.
2. **Má potenciál?** Zisková v 4 z 5 okien, 1167 obchodov (~233 za rok), break-even 0.0146 % (nad poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 44.99 % pri payoffe 1.338. Odložený rok 25/26: -38.18 % PnL, break-even -0.0133 %. Kladné okná sú skôr vlastnosť vzorky ako stabilný jav.
3. **Čo dorobiť.** Skúsiť OR 5 / 30 / 60 min a cieľ RR 0,75–1,5; filter predošlého dňa a knôtu majú byť v mriežke oboma smermi; pre prop koniec dňa.
4. **Čo otestovať ďalej.** Smernica (mriežka glsearch `orb15*`: dĺžka OR, RR, filtre, trend EMA, limit / IBS / pin bar); rozhodne odložený rok 25/26, ktorý je pri MNQ v defaultoch stratový.
5. **Použiteľné?** **V defaultoch predlohy nie** — edge nad poplatkom nie je stabilný po rokoch; šancu má len s nastavením, ktoré nájde smernica (inak vyradiť).
6. **Čo by som pridal.** Smer dňa z VWAP od 9:30 alebo z polohy voči včerajšiemu zavretiu — ORB bez kontextu chytá aj falošné prierazy rána.

<!-- POSUDOK KONIEC -->
