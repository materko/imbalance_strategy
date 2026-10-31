# Základná analytika — FLASH TRIGGER ORB 1.0 (MGC) (`flashorbmgc`)

Zmerané 2026-10-31 na `MGC/USD` 15m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `/Users/martin/IBS/.nightsearch/base_flashorbmgc.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy flashorbmgc \
   --profile /Users/martin/IBS/.nightsearch/base_flashorbmgc.json \
   --pair MGC/USD \
   --timeframe 15m \
   --fee 1.755e-05
```

## V čom je dobrá

- 974 obchodov spolu — na štatistiku dosť
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- zisková v 1 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20231001-20241001, 20250904-20260904 v strate)
- break-even -0.0052 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 30 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 100.0 % (namerané 77.9 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 31.5 % pri riziku, s akým beh bežal
- nie je lepšia než náhodný vstup za tých istých pravidiel (-0.9 sigma) — výber vstupu nepridáva nič
- najhoršia skupina 'short' vlastnosti 'Smer': 457 obchodov (46.9 %), bez nej by break-even bol o +0.0207 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 195 | -11.13 | -0.0139 | 25.9 | 24.1 | +3/-14 | `20261031-084759-411fec` |
| 20221001-20231001 | 181 | -4.62 | -0.0050 | 13.2 | 25.4 | +2/-11 | `20261031-084802-3a1285` |
| 20231001-20241001 | 166 | -25.76 | -0.0327 | 32.5 | 23.5 | +2/-13 | `20261031-084808-c1b19d` |
| 20240904-20250904 | 226 | +11.52 | 0.0102 | 21.5 | 26.6 | +5/-13 | `20261031-084811-800b63` |
| 20250904-20260904 | 219 | -7.82 | -0.0023 | 74.6 | 26.0 | +2/-13 | `20261031-084814-c34e42` |

Zisková v **1 z 5** okien, obchodov spolu 974, break-even celkom -0.0052 %. Okná sa prekrývajú, 13 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+1.10 ATR za 5 barov)
- medián držania 39.8 barov grafu
- winrate 25.26 %, payoff 2.835
- 0.54 obchodov za deň
- šikmosť výnosov +1.545

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 74.6 %, `take_profit` 25.1 %, `force_exit` 0.3 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'short' vlastnosti 'Smer': 457 obchodov (46.9 %), break-even -0.0288 % oproti -0.0052 % celku. Bez nej by break-even bol 0.0155 % (+0.0207). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Smer**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| short | 457 | 46.9 % | 21.7 | -0.0288 | 0.0155 | +0.0207 |
| long | 517 | 53.1 % | 28.4 | 0.0155 | -0.0288 | -0.0236 |

**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 0.4741 % | 243 | 24.9 % | 21.4 | -0.0474 | 0.0123 | +0.0175 |
| do 0.2356 % | 244 | 25.1 % | 25.0 | 0.0033 | -0.0078 | -0.0026 |
| 0.3296 % – 0.4741 % | 243 | 24.9 % | 27.2 | 0.0141 | -0.0114 | -0.0062 |
| 0.2356 % – 0.3296 % | 244 | 25.1 % | 27.5 | 0.0194 | -0.0127 | -0.0075 |

**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 656 | 67.4 % | 24.9 | -0.0134 | 0.0119 | +0.0171 |
| proti trendu | 318 | 32.6 % | 26.1 | 0.0119 | -0.0134 | -0.0082 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0052 % | 0.0065 % ± 0.0130 | -0.90 | 17.7 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0052 % | 0.0104 % ± 0.0127 | -1.23 | 9.9 |

Neodlisitelne od nahody (-0.9 sigma, percentil 17.7). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 243 | 16.5 | 23.9 | -0.0169 | 34 |
| 2022-12 - 2024-03 | 198 | 13.4 | 25.8 | -0.0028 | 58 |
| 2024-03 - 2025-06 | 261 | 17.7 | 24.9 | -0.0063 | 51 |
| 2025-06 - 2026-09 | 272 | 18.4 | 26.5 | -0.0008 | 61 |

Hranice pre úsek veľkosti posledného obdobia: -0.0468 až +0.0384 % (medián -0.0072).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 61. percentile, teda v medziach -0.0468 až +0.0384 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 5** — 2025-08-26T15:00 až 2025-09-03T16:56, spolu +1737.82.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-08-26T15:00 | 2025-08-27T16:35 | +187.79 | +0.55 | `take_profit` |
| 2 | 2025-08-27T16:45 | 2025-08-29T14:13 | +520.78 | +1.51 | `take_profit` |
| 3 | 2025-08-29T15:30 | 2025-09-01T01:59 | +206.77 | +0.59 | `take_profit` |
| 4 | 2025-09-01T22:15 | 2025-09-02T01:47 | +242.75 | +0.68 | `take_profit` |
| 5 | 2025-09-02T15:15 | 2025-09-03T16:56 | +579.73 | +1.62 | `take_profit` |

**Straty za sebou: 14** — 2021-10-01T15:00 až 2021-10-21T17:07, spolu -718.70, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2021-10-01T15:00 | 2021-10-03T22:26 | -60.62 | -0.34 | `stop_loss` |
| 2 | 2021-10-04T16:15 | 2021-10-05T03:49 | -98.62 | -0.56 | `stop_loss` |
| 3 | 2021-10-05T15:15 | 2021-10-06T06:01 | -40.62 | -0.23 | `stop_loss` |
| 4 | 2021-10-06T15:15 | 2021-10-06T15:43 | -51.62 | -0.29 | `stop_loss` |
| 5 | 2021-10-07T15:00 | 2021-10-08T11:05 | -47.62 | -0.27 | `stop_loss` |
| 6 | 2021-10-11T16:15 | 2021-10-12T05:06 | -29.62 | -0.17 | `stop_loss` |
| 7 | 2021-10-12T15:45 | 2021-10-13T08:17 | -82.62 | -0.47 | `stop_loss` |
| 8 | 2021-10-13T15:45 | 2021-10-14T02:51 | -79.63 | -0.44 | `stop_loss` |
| 9 | 2021-10-14T15:45 | 2021-10-14T22:57 | -31.63 | -0.18 | `stop_loss` |
| 10 | 2021-10-15T15:00 | 2021-10-15T15:34 | -35.62 | -0.20 | `stop_loss` |
| 11 | 2021-10-18T15:15 | 2021-10-19T01:48 | -36.62 | -0.21 | `stop_loss` |
| 12 | 2021-10-19T16:15 | 2021-10-20T02:59 | -60.62 | -0.34 | `stop_loss` |
| 13 | 2021-10-20T16:15 | 2021-10-20T20:37 | -28.63 | -0.16 | `stop_loss` |
| 14 | 2021-10-21T16:00 | 2021-10-21T17:07 | -34.63 | -0.19 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0052 %**, medián -0.0056 %, 90 % interval -0.0265–0.0175 %
- P(edge > poplatok) = **30.1 %**
- max drawdown: medián 77.9 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 18, 95. percentil 27 obchodov
- pravdepodobnosť ruiny účtu: 31.5 %

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
<!-- POSUDOK cisla=7d78a36e -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na MGC, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Prieraz jednej sviečky (14:30 UTC = otvorenie NY v zime, v lete o hodinu neskôr — predloha posun nerieši); index futures, nie zlato. Tu na MGC (zlato) — logika robená pre index, čísla to treba brať ako test prenosu.
2. **Má potenciál?** Zisková v 1 z 5 okien, 974 obchodov (~195 za rok), break-even -0.0052 % (pod poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 25.26 % pri payoffe 2.835. Odložený rok 25/26: -7.82 % PnL, break-even -0.0023 %. Kladné okná sú skôr vlastnosť vzorky ako stabilný jav.
3. **Čo dorobiť.** Čas sviečky v New Yorku namiesto pevného UTC (letný čas posúva sviečku o hodinu), koniec dňa, ktorý na 15m grafe naozaj nastane (predloha 23:59 na 15m nikdy).
4. **Čo otestovať ďalej.** Smernica (`flashorb*`: hodina a minúta sviečky, RR 0,5–3, TF, trend, typ vstupu); rozhodne, či RR 3 s WR ~29 % drží aj s plató.
5. **Použiteľné?** **V defaultoch predlohy nie** — edge nad poplatkom nie je stabilný po rokoch; šancu má len s nastavením, ktoré nájde smernica (inak vyradiť).
6. **Čo by som pridal.** Sviečku vyberať podľa NY času otvorenia (9:30 / 9:45) a cieľ menší ako 3 R — vyšší WR, menej dní bez zisku.

<!-- POSUDOK KONIEC -->
