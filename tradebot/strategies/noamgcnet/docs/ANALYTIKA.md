# Základná analytika — NOA 1.0 MGC (C# jadro) (`noamgcnet`)

Zmerané 2026-11-11 na `MGC/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee).

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy noamgcnet \
   --pair MGC/USD \
   --timeframe 5m \
   --fee 1.755e-05
```

## V čom je dobrá

- 1091 obchodov spolu — na štatistiku dosť
- break-even 0.0139 % je nad poplatkom 0.0018 % (rezerva +0.0121 bodu)
- edge nad poplatkom v 97 % bootstrapových vzoriek
- edge drží aj v poslednom období (2025-06 - 2026-09 na 79. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 4 z 5 referenčných okien (20231001-20241001 v strate)
- 95. percentil max drawdownu 33.6 % (namerané 17.1 % medián) — na účet to treba mať
- proti náhode len +1.1 sigma: náznak, nie dôkaz
- 99.3 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 225 | +4.09 | 0.0067 | 5.5 | 40.9 | +6/-6 | `20261111-175812-e13980` |
| 20221001-20231001 | 217 | +5.82 | 0.0088 | 4.7 | 39.2 | +6/-7 | `20261111-175824-f61c07` |
| 20231001-20241001 | 222 | -0.49 | 0.0013 | 10.3 | 32.9 | +4/-15 | `20261111-175836-e69c58` |
| 20240904-20250904 | 229 | +5.20 | 0.0056 | 10.1 | 38.4 | +3/-9 | `20261111-175852-e67f2a` |
| 20250904-20260904 | 215 | +54.21 | 0.0302 | 11.0 | 40.0 | +5/-6 | `20261111-175907-f8a6b8` |

Zisková v **4 z 5** okien, obchodov spolu 1091, break-even celkom 0.0139 %. Okná sa prekrývajú, 17 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+1.09 ATR za 5 barov)
- medián držania 11 barov grafu
- winrate 38.5 %, payoff 1.916
- 0.61 obchodov za deň
- šikmosť výnosov +1.609

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `session_end` 99.3 %, `stop_loss` 0.7 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0096 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Plánovaný RR**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 99.91 R – 100.29 R | 151 | 25.0 % | 31.1 | -0.0139 | 0.0245 | +0.0096 |
| nad 100.29 R | 150 | 24.8 % | 43.3 | 0.0134 | 0.0154 | +0.0005 |
| do 99.52 R | 153 | 25.3 % | 39.9 | 0.0221 | 0.0127 | -0.0022 |
| 99.52 R – 99.91 R | 150 | 24.8 % | 41.3 | 0.0370 | 0.0069 | -0.0080 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 8 | 309 | 28.3 % | 32.4 | -0.0104 | 0.0231 | +0.0092 |
| 8 – 16 | 265 | 24.3 % | 43.0 | 0.0213 | 0.0115 | -0.0024 |
| 16 – 23 | 258 | 23.6 % | 39.9 | 0.0213 | 0.0115 | -0.0024 |
| nad 23 | 259 | 23.7 % | 39.8 | 0.0265 | 0.0097 | -0.0042 |

**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 0.2741 | 272 | 24.9 % | 38.6 | -0.0101 | 0.0216 | +0.0077 |
| do 0.1144 | 273 | 25.0 % | 37.7 | -0.0029 | 0.0194 | +0.0055 |
| 0.1924 – 0.2741 | 273 | 25.0 % | 37.0 | 0.0119 | 0.0145 | +0.0006 |
| 0.1144 – 0.1924 | 273 | 25.0 % | 40.7 | 0.0546 | -0.0002 | -0.0141 |

Parametre, ktorými sa dá s tým niečo spraviť: `hardStopPct`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0139 % | 0.0026 % ± 0.0099 | +1.15 | 88.6 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0139 % | 0.0033 % ± 0.0095 | +1.11 | 86.8 |

Naznak, ale nie dokaz (1.1 sigma, percentil 88.6). Take rozdiely nahoda robi bezne.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 278 | 18.9 | 40.3 | 0.0049 | 28 |
| 2022-12 - 2024-03 | 257 | 17.5 | 36.6 | 0.0114 | 45 |
| 2024-03 - 2025-06 | 287 | 19.5 | 38.0 | 0.0058 | 28 |
| 2025-06 - 2026-09 | 269 | 18.3 | 39.0 | 0.0243 | 79 |

Hranice pre úsek veľkosti posledného obdobia: -0.0069 až +0.0374 % (medián 0.0128).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 79. percentile, teda v medziach -0.0069 až +0.0374 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 6** — 2022-08-17T19:00 až 2022-08-23T19:25, spolu +84.28, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-08-17T19:00 | 2022-08-17T19:25 | +6.37 | +0.04 | `session_end` |
| 2 | 2022-08-18T16:00 | 2022-08-18T18:55 | +5.38 | +0.03 | `session_end` |
| 3 | 2022-08-19T14:00 | 2022-08-19T19:55 | +50.38 | +0.29 | `session_end` |
| 4 | 2022-08-23T14:00 | 2022-08-23T17:25 | +5.38 | +0.03 | `session_end` |
| 5 | 2022-08-23T18:00 | 2022-08-23T18:25 | +8.38 | +0.05 | `session_end` |
| 6 | 2022-08-23T19:00 | 2022-08-23T19:25 | +8.38 | +0.05 | `session_end` |

**Straty za sebou: 15** — 2024-04-16T14:00 až 2024-05-03T15:55, spolu -807.33.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-04-16T14:00 | 2024-04-16T14:55 | -169.84 | -0.71 | `session_end` |
| 2 | 2024-04-17T17:00 | 2024-04-17T18:25 | -36.84 | -0.15 | `session_end` |
| 3 | 2024-04-17T19:30 | 2024-04-17T19:55 | -24.84 | -0.10 | `session_end` |
| 4 | 2024-04-19T15:30 | 2024-04-19T16:25 | -21.84 | -0.09 | `session_end` |
| 5 | 2024-04-19T17:00 | 2024-04-19T17:55 | -60.85 | -0.25 | `session_end` |
| 6 | 2024-04-24T15:30 | 2024-04-24T15:55 | -88.82 | -0.38 | `session_end` |
| 7 | 2024-04-25T15:00 | 2024-04-25T15:55 | -36.82 | -0.16 | `session_end` |
| 8 | 2024-04-30T15:00 | 2024-04-30T15:25 | -59.81 | -0.26 | `session_end` |
| 9 | 2024-04-30T16:00 | 2024-04-30T16:25 | -30.81 | -0.13 | `session_end` |
| 10 | 2024-04-30T17:30 | 2024-04-30T17:55 | -32.81 | -0.14 | `session_end` |
| 11 | 2024-04-30T19:00 | 2024-04-30T19:25 | -27.81 | -0.12 | `session_end` |
| 12 | 2024-05-01T15:30 | 2024-05-01T16:25 | -31.81 | -0.14 | `session_end` |
| 13 | 2024-05-01T19:00 | 2024-05-01T19:55 | -156.82 | -0.67 | `session_end` |
| 14 | 2024-05-03T14:00 | 2024-05-03T14:55 | -6.81 | -0.03 | `session_end` |
| 15 | 2024-05-03T15:30 | 2024-05-03T15:55 | -20.81 | -0.09 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0139 %**, medián 0.0136 %, 90 % interval 0.0030–0.0250 %
- P(edge > poplatok) = **97.0 %**
- max drawdown: medián 17.1 %, 95. percentil 33.6 %, najhorší 81.3 %
- najdlhšia séria strát: medián 13, 95. percentil 18 obchodov
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
<!-- POSUDOK cisla=c5e15c42 -->

**1. Na čo sa to hodí.** Intraday momentum na MGC 5m v seanse NY 9:30–16:00, jeden kontrakt, bez pozície cez noc. Pásmo šumu a poistka sú v percentách, takže logika z MNQ sa prenáša bez prahov v bodoch; seansa je však nasdaqová — hlavný pohyb zlata je skôr počas COMEX (8:20–13:30 NY), čo NOA zatiaľ nepozná.

**2. Potenciál.** Mierny, ale stabilný: zisková v 4 z 5 okien, P(edge > poplatok) 97 %, 90 % interval break-evenu celý nad nulou (0,003–0,025 %) a posledné obdobie drží (79. percentil). Proti náhode len +1,1 sigma a polovica zisku je z posledného roku (+54 % v zlatom trende 2025–2026), takže časť edge je býčí trh zlata.

**3. Čo dorobiť.** Logika je tá istá ako NOA (C# `noamgcnet` zhodný bar po bare). Chýba nastaviteľná seansa (COMEX vs. NY) — ak smernica nenájde silné nastavenie v NY seanse, je to prvá vec, ktorú pridať. Parametre pásma a kontrol treba vlastné pre zlato.

**4. Čo otestovať.** Smernica beží na hube (11.–12. 11. 2026, `.nightsearch` noamgc) — rozhodne, či sa PF dostane na úroveň NOA MNQ (1,5+ v každom roku). Ďalej `cli matrix --strategy noamgc --timeframes 3m,5m,15m` a druhý engine.

**5. Použiteľné?** V zdrojovom nastavení **zatiaľ nie** — edge je malý (rok 2023/24 v strate, 15 strát za sebou) a závisí od trendu zlata. Kandidát na ladenie, nie na nasadenie.

**6. Čo by som pridal.** Seansu ako parameter (COMEX 8:20–13:30) a filter trendu dňa (nad / pod VWAP predchádzajúceho dňa) — skupina „trend alebo rozsah“ ukazuje, že extrémne trendové aj úplne bočné dni kazia výsledok, stredné sú najlepšie.

<!-- POSUDOK KONIEC -->
