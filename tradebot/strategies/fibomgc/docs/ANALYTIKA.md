# Základná analytika — Fibo 1.0 (MGC) (`fibomgc`)

Zmerané 2026-10-22 na `MGC/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/fibomgc_PRESIEL_SMERNICAMI_Fibo_1_0_MGC_1_2026-10-22.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy fibomgc \
   --profile .nightsearch/checkup/fibomgc_PRESIEL_SMERNICAMI_Fibo_1_0_MGC_1_2026-10-22.json \
   --pair MGC/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 834 obchodov spolu — na štatistiku dosť
- break-even 0.0300 % je nad poplatkom 0.0018 % (rezerva +0.0282 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 5.9 %
- odlíšiteľná od náhody (+4.5 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 92. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- charakter: formácia / štruktúra (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 's trendom' vlastnosti 'S trendom, alebo proti': 698 obchodov (83.7 %), bez nej by break-even bol o +0.0233 lepší (riadi `requireBreak`)

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 169 | +2.45 | 0.0160 | 1.5 | 61.5 | +10/-4 | `20261022-071808-a95008` |
| 20221001-20231001 | 167 | +2.22 | 0.0138 | 1.9 | 62.3 | +12/-5 | `20261022-071820-cd36e5` |
| 20231001-20241001 | 180 | +6.26 | 0.0330 | 1.1 | 66.7 | +11/-6 | `20261022-071823-d9eb17` |
| 20240904-20250904 | 167 | +2.85 | 0.0160 | 2.2 | 64.1 | +7/-4 | `20261022-071826-286597` |
| 20250904-20260904 | 165 | +14.28 | 0.0585 | 5.6 | 63.6 | +8/-5 | `20261022-071829-e1429c` |

Zisková v **5 z 5** okien, obchodov spolu 834, break-even celkom 0.0300 %. Okná sa prekrývajú, 14 obchodov započítaných dvakrát vypadlo.

## Charakter

**Formácia / štruktúra** (istota priemerná)

- vstup bez jasného smeru pohybu (+0.07 ATR za 5 barov)
- medián držania 51.8 barov grafu
- winrate 63.79 %, payoff 0.81
- 0.46 obchodov za deň
- šikmosť výnosov -0.116

- **Čo je normálne:** Zmes: časť obchodov sa chová ako prerazenie, časť ako návrat. Priemer preto o jednotlivom obchode nehovorí veľa.
- **Na čo pozor:** Práve pri tomto type sa najviac oplatí rozdeliť obchody na skupiny (`tester.analytics`) — priemer skrýva dve rôzne populácie.
- **Čo ladiť:** Podmienky vstupu (ktoré modely/formácie zapnuté) a potom až výstup.

Výstupy: `take_profit` 63.8 %, `stop_loss` 36.2 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 's trendom' vlastnosti 'S trendom, alebo proti': 698 obchodov (83.7 %), break-even 0.0258 % oproti 0.03 % celku. Bez nej by break-even bol 0.0533 % (+0.0233). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: skus preladit `requireBreak`.


**S trendom, alebo proti** (riadi `requireBreak`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 698 | 83.7 % | 63.5 | 0.0258 | 0.0533 | +0.0233 |
| proti trendu | 136 | 16.3 % | 65.4 | 0.0533 | 0.0258 | -0.0042 |

**Vzdialenosť stopu** (riadi `slBufferAtr`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.2221 % | 210 | 25.2 % | 65.7 | 0.0162 | 0.0386 | +0.0086 |
| 0.3444 % – 0.4948 % | 208 | 24.9 % | 60.6 | 0.0163 | 0.0334 | +0.0034 |
| 0.2221 % – 0.3444 % | 208 | 24.9 % | 64.4 | 0.0216 | 0.0321 | +0.0021 |
| nad 0.4948 % | 208 | 24.9 % | 64.4 | 0.0726 | 0.0176 | -0.0124 |

**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.0642 | 209 | 25.1 % | 58.4 | 0.0082 | 0.0383 | +0.0083 |
| 0.1242 – 0.1812 | 208 | 24.9 % | 64.4 | 0.0362 | 0.0281 | -0.0019 |
| 0.0642 – 0.1242 | 209 | 25.1 % | 67.5 | 0.0377 | 0.0274 | -0.0026 |
| nad 0.1812 | 208 | 24.9 % | 64.9 | 0.0412 | 0.0267 | -0.0033 |

Parametre, ktorými sa dá s tým niečo spraviť: `maxHoldBars`, `requireBreak`, `rrRatio`, `slBufferAtr`, `tradeStartH`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0348 % | 0.0034 % ± 0.0070 | +4.51 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0348 % | 0.0037 % ± 0.0073 | +4.29 | 100.0 |

Edge je odlisitelny od nahody (4.5 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 215 | 14.6 | 60.9 | 0.0124 | 14 |
| 2022-12 - 2024-03 | 195 | 13.2 | 65.1 | 0.0214 | 29 |
| 2024-03 - 2025-06 | 222 | 15.1 | 64.0 | 0.0238 | 34 |
| 2025-06 - 2026-09 | 202 | 13.7 | 65.3 | 0.0540 | 92 |

Hranice pre úsek veľkosti posledného obdobia: +0.0023 až +0.0576 % (medián 0.0297).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 92. percentile, teda v medziach +0.0023 až +0.0576 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 12** — 2023-03-15T23:00 až 2023-04-11T00:14, spolu +982.89.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-03-15T23:00 | 2023-03-15T23:52 | +66.26 | +0.11 | `take_profit` |
| 2 | 2023-03-17T19:36 | 2023-03-20T07:06 | +178.55 | +0.87 | `take_profit` |
| 3 | 2023-03-20T17:06 | 2023-03-20T18:17 | +60.79 | +0.30 | `take_profit` |
| 4 | 2023-03-21T23:09 | 2023-03-22T00:05 | +63.21 | +0.10 | `take_profit` |
| 5 | 2023-03-22T16:15 | 2023-03-22T18:00 | +71.05 | +0.36 | `take_profit` |
| 6 | 2023-03-23T15:16 | 2023-03-23T16:33 | +118.54 | +0.59 | `take_profit` |
| 7 | 2023-03-24T11:03 | 2023-03-24T12:33 | +95.28 | +0.46 | `take_profit` |
| 8 | 2023-03-28T14:12 | 2023-03-28T14:58 | +93.56 | +0.47 | `take_profit` |
| 9 | 2023-03-28T16:24 | 2023-03-28T17:50 | +67.80 | +0.34 | `take_profit` |
| 10 | 2023-03-30T08:00 | 2023-03-30T12:26 | +64.77 | +0.32 | `take_profit` |
| 11 | 2023-04-04T17:07 | 2023-04-05T06:22 | +38.51 | +0.18 | `take_profit` |
| 12 | 2023-04-10T20:27 | 2023-04-11T00:14 | +64.59 | +0.16 | `take_profit` |

**Straty za sebou: 6** — 2024-04-09T10:33 až 2024-04-24T09:19, spolu -704.16.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-04-09T10:33 | 2024-04-09T15:07 | -138.86 | -0.57 | `stop_loss` |
| 2 | 2024-04-10T07:03 | 2024-04-10T12:30 | -127.87 | -0.51 | `stop_loss` |
| 3 | 2024-04-10T18:10 | 2024-04-11T08:50 | -129.87 | -0.53 | `stop_loss` |
| 4 | 2024-04-15T12:24 | 2024-04-15T13:41 | -95.87 | -0.39 | `stop_loss` |
| 5 | 2024-04-17T10:21 | 2024-04-17T16:32 | -109.87 | -0.44 | `stop_loss` |
| 6 | 2024-04-23T19:25 | 2024-04-24T09:19 | -101.84 | -0.43 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0300 %**, medián 0.0301 %, 90 % interval 0.0167–0.0436 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 3.3 %, 95. percentil 5.9 %, najhorší 13.9 %
- najdlhšia séria strát: medián 6, 95. percentil 8 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **610** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=27b12f70 -->

**1. Na čo sa to hodí a na čo nie.** Na zlato (MGC, 3m graf), obchody od 2:00 do 20:00 ET, **len long**, limitkou na úrovni
Fibonacciho návratu (38,2 / 50 / 61,8 %) po nohe pohybu aspoň 2 ATR, stop za nohou, cieľ 0,75 R. Sedí s prieskumom zlata
(MacBook 21. 10.): zlato je mierne návratové a zóny / návraty majú náskok, prierazy nie. Na Nasdaq ani na kryptá sa tieto
čísla preniesť nedajú (iný charakter trhu); na CFD zlate (XAU/USD Dukascopy) drží slabšie (krok 8: PF 1,28, 4 z 5 rokov).

**2. Má to potenciál?** Áno — z doterajších stratégií na zlate najväčší. Za skutočným javom hovorí: zisk v 5 z 5 okien
(break-even 0,014–0,059 % pri poplatku 0,0018 %), **+4,5 sigma proti náhodnému vstupu** v tých istých hodinách
(výber vstupu pridáva, nie len drift zlata), edge v poslednom období na 92. percentile (neslabne), Monte Carlo 95. percentil
DD 5,9 %. Proti: **len long v roku, keď zlato rástlo z ~1 800 na ~4 000 $** — časť výsledku je smer trhu; rok 2025/26
(+14 %) je výrazne nad ostatnými (+2–6 %). Východiskový profil z MacBooku bol vybraný aj podľa roka 25/26 → odložený rok nie je
úplne čistý.

**3. Čo treba dorobiť.** (a) Short strana alebo filter smeru (denný trend) — aby stratégia prežila klesajúce zlato; dnes
v medvedom trhu jednoducho nebude obchodovať tak dobre. (b) Vynechať dni rolovania MGC (aktívne mesiace feb / apr / jún / aug / dec)
a okolie správ 8:30 / 14:00 ET — overiť, či tam nestráca. (c) Najhoršia skupina sú obchody „s trendom“ s `requireBreak` —
skúsiť bez požiadavky zlomu štruktúry.

**4. Čo otestovať ďalej.** Krok 9: forward test 4–8 týždňov na MGC (NinjaTrader / MT5 s XAU). Kontrolne beh na klesajúcom
období zlata (2022: −20 %) s tou istou logikou aj pre short (`tradeDirection=Both`), aby bolo vidno, čo sa stane, keď zlato
otočí. Stres: dvojnásobný poplatok a 1 tick sklzu.

**5. Je to použiteľné?** Áno — ako prvá stratégia na zlato v portfóliu, na menšom riziku, kým forward test nepotvrdí čísla.
Nie ako „istota“: je to long-only stratégia na trhu, ktorý päť rokov rástol.

**6. Čo by som pridal.** Filter dennej EMA (long len nad ňou, short len pod ňou) a k tomu short stranu — aby stratégia
nezávisela od jedného smeru zlata; prípadne obmedziť obchody na COMEX 8–11 ET a Áziu 20–22 h, kde je podľa prieskumu najviac pohybu.

<!-- POSUDOK KONIEC -->
