# Základná analytika — IBS EZ 6E (`ibsentryeur`)

Zmerané 2026-11-15 na `6E/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/ibsentryeur/configs/6e_databento_3m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy ibsentryeur \
   --profile tradebot/strategies/ibsentryeur/configs/6e_databento_3m.json \
   --pair 6E/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- break-even 0.0036 % je nad poplatkom 0.0018 % (rezerva +0.0018 bodu)
- drawdown drží: 95. percentil 15.6 %
- edge drží aj v poslednom období (2025-03 - 2026-04 na 36. percentile toho, čo stratégia vyrobí sama od seba)
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 3 z 5 referenčných okien (20211001-20221001, 20250904-20260904 v strate)
- edge nad poplatkom len v 64 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- nie je lepšia než náhodný vstup za tých istých pravidiel (-0.0 sigma) — výber vstupu nepridáva nič
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 35 | -2.17 | -0.0023 | 8.0 | 60.0 | +5/-3 | `20261115-094921-bacb88` |
| 20221001-20231001 | 31 | +1.88 | 0.0058 | 4.4 | 71.0 | +6/-3 | `20261115-094936-88a690` |
| 20231001-20241001 | 4 | +2.82 | 0.0469 | 0.0 | 100.0 | +4/-0 | `20261115-094951-b4d25b` |
| 20240904-20250904 | 23 | +2.48 | 0.0081 | 4.4 | 69.6 | +5/-2 | `20261115-095006-486b06` |
| 20250904-20260904 | 6 | -2.21 | -0.0209 | 4.3 | 50.0 | +2/-3 | `20261115-095027-1b3ae3` |

Zisková v **3 z 5** okien, obchodov spolu 99, break-even celkom 0.0036 %.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.12 ATR za 5 barov)
- medián držania 8.3 barov grafu
- winrate 66.67 %, payoff 0.532
- 0.06 obchodov za deň
- šikmosť výnosov -1.201

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 66.7 %, `stop_loss` 33.3 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0087 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**S trendom, alebo proti** (riadi `useStructureFilter`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 78 | 78.8 % | 66.7 | 0.0011 | 0.0123 | +0.0087 |
| proti trendu | 21 | 21.2 % | 66.7 | 0.0123 | 0.0011 | -0.0025 |

**Vzdialenosť stopu** (riadi `minSlDistance`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.1598 % – 0.1771 % | 24 | 24.7 % | 54.2 | -0.0141 | 0.0105 | +0.0069 |
| nad 0.2028 % | 24 | 24.7 % | 62.5 | -0.0035 | 0.0050 | +0.0014 |
| do 0.1598 % | 25 | 25.8 % | 72.0 | 0.0077 | 0.0018 | -0.0018 |
| 0.1771 % – 0.2028 % | 24 | 24.7 % | 83.3 | 0.0239 | -0.0028 | -0.0064 |

**Hodina vstupu (UTC)** (riadi `sess2TradeStartH`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 17 h | 21 | 21.2 % | 42.9 | -0.0227 | 0.0102 | +0.0066 |
| do 14 h | 39 | 39.4 % | 64.1 | -0.0030 | 0.0080 | +0.0044 |
| 14 h – 15 h | 24 | 24.2 % | 75.0 | 0.0137 | 0.0004 | -0.0032 |
| 15 h – 17 h | 15 | 15.2 % | 93.3 | 0.0386 | -0.0030 | -0.0066 |

Parametre, ktorými sa dá s tým niečo spraviť: `closeAtSessionEnd`, `minSlDistance`, `sess2TradeStartH`, `state2MaxBars`, `tradeDirection`, `useStructureFilter`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0000 % | 0.0000 % ± 0.0052 | -0.00 | 48.6 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0000 % | -0.0001 % ± 0.0051 | +0.02 | 50.9 |

Neodlisitelne od nahody (-0.0 sigma, percentil 48.6). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-11 | 46 | 3.4 | 60.9 | -0.0029 | 22 |
| 2022-11 - 2024-01 | 23 | 1.7 | 78.3 | 0.0159 | 84 |
| 2024-01 - 2025-03 | 6 | 0.4 | 83.3 | 0.0200 | 63 |
| 2025-03 - 2026-04 | 24 | 1.8 | 62.5 | -0.0007 | 36 |

Hranice pre úsek veľkosti posledného obdobia: -0.0184 až +0.0233 % (medián 0.0036).

**DRZI** — posledné obdobie (2025-03 - 2026-04) je na 36. percentile, teda v medziach -0.0184 až +0.0233 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 8** — 2023-10-03T14:11 až 2025-01-16T17:27, spolu +3457.30.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-10-03T14:11 | 2023-10-03T15:35 | +469.08 | +0.09 | `take_profit` |
| 2 | 2023-11-01T18:54 | 2023-11-01T19:01 | +379.85 | +0.10 | `take_profit` |
| 3 | 2024-01-11T14:49 | 2024-01-11T15:06 | +435.56 | +0.11 | `take_profit` |
| 4 | 2024-08-01T14:42 | 2024-08-01T14:48 | +406.02 | +0.07 | `take_profit` |
| 5 | 2024-10-14T14:18 | 2024-10-14T17:15 | +443.31 | +0.08 | `take_profit` |
| 6 | 2024-12-05T15:57 | 2024-12-05T19:36 | +389.20 | +0.10 | `take_profit` |
| 7 | 2025-01-10T15:33 | 2025-01-10T15:43 | +477.43 | +0.07 | `take_profit` |
| 8 | 2025-01-16T16:38 | 2025-01-16T17:27 | +456.86 | +0.09 | `take_profit` |

**Straty za sebou: 3** — 2022-03-31T14:12 až 2022-05-16T16:09, spolu -2595.87, rovnako dlhých sérií 5.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-03-31T14:12 | 2022-03-31T14:54 | -858.38 | -0.21 | `stop_loss` |
| 2 | 2022-04-07T14:40 | 2022-04-07T15:31 | -844.19 | -0.15 | `stop_loss` |
| 3 | 2022-05-16T14:56 | 2022-05-16T16:09 | -893.30 | -0.17 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0036 %**, medián 0.0036 %, 90 % interval -0.0050–0.0122 %
- P(edge > poplatok) = **64.0 %**
- max drawdown: medián 8.1 %, 95. percentil 15.6 %, najhorší 27.9 %
- najdlhšia séria strát: medián 3, 95. percentil 5 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **1 489** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=8defca3f -->

**1. Na čo sa to hodí.** IBS Entry Zone na 6E 3m s prahmi v ATR (profil z IBS EZ MYM). Čísla sú z **neladeného východiska** (predloha z MNQ, tickové prahy ×0,12); ladenie pôjde len na 2016–2021/9, tieto okná sú preň čisté overenie a nesmú ho ovplyvniť.

**2. Potenciál.** **Malý zatiaľ.** Len ~20 obchodov za rok, −0,0 sigma — profil z MYM (len RTH, prísne filtre) je na EUR priveľmi úzky.

**3. Čo dorobiť.** Uvoľniť filtre a pustiť aj londýnsku seansu (`sess1On`), aby bolo ≥ 75 obchodov za rok.

**4. Čo otestovať.** Smernica EUR (22.–29. 11. 2026) so skupinami IBS EZ ES (ATR); rozhodne počet obchodov a PF ≥ 1,3.

**5. Použiteľné?** **Zatiaľ o ničom** — málo obchodov na posúdenie.

**6. Čo by som pridal.** Zóny z 15m v Londýne, kde EUR robí imbalance najčastejšie.

<!-- POSUDOK KONIEC -->
