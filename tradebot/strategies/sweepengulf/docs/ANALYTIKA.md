# Základná analytika — SWEEPING ENGULF 1.0 (LuxAlgo video) (`sweepengulf`)

Zmerané 2026-10-26 na `MNQ/USD` 4h, engine `multicharts`, poplatok 0.0018 % na stranu (zadané cez --fee), profil `tradebot/strategies/sweepengulf/configs/mnq_databento_4h.json`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy sweepengulf \
   --profile tradebot/strategies/sweepengulf/configs/mnq_databento_4h.json \
   --pair MNQ/USD \
   --timeframe 4h \
   --fee 1.755e-05 \
   --wallet 60000
```

## V čom je dobrá

- break-even 0.0236 % je nad poplatkom 0.0018 % (rezerva +0.0218 bodu)
- charakter: prerazenie (breakout) (istota dobrá) — vie sa teda, čo je pri nej normálne a čo ladiť

## Kde má chyby

- zisková v 2 z 5 referenčných okien (20221001-20231001, 20231001-20241001, 20250904-20260904 v strate)
- edge nad poplatkom len v 62 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- 95. percentil max drawdownu 28.7 % (namerané 13.8 % medián) — na účet to treba mať
- proti náhode len +0.3 sigma: náznak, nie dôkaz
- POZOR NA TREND: každé z 4 období je horšie než predchádzajúce (sklon -0.0683 na obdobie). Posledné je ešte v medziach (26. percentil), takže test úpadok nepotvrdzuje — ale rad sa sám od seba zoradí zriedka. Zopakuj to, keď pribudnú dáta.
- najhoršia skupina 's trendom' vlastnosti 'S trendom, alebo proti': 150 obchodov (79.4 %), bez nej by break-even bol o +0.2599 lepší

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | séria +/- | beh |
|---|---|---|---|---|---|---|---|
| 20211001-20221001 | 34 | +6.93 | 0.2171 | 4.4 | 41.2 | +6/-6 | `20261026-131819-6289e0` |
| 20221001-20231001 | 38 | -2.81 | -0.0822 | 4.9 | 28.9 | +2/-7 | `20261026-131823-f23878` |
| 20231001-20241001 | 39 | -0.53 | -0.0095 | 5.8 | 38.5 | +4/-5 | `20261026-131827-0b6249` |
| 20240904-20250904 | 37 | +7.08 | 0.1388 | 6.7 | 37.8 | +3/-9 | `20261026-131831-25062e` |
| 20250904-20260904 | 43 | -7.17 | -0.0912 | 9.0 | 30.2 | +3/-6 | `20261026-131835-0c8e52` |

Zisková v **2 z 5** okien, obchodov spolu 189, break-even celkom 0.0236 %. Okná sa prekrývajú, 2 obchodov započítaných dvakrát vypadlo.

## Charakter

**Prerazenie (breakout)** (istota dobrá)

- vstup po pohybe v smere obchodu (+0.85 ATR za 5 barov)
- medián držania 5.7 barov grafu
- winrate 35.45 %, payoff 1.94
- 0.11 obchodov za deň
- šikmosť výnosov +1.983

- **Čo je normálne:** Dlhé série strát sú normálne — platí sa nimi za tie prerazenia, ktoré vyjdú. Winrate pod 40 % je pri tomto type v poriadku.
- **Na čo pozor:** Falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či je trh vôbec v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Čo ladiť:** Prahy vstupu (aká veľká musí byť sviečka/pohyb) a RR. Nie winrate — ten sa dá zvýšiť len skrátením TP, a tým sa stratégia pokazí.

Výstupy: `stop_loss` 64 %, `take_profit` 34.9 %, `force_exit` 1.1 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Najhorsia skupina je 's trendom' vlastnosti 'S trendom, alebo proti': 150 obchodov (79.4 %), break-even -0.0452 % oproti 0.0236 % celku. Bez nej by break-even bol 0.2835 % (+0.2599). Je to ale VACSINA obchodov, takze to nie je filter, ale nastavenie: hladaj parameter, ktory tuto vlastnost riadi.


**S trendom, alebo proti**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| s trendom | 150 | 79.4 % | 32.7 | -0.0452 | 0.2835 | +0.2599 |
| proti trendu | 39 | 20.6 % | 46.1 | 0.2835 | -0.0452 | -0.0688 |

**Hodina vstupu (UTC)**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 8 h – 16 h | 111 | 58.7 % | 31.5 | -0.0559 | 0.1310 | +0.1074 |
| do 8 h | 62 | 32.8 % | 41.9 | 0.1249 | -0.0307 | -0.0543 |
| nad 16 h | 16 | 8.5 % | 37.5 | 0.1592 | 0.0125 | -0.0111 |

**Trend alebo rozsah**

| skupina | obchodov | podiel | WR % | break-even % | bez nej | zmena |
|---|---|---|---|---|---|---|
| 0.1528 – 0.2684 | 47 | 24.9 % | 25.5 | -0.1430 | 0.0771 | +0.0535 |
| nad 0.2684 | 47 | 24.9 % | 36.2 | 0.0222 | 0.0241 | +0.0005 |
| 0.0692 – 0.1528 | 47 | 24.9 % | 40.4 | 0.0764 | 0.0069 | -0.0167 |
| do 0.0692 | 48 | 25.4 % | 39.6 | 0.1286 | -0.0149 | -0.0385 |

Parametre, ktorými sa dá s tým niečo spraviť: `rrRatio`, `tradeDirection`.

## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0236 % | 0.0068 % ± 0.0562 | +0.30 | 62.0 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0236 % | 0.0069 % ± 0.0570 | +0.29 | 61.6 |

Neodlisitelne od nahody (+0.3 sigma, percentil 62.0). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2021-10 - 2022-12 | 46 | 3.1 | 39.1 | 0.1399 | 79 |
| 2022-12 - 2024-03 | 42 | 2.9 | 38.1 | 0.0918 | 71 |
| 2024-03 - 2025-06 | 52 | 3.5 | 32.7 | 0.0229 | 51 |
| 2025-06 - 2026-09 | 49 | 3.3 | 32.6 | -0.0647 | 26 |

Hranice pre úsek veľkosti posledného obdobia: -0.1855 až +0.2796 % (medián 0.0186).

**POZOR NA TREND** — každé z 4 období je horšie než predchádzajúce (sklon -0.0683 na obdobie). Posledné je ešte v medziach (26. percentil), takže test úpadok nepotvrdzuje — ale rad sa sám od seba zoradí zriedka. Zopakuj to, keď pribudnú dáta.

## Najdlhšie série

Koľko ziskov a koľko strát prišlo **za sebou** — to, čo priemerný winrate zamlčí a čo musí vydržať účet aj ten, kto stratégiu obchoduje. Obchody idú v poradí zatvorenia cez všetky okná; nulový obchod sériu preruší.

**Zisky za sebou: 6** — 2022-01-13T16:00 až 2022-03-07T18:14, spolu +5400.29.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2022-01-13T16:00 | 2022-01-14T12:59 | +862.41 | +2.74 | `take_profit` |
| 2 | 2022-01-18T04:00 | 2022-01-18T20:44 | +547.92 | +1.77 | `take_profit` |
| 3 | 2022-01-20T20:00 | 2022-01-21T15:20 | +1024.46 | +3.40 | `take_profit` |
| 4 | 2022-01-21T20:00 | 2022-01-24T17:09 | +1388.01 | +4.78 | `take_profit` |
| 5 | 2022-02-02T16:00 | 2022-02-03T16:59 | +786.46 | +2.61 | `take_profit` |
| 6 | 2022-03-04T04:00 | 2022-03-07T18:14 | +791.04 | +2.85 | `take_profit` |

**Straty za sebou: 9** — 2024-10-29T08:00 až 2025-01-16T15:00, spolu -3723.23.

| # | vstup | výstup | PnL | % | dôvod |
|---|---|---|---|---|---|
| 1 | 2024-10-29T08:00 | 2024-10-29T13:32 | -153.94 | -0.38 | `stop_loss` |
| 2 | 2024-10-29T16:00 | 2024-10-30T22:24 | -381.44 | -0.92 | `stop_loss` |
| 3 | 2024-10-31T16:00 | 2024-11-06T01:06 | -698.42 | -1.74 | `stop_loss` |
| 4 | 2024-11-18T16:00 | 2024-11-19T13:48 | -400.44 | -0.97 | `stop_loss` |
| 5 | 2024-11-26T12:00 | 2024-11-27T14:53 | -175.47 | -0.42 | `stop_loss` |
| 6 | 2024-12-06T16:00 | 2024-12-09T16:11 | -363.51 | -0.84 | `stop_loss` |
| 7 | 2024-12-10T12:00 | 2024-12-10T17:16 | -128.01 | -0.30 | `stop_loss` |
| 8 | 2024-12-20T16:00 | 2025-01-02T17:49 | -1014.49 | -2.36 | `stop_loss` |
| 9 | 2025-01-16T08:00 | 2025-01-16T15:00 | -407.51 | -0.95 | `stop_loss` |

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 10 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0236 %**, medián 0.0225 %, 90 % interval -0.0851–0.1464 %
- P(edge > poplatok) = **61.9 %**
- max drawdown: medián 13.8 %, 95. percentil 28.7 %, najhorší 53.8 %
- najdlhšia séria strát: medián 10, 95. percentil 14 obchodov
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
<!-- POSUDOK cisla=ebf56ab2 -->

_Posudok (Claude, 26. 10. 2026) — repo profil „mnq_databento_4h“, MNQ 4h; ladený profil testera pre túto stratégiu
nie je._

1. **Na čo sa to hodí a na čo nie.** MNQ 4h, swing: medián držania 5,7 baru (~1 deň), ~38 obchodov ročne, pozície cez
   noc aj víkend. S dnešným rizikom na obchod sa nehodí na prop ani malý účet: 95. percentil drawdownu 28,7 %, najhorší
   54 % zo 60 000 $.
2. **Má to potenciál?** Nie. Break-even 0,0236 % vyzerá nad poplatkom, ale nesú ho dva roky (2021/22 0,217 %, 2024/25
   0,139 %) proti trom stratovým; +0,3 σ proti náhode, nad poplatkom len 62 % bootstrapu. Každé zo štyroch období je
   horšie než predchádzajúce (0,140 → 0,092 → 0,023 → −0,065 %). 189 obchodov na 4h je na rozhodnutie málo.
3. **Čo treba dorobiť.** Smer vzoru: obchody s trendom (150, 79 %) majú break-even −0,045 %, proti trendu (39) +0,28 %.
   Sweep likvidity s pohltením je reverzný vzor — mal by sa brať na extréme proti trendu, port ho berie najmä s ním a
   žiadny parameter to neriadi (len `rrRatio`, `tradeDirection`). Riziko na obchod znížiť podľa Monte Carlo.
4. **Čo otestovať ďalej.** `cli matrix --strategy sweepengulf --profile mnq_databento_4h --pairs all --timeframes 1h,4h`
   — na 1h je obchodov 4× viac a ukáže sa, či myšlienka vôbec drží. Po pridaní filtra proti trendu znova `cli checkup`
   na piatich oknách: rozhodne 4 z 5 a sigma nad 2.
5. **Je to použiteľné?** Nie — neodlíšiteľné od náhody a slabne.
6. **Čo by som pridal.** Podmienku, že sweep berie likviditu proti prevládajúcemu trendu (napr. nad maximom pri cene pod
   EMA 50 na dennom grafe). Jediná skupina, v ktorej čísla dávajú zmysel, je práve tá proti trendu — hoci len 39 obchodov.

<!-- POSUDOK KONIEC -->
