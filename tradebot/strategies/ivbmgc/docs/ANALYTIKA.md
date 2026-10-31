# Základná analytika — IVB 1.0 (MGC) (`ivbmgc`)

Zmerané 2026-10-31 na `MGC/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `/Users/martin/IBS/.nightsearch/base_ivbmgc.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy ivbmgc \
   --profile /Users/martin/IBS/.nightsearch/base_ivbmgc.json \
   --pair MGC/USD \
   --timeframe 5m \
   --fee 1.755e-05
```

## V čom je dobrá

- 550 obchodov spolu — na štatistiku dosť
- break-even 0.0041 % je nad poplatkom 0.0018 % (rezerva +0.0023 bodu)
- edge drží aj v poslednom období (2025-06 - 2026-08 na 52. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- zisková v 3 z 5 referenčných okien (20211001-20221001, 20250904-20260904 v strate)
- edge nad poplatkom len v 62 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 50.6 % (namerané 21.9 % medián) — na účet to treba mať
- proti náhode len +0.7 sigma: náznak, nie dôkaz
- charakter: prerazenie (breakout) (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- najhoršia skupina '0.66 R – 0.68 R' vlastnosti 'Plánovaný RR': 147 obchodov (26.7 %), bez nej by break-even bol o +0.0146 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 121 | -2.23 | -0.0033 | 6.1 | 59.5 | +7/-5 | `20261031-085200-91d6d9` |
| 20221001-20231001 | 121 | +1.69 | 0.0055 | 4.5 | 61.2 | +6/-4 | `20261031-085203-50fa61` |
| 20231001-20241001 | 100 | +0.36 | 0.0025 | 6.3 | 61.0 | +6/-4 | `20261031-085206-58f3b9` |
| 20240904-20250904 | 105 | +14.99 | 0.0254 | 5.9 | 69.5 | +9/-3 | `20261031-085209-200472` |
| 20250904-20260904 | 113 | -8.32 | -0.0066 | 30.7 | 61.1 | +7/-5 | `20261031-085212-2e6fb2` |

Zisková v **3 z 5** okien, obchodov spolu 550, break-even celkom 0.0041 %. Okná sa prekrývajú, 10 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota priemerná)

- vstup po pohybe v smere obchodu (+1.56 ATR za 5 barov)
- medián držania 13.1 barov grafu
- winrate 62.36 %, payoff 0.621
- 0.31 obchodov za deň
- šikmosť výnosov -0.666

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `take_profit` 62.4 %, `stop_loss` 37.6 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je '0.66 R – 0.68 R' vlastnosti 'Plánovaný RR': 147 obchodov (26.7 %), break-even -0.0316 % oproti 0.0041 % celku. Bez nej by break-even bol 0.0187 % (+0.0146). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Plánovaný RR**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.66 R – 0.68 R | 147 | 26.7 % | 53.1 | -0.0316 | 0.0187 | +0.0146 |
| 0.64 R – 0.66 R | 141 | 25.6 % | 62.4 | 0.0183 | -0.0016 | -0.0057 |
| do 0.64 R | 143 | 26.0 % | 69.2 | 0.0189 | -0.0004 | -0.0045 |
| nad 0.68 R | 119 | 21.6 % | 65.5 | 0.0190 | 0.0006 | -0.0035 |

**Sviatok na burze v USA**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| bežný deň | 496 | 90.2 % | 62.9 | 0.0028 | 0.0158 | +0.0117 |
| deň po sviatku | 11 | 2.0 % | 81.8 | 0.0760 | 0.0026 | -0.0015 |
| deň pred sviatkom | 9 | 1.6 % | 88.9 | 0.1007 | 0.0022 | -0.0019 |

**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| nad 0.4482 % | 137 | 24.9 % | 57.7 | -0.0148 | 0.0131 | +0.0090 |
| 0.3639 % – 0.4482 % | 137 | 24.9 % | 60.6 | 0.0008 | 0.0051 | +0.0010 |
| do 0.3003 % | 138 | 25.1 % | 61.6 | 0.0080 | 0.0030 | -0.0011 |
| 0.3003 % – 0.3639 % | 138 | 25.1 % | 69.6 | 0.0314 | -0.0037 | -0.0078 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0041 % | -0.0011 % ± 0.0070 | +0.74 | 76.4 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0041 % | -0.0004 % ± 0.0072 | +0.63 | 73.0 |

Neodlisitelne od nahody (+0.7 sigma, percentil 76.4). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 149 | 10.2 | 59.7 | -0.0020 | 32 |
| 2022-12 - 2024-03 | 129 | 8.8 | 62.0 | 0.0070 | 52 |
| 2024-03 - 2025-06 | 124 | 8.4 | 62.1 | 0.0025 | 45 |
| 2025-06 - 2026-08 | 148 | 10.1 | 65.5 | 0.0064 | 52 |

Hranice pre úsek veľkosti posledného obdobia: -0.0244 až +0.0298 % (medián 0.0055).

**DRZI** — posledné obdobie (2025-06 - 2026-08) je na 52. percentile, teda v medziach -0.0244 až +0.0298 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 9** — 2024-11-14T15:10 až 2024-12-20T15:22, spolu +467.65.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-11-14T15:10 | 2024-11-14T16:18 | +69.10 | +0.27 | `take_profit` |
| 2 | 2024-11-18T15:25 | 2024-11-19T01:05 | +52.08 | +0.20 | `take_profit` |
| 3 | 2024-11-27T15:05 | 2024-11-27T19:40 | +69.07 | +0.26 | `take_profit` |
| 4 | 2024-11-27T19:45 | 2024-11-28T01:01 | +33.07 | +0.12 | `take_profit` |
| 5 | 2024-11-28T15:25 | 2024-11-29T00:52 | +36.07 | +0.14 | `take_profit` |
| 6 | 2024-12-13T15:25 | 2024-12-13T20:39 | +61.06 | +0.23 | `take_profit` |
| 7 | 2024-12-18T15:05 | 2024-12-18T19:00 | +44.07 | +0.17 | `take_profit` |
| 8 | 2024-12-18T19:05 | 2024-12-18T19:06 | +41.07 | +0.16 | `take_profit` |
| 9 | 2024-12-20T15:10 | 2024-12-20T15:22 | +62.07 | +0.24 | `take_profit` |

**Straty za sebou: 5** — 2021-11-03T14:50 až 2021-11-10T02:51, spolu -304.16, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2021-11-03T14:50 | 2021-11-03T18:48 | -84.62 | -0.48 | `stop_loss` |
| 2 | 2021-11-04T14:05 | 2021-11-04T16:51 | -68.63 | -0.38 | `stop_loss` |
| 3 | 2021-11-04T16:55 | 2021-11-05T01:16 | -44.63 | -0.25 | `stop_loss` |
| 4 | 2021-11-09T15:05 | 2021-11-09T17:53 | -67.64 | -0.37 | `stop_loss` |
| 5 | 2021-11-09T17:55 | 2021-11-10T02:51 | -38.64 | -0.21 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0041 %**, medián 0.0045 %, 90 % interval -0.0108–0.0178 %
- P(edge > poplatok) = **62.3 %**
- max drawdown: medián 21.9 %, 95. percentil 50.6 %, najhorší 100.0 %
- najdlhšia séria strát: medián 5, 95. percentil 7 obchodov
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
<!-- POSUDOK cisla=ec6563ed -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na MGC, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Prieraz stlačeného IB 9:30–10:00 NY pri náraste objemu; index futures 5m. Tu na MGC (zlato) — logika robená pre index, čísla to treba brať ako test prenosu.
2. **Má potenciál?** Zisková v 3 z 5 okien, 550 obchodov (~110 za rok), break-even 0.0041 % (nad poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 62.36 % pri payoffe 0.621. Odložený rok 25/26: -8.32 % PnL, break-even -0.0066 %. Kladné okná sú skôr vlastnosť vzorky ako stabilný jav.
3. **Čo dorobiť.** Dve zvláštnosti predlohy (pokus aj bez prierazu, IB do priemeru na 10:00–10:04) ako prepínače; koniec dňa pre prop.
4. **Čo otestovať ďalej.** Smernica (`ivb*`: pomer IB, objem, stop / cieľ v ATR, okno vstupu, TF).
5. **Použiteľné?** **V defaultoch predlohy nie** — edge nad poplatkom nie je stabilný po rokoch; šancu má len s nastavením, ktoré nájde smernica (inak vyradiť).
6. **Čo by som pridal.** Smer dňa (VWAP od 9:30) a cieľ ≥ 1 R namiesto 0,67 R.

<!-- POSUDOK KONIEC -->
