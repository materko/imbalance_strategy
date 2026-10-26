# Základná analytika — Fibo 1.0 MGC (C# jadro) (`fibomgcnet`)

Zmerané 2026-10-26 na `MGC/USD` 3m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/fibomgcnet/configs/PRESIEL_SMERNICAMI_Fibo_1_0_MGC_1.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy fibomgcnet \
   --profile tradebot/strategies/fibomgcnet/configs/PRESIEL_SMERNICAMI_Fibo_1_0_MGC_1.json \
   --pair MGC/USD \
   --timeframe 3m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 824 obchodov spolu — na štatistiku dosť
- break-even 0.0207 % je nad poplatkom 0.0018 % (rezerva +0.0189 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 11.2 %
- odlíšiteľná od náhody (+3.8 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 70. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- charakter: formácia / štruktúra (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'do 0.75 R' vlastnosti 'Plánovaný RR': 690 obchodov (83.7 %), bez nej by break-even bol o +0.0136 lepší (riadi `rrRatio`)

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 169 | +10.72 | 0.0132 | 6.8 | 61.5 | +10/-4 | `20261026-083404-ac1bb3` |
| 20221001-20231001 | 167 | +13.62 | 0.0148 | 6.4 | 62.3 | +12/-5 | `20261026-083410-129b08` |
| 20231001-20241001 | 180 | +28.21 | 0.0284 | 3.5 | 66.7 | +11/-6 | `20261026-083416-b4d0f1` |
| 20240904-20250904 | 167 | +19.32 | 0.0230 | 5.8 | 64.1 | +7/-4 | `20261026-083422-b832e9` |
| 20250904-20260904 | 155 | +10.78 | 0.0235 | 5.7 | 62.6 | +6/-5 | `20261026-083428-b0b51b` |

Zisková v **5 z 5** okien, obchodov spolu 824, break-even celkom 0.0207 %. Okná sa prekrývajú, 14 obchodov započítaných dvakrát vypadlo.

## Charakter

**Formácia / štruktúra** (istota priemerná)

- vstup bez jasného smeru pohybu (+0.08 ATR za 5 barov)
- medián držania 51.5 barov grafu
- winrate 63.59 %, payoff 0.786
- 0.46 obchodov za deň
- šikmosť výnosov -0.127

- **Čo je normálne:** Zmes: časť obchodov sa chová ako prerazenie, časť ako návrat. Priemer preto o jednotlivom obchode nehovorí veľa.
- **Na čo pozor:** Práve pri tomto type sa najviac oplatí rozdeliť obchody na skupiny (`tester.analytics`) — priemer skrýva dve rôzne populácie.
- **Čo ladiť:** Podmienky vstupu (ktoré modely/formácie zapnuté) a potom až výstup.

Výstupy: `take_profit` 63.6 %, `stop_loss` 36.4 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'do 0.75 R' vlastnosti 'Plánovaný RR': 690 obchodov (83.7 %), break-even 0.017 % oproti 0.0207 % celku. Bez nej by break-even bol 0.0343 % (+0.0136). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: skus preladit `rrRatio`.


**Plánovaný RR** (riadi `rrRatio`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.75 R | 690 | 83.7 % | 62.8 | 0.0170 | 0.0343 | +0.0136 |
| nad 0.75 R | 134 | 16.3 % | 67.9 | 0.0343 | 0.0170 | -0.0037 |

**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.0634 | 207 | 25.1 % | 58.0 | 0.0049 | 0.0269 | +0.0062 |
| 0.1235 – 0.1806 | 206 | 25.0 % | 64.6 | 0.0232 | 0.0199 | -0.0008 |
| nad 0.1806 | 205 | 24.9 % | 64.9 | 0.0267 | 0.0191 | -0.0016 |
| 0.0634 – 0.1235 | 206 | 25.0 % | 67.0 | 0.0302 | 0.0172 | -0.0035 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 8 – 15 | 186 | 22.6 % | 59.7 | 0.0058 | 0.0250 | +0.0043 |
| do 8 | 227 | 27.5 % | 65.6 | 0.0197 | 0.0211 | +0.0004 |
| 15 – 23 | 209 | 25.4 % | 65.5 | 0.0207 | 0.0207 | +0.0000 |
| nad 23 | 202 | 24.5 % | 62.9 | 0.0352 | 0.0159 | -0.0048 |

Parametre, ktorými sa dá s tým niečo spraviť: `maxHoldBars`, `requireBreak`, `rrRatio`, `slBufferAtr`, `tradeStartH`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0287 % | 0.0026 % ± 0.0069 | +3.76 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0287 % | 0.0032 % ± 0.0066 | +3.83 | 100.0 |

Edge je odlisitelny od nahody (3.8 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 215 | 14.6 | 60.9 | 0.0110 | 14 |
| 2022-12 - 2024-03 | 195 | 13.2 | 65.1 | 0.0207 | 49 |
| 2024-03 - 2025-06 | 222 | 15.1 | 64.0 | 0.0276 | 78 |
| 2025-06 - 2026-09 | 192 | 13.0 | 64.6 | 0.0255 | 70 |

Hranice pre úsek veľkosti posledného obdobia: +0.0057 až +0.0379 % (medián 0.0199).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 70. percentile, teda v medziach +0.0057 až +0.0379 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 12** — 2023-03-15T23:00 až 2023-04-11T00:14, spolu +4082.78.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-03-15T23:00 | 2023-03-15T23:52 | +362.51 | +0.11 | `take_profit` |
| 2 | 2023-03-17T19:36 | 2023-03-20T07:06 | +346.60 | +0.87 | `take_profit` |
| 3 | 2023-03-20T17:06 | 2023-03-20T18:17 | +355.82 | +0.30 | `take_profit` |
| 4 | 2023-03-21T23:09 | 2023-03-22T00:05 | +345.38 | +0.10 | `take_profit` |
| 5 | 2023-03-22T16:15 | 2023-03-22T18:00 | +351.57 | +0.36 | `take_profit` |
| 6 | 2023-03-23T15:16 | 2023-03-23T16:33 | +348.90 | +0.59 | `take_profit` |
| 7 | 2023-03-24T11:03 | 2023-03-24T12:33 | +276.89 | +0.46 | `take_profit` |
| 8 | 2023-03-28T14:12 | 2023-03-28T14:58 | +365.24 | +0.47 | `take_profit` |
| 9 | 2023-03-28T16:24 | 2023-03-28T17:50 | +331.54 | +0.34 | `take_profit` |
| 10 | 2023-03-30T08:00 | 2023-03-30T12:26 | +316.51 | +0.32 | `take_profit` |
| 11 | 2023-04-04T17:07 | 2023-04-05T06:22 | +326.55 | +0.18 | `take_profit` |
| 12 | 2023-04-10T20:27 | 2023-04-11T00:14 | +355.25 | +0.16 | `take_profit` |

**Straty za sebou: 6** — 2024-04-09T10:33 až 2024-04-24T09:19, spolu -2427.26.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-04-09T10:33 | 2024-04-09T15:07 | -404.50 | -0.57 | `stop_loss` |
| 2 | 2024-04-10T07:03 | 2024-04-10T12:30 | -365.49 | -0.51 | `stop_loss` |
| 3 | 2024-04-10T18:10 | 2024-04-11T08:50 | -371.47 | -0.53 | `stop_loss` |
| 4 | 2024-04-15T12:24 | 2024-04-15T13:41 | -459.15 | -0.39 | `stop_loss` |
| 5 | 2024-04-17T10:21 | 2024-04-17T16:32 | -427.37 | -0.44 | `stop_loss` |
| 6 | 2024-04-23T19:25 | 2024-04-24T09:19 | -399.28 | -0.43 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0207 %**, medián 0.0207 %, 90 % interval 0.0129–0.0290 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 6.4 %, 95. percentil 11.2 %, najhorší 22.2 %
- najdlhšia séria strát: medián 6, 95. percentil 8 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **1 508** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=96793b40 -->

**C# jadro, riziko 500 $.** Logika je bar po bare zhodná s Python predlohou `fibomgc` na všetkých desiatich profiloch zo smernice (`tester/tests/test_csharp_parity_mgc.py`); čísla sa od staršej analytiky predlohy líšia, lebo profil č. 1 je z posledného kola smernice a veľkosť pozície je z rizika 500 $ (MGC 10 $ za bod — strop straty takmer nič nevynechá).

**1. Na čo sa to hodí a na čo nie.** Na zlato — MGC (aj GC s menším počtom), 3m graf, swingy na 6m, len tam, kde je skutočný futures objem a fill. Charakter „formácia / štruktúra“: obchod na návrat k Fibonacciho zóne po impulze, WR 62–67 %, cieľ okolo 0,75 R. Pri riziku 500 $ na účet 60 000 $ je DD v 95 % ciest 11 % — vhodné aj na prop. Na CFD XAU prešla aj krokom 8.

**2. Má to potenciál?** Áno: zisk v **5 z 5** okien (+10,7 až +28,2 % ročne), break-even 0,0207 % je ~11× poplatok, edge nad poplatkom v 100 % bootstrapových vzoriek, posledné obdobie na 70. percentile. Slabšie je +3,8 sigma proti náhode — časť výsledku dáva samotný pohyb zlata, nie len výber vstupu.

**3. Čo treba dorobiť.** Obchody s plánovaným RR do 0,75 sú 84 % a zhoršujú break-even (bez nich +0,0136) — `rrRatio` a cieľ (extenzia vs RR) stojí za preverenie. Stop je za začiatok nohy — pri veľkej nohe dlhý; strop `skipOverRisk` je zapnutý len cez obal (predvolene vypnutý).

**4. Čo otestovať ďalej.** Natívny hyperopt (`cli hyperopt --strategy fibomgcnet --engine multicharts --windows ref --aggregate min --select plateau`) na `rrRatio`, `tpExtensionPct`, `levelTolAtr`; `--walk-forward`. Potom forward test na MGC 4–6 týždňov (WR a sklz proti backtestu).

**5. Je to použiteľné, alebo je to o ničom?** **Použiteľné** — prešlo smernicou celou (kroky 1–8), je v C# a pripravené na NinjaTrader / MT5.

**6. Čo by som pridal.** Filter podľa sily dolára (DXY) alebo podľa trendu zlata na 1h — Fibo návrat v smere vyššieho trendu býva spoľahlivejší než proti nemu.

<!-- POSUDOK KONIEC -->
