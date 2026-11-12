# Základná analytika — WILLIAMS %R LONG 1.0 MYM (C# jadro) (`wprmymnet`)

Zmerané 2026-11-12 na `MYM/USD` 15m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `mym_databento_15m`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy wprmymnet \
   --profile mym_databento_15m \
   --pair MYM/USD \
   --timeframe 15m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 3816 obchodov spolu — na štatistiku dosť
- drawdown drží: 95. percentil 10.9 %
- charakter: protitrendová (mean reversion) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 2 z 5 referenčných okien (20221001-20231001, 20231001-20241001, 20240904-20250904 v strate)
- break-even 0.0017 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 50 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- nie je lepšia než náhodný vstup za tých istých pravidiel (-0.1 sigma) — výber vstupu nepridáva nič
- 100 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 817 | +1.33 | 0.0047 | 2.4 | 66.6 | +10/-6 | `20261112-112650-d7fbae` |
| 20221001-20231001 | 757 | -2.23 | -0.0035 | 3.7 | 62.8 | +14/-10 | `20261112-112657-ce3fc8` |
| 20231001-20241001 | 749 | -0.29 | 0.0011 | 3.7 | 64.0 | +15/-6 | `20261112-112703-7e70ec` |
| 20240904-20250904 | 774 | -0.92 | 0.0001 | 3.3 | 65.0 | +14/-7 | `20261112-112706-16ce42` |
| 20250904-20260904 | 774 | +2.67 | 0.0060 | 2.0 | 67.3 | +12/-5 | `20261112-112709-9b69f9` |

Zisková v **2 z 5** okien, obchodov spolu 3816, break-even celkom 0.0017 %. Okná sa prekrývajú, 55 obchodov započítaných dvakrát vypadlo.

## Charakter

**Protitrendová (mean reversion)** (istota dobrá)

- vstup proti poslednému pohybu (-1.46 ATR za 5 barov)
- medián držania 3 barov grafu
- winrate 64.96 %, payoff 0.539
- 2.12 obchodov za deň
- šikmosť výnosov -3.051

- **Čo je normálne:** Winrate nad 60 % a payoff pod 1 je pri tomto type v poriadku — zarába sa frekvenciou, nie veľkosťou.
- **Na čo pozor:** Jedna strata môže zmazať mesiac. Stop je tu dôležitejší než vstup a `maxLossDollar` aj drawdown limit majú väčší význam než pri ostatných typoch.
- **Čo ladiť:** Stop a filter režimu (v trende protitrendová stratégia dostáva rany). Ladiť RR nahor väčšinou len zníži winrate a nič nepridá.

Výstupy: `session_end` 100 %, `force_exit` 0 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0018 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Volatilita voči normálu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.732 | 962 | 25.2 % | 65.1 | -0.0035 | 0.0035 | +0.0018 |
| 0.732 – 0.983 | 948 | 24.8 % | 65.1 | -0.0010 | 0.0026 | +0.0009 |
| nad 1.425 | 952 | 24.9 % | 63.1 | 0.0054 | 0.0005 | -0.0012 |
| 0.983 – 1.425 | 954 | 25.0 % | 66.6 | 0.0059 | 0.0003 | -0.0014 |

**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 10.0002 % – 10.0031 % | 933 | 24.4 % | 65.8 | -0.0038 | 0.0035 | +0.0018 |
| do 9.9973 % | 956 | 25.1 % | 63.4 | -0.0034 | 0.0034 | +0.0017 |
| nad 10.0031 % | 951 | 24.9 % | 64.8 | 0.0053 | 0.0005 | -0.0012 |
| 9.9973 % – 10.0002 % | 976 | 25.6 % | 65.9 | 0.0085 | -0.0006 | -0.0023 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 16 – 23 | 885 | 23.2 % | 62.0 | -0.0040 | 0.0034 | +0.0017 |
| do 8 | 1006 | 26.4 % | 64.6 | -0.0003 | 0.0024 | +0.0007 |
| 8 – 16 | 1011 | 26.5 % | 67.5 | 0.0049 | 0.0005 | -0.0012 |
| nad 23 | 914 | 24.0 % | 65.4 | 0.0059 | 0.0004 | -0.0013 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0017 % | 0.0020 % ± 0.0024 | -0.10 | 45.8 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0017 % | 0.0020 % ± 0.0024 | -0.10 | 45.8 |

Neodlisitelne od nahody (-0.1 sigma, percentil 45.8). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 988 | 67.0 | 66.3 | 0.0050 | 81 |
| 2022-12 - 2024-03 | 954 | 64.7 | 63.6 | -0.0006 | 24 |
| 2024-03 - 2025-06 | 933 | 63.2 | 63.1 | -0.0038 | 7 |
| 2025-06 - 2026-09 | 941 | 63.8 | 66.7 | 0.0057 | 85 |

Hranice pre úsek veľkosti posledného obdobia: -0.0050 až +0.0081 % (medián 0.0017).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 85. percentile, teda v medziach -0.0050 až +0.0081 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 15** — 2024-03-25T10:15 až 2024-04-01T10:30, spolu +136.50.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-03-25T10:15 | 2024-03-25T10:30 | +13.30 | +0.07 | `session_end` |
| 2 | 2024-03-25T11:45 | 2024-03-25T12:00 | +9.80 | +0.05 | `session_end` |
| 3 | 2024-03-25T14:45 | 2024-03-25T15:30 | +7.30 | +0.04 | `session_end` |
| 4 | 2024-03-25T16:45 | 2024-03-25T18:15 | +3.80 | +0.02 | `session_end` |
| 5 | 2024-03-25T20:15 | 2024-03-25T20:30 | +5.30 | +0.03 | `session_end` |
| 6 | 2024-03-26T03:45 | 2024-03-26T04:00 | +5.80 | +0.03 | `session_end` |
| 7 | 2024-03-26T08:00 | 2024-03-26T08:30 | +13.80 | +0.07 | `session_end` |
| 8 | 2024-03-26T13:15 | 2024-03-26T13:15 | +16.80 | +0.08 | `session_end` |
| 9 | 2024-03-26T19:45 | 2024-03-26T20:00 | +12.30 | +0.06 | `session_end` |
| 10 | 2024-03-27T07:45 | 2024-03-27T09:00 | +9.80 | +0.05 | `session_end` |
| 11 | 2024-03-27T16:15 | 2024-03-27T16:15 | +16.30 | +0.08 | `session_end` |
| 12 | 2024-03-28T14:30 | 2024-03-28T14:45 | +9.30 | +0.05 | `session_end` |
| 13 | 2024-04-01T02:45 | 2024-04-01T02:45 | +3.29 | +0.02 | `session_end` |
| 14 | 2024-04-01T03:30 | 2024-04-01T03:30 | +2.79 | +0.01 | `session_end` |
| 15 | 2024-04-01T09:15 | 2024-04-01T10:30 | +6.79 | +0.03 | `session_end` |

**Straty za sebou: 10** — 2023-02-23T16:15 až 2023-03-01T14:30, spolu -368.76.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-02-23T16:15 | 2023-02-23T17:45 | -65.58 | -0.40 | `session_end` |
| 2 | 2023-02-24T09:00 | 2023-02-24T16:00 | -180.08 | -1.09 | `session_end` |
| 3 | 2023-02-27T05:15 | 2023-02-27T07:00 | -3.08 | -0.02 | `session_end` |
| 4 | 2023-02-27T16:15 | 2023-02-27T17:30 | -13.58 | -0.08 | `session_end` |
| 5 | 2023-02-28T04:45 | 2023-02-28T06:00 | -5.08 | -0.03 | `session_end` |
| 6 | 2023-02-28T07:15 | 2023-02-28T08:45 | -13.58 | -0.08 | `session_end` |
| 7 | 2023-02-28T14:30 | 2023-02-28T16:00 | -43.08 | -0.26 | `session_end` |
| 8 | 2023-02-28T20:30 | 2023-02-28T21:30 | -22.57 | -0.14 | `session_end` |
| 9 | 2023-02-28T23:30 | 2023-03-01T01:00 | -18.07 | -0.11 | `session_end` |
| 10 | 2023-03-01T13:30 | 2023-03-01T14:30 | -4.07 | -0.02 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0017 %**, medián 0.0017 %, 90 % interval -0.0015–0.0049 %
- P(edge > poplatok) = **49.5 %**
- max drawdown: medián 5.3 %, 95. percentil 10.9 %, najhorší 21.4 %
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
<!-- POSUDOK cisla=ad4966ed -->

**1. Na čo sa to hodí.** _(C# jadro `wprmymnet`: čísla sú v každom okne zhodné s Python `wprmym`.)_ Krátkodobý návrat k priemeru (Williams %R, len long) na MYM 15m. Vysoký počet obchodov (~770 za rok) a WR okolo 65 %.

**2. Potenciál.** Charakter sedí (protitrendová, istota dobrá) a Dow je najmenej trendový index, teda pre mean reversion najvhodnejší z troch. Čísla to zatiaľ nepotvrdzujú: proti náhode −0,1 sigma, zisk v 2 z 5 okien, break-even celkom len 0,0017 %. Výsledok je tenký a pri takom počte obchodov ho zožerú náklady.

**3. Čo dorobiť.** V logike nič, C# `wprmymnet` sedí bar po bare. Treba prahy (`entryLevel`, `exitLevel`), stop a filter trendu ladiť pre MYM.

**4. Čo otestovať.** Smernica od 12. 11. 19:00. Rozhodne, či menej a lepších obchodov (prísnejší `entryLevel`, filter trendu „with“) dá PF ≥ 1,3 v každom roku pri ≥ 75 obchodoch za rok.

**5. Použiteľné?** Zatiaľ **nie**, ale z ôsmich MYM stratégií má podľa charakteru trhu najlepšiu šancu.

**6. Čo by som pridal.** Výstup v čase (napr. do 3–5 barov) namiesto čakania na `exitLevel`: návrat na Dow je krátky a dlhé držanie zbytočne nesie riziko trendového dňa.

<!-- POSUDOK KONIEC -->
