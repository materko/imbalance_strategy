# Základná analytika — SWEEPING ENGULF 1.0 (MYM) (`sweepengulfmym`)

Zmerané 2026-11-12 na `MYM/USD` 4h, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `mym_databento_4h`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy sweepengulfmym \
   --profile mym_databento_4h \
   --pair MYM/USD \
   --timeframe 4h \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 210 obchodov spolu — na štatistiku dosť
- drawdown drží: 95. percentil 12.6 %
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- zisková v 1 z 5 referenčných okien (20221001-20231001, 20231001-20241001, 20240904-20250904, 20250904-20260904 v strate)
- break-even -0.0118 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 35 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- nie je lepšia než náhodný vstup za tých istých pravidiel (-0.3 sigma) — výber vstupu nepridáva nič
- najhoršia skupina '12 h – 16 h' vlastnosti 'Hodina vstupu (UTC)': 98 obchodov (46.7 %), bez nej by break-even bol o +0.0626 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 37 | +1.36 | 0.0675 | 2.8 | 35.1 | +4/-7 | `20261112-111825-e038d7` |
| 20221001-20231001 | 51 | -0.29 | -0.0085 | 3.0 | 33.3 | +4/-6 | `20261112-111828-777ba4` |
| 20231001-20241001 | 42 | -0.42 | -0.0138 | 1.6 | 35.7 | +3/-5 | `20261112-111831-9c035e` |
| 20240904-20250904 | 41 | -2.05 | -0.0681 | 2.4 | 24.4 | +2/-7 | `20261112-111834-5f9258` |
| 20250904-20260904 | 42 | -0.85 | -0.0230 | 1.9 | 30.9 | +5/-8 | `20261112-111837-919453` |

Zisková v **1 z 5** okien, obchodov spolu 210, break-even celkom -0.0118 %. Okná sa prekrývajú, 3 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+0.80 ATR za 5 barov)
- medián držania 5.5 barov grafu
- winrate 31.9 %, payoff 2.01
- 0.12 obchodov za deň
- šikmosť výnosov +2.068

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 67.1 %, `take_profit` 31.9 %, `force_exit` 1 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je '12 h – 16 h' vlastnosti 'Hodina vstupu (UTC)': 98 obchodov (46.7 %), break-even -0.0857 % oproti -0.0118 % celku. Bez nej by break-even bol 0.0508 % (+0.0626). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 12 h – 16 h | 98 | 46.7 % | 28.6 | -0.0857 | 0.0508 | +0.0626 |
| nad 16 h | 18 | 8.6 % | 33.3 | 0.0412 | -0.0165 | -0.0047 |
| do 12 h | 94 | 44.8 % | 35.1 | 0.0526 | -0.0665 | -0.0547 |

**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 164 | 78.1 % | 31.7 | -0.0291 | 0.0477 | +0.0595 |
| proti trendu | 46 | 21.9 % | 32.6 | 0.0477 | -0.0291 | -0.0173 |

**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.1505 – 0.2286 | 52 | 24.8 % | 23.1 | -0.1585 | 0.0368 | +0.0486 |
| nad 0.2286 | 52 | 24.8 % | 34.6 | 0.0014 | -0.0160 | -0.0042 |
| 0.0643 – 0.1505 | 53 | 25.2 % | 34.0 | 0.0218 | -0.0231 | -0.0113 |
| do 0.0643 | 53 | 25.2 % | 35.9 | 0.0837 | -0.0455 | -0.0337 |

Parametre, ktorými sa dá s tým niečo spraviť: `rrRatio`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0118 % | -0.0025 % ± 0.0351 | -0.27 | 42.6 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0118 % | -0.0018 % ± 0.0355 | -0.28 | 38.0 |

Neodlisitelne od nahody (-0.3 sigma, percentil 42.6). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 48 | 3.3 | 39.6 | 0.1191 | 93 |
| 2022-12 - 2024-03 | 55 | 3.8 | 30.9 | -0.0416 | 39 |
| 2024-03 - 2025-06 | 59 | 4.0 | 28.8 | -0.0502 | 34 |
| 2025-06 - 2026-08 | 48 | 3.3 | 29.2 | -0.0371 | 43 |

Hranice pre úsek veľkosti posledného obdobia: -0.1370 až +0.1484 % (medián -0.0205).

**DRZI** — posledné obdobie (2025-06 - 2026-08) je na 43. percentile, teda v medziach -0.1370 až +0.1484 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 5** — 2026-05-28T16:00 až 2026-07-07T08:24, spolu +1347.46.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-05-28T16:00 | 2026-06-04T13:57 | +379.60 | +1.50 | `take_profit` |
| 2 | 2026-06-09T04:00 | 2026-06-09T13:49 | +208.60 | +0.82 | `take_profit` |
| 3 | 2026-06-12T08:00 | 2026-06-12T09:31 | +137.10 | +0.54 | `take_profit` |
| 4 | 2026-06-25T08:00 | 2026-06-25T13:30 | +128.58 | +0.49 | `take_profit` |
| 5 | 2026-06-26T16:00 | 2026-07-07T08:24 | +493.57 | +1.88 | `take_profit` |

**Straty za sebou: 8** — 2026-07-10T08:00 až 2026-08-31T12:48, spolu -1172.43.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-07-10T08:00 | 2026-07-10T14:15 | -52.43 | -0.20 | `stop_loss` |
| 2 | 2026-07-13T08:00 | 2026-07-13T16:29 | -99.43 | -0.38 | `stop_loss` |
| 3 | 2026-07-16T04:00 | 2026-07-16T07:54 | -52.43 | -0.20 | `stop_loss` |
| 4 | 2026-07-17T16:00 | 2026-07-20T14:59 | -288.92 | -1.10 | `stop_loss` |
| 5 | 2026-07-21T16:00 | 2026-07-23T12:08 | -170.92 | -0.65 | `stop_loss` |
| 6 | 2026-08-04T12:00 | 2026-08-20T11:45 | -303.94 | -1.13 | `stop_loss` |
| 7 | 2026-08-24T00:00 | 2026-08-24T05:47 | -49.94 | -0.19 | `stop_loss` |
| 8 | 2026-08-27T16:00 | 2026-08-31T12:48 | -154.44 | -0.58 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0118 %**, medián -0.0139 %, 90 % interval -0.0755–0.0585 %
- P(edge > poplatok) = **35.5 %**
- max drawdown: medián 6.7 %, 95. percentil 12.6 %, najhorší 20.3 %
- najdlhšia séria strát: medián 10, 95. percentil 16 obchodov
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
<!-- POSUDOK cisla=91a32f34 -->

**1. Na čo sa to hodí.** Swingový vzor na 4h (výber likvidity + pohltenie predošlej sviečky, filter EMA 200) na MYM, ~40 obchodov za rok.

**2. Potenciál.** Malý: proti náhode −0,3 sigma, zisk len v 1 z 5 okien (2021/22) a od 2024 súvisle v strate. Pri 40 obchodoch za rok je smernicové minimum 75 obchodov na 4h nedosiahnuteľné, vyhovieť mu môže len nižší TF.

**3. Čo dorobiť.** V logike nič. Na MYM treba skúsiť nižšie TF (15m–60m), aby bol vôbec počet obchodov.

**4. Čo otestovať.** Smernica od 12. 11. 19:00 skúša TF 15/30/60/240. Ak na 15–60m nevyjde PF ≥ 1,3 v každom roku, vyradiť.

**5. Použiteľné?** **Nie** vo východiskovom nastavení. Šanca, že prejde, je malá.

**6. Čo by som pridal.** Vzor len pri výbere predchádzajúceho denného high / low (nie ľubovoľnej sviečky): na rangeovom Dow sú zmysluplné hlavne výbery významných úrovní.

<!-- POSUDOK KONIEC -->
