# Základná analytika — Scalping 3MA + RSI + fraktál 1.0 (`scalp3ma`)

Zmerané 2026-10-26 na `MNQ/USD` 5m, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/scalp3ma/configs/mnq_databento_5m.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy scalp3ma \
   --profile tradebot/strategies/scalp3ma/configs/mnq_databento_5m.json \
   --pair MNQ/USD \
   --timeframe 5m \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- 1279 obchodov spolu — na štatistiku dosť
- drawdown drží: 95. percentil 24.0 %
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť
- žiadna vopred známa vlastnosť obchodov výsledok výrazne nekazí — niet čo filtrovať, ladiť sa dá len parametrami

## Kde má chyby

- zisková v 1 z 5 referenčných okien (20211001-20221001, 20221001-20231001, 20231001-20241001, 20240904-20250904 v strate)
- break-even 0.0005 % je pod poplatkom 0.0018 % — pri tomto poplatku je to strata, nech PnL ukazuje čokoľvek
- edge nad poplatkom len v 4 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- proti náhode len +1.0 sigma: náznak, nie dôkaz

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 259 | -4.62 | -0.0016 | 6.9 | 25.5 | +5/-20 | `20261026-131629-400377` |
| 20221001-20231001 | 260 | -3.53 | -0.0001 | 4.4 | 26.9 | +5/-13 | `20261026-131635-e10dd2` |
| 20231001-20241001 | 260 | -0.34 | 0.0016 | 2.7 | 28.5 | +3/-17 | `20261026-131641-78e6a4` |
| 20240904-20250904 | 258 | -3.30 | 0.0000 | 4.6 | 25.6 | +4/-16 | `20261026-131647-511471` |
| 20250904-20260904 | 261 | +0.48 | 0.0021 | 3.2 | 28.4 | +5/-20 | `20261026-131653-7c7a19` |

Zisková v **1 z 5** okien, obchodov spolu 1279, break-even celkom 0.0005 %. Okná sa prekrývajú, 19 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+0.56 ATR za 5 barov)
- medián držania 2.4 barov grafu
- winrate 26.97 %, payoff 2.41
- 0.71 obchodov za deň
- šikmosť výnosov +1.401

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 42.3 %, `take_profit` 25.3 %, `trailing_stop` 21.7 %, `session_end` 10.6 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Ziadna vopred zname vlastnost vysledok vyrazne nekazi (najviac +0.0015 % break-even). Filter ani model tu nema co najst - hladaj radsej v parametroch (hyperopt) alebo v inom podklade.


**Smer** (riadi `tradeDirection`)

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| long | 729 | 57.0 % | 25.4 | -0.0003 | 0.0020 | +0.0015 |
| short | 550 | 43.0 % | 29.1 | 0.0020 | -0.0003 | -0.0008 |

**Volatilita voči normálu**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.488 – 0.611 | 321 | 25.1 % | 20.2 | -0.0028 | 0.0019 | +0.0014 |
| do 0.488 | 320 | 25.0 % | 30.0 | 0.0017 | -0.0001 | -0.0006 |
| 0.611 – 0.812 | 319 | 24.9 % | 28.2 | 0.0019 | 0.0001 | -0.0004 |
| nad 0.812 | 319 | 24.9 % | 29.5 | 0.0022 | 0.0003 | -0.0002 |

**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.1136 – 0.2096 | 320 | 25.0 % | 22.5 | -0.0020 | 0.0014 | +0.0009 |
| do 0.0513 | 320 | 25.0 % | 27.2 | 0.0001 | 0.0007 | +0.0002 |
| 0.0513 – 0.1136 | 320 | 25.0 % | 27.5 | 0.0014 | 0.0002 | -0.0003 |
| nad 0.2096 | 319 | 24.9 % | 30.7 | 0.0029 | -0.0001 | -0.0006 |

Parametre, ktorými sa dá s tým niečo spraviť: `requireMaOrder`, `rrRatio`, `rsiExit`, `slAtr`, `tradeDirection`, `tradeStartH`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0008 % | -0.0002 % ± 0.0010 | +1.00 | 83.5 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0008 % | -0.0003 % ± 0.0010 | +1.12 | 86.5 |

Naznak, ale nie dokaz (1.0 sigma, percentil 83.5). Take rozdiely nahoda robi bezne.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 319 | 21.6 | 25.4 | -0.0019 | 3 |
| 2022-12 - 2024-03 | 320 | 21.7 | 28.1 | 0.0011 | 68 |
| 2024-03 - 2025-06 | 318 | 21.6 | 26.1 | 0.0001 | 44 |
| 2025-06 - 2026-09 | 322 | 21.8 | 28.3 | 0.0023 | 90 |

Hranice pre úsek veľkosti posledného obdobia: -0.0020 až +0.0028 % (medián 0.0005).

**DRZI** — posledné obdobie (2025-06 - 2026-09) je na 90. percentile, teda v medziach -0.0020 až +0.0028 %, ktoré tá istá stratégia vyrobí sama od seba. Úpadok v dátach vidieť nie je.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 5** — 2021-10-19T05:40 až 2021-10-25T08:08, spolu +877.38, rovnako dlhých sérií 3.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2021-10-19T05:40 | 2021-10-19T05:46 | +164.26 | +0.05 | `take_profit` |
| 2 | 2021-10-20T07:15 | 2021-10-20T07:25 | +170.93 | +0.08 | `take_profit` |
| 3 | 2021-10-21T05:05 | 2021-10-21T05:15 | +179.32 | +0.07 | `take_profit` |
| 4 | 2021-10-22T06:50 | 2021-10-22T07:00 | +195.35 | +0.08 | `take_profit` |
| 5 | 2021-10-25T07:45 | 2021-10-25T08:08 | +167.52 | +0.09 | `take_profit` |

**Straty za sebou: 20** — 2021-10-26T05:05 až 2021-11-22T07:25, spolu -1393.76, rovnako dlhých sérií 2.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2021-10-26T05:05 | 2021-10-26T05:12 | -111.71 | -0.03 | `stop_loss` |
| 2 | 2021-10-27T06:30 | 2021-10-27T06:55 | -9.84 | -0.00 | `trailing_stop` |
| 3 | 2021-10-28T04:20 | 2021-10-28T04:31 | -100.96 | -0.03 | `stop_loss` |
| 4 | 2021-10-29T04:35 | 2021-10-29T04:57 | -5.39 | -0.00 | `trailing_stop` |
| 5 | 2021-11-01T06:00 | 2021-11-01T06:00 | -116.15 | -0.04 | `stop_loss` |
| 6 | 2021-11-02T04:40 | 2021-11-02T05:00 | -109.37 | -0.03 | `stop_loss` |
| 7 | 2021-11-03T04:40 | 2021-11-03T04:40 | -31.81 | -0.01 | `session_end` |
| 8 | 2021-11-04T04:40 | 2021-11-04T04:47 | -114.52 | -0.02 | `stop_loss` |
| 9 | 2021-11-05T04:40 | 2021-11-05T05:05 | -100.62 | -0.03 | `stop_loss` |
| 10 | 2021-11-08T05:20 | 2021-11-08T05:25 | -31.43 | -0.01 | `session_end` |
| 11 | 2021-11-09T06:40 | 2021-11-09T07:05 | -96.46 | -0.03 | `stop_loss` |
| 12 | 2021-11-10T09:20 | 2021-11-10T09:25 | -5.68 | -0.00 | `trailing_stop` |
| 13 | 2021-11-11T14:10 | 2021-11-11T14:16 | -102.78 | -0.05 | `stop_loss` |
| 14 | 2021-11-12T05:50 | 2021-11-12T05:50 | -37.15 | -0.01 | `session_end` |
| 15 | 2021-11-15T05:40 | 2021-11-15T06:11 | -18.03 | -0.01 | `trailing_stop` |
| 16 | 2021-11-16T06:30 | 2021-11-16T06:34 | -105.09 | -0.04 | `stop_loss` |
| 17 | 2021-11-17T05:40 | 2021-11-17T05:45 | -122.58 | -0.03 | `stop_loss` |
| 18 | 2021-11-18T06:05 | 2021-11-18T06:10 | -65.06 | -0.01 | `session_end` |
| 19 | 2021-11-19T06:15 | 2021-11-19T06:15 | -37.47 | -0.01 | `session_end` |
| 20 | 2021-11-22T07:15 | 2021-11-22T07:25 | -71.67 | -0.02 | `session_end` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0005 %**, medián 0.0005 %, 90 % interval -0.0006–0.0017 %
- P(edge > poplatok) = **4.3 %**
- max drawdown: medián 14.4 %, 95. percentil 24.0 %, najhorší 35.2 %
- najdlhšia séria strát: medián 20, 95. percentil 29 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **85** na obchod pri účte 60 000

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
<!-- POSUDOK cisla=9f544f6d -->

_Posudok (Claude, 26. 10. 2026) — nastavenie: repo profil `mnq_databento_5m` (MNQ 5m), nie ladený profil
testera; ladené profily `S3_BTC_*` sú na BTC (posl. rok PF 2,2–2,5)._

1. **Na čo sa to hodí a na čo nie.** V tomto nastavení na nič. Tri kĺzavé priemery + RSI + fraktál ako prerazenie
   (istota dobrá): 1 279 obchodov, 0,71 za deň, medián držania 2,4 baru, winrate 27 %, payoff 2,4; výstupy SL 42 %,
   TP 25 %, trailing 22 %, koniec seansy 11 %.
2. **Má to potenciál?** Nie na MNQ. Zisková v 1 z 5 okien (len 2025/26 +0,48 %), break-even 0,0005 % pod poplatkom
   0,0018 %, nad poplatkom 4 % vzoriek, +1,0 σ proti náhode. Edge „drží“ (90. percentil posledného obdobia), lebo bol
   vždy okolo nuly; drawdown malý (95. percentil 24 % je pri tomto riziku skôr dĺžka série strát do 20).
3. **Čo treba dorobiť.** Repo profil je Pine default prenesený na MNQ; ladené nastavenia sú len BTC a vybrané na
   poslednom roku. Na MNQ chýba akékoľvek ladenie — dokument hovorí o defaultoch, nie o stratégii v najlepšom stave.
4. **Čo otestovať ďalej.** `cli checkup --strategy scalp3ma --profile tester/profiles/S3_BTC_148obch_WR66_PF2_5.json
   --pair BTC/USDT:USDT` — či BTC profil prežije päť rokov. Ak ziskový ostane len rok ladenia (ako pri ostatných
   „posl. rok“ profiloch v tejto dávke), stratégiu odložiť.
5. **Je to použiteľné?** Nie. Na MNQ pod poplatkom, odlíšenie od náhody 1 σ.
6. **Čo by som pridal.** Trailing (22 % výstupov) zapínať až po 1 R zisku — pri payoffe 2,4 a winrate 27 % sa dnes
   časť obchodov, ktoré by došli na TP, zatvorí trailingom predčasne.

<!-- POSUDOK KONIEC -->
