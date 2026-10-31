# Základná analytika — LONDON LIQUIDITY IFVG 1.0 (ES) (`lliqes`)

Zmerané 2026-10-31 na `ES/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `/Users/martin/IBS/.nightsearch/base_lliqes.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy lliqes \
   --profile /Users/martin/IBS/.nightsearch/base_lliqes.json \
   --pair ES/USD \
   --timeframe 5m \
   --fee 1.755e-05
```

## V čom je dobrá

- 306 obchodov spolu — na štatistiku dosť
- break-even 0.0018 % je nad poplatkom 0.0018 % (rezerva +0.0000 bodu)
- edge drží aj v poslednom období (2025-06 - 2026-08 na 46. percentile toho, čo stratégia vyrobí sama od seba)
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 2 z 5 referenčných okien (20221001-20231001, 20231001-20241001, 20240904-20250904 v strate)
- edge nad poplatkom len v 52 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 87.7 % (namerané 39.3 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 2.5 % pri riziku, s akým beh bežal
- proti náhode len +0.9 sigma: náznak, nie dôkaz
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 66 | +34.33 | 0.0140 | 23.7 | 63.6 | +8/-5 | `20261031-085039-74dcec` |
| 20221001-20231001 | 61 | -7.01 | -0.0010 | 11.5 | 45.9 | +2/-6 | `20261031-085045-f6acca` |
| 20231001-20241001 | 44 | -4.58 | -0.0003 | 13.3 | 45.5 | +4/-6 | `20261031-085048-aebe49` |
| 20240904-20250904 | 67 | -38.62 | -0.0079 | 41.1 | 43.3 | +3/-6 | `20261031-085054-4d65b7` |
| 20250904-20260904 | 73 | +11.79 | 0.0040 | 19.6 | 54.8 | +8/-4 | `20261031-085058-3f9206` |

Zisková v **2 z 5** okien, obchodov spolu 306, break-even celkom 0.0018 %. Okná sa prekrývajú, 5 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.39 ATR za 5 barov)
- medián držania 5.4 barov grafu
- winrate 51.31 %, payoff 0.952
- 0.17 obchodov za deň
- šikmosť výnosov -0.232

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 51.3 %, `stop_loss` 48.7 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0080 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| proti trendu | 233 | 76.1 % | 50.2 | -0.0008 | 0.0098 | +0.0080 |
| s trendom | 73 | 23.9 % | 54.8 | 0.0098 | -0.0008 | -0.0026 |

**Plánovaný RR**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 1 R | 227 | 74.2 % | 51.5 | 0.0008 | 0.0049 | +0.0031 |
| nad 1.04 R | 75 | 24.5 % | 49.3 | 0.0021 | 0.0017 | -0.0001 |

**Kalendárny mesiac**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 04 | 22 | 7.2 % | 40.9 | -0.0234 | 0.0038 | +0.0020 |
| 06 | 23 | 7.5 % | 39.1 | -0.0082 | 0.0026 | +0.0008 |
| 12 | 24 | 7.8 % | 37.5 | -0.0072 | 0.0026 | +0.0008 |
| 02 | 18 | 5.9 % | 38.9 | -0.0058 | 0.0023 | +0.0005 |
| … | | | | | | |
| 03 | 26 | 8.5 % | 53.9 | 0.0095 | 0.0011 | -0.0007 |
| 05 | 28 | 9.2 % | 53.6 | 0.0107 | 0.0010 | -0.0008 |
| 08 | 28 | 9.2 % | 60.7 | 0.0123 | 0.0007 | -0.0011 |
| 11 | 26 | 8.5 % | 61.5 | 0.0126 | 0.0008 | -0.0010 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0018 % | -0.0002 % ± 0.0023 | +0.87 | 79.3 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0018 % | -0.0000 % ± 0.0019 | +0.97 | 83.7 |

Neodlisitelne od nahody (+0.9 sigma, percentil 79.3). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 83 | 5.7 | 61.5 | 0.0123 | 97 |
| 2022-12 - 2024-03 | 64 | 4.4 | 43.8 | -0.0030 | 18 |
| 2024-03 - 2025-06 | 72 | 4.9 | 45.8 | -0.0028 | 17 |
| 2025-06 - 2026-08 | 87 | 5.9 | 51.7 | 0.0012 | 46 |

Hranice pre úsek veľkosti posledného obdobia: -0.0069 až +0.0106 % (medián 0.0019).

**DRZI** — posledné obdobie (2025-06 - 2026-08) je na 46. percentile, teda v medziach -0.0069 až +0.0106 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 8** — 2021-10-15T00:05 až 2021-11-05T01:39, spolu +986.12, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2021-10-15T00:05 | 2021-10-15T00:07 | +117.22 | +0.05 | `take_profit` |
| 2 | 2021-10-18T00:45 | 2021-10-18T00:54 | +179.67 | +0.08 | `take_profit` |
| 3 | 2021-10-19T02:20 | 2021-10-19T02:37 | +117.14 | +0.05 | `take_profit` |
| 4 | 2021-10-25T00:45 | 2021-10-25T00:52 | +154.55 | +0.07 | `take_profit` |
| 5 | 2021-10-27T03:05 | 2021-10-27T05:00 | +116.98 | +0.05 | `take_profit` |
| 6 | 2021-11-01T03:45 | 2021-11-01T04:41 | +79.42 | +0.03 | `take_profit` |
| 7 | 2021-11-04T00:40 | 2021-11-04T01:20 | +104.33 | +0.04 | `take_profit` |
| 8 | 2021-11-05T00:35 | 2021-11-05T01:39 | +116.80 | +0.05 | `take_profit` |

**Straty za sebou: 6** — 2023-08-09T03:25 až 2023-09-11T04:15, spolu -772.13, rovnako dlhých sérií 3.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-08-09T03:25 | 2023-08-09T05:05 | -95.44 | -0.04 | `stop_loss` |
| 2 | 2023-08-15T01:40 | 2023-08-15T01:43 | -145.42 | -0.06 | `stop_loss` |
| 3 | 2023-08-17T02:40 | 2023-08-17T02:50 | -170.26 | -0.08 | `stop_loss` |
| 4 | 2023-08-21T01:20 | 2023-08-21T01:41 | -157.70 | -0.07 | `stop_loss` |
| 5 | 2023-09-06T02:20 | 2023-09-06T02:53 | -95.40 | -0.04 | `stop_loss` |
| 6 | 2023-09-11T03:20 | 2023-09-11T04:15 | -107.92 | -0.05 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0018 %**, medián 0.0019 %, 90 % interval -0.0027–0.0064 %
- P(edge > poplatok) = **51.6 %**
- max drawdown: medián 39.3 %, 95. percentil 87.7 %, najhorší 100.0 %
- najdlhšia séria strát: medián 6, 95. percentil 9 obchodov
- pravdepodobnosť ruiny účtu: 2.5 %

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
<!-- POSUDOK cisla=4d47f85b -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na ES, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Večerný sweep high / low popoludnia NY (19:15–23:45) a inverzný FVG — málo obchodov (~60 / rok na MNQ), likvidita v Ázii je tenká. Tu na ES — rovnaká logika ako MNQ, prahy v ATR sa prispôsobia.
2. **Má potenciál?** Zisková v 2 z 5 okien, 306 obchodov (~61 za rok), break-even 0.0018 % (pod poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 51.31 % pri payoffe 0.952. Odložený rok 25/26: +11.79 % PnL, break-even 0.0040 %. Kladné okná sú skôr vlastnosť vzorky ako stabilný jav.
3. **Čo dorobiť.** Okno seansy aj sweepu sú pre NQ nevhodné (popoludnie NY → večer); skúsiť Ázia / Londýn ako zdroj likvidity a sweep v NY ráno.
4. **Čo otestovať ďalej.** Smernica (`lliq*`: okná seansy a sweepu, stop / cieľ, vek FVG); pri ~60 obchodoch za rok hranicu 150 z princípu nesplní, kým sa okno nezmení.
5. **Použiteľné?** **V defaultoch predlohy nie** — edge nad poplatkom nie je stabilný po rokoch; šancu má len s nastavením, ktoré nájde smernica (inak vyradiť).
6. **Čo by som pridal.** Likviditu brať z Ázie (20:00–2:00 NY) a sweep v Londýne / NY ráno — klasické ICT poradie, ktoré dá viac obchodov.

<!-- POSUDOK KONIEC -->
