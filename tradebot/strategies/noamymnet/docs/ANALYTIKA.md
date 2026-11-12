# Základná analytika — NOA 1.0 MYM (C# jadro) (`noamymnet`)

Zmerané 2026-11-12 na `MYM/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `mym_databento_5m`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy noamymnet \
   --profile mym_databento_5m \
   --pair MYM/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 1307 obchodov spolu — na štatistiku dosť
- drawdown drží: 95. percentil 10.4 %
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 1 z 5 referenčných okien (20211001-20221001, 20231001-20241001, 20240904-20250904, 20250904-20260904 v strate)
- break-even -0.0020 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 18 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- nie je lepšia než náhodný vstup za tých istých pravidiel (-0.8 sigma) — výber vstupu nepridáva nič
- 71.5 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 307 | -1.74 | -0.0083 | 3.8 | 29.3 | +3/-16 | `20261112-112549-ba6d00` |
| 20221001-20231001 | 250 | +0.98 | 0.0088 | 0.8 | 36.4 | +5/-8 | `20261112-112559-b5e38e` |
| 20231001-20241001 | 257 | -0.65 | -0.0022 | 1.5 | 33.1 | +3/-11 | `20261112-112614-86b62d` |
| 20240904-20250904 | 273 | -1.20 | -0.0044 | 2.0 | 32.2 | +3/-11 | `20261112-112623-ffa908` |
| 20250904-20260904 | 245 | -1.60 | -0.0062 | 1.9 | 32.2 | +8/-12 | `20261112-112632-5eb60c` |

Zisková v **1 z 5** okien, obchodov spolu 1307, break-even celkom -0.0020 %. Okná sa prekrývajú, 25 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+1.25 ATR za 5 barov)
- medián držania 11 barov grafu
- winrate 32.67 %, payoff 1.929
- 0.73 obchodov za deň
- šikmosť výnosov +2.516

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `session_end` 71.5 %, `stop_loss` 28.5 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0036 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.1429 | 327 | 25.0 % | 29.7 | -0.0129 | 0.0016 | +0.0036 |
| 0.1429 – 0.2182 | 327 | 25.0 % | 33.3 | -0.0118 | 0.0012 | +0.0032 |
| 0.2182 – 0.307 | 327 | 25.0 % | 33.9 | 0.0068 | -0.0050 | -0.0030 |
| nad 0.307 | 326 | 24.9 % | 33.7 | 0.0097 | -0.0059 | -0.0039 |

**Smer** (riadi `tradeDirection`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| short | 654 | 50.0 % | 31.2 | -0.0054 | 0.0012 | +0.0032 |
| long | 653 | 50.0 % | 34.1 | 0.0012 | -0.0054 | -0.0034 |

**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 14 h | 343 | 26.2 % | 27.7 | -0.0114 | 0.0012 | +0.0032 |
| 16 h – 17 h | 151 | 11.6 % | 28.5 | -0.0048 | -0.0017 | +0.0003 |
| 14 h – 16 h | 489 | 37.4 % | 30.3 | -0.0014 | -0.0024 | -0.0004 |
| nad 17 h | 324 | 24.8 % | 43.5 | 0.0080 | -0.0054 | -0.0034 |

Parametre, ktorými sa dá s tým niečo spraviť: `hardStopPct`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0020 % | 0.0012 % ± 0.0042 | -0.76 | 22.8 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0020 % | 0.0017 % ± 0.0046 | -0.81 | 21.6 |

Neodlisitelne od nahody (-0.8 sigma, percentil 22.8). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 371 | 25.1 | 29.9 | -0.0049 | 38 |
| 2022-12 - 2024-03 | 312 | 21.1 | 36.5 | 0.0042 | 75 |
| 2024-03 - 2025-06 | 319 | 21.6 | 32.3 | -0.0025 | 49 |
| 2025-06 - 2026-09 | 305 | 20.7 | 32.5 | -0.0038 | 42 |

Hranice pre úsek veľkosti posledného obdobia: -0.0163 až +0.0122 % (medián -0.0022).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 42. percentile, teda v medziach -0.0163 až +0.0122 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 8** — 2026-04-14T14:30 až 2026-05-06T15:25, spolu +406.59.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-04-14T14:30 | 2026-04-14T16:55 | +28.65 | +0.12 | `session_end` |
| 2 | 2026-04-15T15:00 | 2026-04-15T16:55 | +2.65 | +0.01 | `session_end` |
| 3 | 2026-04-17T14:00 | 2026-04-17T19:25 | +44.63 | +0.18 | `session_end` |
| 4 | 2026-04-24T14:00 | 2026-04-24T14:55 | +2.13 | +0.01 | `session_end` |
| 5 | 2026-04-29T14:00 | 2026-04-29T19:55 | +20.14 | +0.08 | `session_end` |
| 6 | 2026-04-30T14:00 | 2026-04-30T19:55 | +204.63 | +0.83 | `session_end` |
| 7 | 2026-05-04T15:30 | 2026-05-04T19:55 | +81.64 | +0.33 | `session_end` |
| 8 | 2026-05-06T14:00 | 2026-05-06T15:25 | +22.12 | +0.09 | `session_end` |

**Straty za sebou: 16** — 2022-01-24T15:00 až 2022-01-28T19:11, spolu -764.55.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-01-24T15:00 | 2022-01-24T15:36 | -46.59 | -0.28 | `stop_loss` |
| 2 | 2022-01-24T16:00 | 2022-01-24T18:55 | -40.09 | -0.24 | `session_end` |
| 3 | 2022-01-24T19:30 | 2022-01-24T19:59 | -48.59 | -0.29 | `stop_loss` |
| 4 | 2022-01-24T20:00 | 2022-01-24T20:02 | -47.59 | -0.28 | `stop_loss` |
| 5 | 2022-01-25T15:00 | 2022-01-25T15:16 | -47.09 | -0.28 | `stop_loss` |
| 6 | 2022-01-25T17:00 | 2022-01-25T17:05 | -48.59 | -0.29 | `stop_loss` |
| 7 | 2022-01-25T20:00 | 2022-01-25T20:06 | -48.60 | -0.28 | `stop_loss` |
| 8 | 2022-01-26T15:00 | 2022-01-26T15:13 | -49.11 | -0.28 | `stop_loss` |
| 9 | 2022-01-26T20:30 | 2022-01-26T20:54 | -49.60 | -0.29 | `stop_loss` |
| 10 | 2022-01-27T15:00 | 2022-01-27T15:00 | -50.11 | -0.29 | `stop_loss` |
| 11 | 2022-01-27T16:00 | 2022-01-27T16:16 | -48.11 | -0.28 | `stop_loss` |
| 12 | 2022-01-27T16:30 | 2022-01-27T17:16 | -48.10 | -0.28 | `stop_loss` |
| 13 | 2022-01-28T15:00 | 2022-01-28T15:09 | -48.59 | -0.29 | `stop_loss` |
| 14 | 2022-01-28T15:30 | 2022-01-28T15:54 | -46.60 | -0.27 | `stop_loss` |
| 15 | 2022-01-28T17:00 | 2022-01-28T17:25 | -50.10 | -0.29 | `stop_loss` |
| 16 | 2022-01-28T19:00 | 2022-01-28T19:11 | -47.10 | -0.28 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0020 %**, medián -0.0021 %, 90 % interval -0.0089–0.0049 %
- P(edge > poplatok) = **18.1 %**
- max drawdown: medián 5.7 %, 95. percentil 10.4 %, najhorší 17.7 %
- najdlhšia séria strát: medián 15, 95. percentil 21 obchodov
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
<!-- POSUDOK cisla=010d05e9 -->

**1. Na čo sa to hodí.** _(C# jadro `noamymnet`: čísla sú v každom okne zhodné s Python `noamym`.)_ Intraday momentum (NOA) na MYM 5m, seansa NY, bez pozície cez noc. Pásmo šumu si NOA ráta sama v percentách; poistka `hardStopPct` je zmenšená na 0,28 % podľa rozboru (pásmo MYM ≈ 0,65 × MNQ).

**2. Potenciál.** Slabý: proti náhode −0,8 sigma, zisk v 1 z 5 okien, WR 29–36 % a posledný rok stratový. Sedí to s rozborom trendovosti. Na Dow smer 9:30–10:00 pokračuje do 16:00 len v 50,6 % dní (MNQ 53,7 %), \|close−open\| / rozpätie dňa je 0,42, najmenej z troch indexov. NOA žije z trendových dní a tých má Dow najmenej.

**3. Čo dorobiť.** V logike nič, C# `noamymnet` sedí bar po bare. Treba ladiť šírku pásma (`volMult`, `lookbackDays`), hustotu kontrol a filter trendu.

**4. Čo otestovať.** Smernica od 12. 11. 19:00 (skúša aj `hardStopPct` 0,2–0,6 a TF 3/5/15m). Ak ani najlepšie nastavenie nemá PF ≥ 1,3 v každom roku, NOA na MYM zahodiť, nie ďalej ladiť.

**5. Použiteľné?** V zdrojovom nastavení **nie**. Čakám skôr, že smernicou neprejde (trh na to nie je).

**6. Čo by som pridal.** Vstup len pri zhode smeru s MNQ v tú istú minútu: Dow ako nasledovník trendu Nasdaqu, nie ako samostatný signál.

<!-- POSUDOK KONIEC -->
