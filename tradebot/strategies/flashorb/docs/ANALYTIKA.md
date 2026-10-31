# Základná analytika — FLASH TRIGGER ORB 1.0 (`flashorb`)

Zmerané 2026-10-31 na `MNQ/USD` 15m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `/Users/martin/IBS/.nightsearch/base_flashorb.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy flashorb \
   --profile /Users/martin/IBS/.nightsearch/base_flashorb.json \
   --pair MNQ/USD \
   --timeframe 15m \
   --fee 1.755e-05
```

## V čom je dobrá

- 798 obchodov spolu — na štatistiku dosť
- break-even 0.0428 % je nad poplatkom 0.0018 % (rezerva +0.0410 bodu)
- edge nad poplatkom v 97 % bootstrapových vzoriek
- edge drží aj v poslednom období (2025-06 - 2026-09 na 34. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- zisková v 4 z 5 referenčných okien (20221001-20231001 v strate)
- 95. percentil max drawdownu 100.0 % (namerané 43.6 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 5.4 % pri riziku, s akým beh bežal
- proti náhode len +1.9 sigma: náznak, nie dôkaz
- najhoršia skupina '16 – 23' vlastnosti 'Deň v mesiaci': 202 obchodov (25.3 %), bez nej by break-even bol o +0.0304 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 174 | +114.98 | 0.1227 | 16.5 | 31.0 | +4/-12 | `20261031-084759-af9c91` |
| 20221001-20231001 | 159 | -15.38 | -0.0163 | 49.5 | 25.2 | +3/-14 | `20261031-084802-c86f8a` |
| 20231001-20241001 | 161 | +57.81 | 0.0518 | 20.8 | 31.7 | +4/-10 | `20261031-084805-62f377` |
| 20240904-20250904 | 153 | +58.84 | 0.0467 | 29.8 | 29.4 | +3/-11 | `20261031-084811-f6a77a` |
| 20250904-20260904 | 160 | +34.41 | 0.0213 | 36.6 | 29.4 | +4/-11 | `20261031-084814-239b0a` |

Zisková v **4 z 5** okien, obchodov spolu 798, break-even celkom 0.0428 %. Okná sa prekrývajú, 9 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+1.21 ATR za 5 barov)
- medián držania 38.6 barov grafu
- winrate 29.32 %, payoff 2.866
- 0.44 obchodov za deň
- šikmosť výnosov +2.928

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 70.6 %, `take_profit` 29.1 %, `force_exit` 0.4 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je '16 – 23' vlastnosti 'Deň v mesiaci': 202 obchodov (25.3 %), break-even -0.0466 % oproti 0.0428 % celku. Bez nej by break-even bol 0.0732 % (+0.0304). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 16 – 23 | 202 | 25.3 % | 23.8 | -0.0466 | 0.0732 | +0.0304 |
| do 9 | 221 | 27.7 % | 30.3 | 0.0368 | 0.0452 | +0.0024 |
| nad 23 | 191 | 23.9 % | 29.3 | 0.0713 | 0.0340 | -0.0088 |
| 9 – 16 | 184 | 23.1 % | 34.2 | 0.1196 | 0.0200 | -0.0228 |

**Smer**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| short | 384 | 48.1 % | 25.5 | 0.0114 | 0.0725 | +0.0297 |
| long | 414 | 51.9 % | 32.9 | 0.0725 | 0.0114 | -0.0314 |

**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 15 h | 616 | 77.2 % | 29.2 | 0.0373 | 0.0628 | +0.0200 |
| nad 15 h | 182 | 22.8 % | 29.7 | 0.0628 | 0.0373 | -0.0055 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0428 % | 0.0039 % ± 0.0203 | +1.91 | 96.8 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0428 % | 0.0068 % ± 0.0203 | +1.78 | 95.6 |

Naznak, ale nie dokaz (1.9 sigma, percentil 96.8). Take rozdiely nahoda robi bezne.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 211 | 14.3 | 29.9 | 0.0960 | 86 |
| 2022-12 - 2024-03 | 192 | 13.0 | 27.1 | 0.0035 | 20 |
| 2024-03 - 2025-06 | 178 | 12.1 | 30.3 | 0.0631 | 64 |
| 2025-06 - 2026-09 | 217 | 14.7 | 29.9 | 0.0239 | 34 |

Hranice pre úsek veľkosti posledného obdobia: -0.0306 až +0.1140 % (medián 0.0417).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 34. percentile, teda v medziach -0.0306 až +0.1140 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 4** — 2022-07-27T19:00 až 2022-08-08T18:05, spolu +2281.81, rovnako dlhých sérií 5.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-07-27T19:00 | 2022-08-03T14:05 | +1155.10 | +4.59 | `take_profit` |
| 2 | 2022-08-03T15:00 | 2022-08-05T02:34 | +480.07 | +1.83 | `take_profit` |
| 3 | 2022-08-05T15:00 | 2022-08-05T15:30 | +284.08 | +1.07 | `take_profit` |
| 4 | 2022-08-08T15:00 | 2022-08-08T18:05 | +362.57 | +1.36 | `take_profit` |

**Straty za sebou: 14** — 2023-07-20T15:45 až 2023-08-09T18:19, spolu -1706.32.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-07-20T15:45 | 2023-07-20T16:33 | -147.10 | -0.47 | `stop_loss` |
| 2 | 2023-07-21T15:15 | 2023-07-21T19:09 | -137.59 | -0.44 | `stop_loss` |
| 3 | 2023-07-24T15:45 | 2023-07-24T18:01 | -118.09 | -0.38 | `stop_loss` |
| 4 | 2023-07-25T15:15 | 2023-07-26T12:09 | -72.60 | -0.23 | `stop_loss` |
| 5 | 2023-07-26T15:00 | 2023-07-26T18:38 | -164.59 | -0.53 | `stop_loss` |
| 6 | 2023-07-27T15:30 | 2023-07-27T17:17 | -118.61 | -0.37 | `stop_loss` |
| 7 | 2023-07-28T15:15 | 2023-07-28T17:42 | -91.61 | -0.29 | `stop_loss` |
| 8 | 2023-07-31T15:15 | 2023-07-31T15:32 | -91.11 | -0.29 | `stop_loss` |
| 9 | 2023-08-01T17:15 | 2023-08-01T22:00 | -122.11 | -0.39 | `stop_loss` |
| 10 | 2023-08-02T15:00 | 2023-08-04T05:51 | -135.59 | -0.44 | `stop_loss` |
| 11 | 2023-08-04T15:00 | 2023-08-04T18:05 | -110.59 | -0.36 | `stop_loss` |
| 12 | 2023-08-07T15:00 | 2023-08-07T17:49 | -100.08 | -0.33 | `stop_loss` |
| 13 | 2023-08-08T15:00 | 2023-08-08T17:16 | -127.57 | -0.42 | `stop_loss` |
| 14 | 2023-08-09T15:00 | 2023-08-09T18:19 | -169.07 | -0.56 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0428 %**, medián 0.0426 %, 90 % interval 0.0056–0.0819 %
- P(edge > poplatok) = **96.6 %**
- max drawdown: medián 43.6 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 17, 95. percentil 24 obchodov
- pravdepodobnosť ruiny účtu: 5.4 %

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
<!-- POSUDOK cisla=8a664b9d -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na MNQ, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Prieraz jednej sviečky (14:30 UTC = otvorenie NY v zime, v lete o hodinu neskôr — predloha posun nerieši); index futures, nie zlato.
2. **Má potenciál?** Zisková v 4 z 5 okien, 798 obchodov (~160 za rok), break-even 0.0428 % (nad poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 29.32 % pri payoffe 2.866. Odložený rok 25/26: +34.41 % PnL, break-even 0.0213 %. Jav je skôr skutočný ako vlastnosť vzorky.
3. **Čo dorobiť.** Čas sviečky v New Yorku namiesto pevného UTC (letný čas posúva sviečku o hodinu), koniec dňa, ktorý na 15m grafe naozaj nastane (predloha 23:59 na 15m nikdy).
4. **Čo otestovať ďalej.** Smernica (`flashorb*`: hodina a minúta sviečky, RR 0,5–3, TF, trend, typ vstupu); rozhodne, či RR 3 s WR ~29 % drží aj s plató.
5. **Použiteľné?** **Áno ako kandidát do smernice** — defaulty predlohy sú ziskové vo väčšine okien a edge je nad poplatkom; rozhodne hľadanie a odložený rok.
6. **Čo by som pridal.** Sviečku vyberať podľa NY času otvorenia (9:30 / 9:45) a cieľ menší ako 3 R — vyšší WR, menej dní bez zisku.

<!-- POSUDOK KONIEC -->
