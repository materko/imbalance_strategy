# Základná analytika — NY VA BREAKOUT ES (`nyvaes`)

Zmerané 2026-10-24 na `ES/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/nyvaes_PRESIEL_SMERNICAMI_NY_VA_BREAKOUT_ES_1_2026-10-24.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy nyvaes \
   --profile .nightsearch/checkup/nyvaes_PRESIEL_SMERNICAMI_NY_VA_BREAKOUT_ES_1_2026-10-24.json \
   --pair ES/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 753 obchodov spolu — na štatistiku dosť
- break-even 0.0098 % je nad poplatkom 0.0018 % (rezerva +0.0080 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 12.0 %
- odlíšiteľná od náhody (+7.0 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-08 na 28. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- proti náhode v tých istých hodinách je rozdiel podstatne menší (+5.2 vs +7.0 sigma) — veľká časť edge je v tom, KEDY obchoduje, nie v tom, čo si vyberá
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'bežný deň' vlastnosti 'Sviatok na burze v USA': 708 obchodov (94.0 %), bez nej by break-even bol o +0.0121 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 157 | +12.31 | 0.0115 | 3.6 | 74.5 | +11/-2 | `20261024-064721-065f5a` |
| 20221001-20231001 | 146 | +10.42 | 0.0104 | 3.0 | 71.9 | +13/-4 | `20261024-064733-687edf` |
| 20231001-20241001 | 155 | +11.25 | 0.0082 | 4.9 | 73.5 | +11/-4 | `20261024-064742-edb105` |
| 20240904-20250904 | 151 | +17.11 | 0.0115 | 5.9 | 72.2 | +8/-5 | `20261024-064751-5dcf63` |
| 20250904-20260904 | 160 | +13.78 | 0.0088 | 10.4 | 73.1 | +18/-4 | `20261024-064803-7eedf5` |

Zisková v **5 z 5** okien, obchodov spolu 753, break-even celkom 0.0098 %. Okná sa prekrývajú, 16 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+0.50 ATR za 5 barov)
- medián držania 2.3 barov grafu
- winrate 72.91 %, payoff 0.503
- 0.42 obchodov za deň
- šikmosť výnosov -1.215

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 72.9 %, `stop_loss` 27.1 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'bežný deň' vlastnosti 'Sviatok na burze v USA': 708 obchodov (94.0 %), break-even 0.0089 % oproti 0.0098 % celku. Bez nej by break-even bol 0.0219 % (+0.0121). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bežný deň | 708 | 94.0 % | 72.3 | 0.0089 | 0.0219 | +0.0121 |
| deň po sviatku | 23 | 3.1 % | 69.6 | 0.0169 | 0.0096 | -0.0002 |
| deň pred sviatkom | 9 | 1.2 % | 100.0 | 0.0419 | 0.0094 | -0.0004 |

**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| FOMC | 27 | 3.6 % | 70.4 | 0.0028 | 0.0100 | +0.0002 |
| žiadna | 660 | 87.6 % | 72.3 | 0.0086 | 0.0185 | +0.0087 |
| CPI | 33 | 4.4 % | 81.8 | 0.0218 | 0.0093 | -0.0005 |
| NFP | 33 | 4.4 % | 78.8 | 0.0281 | 0.0090 | -0.0008 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| pred vyhlásením | 27 | 3.6 % | 70.4 | 0.0028 | 0.0100 | +0.0002 |
| bez udalosti | 660 | 87.6 % | 72.3 | 0.0086 | 0.0185 | +0.0087 |
| po vyhlásení | 66 | 8.8 % | 80.3 | 0.0250 | 0.0084 | -0.0014 |

Parametre, ktorými sa dá s tým niečo spraviť: `entryEndH`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0107 % | -0.0001 % ± 0.0016 | +6.96 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0107 % | -0.0001 % ± 0.0021 | +5.17 | 100.0 |

Edge je odlisitelny od nahody (7.0 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 190 | 12.9 | 75.8 | 0.0156 | 93 |
| 2022-12 - 2024-03 | 184 | 12.5 | 71.7 | 0.0082 | 37 |
| 2024-03 - 2025-06 | 189 | 12.8 | 72.0 | 0.0096 | 46 |
| 2025-06 - 2026-08 | 190 | 12.9 | 72.1 | 0.0074 | 28 |

Hranice pre úsek veľkosti posledného obdobia: +0.0025 až +0.0169 % (medián 0.0096).

**DRZI** — posledné obdobie (2025-06 - 2026-08) je na 28. percentile, teda v medziach +0.0025 až +0.0169 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 18** — 2025-08-22T14:49 až 2025-09-29T14:41, spolu +3771.00, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-08-22T14:49 | 2025-08-22T15:34 | +488.61 | +0.15 | `take_profit` |
| 2 | 2025-08-25T14:51 | 2025-08-25T15:04 | +227.28 | +0.04 | `take_profit` |
| 3 | 2025-08-26T14:33 | 2025-08-26T14:34 | +152.33 | +0.02 | `take_profit` |
| 4 | 2025-08-29T14:51 | 2025-08-29T14:52 | +201.17 | +0.06 | `take_profit` |
| 5 | 2025-09-03T14:33 | 2025-09-03T14:37 | +113.67 | +0.04 | `take_profit` |
| 6 | 2025-09-04T14:33 | 2025-09-04T14:36 | +126.14 | +0.04 | `take_profit` |
| 7 | 2025-09-08T14:33 | 2025-09-08T14:36 | +138.58 | +0.04 | `take_profit` |
| 8 | 2025-09-11T14:52 | 2025-09-11T14:54 | +163.45 | +0.05 | `take_profit` |
| 9 | 2025-09-12T14:33 | 2025-09-12T14:55 | +138.43 | +0.04 | `take_profit` |
| 10 | 2025-09-15T14:38 | 2025-09-15T14:40 | +151.57 | +0.02 | `take_profit` |
| 11 | 2025-09-16T14:42 | 2025-09-16T15:01 | +125.80 | +0.04 | `take_profit` |
| 12 | 2025-09-17T14:55 | 2025-09-17T15:01 | +150.81 | +0.05 | `take_profit` |
| 13 | 2025-09-18T14:52 | 2025-09-18T15:19 | +313.24 | +0.09 | `take_profit` |
| 14 | 2025-09-19T14:52 | 2025-09-19T14:55 | +163.24 | +0.05 | `take_profit` |
| 15 | 2025-09-22T14:38 | 2025-09-22T14:43 | +188.19 | +0.06 | `take_profit` |
| 16 | 2025-09-23T14:55 | 2025-09-23T14:57 | +201.31 | +0.03 | `take_profit` |
| 17 | 2025-09-26T14:39 | 2025-09-26T14:49 | +500.80 | +0.15 | `take_profit` |
| 18 | 2025-09-29T14:33 | 2025-09-29T14:41 | +226.39 | +0.03 | `take_profit` |

**Straty za sebou: 5** — 2025-05-15T14:36 až 2025-05-22T14:41, spolu -1739.41.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-05-15T14:36 | 2025-05-15T14:55 | -410.34 | -0.14 | `stop_loss` |
| 2 | 2025-05-16T14:50 | 2025-05-16T15:11 | -322.92 | -0.11 | `stop_loss` |
| 3 | 2025-05-20T14:57 | 2025-05-20T14:59 | -285.46 | -0.10 | `stop_loss` |
| 4 | 2025-05-21T14:49 | 2025-05-21T14:56 | -447.90 | -0.15 | `stop_loss` |
| 5 | 2025-05-22T14:39 | 2025-05-22T14:41 | -272.77 | -0.09 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0098 %**, medián 0.0098 %, 90 % interval 0.0061–0.0133 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 6.8 %, 95. percentil 12.0 %, najhorší 24.8 %
- najdlhšia séria strát: medián 5, 95. percentil 6 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **1 402** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=f94088ac -->

**1. Na čo sa to hodí a na čo nie.** Na ES (aj MES) 3m, len prvé dopoludnie New Yorku: profil 9:30–10:30, vstupy do 11:00, **retest** — limitka na VAH / VAL po prieraze, cieľ 0,5 R, stop 8 tickov za POC (najviac 3 ATR), len pri vyššej volatilite. Je to jeden krátky obchod denne (0,42 obchodu za deň, medián držania 2,3 baru), WR ~73 %. Hodí sa na prop účet a ako druhý trh k NQ stratégiám: DD v 95 % ciest do 12 %, séria strát najviac 6. Nehodí sa na CFD so širokým spreadom (cieľ 0,5 R je pár bodov) ani na popoludnie — mimo prvej hodiny sa logika nedá použiť.

**2. Má to potenciál?** Áno. Zisk v **5 z 5** okien rovnomerne (PnL +10 až +17 % ročne, WR 72–75 % v každom), odložený rok +13,8 %, break-even 0,0098 % je 5,5× poplatok a edge je nad poplatkom v 100 % bootstrapových vzoriek. Frekvencia sa nemení (12,5–12,9 obchodu za mesiac vo všetkých úsekoch) — na rozdiel od IBS EZ ES signály neubúdajú. Opatrne treba brať to, že proti náhode **v tých istých hodinách** je to už len +5,2 sigma (proti +7,0): časť edge je v tom, že obchoduje v prvej hodine, kedy sa ES hýbe najviac. Posledné obdobie je na 28. percentile — stále v norme, ale najslabší úsek zo štyroch.

**3. Čo treba dorobiť.** (a) Dni so správami: po vyhlásení (CPI, NFP) je break-even 0,025 %, kým deň FOMC (vyhlásenie poobede, obchod ráno pred ním) len 0,003 % — FOMC dni vynechať stojí za test, je ich 27. (b) Tabuľka „sviatok“ je skreslená (94 % obchodov je „bežný deň“), filter tam nie je. (c) Kópia do C# jadra pred forward testom (retest = limitka, treba overiť fill na NT / MT5). (d) Kontrolovať sklz: pri cieli 0,5 R rozhoduje 1 tick.

**4. Čo otestovať ďalej.** `cli matrix --pairs ES/USD,US500/USD --timeframes 3m,5m` — 5m by mal dať podobné úrovne VA s menším šumom. `cli sweep` na `entryEndH` 10:45–12:00 a `rrRatio` 0,4–0,75 len na ladení (odložený rok je spotrebovaný) — rozhodne, či plató okolo 11:00 / 0,5 R je široké. Krok 8 na US500 (CFD) **neprešiel** — PF 0,98, 730 obchodov, roky 1,07 / 0,95 / 1,04 / 0,98 / 0,91: jav je viazaný na objem a fill futures, na CFD s iným objemom a spreadom nedrží. Krok 9 teda len na ES / MES: forward test: forward test na MES 4–6 týždňov s porovnaním WR a sklzu proti backtestu.

**5. Je to použiteľné, alebo je to o ničom?** **Použiteľné len na futures (ES / MES).** Prešlo smernicou cez krok 7, krok 8 na US500 nie a analytika nemá vážnu slabinu: stabilné roky, stála frekvencia, štatisticky jasný edge. Do forward testu ide ako doplnok k IBS EZ ES — obe sú na ES, ale v iných hodinách a s inou logikou (NY VA len 9:30–11:00).

**6. Čo by som pridal.** Vynechanie dní FOMC a obchod len **v smere prvého prierazu dňa NQ** — keď Nasdaq v prvej hodine prerazí opačným smerom ako ES, prieraz ES býva falošný. Druhý nápad: pri retestovej limitke posunúť cieľ na najbližší vrchol rangeu (high prvej hodiny), ak je bližšie ako 0,5 R — skráti držanie bez straty WR.

<!-- POSUDOK KONIEC -->
