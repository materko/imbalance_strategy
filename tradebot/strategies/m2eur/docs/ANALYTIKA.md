# Základná analytika — M2 (6E) (`m2eur`)

Zmerané 2026-10-28 na `6E/USD` 1m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `6e_databento_1m`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy m2eur \
   --profile 6e_databento_1m \
   --pair 6E/USD \
   --timeframe 1m \
   --fee 1.755e-05 \
   --wallet 100000
```

## V čom je dobrá

- 36133 obchodov spolu — na štatistiku dosť
- charakter: scalping (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 0 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20231001-20241001, 20240904-20250904, 20250904-20260904 v strate)
- break-even -0.0000 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 0 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 100.0 % (namerané 100.0 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 100.0 % pri riziku, s akým beh bežal
- nie je lepšia než náhodný vstup za tých istých pravidiel (-1.8 sigma) — výber vstupu nepridáva nič

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 7667 | -977.44 | -0.0003 | 970.6 | 31.8 | +6/-21 | `20261028-154104-09d40a` |
| 20221001-20231001 | 7484 | -804.77 | 0.0001 | 804.8 | 33.4 | +6/-20 | `20261028-154111-6442ce` |
| 20231001-20241001 | 6754 | -837.63 | 0.0002 | 831.7 | 33.7 | +7/-21 | `20261028-154117-3a1308` |
| 20240904-20250904 | 7559 | -922.21 | -0.0001 | 912.8 | 32.7 | +8/-21 | `20261028-154124-98be29` |
| 20250904-20260904 | 7213 | -1104.89 | -0.0001 | 1100.3 | 32.3 | +6/-29 | `20261028-154131-6077f5` |

Zisková v **0 z 5** okien, obchodov spolu 36133, break-even celkom -0.0000 %. Okná sa prekrývajú, 544 obchodov započítaných dvakrát vypadlo.

## Charakter

**Scalping** (istota dobrá)

- vstup bez jasného smeru pohybu (+0.00 ATR za 5 barov)
- medián držania 3 barov grafu
- winrate 32.78 %, payoff 1.426
- 20.09 obchodov za deň
- šikmosť výnosov +2.405

- **Čo je normálne:** Edge na obchod je rádovo taký veľký ako poplatok. Break-even poplatok je tu jediné číslo, ktoré niečo znamená.
- **Na čo pozor:** Poplatky a slippage rozhodujú o všetkom. Beh s `--fee 0` je pri tomto type úplne bezcenný.
- **Čo ladiť:** Break-even poplatok, nie PnL. A počet obchodov — menej lepších je zvyčajne viac.

Výstupy: `stop_loss` 67.2 %, `take_profit` 32.8 %, `force_exit` 0 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0007 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Plánovaný RR**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 2 R | 35411 | 98.1 % | 33.0 | -0.0001 | 0.0007 | +0.0007 |
| nad 2 R | 684 | 1.9 % | 23.7 | 0.0007 | -0.0001 | -0.0001 |

**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| do 6 h | 9454 | 26.2 % | 31.6 | -0.0002 | 0.0001 | +0.0001 |
| 6 h – 12 h | 10008 | 27.7 % | 32.4 | -0.0002 | 0.0000 | +0.0000 |
| 12 h – 17 h | 9458 | 26.2 % | 33.9 | 0.0002 | -0.0001 | -0.0001 |
| nad 17 h | 7213 | 20.0 % | 33.4 | 0.0002 | -0.0001 | -0.0001 |

**Smer**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| short | 18398 | 50.9 % | 32.7 | -0.0001 | -0.0000 | +0.0000 |
| long | 17735 | 49.1 % | 32.9 | -0.0000 | -0.0001 | -0.0001 |

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | -0.0000 % | 0.0001 % ± 0.0001 | -1.75 | 4.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | -0.0000 % | 0.0001 % ± 0.0001 | -1.75 | 4.0 |

HORSIE nez nahoda (-1.8 sigma). Nahodny vstup za tych istych pravidiel dava lepsi vysledok - vyber vstupu vysledku skodi.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 9507 | 644.5 | 31.7 | -0.0003 | 1 |
| 2022-12 - 2024-03 | 8857 | 600.5 | 33.7 | 0.0002 | 98 |
| 2024-03 - 2025-06 | 8769 | 594.5 | 33.5 | 0.0001 | 91 |
| 2025-06 - 2026-09 | 9000 | 610.2 | 32.4 | -0.0001 | 27 |

Hranice pre úsek veľkosti posledného obdobia: -0.0002 až +0.0001 % (medián -0.0000).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 27. percentile, teda v medziach -0.0002 až +0.0001 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 8** — 2024-10-02T23:37 až 2024-10-03T01:48, spolu +6445.46.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-10-02T23:37 | 2024-10-03T00:01 | +805.58 | +0.01 | `take_profit` |
| 2 | 2024-10-03T00:13 | 2024-10-03T00:16 | +805.61 | +0.01 | `take_profit` |
| 3 | 2024-10-03T00:34 | 2024-10-03T00:44 | +805.67 | +0.01 | `take_profit` |
| 4 | 2024-10-03T00:46 | 2024-10-03T00:47 | +805.70 | +0.01 | `take_profit` |
| 5 | 2024-10-03T00:49 | 2024-10-03T00:50 | +805.71 | +0.01 | `take_profit` |
| 6 | 2024-10-03T01:16 | 2024-10-03T01:20 | +805.72 | +0.01 | `take_profit` |
| 7 | 2024-10-03T01:36 | 2024-10-03T01:38 | +805.73 | +0.01 | `take_profit` |
| 8 | 2024-10-03T01:45 | 2024-10-03T01:48 | +805.74 | +0.01 | `take_profit` |

**Straty za sebou: 29** — 2025-12-19T08:13 až 2025-12-22T11:37, spolu -19379.73.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2025-12-19T08:13 | 2025-12-19T08:15 | -621.67 | -0.02 | `stop_loss` |
| 2 | 2025-12-19T08:40 | 2025-12-19T08:40 | -706.40 | -0.01 | `stop_loss` |
| 3 | 2025-12-19T08:50 | 2025-12-19T08:54 | -728.19 | -0.02 | `stop_loss` |
| 4 | 2025-12-19T09:04 | 2025-12-19T09:04 | -706.43 | -0.01 | `stop_loss` |
| 5 | 2025-12-19T09:16 | 2025-12-19T09:23 | -621.70 | -0.02 | `stop_loss` |
| 6 | 2025-12-19T09:53 | 2025-12-19T10:15 | -554.60 | -0.03 | `stop_loss` |
| 7 | 2025-12-19T10:47 | 2025-12-19T10:49 | -621.67 | -0.02 | `stop_loss` |
| 8 | 2025-12-19T11:38 | 2025-12-19T11:52 | -582.56 | -0.02 | `stop_loss` |
| 9 | 2025-12-19T12:11 | 2025-12-19T12:14 | -621.66 | -0.02 | `stop_loss` |
| 10 | 2025-12-19T12:41 | 2025-12-19T12:42 | -706.42 | -0.01 | `stop_loss` |
| 11 | 2025-12-19T13:02 | 2025-12-19T13:02 | -706.37 | -0.01 | `stop_loss` |
| 12 | 2025-12-19T13:29 | 2025-12-19T13:30 | -603.20 | -0.02 | `stop_loss` |
| 13 | 2025-12-19T21:57 | 2025-12-21T23:00 | -1271.65 | -0.03 | `stop_loss` |
| 14 | 2025-12-22T00:01 | 2025-12-22T00:02 | -706.38 | -0.01 | `stop_loss` |
| 15 | 2025-12-22T00:07 | 2025-12-22T00:07 | -706.42 | -0.01 | `stop_loss` |
| 16 | 2025-12-22T00:19 | 2025-12-22T00:26 | -603.21 | -0.02 | `stop_loss` |
| 17 | 2025-12-22T00:31 | 2025-12-22T00:54 | -603.21 | -0.02 | `stop_loss` |
| 18 | 2025-12-22T03:29 | 2025-12-22T03:30 | -706.44 | -0.01 | `stop_loss` |
| 19 | 2025-12-22T08:58 | 2025-12-22T09:07 | -582.72 | -0.02 | `stop_loss` |
| 20 | 2025-12-22T09:13 | 2025-12-22T09:16 | -621.88 | -0.02 | `stop_loss` |
| 21 | 2025-12-22T09:25 | 2025-12-22T09:26 | -621.84 | -0.02 | `stop_loss` |
| 22 | 2025-12-22T09:37 | 2025-12-22T09:37 | -706.73 | -0.01 | `stop_loss` |
| 23 | 2025-12-22T09:48 | 2025-12-22T09:50 | -603.35 | -0.02 | `stop_loss` |
| 24 | 2025-12-22T09:53 | 2025-12-22T09:55 | -706.70 | -0.01 | `stop_loss` |
| 25 | 2025-12-22T10:02 | 2025-12-22T10:02 | -706.70 | -0.01 | `stop_loss` |
| 26 | 2025-12-22T10:10 | 2025-12-22T10:12 | -603.39 | -0.02 | `stop_loss` |
| 27 | 2025-12-22T10:24 | 2025-12-22T10:40 | -603.40 | -0.02 | `stop_loss` |
| 28 | 2025-12-22T10:54 | 2025-12-22T10:54 | -706.76 | -0.01 | `stop_loss` |
| 29 | 2025-12-22T11:09 | 2025-12-22T11:37 | -538.10 | -0.03 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **-0.0000 %**, medián -0.0000 %, 90 % interval -0.0001–0.0001 %
- P(edge > poplatok) = **0.0 %**
- max drawdown: medián 100.0 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 24, 95. percentil 31 obchodov
- pravdepodobnosť ruiny účtu: 100.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **2** na obchod pri účte 100 000

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
<!-- POSUDOK cisla=e8bcdcd7 -->

**Posudok (28. 10. 2026, pravidlá podľa podkladov METODA_2 / advanced, 6E 1m, RR 2, EMA 20–1200, rozšírenia kvality vypnuté).**

1. **Na čo sa hodí a na čo nie.** Na 1m je na 6E M2 každých pár minút (~7 300 obchodov za rok) so stopom na pár tickov. Pri tick 0,00005 je poplatok väčší než edge, takže na takýto skalp sa pravidlá v tejto podobe nehodia.
2. **Má potenciál?** V základnej podobe nie. Zisková je v 0 z 5 okien, break-even je okolo nuly a proti náhodnému vstupu vychádza −1,8 sigma: výber vstupu nepridáva nič. WR 33 % pri RR 2 je náhoda.
3. **Čo dorobiť.** Hotové 28. 10. sú filtre kvality, predvolene vypnuté: potvrdenie hneď po M2 (`confirmMaxBars`), impulz potvrdenia v ATR (`minImpulseAtr`), M2 na extréme (`swingBars`), riziko v ATR (`minRiskAtr` / `maxRiskAtr`), hĺbka limitky (`entryPct`) a zrušenie limitky pri dosiahnutí cieľa (`cancelAtTarget`).
4. **Čo otestovať ďalej.** Hľadanie podľa smernice (`.nightsearch/glsearch.py`, kľúč `m2eur`) cez všetky TF 1–15m a tieto filtre. Rozhodne PF ≥ 1,3 na ladení pri ≥ 150 obchodoch za rok, žiadny rok pod 0,9 a potom odložený rok.
5. **Použiteľné?** Pravidlá podkladu samy o sebe na 6E **nie**. Použiteľné to bude, len ak filtre kvality nájdu stabilnú podmnožinu na všetkých rokoch.
6. **Čo by som pridal.** Vstupy len v Londýne a v NY dopoludní, keď má 6E objem, a cieľ na poslednú likviditu (swing) namiesto pevného RR.

<!-- POSUDOK KONIEC -->
