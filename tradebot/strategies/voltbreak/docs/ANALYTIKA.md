# Základná analytika — Volt Break (`voltbreak`)

Zmerané 2026-10-11 na `MNQ/USD` 1h, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `.nightsearch/checkup/voltbreak_PRESIEL_SMERNICAMI_Volt_Break_1_2026-10-11.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy voltbreak \
   --profile .nightsearch/checkup/voltbreak_PRESIEL_SMERNICAMI_Volt_Break_1_2026-10-11.json \
   --pair MNQ/USD \
   --timeframe 1h \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 812 obchodov spolu — na štatistiku dosť
- break-even 0.0290 % je nad poplatkom 0.0018 % (rezerva +0.0272 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 2.9 %
- odlíšiteľná od náhody (+4.8 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 27. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'žiadna' vlastnosti 'Makro udalosť v ten deň': 689 obchodov (84.9 %), bez nej by break-even bol o +0.0106 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 160 | +5.67 | 0.0395 | 1.9 | 55.6 | +7/-7 | `20261011-072029-89a70d` |
| 20221001-20231001 | 151 | +5.41 | 0.0421 | 1.2 | 55.6 | +6/-7 | `20261011-072032-badd1d` |
| 20231001-20241001 | 162 | +5.35 | 0.0294 | 1.6 | 54.3 | +8/-7 | `20261011-072035-af4063` |
| 20240904-20250904 | 150 | +5.04 | 0.0258 | 1.1 | 54.0 | +8/-4 | `20261011-072039-4ab9f5` |
| 20250904-20260904 | 189 | +6.41 | 0.0208 | 1.5 | 54.0 | +6/-5 | `20261011-072042-37538c` |

Zisková v **5 z 5** okien, obchodov spolu 812, break-even celkom 0.0290 %.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.73 ATR za 5 barov)
- medián držania 1.1 barov grafu
- winrate 54.68 %, payoff 1.2
- 0.45 obchodov za deň
- šikmosť výnosov +0.016

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 54.7 %, `stop_loss` 45.3 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'žiadna' vlastnosti 'Makro udalosť v ten deň': 689 obchodov (84.9 %), break-even 0.0271 % oproti 0.029 % celku. Bez nej by break-even bol 0.0396 % (+0.0106). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| žiadna | 689 | 84.9 % | 54.3 | 0.0271 | 0.0396 | +0.0106 |
| NFP | 41 | 5.0 % | 53.7 | 0.0321 | 0.0288 | -0.0002 |
| FOMC | 28 | 3.4 % | 57.1 | 0.0396 | 0.0286 | -0.0004 |
| CPI | 52 | 6.4 % | 59.6 | 0.0466 | 0.0278 | -0.0012 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| pred vyhlásením | 11 | 1.4 % | 45.5 | 0.0001 | 0.0293 | +0.0003 |
| bez udalosti | 689 | 84.9 % | 54.3 | 0.0271 | 0.0396 | +0.0106 |
| po vyhlásení | 112 | 13.8 % | 58.0 | 0.0431 | 0.0268 | -0.0022 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.7034 | 204 | 25.1 % | 45.1 | -0.0013 | 0.0392 | +0.0102 |
| 0.8992 – 0.97 | 203 | 25.0 % | 57.1 | 0.0354 | 0.0268 | -0.0022 |
| nad 0.97 | 202 | 24.9 % | 55.9 | 0.0382 | 0.0259 | -0.0031 |
| 0.7034 – 0.8992 | 203 | 25.0 % | 60.6 | 0.0441 | 0.0239 | -0.0051 |

Parametre, ktorými sa dá s tým niečo spraviť: `endHHMM`, `slUsd`, `startHHMM`, `tpUsd`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0290 % | 0.0019 % ± 0.0057 | +4.79 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0290 % | 0.0021 % ± 0.0056 | +4.79 | 100.0 |

Edge je odlisitelny od nahody (4.8 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 195 | 13.2 | 53.9 | 0.0336 | 68 |
| 2022-12 - 2024-03 | 196 | 13.3 | 54.6 | 0.0358 | 70 |
| 2024-03 - 2025-06 | 205 | 13.9 | 55.1 | 0.0293 | 50 |
| 2025-06 - 2026-09 | 216 | 14.6 | 55.1 | 0.0231 | 27 |

Hranice pre úsek veľkosti posledného obdobia: +0.0121 až +0.0464 % (medián 0.0292).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 27. percentile, teda v medziach +0.0121 až +0.0464 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 10** — 2024-09-11T17:00 až 2024-09-19T16:26, spolu +1184.33.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-09-11T17:00 | 2024-09-11T17:07 | +118.67 | +0.31 | `take_profit` |
| 2 | 2024-09-11T17:00 | 2024-09-11T17:07 | +118.67 | +0.31 | `take_profit` |
| 3 | 2024-09-11T18:00 | 2024-09-11T18:27 | +118.66 | +0.31 | `take_profit` |
| 4 | 2024-09-11T18:00 | 2024-09-11T18:27 | +118.66 | +0.31 | `take_profit` |
| 5 | 2024-09-11T19:00 | 2024-09-11T19:23 | +118.16 | +0.31 | `take_profit` |
| 6 | 2024-09-11T19:00 | 2024-09-11T19:23 | +118.16 | +0.31 | `take_profit` |
| 7 | 2024-09-19T15:00 | 2024-09-19T15:16 | +119.09 | +0.30 | `take_profit` |
| 8 | 2024-09-19T15:00 | 2024-09-19T15:16 | +119.09 | +0.30 | `take_profit` |
| 9 | 2024-09-19T16:00 | 2024-09-19T16:26 | +117.59 | +0.29 | `take_profit` |
| 10 | 2024-09-19T16:00 | 2024-09-19T16:26 | +117.59 | +0.29 | `take_profit` |

**Straty za sebou: 7** — 2022-01-27T16:00 až 2022-02-08T18:17, spolu -705.14, rovnako dlhých sérií 5.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-01-27T16:00 | 2022-01-27T16:26 | -100.50 | -0.35 | `stop_loss` |
| 2 | 2022-01-27T17:00 | 2022-01-27T17:07 | -100.00 | -0.35 | `stop_loss` |
| 3 | 2022-01-28T17:00 | 2022-01-28T17:22 | -102.00 | -0.36 | `stop_loss` |
| 4 | 2022-01-31T16:00 | 2022-01-31T16:11 | -100.53 | -0.34 | `stop_loss` |
| 5 | 2022-01-31T17:00 | 2022-01-31T17:24 | -100.54 | -0.34 | `stop_loss` |
| 6 | 2022-01-31T18:00 | 2022-01-31T20:17 | -100.04 | -0.34 | `stop_loss` |
| 7 | 2022-02-08T18:00 | 2022-02-08T18:17 | -101.53 | -0.34 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0290 %**, medián 0.0287 %, 90 % interval 0.0206–0.0375 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 1.8 %, 95. percentil 2.9 %, najhorší 5.5 %
- najdlhšia séria strát: medián 8, 95. percentil 10 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **2 110** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=4cfba1fd -->
**Posudok (AI, 11. 10. 2026)** — profil PREŠIEL SMERNICAMI č. 1 z testovania podľa smernice (krok 7).

1. **Na čo sa to hodí a na čo nie.** MNQ 1h, prieraz noise barrier + VWAP (Matteo Conti), len long, drží ~1 bar. WR 55 %, payoff 1,2, veľmi stabilné roky (+5,0 až +6,4 %).
2. **Má to potenciál?** Áno: najstabilnejšie roky zo všetkých, +4,8 σ, break-even 0,029 % (~16× poplatok), drawdown nízky (MC 95 %: 2,9 %). Pozor: posledné obdobie na 27. percentile a break-even po rokoch klesá (0,040 → 0,021) — sleduj, či edge neslabne.
3. **Čo dorobiť.** Len long — na medvedom trhu (2022) držala, ale treba overiť short variantu ako zvlášť test. Makro dni (CPI, FOMC) sú lepšie než bežné — bez filtra dobre. Analytika ráta obchody z prekrývajúcich sa okien 23/24 a 24/25 (september 2024) dvakrát — najdlhšia séria strát môže byť o 1–2 nadsadená.
4. **Čo otestovať ďalej.** NAS100 z Dukascopy (krok 8) — rovnaký smer výsledku = jav trhu, nie dát; 2× poplatok (`--fee 3.51e-05`) a 1 tick sklzu navyše; parita s TradingView na 1–2 mesiacoch (krok 9); forward test 4–8 týždňov na 1 MNQ (krok 10).
5. **Je to použiteľné?** Áno — vďaka stabilite a nízkemu DD najvhodnejšia pre prop účty (FTMO/Tradeify). Krok 8 a 10.
6. **Čo by som pridal.** Short zrkadlo (noise barrier dole) ako samostatný test a filter režimu: v rokoch s klesajúcim break-even sledovať veľkosť noise pásma.
<!-- POSUDOK KONIEC -->
