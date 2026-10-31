# Základná analytika — IVB 1.0 (ES) (`ivbes`)

Zmerané 2026-10-31 na `ES/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `/Users/martin/IBS/.nightsearch/base_ivbes.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy ivbes \
   --profile /Users/martin/IBS/.nightsearch/base_ivbes.json \
   --pair ES/USD \
   --timeframe 5m \
   --fee 1.755e-05
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- 559 obchodov spolu — na štatistiku dosť
- break-even 0.0137 % je nad poplatkom 0.0018 % (rezerva +0.0119 bodu)
- edge nad poplatkom v 99 % bootstrapových vzoriek
- odlíšiteľná od náhody (+3.3 sigma proti náhodnému vstupu)
- edge drží aj v poslednom období (2025-06 - 2026-09 na 29. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- 95. percentil max drawdownu 100.0 % (namerané 43.6 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 5.1 % pri riziku, s akým beh bežal
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina 'nad 2.05' vlastnosti 'Volatilita voči normálu': 139 obchodov (24.9 %), bez nej by break-even bol o +0.0101 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 106 | +58.31 | 0.0144 | 34.0 | 63.2 | +10/-4 | `20261031-085150-49cb58` |
| 20221001-20231001 | 113 | +23.78 | 0.0068 | 44.6 | 62.8 | +8/-4 | `20261031-085153-4061bc` |
| 20231001-20241001 | 116 | +62.77 | 0.0123 | 25.0 | 64.7 | +8/-4 | `20261031-085156-ea9bce` |
| 20240904-20250904 | 128 | +114.11 | 0.0167 | 63.4 | 64.8 | +7/-5 | `20261031-085159-40af1e` |
| 20250904-20260904 | 106 | +44.67 | 0.0077 | 49.8 | 64.2 | +8/-6 | `20261031-085202-ed50c7` |

Zisková v **5 z 5** okien, obchodov spolu 559, break-even celkom 0.0137 %. Okná sa prekrývajú, 10 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.49 ATR za 5 barov)
- medián držania 9.2 barov grafu
- winrate 64.76 %, payoff 0.665
- 0.31 obchodov za deň
- šikmosť výnosov -0.681

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 64.8 %, `stop_loss` 35.2 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'nad 2.05' vlastnosti 'Volatilita voči normálu': 139 obchodov (24.9 %), break-even -0.018 % oproti 0.0137 % celku. Bez nej by break-even bol 0.0238 % (+0.0101). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Volatilita voči normálu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 2.05 | 139 | 24.9 % | 54.0 | -0.0180 | 0.0238 | +0.0101 |
| do 1.454 | 141 | 25.2 % | 64.5 | 0.0140 | 0.0137 | +0.0000 |
| 1.762 – 2.05 | 140 | 25.0 % | 67.1 | 0.0228 | 0.0108 | -0.0029 |
| 1.454 – 1.762 | 139 | 24.9 % | 73.4 | 0.0351 | 0.0067 | -0.0070 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.8471 – 0.9242 | 141 | 25.2 % | 57.5 | -0.0084 | 0.0214 | +0.0077 |
| do 0.8471 | 140 | 25.0 % | 65.7 | 0.0105 | 0.0149 | +0.0012 |
| nad 0.9632 | 139 | 24.9 % | 63.3 | 0.0161 | 0.0130 | -0.0007 |
| 0.9242 – 0.9632 | 139 | 24.9 % | 72.7 | 0.0382 | 0.0059 | -0.0078 |

**Plánovaný RR**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 0.65 R | 158 | 28.3 % | 60.8 | -0.0012 | 0.0195 | +0.0058 |
| 0.65 R – 0.67 R | 278 | 49.7 % | 66.2 | 0.0193 | 0.0082 | -0.0055 |
| nad 0.67 R | 123 | 22.0 % | 66.7 | 0.0201 | 0.0120 | -0.0017 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0137 % | -0.0002 % ± 0.0042 | +3.32 | 100.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0137 % | -0.0004 % ± 0.0049 | +2.89 | 99.8 |

Edge je odlisitelny od nahody (3.3 sigma, percentil 100.0).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 133 | 9.0 | 63.9 | 0.0174 | 62 |
| 2022-12 - 2024-03 | 132 | 9.0 | 64.4 | 0.0069 | 29 |
| 2024-03 - 2025-06 | 157 | 10.7 | 66.2 | 0.0222 | 78 |
| 2025-06 - 2026-09 | 137 | 9.3 | 64.2 | 0.0079 | 29 |

Hranice pre úsek veľkosti posledného obdobia: -0.0039 až +0.0318 % (medián 0.0138).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 29. percentile, teda v medziach -0.0039 až +0.0318 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 10** — 2022-02-23T15:05 až 2022-03-22T15:24, spolu +7461.03.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-02-23T15:05 | 2022-02-23T15:17 | +654.95 | +0.30 | `take_profit` |
| 2 | 2022-02-23T15:30 | 2022-02-23T16:18 | +779.99 | +0.36 | `take_profit` |
| 3 | 2022-02-28T15:40 | 2022-02-28T16:22 | +1079.84 | +0.50 | `take_profit` |
| 4 | 2022-03-01T15:45 | 2022-03-01T16:45 | +1054.92 | +0.49 | `take_profit` |
| 5 | 2022-03-11T15:05 | 2022-03-11T16:42 | +817.56 | +0.38 | `take_profit` |
| 6 | 2022-03-11T16:45 | 2022-03-11T19:53 | +842.57 | +0.40 | `take_profit` |
| 7 | 2022-03-18T14:05 | 2022-03-18T16:31 | +679.76 | +0.31 | `take_profit` |
| 8 | 2022-03-18T16:35 | 2022-03-18T17:58 | +617.23 | +0.28 | `take_profit` |
| 9 | 2022-03-22T14:05 | 2022-03-22T14:34 | +454.61 | +0.20 | `take_profit` |
| 10 | 2022-03-22T15:05 | 2022-03-22T15:24 | +479.60 | +0.21 | `take_profit` |

**Straty za sebou: 6** — 2026-04-29T14:35 až 2026-05-26T19:40, spolu -4615.50.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-04-29T14:35 | 2026-04-29T15:11 | -762.57 | -0.21 | `stop_loss` |
| 2 | 2026-05-04T14:15 | 2026-05-04T15:19 | -1050.22 | -0.29 | `stop_loss` |
| 3 | 2026-05-07T15:10 | 2026-05-07T15:58 | -725.48 | -0.20 | `stop_loss` |
| 4 | 2026-05-25T14:35 | 2026-05-25T15:11 | -350.77 | -0.09 | `stop_loss` |
| 5 | 2026-05-26T14:40 | 2026-05-26T15:17 | -825.74 | -0.22 | `stop_loss` |
| 6 | 2026-05-26T15:55 | 2026-05-26T19:40 | -900.71 | -0.24 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0137 %**, medián 0.0138 %, 90 % interval 0.0050–0.0227 %
- P(edge > poplatok) = **98.8 %**
- max drawdown: medián 43.6 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 6, 95. percentil 7 obchodov
- pravdepodobnosť ruiny účtu: 5.1 %

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
<!-- POSUDOK cisla=4444a3c3 -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na ES, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Prieraz stlačeného IB 9:30–10:00 NY pri náraste objemu; index futures 5m. Tu na ES — rovnaká logika ako MNQ, prahy v ATR sa prispôsobia.
2. **Má potenciál?** Zisková v 5 z 5 okien, 559 obchodov (~112 za rok), break-even 0.0137 % (nad poplatkom 0,0018 %), +3.3 sigma proti náhodnému vstupu; WR 64.76 % pri payoffe 0.665. Odložený rok 25/26: +44.67 % PnL, break-even 0.0077 %. Jav je skôr skutočný ako vlastnosť vzorky.
3. **Čo dorobiť.** Dve zvláštnosti predlohy (pokus aj bez prierazu, IB do priemeru na 10:00–10:04) ako prepínače; koniec dňa pre prop.
4. **Čo otestovať ďalej.** Smernica (`ivb*`: pomer IB, objem, stop / cieľ v ATR, okno vstupu, TF).
5. **Použiteľné?** **Áno ako kandidát do smernice** — defaulty predlohy sú ziskové vo väčšine okien a edge je nad poplatkom; rozhodne hľadanie a odložený rok.
6. **Čo by som pridal.** Smer dňa (VWAP od 9:30) a cieľ ≥ 1 R namiesto 0,67 R.

<!-- POSUDOK KONIEC -->
