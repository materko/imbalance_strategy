# Základná analytika — T-MEAN REVERSION 1.0 (ES) (`tmres`)

Zmerané 2026-10-31 na `ES/USD` 15m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `/Users/martin/IBS/.nightsearch/base_tmres.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy tmres \
   --profile /Users/martin/IBS/.nightsearch/base_tmres.json \
   --pair ES/USD \
   --timeframe 15m \
   --fee 1.755e-05
```

## V čom je dobrá

- zisková v 5 z 5 referenčných okien
- break-even 0.1269 % je nad poplatkom 0.0018 % (rezerva +0.1251 bodu)
- edge nad poplatkom v 97 % bootstrapových vzoriek
- edge drží aj v poslednom období (2025-06 - 2026-08 na 19. percentile toho, čo stratégia vyrobí sama od seba)

## Kde má chyby

- 95. percentil max drawdownu 100.0 % (namerané 75.5 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 35.2 % pri riziku, s akým beh bežal
- proti náhode len +1.1 sigma: náznak, nie dôkaz
- charakter: formácia / štruktúra (istota priemerná) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne
- 99.2 % obchodov končí na čase (session_end), nie na pláne — to je nastavenie okna seansy, nie vlastnosť vstupu
- najhoršia skupina 'do 100 R' vlastnosti 'Plánovaný RR': 86 obchodov (69.9 %), bez nej by break-even bol o +0.1487 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 29 | +387.80 | 0.3112 | 69.9 | 58.6 | +4/-4 | `20261031-085104-715314` |
| 20221001-20231001 | 23 | +27.45 | 0.0305 | 40.4 | 56.5 | +4/-2 | `20261031-085107-aff520` |
| 20231001-20241001 | 25 | +103.65 | 0.0834 | 79.6 | 48.0 | +3/-5 | `20261031-085110-b43ea4` |
| 20240904-20250904 | 20 | +305.65 | 0.2569 | 70.3 | 55.0 | +4/-5 | `20261031-085113-b52d30` |
| 20250904-20260904 | 28 | +35.18 | 0.0197 | 123.2 | 53.6 | +5/-4 | `20261031-085120-171455` |

Zisková v **5 z 5** okien, obchodov spolu 123, break-even celkom 0.1269 %. Okná sa prekrývajú, 2 obchodov započítaných dvakrát vypadlo.

## Charakter

**Formácia / štruktúra** (istota priemerná)

- vstup bez jasného smeru pohybu (+0.00 ATR za 5 barov)
- medián držania 203 barov grafu
- winrate 53.66 %, payoff 1.359
- 0.07 obchodov za deň
- šikmosť výnosov +1.293

- **Čo je normálne:** Zmes: časť obchodov sa chová ako prerazenie, časť ako návrat. Priemer preto o jednotlivom obchode nehovorí veľa.
- **Na čo pozor:** Práve pri tomto type sa najviac oplatí rozdeliť obchody na skupiny (`tester.analytics`) — priemer skrýva dve rôzne populácie.
- **Čo ladiť:** Podmienky vstupu (ktoré modely/formácie zapnuté) a potom až výstup.

Výstupy: `session_end` 99.2 %, `force_exit` 0.8 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 'do 100 R' vlastnosti 'Plánovaný RR': 86 obchodov (69.9 %), break-even 0.0626 % oproti 0.1269 % celku. Bez nej by break-even bol 0.2756 % (+0.1487). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**Plánovaný RR**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 100 R | 86 | 69.9 % | 50.0 | 0.0626 | 0.2756 | +0.1487 |
| 100 R – 100.04 R | 14 | 11.4 % | 71.4 | 0.1576 | 0.1217 | -0.0052 |
| nad 100.04 R | 23 | 18.7 % | 56.5 | 0.3843 | 0.0789 | -0.0480 |

**Vzdialenosť stopu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 9.9996 % – 10.0017 % | 34 | 27.6 % | 38.2 | -0.1186 | 0.2274 | +0.1005 |
| do 9.9973 % | 31 | 25.2 % | 61.3 | 0.2048 | 0.1020 | -0.0249 |
| nad 10.0017 % | 27 | 22.0 % | 55.6 | 0.2053 | 0.1058 | -0.0211 |
| 9.9973 % – 9.9996 % | 31 | 25.2 % | 61.3 | 0.2675 | 0.0789 | -0.0480 |

**Volatilita voči normálu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 1.49 – 1.935 | 31 | 25.2 % | 38.7 | -0.0704 | 0.1930 | +0.0661 |
| 1.213 – 1.49 | 31 | 25.2 % | 58.1 | 0.1029 | 0.1346 | +0.0077 |
| do 1.213 | 31 | 25.2 % | 61.3 | 0.2099 | 0.0982 | -0.0287 |
| nad 1.935 | 30 | 24.4 % | 56.7 | 0.2629 | 0.0817 | -0.0452 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.1269 % | 0.0477 % ± 0.0689 | +1.15 | 86.7 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.1269 % | 0.0575 % ± 0.0708 | +0.98 | 82.9 |

Naznak, ale nie dokaz (1.1 sigma, percentil 86.7). Take rozdiely nahoda robi bezne.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 36 | 2.5 | 61.1 | 0.3296 | 96 |
| 2022-12 - 2024-03 | 28 | 1.9 | 42.9 | -0.0761 | 6 |
| 2024-03 - 2025-06 | 25 | 1.7 | 56.0 | 0.2801 | 84 |
| 2025-06 - 2026-08 | 34 | 2.3 | 52.9 | 0.0114 | 19 |

Hranice pre úsek veľkosti posledného obdobia: -0.0708 až +0.3490 % (medián 0.1216).

**DRZI** — posledné obdobie (2025-06 - 2026-08) je na 19. percentile, teda v medziach -0.0708 až +0.3490 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 5** — 2026-03-23T17:15 až 2026-05-20T20:00, spolu +31326.76.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2026-03-23T17:15 | 2026-03-25T20:00 | +538.35 | +0.16 | `session_end` |
| 2 | 2026-03-30T17:15 | 2026-04-01T20:00 | +10476.06 | +3.27 | `session_end` |
| 3 | 2026-04-06T17:15 | 2026-04-08T20:00 | +9800.70 | +2.96 | `session_end` |
| 4 | 2026-05-04T17:15 | 2026-05-06T20:00 | +8487.17 | +2.35 | `session_end` |
| 5 | 2026-05-18T17:15 | 2026-05-20T20:00 | +2024.46 | +0.55 | `session_end` |

**Straty za sebou: 5** — 2023-09-18T17:15 až 2023-10-25T20:00, spolu -11913.16, rovnako dlhých sérií 3.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2023-09-18T17:15 | 2023-09-20T20:00 | -3232.86 | -1.43 | `session_end` |
| 2 | 2023-09-25T17:15 | 2023-09-27T20:00 | -2707.63 | -1.24 | `session_end` |
| 3 | 2023-10-02T17:15 | 2023-10-04T20:00 | -182.54 | -0.08 | `session_end` |
| 4 | 2023-10-16T17:15 | 2023-10-18T20:00 | -2995.19 | -1.36 | `session_end` |
| 5 | 2023-10-23T17:15 | 2023-10-25T20:00 | -2794.95 | -1.31 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.1269 %**, medián 0.1269 %, 90 % interval 0.0153–0.2446 %
- P(edge > poplatok) = **96.8 %**
- max drawdown: medián 75.5 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 7, 95. percentil 9 obchodov
- pravdepodobnosť ruiny účtu: 35.2 %

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
<!-- POSUDOK cisla=0450db0b -->

**Posudok (31. 10. 2026, prepis roboquant šablóny 1 : 1 na ES, defaulty predlohy, 1 kontrakt, poplatok 0,0018 %.)**

1. **Na čo sa hodí a na čo nie.** Kalendárny jav (pondelok po červenom piatku → streda), ~25 obchodov za rok — pre smernicu (150 / rok) z princípu nevhodný, skôr doplnok portfólia. Tu na ES — rovnaká logika ako MNQ, prahy v ATR sa prispôsobia.
2. **Má potenciál?** Zisková v 5 z 5 okien, 123 obchodov (~25 za rok), break-even 0.1269 % (nad poplatkom 0,0018 %), od náhody neodlíšiteľná; WR 53.66 % pri payoffe 1.359. Odložený rok 25/26: +35.18 % PnL, break-even 0.0197 %. Jav je skôr skutočný ako vlastnosť vzorky.
3. **Čo dorobiť.** Bez stopu: poistka 10 % je len technická; pre live treba stop v % alebo ATR. Sviatky (pondelok zatvorené) predloha nerieši.
4. **Čo otestovať ďalej.** Smernica ho pre počet obchodov nepustí; ako doplnok portfólia `cli portfolio` s inými stratégiami a test proti náhode na dňoch v týždni.
5. **Použiteľné?** **Pre smernicu nie** (≈25 obchodov za rok, hranica 150); ako kalendárny doplnok portfólia áno — zisková vo väčšine okien a break-even vysoko nad poplatkom.
6. **Čo by som pridal.** Rovnaký jav aj pre pozitívny piatok (short alebo bez obchodu) a výstup už v utorok — overiť, kde je drift najsilnejší.

<!-- POSUDOK KONIEC -->
