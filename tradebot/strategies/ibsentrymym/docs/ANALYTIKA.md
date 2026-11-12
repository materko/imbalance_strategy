# Základná analytika — IBS EZ MYM (`ibsentrymym`)

Zmerané 2026-11-12 na `MYM/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `mym_databento_3m`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy ibsentrymym \
   --profile mym_databento_3m \
   --pair MYM/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 931 obchodov spolu — na štatistiku dosť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 2 z 5 referenčných okien (20211001-20221001, 20231001-20241001, 20240904-20250904 v strate)
- break-even -0.0011 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 14 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 100.0 % (namerané 54.6 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 6.5 % pri riziku, s akým beh bežal
- nie je lepšia než náhodný vstup za tých istých pravidiel (-0.1 sigma) — výber vstupu nepridáva nič
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 304 | -48.61 | -0.0102 | 55.8 | 59.2 | +12/-6 | `20261112-111523-624cab` |
| 20221001-20231001 | 183 | +1.62 | 0.0023 | 12.9 | 66.1 | +12/-3 | `20261112-111545-9d3258` |
| 20231001-20241001 | 112 | -9.37 | -0.0037 | 19.3 | 62.5 | +9/-4 | `20261112-111615-01dbb8` |
| 20240904-20250904 | 197 | -16.07 | -0.0038 | 26.1 | 62.4 | +12/-4 | `20261112-111633-26e41f` |
| 20250904-20260904 | 151 | +26.39 | 0.0137 | 9.2 | 73.5 | +11/-5 | `20261112-111658-3a3a45` |

Zisková v **2 z 5** okien, obchodov spolu 931, break-even celkom -0.0011 %. Okná sa prekrývajú, 16 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+0.77 ATR za 5 barov)
- medián držania 3.7 barov grafu
- winrate 64.23 %, payoff 0.515
- 0.52 obchodov za deň
- šikmosť výnosov -1.019

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 64.2 %, `stop_loss` 35.7 %, `force_exit` 0.1 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0065 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**S trendom, alebo proti** (riadi `useStructureFilter`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 731 | 78.5 % | 63.9 | -0.0030 | 0.0054 | +0.0065 |
| proti trendu | 200 | 21.5 % | 65.5 | 0.0054 | -0.0030 | -0.0019 |

**Volatilita voči normálu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 1.84 – 2.328 | 233 | 25.0 % | 57.9 | -0.0093 | 0.0017 | +0.0028 |
| 2.328 – 2.909 | 233 | 25.0 % | 64.4 | -0.0027 | -0.0006 | +0.0005 |
| do 1.84 | 233 | 25.0 % | 66.5 | 0.0040 | -0.0030 | -0.0019 |
| nad 2.909 | 232 | 24.9 % | 68.1 | 0.0040 | -0.0026 | -0.0015 |

**Vzdialenosť stopu** (riadi `minSlDistance`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.1765 % – 0.219 % | 230 | 24.8 % | 61.7 | -0.0071 | 0.0012 | +0.0023 |
| do 0.1765 % | 234 | 25.2 % | 61.5 | 0.0005 | -0.0020 | -0.0009 |
| 0.219 % – 0.2848 % | 232 | 25.0 % | 67.2 | 0.0011 | -0.0018 | -0.0007 |
| nad 0.2848 % | 231 | 24.9 % | 67.5 | 0.0031 | -0.0019 | -0.0008 |

Parametre, ktorými sa dá s tým niečo spraviť: `closeAtSessionEnd`, `minSlDistance`, `rrRatio`, `sess2TradeStartH`, `state2MaxBars`, `tradeDirection`, `useStructureFilter`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0003 % | -0.0000 % ± 0.0020 | -0.13 | 45.4 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0003 % | -0.0001 % ± 0.0023 | -0.11 | 45.6 |

Neodlisitelne od nahody (-0.1 sigma, percentil 45.4). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 369 | 25.2 | 60.4 | -0.0078 | 7 |
| 2022-12 - 2024-03 | 160 | 10.9 | 66.2 | 0.0021 | 68 |
| 2024-03 - 2025-06 | 217 | 14.8 | 62.2 | -0.0044 | 32 |
| 2025-06 - 2026-08 | 185 | 12.6 | 72.4 | 0.0116 | 99 |

Hranice pre úsek veľkosti posledného obdobia: -0.0115 až +0.0084 % (medián -0.0011).

**ZLEPSUJE SA** — posledné obdobie (2025-06 - 2026-08) je nad hornou hranicou +0.0084 %. Pozor na opačnú chybu — dôvod zvyšovať riziko to nie je, rovnako dobre to môže byť priaznivý režim.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 13** — 2025-08-06T14:18 až 2025-09-10T14:34, spolu +6154.68.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-08-06T14:18 | 2025-08-06T14:23 | +476.66 | +0.09 | `take_profit` |
| 2 | 2025-08-06T16:00 | 2025-08-06T18:08 | +474.42 | +0.11 | `take_profit` |
| 3 | 2025-08-07T16:52 | 2025-08-07T17:04 | +466.80 | +0.10 | `take_profit` |
| 4 | 2025-08-07T17:07 | 2025-08-07T17:10 | +479.35 | +0.11 | `take_profit` |
| 5 | 2025-08-14T14:52 | 2025-08-14T14:56 | +473.07 | +0.09 | `take_profit` |
| 6 | 2025-08-15T15:37 | 2025-08-15T15:53 | +471.63 | +0.10 | `take_profit` |
| 7 | 2025-08-18T14:47 | 2025-08-18T14:53 | +474.87 | +0.08 | `take_profit` |
| 8 | 2025-08-18T17:51 | 2025-08-18T18:00 | +467.77 | +0.08 | `take_profit` |
| 9 | 2025-08-20T16:18 | 2025-08-20T16:24 | +466.97 | +0.08 | `take_profit` |
| 10 | 2025-08-21T15:29 | 2025-08-21T15:34 | +474.27 | +0.11 | `take_profit` |
| 11 | 2025-08-26T20:00 | 2025-08-26T20:33 | +478.84 | +0.09 | `take_profit` |
| 12 | 2025-09-02T14:24 | 2025-09-02T14:25 | +466.85 | +0.08 | `take_profit` |
| 13 | 2025-09-10T13:54 | 2025-09-10T14:34 | +483.19 | +0.13 | `take_profit` |

**Straty za sebou: 6** — 2022-04-04T14:19 až 2022-04-06T23:56, spolu -4905.50.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-04-04T14:19 | 2022-04-04T14:22 | -983.04 | -0.20 | `stop_loss` |
| 2 | 2022-04-04T14:47 | 2022-04-04T15:07 | -1008.27 | -0.19 | `stop_loss` |
| 3 | 2022-04-05T14:59 | 2022-04-05T15:54 | -977.76 | -0.22 | `stop_loss` |
| 4 | 2022-04-06T18:04 | 2022-04-06T18:09 | -961.54 | -0.37 | `stop_loss` |
| 5 | 2022-04-06T18:12 | 2022-04-06T18:12 | -12.63 | -0.00 | `stop_loss` |
| 6 | 2022-04-06T19:54 | 2022-04-06T23:56 | -962.25 | -0.33 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0011 %**, medián -0.0011 %, 90 % interval -0.0055–0.0033 %
- P(edge > poplatok) = **14.4 %**
- max drawdown: medián 54.6 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 6, 95. percentil 8 obchodov
- pravdepodobnosť ruiny účtu: 6.5 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **192** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=c0a9590e -->

**1. Na čo sa to hodí.** IBS Entry Zone na Micro Dow 3m, len RTH 9:30–16:00 NY (v noci má MYM ~54 kontraktov za 3m, nočné zóny a vstupy by niesli sklz). Prahy sú v násobkoch ATR z profilu IBS EZ ES. FVG sú na MYM v ATR rovnako veľké ako na MNQ a ES (0,27 ATR), takže mierka sedí.

**2. Potenciál.** Východisko nemá výhodu: proti náhode −0,1 sigma, zisk len v 2 z 5 okien a rok 2021/22 je hlboko v strate (−48 %, DD 56 % pri malom účte). Posledný rok (+26 %, WR 73 %, PF 1,6) je výnimka, nie trend. Rozbor trhu hovorí to isté: Dow je najmenej trendový z troch indexov a zlyhanie nie je v mierke, ale v správaní trhu.

**3. Čo dorobiť.** V logike nič, C# `ibsentrymymnet` sedí s Pythonom bar po bare. Treba vlastné prahy a výstupy pre MYM, najmä `rrRatio`, šírku stopu (`minSlDistance`, `slBufferTicks`) a časové okno.

**4. Čo otestovať.** Smernica na hube od 12. 11. 19:00 do 15. 11. 18:00 (ladenie 10/2021 – 9/2025, odložený rok 9/2025 – 9/2026). Rozhodne, či existuje nastavenie s PF ≥ 1,3 v každom roku. Kľúčový je rok 2021/22: ak ho žiadne nastavenie neudrží nad PF 0,9, stratégia na MYM nemá zmysel.

**5. Použiteľné?** Vo východiskovom nastavení **nie**. Použiteľné len ak smernica nájde nastavenie, ktoré prejde aj odloženým rokom.

**6. Čo by som pridal.** Filter režimu dňa podľa šírky ranného rozsahu (Dow je rangeový): obchodovať zóny len v dňoch, keď je rozsah 9:30–10:00 pod mediánom, teda keď sa trh vracia, a nie keď ide trendom.

<!-- POSUDOK KONIEC -->
