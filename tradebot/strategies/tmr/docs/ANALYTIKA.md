# Základná analytika — T-MEAN REVERSION 1.0 (`tmr`)

Zmerané 2026-10-31 na `MNQ/USD` 15m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `/Users/martin/IBS/.nightsearch/base_tmr.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy tmr \
   --profile /Users/martin/IBS/.nightsearch/base_tmr.json \
   --pair MNQ/USD \
   --timeframe 15m \
   --fee 1.755e-05
```

## V čom je dobrá

- break-even 0.1530 % je nad poplatkom 0.0018 % (rezerva +0.1512 bodu)
- edge nad poplatkom v 97 % bootstrapových vzoriek
- edge drží aj v poslednom období (2025-06 - 2026-08 na 10. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- zisková v 4 z 5 referenčných okien (20250904-20260904 v strate)
- 95. percentil max drawdownu 55.7 % (namerané 25.3 % medián) — na účet to treba mať
- proti náhode len +1.0 sigma: náznak, nie dôkaz
- charakter: formácia / štruktúra (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- 99.2 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina '99.99 R – 100 R' vlastnosti 'Plánovaný RR': 39 obchodov (32.0 %), bez nej by break-even bol o +0.1684 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 28 | +62.39 | 0.4008 | 7.6 | 60.7 | +4/-2 | `20261031-085059-2dea39` |
| 20221001-20231001 | 25 | +24.01 | 0.1842 | 7.4 | 60.0 | +4/-2 | `20261031-085102-3e6f8c` |
| 20231001-20241001 | 24 | +15.29 | 0.0899 | 21.6 | 54.2 | +5/-4 | `20261031-085105-be153c` |
| 20240904-20250904 | 21 | +60.74 | 0.3401 | 11.0 | 52.4 | +3/-4 | `20261031-085108-287b98` |
| 20250904-20260904 | 26 | -11.61 | -0.0404 | 32.8 | 61.5 | +4/-2 | `20261031-085111-7a17ee` |

Zisková v **4 z 5** okien, obchodov spolu 122, break-even celkom 0.1530 %. Okná sa prekrývajú, 2 obchodov započítaných dvakrát vypadlo.

## Charakter

**Formácia / štruktúra** (istota priemerná)

- vstup bez jasného smeru pohybu (+0.03 ATR za 5 barov)
- medián držania 203 barov grafu
- winrate 57.38 %, payoff 1.088
- 0.07 obchodov za deň
- šikmosť výnosov +0.862

- **Čo je normálne:** Zmes: časť obchodov sa chová ako prerazenie, časť ako návrat. Priemer preto o jednotlivom obchode nehovorí veľa.
- **Na čo pozor:** Práve pri tomto type sa najviac oplatí rozdeliť obchody na skupiny (`tester.analytics`) — priemer skrýva dve rôzne populácie.
- **Čo ladiť:** Podmienky vstupu (ktoré modely/formácie zapnuté) a potom až výstup.

Výstupy: `session_end` 99.2 %, `force_exit` 0.8 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je '99.99 R – 100 R' vlastnosti 'Plánovaný RR': 39 obchodov (32.0 %), break-even -0.1922 % oproti 0.153 % celku. Bez nej by break-even bol 0.3214 % (+0.1684). Ziadny parameter tuto vlastnost priamo neriadi, takze ak sa to potvrdi aj na inych oknach, je to kandidat na filter.


**Plánovaný RR**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 99.99 R – 100 R | 39 | 32.0 % | 41.0 | -0.1922 | 0.3214 | +0.1684 |
| do 99.99 R | 40 | 32.8 % | 57.5 | 0.1442 | 0.1576 | +0.0046 |
| 100 R – 100.02 R | 30 | 24.6 % | 63.3 | 0.4908 | 0.0488 | -0.1042 |
| nad 100.02 R | 13 | 10.7 % | 92.3 | 0.5329 | 0.1126 | -0.0404 |

**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 69 | 56.6 % | 56.5 | 0.0792 | 0.2573 | +0.1043 |
| proti trendu | 53 | 43.4 % | 58.5 | 0.2573 | 0.0792 | -0.0738 |

**Kde v rozsahu, v smere obchodu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.5879 – 0.8749 | 30 | 24.6 % | 43.3 | -0.1117 | 0.2422 | +0.0892 |
| 0.2784 – 0.5879 | 31 | 25.4 % | 58.1 | 0.2047 | 0.1347 | -0.0183 |
| nad 0.8749 | 30 | 24.6 % | 66.7 | 0.2142 | 0.1327 | -0.0203 |
| do 0.2784 | 31 | 25.4 % | 61.3 | 0.3135 | 0.1034 | -0.0496 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.1530 % | 0.0628 % ± 0.0870 | +1.04 | 83.8 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.1530 % | 0.0774 % ± 0.0916 | +0.83 | 80.3 |

Naznak, ale nie dokaz (1.0 sigma, percentil 83.8). Take rozdiely nahoda robi bezne.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 36 | 2.5 | 63.9 | 0.4253 | 96 |
| 2022-12 - 2024-03 | 27 | 1.8 | 48.1 | -0.0386 | 13 |
| 2024-03 - 2025-06 | 26 | 1.8 | 53.9 | 0.3341 | 84 |
| 2025-06 - 2026-08 | 33 | 2.2 | 60.6 | -0.0208 | 10 |

Hranice pre úsek veľkosti posledného obdobia: -0.0709 až +0.4252 % (medián 0.1537).

**DRZI** — posledné obdobie (2025-06 - 2026-08) je na 10. percentile, teda v medziach -0.0709 až +0.4252 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 5** — 2024-04-22T17:15 až 2024-07-10T20:00, spolu +3275.27.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-04-22T17:15 | 2024-04-24T20:00 | +467.78 | +1.35 | `session_end` |
| 2 | 2024-05-20T17:15 | 2024-05-22T20:00 | +13.18 | +0.04 | `session_end` |
| 3 | 2024-06-10T17:15 | 2024-06-12T20:00 | +784.15 | +2.05 | `session_end` |
| 4 | 2024-06-24T17:15 | 2024-06-26T20:00 | +260.60 | +0.66 | `session_end` |
| 5 | 2024-07-01T17:15 | 2024-07-10T20:00 | +1749.57 | +4.37 | `session_end` |

**Straty za sebou: 4** — 2023-11-27T17:15 až 2024-02-28T20:00, spolu -1674.85, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-11-27T17:15 | 2023-11-29T20:00 | -39.63 | -0.12 | `session_end` |
| 2 | 2024-01-29T17:15 | 2024-01-31T20:00 | -583.22 | -1.66 | `session_end` |
| 3 | 2024-02-19T17:15 | 2024-02-21T20:00 | -773.23 | -2.17 | `session_end` |
| 4 | 2024-02-26T17:15 | 2024-02-28T20:00 | -278.76 | -0.77 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.1530 %**, medián 0.1540 %, 90 % interval 0.0248–0.2913 %
- P(edge > poplatok) = **97.4 %**
- max drawdown: medián 25.3 %, 95. percentil 55.7 %, najhorší 100.0 %
- najdlhšia séria strát: medián 4, 95. percentil 6 obchodov
- pravdepodobnosť ruiny účtu: 0.2 %

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
<!-- POSUDOK cisla=62e155ac -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na MNQ, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Kalendárny jav (pondelok po červenom piatku → streda), ~25 obchodov za rok — pre smernicu (150 / rok) z princípu nevhodný, skôr doplnok portfólia.
2. **Má potenciál?** Zisková v 4 z 5 okien, 122 obchodov (~24 za rok), break-even 0.1530 % (nad poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 57.38 % pri payoffe 1.088. Odložený rok 25/26: -11.61 % PnL, break-even -0.0404 %. Kladné okná sú skôr vlastnosť vzorky ako stabilný jav.
3. **Čo dorobiť.** Bez stopu: poistka 10 % je len technická; pre live treba stop v % alebo ATR. Sviatky (pondelok zatvorené) predloha nerieši.
4. **Čo otestovať ďalej.** Smernica ho pre počet obchodov nepustí; ako doplnok portfólia `cli portfolio` s inými stratégiami a test proti náhode na dňoch v týždni.
5. **Použiteľné?** **Pre smernicu nie** (≈25 obchodov za rok, hranica 150); ako kalendárny doplnok portfólia áno — zisková vo väčšine okien a break-even vysoko nad poplatkom.
6. **Čo by som pridal.** Rovnaký jav aj pre pozitívny piatok (short alebo bez obchodu) a výstup už v utorok — overiť, kde je drift najsilnejší.

<!-- POSUDOK KONIEC -->
