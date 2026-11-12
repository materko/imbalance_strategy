# Základná analytika — SIGMA BREAKOUT 1.0 (MYM) (`sigmamym`)

Zmerané 2026-11-12 na `MYM/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `mym_databento_5m`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy sigmamym \
   --profile mym_databento_5m \
   --pair MYM/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 1851 obchodov spolu — na štatistiku dosť
- drawdown drží: 95. percentil 24.4 %

## Kde má chyby

- zisková v 1 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20231001-20241001, 20250904-20260904 v strate)
- break-even -0.0042 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 22 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- nie je lepšia než náhodný vstup za tých istých pravidiel (-0.7 sigma) — výber vstupu nepridáva nič
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- 100 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 's trendom' vlastnosti 'S trendom, alebo proti': 1491 obchodov (80.6 %), bez nej by break-even bol o +0.0157 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 450 | -6.22 | -0.0231 | 9.3 | 43.3 | +6/-7 | `20261112-111952-24ddbd` |
| 20221001-20231001 | 377 | -1.10 | -0.0035 | 5.3 | 47.0 | +7/-7 | `20261112-111958-2c912f` |
| 20231001-20241001 | 360 | -1.39 | -0.0043 | 3.1 | 48.9 | +8/-7 | `20261112-112004-2c4b7f` |
| 20240904-20250904 | 329 | +5.63 | 0.0256 | 3.2 | 48.6 | +9/-7 | `20261112-112007-cd59a1` |
| 20250904-20260904 | 359 | -5.27 | -0.0162 | 5.7 | 49.6 | +9/-7 | `20261112-112010-0f6c5a` |

Zisková v **1 z 5** okien, obchodov spolu 1851, break-even celkom -0.0042 %. Okná sa prekrývajú, 24 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.47 ATR za 5 barov)
- medián držania 58 barov grafu
- winrate 47.38 %, payoff 1.047
- 1.03 obchodov za deň
- šikmosť výnosov +2.224

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `session_end` 100 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 's trendom' vlastnosti 'S trendom, alebo proti': 1491 obchodov (80.6 %), break-even -0.0079 % oproti -0.0042 % celku. Bez nej by break-even bol 0.0115 % (+0.0157). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 1491 | 80.6 % | 47.7 | -0.0079 | 0.0115 | +0.0157 |
| proti trendu | 360 | 19.4 % | 46.1 | 0.0115 | -0.0079 | -0.0037 |

**Plánovaný RR**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 99.94 R – 100 R | 337 | 36.4 % | 46.0 | -0.0134 | 0.0131 | +0.0097 |
| nad 100.04 R | 221 | 23.8 % | 42.1 | -0.0112 | 0.0079 | +0.0045 |
| do 99.94 R | 251 | 27.1 % | 55.0 | 0.0131 | -0.0001 | -0.0035 |
| 100 R – 100.04 R | 118 | 12.7 % | 54.2 | 0.0571 | -0.0047 | -0.0081 |

**Smer**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| short | 924 | 49.9 % | 46.2 | -0.0117 | 0.0034 | +0.0076 |
| long | 927 | 50.1 % | 48.5 | 0.0034 | -0.0117 | -0.0075 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0042 % | -0.0002 % ± 0.0055 | -0.73 | 23.3 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0042 % | 0.0001 % ± 0.0062 | -0.70 | 24.5 |

Neodlisitelne od nahody (-0.7 sigma, percentil 23.3). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 535 | 36.3 | 43.5 | -0.0205 | 11 |
| 2022-12 - 2024-03 | 464 | 31.5 | 48.9 | -0.0030 | 54 |
| 2024-03 - 2025-06 | 418 | 28.3 | 48.1 | 0.0226 | 96 |
| 2025-06 - 2026-09 | 434 | 29.4 | 49.8 | -0.0133 | 29 |

Hranice pre úsek veľkosti posledného obdobia: -0.0282 až +0.0243 % (medián -0.0050).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 29. percentile, teda v medziach -0.0282 až +0.0243 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 9** — 2025-03-11T13:55 až 2025-03-21T20:00, spolu +590.39, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-03-11T13:55 | 2025-03-11T20:00 | +88.27 | +0.42 | `session_end` |
| 2 | 2025-03-12T13:45 | 2025-03-12T20:00 | +51.27 | +0.25 | `session_end` |
| 3 | 2025-03-13T15:20 | 2025-03-13T20:00 | +99.78 | +0.49 | `session_end` |
| 4 | 2025-03-14T13:50 | 2025-03-14T20:00 | +110.27 | +0.53 | `session_end` |
| 5 | 2025-03-17T13:35 | 2025-03-17T20:00 | +115.26 | +0.55 | `session_end` |
| 6 | 2025-03-18T13:40 | 2025-03-18T20:00 | +26.26 | +0.12 | `session_end` |
| 7 | 2025-03-19T15:55 | 2025-03-19T20:00 | +32.76 | +0.15 | `session_end` |
| 8 | 2025-03-20T14:00 | 2025-03-20T20:00 | +9.76 | +0.05 | `session_end` |
| 9 | 2025-03-21T16:25 | 2025-03-21T20:00 | +56.76 | +0.27 | `session_end` |

**Straty za sebou: 7** — 2022-05-11T13:35 až 2022-05-12T20:00, spolu -927.90, rovnako dlhých sérií 8.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-05-11T13:35 | 2022-05-11T13:40 | -108.06 | -0.68 | `session_end` |
| 2 | 2022-05-11T13:50 | 2022-05-11T17:55 | -259.56 | -1.61 | `session_end` |
| 3 | 2022-05-11T18:05 | 2022-05-11T20:00 | -40.06 | -0.25 | `session_end` |
| 4 | 2022-05-11T20:10 | 2022-05-11T20:10 | -7.56 | -0.05 | `session_end` |
| 5 | 2022-05-12T13:35 | 2022-05-12T14:10 | -122.55 | -0.78 | `session_end` |
| 6 | 2022-05-12T14:20 | 2022-05-12T17:45 | -200.05 | -1.26 | `session_end` |
| 7 | 2022-05-12T17:55 | 2022-05-12T20:00 | -190.05 | -1.22 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0042 %**, medián -0.0043 %, 90 % interval -0.0163–0.0090 %
- P(edge > poplatok) = **22.0 %**
- max drawdown: medián 13.2 %, 95. percentil 24.4 %, najhorší 41.2 %
- najdlhšia séria strát: medián 9, 95. percentil 12 obchodov
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
<!-- POSUDOK cisla=b8fd8c20 -->

**1. Na čo sa to hodí.** Prieraz pásma sigma od otvorenia na MYM 5m, ~360 obchodov za rok, výstup najneskôr na konci seansy.

**2. Potenciál.** Žiadny vo východisku: proti náhode −0,7 sigma, zisk v 1 z 5 okien (2024/25) a posledný rok −5 %. Prierazy na Dow podľa rozboru nepokračujú (MacBook: ORB, VWAP ORB, Volt Break, JSS a FLASH ORB sa na Dow nehodia), Sigma je rovnaký typ.

**3. Čo dorobiť.** V logike nič, C# `sigmamymnet` sedí bar po bare.

**4. Čo otestovať.** Smernica od 12. 11. 19:00 (`bandMult`, `nSigmaDays`, VWAP, stop). Ak ani širšie pásmo (`bandMult` ≥ 1,5, menej a silnejších prierazov) nedá PF ≥ 1,3 v každom roku, vyradiť.

**5. Použiteľné?** **Nie**, šanca na prechod je malá.

**6. Čo by som pridal.** Obrátiť logiku: prieraz pásma na Dow fádovať (návrat do pásma). Rozbor ukazuje, že Dow sa skôr vracia, ako pokračuje.

<!-- POSUDOK KONIEC -->
