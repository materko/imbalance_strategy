# Základná analytika — SIGMA BREAKOUT 1.0 (`sigma`)

Zmerané 2026-10-31 na `MNQ/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `/Users/martin/IBS/.nightsearch/base_sigma.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy sigma \
   --profile /Users/martin/IBS/.nightsearch/base_sigma.json \
   --pair MNQ/USD \
   --timeframe 5m \
   --fee 1.755e-05
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 1686 obchodov spolu — na štatistiku dosť
- break-even 0.0244 % je nad poplatkom 0.0018 % (rezerva +0.0226 bodu)
- edge nad poplatkom v 98 % bootstrapových vzoriek
- odlíšiteľná od náhody (+2.6 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 38. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- 95. percentil max drawdownu 85.4 % (namerané 36.9 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 2.7 % pri riziku, s akým beh bežal
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- 100 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 's trendom' vlastnosti 'S trendom, alebo proti': 1379 obchodov (81.8 %), bez nej by break-even bol o +0.0271 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 374 | +43.38 | 0.0224 | 48.6 | 49.2 | +10/-6 | `20261031-084859-4ecd10` |
| 20221001-20231001 | 346 | +32.06 | 0.0191 | 18.7 | 48.0 | +7/-7 | `20261031-084905-5d418b` |
| 20231001-20241001 | 340 | +36.41 | 0.0165 | 14.3 | 48.5 | +5/-8 | `20261031-084908-aa30cc` |
| 20240904-20250904 | 302 | +121.18 | 0.0491 | 19.6 | 56.0 | +7/-6 | `20261031-084914-2aae5c` |
| 20250904-20260904 | 330 | +46.12 | 0.0147 | 46.2 | 50.3 | +6/-8 | `20261031-084920-8c1d50` |

Zisková v **5 z 5** okien, obchodov spolu 1686, break-even celkom 0.0244 %. Okná sa prekrývajú, 6 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.51 ATR za 5 barov)
- medián držania 64 barov grafu
- winrate 50.24 %, payoff 1.154
- 0.95 obchodov za deň
- šikmosť výnosov +1.801

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `session_end` 100 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 's trendom' vlastnosti 'S trendom, alebo proti': 1379 obchodov (81.8 %), break-even 0.0183 % oproti 0.0244 % celku. Bez nej by break-even bol 0.0515 % (+0.0271). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 1379 | 81.8 % | 50.4 | 0.0183 | 0.0515 | +0.0271 |
| proti trendu | 307 | 18.2 % | 49.5 | 0.0515 | 0.0183 | -0.0061 |

**Plánovaný RR**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 99.97 R | 220 | 26.8 % | 55.0 | 0.0064 | 0.0304 | +0.0060 |
| 99.97 R – 100 R | 335 | 40.9 % | 50.8 | 0.0067 | 0.0366 | +0.0122 |
| nad 100.02 R | 164 | 20.0 % | 51.2 | 0.0298 | 0.0229 | -0.0015 |
| 100 R – 100.02 R | 101 | 12.3 % | 59.4 | 0.1040 | 0.0121 | -0.0123 |

**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 16 h | 368 | 21.8 % | 45.4 | -0.0193 | 0.0364 | +0.0120 |
| 14 h – 16 h | 229 | 13.6 % | 54.1 | 0.0271 | 0.0240 | -0.0004 |
| do 13 h | 584 | 34.6 % | 50.2 | 0.0272 | 0.0229 | -0.0015 |
| 13 h – 14 h | 505 | 30.0 % | 52.1 | 0.0517 | 0.0130 | -0.0114 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0244 % | -0.0001 % ± 0.0094 | +2.60 | 99.2 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0244 % | -0.0007 % ± 0.0102 | +2.46 | 99.5 |

Edge je odlisitelny od nahody (2.6 sigma, percentil 99.2).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2023-01 | 449 | 30.8 | 49.2 | 0.0266 | 57 |
| 2023-01 - 2024-03 | 415 | 28.4 | 48.9 | 0.0175 | 37 |
| 2024-03 - 2025-06 | 427 | 29.3 | 51.5 | 0.0363 | 73 |
| 2025-06 - 2026-09 | 395 | 27.1 | 51.4 | 0.0176 | 38 |

Hranice pre úsek veľkosti posledného obdobia: -0.0083 až +0.0644 % (medián 0.0239).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 38. percentile, teda v medziach -0.0083 až +0.0644 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 10** — 2022-04-07T19:20 až 2022-04-20T20:00, spolu +2752.54.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-04-07T19:20 | 2022-04-07T20:00 | +128.48 | +0.44 | `session_end` |
| 2 | 2022-04-07T20:10 | 2022-04-07T20:10 | +0.48 | +0.00 | `session_end` |
| 3 | 2022-04-08T13:35 | 2022-04-08T20:00 | +145.49 | +0.50 | `session_end` |
| 4 | 2022-04-11T13:35 | 2022-04-11T20:00 | +270.51 | +0.96 | `session_end` |
| 5 | 2022-04-12T13:35 | 2022-04-12T20:00 | +454.51 | +1.60 | `session_end` |
| 6 | 2022-04-13T13:45 | 2022-04-13T20:00 | +384.51 | +1.37 | `session_end` |
| 7 | 2022-04-14T13:40 | 2022-04-14T20:00 | +588.02 | +2.07 | `session_end` |
| 8 | 2022-04-18T13:35 | 2022-04-18T20:00 | +96.02 | +0.35 | `session_end` |
| 9 | 2022-04-19T13:35 | 2022-04-19T20:00 | +361.02 | +1.30 | `session_end` |
| 10 | 2022-04-20T13:35 | 2022-04-20T20:00 | +323.51 | +1.14 | `session_end` |

**Straty za sebou: 8** — 2024-07-25T13:35 až 2024-07-29T20:00, spolu -1936.24, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-07-25T13:35 | 2024-07-25T17:00 | -408.35 | -1.07 | `session_end` |
| 2 | 2024-07-25T17:10 | 2024-07-25T19:50 | -712.35 | -1.84 | `session_end` |
| 3 | 2024-07-25T20:00 | 2024-07-25T20:00 | -72.83 | -0.19 | `session_end` |
| 4 | 2024-07-25T20:10 | 2024-07-25T20:10 | -58.33 | -0.15 | `session_end` |
| 5 | 2024-07-25T20:20 | 2024-07-25T20:20 | -8.33 | -0.02 | `session_end` |
| 6 | 2024-07-26T13:35 | 2024-07-26T20:00 | -154.84 | -0.41 | `session_end` |
| 7 | 2024-07-29T13:45 | 2024-07-29T15:30 | -438.85 | -1.13 | `session_end` |
| 8 | 2024-07-29T15:40 | 2024-07-29T20:00 | -82.35 | -0.21 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0244 %**, medián 0.0245 %, 90 % interval 0.0073–0.0426 %
- P(edge > poplatok) = **98.5 %**
- max drawdown: medián 36.9 %, 95. percentil 85.4 %, najhorší 100.0 %
- najdlhšia séria strát: medián 9, 95. percentil 11 obchodov
- pravdepodobnosť ruiny účtu: 2.7 %

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
<!-- POSUDOK cisla=b8b598c3 -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na MNQ, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Intraday momentum na indexoch (rovnaký jav ako NOA — Zarattini a spol.), 9:30–16:00 NY; zlato nemá otvorenie RTH, ktoré by pásmo ukotvilo.
2. **Má potenciál?** Zisková v 5 z 5 okien, 1686 obchodov (~337 za rok), break-even 0.0244 % (nad poplatkom 0,0018 %), +2.6 sigma proti náhodnému vstupu; WR 50.24 % pri payoffe 1.154. Odložený rok 25/26: +46.12 % PnL, break-even 0.0147 %. Jav je skôr skutočný ako vlastnosť vzorky.
3. **Čo dorobiť.** Stop: predloha bez stopu → 95. percentil DD je obrovský; otestovať `slPct` 0,25–1 % a kontrolu len každých 15–30 min (otočky v šume).
4. **Čo otestovať ďalej.** Smernica (`sigma*`: TF, dni sigma, násobok pásma, VWAP, stop); porovnať s NOA — ak NOA robí to isté lepšie, Sigma je duplicita.
5. **Použiteľné?** **Áno ako kandidát do smernice** — defaulty predlohy sú ziskové vo väčšine okien a edge je nad poplatkom; rozhodne hľadanie a odložený rok.
6. **Čo by som pridal.** Výstup cez VWAP / hranicu pásma (trailing ako NOA) namiesto držania do 16:00; menej otočiek pri širšom pásme.

<!-- POSUDOK KONIEC -->
