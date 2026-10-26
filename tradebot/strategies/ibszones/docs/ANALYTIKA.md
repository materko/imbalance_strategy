# Základná analytika — IBS plus zmena zón (`ibszones`)

Zmerané 2026-10-26 na `MNQ/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/ibszones/configs/multicharts_mnq_3m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy ibszones \
   --profile tradebot/strategies/ibszones/configs/multicharts_mnq_3m.json \
   --pair MNQ/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 923 obchodov spolu — na štatistiku dosť
- odlíšiteľná od náhody (+2.5 sigma proti náhodnému vstupu)
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 2 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20231001-20241001 v strate)
- break-even 0.0011 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 30 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 38.9 % (namerané 19.9 % medián) — na účet to treba mať
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 173 | -3.17 | -0.0003 | 6.2 | 49.1 | +7/-5 | `20261026-130930-94167e` |
| 20221001-20231001 | 163 | -12.01 | -0.0041 | 13.4 | 44.2 | +6/-6 | `20261026-130942-0aeccc` |
| 20231001-20241001 | 188 | -3.88 | 0.0005 | 8.7 | 51.1 | +7/-6 | `20261026-130955-2adeb4` |
| 20240904-20250904 | 222 | +4.21 | 0.0030 | 4.0 | 53.1 | +9/-8 | `20261026-131007-f33642` |
| 20250904-20260904 | 177 | +6.41 | 0.0049 | 7.3 | 56.5 | +8/-4 | `20261026-131017-d4b97e` |

Zisková v **2 z 5** okien, obchodov spolu 923, break-even celkom 0.0011 %.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+0.41 ATR za 5 barov)
- medián držania 4.3 barov grafu
- winrate 51.03 %, payoff 0.926
- 0.51 obchodov za deň
- šikmosť výnosov -0.118

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 50.2 %, `stop_loss` 47.9 %, `session_end` 1.8 %, `trailing_stop` 0.1 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0026 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**S trendom, alebo proti** (riadi `useStructureFilter`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 575 | 62.3 % | 49.2 | -0.0005 | 0.0037 | +0.0026 |
| proti trendu | 348 | 37.7 % | 54.0 | 0.0037 | -0.0005 | -0.0016 |

**Trend alebo rozsah** (riadi `useStructureFilter`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 0.1689 | 230 | 24.9 % | 44.4 | -0.0047 | 0.0032 | +0.0021 |
| 0.0993 – 0.1689 | 230 | 24.9 % | 51.3 | 0.0010 | 0.0011 | +0.0000 |
| 0.043 – 0.0993 | 232 | 25.1 % | 53.5 | 0.0041 | 0.0001 | -0.0010 |
| do 0.043 | 231 | 25.0 % | 55.0 | 0.0046 | -0.0000 | -0.0011 |

**Plánovaný RR** (riadi `rrRatio`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 1 R | 133 | 14.6 % | 41.4 | -0.0031 | 0.0025 | +0.0014 |
| do 1 R | 781 | 85.4 % | 53.3 | 0.0025 | -0.0031 | -0.0042 |

Parametre, ktorými sa dá s tým niečo spraviť: `closeAtSessionEnd`, `minSlDistance`, `rrRatio`, `sess2TradeStartH`, `state2MaxBars`, `useStructureFilter`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0067 % | 0.0003 % ± 0.0025 | +2.51 | 99.4 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0067 % | 0.0002 % ± 0.0026 | +2.51 | 99.0 |

Edge je odlisitelny od nahody (2.5 sigma, percentil 99.4).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 214 | 14.5 | 48.1 | -0.0018 | 14 |
| 2022-12 - 2024-03 | 222 | 15.1 | 46.9 | -0.0017 | 15 |
| 2024-03 - 2025-06 | 258 | 17.5 | 53.9 | 0.0030 | 80 |
| 2025-06 - 2026-09 | 229 | 15.6 | 54.6 | 0.0033 | 82 |

Hranice pre úsek veľkosti posledného obdobia: -0.0032 až +0.0053 % (medián 0.0010).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 82. percentile, teda v medziach -0.0032 až +0.0053 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 9** — 2025-05-30T07:57 až 2025-06-10T08:48, spolu +2850.70.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-05-30T07:57 | 2025-05-30T07:59 | +345.01 | +0.05 | `take_profit` |
| 2 | 2025-05-30T08:56 | 2025-05-30T09:18 | +329.99 | +0.07 | `take_profit` |
| 3 | 2025-05-30T14:03 | 2025-05-30T14:12 | +270.00 | +0.32 | `take_profit` |
| 4 | 2025-06-03T08:43 | 2025-06-03T10:31 | +329.97 | +0.15 | `take_profit` |
| 5 | 2025-06-04T14:22 | 2025-06-04T15:11 | +282.95 | +0.33 | `take_profit` |
| 6 | 2025-06-06T14:33 | 2025-06-06T14:35 | +318.29 | +0.10 | `take_profit` |
| 7 | 2025-06-06T14:45 | 2025-06-06T15:06 | +310.40 | +0.24 | `take_profit` |
| 8 | 2025-06-09T08:48 | 2025-06-09T08:49 | +324.63 | +0.06 | `take_profit` |
| 9 | 2025-06-10T08:45 | 2025-06-10T08:48 | +339.46 | +0.05 | `take_profit` |

**Straty za sebou: 8** — 2025-02-28T16:46 až 2025-03-13T15:08, spolu -1994.39.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-02-28T16:46 | 2025-02-28T17:43 | -184.95 | -0.45 | `stop_loss` |
| 2 | 2025-03-04T09:14 | 2025-03-04T09:40 | -352.20 | -0.17 | `stop_loss` |
| 3 | 2025-03-04T09:42 | 2025-03-04T09:42 | -21.58 | -0.00 | `stop_loss` |
| 4 | 2025-03-04T15:42 | 2025-03-04T15:54 | -233.84 | -0.29 | `stop_loss` |
| 5 | 2025-03-05T15:24 | 2025-03-05T16:11 | -332.86 | -0.41 | `stop_loss` |
| 6 | 2025-03-07T10:15 | 2025-03-07T11:00 | -328.41 | -0.12 | `stop_loss` |
| 7 | 2025-03-07T15:03 | 2025-03-07T15:16 | -254.82 | -0.32 | `stop_loss` |
| 8 | 2025-03-13T14:54 | 2025-03-13T15:08 | -285.73 | -0.37 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0011 %**, medián 0.0011 %, 90 % interval -0.0010–0.0031 %
- P(edge > poplatok) = **29.7 %**
- max drawdown: medián 19.9 %, 95. percentil 38.9 %, najhorší 68.0 %
- najdlhšia séria strát: medián 8, 95. percentil 11 obchodov
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
<!-- POSUDOK cisla=f9b54afe -->

_Posudok (Claude, 26. 10. 2026) — nastavenie `multicharts_mnq_3m`: referenčný profil repozitára (parametre IBS pre MNQ),
nie ladený. `ibszones` je `ibs` so synchronizovanou detekciou zón (zóna nezávisí od TF grafu); čísla hovoria o tejto
zmene na defaultoch, nie o najlepšom nastavení._

1. **Na čo sa to hodí a na čo nie.** V tejto podobe na nič. MNQ 3m, 923 obchodov, winrate 51 %, payoff 0,93: break-even
   0,0011 % je pod poplatkom 0,0018 %, ziskové sú len 2 z 5 rokov (2024/25 a 2025/26) a 95. percentil drawdownu 38,9 %.
   Ladené profily testera (`MNQ_R05_WR80_*`, `NOCNE*`) sú ladené na poslednom roku a ten o ostatných nehovorí.
2. **Má to potenciál? Slabý.** Za javom: +2,5 σ proti náhodnému vstupu a posledné dve obdobia sú lepšie (80. a 82.
   percentil). Proti: prvé dva roky sú stratové a edge nad poplatkom má len 30 % bootstrapu. Kontrola ladeného
   profilu `MNQ_R05_WR80_najlepsi_pomer_zones` na tých istých piatich oknách (26. 10., `--no-write`, behy v histórii
   s poznámkou „posudok ibszones“): 3 z 5 rokov v zisku, break-even 0,0098 %, +2,1 σ, ale 2021/22 −9,0 % a 2022/23
   −0,7 % a polovica zisku je z ladeného roku 25/26 (+25,4 %, WR 80,5 %). Čím ďalej od ladeného roku, tým horšie — to
   je podpis pretrénovania, nie javu.
3. **Čo treba dorobiť.** (a) Ladiť s oknami cez všetky roky. (b) Obchody v smere trendu (62 %) majú break-even
   −0,0005 %, proti trendu +0,0037 % a v rozsahu (`trend alebo rozsah` do 0,1) sú lepšie — stratégia je v skutočnosti
   návrat do rozsahu, nie prerazenie; `useStructureFilter` to dnes nevie povedať opačne. (c) RR nad 1 má break-even
   −0,0031 % — cieľ do 1 R je pre tento vstup prirodzený.
4. **Čo otestovať ďalej.** `cli hyperopt --strategy ibszones --pair MNQ/USD --engine multicharts --timeframe 3m --windows ref
   --aggregate min --select plateau` s `rrRatio` do 1, `useStructureFilter` a prahmi zón. Doplnkovo `cli checkup` toho
   istého profilu na `ibs` — rozhodne, či synchronizovaná detekcia zón výsledok mení, alebo je to len iný TF tej istej
   stratégie.
5. **Je to použiteľné? Nie** — referenčný profil je pod poplatkom a ladený profil drží len blízko roku, na ktorom bol
   ladený. Hodnota `ibszones` je v tom, že zóny nezávisia od TF grafu (technická oprava proti `ibs`), nie v edge.
6. **Čo by som pridal.** Filter „obchoduj len v rozsahu“ (meranie trendu pod prahom) — skupiny ukazujú, že edge je
   v pokojnom trhu a proti krátkodobému trendu; jeden prepínač by to overil bez ďalšieho hľadania.

<!-- POSUDOK KONIEC -->
