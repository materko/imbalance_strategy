# Základná analytika — NOA 1.0 (C# jadro EOD) (`noaneteod`)

Zmerané 2026-10-26 na `MNQ/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tester/profiles/SMERNICE_CS_EOD_NOA_1.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy noaneteod \
   --profile tester/profiles/SMERNICE_CS_EOD_NOA_1.json \
   --pair MNQ/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 778 obchodov spolu — na štatistiku dosť
- break-even 0.0396 % je nad poplatkom 0.0018 % (rezerva +0.0378 bodu)
- edge nad poplatkom v 100 % bootstrapových vzoriek
- drawdown drží: 95. percentil 3.4 %
- odlíšiteľná od náhody (+5.0 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 16. percentile toho, čo stratégia vyrobí sama od seba)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- 81.9 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 's trendom' vlastnosti 'S trendom, alebo proti': 767 obchodov (98.6 %), bez nej by break-even bol o +0.1274 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 174 | +8.22 | 0.0533 | 1.0 | 42.0 | +5/-6 | `20261026-125654-e6320e` |
| 20221001-20231001 | 175 | +4.36 | 0.0303 | 0.8 | 43.4 | +5/-6 | `20261026-125700-c79846` |
| 20231001-20241001 | 131 | +5.93 | 0.0399 | 1.3 | 36.6 | +3/-11 | `20261026-125706-311e12` |
| 20240904-20250904 | 144 | +11.66 | 0.0590 | 1.6 | 41.7 | +5/-6 | `20261026-125712-e926f8` |
| 20250904-20260904 | 158 | +6.79 | 0.0261 | 1.8 | 39.2 | +4/-8 | `20261026-125718-7f8e1c` |

Zisková v **5 z 5** okien, obchodov spolu 778, break-even celkom 0.0396 %. Okná sa prekrývajú, 4 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+1.00 ATR za 5 barov)
- medián držania 4.4 barov grafu
- winrate 40.75 %, payoff 2.598
- 0.43 obchodov za deň
- šikmosť výnosov +9.246

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `session_end` 81.9 %, `stop_loss` 18.1 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 's trendom' vlastnosti 'S trendom, alebo proti': 767 obchodov (98.6 %), break-even 0.0376 % oproti 0.0396 % celku. Bez nej by break-even bol 0.167 % (+0.1274). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 767 | 98.6 % | 40.7 | 0.0376 | 0.1670 | +0.1274 |
| proti trendu | 11 | 1.4 % | 45.5 | 0.1670 | 0.0376 | -0.0020 |

**Makro udalosť v ten deň**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| žiadna | 678 | 87.1 % | 39.8 | 0.0329 | 0.0866 | +0.0470 |
| FOMC | 18 | 2.3 % | 44.4 | 0.0471 | 0.0395 | -0.0001 |
| CPI | 34 | 4.4 % | 47.1 | 0.0546 | 0.0390 | -0.0006 |
| NFP | 47 | 6.0 % | 48.9 | 0.1252 | 0.0340 | -0.0056 |

**Pred vyhlásením, alebo po ňom**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| pred vyhlásením | 16 | 2.1 % | 37.5 | -0.0011 | 0.0404 | +0.0008 |
| bez udalosti | 678 | 87.1 % | 39.8 | 0.0329 | 0.0866 | +0.0470 |
| po vyhlásení | 84 | 10.8 % | 48.8 | 0.1024 | 0.0322 | -0.0074 |

Parametre, ktorými sa dá s tým niečo spraviť: `hardStopPct`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0396 % | 0.0014 % ± 0.0077 | +4.96 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0396 % | 0.0036 % ± 0.0089 | +4.06 | 100.0 |

Edge je odlisitelny od nahody (5.0 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 218 | 14.8 | 42.2 | 0.0547 | 77 |
| 2022-12 - 2024-03 | 201 | 13.6 | 38.8 | 0.0163 | 14 |
| 2024-03 - 2025-06 | 165 | 11.2 | 44.2 | 0.0782 | 93 |
| 2025-06 - 2026-09 | 194 | 13.2 | 38.1 | 0.0192 | 16 |

Hranice pre úsek veľkosti posledného obdobia: +0.0092 až +0.0807 % (medián 0.0359).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 16. percentile, teda v medziach +0.0092 až +0.0807 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 5** — 2022-09-02T17:31 až 2022-09-07T19:50, spolu +191.74, rovnako dlhých sérií 3.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-09-02T17:31 | 2022-09-02T18:25 | +4.15 | +0.02 | `session_end` |
| 2 | 2022-09-02T19:00 | 2022-09-02T19:50 | +20.15 | +0.08 | `session_end` |
| 3 | 2022-09-06T17:19 | 2022-09-06T17:20 | +8.66 | +0.04 | `session_end` |
| 4 | 2022-09-07T16:57 | 2022-09-07T16:55 | +27.65 | +0.11 | `session_end` |
| 5 | 2022-09-07T18:17 | 2022-09-07T19:50 | +131.14 | +0.54 | `session_end` |

**Straty za sebou: 11** — 2023-10-10T15:25 až 2023-11-07T19:40, spolu -650.06.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-10-10T15:25 | 2023-10-10T17:12 | -163.07 | -0.53 | `stop_loss` |
| 2 | 2023-10-13T15:32 | 2023-10-13T16:30 | -52.07 | -0.17 | `session_end` |
| 3 | 2023-10-13T17:55 | 2023-10-13T18:05 | -16.56 | -0.05 | `stop_loss` |
| 4 | 2023-10-16T15:36 | 2023-10-16T15:35 | -36.07 | -0.12 | `session_end` |
| 5 | 2023-10-20T15:47 | 2023-10-20T16:30 | -71.53 | -0.24 | `session_end` |
| 6 | 2023-10-23T13:45 | 2023-10-23T13:48 | -84.52 | -0.29 | `stop_loss` |
| 7 | 2023-10-23T17:04 | 2023-10-23T17:19 | -64.04 | -0.22 | `stop_loss` |
| 8 | 2023-10-31T13:45 | 2023-10-31T14:05 | -51.51 | -0.18 | `session_end` |
| 9 | 2023-11-01T15:10 | 2023-11-01T15:10 | -46.53 | -0.16 | `session_end` |
| 10 | 2023-11-07T15:57 | 2023-11-07T17:05 | -41.58 | -0.14 | `session_end` |
| 11 | 2023-11-07T19:40 | 2023-11-07T19:40 | -22.58 | -0.07 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0396 %**, medián 0.0387 %, 90 % interval 0.0231–0.0598 %
- P(edge > poplatok) = **100.0 %**
- max drawdown: medián 2.0 %, 95. percentil 3.4 %, najhorší 7.4 %
- najdlhšia séria strát: medián 10, 95. percentil 14 obchodov
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
<!-- POSUDOK cisla=09c92a13 -->

_Posudok (Claude, 26. 10. 2026) — nastavenie „NOA 1 C# EOD“ (`SMERNICE_CS_EOD_NOA_1`, parametre ako NOA 1), kópia
`noanet` so zatvorením o 15:59 NY pre prop účty (`EodCloseEngine`)._

1. **Na čo sa to hodí a na čo nie.** To isté čo `noanet` — MNQ / NQ 5m, newyorská seansa — ale pre účty, ktoré
   vyžadujú byť flat pred koncom dňa (prop výzvy). Zatvorenie o 15:59 tu skoro nič nemení: NOA aj tak zatvára
   o 16:00, takže sa líšia len posledné minúty — 778 obchodov a break-even 0,0396 % ako `noanet`, PnL po oknách sa
   pohne o ±0,8 bodu (+8,22 vs +7,43 %, +11,66 vs +12,26 %). Na 60 000 $ je 95. percentil drawdownu 3,4 % (~2 040 $):
   pri 50k prop účte s trailing drawdownom ~2 000–2 500 $ je to na hrane — riziko na obchod treba nastaviť podľa
   limitu výzvy, nie podľa tohto čísla.
2. **Má to potenciál?** Áno, rovnako ako `noanet`: 5 z 5 okien, +5,0 sigma (+4,1 proti vstupom v tých istých
   hodinách), break-even 22× nad poplatkom, 100 % bootstrapu nad poplatkom, posledné obdobie na 16. percentile (DRZI).
   Proti: výber z veľkého prehľadávania a slabší posledný rok (0,0261 %).
3. **Čo treba dorobiť.** Hodinové zatvorenie od 15:58:30 NY (`IClockFlatten`) beží aj bez nového baru — overiť
   naživo, že pri výpadku feedu pozícia nezostane cez noc; skrátené seansy (13:00) potrebujú vlastný čas zatvorenia,
   15:59 ich nepokryje. Výstupy (81,9 % `session_end`) a skupina „s trendom“ ako pri `noanet`.
4. **Čo otestovať ďalej.** `cli prop` (alebo karta Prop) s pravidlami konkrétnej výzvy na behoch z tohto dokumentu —
   rozhodne, či 95. percentil drawdownu a séria 14 strát prejdú denným aj celkovým limitom. Potom deň–týždeň na
   Sim101 s porovnaním `python -m tester.ninjatrader compare --strategy noaneteod --profile tester/profiles/SMERNICE_CS_EOD_NOA_1.json
   --timeframe 5m`.
5. **Je to použiteľné?** Áno — na prop účty je to správna verzia NOA, edge sa zatvorením o 15:59 nestráca.
   Ostro až po forward teste a overení limitov výzvy.
6. **Čo by som pridal.** Denný stop podľa pravidiel výzvy priamo v jadre (po strate X $ za deň už nevstupovať) —
   séria 11 strát v októbri 2023 prišla počas niekoľkých dní a prop účet padá na dennom limite skôr než na celkovom.

<!-- POSUDOK KONIEC -->
