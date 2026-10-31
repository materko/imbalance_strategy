# Základná analytika — ORB 15/5 1.0 (ES) (`orb15es`)

Zmerané 2026-10-31 na `ES/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `/Users/martin/IBS/.nightsearch/base_orb15es.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy orb15es \
   --profile /Users/martin/IBS/.nightsearch/base_orb15es.json \
   --pair ES/USD \
   --timeframe 5m \
   --fee 1.755e-05
```

## V čom je dobrá

- 1161 obchodov spolu — na štatistiku dosť
- break-even 0.0075 % je nad poplatkom 0.0018 % (rezerva +0.0057 bodu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 34. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- zisková v 3 z 5 referenčných okien (20211001-20221001, 20231001-20241001 v strate)
- edge nad poplatkom len v 82 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 100.0 % (namerané 100.0 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 57.3 % pri riziku, s akým beh bežal
- proti náhode len +1.3 sigma: náznak, nie dôkaz
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- 27.7 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 'nad 2.232' vlastnosti 'Volatilita voči normálu': 290 obchodov (25.0 %), bez nej by break-even bol o +0.0116 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 249 | -19.72 | -0.0001 | 141.5 | 43.0 | +6/-6 | `20261031-084724-f4c942` |
| 20221001-20231001 | 224 | +183.32 | 0.0215 | 51.8 | 44.6 | +6/-8 | `20261031-084730-1a12d4` |
| 20231001-20241001 | 240 | -13.35 | 0.0007 | 87.5 | 38.3 | +5/-9 | `20261031-084733-6b2624` |
| 20240904-20250904 | 230 | +114.44 | 0.0101 | 63.4 | 42.2 | +6/-7 | `20261031-084739-6a97a8` |
| 20250904-20260904 | 236 | +26.17 | 0.0033 | 66.7 | 42.8 | +6/-11 | `20261031-084745-030948` |

Zisková v **3 z 5** okien, obchodov spolu 1161, break-even celkom 0.0075 %. Okná sa prekrývajú, 18 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.41 ATR za 5 barov)
- medián držania 32.4 barov grafu
- winrate 42.46 %, payoff 1.434
- 0.65 obchodov za deň
- šikmosť výnosov +0.771

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 50.8 %, `session_end` 27.7 %, `take_profit` 21.4 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'nad 2.232' vlastnosti 'Volatilita voči normálu': 290 obchodov (25.0 %), break-even -0.0276 % oproti 0.0075 % celku. Bez nej by break-even bol 0.0191 % (+0.0116). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Volatilita voči normálu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 2.232 | 290 | 25.0 % | 36.9 | -0.0276 | 0.0191 | +0.0116 |
| 1.819 – 2.232 | 289 | 24.9 % | 43.6 | 0.0136 | 0.0056 | -0.0019 |
| 1.475 – 1.819 | 291 | 25.1 % | 44.0 | 0.0139 | 0.0053 | -0.0022 |
| do 1.475 | 291 | 25.1 % | 45.4 | 0.0293 | -0.0001 | -0.0076 |

**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.0721 | 291 | 25.1 % | 40.5 | -0.0176 | 0.0159 | +0.0084 |
| 0.0721 – 0.1439 | 291 | 25.1 % | 39.2 | -0.0009 | 0.0104 | +0.0029 |
| 0.1439 – 0.246 | 289 | 24.9 % | 42.2 | 0.0164 | 0.0046 | -0.0029 |
| nad 0.246 | 290 | 25.0 % | 47.9 | 0.0325 | -0.0008 | -0.0083 |

**Deň v týždni**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| streda | 239 | 20.6 % | 37.7 | -0.0137 | 0.0130 | +0.0055 |
| štvrtok | 231 | 19.9 % | 39.4 | 0.0015 | 0.0090 | +0.0015 |
| pondelok | 225 | 19.4 % | 44.0 | 0.0109 | 0.0067 | -0.0008 |
| utorok | 241 | 20.8 % | 45.2 | 0.0149 | 0.0056 | -0.0019 |
| piatok | 225 | 19.4 % | 46.2 | 0.0250 | 0.0033 | -0.0042 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0075 % | 0.0010 % ± 0.0050 | +1.30 | 90.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0075 % | 0.0011 % ± 0.0055 | +1.17 | 88.9 |

Naznak, ale nie dokaz (1.3 sigma, percentil 90.0). Take rozdiely nahoda robi bezne.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 301 | 20.4 | 43.5 | 0.0080 | 49 |
| 2022-12 - 2024-03 | 284 | 19.2 | 41.2 | 0.0031 | 35 |
| 2024-03 - 2025-06 | 284 | 19.2 | 41.9 | 0.0171 | 75 |
| 2025-06 - 2026-09 | 292 | 19.8 | 43.1 | 0.0023 | 34 |

Hranice pre úsek veľkosti posledného obdobia: -0.0139 až +0.0289 % (medián 0.0074).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 34. percentile, teda v medziach -0.0139 až +0.0289 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 6** — 2021-10-14T14:05 až 2021-10-21T19:55, spolu +3965.28, rovnako dlhých sérií 6.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2021-10-14T14:05 | 2021-10-14T20:00 | +929.74 | +0.42 | `session_end` |
| 2 | 2021-10-15T14:00 | 2021-10-15T20:00 | +329.67 | +0.15 | `session_end` |
| 3 | 2021-10-18T13:50 | 2021-10-18T20:00 | +1054.66 | +0.47 | `session_end` |
| 4 | 2021-10-19T14:10 | 2021-10-19T20:00 | +854.59 | +0.38 | `session_end` |
| 5 | 2021-10-20T13:50 | 2021-10-20T20:00 | +104.56 | +0.05 | `session_end` |
| 6 | 2021-10-21T13:55 | 2021-10-21T19:55 | +692.05 | +0.31 | `take_profit` |

**Straty za sebou: 11** — 2025-11-17T14:50 až 2025-12-02T15:01, spolu -14467.57.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-11-17T14:50 | 2025-11-17T16:08 | -1949.34 | -0.58 | `stop_loss` |
| 2 | 2025-11-18T14:50 | 2025-11-18T17:58 | -1686.69 | -0.51 | `stop_loss` |
| 3 | 2025-11-19T14:50 | 2025-11-19T17:33 | -1749.18 | -0.52 | `stop_loss` |
| 4 | 2025-11-20T14:55 | 2025-11-20T16:00 | -886.88 | -0.26 | `stop_loss` |
| 5 | 2025-11-21T15:05 | 2025-11-21T16:36 | -1299.05 | -0.40 | `stop_loss` |
| 6 | 2025-11-24T14:50 | 2025-11-24T15:05 | -1649.21 | -0.50 | `stop_loss` |
| 7 | 2025-11-25T14:50 | 2025-11-25T15:44 | -2549.27 | -0.76 | `stop_loss` |
| 8 | 2025-11-26T14:50 | 2025-11-26T14:59 | -974.46 | -0.29 | `stop_loss` |
| 9 | 2025-11-27T15:35 | 2025-11-27T23:00 | -236.98 | -0.07 | `session_end` |
| 10 | 2025-11-28T15:20 | 2025-12-01T00:45 | -774.50 | -0.23 | `stop_loss` |
| 11 | 2025-12-02T14:55 | 2025-12-02T15:01 | -712.02 | -0.21 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0075 %**, medián 0.0075 %, 90 % interval -0.0029–0.0181 %
- P(edge > poplatok) = **81.6 %**
- max drawdown: medián 100.0 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 10, 95. percentil 15 obchodov
- pravdepodobnosť ruiny účtu: 57.3 %

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
<!-- POSUDOK cisla=85348268 -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na ES, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Intraday index futures od 9:45 NY, jeden obchod denne; na zlate OR 9:30–9:45 nemá zmysel otvorenia akciovej burzy, čísla tam ukazujú skôr šum. Tu na ES — rovnaká logika ako MNQ, prahy v ATR sa prispôsobia.
2. **Má potenciál?** Zisková v 3 z 5 okien, 1161 obchodov (~232 za rok), break-even 0.0075 % (nad poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 42.46 % pri payoffe 1.434. Odložený rok 25/26: +26.17 % PnL, break-even 0.0033 %. Kladné okná sú skôr vlastnosť vzorky ako stabilný jav.
3. **Čo dorobiť.** Skúsiť OR 5 / 30 / 60 min a cieľ RR 0,75–1,5; filter predošlého dňa a knôtu majú byť v mriežke oboma smermi; pre prop koniec dňa.
4. **Čo otestovať ďalej.** Smernica (mriežka glsearch `orb15*`: dĺžka OR, RR, filtre, trend EMA, limit / IBS / pin bar); rozhodne odložený rok 25/26, ktorý je pri MNQ v defaultoch stratový.
5. **Použiteľné?** **V defaultoch predlohy nie** — edge nad poplatkom nie je stabilný po rokoch; šancu má len s nastavením, ktoré nájde smernica (inak vyradiť).
6. **Čo by som pridal.** Smer dňa z VWAP od 9:30 alebo z polohy voči včerajšiemu zavretiu — ORB bez kontextu chytá aj falošné prierazy rána.

<!-- POSUDOK KONIEC -->
