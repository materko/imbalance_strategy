# Základná analytika — IBS EZ ES (`ibsentryes`)

Zmerané 2026-10-23 na `ES/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/ibsentryes_PRESIEL_SMERNICAMI_IBS_EZ_ES_1_2026-10-23.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy ibsentryes \
   --profile .nightsearch/checkup/ibsentryes_PRESIEL_SMERNICAMI_IBS_EZ_ES_1_2026-10-23.json \
   --pair ES/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 824 obchodov spolu — na štatistiku dosť
- break-even 0.0088 % je nad poplatkom 0.0018 % (rezerva +0.0070 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 18.9 %
- odlíšiteľná od náhody (+7.5 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-08 na 51. percentile toho, čo stratégia vyrobí sama od seba)
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 245 | +32.85 | 0.0101 | 7.3 | 73.9 | +13/-6 | `20261023-040600-e4f4c4` |
| 20221001-20231001 | 161 | +14.44 | 0.0065 | 10.6 | 73.3 | +9/-3 | `20261023-040612-558d6a` |
| 20231001-20241001 | 124 | +16.17 | 0.0088 | 5.2 | 75.0 | +19/-3 | `20261023-040625-caeff2` |
| 20240904-20250904 | 168 | +21.75 | 0.0091 | 12.2 | 72.6 | +10/-3 | `20261023-040637-812366` |
| 20250904-20260904 | 126 | +16.47 | 0.0093 | 6.5 | 74.6 | +13/-5 | `20261023-040649-0de82f` |

Zisková v **5 z 5** okien, obchodov spolu 824, break-even celkom 0.0088 %.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+0.68 ATR za 5 barov)
- medián držania 1.7 barov grafu
- winrate 73.79 %, payoff 0.475
- 0.46 obchodov za deň
- šikmosť výnosov -0.969

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 74.3 %, `stop_loss` 25.7 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0066 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Plánovaný RR** (riadi `rrRatio`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.5 R | 752 | 91.3 % | 73.7 | 0.0080 | 0.0154 | +0.0066 |
| nad 0.5 R | 72 | 8.7 % | 75.0 | 0.0154 | 0.0080 | -0.0008 |

**S trendom, alebo proti** (riadi `useStructureFilter`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 550 | 66.7 % | 72.4 | 0.0074 | 0.0117 | +0.0029 |
| proti trendu | 274 | 33.3 % | 76.6 | 0.0117 | 0.0074 | -0.0014 |

**Deň v týždni**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| streda | 190 | 23.1 % | 70.5 | 0.0028 | 0.0106 | +0.0018 |
| pondelok | 108 | 13.1 % | 69.4 | 0.0041 | 0.0095 | +0.0007 |
| piatok | 175 | 21.2 % | 76.6 | 0.0112 | 0.0082 | -0.0006 |
| utorok | 162 | 19.7 % | 76.5 | 0.0117 | 0.0081 | -0.0007 |
| štvrtok | 184 | 22.3 % | 75.0 | 0.0136 | 0.0075 | -0.0013 |

Parametre, ktorými sa dá s tým niečo spraviť: `closeAtSessionEnd`, `minSlDistance`, `rrRatio`, `sess2TradeStartH`, `state2MaxBars`, `tradeDirection`, `useStructureFilter`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0109 % | -0.0001 % ± 0.0015 | +7.49 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0109 % | -0.0001 % ± 0.0017 | +6.50 | 100.0 |

Edge je odlisitelny od nahody (7.5 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 308 | 21.0 | 73.0 | 0.0087 | 48 |
| 2022-12 - 2024-03 | 148 | 10.1 | 73.7 | 0.0066 | 32 |
| 2024-03 - 2025-06 | 221 | 15.1 | 74.7 | 0.0103 | 68 |
| 2025-06 - 2026-08 | 147 | 10.0 | 74.2 | 0.0092 | 51 |

Hranice pre úsek veľkosti posledného obdobia: +0.0013 až +0.0164 % (medián 0.0091).

**DRZI** — posledné obdobie (2025-06 - 2026-08) je na 51. percentile, teda v medziach +0.0013 až +0.0164 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je. Signálov pritom ubudlo: z 20.97 na 10.01 obchodov za mesiac. To je úpadok tiež, len v break-evene ho vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 23** — 2025-07-22T18:24 až 2025-11-03T17:57, spolu +9424.34.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-07-22T18:24 | 2025-07-22T18:36 | +465.23 | +0.07 | `take_profit` |
| 2 | 2025-07-23T17:54 | 2025-07-23T18:03 | +327.59 | +0.05 | `take_profit` |
| 3 | 2025-07-23T18:07 | 2025-07-23T18:14 | +477.58 | +0.07 | `take_profit` |
| 4 | 2025-07-31T20:03 | 2025-07-31T20:18 | +563.83 | +0.18 | `take_profit` |
| 5 | 2025-08-01T15:18 | 2025-08-01T15:22 | +340.50 | +0.05 | `take_profit` |
| 6 | 2025-08-05T16:58 | 2025-08-05T17:25 | +263.88 | +0.08 | `take_profit` |
| 7 | 2025-08-06T22:12 | 2025-08-06T22:17 | +315.13 | +0.05 | `take_profit` |
| 8 | 2025-08-14T16:19 | 2025-08-14T16:21 | +414.79 | +0.06 | `take_profit` |
| 9 | 2025-08-15T16:00 | 2025-08-15T16:01 | +453.44 | +0.05 | `take_profit` |
| 10 | 2025-08-22T19:51 | 2025-08-24T22:00 | +977.23 | +0.15 | `take_profit` |
| 11 | 2025-09-17T18:51 | 2025-09-17T18:52 | +319.62 | +0.10 | `take_profit` |
| 12 | 2025-09-25T15:36 | 2025-09-25T15:40 | +288.30 | +0.09 | `take_profit` |
| 13 | 2025-10-02T16:05 | 2025-10-02T16:08 | +376.30 | +0.06 | `take_profit` |
| 14 | 2025-10-09T15:51 | 2025-10-09T16:01 | +413.69 | +0.06 | `take_profit` |
| 15 | 2025-10-12T23:21 | 2025-10-12T23:22 | +401.63 | +0.06 | `take_profit` |
| 16 | 2025-10-14T15:42 | 2025-10-14T15:43 | +376.58 | +0.06 | `take_profit` |
| 17 | 2025-10-14T17:45 | 2025-10-14T17:47 | +326.42 | +0.05 | `take_profit` |
| 18 | 2025-10-22T18:31 | 2025-10-22T18:38 | +369.47 | +0.11 | `take_profit` |
| 19 | 2025-10-23T15:59 | 2025-10-23T16:06 | +344.38 | +0.10 | `take_profit` |
| 20 | 2025-10-30T16:44 | 2025-10-30T17:05 | +463.30 | +0.07 | `take_profit` |
| 21 | 2025-10-30T20:33 | 2025-10-30T20:37 | +400.42 | +0.12 | `take_profit` |
| 22 | 2025-10-31T16:42 | 2025-10-31T16:56 | +319.21 | +0.09 | `take_profit` |
| 23 | 2025-11-03T17:44 | 2025-11-03T17:57 | +425.82 | +0.06 | `take_profit` |

**Straty za sebou: 6** — 2021-10-01T15:12 až 2021-10-04T19:51, spolu -4782.80.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2021-10-01T15:12 | 2021-10-01T15:13 | -990.08 | -0.23 | `stop_loss` |
| 2 | 2021-10-01T19:54 | 2021-10-01T19:58 | -532.64 | -0.24 | `stop_loss` |
| 3 | 2021-10-04T15:27 | 2021-10-04T15:32 | -865.02 | -0.20 | `stop_loss` |
| 4 | 2021-10-04T16:59 | 2021-10-04T17:03 | -690.00 | -0.16 | `stop_loss` |
| 5 | 2021-10-04T17:30 | 2021-10-04T18:00 | -765.03 | -0.18 | `stop_loss` |
| 6 | 2021-10-04T19:50 | 2021-10-04T19:51 | -940.03 | -0.22 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0088 %**, medián 0.0088 %, 90 % interval 0.0056–0.0119 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 10.0 %, 95. percentil 18.9 %, najhorší 41.7 %
- najdlhšia séria strát: medián 6, 95. percentil 9 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **1 636** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=c9c9ef90 -->

**1. Na čo sa to hodí a na čo nie.** Na E-mini S&P 500 (ES, aj MES s menšou pozíciou), 3m graf, ako **skalpovací doplnok k IBS EZ na NQ** — krátke obchody (medián 1,7 baru), WR ~74 %, cieľ ~0,5 R. Hodí sa na prop / menší účet, lebo séria strát je krátka (medián 6, 95. percentil 9) a DD v 95 % ciest do 19 %. Nehodí sa tam, kde je spread a sklz veľký voči cieľu: break-even 0,0088 % je asi päťnásobok poplatku, ale cieľ je pár tickov — na CFD US500 s horším fillom už PF klesá na 1,12 (krok 8). Na pomalé, široké seansy (obed, Ázia) to nie je.

**2. Má to potenciál?** Áno. Za skutočným javom hovorí: zisk v **5 z 5** okien vrátane odloženého roka (+16,5 %, WR 74,6 %), +7,5 sigma proti náhodnému vstupu v tých istých hodinách, edge v 100 % bootstrapových vzoriek a posledné obdobie na 51. percentile (nič neslabne). Žiadna skupina obchodov (deň, smer trendu, RR) výsledok nekazí — edge nie je schovaný v jednej podskupine. Proti hovorí len to, že **signálov ubúda** (z 21 na 10 za mesiac) a že US500 ide v poslednom roku na nulu (PF 0,99) — jav je teda viazaný na mikroštruktúru futures, nie na index všeobecne.

**3. Čo treba dorobiť.** (a) Sledovať frekvenciu: pri 10 obchodoch za mesiac je ročná vzorka malá; ak klesne ešte, profil č. 1 treba znova prepočítať. (b) Streda a pondelok majú break-even 0,003–0,004 % (ostatné dni 0,011–0,014 %) — rozdiel nie je veľký, ale stojí za test vynechania pondelka. (c) Výstupy: 74 % TP, 26 % SL, bez času — zvážiť časový stop pre obchody, ktoré sa do N barov nepohnú (dlhé držanie cez víkend, napr. 22.–24. 8. 2025). (d) Kópia do C# jadra (`ibsentrynet`) s ES profilom pred forward testom.

**4. Čo otestovať ďalej.** `cli matrix --pairs ES/USD,US500/USD --timeframes 3m,5m` — či 5m drží rovnaký PF (viac rezervy na sklz). `cli sweep` na `rrRatio` 0,4–0,75 a `minSlDistance` na odloženom roku nie (ten je spotrebovaný) — len na ladení, rozhodne, či plató okolo 0,5 R je široké. Krok 9: forward test na demo účte MES (alebo ES) 4–6 týždňov; rozhoduje, či WR živých obchodov ostane nad 70 % a priemerný sklz pod 1 tick.

**5. Je to použiteľné, alebo je to o ničom?** **Použiteľné** — prešlo smernicou celou (kroky 1–8), edge je štatisticky jasný a stabilný po rokoch. Ide do forward testu ako druhý trh k IBS EZ NQ; samostatne ako hlavná stratégia nie, kvôli klesajúcej frekvencii.

**6. Čo by som pridal.** Filter podľa toho, či **NQ potvrdzuje smer** (IBS zóna na ES len keď je NQ na tej istej strane VWAP / otvorenia) — S&P býva oneskorený za Nasdaqom a falošné prierazy na ES často prídu, keď NQ ide opačne. Druhý nápad: pri dvoch obchodoch denne obmedziť druhý len na smer prvého víťazného.

<!-- POSUDOK KONIEC -->
