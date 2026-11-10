# Základná analytika — MTK ZONE (SD zóny z volume) (`mtkzone`)

Zmerané 2026-11-10 na `MNQ/USD` 3m, engine `multicharts`, poplatok 0.0027 % na stranu (1.5 tick na stranu pri cene 13914.2 = 0.00270 %; odhad: polovica spreadu 0,5 ticku + provizia ~0,5 $ na stranu = 1 tick, spolu 1,5 ticku (0,375 bodu); spread z ohlcv dat nevidno), profil `mnq_databento_3m`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy mtkzone \
   --profile mnq_databento_3m \
   --pair MNQ/USD \
   --timeframe 3m
```

## V čom je dobrá

- 11477 obchodov spolu — na štatistiku dosť
- odlíšiteľná od náhody (+2.1 sigma proti náhodnému vstupu)
- charakter: scalping (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 0 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20231001-20241001, 20240904-20250904, 20250904-20260904 v strate)
- break-even 0.0003 % je pod poplatkom 0.0027 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 0 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 100.0 % (namerané 100.0 % medián) — na účet to treba mať
- pravdepodobnosť ruiny účtu 99.2 % pri riziku, s akým beh bežal
- POZOR NA TREND: každé z 4 období je horšie než predchádzajúce (sklon -0.0009 na obdobie). Posledné je ešte v medziach (20. percentil), takže test úpadok nepotvrdzuje — ale rad sa sám od seba zoradí zriedka. Zopakuj to, keď pribudnú dáta.

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 2406 | -7.81 | 0.0021 | 21.2 | 49.0 | +12/-12 | `20261110-190503-f9a2e3` |
| 20221001-20231001 | 2428 | -18.08 | 0.0013 | 30.3 | 48.4 | +9/-9 | `20261110-190513-cd9877` |
| 20231001-20241001 | 2432 | -66.92 | -0.0012 | 68.2 | 47.4 | +11/-11 | `20261110-190519-3e08cf` |
| 20240904-20250904 | 2305 | -37.05 | 0.0008 | 44.2 | 50.0 | +9/-9 | `20261110-190525-dd2612` |
| 20250904-20260904 | 2085 | -73.65 | -0.0006 | 77.2 | 46.6 | +9/-9 | `20261110-190531-ff885c` |

Zisková v **0 z 5** okien, obchodov spolu 11477, break-even celkom 0.0003 %. Okná sa prekrývajú, 179 obchodov započítaných dvakrát vypadlo.

## Charakter

**Scalping** (istota dobrá)

- vstup proti poslednému pohybu (-1.39 ATR za 5 barov)
- medián držania 1 barov grafu
- winrate 48.35 %, payoff 0.953
- 6.38 obchodov za deň
- šikmosť výnosov +0.363

- **Čo je normálne:** Edge na obchod je rádovo taký veľký ako poplatok. Break-even poplatok je tu jediné číslo, ktoré niečo znamená.
- **Na čo pozor:** Poplatky a slippage rozhodujú o všetkom. Beh s `--fee 0` je pri tomto type úplne bezcenný.
- **Čo ladiť:** Break-even poplatok, nie PnL. A počet obchodov — menej lepších je zvyčajne viac.

Výstupy: `stop_loss` 51.6 %, `take_profit` 48.4 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0011 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 11 h – 14 h | 3624 | 31.6 % | 44.9 | -0.0019 | 0.0014 | +0.0011 |
| do 7 h | 3714 | 32.4 % | 50.3 | 0.0002 | 0.0004 | +0.0001 |
| 7 h – 11 h | 2078 | 18.1 % | 49.2 | 0.0002 | 0.0003 | +0.0000 |
| nad 14 h | 2061 | 18.0 % | 49.9 | 0.0046 | -0.0006 | -0.0009 |

**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 6888 | 60.0 % | 48.4 | -0.0002 | 0.0010 | +0.0007 |
| proti trendu | 4589 | 40.0 % | 48.3 | 0.0010 | -0.0002 | -0.0005 |

**Smer** (riadi `tradeDirection`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| short | 6166 | 53.7 % | 48.2 | -0.0002 | 0.0009 | +0.0006 |
| long | 5311 | 46.3 % | 48.5 | 0.0009 | -0.0002 | -0.0005 |

Parametre, ktorými sa dá s tým niečo spraviť: `rrRatio`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0003 % | -0.0004 % ± 0.0003 | +2.14 | 98.4 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0003 % | -0.0004 % ± 0.0003 | +2.14 | 98.4 |

Edge je odlisitelny od nahody (2.1 sigma, percentil 98.4).

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 2935 | 199.0 | 49.1 | 0.0023 | 97 |
| 2022-12 - 2024-03 | 3038 | 206.0 | 48.0 | 0.0004 | 55 |
| 2024-03 - 2025-06 | 2836 | 192.3 | 49.0 | 0.0001 | 40 |
| 2025-06 - 2026-09 | 2668 | 180.9 | 47.3 | -0.0006 | 20 |

Hranice pre úsek veľkosti posledného obdobia: -0.0015 až +0.0021 % (medián 0.0003).

**POZOR NA TREND** — každé z 4 období je horšie než predchádzajúce (sklon -0.0009 na obdobie). Posledné je ešte v medziach (20. percentil), takže test úpadok nepotvrdzuje — ale rad sa sám od seba zoradí zriedka. Zopakuj to, keď pribudnú dáta.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 12** — 2021-11-25T11:25 až 2021-11-26T09:01, spolu +207.83.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2021-11-25T11:25 | 2021-11-25T11:27 | +8.23 | +0.03 | `take_profit` |
| 2 | 2021-11-25T12:38 | 2021-11-25T12:42 | +8.23 | +0.03 | `take_profit` |
| 3 | 2021-11-25T12:57 | 2021-11-25T13:01 | +6.23 | +0.02 | `take_profit` |
| 4 | 2021-11-25T14:02 | 2021-11-25T14:11 | +12.73 | +0.04 | `take_profit` |
| 5 | 2021-11-25T14:29 | 2021-11-25T14:33 | +11.73 | +0.04 | `take_profit` |
| 6 | 2021-11-25T15:51 | 2021-11-25T15:52 | +8.23 | +0.03 | `take_profit` |
| 7 | 2021-11-25T17:01 | 2021-11-25T17:08 | +6.73 | +0.02 | `take_profit` |
| 8 | 2021-11-25T23:26 | 2021-11-25T23:27 | +12.73 | +0.04 | `take_profit` |
| 9 | 2021-11-26T00:16 | 2021-11-26T00:20 | +21.74 | +0.07 | `take_profit` |
| 10 | 2021-11-26T01:26 | 2021-11-26T01:37 | +22.74 | +0.07 | `take_profit` |
| 11 | 2021-11-26T03:13 | 2021-11-26T03:40 | +41.74 | +0.13 | `take_profit` |
| 12 | 2021-11-26T08:47 | 2021-11-26T09:01 | +46.75 | +0.14 | `take_profit` |

**Straty za sebou: 12** — 2021-10-12T07:10 až 2021-10-13T11:35, spolu -228.99.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2021-10-12T07:10 | 2021-10-12T07:11 | -24.58 | -0.08 | `stop_loss` |
| 2 | 2021-10-12T08:45 | 2021-10-12T08:48 | -20.58 | -0.07 | `stop_loss` |
| 3 | 2021-10-12T11:36 | 2021-10-12T11:37 | -10.09 | -0.03 | `stop_loss` |
| 4 | 2021-10-12T12:43 | 2021-10-12T12:43 | -9.59 | -0.03 | `stop_loss` |
| 5 | 2021-10-12T13:30 | 2021-10-12T13:31 | -32.59 | -0.11 | `stop_loss` |
| 6 | 2021-10-12T18:36 | 2021-10-12T18:57 | -26.08 | -0.09 | `stop_loss` |
| 7 | 2021-10-12T20:03 | 2021-10-12T20:27 | -31.57 | -0.11 | `stop_loss` |
| 8 | 2021-10-13T04:08 | 2021-10-13T04:59 | -24.58 | -0.08 | `stop_loss` |
| 9 | 2021-10-13T07:01 | 2021-10-13T07:02 | -6.08 | -0.02 | `stop_loss` |
| 10 | 2021-10-13T07:30 | 2021-10-13T07:33 | -13.58 | -0.05 | `stop_loss` |
| 11 | 2021-10-13T10:34 | 2021-10-13T10:38 | -13.09 | -0.04 | `stop_loss` |
| 12 | 2021-10-13T11:26 | 2021-10-13T11:35 | -16.59 | -0.06 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0003 %**, medián 0.0003 %, 90 % interval -0.0005–0.0012 %
- P(edge > poplatok) = **0.0 %**
- max drawdown: medián 100.0 %, 95. percentil 100.0 %, najhorší 100.0 %
- najdlhšia séria strát: medián 13, 95. percentil 17 obchodov
- pravdepodobnosť ruiny účtu: 99.2 %

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
<!-- POSUDOK cisla=9c8c7b89 -->

1. **Na čo sa to hodí a na čo nie** — východiskový profil (graf 3m, zóny 5m, min. 2 potvrdenia, limit na zónu, RR 1) je na MNQ čistý scalping: ~6 obchodov denne, medián držania 1 bar, winrate 48 %, payoff 0,95. Na účte s poplatkom 1,5 ticku na stranu sa to nedá obchodovať — break-even 0,0003 % je desaťkrát pod poplatkom 0,0027 %. Na CFD so spreadom by to bolo ešte horšie.
2. **Má to potenciál?** Slabý, ale nie nulový: vstupy sú odlíšiteľné od náhody (+2,1 sigma, percentil 98), takže zóny niečo nesú. Edge na obchod je však rádovo veľkosti poplatku a po rokoch klesá (0,0023 → −0,0006 %). Zisková v 0 z 5 okien — v tejto podobe je to vlastnosť vzorky, nie použiteľný jav.
3. **Čo treba dorobiť** — menej a lepších obchodov: prísnejšie zóny (minConf 3, vyšší minScore, menej aktívnych zón), vstupy cez IBS / pin bar namiesto slepého limitu na hranu, väčšie riziko na obchod (širšia zóna z 15m), aby poplatok zjedol menšiu časť. Hodiny 11–14 UTC (pred otvorením NY) majú najhorší break-even.
4. **Čo otestovať ďalej** — hľadanie podľa smernice (beží na Mac mini do 11. 11. 18:00) cez skupiny minConf / maxZones / modely / RR / VWAP a seansa; rozhodne, či existuje nastavenie s ≥ 75 obch./rok, PF ≥ 1,3 v každom roku a odloženým rokom. Ak nie, stratégia ide preč.
5. **Je to použiteľné, alebo je to o ničom?** Východiskový profil je o ničom (strata v každom roku, P(edge > poplatok) = 0 %). Použiteľnosť rozhodne až smernica; dovtedy na trh nie.
6. **Čo by som pridal** — vstup len na prvý návrat do čerstvej zóny vytvorenej v NY seanse (9:30–16:00) a cieľ na protiľahlú zónu alebo POC namiesto pevného RR; scalp s RR 1 a 6 obchodmi denne poplatok neunesie.

<!-- POSUDOK KONIEC -->
