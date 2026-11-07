# Základná analytika — VA NÁVRAT 1.0 (C# jadro) (`va80net`)

Zmerané 2026-11-07 na `MNQ/USD` 1m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `mnq_databento_1m`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy va80net \
   --profile mnq_databento_1m \
   --pair MNQ/USD \
   --timeframe 1m \
   --fee 1.755e-05
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 213 obchodov spolu — na štatistiku dosť
- break-even 0.0403 % je nad poplatkom 0.0018 % (rezerva +0.0385 bodu)
- edge nad poplatkom v 99 % bootstrapových vzoriek
- drawdown drží: 95. percentil 21.6 %
- odlíšiteľná od náhody (+3.2 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-08 na 32. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina '15 h' vlastnosti 'Hodina vstupu (UTC)': 87 obchodov (40.8 %), bez nej by break-even bol o +0.0236 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 44 | +9.30 | 0.0394 | 7.3 | 68.2 | +7/-4 | `20261107-160614-a58b8d` |
| 20221001-20231001 | 55 | +10.91 | 0.0394 | 7.7 | 80.0 | +12/-2 | `20261107-160629-a9aff5` |
| 20231001-20241001 | 39 | +2.64 | 0.0111 | 5.4 | 71.8 | +8/-3 | `20261107-160644-2699fd` |
| 20240904-20250904 | 38 | +30.32 | 0.0960 | 2.9 | 84.2 | +9/-1 | `20261107-160659-a5ea31` |
| 20250904-20260904 | 42 | +8.52 | 0.0206 | 15.8 | 78.6 | +11/-3 | `20261107-160714-307847` |

Zisková v **5 z 5** okien, obchodov spolu 213, break-even celkom 0.0403 %. Okná sa prekrývajú, 5 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+0.37 ATR za 5 barov)
- medián držania 23 barov grafu
- winrate 76.53 %, payoff 0.495
- 0.12 obchodov za deň
- šikmosť výnosov +1.463

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 69.5 %, `session_end` 19.2 %, `stop_loss` 11.3 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je '15 h' vlastnosti 'Hodina vstupu (UTC)': 87 obchodov (40.8 %), break-even 0.0029 % oproti 0.0403 % celku. Bez nej by break-even bol 0.0639 % (+0.0236). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 15 h | 87 | 40.8 % | 70.1 | 0.0029 | 0.0639 | +0.0236 |
| 16 h | 31 | 14.6 % | 83.9 | 0.0564 | 0.0376 | -0.0027 |
| 14 h | 90 | 42.3 % | 82.2 | 0.0669 | 0.0189 | -0.0214 |

**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.7679 % – 1.2166 % | 53 | 24.9 % | 67.9 | -0.0145 | 0.0577 | +0.0174 |
| 0.49 % – 0.7679 % | 53 | 24.9 % | 75.5 | 0.0016 | 0.0538 | +0.0135 |
| do 0.49 % | 54 | 25.4 % | 88.9 | 0.0638 | 0.0313 | -0.0090 |
| nad 1.2166 % | 53 | 24.9 % | 73.6 | 0.1158 | 0.0186 | -0.0217 |

**Deň v mesiaci**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 8 | 56 | 26.3 % | 66.1 | -0.0027 | 0.0545 | +0.0142 |
| 8 – 14 | 54 | 25.4 % | 70.4 | 0.0209 | 0.0471 | +0.0068 |
| 14 – 23 | 53 | 24.9 % | 81.1 | 0.0600 | 0.0336 | -0.0067 |
| nad 23 | 50 | 23.5 % | 90.0 | 0.0855 | 0.0262 | -0.0141 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0403 % | -0.0010 % ± 0.0128 | +3.22 | 99.9 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0403 % | -0.0003 % ± 0.0152 | +2.68 | 99.6 |

Edge je odlisitelny od nahody (3.2 sigma, percentil 99.9).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 54 | 3.7 | 68.5 | 0.0319 | 45 |
| 2022-12 - 2024-03 | 60 | 4.1 | 78.3 | 0.0257 | 34 |
| 2024-03 - 2025-06 | 46 | 3.1 | 80.4 | 0.0879 | 91 |
| 2025-06 - 2026-08 | 53 | 3.6 | 79.2 | 0.0225 | 32 |

Hranice pre úsek veľkosti posledného obdobia: -0.0176 až +0.1027 % (medián 0.0377).

**DRZI** — posledné obdobie (2025-06 - 2026-08) je na 32. percentile, teda v medziach -0.0176 až +0.1027 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 14** — 2025-08-25T14:30 až 2025-11-20T16:54, spolu +1460.77.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-08-25T14:30 | 2025-08-25T14:49 | +58.35 | +0.12 | `take_profit` |
| 2 | 2025-08-26T14:30 | 2025-08-26T14:31 | +6.85 | +0.01 | `take_profit` |
| 3 | 2025-08-28T14:00 | 2025-08-28T14:00 | +29.34 | +0.06 | `take_profit` |
| 4 | 2025-09-05T15:00 | 2025-09-05T15:01 | +23.35 | +0.05 | `take_profit` |
| 5 | 2025-09-11T14:30 | 2025-09-11T14:30 | +0.32 | +0.00 | `take_profit` |
| 6 | 2025-09-30T15:00 | 2025-09-30T15:00 | +13.26 | +0.03 | `take_profit` |
| 7 | 2025-10-06T14:30 | 2025-10-06T14:36 | +34.74 | +0.07 | `take_profit` |
| 8 | 2025-10-07T14:30 | 2025-10-07T15:03 | +100.23 | +0.20 | `take_profit` |
| 9 | 2025-10-09T14:00 | 2025-10-09T14:39 | +132.23 | +0.26 | `take_profit` |
| 10 | 2025-10-14T16:00 | 2025-10-14T16:37 | +188.76 | +0.38 | `take_profit` |
| 11 | 2025-11-03T15:00 | 2025-11-03T15:06 | +95.17 | +0.18 | `take_profit` |
| 12 | 2025-11-12T15:00 | 2025-11-12T16:10 | +161.21 | +0.31 | `take_profit` |
| 13 | 2025-11-14T16:00 | 2025-11-14T16:24 | +151.73 | +0.30 | `take_profit` |
| 14 | 2025-11-20T16:30 | 2025-11-20T16:54 | +465.26 | +0.93 | `take_profit` |

**Straty za sebou: 4** — 2022-06-29T14:00 až 2022-08-05T15:27, spolu -645.41.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-06-29T14:00 | 2022-06-29T19:54 | -30.82 | -0.13 | `session_end` |
| 2 | 2022-07-06T15:30 | 2022-07-06T18:40 | -258.33 | -1.10 | `stop_loss` |
| 3 | 2022-07-13T15:00 | 2022-07-13T19:54 | -18.33 | -0.08 | `session_end` |
| 4 | 2022-08-05T14:30 | 2022-08-05T15:27 | -337.93 | -1.27 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0403 %**, medián 0.0397 %, 90 % interval 0.0112–0.0708 %
- P(edge > poplatok) = **98.7 %**
- max drawdown: medián 10.5 %, 95. percentil 21.6 %, najhorší 70.1 %
- najdlhšia séria strát: medián 4, 95. percentil 5 obchodov
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
<!-- POSUDOK cisla=567efff3 -->

**Posudok (7. 11. 2026, VA NÁVRAT 1.0 — pravidlo 80 %, C# jadro, predvolené nastavenie, MNQ 1m, 1 kontrakt.)**

1. **Na čo sa hodí a na čo nie.** Nasdaq futures (MNQ / NQ) v RTH, len dni, keď trh otvorí mimo včerajšej value area a vráti sa do nej; intraday, výstup 15:55. Prieskum: na ES a MGC nefunguje — nie je to všeobecný jav, ale vlastnosť Nasdaqu. Beží na 1m grafe (value area z 1m sviečok; z 5m je hrubá a edge mizne).
2. **Má potenciál?** Áno: zisková v 5 z 5 okien, +3,2 sigma proti náhodnému vstupu, break-even 0,040 % (22× poplatok), edge nad poplatkom v 99 % bootstrapových vzoriek, prepad drží. Robustné voči výpočtu VA (koš 0,03–0,1 %, 65–75 %, rank aj expand: PF 1,29–1,81 na ladení). Iný zdroj dát (NAS100) potvrdil (PF 1,4–1,6, 4 z 5 rokov).
3. **Čo dorobiť.** Edge stojí na obchodoch s malým plánovaným RR (cieľ POC býva bližšie ako pol stopu, WR ~76 %) — s podmienkou RR ≥ 0,5 ostáva ~16 obchodov za rok a odložený rok je stratový. Vstupy po 15 h UTC (popoludní NY) sú najslabšie — kandidát na skorší posledný vstup.
4. **Čo otestovať ďalej.** Smernica (`va80` v glsearch: VA, cieľ, stop, posledný vstup, typ vstupu), krok 9 (2× poplatok, oneskorený vstup — pri malom RR rozhodujúci), forward test na deme.
5. **Použiteľné?** Áno ako rangeová stratégia pre Nasdaq s ~40–50 obchodmi za rok (pod hranicou 150 — potrebuje výnimku ako SPRÁVY); C# jadro (`va80net`) sedí s Pythonom bar po bare.
6. **Čo by som pridal.** Filter dňa podľa veľkosti otvorenia mimo VA (`minOpenOutside`) a cieľ POC / opačný okraj podľa toho, ako ďaleko je POC — vyšší RR bez straty WR.

<!-- POSUDOK KONIEC -->
